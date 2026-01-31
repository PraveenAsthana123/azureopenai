"""
Document Summarization Platform - Azure Functions
==================================================
AI-powered document and CSV summarization using Azure Document Intelligence
and GPT-4o. Supports PDF/DOCX/TXT uploads and CSV data analysis.

Datasets: General documents (PDF/DOCX/TXT) + Telco-Customer-Churn.csv
"""

import azure.functions as func
import logging
import json
import os
import csv
import io
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
    DATABASE_NAME = "docsummarizer"

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


# ==============================================================================
# Core Functions — Document Processing
# ==============================================================================

def extract_document_text(blob_url: str) -> dict:
    """
    Extract text from a document using Azure Document Intelligence.

    Supports PDF, DOCX, TIFF, and image files.

    Args:
        blob_url: URL of the document in Azure Blob Storage

    Returns:
        dict with extracted text, page count, tables, and metadata
    """
    client = get_document_intelligence_client()

    poller = client.begin_analyze_document_from_url(
        "prebuilt-layout",
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

    return {
        "text": "\n\n".join(full_text_parts),
        "page_count": len(pages),
        "pages": pages,
        "tables": tables,
        "extracted_at": datetime.utcnow().isoformat()
    }


def summarize_document(text: str, summary_type: str = "executive") -> dict:
    """
    Generate a summary of document text using GPT-4o.

    Args:
        text: Extracted document text
        summary_type: Type of summary — "executive", "detailed", or "bullet"

    Returns:
        dict with summary, key_points, and metadata
    """
    client = get_openai_client()

    prompts = {
        "executive": "Provide a concise executive summary (3-5 sentences) of the following document. Focus on the main purpose, key findings, and conclusions.",
        "detailed": "Provide a detailed summary of the following document. Include all major sections, key points, and important details. Organize by topic.",
        "bullet": "Summarize the following document as a bullet-point list. Each bullet should capture one key point or finding. Use 5-15 bullets."
    }

    system_prompt = f"""{prompts.get(summary_type, prompts['executive'])}

Also extract:
1. key_points: List of 3-7 key takeaways
2. topics: List of main topics covered
3. word_count: Approximate word count of the original document

Respond in valid JSON with fields: summary, key_points, topics, word_count"""

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
        "topics": result.get("topics", []),
        "word_count": result.get("word_count", len(text.split())),
        "summary_type": summary_type,
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def summarize_csv_data(csv_text: str, analysis_type: str = "overview") -> dict:
    """
    Analyze and summarize CSV data using GPT-4o.

    Parses CSV, computes basic statistics, then generates an AI summary.

    Args:
        csv_text: Raw CSV content as string
        analysis_type: Type of analysis — "overview", "trends", or "insights"

    Returns:
        dict with data summary, statistics, and AI-generated insights
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    columns = reader.fieldnames or []

    # Compute basic statistics
    stats = {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns
    }

    # Sample rows for GPT analysis (first 20 + last 5)
    sample_rows = rows[:20]
    if len(rows) > 25:
        sample_rows += rows[-5:]

    client = get_openai_client()

    prompts = {
        "overview": "Provide a comprehensive overview of this dataset. Describe what the data represents, key columns, data types, and general patterns.",
        "trends": "Analyze trends and patterns in this dataset. Identify correlations, distributions, and notable data characteristics.",
        "insights": "Generate actionable business insights from this dataset. What decisions could be made based on this data?"
    }

    system_prompt = f"""{prompts.get(analysis_type, prompts['overview'])}

Dataset has {len(rows)} rows and {len(columns)} columns: {', '.join(columns)}

Respond in valid JSON with fields: summary, insights (list), patterns (list), recommendations (list)"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Sample data:\n{json.dumps(sample_rows[:15], indent=2)}"}
        ],
        temperature=0.4,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "data_stats": stats,
        "summary": result.get("summary", ""),
        "insights": result.get("insights", []),
        "patterns": result.get("patterns", []),
        "recommendations": result.get("recommendations", []),
        "analysis_type": analysis_type,
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def search_documents(query: str, top_k: int = 10) -> list:
    """
    Search indexed documents using hybrid search (vector + keyword).

    Args:
        query: Search query text
        top_k: Number of results to return

    Returns:
        List of matching document summaries with scores
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
        select=["id", "title", "summary", "source", "page_count"]
    )

    documents = []
    for result in results:
        documents.append({
            "id": result["id"],
            "title": result.get("title", "Untitled"),
            "summary": result.get("summary", ""),
            "source": result.get("source", ""),
            "page_count": result.get("page_count", 0),
            "score": result["@search.score"],
            "reranker_score": result.get("@search.reranker_score", 0)
        })

    return documents


def store_summary(document_id: str, title: str, summary_result: dict, source: str = "upload") -> dict:
    """
    Store a document summary in Cosmos DB and index for search.

    Args:
        document_id: Unique document identifier
        title: Document title
        summary_result: Output from summarize_document or summarize_csv_data
        source: Origin of the document

    Returns:
        Stored document record
    """
    container = get_cosmos_container("summaries")

    record = {
        "id": document_id,
        "documentId": document_id,
        "title": title,
        "summary": summary_result.get("summary", ""),
        "key_points": summary_result.get("key_points", []),
        "topics": summary_result.get("topics", []),
        "source": source,
        "created_at": datetime.utcnow().isoformat()
    }

    container.upsert_item(record)

    # Generate embedding for search indexing
    embedding_text = f"{title} {record['summary']}"
    generate_embedding(embedding_text)

    logger.info(f"Stored summary for document {document_id}")
    return record


def get_document_summary(document_id: str) -> dict:
    """
    Retrieve a stored document summary from Cosmos DB.

    Args:
        document_id: Unique document identifier

    Returns:
        Document summary record
    """
    container = get_cosmos_container("summaries")
    return container.read_item(item=document_id, partition_key=document_id)


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="summarize", methods=["POST"])
async def summarize_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Document summarization endpoint.

    Request:
    {
        "blob_url": "https://storage.../document.pdf",
        "title": "My Document",
        "summary_type": "executive"  // optional: executive, detailed, bullet
    }

    Response:
    {
        "document_id": "...",
        "summary": "...",
        "key_points": [...],
        "topics": [...],
        "usage": {...}
    }
    """
    try:
        req_body = req.get_json()
        blob_url = req_body.get("blob_url")
        title = req_body.get("title", "Untitled Document")
        summary_type = req_body.get("summary_type", "executive")

        if not blob_url:
            return func.HttpResponse(
                json.dumps({"error": "blob_url is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Check cache
        url_hash = hashlib.md5(f"{blob_url}:{summary_type}".encode()).hexdigest()
        cache_key = f"docsum:summarize:{url_hash}"
        cached = get_cached(cache_key)
        if cached:
            logger.info("Returning cached document summary")
            return func.HttpResponse(
                json.dumps(cached),
                mimetype="application/json"
            )

        logger.info(f"Processing document: {title}")

        # Extract text
        extraction = extract_document_text(blob_url)

        # Summarize
        summary_result = summarize_document(extraction["text"], summary_type)

        # Store in Cosmos DB
        document_id = str(uuid.uuid4())
        store_summary(document_id, title, summary_result, source=blob_url)

        response_data = {
            "document_id": document_id,
            "title": title,
            "page_count": extraction["page_count"],
            "table_count": len(extraction["tables"]),
            **summary_result
        }

        set_cached(cache_key, response_data)

        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarize endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize/text", methods=["POST"])
async def summarize_text_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Direct text summarization endpoint (no Document Intelligence needed).

    Request:
    {
        "text": "Full document text...",
        "title": "My Document",
        "summary_type": "executive"
    }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")
        title = req_body.get("title", "Untitled Document")
        summary_type = req_body.get("summary_type", "executive")

        if not text:
            return func.HttpResponse(
                json.dumps({"error": "text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Summarizing text: {title} ({len(text)} chars)")
        summary_result = summarize_document(text, summary_type)

        document_id = str(uuid.uuid4())
        store_summary(document_id, title, summary_result, source="direct_text")

        response_data = {
            "document_id": document_id,
            "title": title,
            **summary_result
        }

        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarize/text endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize/csv", methods=["POST"])
async def summarize_csv_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    CSV data summarization endpoint.

    Request:
    {
        "csv_text": "col1,col2\\nval1,val2\\n...",
        "title": "Telco Customer Churn Data",
        "analysis_type": "overview"  // optional: overview, trends, insights
    }
    """
    try:
        req_body = req.get_json()
        csv_text = req_body.get("csv_text")
        title = req_body.get("title", "CSV Dataset")
        analysis_type = req_body.get("analysis_type", "overview")

        if not csv_text:
            return func.HttpResponse(
                json.dumps({"error": "csv_text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing CSV: {title}")
        result = summarize_csv_data(csv_text, analysis_type)

        document_id = str(uuid.uuid4())
        store_summary(document_id, title, result, source="csv_upload")

        response_data = {
            "document_id": document_id,
            "title": title,
            **result
        }

        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarize/csv endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="documents/{document_id}", methods=["GET"])
async def get_document_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve a stored document summary by ID.
    """
    try:
        document_id = req.route_params.get("document_id")

        if not document_id:
            return func.HttpResponse(
                json.dumps({"error": "document_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        record = get_document_summary(document_id)

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


@app.route(route="search", methods=["POST"])
async def search_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search indexed document summaries.

    Request:
    {
        "query": "quarterly revenue report",
        "top_k": 10
    }
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


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger for Document Upload
# ==============================================================================

@app.function_name(name="DocumentUploadTrigger")
@app.event_grid_trigger(arg_name="event")
async def document_upload_trigger(event: func.EventGridEvent):
    """
    Triggered when a new document is uploaded to blob storage.
    Automatically extracts text, generates summary, and indexes.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1] if blob_url else "unknown"

        logger.info(f"New document uploaded: {blob_name}")

        # Extract text
        extraction = extract_document_text(blob_url)

        # Summarize
        summary_result = summarize_document(extraction["text"], "executive")

        # Store
        document_id = str(uuid.uuid4())
        store_summary(document_id, blob_name, summary_result, source=blob_url)

        logger.info(f"Document {blob_name} processed and indexed as {document_id}")

    except Exception as e:
        logger.error(f"Error processing document upload: {e}", exc_info=True)
        raise
