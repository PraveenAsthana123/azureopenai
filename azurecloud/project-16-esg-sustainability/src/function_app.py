"""
ESG & Sustainability Reporter - Azure Functions
================================================
ESG data extraction, carbon footprint analytics, CSRD/TCFD compliance
checking, and GenAI narrative generation for sustainability reporting.
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
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

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
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    SEARCH_INDEX = "esg-documents-index"

    # ESG parameters
    SUPPORTED_FRAMEWORKS = ["CSRD", "TCFD", "GRI", "SASB", "IFRS_S1", "IFRS_S2"]
    EMISSION_SCOPES = ["scope_1", "scope_2", "scope_3"]
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
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
    database = _cosmos_client.get_database_client("esg-sustainability")
    return database.get_container_client(container_name)


# ==============================================================================
# Core ESG Domain Functions
# ==============================================================================

def extract_esg_metrics(document_text: str, framework: str) -> dict:
    """
    Extract ESG metrics from reports using GenAI against a specified framework.

    Args:
        document_text: Raw text content of the ESG report or disclosure
        framework: Reporting framework (CSRD, TCFD, GRI, SASB, IFRS_S1, IFRS_S2)

    Returns:
        Dictionary of extracted metrics organized by E/S/G pillars
    """
    if framework not in Config.SUPPORTED_FRAMEWORKS:
        raise ValueError(f"Unsupported framework: {framework}. Use one of {Config.SUPPORTED_FRAMEWORKS}")

    client = get_openai_client()

    system_prompt = f"""You are an expert ESG analyst specializing in the {framework} framework.
Extract structured ESG metrics from the provided document text.

Return a JSON object with the following structure:
{{
  "framework": "{framework}",
  "environmental": {{
    "ghg_emissions_tco2e": null,
    "energy_consumption_mwh": null,
    "renewable_energy_pct": null,
    "water_withdrawal_m3": null,
    "waste_generated_tonnes": null,
    "biodiversity_impact": null
  }},
  "social": {{
    "total_employees": null,
    "gender_diversity_pct": null,
    "lost_time_injury_rate": null,
    "employee_turnover_pct": null,
    "training_hours_per_employee": null,
    "community_investment_usd": null
  }},
  "governance": {{
    "board_independence_pct": null,
    "board_gender_diversity_pct": null,
    "ethics_violations": null,
    "data_breaches": null,
    "anti_corruption_training_pct": null,
    "executive_esg_linked_pay": null
  }},
  "data_quality_score": 0.0,
  "extraction_notes": []
}}

Only populate fields where data is explicitly stated in the document.
Set data_quality_score between 0.0 and 1.0 based on completeness and clarity."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract ESG metrics from this document:\n\n{document_text[:8000]}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    metrics = json.loads(response.choices[0].message.content)
    metrics["extracted_at"] = datetime.utcnow().isoformat()
    metrics["model_used"] = Config.GPT_MODEL

    logger.info(f"Extracted ESG metrics using {framework} framework, quality score: {metrics.get('data_quality_score')}")
    return metrics


def calculate_carbon_footprint(activity_data: dict) -> dict:
    """
    Calculate Scope 1, 2, and 3 greenhouse gas emissions from activity data.

    Args:
        activity_data: Dictionary containing activity data by scope:
            - scope_1: Direct emissions (fuel combustion, fleet, refrigerants)
            - scope_2: Indirect energy emissions (electricity, heat, steam)
            - scope_3: Value chain emissions (travel, procurement, logistics)

    Returns:
        Detailed carbon footprint breakdown in tCO2e
    """
    # Standard emission factors (tCO2e per unit)
    emission_factors = {
        "natural_gas_m3": 0.00202,
        "diesel_litre": 0.002676,
        "petrol_litre": 0.002315,
        "electricity_kwh": 0.000233,
        "heat_kwh": 0.000170,
        "air_travel_km": 0.000255,
        "rail_travel_km": 0.000041,
        "road_freight_tonne_km": 0.000107,
        "paper_kg": 0.000919,
        "water_m3": 0.000344,
    }

    results = {
        "calculation_date": datetime.utcnow().isoformat(),
        "methodology": "GHG Protocol Corporate Standard",
        "scope_1": {"total_tco2e": 0.0, "categories": {}},
        "scope_2": {"total_tco2e": 0.0, "categories": {}, "method": "location-based"},
        "scope_3": {"total_tco2e": 0.0, "categories": {}},
        "total_tco2e": 0.0,
    }

    # Calculate Scope 1 - Direct emissions
    scope_1_data = activity_data.get("scope_1", {})
    for activity, quantity in scope_1_data.items():
        factor = emission_factors.get(activity, 0)
        emissions = quantity * factor
        results["scope_1"]["categories"][activity] = {
            "quantity": quantity,
            "factor": factor,
            "emissions_tco2e": round(emissions, 4)
        }
        results["scope_1"]["total_tco2e"] += emissions

    # Calculate Scope 2 - Indirect energy emissions
    scope_2_data = activity_data.get("scope_2", {})
    for activity, quantity in scope_2_data.items():
        factor = emission_factors.get(activity, 0)
        emissions = quantity * factor
        results["scope_2"]["categories"][activity] = {
            "quantity": quantity,
            "factor": factor,
            "emissions_tco2e": round(emissions, 4)
        }
        results["scope_2"]["total_tco2e"] += emissions

    # Calculate Scope 3 - Value chain emissions
    scope_3_data = activity_data.get("scope_3", {})
    for activity, quantity in scope_3_data.items():
        factor = emission_factors.get(activity, 0)
        emissions = quantity * factor
        results["scope_3"]["categories"][activity] = {
            "quantity": quantity,
            "factor": factor,
            "emissions_tco2e": round(emissions, 4)
        }
        results["scope_3"]["total_tco2e"] += emissions

    # Round scope totals
    results["scope_1"]["total_tco2e"] = round(results["scope_1"]["total_tco2e"], 4)
    results["scope_2"]["total_tco2e"] = round(results["scope_2"]["total_tco2e"], 4)
    results["scope_3"]["total_tco2e"] = round(results["scope_3"]["total_tco2e"], 4)
    results["total_tco2e"] = round(
        results["scope_1"]["total_tco2e"]
        + results["scope_2"]["total_tco2e"]
        + results["scope_3"]["total_tco2e"],
        4
    )

    logger.info(f"Carbon footprint calculated: {results['total_tco2e']} tCO2e")
    return results


def check_regulatory_compliance(metrics: dict, framework: str) -> dict:
    """
    Check ESG metrics against CSRD/TCFD regulatory disclosure requirements.

    Args:
        metrics: Extracted ESG metrics dictionary
        framework: Target regulatory framework (CSRD or TCFD)

    Returns:
        Compliance assessment with gaps and recommendations
    """
    client = get_openai_client()

    framework_requirements = {
        "CSRD": [
            "Climate change mitigation and adaptation disclosures",
            "GHG emissions Scope 1, 2, and 3",
            "Energy consumption and mix",
            "Biodiversity and ecosystems impact",
            "Water and marine resources",
            "Circular economy and waste",
            "Workforce diversity and inclusion metrics",
            "Working conditions and social dialogue",
            "Business conduct and anti-corruption",
            "Due diligence process description",
            "Double materiality assessment",
        ],
        "TCFD": [
            "Governance: Board oversight of climate risks",
            "Governance: Management role in climate assessment",
            "Strategy: Climate risks and opportunities identified",
            "Strategy: Impact on business and financial planning",
            "Strategy: Scenario analysis (2C or below)",
            "Risk Management: Process for identifying climate risks",
            "Risk Management: Integration with overall risk management",
            "Metrics: GHG emissions Scope 1 and 2",
            "Metrics: GHG emissions Scope 3 (if material)",
            "Metrics: Climate-related targets and performance",
        ],
    }

    requirements = framework_requirements.get(framework, [])
    if not requirements:
        return {"error": f"Compliance check not supported for framework: {framework}"}

    system_prompt = f"""You are a regulatory compliance expert for {framework} reporting.
Evaluate the provided ESG metrics against the {framework} disclosure requirements.

For each requirement, assess:
- status: "compliant", "partial", or "gap"
- evidence: What data supports compliance
- recommendation: What action is needed for full compliance

Return a JSON object with:
{{
  "framework": "{framework}",
  "overall_compliance_pct": 0.0,
  "compliant_count": 0,
  "partial_count": 0,
  "gap_count": 0,
  "requirements": [
    {{
      "requirement": "...",
      "status": "compliant|partial|gap",
      "evidence": "...",
      "recommendation": "..."
    }}
  ],
  "priority_actions": []
}}"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Requirements to check:\n{json.dumps(requirements, indent=2)}\n\n"
                    f"Available metrics:\n{json.dumps(metrics, indent=2)}"
                ),
            },
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    compliance_result = json.loads(response.choices[0].message.content)
    compliance_result["assessed_at"] = datetime.utcnow().isoformat()

    logger.info(
        f"{framework} compliance check: {compliance_result.get('overall_compliance_pct', 0)}% compliant"
    )
    return compliance_result


def generate_esg_narrative(metrics: dict, period: str) -> dict:
    """
    Generate a GenAI narrative section for an ESG report.

    Args:
        metrics: Extracted ESG metrics for the reporting period
        period: Reporting period label (e.g. "FY2025", "H1 2025")

    Returns:
        Generated narrative text with metadata
    """
    client = get_openai_client()

    system_prompt = f"""You are a sustainability report writer producing investor-grade ESG narratives.
Write a professional narrative section for the {period} sustainability report based on the metrics provided.

Structure the narrative with:
1. Executive Summary (2-3 sentences)
2. Environmental Performance highlights
3. Social Impact highlights
4. Governance highlights
5. Forward-Looking Statements and Targets

Use precise language, cite specific metrics, and maintain a balanced, factual tone.
Avoid greenwashing or unsubstantiated claims."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Metrics for {period}:\n{json.dumps(metrics, indent=2)}"},
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
    )

    narrative = response.choices[0].message.content
    return {
        "period": period,
        "narrative": narrative,
        "generated_at": datetime.utcnow().isoformat(),
        "model": Config.GPT_MODEL,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }


def generate_sustainability_report(company_data: dict) -> dict:
    """
    Generate a full sustainability report combining metrics, compliance, and narrative.

    Args:
        company_data: Dictionary containing company info, activity data, and document text

    Returns:
        Complete sustainability report with all sections
    """
    company_name = company_data.get("company_name", "Unknown Company")
    period = company_data.get("reporting_period", "FY2025")
    framework = company_data.get("framework", "CSRD")
    document_text = company_data.get("document_text", "")
    activity_data = company_data.get("activity_data", {})

    logger.info(f"Generating sustainability report for {company_name}, period {period}")

    report = {
        "report_id": hashlib.md5(
            f"{company_name}-{period}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest(),
        "company_name": company_name,
        "reporting_period": period,
        "framework": framework,
        "generated_at": datetime.utcnow().isoformat(),
        "sections": {},
    }

    # Section 1: Extract ESG metrics from provided documents
    if document_text:
        metrics = extract_esg_metrics(document_text, framework)
        report["sections"]["metrics"] = metrics
    else:
        metrics = {}
        report["sections"]["metrics"] = {"note": "No document text provided for extraction"}

    # Section 2: Calculate carbon footprint
    if activity_data:
        carbon = calculate_carbon_footprint(activity_data)
        report["sections"]["carbon_footprint"] = carbon
    else:
        report["sections"]["carbon_footprint"] = {"note": "No activity data provided"}

    # Section 3: Regulatory compliance assessment
    if metrics and framework in ("CSRD", "TCFD"):
        compliance = check_regulatory_compliance(metrics, framework)
        report["sections"]["compliance"] = compliance
    else:
        report["sections"]["compliance"] = {"note": f"Compliance check requires CSRD or TCFD framework"}

    # Section 4: Generate narrative
    combined_metrics = {**metrics}
    if activity_data:
        combined_metrics["carbon_footprint_tco2e"] = report["sections"].get(
            "carbon_footprint", {}
        ).get("total_tco2e", "N/A")
    narrative = generate_esg_narrative(combined_metrics, period)
    report["sections"]["narrative"] = narrative

    # Persist report to Cosmos DB
    try:
        container = get_cosmos_container("esg-reports")
        report["id"] = report["report_id"]
        report["partitionKey"] = company_name
        container.create_item(body=report)
        logger.info(f"Report {report['report_id']} saved to Cosmos DB")
    except Exception as e:
        logger.warning(f"Failed to persist report to Cosmos DB: {e}")

    return report


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="extract-metrics", methods=["POST"])
async def extract_metrics_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    ESG metric extraction endpoint.

    Request Body:
    {
        "document_text": "Full text of ESG report...",
        "framework": "CSRD"
    }

    Response:
    {
        "metrics": { ... extracted ESG metrics ... }
    }
    """
    try:
        req_body = req.get_json()
        document_text = req_body.get("document_text")
        framework = req_body.get("framework", "CSRD")

        if not document_text:
            return func.HttpResponse(
                json.dumps({"error": "document_text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Extracting ESG metrics using {framework} framework")
        metrics = extract_esg_metrics(document_text, framework)

        return func.HttpResponse(
            json.dumps({"metrics": metrics}),
            mimetype="application/json"
        )

    except ValueError as ve:
        return func.HttpResponse(
            json.dumps({"error": str(ve)}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error extracting metrics: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="carbon-footprint", methods=["POST"])
async def carbon_footprint_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Carbon footprint calculation endpoint.

    Request Body:
    {
        "activity_data": {
            "scope_1": { "natural_gas_m3": 50000, "diesel_litre": 12000 },
            "scope_2": { "electricity_kwh": 2000000 },
            "scope_3": { "air_travel_km": 500000, "road_freight_tonne_km": 1000000 }
        }
    }

    Response:
    {
        "carbon_footprint": { ... emissions breakdown ... }
    }
    """
    try:
        req_body = req.get_json()
        activity_data = req_body.get("activity_data")

        if not activity_data:
            return func.HttpResponse(
                json.dumps({"error": "activity_data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Calculating carbon footprint")
        footprint = calculate_carbon_footprint(activity_data)

        return func.HttpResponse(
            json.dumps({"carbon_footprint": footprint}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error calculating carbon footprint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="compliance-check", methods=["POST"])
async def compliance_check_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Regulatory compliance check endpoint.

    Request Body:
    {
        "metrics": { ... ESG metrics ... },
        "framework": "CSRD"
    }

    Response:
    {
        "compliance": { ... compliance assessment ... }
    }
    """
    try:
        req_body = req.get_json()
        metrics = req_body.get("metrics")
        framework = req_body.get("framework", "CSRD")

        if not metrics:
            return func.HttpResponse(
                json.dumps({"error": "metrics is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Running {framework} compliance check")
        compliance = check_regulatory_compliance(metrics, framework)

        return func.HttpResponse(
            json.dumps({"compliance": compliance}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error checking compliance: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="generate-report", methods=["POST"])
async def generate_report_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    ESG report generation endpoint.

    Request Body:
    {
        "company_name": "Contoso Ltd",
        "reporting_period": "FY2025",
        "framework": "CSRD",
        "document_text": "Optional raw report text...",
        "activity_data": { ... optional activity data ... }
    }

    Response:
    {
        "report": { ... full sustainability report ... }
    }
    """
    try:
        req_body = req.get_json()
        company_name = req_body.get("company_name")

        if not company_name:
            return func.HttpResponse(
                json.dumps({"error": "company_name is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating sustainability report for {company_name}")
        report = generate_sustainability_report(req_body)

        return func.HttpResponse(
            json.dumps({"report": report}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
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
            "service": "esg-sustainability-reporter",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "supported_frameworks": Config.SUPPORTED_FRAMEWORKS
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger for ESG Document Uploads
# ==============================================================================

@app.function_name(name="ESGDocumentUploadTrigger")
@app.event_grid_trigger(arg_name="event")
async def esg_document_upload_trigger(event: func.EventGridEvent):
    """
    Triggered when a new ESG document is uploaded to blob storage.
    Initiates metric extraction and compliance assessment pipeline.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1]

        logger.info(f"New ESG document uploaded: {blob_name}")

        # Log processing event to Cosmos DB
        container = get_cosmos_container("esg-processing-events")
        processing_event = {
            "id": hashlib.md5(f"{blob_name}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "partitionKey": "document-upload",
            "blob_name": blob_name,
            "blob_url": blob_url,
            "status": "received",
            "received_at": datetime.utcnow().isoformat(),
            "pipeline_steps": [
                "document_extraction",
                "metric_extraction",
                "compliance_check",
                "narrative_generation",
                "report_assembly",
            ],
        }
        container.create_item(body=processing_event)

        logger.info(f"ESG document processing pipeline initiated for: {blob_name}")

    except Exception as e:
        logger.error(f"Error processing ESG document event: {e}", exc_info=True)
        raise
