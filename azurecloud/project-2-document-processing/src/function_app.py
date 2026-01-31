"""
Intelligent Document Processing & Classification Pipeline - Azure Functions
============================================================================
Enterprise document processing platform using Azure Document Intelligence
and GPT-4o for extraction, classification, and confidence-based routing.

Datasets: customer_shopping_data.csv + multi-format documents (PDF/DOCX/TIFF/images)
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib
import uuid

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
import redis

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    """Application configuration from environment variables."""

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "documents-index"

    # Database
    DATABASE_NAME = "docprocessor"

    # Classification thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    # Document categories
    DOCUMENT_CATEGORIES = ["invoice", "contract", "form", "compliance", "hr_document"]

    # Cache settings
    CACHE_TTL = 3600  # 1 hour


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None
_redis_client = None
_doc_intelligence_client = None
_blob_service_client = None


def get_credential():
    """Get Azure credential using Managed Identity."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_client() -> AzureOpenAI:
    """Get Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=lambda: get_credential().get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-06-01"
        )
    return _openai_client


def get_search_client() -> SearchClient:
    """Get Azure AI Search client."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=Config.AZURE_SEARCH_ENDPOINT,
            index_name=Config.SEARCH_INDEX,
            credential=get_credential()
        )
    return _search_client


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client(Config.DATABASE_NAME)
    return database.get_container_client(container_name)


def get_redis_client():
    """Get Redis cache client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=Config.REDIS_HOST,
            port=6380,
            ssl=True,
            decode_responses=True
        )
    return _redis_client


def get_document_intelligence_client() -> DocumentAnalysisClient:
    """Get Azure Document Intelligence client."""
    global _doc_intelligence_client
    if _doc_intelligence_client is None:
        _doc_intelligence_client = DocumentAnalysisClient(
            endpoint=Config.DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=get_credential()
        )
    return _doc_intelligence_client


def get_blob_service_client() -> BlobServiceClient:
    """Get Azure Blob Storage client."""
    global _blob_service_client
    if _blob_service_client is None:
        _blob_service_client = BlobServiceClient(
            account_url=Config.STORAGE_ACCOUNT_URL,
            credential=get_credential()
        )
    return _blob_service_client


# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()
    response = client.embeddings.create(
        input=text[:8000],
        model=Config.EMBEDDING_MODEL
    )
    return response.data[0].embedding


def get_cached(cache_key: str) -> Optional[dict]:
    """Retrieve a value from Redis cache."""
    try:
        r = get_redis_client()
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    return None


def set_cached(cache_key: str, data: dict, ttl: int = Config.CACHE_TTL):
    """Store a value in Redis cache."""
    try:
        r = get_redis_client()
        r.setex(cache_key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def determine_routing(confidence: float) -> str:
    """Determine document routing based on confidence score."""
    if confidence >= Config.HIGH_CONFIDENCE_THRESHOLD:
        return "auto_process"
    elif confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD:
        return "human_review"
    else:
        return "manual_review"


# ==============================================================================
# Core Functions — Document Extraction
# ==============================================================================

def extract_document(blob_url: str, model_id: str = "prebuilt-layout") -> dict:
    """
    Extract text, tables, and key-value pairs from a document using
    Azure Document Intelligence.

    Supports models: prebuilt-layout, prebuilt-invoice, prebuilt-receipt,
    prebuilt-idDocument, and custom models.

    Args:
        blob_url: URL of the document in Azure Blob Storage
        model_id: Document Intelligence model to use

    Returns:
        dict with extracted text, tables, key-value pairs, and metadata
    """
    client = get_document_intelligence_client()

    poller = client.begin_analyze_document_from_url(
        model_id,
        document_url=blob_url
    )
    result = poller.result()

    pages = []
    full_text_parts = []
    for page in result.pages:
        page_text = ""
        if page.lines:
            page_text = "\n".join([line.content for line in page.lines])
        pages.append({
            "page_number": page.page_number,
            "text": page_text,
            "width": page.width,
            "height": page.height
        })
        full_text_parts.append(page_text)

    tables = []
    if result.tables:
        for table in result.tables:
            table_data = {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": [
                    {
                        "row": cell.row_index,
                        "column": cell.column_index,
                        "content": cell.content
                    }
                    for cell in table.cells
                ]
            }
            tables.append(table_data)

    key_value_pairs = []
    if hasattr(result, "key_value_pairs") and result.key_value_pairs:
        for kvp in result.key_value_pairs:
            key_value_pairs.append({
                "key": kvp.key.content if kvp.key else "",
                "value": kvp.value.content if kvp.value else "",
                "confidence": kvp.confidence
            })

    return {
        "text": "\n\n".join(full_text_parts),
        "page_count": len(pages),
        "pages": pages,
        "tables": tables,
        "key_value_pairs": key_value_pairs,
        "model_id": model_id,
        "extracted_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Document Classification
# ==============================================================================

def classify_document(text: str) -> dict:
    """
    Classify a document into categories using GPT-4o.

    Categories: invoice, contract, form, compliance, hr_document

    Args:
        text: Extracted document text

    Returns:
        dict with category, confidence, and reasoning
    """
    client = get_openai_client()

    system_prompt = """You are a document classification expert. Classify the given document into one of these categories:
- invoice: Vendor invoices, utility bills, payment requests
- contract: Service agreements, NDAs, SOWs, legal agreements
- form: Application forms, request forms, registration forms
- compliance: KYC documents, AML forms, audit documents, regulatory filings
- hr_document: Resumes, offer letters, performance reviews, employee records

Respond in valid JSON with fields: category, confidence (0.0-1.0), reasoning"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this document:\n\n{text[:8000]}"}
        ],
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    category = result.get("category", "unknown")
    confidence = float(result.get("confidence", 0.0))
    routing = determine_routing(confidence)

    return {
        "category": category,
        "confidence": confidence,
        "reasoning": result.get("reasoning", ""),
        "routing": routing,
        "classified_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Validation
# ==============================================================================

def validate_document(extraction: dict, category: str) -> dict:
    """
    Validate extracted document fields against business rules.

    Checks required fields, value ranges, and cross-field consistency
    based on the document category.

    Args:
        extraction: Extracted document data
        category: Document classification category

    Returns:
        dict with is_valid flag, errors list, and validation details
    """
    errors = []

    # Common validations
    if not extraction.get("text"):
        errors.append("Document text is empty")

    if extraction.get("page_count", 0) == 0:
        errors.append("No pages detected in document")

    # Category-specific validations
    required_fields = {
        "invoice": ["invoice_number", "date", "amount", "vendor"],
        "contract": ["parties", "effective_date", "term"],
        "form": ["form_type", "applicant", "date"],
        "compliance": ["entity", "compliance_type", "date"],
        "hr_document": ["name", "position", "date"]
    }

    kvp_keys = [kvp.get("key", "").lower() for kvp in extraction.get("key_value_pairs", [])]

    category_fields = required_fields.get(category, [])
    missing_fields = []
    for field in category_fields:
        field_found = any(field.replace("_", " ") in k or field in k for k in kvp_keys)
        if not field_found:
            missing_fields.append(field)

    if missing_fields:
        errors.append(f"Missing required fields for {category}: {', '.join(missing_fields)}")

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "category": category,
        "fields_checked": len(category_fields),
        "fields_found": len(category_fields) - len(missing_fields),
        "validated_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Summarization
# ==============================================================================

def summarize_document(text: str, category: str = "general") -> dict:
    """
    Generate a summary of document text using GPT-4o.

    Args:
        text: Extracted document text
        category: Document category for context-aware summarization

    Returns:
        dict with summary, key_points, and metadata
    """
    client = get_openai_client()

    system_prompt = f"""Summarize this {category} document. Provide:
1. A concise executive summary (3-5 sentences)
2. Key data points extracted
3. Action items or notable findings

Respond in valid JSON with fields: summary, key_points (list), action_items (list), word_count"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document text:\n\n{text[:12000]}"}
        ],
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "summary": result.get("summary", ""),
        "key_points": result.get("key_points", []),
        "action_items": result.get("action_items", []),
        "word_count": result.get("word_count", len(text.split())),
        "category": category,
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


# ==============================================================================
# Core Functions — Search
# ==============================================================================

def search_documents(query: str, top_k: int = 10) -> list:
    """
    Search indexed documents using hybrid search (vector + keyword).

    Args:
        query: Search query text
        top_k: Number of results to return

    Returns:
        List of matching documents with scores
    """
    search_client = get_search_client()

    query_vector = generate_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="contentVector"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="default-semantic-config",
        top=top_k,
        select=["id", "title", "category", "summary", "source", "status"]
    )

    documents = []
    for result in results:
        documents.append({
            "id": result["id"],
            "title": result.get("title", "Untitled"),
            "category": result.get("category", ""),
            "summary": result.get("summary", ""),
            "source": result.get("source", ""),
            "status": result.get("status", ""),
            "score": result["@search.score"],
            "reranker_score": result.get("@search.reranker_score", 0)
        })

    return documents


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="extract", methods=["POST"])
async def extract_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document extraction endpoint.

    Request: { "blob_url": "...", "model_id": "prebuilt-layout" }
    """
    try:
        req_body = req.get_json()
        blob_url = req_body.get("blob_url")
        model_id = req_body.get("model_id", "prebuilt-layout")

        if not blob_url:
            return func.HttpResponse(
                json.dumps({"error": "blob_url is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Check cache
        url_hash = hashlib.md5(f"{blob_url}:{model_id}".encode()).hexdigest()
        cache_key = f"docproc:extract:{url_hash}"
        cached = get_cached(cache_key)
        if cached:
            logger.info("Returning cached extraction")
            return func.HttpResponse(
                json.dumps(cached),
                mimetype="application/json"
            )

        logger.info(f"Extracting document: {blob_url}")
        extraction = extract_document(blob_url, model_id)

        # Store extraction in Cosmos DB
        doc_id = str(uuid.uuid4())
        container = get_cosmos_container("extractions")
        record = {
            "id": doc_id,
            "documentId": doc_id,
            "blob_url": blob_url,
            "model_id": model_id,
            **extraction
        }
        container.upsert_item(record)

        set_cached(cache_key, record)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in extract endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="classify", methods=["POST"])
async def classify_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document classification endpoint.

    Request: { "text": "...", "document_id": "..." }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")
        document_id = req_body.get("document_id", str(uuid.uuid4()))

        if not text:
            return func.HttpResponse(
                json.dumps({"error": "text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Classifying document: {document_id}")
        classification = classify_document(text)

        # Store classification result
        container = get_cosmos_container("documents")
        record = {
            "id": document_id,
            "documentId": document_id,
            **classification
        }
        container.upsert_item(record)

        # Route to review queue if needed
        if classification["routing"] == "human_review":
            review_container = get_cosmos_container("reviews")
            review_record = {
                "id": str(uuid.uuid4()),
                "documentId": document_id,
                "category": classification["category"],
                "confidence": classification["confidence"],
                "status": "pending_review",
                "created_at": datetime.utcnow().isoformat()
            }
            review_container.upsert_item(review_record)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in classify endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="validate", methods=["POST"])
async def validate_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document validation endpoint.

    Request: { "extraction": {...}, "category": "invoice" }
    """
    try:
        req_body = req.get_json()
        extraction = req_body.get("extraction")
        category = req_body.get("category")

        if not extraction or not category:
            return func.HttpResponse(
                json.dumps({"error": "extraction and category are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Validating document as {category}")
        validation = validate_document(extraction, category)

        return func.HttpResponse(
            json.dumps(validation),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in validate endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize", methods=["POST"])
async def summarize_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document summarization endpoint.

    Request: { "text": "...", "category": "invoice" }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")
        category = req_body.get("category", "general")

        if not text:
            return func.HttpResponse(
                json.dumps({"error": "text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Summarizing {category} document")
        summary = summarize_document(text, category)

        return func.HttpResponse(
            json.dumps(summary),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarize endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="search", methods=["POST"])
async def search_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document search endpoint.

    Request: { "query": "...", "top_k": 10 }
    """
    try:
        req_body = req.get_json()
        query = req_body.get("query")
        top_k = req_body.get("top_k", 10)

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Searching documents: {query[:50]}...")
        results = search_documents(query, top_k=top_k)

        return func.HttpResponse(
            json.dumps({"query": query, "results": results, "count": len(results)}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="documents/{document_id}", methods=["GET"])
async def get_document_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Retrieve a document record by ID."""
    try:
        document_id = req.route_params.get("document_id")

        if not document_id:
            return func.HttpResponse(
                json.dumps({"error": "document_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        container = get_cosmos_container("documents")
        record = container.read_item(item=document_id, partition_key=document_id)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except CosmosResourceNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": f"Document {document_id} not found"}),
            status_code=404,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in get document endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "document-processing",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger
# ==============================================================================

@app.function_name(name="DocumentUploadTrigger")
@app.event_grid_trigger(arg_name="event")
async def document_upload_trigger(event: func.EventGridEvent):
    """
    Triggered when a new document is uploaded to blob storage.
    Automatically extracts, classifies, validates, and routes the document.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1] if blob_url else "unknown"

        logger.info(f"New document uploaded: {blob_name}")

        # Step 1: Extract
        extraction = extract_document(blob_url)

        # Step 2: Classify
        classification = classify_document(extraction["text"])

        # Step 3: Validate
        validation = validate_document(extraction, classification["category"])

        # Step 4: Store in Cosmos DB
        document_id = str(uuid.uuid4())
        container = get_cosmos_container("documents")
        record = {
            "id": document_id,
            "documentId": document_id,
            "filename": blob_name,
            "blob_url": blob_url,
            "category": classification["category"],
            "confidence": classification["confidence"],
            "routing": classification["routing"],
            "is_valid": validation["is_valid"],
            "status": "processed",
            "processed_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(record)

        # Step 5: Audit log
        audit_container = get_cosmos_container("audit_logs")
        audit_record = {
            "id": str(uuid.uuid4()),
            "documentId": document_id,
            "action": "document_processed",
            "category": classification["category"],
            "confidence": classification["confidence"],
            "routing": classification["routing"],
            "timestamp": datetime.utcnow().isoformat()
        }
        audit_container.upsert_item(audit_record)

        logger.info(f"Document {blob_name} processed: {classification['category']} "
                     f"(confidence: {classification['confidence']:.2f}, "
                     f"routing: {classification['routing']})")

    except Exception as e:
        logger.error(f"Error processing document upload: {e}", exc_info=True)
        raise
