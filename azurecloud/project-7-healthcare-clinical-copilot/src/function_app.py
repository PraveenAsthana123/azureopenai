"""
Healthcare Clinical Copilot - Azure Functions
===================================================
Clinical decision support with medical NER, drug interactions, and patient summaries
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
import requests

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
    FHIR_ENDPOINT = os.getenv("FHIR_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    FHIR_API_VERSION = "2023-11-01"

    # Clinical parameters
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3  # Lower temperature for clinical accuracy
    NER_TEMPERATURE = 0.1  # Near-deterministic for entity extraction


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_cosmos_client = None


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


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client("clinicalcopilot")
    return database.get_container_client(container_name)


def get_keyvault_secret(secret_name: str) -> str:
    """Retrieve a secret from Azure Key Vault."""
    client = SecretClient(
        vault_url=Config.KEY_VAULT_URL,
        credential=get_credential()
    )
    return client.get_secret(secret_name).value


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def extract_medical_entities(text: str) -> dict:
    """
    Extract medical entities from clinical notes using Azure OpenAI.

    Identifies conditions, medications, procedures, lab values,
    and anatomical references from unstructured clinical text.

    Args:
        text: Raw clinical note or patient narrative

    Returns:
        Dictionary with categorized medical entities
    """
    client = get_openai_client()

    system_prompt = """You are a clinical NLP engine for a HIPAA-compliant medical system.
Extract all medical entities from the provided clinical text and return them as structured JSON.

Return ONLY valid JSON with these keys:
- conditions: list of medical conditions/diagnoses (with ICD-10 codes if identifiable)
- medications: list of medications (with dosage if mentioned)
- procedures: list of medical procedures or surgeries
- lab_values: list of lab results with values and units
- allergies: list of known allergies
- vitals: list of vital signs with values

Be precise. Do not infer entities that are not explicitly stated."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=2048,
        temperature=Config.NER_TEMPERATURE,
        response_format={"type": "json_object"}
    )

    entities = json.loads(response.choices[0].message.content)

    logger.info(
        f"Extracted entities: {len(entities.get('conditions', []))} conditions, "
        f"{len(entities.get('medications', []))} medications, "
        f"{len(entities.get('procedures', []))} procedures"
    )

    return entities


def check_drug_interactions(medications: list[str]) -> dict:
    """
    Check for drug-drug interactions using Azure OpenAI with structured output.

    Args:
        medications: List of medication names to check for interactions

    Returns:
        Dictionary with interaction details and severity levels
    """
    if len(medications) < 2:
        return {
            "interactions": [],
            "risk_level": "none",
            "message": "At least two medications are required to check interactions."
        }

    client = get_openai_client()

    system_prompt = """You are a clinical pharmacology decision support system.
Analyze the provided list of medications for potential drug-drug interactions.

Return ONLY valid JSON with these keys:
- interactions: list of objects, each with:
    - drug_pair: [drug_a, drug_b]
    - severity: "contraindicated" | "major" | "moderate" | "minor" | "none"
    - description: brief clinical description of the interaction
    - mechanism: pharmacological mechanism
    - recommendation: clinical action recommendation
- risk_level: overall risk level ("critical" | "high" | "moderate" | "low" | "none")
- summary: brief overall summary

Base your analysis on established pharmacological evidence. Flag unknown or uncertain interactions clearly."""

    medications_text = ", ".join(medications)

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Check interactions for: {medications_text}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.NER_TEMPERATURE,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    logger.info(
        f"Drug interaction check for {len(medications)} medications: "
        f"risk_level={result.get('risk_level', 'unknown')}, "
        f"interactions_found={len(result.get('interactions', []))}"
    )

    return result


def generate_patient_summary(patient_id: str, fhir_data: dict) -> dict:
    """
    Generate a structured clinical summary from FHIR patient data.

    Args:
        patient_id: FHIR patient resource ID
        fhir_data: Aggregated FHIR resources for the patient

    Returns:
        Structured clinical summary with sections
    """
    client = get_openai_client()

    system_prompt = """You are a clinical summarization engine for a HIPAA-compliant EHR system.
Generate a structured clinical summary from the provided FHIR patient data.

Return ONLY valid JSON with these keys:
- patient_demographics: age, gender, identifiers
- active_conditions: list of current diagnoses with onset dates
- current_medications: list with dosage and frequency
- recent_encounters: summary of recent visits (last 6 months)
- pending_orders: any outstanding lab or imaging orders
- allergies_and_alerts: critical allergy and safety alerts
- care_gaps: identified gaps in preventive care or follow-up
- clinical_narrative: 2-3 paragraph natural language summary

Prioritize clinically significant information. Flag any critical alerts prominently."""

    fhir_json = json.dumps(fhir_data, indent=2, default=str)

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate clinical summary for patient {patient_id}:\n\n{fhir_json}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    summary = json.loads(response.choices[0].message.content)
    summary["patient_id"] = patient_id
    summary["generated_at"] = datetime.utcnow().isoformat()

    logger.info(f"Generated clinical summary for patient {patient_id}")

    return summary


def get_fhir_patient_data(patient_id: str) -> dict:
    """
    Fetch patient data from Azure Health Data Services FHIR endpoint.

    Retrieves Patient, Condition, MedicationRequest, Encounter,
    AllergyIntolerance, and Observation resources.

    Args:
        patient_id: FHIR patient resource ID

    Returns:
        Aggregated patient data from multiple FHIR resources
    """
    credential = get_credential()
    token = credential.get_token("https://fhir.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/fhir+json",
        "x-ms-fhir-version": Config.FHIR_API_VERSION
    }

    base_url = Config.FHIR_ENDPOINT.rstrip("/")

    resource_types = [
        "Patient",
        "Condition",
        "MedicationRequest",
        "Encounter",
        "AllergyIntolerance",
        "Observation"
    ]

    patient_data = {}

    for resource_type in resource_types:
        try:
            if resource_type == "Patient":
                url = f"{base_url}/{resource_type}/{patient_id}"
            else:
                url = f"{base_url}/{resource_type}?patient={patient_id}&_count=50&_sort=-date"

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if resource_type == "Patient":
                patient_data[resource_type.lower()] = data
            else:
                entries = data.get("entry", [])
                patient_data[resource_type.lower()] = [
                    entry.get("resource", {}) for entry in entries
                ]

            logger.info(f"Fetched {resource_type} data for patient {patient_id}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {resource_type} for patient {patient_id}: {e}")
            patient_data[resource_type.lower()] = [] if resource_type != "Patient" else {}

    return patient_data


# ==============================================================================
# Session & History Management
# ==============================================================================

def save_clinical_session(
    session_id: str,
    patient_id: str,
    query: str,
    response_text: str,
    entities: Optional[dict] = None,
    interaction_check: Optional[dict] = None
) -> dict:
    """
    Save a clinical session interaction to Cosmos DB for audit compliance.

    Args:
        session_id: Unique session identifier
        patient_id: FHIR patient ID (if applicable)
        query: Original clinical query
        response_text: Generated response
        entities: Extracted medical entities
        interaction_check: Drug interaction results

    Returns:
        Saved session document
    """
    container = get_cosmos_container("clinicalSessions")

    session_record = {
        "id": hashlib.md5(
            f"{session_id}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest(),
        "sessionId": session_id,
        "patientId": patient_id,
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "response": response_text,
        "entities": entities or {},
        "interactionCheck": interaction_check or {},
        "auditTrail": {
            "action": "clinical_query",
            "accessedAt": datetime.utcnow().isoformat(),
            "complianceFlags": ["HIPAA", "HITECH"]
        }
    }

    container.create_item(body=session_record)
    logger.info(f"Saved clinical session {session_id} for patient {patient_id}")

    return session_record


def get_session_history(session_id: str, limit: int = 20) -> list[dict]:
    """
    Retrieve clinical session history from Cosmos DB.

    Args:
        session_id: Session identifier to query
        limit: Maximum number of records to return

    Returns:
        List of session interaction records
    """
    container = get_cosmos_container("clinicalSessions")

    query = (
        "SELECT * FROM c WHERE c.sessionId = @sessionId "
        f"ORDER BY c.timestamp DESC OFFSET 0 LIMIT {limit}"
    )

    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sessionId", "value": session_id}],
        enable_cross_partition_query=False
    ))

    return list(reversed(items))


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="clinical-query", methods=["POST"])
async def clinical_query_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main clinical Q&A endpoint.

    Request Body:
    {
        "query": "What are the treatment options for Type 2 Diabetes with CKD stage 3?",
        "patient_id": "optional-fhir-patient-id",
        "session_id": "optional-session-id",
        "include_entities": true
    }

    Response:
    {
        "answer": "Based on clinical guidelines...",
        "entities": {...},
        "citations": [...],
        "session_id": "...",
        "usage": {...}
    }
    """
    try:
        req_body = req.get_json()
        query = req_body.get("query")
        patient_id = req_body.get("patient_id", "")
        session_id = req_body.get("session_id", hashlib.md5(
            datetime.utcnow().isoformat().encode()
        ).hexdigest())
        include_entities = req_body.get("include_entities", True)

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "Query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Processing clinical query: {query[:80]}...")

        # Step 1: Extract medical entities from the query
        entities = {}
        if include_entities:
            entities = extract_medical_entities(query)

        # Step 2: Build clinical context prompt
        system_prompt = """You are a clinical decision support assistant operating within a
HIPAA-compliant healthcare environment. Provide evidence-based clinical information.

INSTRUCTIONS:
1. Provide responses grounded in established clinical guidelines (e.g., AHA, ADA, NCCN)
2. Always cite guideline sources using [Source: guideline_name, Year] format
3. Include relevant ICD-10 and CPT codes where applicable
4. Flag any critical safety concerns or contraindications prominently
5. State limitations clearly - you support but do not replace clinical judgment
6. Never provide a definitive diagnosis - frame as clinical considerations

IMPORTANT: This system is for clinical decision SUPPORT only. All output must be
reviewed by a licensed healthcare provider before clinical action."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Step 3: Generate clinical response
        client = get_openai_client()
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=messages,
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMPERATURE
        )

        answer = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        # Step 4: Save session for audit trail
        save_clinical_session(
            session_id=session_id,
            patient_id=patient_id,
            query=query,
            response_text=answer,
            entities=entities
        )

        response_data = {
            "answer": answer,
            "entities": entities,
            "citations": [],
            "session_id": session_id,
            "usage": usage,
            "disclaimer": "Clinical decision support only. Review by licensed provider required."
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing clinical query: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="drug-check", methods=["POST"])
async def drug_check_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Drug interaction check endpoint.

    Request Body:
    {
        "medications": ["metformin", "lisinopril", "warfarin"],
        "patient_id": "optional-fhir-patient-id"
    }

    Response:
    {
        "interactions": [...],
        "risk_level": "moderate",
        "summary": "...",
        "checked_at": "..."
    }
    """
    try:
        req_body = req.get_json()
        medications = req_body.get("medications", [])
        patient_id = req_body.get("patient_id", "")

        if not medications:
            return func.HttpResponse(
                json.dumps({"error": "Medications list is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Drug interaction check for {len(medications)} medications")

        result = check_drug_interactions(medications)
        result["checked_at"] = datetime.utcnow().isoformat()
        result["medications_checked"] = medications

        # Audit log for drug interaction checks
        if patient_id:
            save_clinical_session(
                session_id=hashlib.md5(
                    f"drugcheck-{datetime.utcnow().isoformat()}".encode()
                ).hexdigest(),
                patient_id=patient_id,
                query=f"Drug interaction check: {', '.join(medications)}",
                response_text=result.get("summary", ""),
                interaction_check=result
            )

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in drug interaction check: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="patient-summary", methods=["POST"])
async def patient_summary_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Patient summary generation endpoint.

    Request Body:
    {
        "patient_id": "fhir-patient-resource-id"
    }

    Response:
    {
        "patient_id": "...",
        "patient_demographics": {...},
        "active_conditions": [...],
        "current_medications": [...],
        "clinical_narrative": "...",
        "generated_at": "..."
    }
    """
    try:
        req_body = req.get_json()
        patient_id = req_body.get("patient_id")

        if not patient_id:
            return func.HttpResponse(
                json.dumps({"error": "patient_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating patient summary for {patient_id}")

        # Step 1: Fetch FHIR data
        fhir_data = get_fhir_patient_data(patient_id)

        if not fhir_data.get("patient"):
            return func.HttpResponse(
                json.dumps({"error": f"Patient {patient_id} not found in FHIR"}),
                status_code=404,
                mimetype="application/json"
            )

        # Step 2: Generate structured summary
        summary = generate_patient_summary(patient_id, fhir_data)

        # Step 3: Audit log
        save_clinical_session(
            session_id=hashlib.md5(
                f"summary-{patient_id}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest(),
            patient_id=patient_id,
            query=f"Patient summary generation for {patient_id}",
            response_text=summary.get("clinical_narrative", "")
        )

        return func.HttpResponse(
            json.dumps(summary, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating patient summary: {e}", exc_info=True)
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
            "service": "healthcare-clinical-copilot",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "compliance": ["HIPAA", "HITECH"]
        }),
        mimetype="application/json"
    )


@app.route(route="sessions/{session_id}/history", methods=["GET"])
async def session_history_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Get clinical session history for audit and review."""
    try:
        session_id = req.route_params.get("session_id")
        limit = int(req.params.get("limit", 20))

        history = get_session_history(session_id, limit=limit)

        return func.HttpResponse(
            json.dumps({"session_id": session_id, "history": history}, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error fetching session history: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
