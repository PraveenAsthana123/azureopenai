"""
Compliance Audit Automation - Azure Functions
==============================================
Evidence collection, control testing, audit trail analysis,
and GenAI-powered audit report generation for enterprise compliance.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.policyinsights import PolicyInsightsClient

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
    LOG_ANALYTICS_WORKSPACE_ID = os.getenv("LOG_ANALYTICS_WORKSPACE_ID")
    SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")

    # Model configurations
    GPT_MODEL = "gpt-4o"

    # Compliance frameworks supported
    SUPPORTED_FRAMEWORKS = ["SOC2", "ISO27001", "HIPAA", "PCI-DSS", "NIST-800-53", "FedRAMP"]

    # Search index for compliance evidence
    SEARCH_INDEX = "compliance-evidence-index"


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None
_resource_client = None
_policy_client = None


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
    database = _cosmos_client.get_database_client("complianceaudit")
    return database.get_container_client(container_name)


def get_resource_client() -> ResourceManagementClient:
    """Get Azure Resource Management client."""
    global _resource_client
    if _resource_client is None:
        _resource_client = ResourceManagementClient(
            credential=get_credential(),
            subscription_id=Config.SUBSCRIPTION_ID
        )
    return _resource_client


def get_policy_client() -> PolicyInsightsClient:
    """Get Azure Policy Insights client."""
    global _policy_client
    if _policy_client is None:
        _policy_client = PolicyInsightsClient(
            credential=get_credential(),
            subscription_id=Config.SUBSCRIPTION_ID
        )
    return _policy_client


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def collect_evidence(control_id: str, scope: str) -> dict:
    """
    Collect compliance evidence from Azure resources using Resource Graph.

    Args:
        control_id: Compliance control identifier (e.g., SOC2-CC6.1)
        scope: Azure scope for evidence collection (subscription or resource group)

    Returns:
        Evidence package with resource data, policy states, and timestamps
    """
    logger.info(f"Collecting evidence for control {control_id} in scope {scope}")

    resource_client = get_resource_client()
    policy_client = get_policy_client()

    # Query resource configuration as evidence
    resources = []
    for resource in resource_client.resources.list_by_resource_group(scope):
        resources.append({
            "id": resource.id,
            "name": resource.name,
            "type": resource.type,
            "location": resource.location,
            "tags": resource.tags or {},
            "provisioning_state": resource.provisioning_state
        })

    # Query policy compliance states
    policy_states = []
    for state in policy_client.policy_states.list_query_results_for_subscription(
        policy_states_resource="latest"
    ):
        policy_states.append({
            "policy_assignment_id": state.policy_assignment_id,
            "compliance_state": state.compliance_state,
            "resource_id": state.resource_id,
            "timestamp": state.timestamp.isoformat() if state.timestamp else None
        })

    evidence_package = {
        "id": hashlib.md5(f"{control_id}-{scope}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "control_id": control_id,
        "scope": scope,
        "collected_at": datetime.utcnow().isoformat(),
        "resources": resources,
        "policy_states": policy_states,
        "resource_count": len(resources),
        "compliant_count": sum(1 for s in policy_states if s["compliance_state"] == "Compliant"),
        "non_compliant_count": sum(1 for s in policy_states if s["compliance_state"] == "NonCompliant")
    }

    # Persist evidence to Cosmos DB
    container = get_cosmos_container("evidence")
    container.create_item(body=evidence_package)

    logger.info(f"Evidence collected: {len(resources)} resources, {len(policy_states)} policy states")
    return evidence_package


def test_control(control_id: str, evidence: dict) -> dict:
    """
    Test control effectiveness using AI analysis.

    Args:
        control_id: Compliance control identifier
        evidence: Collected evidence package

    Returns:
        Control test result with pass/fail status and AI-generated analysis
    """
    logger.info(f"Testing control {control_id}")

    client = get_openai_client()

    system_prompt = """You are a compliance audit expert specializing in cloud infrastructure.
Analyze the provided evidence and determine if the compliance control is effectively implemented.

Provide your analysis in the following JSON structure:
{
    "status": "PASS" or "FAIL" or "PARTIAL",
    "confidence": 0.0 to 1.0,
    "findings": ["list of specific findings"],
    "gaps": ["list of identified gaps"],
    "recommendations": ["list of remediation recommendations"],
    "risk_level": "LOW" or "MEDIUM" or "HIGH" or "CRITICAL"
}
"""

    user_prompt = f"""Control ID: {control_id}
Scope: {evidence.get('scope', 'N/A')}
Total Resources: {evidence.get('resource_count', 0)}
Compliant Resources: {evidence.get('compliant_count', 0)}
Non-Compliant Resources: {evidence.get('non_compliant_count', 0)}

Policy States Summary:
{json.dumps(evidence.get('policy_states', [])[:20], indent=2)}

Resource Configuration Sample:
{json.dumps(evidence.get('resources', [])[:10], indent=2)}

Evaluate whether this control is effectively implemented and identify any gaps."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=2048,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    analysis = json.loads(response.choices[0].message.content)

    test_result = {
        "id": hashlib.md5(f"test-{control_id}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "control_id": control_id,
        "tested_at": datetime.utcnow().isoformat(),
        "evidence_id": evidence.get("id"),
        "status": analysis.get("status", "UNKNOWN"),
        "confidence": analysis.get("confidence", 0.0),
        "findings": analysis.get("findings", []),
        "gaps": analysis.get("gaps", []),
        "recommendations": analysis.get("recommendations", []),
        "risk_level": analysis.get("risk_level", "UNKNOWN"),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

    # Persist test result
    container = get_cosmos_container("testResults")
    container.create_item(body=test_result)

    logger.info(f"Control {control_id} test result: {test_result['status']}")
    return test_result


def analyze_audit_trail(resource_id: str, time_range: dict) -> dict:
    """
    Analyze activity logs for compliance violations.

    Args:
        resource_id: Azure resource ID to audit
        time_range: Dict with 'start' and 'end' ISO timestamps

    Returns:
        Audit trail analysis with violations and risk assessment
    """
    logger.info(f"Analyzing audit trail for resource {resource_id}")

    client = get_openai_client()

    # Query compliance evidence from search index
    search_client = get_search_client()
    results = search_client.search(
        search_text=f"resource:{resource_id}",
        filter=f"timestamp ge {time_range.get('start', '')} and timestamp le {time_range.get('end', '')}",
        top=50,
        select=["id", "operation", "caller", "timestamp", "status", "resource_id", "category"]
    )

    activity_entries = []
    for result in results:
        activity_entries.append({
            "operation": result.get("operation", "Unknown"),
            "caller": result.get("caller", "Unknown"),
            "timestamp": result.get("timestamp", ""),
            "status": result.get("status", "Unknown"),
            "category": result.get("category", "Unknown")
        })

    # Use GenAI to analyze the audit trail
    system_prompt = """You are a security auditor analyzing Azure activity logs for compliance violations.
Identify unauthorized access, suspicious operations, policy violations, and anomalous patterns.

Return your analysis as JSON:
{
    "violations": [{"type": "...", "severity": "...", "description": "...", "timestamp": "..."}],
    "anomalies": [{"pattern": "...", "risk_level": "...", "details": "..."}],
    "summary": "...",
    "risk_score": 0 to 100,
    "recommendations": ["..."]
}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Resource: {resource_id}\nTime Range: {json.dumps(time_range)}\n\nActivity Log Entries:\n{json.dumps(activity_entries, indent=2)}"}
        ],
        max_tokens=2048,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    analysis = json.loads(response.choices[0].message.content)

    audit_result = {
        "id": hashlib.md5(f"audit-{resource_id}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "resource_id": resource_id,
        "time_range": time_range,
        "analyzed_at": datetime.utcnow().isoformat(),
        "total_entries": len(activity_entries),
        "violations": analysis.get("violations", []),
        "anomalies": analysis.get("anomalies", []),
        "summary": analysis.get("summary", ""),
        "risk_score": analysis.get("risk_score", 0),
        "recommendations": analysis.get("recommendations", [])
    }

    # Persist audit result
    container = get_cosmos_container("auditTrails")
    container.create_item(body=audit_result)

    logger.info(f"Audit trail analysis complete: {len(audit_result['violations'])} violations found")
    return audit_result


def generate_audit_report(audit_data: dict) -> dict:
    """
    Generate comprehensive audit report using GenAI.

    Args:
        audit_data: Dict containing audit_name, framework, controls tested,
                    evidence collected, and test results

    Returns:
        Generated audit report with executive summary, findings, and recommendations
    """
    logger.info(f"Generating audit report for: {audit_data.get('audit_name', 'unnamed')}")

    client = get_openai_client()

    system_prompt = """You are a senior compliance auditor generating a formal audit report.
Create a comprehensive, professional audit report based on the provided audit data.

Structure the report as JSON with these sections:
{
    "executive_summary": "...",
    "scope": "...",
    "methodology": "...",
    "findings": [
        {"id": "F-001", "title": "...", "severity": "...", "description": "...", "control_id": "...", "status": "...", "remediation": "..."}
    ],
    "overall_compliance_rating": "COMPLIANT" or "PARTIALLY_COMPLIANT" or "NON_COMPLIANT",
    "compliance_score": 0 to 100,
    "risk_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "recommendations": [{"priority": "...", "description": "...", "timeline": "..."}],
    "conclusion": "..."
}
"""

    user_prompt = f"""Audit Name: {audit_data.get('audit_name', 'Compliance Audit')}
Framework: {audit_data.get('framework', 'SOC2')}
Audit Period: {audit_data.get('period_start', 'N/A')} to {audit_data.get('period_end', 'N/A')}
Organization: {audit_data.get('organization', 'N/A')}

Controls Tested: {json.dumps(audit_data.get('controls_tested', []), indent=2)}

Evidence Summary: {json.dumps(audit_data.get('evidence_summary', {}), indent=2)}

Test Results: {json.dumps(audit_data.get('test_results', []), indent=2)}

Generate a complete audit report."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=4096,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    report_content = json.loads(response.choices[0].message.content)

    report = {
        "id": hashlib.md5(f"report-{audit_data.get('audit_name', '')}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "audit_name": audit_data.get("audit_name", "Compliance Audit"),
        "framework": audit_data.get("framework", "SOC2"),
        "generated_at": datetime.utcnow().isoformat(),
        "report": report_content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

    # Persist report
    container = get_cosmos_container("auditReports")
    container.create_item(body=report)

    logger.info(f"Audit report generated: {report['id']}")
    return report


def assess_compliance_posture(framework: str) -> dict:
    """
    Overall compliance posture assessment for a given framework.

    Args:
        framework: Compliance framework (SOC2, ISO27001, HIPAA, PCI-DSS, etc.)

    Returns:
        Posture assessment with control status breakdown and risk profile
    """
    logger.info(f"Assessing compliance posture for framework: {framework}")

    if framework not in Config.SUPPORTED_FRAMEWORKS:
        raise ValueError(f"Unsupported framework: {framework}. Supported: {Config.SUPPORTED_FRAMEWORKS}")

    client = get_openai_client()
    policy_client = get_policy_client()

    # Gather policy compliance summary
    policy_summary = {"compliant": 0, "non_compliant": 0, "exempt": 0}
    for state in policy_client.policy_states.list_query_results_for_subscription(
        policy_states_resource="latest"
    ):
        if state.compliance_state == "Compliant":
            policy_summary["compliant"] += 1
        elif state.compliance_state == "NonCompliant":
            policy_summary["non_compliant"] += 1
        else:
            policy_summary["exempt"] += 1

    # Query recent test results from Cosmos DB
    container = get_cosmos_container("testResults")
    recent_tests = list(container.query_items(
        query="SELECT * FROM c WHERE c.control_id LIKE @prefix ORDER BY c.tested_at DESC OFFSET 0 LIMIT 50",
        parameters=[{"name": "@prefix", "value": f"{framework}%"}],
        enable_cross_partition_query=True
    ))

    # Use GenAI for posture assessment
    system_prompt = f"""You are a compliance posture analyst for the {framework} framework.
Assess the overall compliance posture based on policy states and control test results.

Return JSON:
{{
    "framework": "{framework}",
    "overall_status": "STRONG" or "ADEQUATE" or "NEEDS_IMPROVEMENT" or "CRITICAL",
    "compliance_percentage": 0 to 100,
    "control_summary": {{"passed": 0, "failed": 0, "partial": 0, "untested": 0}},
    "top_risks": [{{"risk": "...", "impact": "...", "likelihood": "...", "mitigation": "..."}}],
    "maturity_level": 1 to 5,
    "key_strengths": ["..."],
    "improvement_areas": ["..."],
    "next_steps": ["..."]
}}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Policy Compliance Summary:\n{json.dumps(policy_summary, indent=2)}\n\nRecent Control Test Results:\n{json.dumps(recent_tests[:20], indent=2, default=str)}"}
        ],
        max_tokens=2048,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    posture = json.loads(response.choices[0].message.content)

    assessment = {
        "id": hashlib.md5(f"posture-{framework}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "framework": framework,
        "assessed_at": datetime.utcnow().isoformat(),
        "policy_summary": policy_summary,
        "posture": posture,
        "controls_evaluated": len(recent_tests)
    }

    # Persist assessment
    container = get_cosmos_container("postureAssessments")
    container.create_item(body=assessment)

    logger.info(f"Posture assessment for {framework}: {posture.get('overall_status', 'UNKNOWN')}")
    return assessment


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="collect-evidence", methods=["POST"])
async def collect_evidence_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Evidence collection endpoint.

    Request Body:
    {
        "control_id": "SOC2-CC6.1",
        "scope": "my-resource-group"
    }
    """
    try:
        req_body = req.get_json()
        control_id = req_body.get("control_id")
        scope = req_body.get("scope")

        if not control_id or not scope:
            return func.HttpResponse(
                json.dumps({"error": "control_id and scope are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Evidence collection request: control={control_id}, scope={scope}")

        result = collect_evidence(control_id, scope)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error collecting evidence: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="test-control", methods=["POST"])
async def test_control_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Control testing endpoint.

    Request Body:
    {
        "control_id": "SOC2-CC6.1",
        "evidence_id": "optional-evidence-id",
        "scope": "my-resource-group"
    }
    """
    try:
        req_body = req.get_json()
        control_id = req_body.get("control_id")
        evidence_id = req_body.get("evidence_id")
        scope = req_body.get("scope")

        if not control_id:
            return func.HttpResponse(
                json.dumps({"error": "control_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Retrieve existing evidence or collect new
        if evidence_id:
            container = get_cosmos_container("evidence")
            evidence = container.read_item(item=evidence_id, partition_key=control_id)
        elif scope:
            evidence = collect_evidence(control_id, scope)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Either evidence_id or scope is required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = test_control(control_id, evidence)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error testing control: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="audit-trail", methods=["POST"])
async def audit_trail_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Audit trail analysis endpoint.

    Request Body:
    {
        "resource_id": "/subscriptions/.../resourceGroups/.../providers/...",
        "time_range": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z"
        }
    }
    """
    try:
        req_body = req.get_json()
        resource_id = req_body.get("resource_id")
        time_range = req_body.get("time_range", {})

        if not resource_id:
            return func.HttpResponse(
                json.dumps({"error": "resource_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Default time range to last 30 days
        if not time_range.get("start"):
            time_range["start"] = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
        if not time_range.get("end"):
            time_range["end"] = datetime.utcnow().isoformat() + "Z"

        result = analyze_audit_trail(resource_id, time_range)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error analyzing audit trail: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="generate-report", methods=["POST"])
async def generate_report_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Audit report generation endpoint.

    Request Body:
    {
        "audit_name": "Q4 2024 SOC2 Audit",
        "framework": "SOC2",
        "organization": "Contoso Ltd",
        "period_start": "2024-10-01",
        "period_end": "2024-12-31",
        "controls_tested": ["SOC2-CC6.1", "SOC2-CC6.2"],
        "evidence_summary": {...},
        "test_results": [...]
    }
    """
    try:
        req_body = req.get_json()
        audit_name = req_body.get("audit_name")

        if not audit_name:
            return func.HttpResponse(
                json.dumps({"error": "audit_name is required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = generate_audit_report(req_body)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating audit report: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="compliance-posture", methods=["POST"])
async def compliance_posture_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Compliance posture assessment endpoint.

    Request Body:
    {
        "framework": "SOC2"
    }
    """
    try:
        req_body = req.get_json()
        framework = req_body.get("framework")

        if not framework:
            return func.HttpResponse(
                json.dumps({"error": "framework is required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = assess_compliance_posture(framework)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except ValueError as ve:
        return func.HttpResponse(
            json.dumps({"error": str(ve)}),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error assessing compliance posture: {e}", exc_info=True)
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
            "service": "compliance-audit-automation",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "supported_frameworks": Config.SUPPORTED_FRAMEWORKS
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Timer Trigger for Scheduled Compliance Scans
# ==============================================================================

@app.function_name(name="ScheduledComplianceScan")
@app.timer_trigger(schedule="0 0 6 * * 1", arg_name="timer", run_on_startup=False)
async def scheduled_compliance_scan(timer: func.TimerRequest):
    """
    Scheduled weekly compliance scan.
    Runs every Monday at 06:00 UTC to assess posture across all frameworks.
    """
    try:
        logger.info("Starting scheduled compliance scan")

        scan_results = []
        for framework in Config.SUPPORTED_FRAMEWORKS:
            try:
                logger.info(f"Scanning framework: {framework}")
                assessment = assess_compliance_posture(framework)
                scan_results.append({
                    "framework": framework,
                    "status": assessment.get("posture", {}).get("overall_status", "UNKNOWN"),
                    "compliance_percentage": assessment.get("posture", {}).get("compliance_percentage", 0)
                })
            except Exception as fw_err:
                logger.error(f"Error scanning framework {framework}: {fw_err}")
                scan_results.append({
                    "framework": framework,
                    "status": "ERROR",
                    "error": str(fw_err)
                })

        # Persist scan summary
        scan_summary = {
            "id": hashlib.md5(f"scan-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "scan_type": "scheduled_weekly",
            "executed_at": datetime.utcnow().isoformat(),
            "results": scan_results,
            "frameworks_scanned": len(scan_results),
            "is_past_due": timer.past_due
        }

        container = get_cosmos_container("scanHistory")
        container.create_item(body=scan_summary)

        logger.info(f"Scheduled compliance scan complete: {len(scan_results)} frameworks assessed")

    except Exception as e:
        logger.error(f"Error in scheduled compliance scan: {e}", exc_info=True)
        raise
