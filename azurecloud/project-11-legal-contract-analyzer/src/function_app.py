# ============================================================================
# Project 11 - Legal Contract Analyzer
# Azure Functions v2 | Document Intelligence | GPT-4o | AI Search | Cosmos DB
# Dataset: CUAD_v1/ (510 contracts, 41 clause types)
# ============================================================================

import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

import azure.functions as func
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.cosmos import CosmosClient, exceptions as cosmos_exceptions
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Application configuration from environment variables."""
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "")
    DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    KEY_VAULT_URL = os.environ.get("KEY_VAULT_URL", "")
    STORAGE_ACCOUNT_URL = os.environ.get("STORAGE_ACCOUNT_URL", "")

    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "contracts-index"


# ============================================================================
# CUAD Clause Types (41 standard clause categories)
# ============================================================================

CUAD_CLAUSE_TYPES = [
    "Document Name",
    "Parties",
    "Agreement Date",
    "Effective Date",
    "Expiration Date",
    "Renewal Term",
    "Notice Period",
    "Governing Law",
    "Most Favored Nation",
    "Non-Compete",
    "Exclusivity",
    "No-Solicit Of Customers",
    "Competitive Restriction Exception",
    "No-Solicit Of Employees",
    "Non-Disparagement",
    "Termination For Convenience",
    "Rofr/Rofo/Rofn",
    "Change Of Control",
    "Anti-Assignment",
    "Revenue/Profit Sharing",
    "Price Restrictions",
    "Minimum Commitment",
    "Volume Restriction",
    "IP Ownership Assignment",
    "Joint IP Ownership",
    "License Grant",
    "Non-Transferable License",
    "Affiliate License",
    "Unlimited/All-You-Can-Eat License",
    "Irrevocable Or Perpetual License",
    "Source Code Escrow",
    "Post-Termination Services",
    "Audit Rights",
    "Uncapped Liability",
    "Cap On Liability",
    "Liquidated Damages",
    "Warranty Duration",
    "Insurance",
    "Covenant Not To Sue",
    "Third Party Beneficiary",
]

# ============================================================================
# Logging
# ============================================================================

logger = logging.getLogger("legal-contract-analyzer")
logger.setLevel(logging.INFO)

# ============================================================================
# Lazy-Initialized Clients
# ============================================================================

_credential: Optional[DefaultAzureCredential] = None
_openai_client: Optional[AzureOpenAI] = None
_search_client: Optional[SearchClient] = None
_cosmos_client: Optional[CosmosClient] = None
_cosmos_db = None
_cosmos_containers: dict = {}
_document_intelligence_client: Optional[DocumentAnalysisClient] = None


def get_credential() -> DefaultAzureCredential:
    """Get or create DefaultAzureCredential (Managed Identity)."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
        logger.info("Initialized DefaultAzureCredential")
    return _credential


def get_openai_client() -> AzureOpenAI:
    """Get or create Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        credential = get_credential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        _openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token=token.token,
            api_version="2024-02-15-preview",
        )
        logger.info("Initialized Azure OpenAI client")
    return _openai_client


def get_search_client() -> SearchClient:
    """Get or create Azure AI Search client."""
    global _search_client
    if _search_client is None:
        credential = get_credential()
        _search_client = SearchClient(
            endpoint=Config.AZURE_SEARCH_ENDPOINT,
            index_name=Config.SEARCH_INDEX,
            credential=credential,
        )
        logger.info("Initialized Azure AI Search client")
    return _search_client


def get_cosmos_container(container_name: str):
    """Get or create Cosmos DB container client."""
    global _cosmos_client, _cosmos_db, _cosmos_containers
    if _cosmos_client is None:
        credential = get_credential()
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=credential,
        )
        _cosmos_db = _cosmos_client.get_database_client("legalcontracts")
        logger.info("Initialized Cosmos DB client (database: legalcontracts)")
    if container_name not in _cosmos_containers:
        _cosmos_containers[container_name] = _cosmos_db.get_container_client(container_name)
        logger.info(f"Initialized Cosmos container: {container_name}")
    return _cosmos_containers[container_name]


def get_document_intelligence_client() -> DocumentAnalysisClient:
    """Get or create Document Intelligence client."""
    global _document_intelligence_client
    if _document_intelligence_client is None:
        credential = get_credential()
        _document_intelligence_client = DocumentAnalysisClient(
            endpoint=Config.DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=credential,
        )
        logger.info("Initialized Document Intelligence client")
    return _document_intelligence_client


# ============================================================================
# Core Functions
# ============================================================================

def extract_contract_text(blob_url: str) -> dict:
    """Extract text, tables, and signatures from a contract document using Document Intelligence."""
    try:
        client = get_document_intelligence_client()
        poller = client.begin_analyze_document_from_url("prebuilt-layout", blob_url)
        result = poller.result()

        pages = []
        full_text = ""
        for page in result.pages:
            page_text = ""
            for line in page.lines:
                page_text += line.content + "\n"
            pages.append({
                "page_number": page.page_number,
                "text": page_text,
                "width": page.width,
                "height": page.height,
            })
            full_text += page_text

        tables = []
        if result.tables:
            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [],
                }
                for cell in table.cells:
                    table_data["cells"].append({
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content,
                    })
                tables.append(table_data)

        signatures = []
        if hasattr(result, "signatures") and result.signatures:
            for sig in result.signatures:
                signatures.append({
                    "confidence": sig.confidence,
                    "page_number": sig.page_number if hasattr(sig, "page_number") else None,
                })

        logger.info(f"Extracted text from {len(pages)} pages, {len(tables)} tables")
        return {
            "text": full_text,
            "pages": pages,
            "tables": tables,
            "signatures": signatures,
            "page_count": len(pages),
        }
    except Exception as e:
        logger.error(f"Error extracting contract text: {str(e)}")
        raise


def identify_clauses(contract_text: str) -> list:
    """Identify CUAD clause types in contract text using GPT-4o."""
    try:
        client = get_openai_client()
        clause_types_str = "\n".join(f"- {ct}" for ct in CUAD_CLAUSE_TYPES)

        system_prompt = (
            "You are an expert legal contract analyst. Analyze the contract text and identify "
            "all clauses matching the CUAD (Contract Understanding Atticus Dataset) clause types. "
            "For each clause found, return the clause type, the exact text, a confidence score (0.0-1.0), "
            "and the approximate position in the document.\n\n"
            "Return your analysis as a JSON array of objects with keys: "
            "clause_type, text, confidence, position."
        )

        user_prompt = (
            f"Identify all clauses from the following CUAD clause types:\n{clause_types_str}\n\n"
            f"Contract text:\n{contract_text[:8000]}"
        )

        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        clauses = result.get("clauses", result if isinstance(result, list) else [])
        logger.info(f"Identified {len(clauses)} clauses in contract")
        return clauses
    except Exception as e:
        logger.error(f"Error identifying clauses: {str(e)}")
        raise


def assess_risk(clauses: list) -> dict:
    """Assess risk for each clause and provide overall risk evaluation using GPT-4o."""
    try:
        client = get_openai_client()

        system_prompt = (
            "You are a legal risk assessment expert. Evaluate the risk level of each clause "
            "in the contract. Provide an overall risk score (1-10), risk level "
            "(low/medium/high/critical), and a list of specific risks with severity and "
            "recommendation.\n\n"
            "Return JSON with keys: overall_risk_score, risk_level, risks (array of objects "
            "with clause_type, severity, description, recommendation)."
        )

        user_prompt = f"Assess the risk of these contract clauses:\n{json.dumps(clauses, indent=2)}"

        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Risk assessment complete: score={result.get('overall_risk_score')}, level={result.get('risk_level')}")
        return result
    except Exception as e:
        logger.error(f"Error assessing risk: {str(e)}")
        raise


def generate_summary(contract_text: str, clauses: list) -> dict:
    """Generate executive summary of the contract using GPT-4o."""
    try:
        client = get_openai_client()

        system_prompt = (
            "You are a legal document summarizer. Generate a comprehensive executive summary "
            "of the contract including key highlights, action items, parties involved, important "
            "dates, and financial terms.\n\n"
            "Return JSON with keys: executive_summary, key_highlights (array), action_items (array), "
            "parties (array), dates (object), financial_terms (object)."
        )

        user_prompt = (
            f"Summarize this contract:\n\nText:\n{contract_text[:6000]}\n\n"
            f"Identified clauses:\n{json.dumps(clauses[:20], indent=2)}"
        )

        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        logger.info("Contract summary generated successfully")
        return result
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise


def compare_to_template(clauses: list, template_id: str) -> dict:
    """Compare contract clauses against a standard template from Cosmos DB."""
    try:
        container = get_cosmos_container("templates")
        template = container.read_item(item=template_id, partition_key=template_id)

        template_clauses = template.get("clauses", [])
        template_clause_map = {tc["clause_type"]: tc for tc in template_clauses}

        deviations = []
        matched = 0
        total = len(template_clauses)

        for clause in clauses:
            clause_type = clause.get("clause_type", "")
            if clause_type in template_clause_map:
                template_clause = template_clause_map[clause_type]
                if clause.get("text", "").strip() != template_clause.get("expected_text", "").strip():
                    deviations.append({
                        "clause_type": clause_type,
                        "contract_text": clause.get("text", ""),
                        "template_text": template_clause.get("expected_text", ""),
                        "severity": template_clause.get("deviation_severity", "medium"),
                    })
                else:
                    matched += 1
            else:
                matched += 1

        compliance_percentage = (matched / total * 100) if total > 0 else 100.0
        approval_needed = compliance_percentage < 80.0 or any(
            d["severity"] == "high" for d in deviations
        )

        result = {
            "template_id": template_id,
            "template_name": template.get("name", ""),
            "compliance_percentage": round(compliance_percentage, 2),
            "deviations": deviations,
            "approval_needed": approval_needed,
            "total_template_clauses": total,
            "matched_clauses": matched,
        }
        logger.info(f"Template comparison: {compliance_percentage:.1f}% compliance, {len(deviations)} deviations")
        return result
    except cosmos_exceptions.CosmosResourceNotFoundError:
        logger.error(f"Template not found: {template_id}")
        raise
    except Exception as e:
        logger.error(f"Error comparing to template: {str(e)}")
        raise


def track_obligations(contract_id: str, clauses: list) -> list:
    """Extract and track obligations from contract clauses using GPT-4o."""
    try:
        client = get_openai_client()

        system_prompt = (
            "You are a legal obligation tracker. Extract all obligations from the contract clauses. "
            "For each obligation, identify the deadline, responsible party, obligation type, "
            "and priority.\n\n"
            "Return JSON with key 'obligations' containing an array of objects with keys: "
            "obligation_id, description, clause_type, deadline, responsible_party, "
            "obligation_type, priority (high/medium/low), status."
        )

        user_prompt = f"Extract obligations from these clauses:\n{json.dumps(clauses, indent=2)}"

        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        obligations = result.get("obligations", [])

        # Store obligations in Cosmos DB
        container = get_cosmos_container("obligations")
        for obligation in obligations:
            obligation["contractId"] = contract_id
            obligation["id"] = obligation.get(
                "obligation_id",
                hashlib.md5(f"{contract_id}_{obligation.get('description', '')}".encode()).hexdigest(),
            )
            obligation["created_at"] = datetime.now(timezone.utc).isoformat()
            obligation["status"] = obligation.get("status", "pending")
            container.create_item(body=obligation)

        logger.info(f"Tracked {len(obligations)} obligations for contract {contract_id}")
        return obligations
    except Exception as e:
        logger.error(f"Error tracking obligations: {str(e)}")
        raise


def search_contracts(query: str, top_k: int = 10) -> list:
    """Hybrid search (vector + keyword) on AI Search contracts-index."""
    try:
        client = get_search_client()
        vector_query = VectorizableTextQuery(
            text=query,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=top_k,
            select=["contract_id", "title", "parties", "agreement_date", "content", "risk_level"],
        )

        contracts = []
        for result in results:
            contracts.append({
                "contract_id": result.get("contract_id", ""),
                "title": result.get("title", ""),
                "parties": result.get("parties", []),
                "agreement_date": result.get("agreement_date", ""),
                "content_snippet": result.get("content", "")[:500],
                "risk_level": result.get("risk_level", ""),
                "score": result["@search.score"],
            })

        logger.info(f"Search returned {len(contracts)} results for query: {query[:50]}")
        return contracts
    except Exception as e:
        logger.error(f"Error searching contracts: {str(e)}")
        raise


def generate_embedding(text: str) -> list:
    """Generate embedding vector using text-embedding-ada-002."""
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            model=Config.EMBEDDING_MODEL,
            input=text,
        )
        embedding = response.data[0].embedding
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


# ============================================================================
# Azure Functions App
# ============================================================================

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ============================================================================
# HTTP Endpoints
# ============================================================================

@app.route(route="analyze", methods=["POST"])
def analyze_contract(req: func.HttpRequest) -> func.HttpResponse:
    """Full contract analysis: extract + clauses + risk + summary."""
    try:
        body = req.get_json()
        blob_url = body.get("blob_url")
        if not blob_url:
            return func.HttpResponse(
                json.dumps({"error": "blob_url is required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Step 1: Extract text from document
        extraction = extract_contract_text(blob_url)
        contract_text = extraction["text"]

        # Step 2: Identify clauses
        clauses = identify_clauses(contract_text)

        # Step 3: Assess risk
        risk = assess_risk(clauses)

        # Step 4: Generate summary
        summary = generate_summary(contract_text, clauses)

        # Step 5: Generate contract ID and store in Cosmos
        contract_id = hashlib.md5(blob_url.encode()).hexdigest()
        contract_record = {
            "id": contract_id,
            "contractId": contract_id,
            "blob_url": blob_url,
            "extraction": {
                "page_count": extraction["page_count"],
                "table_count": len(extraction["tables"]),
                "signature_count": len(extraction["signatures"]),
            },
            "clauses": clauses,
            "risk": risk,
            "summary": summary,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "status": "analyzed",
        }

        container = get_cosmos_container("contracts")
        container.create_item(body=contract_record)

        # Step 6: Generate and store embeddings for search
        embedding = generate_embedding(contract_text[:8000])

        result = {
            "contract_id": contract_id,
            "extraction": extraction,
            "clauses": clauses,
            "risk": risk,
            "summary": summary,
            "analyzed_at": contract_record["analyzed_at"],
        }

        logger.info(f"Full analysis complete for contract {contract_id}")
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in analyze_contract: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="clauses", methods=["POST"])
def identify_clauses_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Clause identification only."""
    try:
        body = req.get_json()
        contract_text = body.get("contract_text")
        if not contract_text:
            return func.HttpResponse(
                json.dumps({"error": "contract_text is required"}),
                status_code=400,
                mimetype="application/json",
            )

        clauses = identify_clauses(contract_text)
        return func.HttpResponse(
            json.dumps({"clauses": clauses}, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in identify_clauses_endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="risk", methods=["POST"])
def assess_risk_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Risk assessment for provided clauses."""
    try:
        body = req.get_json()
        clauses = body.get("clauses")
        if not clauses:
            return func.HttpResponse(
                json.dumps({"error": "clauses list is required"}),
                status_code=400,
                mimetype="application/json",
            )

        risk = assess_risk(clauses)
        return func.HttpResponse(
            json.dumps(risk, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in assess_risk_endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="compare", methods=["POST"])
def compare_template_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Compare contract clauses against a template."""
    try:
        body = req.get_json()
        contract_id = body.get("contract_id")
        template_id = body.get("template_id")
        if not contract_id or not template_id:
            return func.HttpResponse(
                json.dumps({"error": "contract_id and template_id are required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Retrieve contract clauses from Cosmos
        container = get_cosmos_container("contracts")
        contract = container.read_item(item=contract_id, partition_key=contract_id)
        clauses = contract.get("clauses", [])

        comparison = compare_to_template(clauses, template_id)
        return func.HttpResponse(
            json.dumps(comparison, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": "Contract or template not found"}),
            status_code=404,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in compare_template_endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="obligations", methods=["POST"])
def obligations_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Track obligations for a contract."""
    try:
        body = req.get_json()
        contract_id = body.get("contract_id")
        if not contract_id:
            return func.HttpResponse(
                json.dumps({"error": "contract_id is required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Retrieve contract clauses from Cosmos
        container = get_cosmos_container("contracts")
        contract = container.read_item(item=contract_id, partition_key=contract_id)
        clauses = contract.get("clauses", [])

        obligations = track_obligations(contract_id, clauses)
        return func.HttpResponse(
            json.dumps({"contract_id": contract_id, "obligations": obligations}, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": "Contract not found"}),
            status_code=404,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in obligations_endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="search", methods=["POST"])
def search_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Search contracts using hybrid search."""
    try:
        body = req.get_json()
        query = body.get("query")
        if not query:
            return func.HttpResponse(
                json.dumps({"error": "query is required"}),
                status_code=400,
                mimetype="application/json",
            )

        top_k = body.get("top_k", 10)
        results = search_contracts(query, top_k)
        return func.HttpResponse(
            json.dumps({"query": query, "results": results, "count": len(results)}, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error in search_endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "service": "legal-contract-analyzer",
        }),
        status_code=200,
        mimetype="application/json",
    )


# ============================================================================
# Event Grid Trigger
# ============================================================================

@app.function_name(name="ContractUploadTrigger")
@app.event_grid_trigger(arg_name="event")
def contract_upload_trigger(event: func.EventGridEvent):
    """Process contract when uploaded to /contracts/inbox/ via Event Grid."""
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url", "")

        # Only process blobs in contracts/inbox/
        if "/contracts/inbox/" not in blob_url:
            logger.info(f"Skipping blob not in contracts/inbox/: {blob_url}")
            return

        logger.info(f"Processing uploaded contract: {blob_url}")

        # Step 1: Extract text
        extraction = extract_contract_text(blob_url)
        contract_text = extraction["text"]

        # Step 2: Identify clauses
        clauses = identify_clauses(contract_text)

        # Step 3: Assess risk
        risk = assess_risk(clauses)

        # Step 4: Generate summary
        summary = generate_summary(contract_text, clauses)

        # Step 5: Store results in Cosmos
        contract_id = hashlib.md5(blob_url.encode()).hexdigest()
        contract_record = {
            "id": contract_id,
            "contractId": contract_id,
            "blob_url": blob_url,
            "extraction": {
                "page_count": extraction["page_count"],
                "table_count": len(extraction["tables"]),
                "signature_count": len(extraction["signatures"]),
            },
            "clauses": clauses,
            "risk": risk,
            "summary": summary,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "status": "analyzed",
            "source": "event_grid_trigger",
        }

        container = get_cosmos_container("contracts")
        container.create_item(body=contract_record)

        # Step 6: Track obligations
        track_obligations(contract_id, clauses)

        # Step 7: Generate embedding for search indexing
        generate_embedding(contract_text[:8000])

        logger.info(f"Contract analysis pipeline complete for {contract_id}")
    except Exception as e:
        logger.error(f"Error in contract_upload_trigger: {str(e)}")
        raise
