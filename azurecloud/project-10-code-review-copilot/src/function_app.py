"""
Code Review & DevOps Copilot - Azure Functions
===============================================
AI-powered code review, PR summarization, incident root cause analysis,
and deployment risk assessment for enterprise DevOps workflows.
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
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    DEVOPS_ORG_URL = os.getenv("DEVOPS_ORG_URL")
    GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")

    # Model configurations
    GPT_MODEL = "gpt-4o"

    # Review parameters
    MAX_DIFF_LINES = 5000
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3
    RISK_THRESHOLD_HIGH = 0.7
    RISK_THRESHOLD_MEDIUM = 0.4


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_cosmos_client = None
_keyvault_client = None


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
    database = _cosmos_client.get_database_client("codereviewcopilot")
    return database.get_container_client(container_name)


def get_keyvault_client() -> SecretClient:
    """Get Azure Key Vault client."""
    global _keyvault_client
    if _keyvault_client is None:
        _keyvault_client = SecretClient(
            vault_url=Config.KEY_VAULT_URL,
            credential=get_credential()
        )
    return _keyvault_client


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def review_code_changes(diff_content: str, language: str = "auto") -> dict:
    """
    Perform AI-powered code review analyzing quality, bugs, and security issues.

    Args:
        diff_content: The unified diff content to review
        language: Programming language hint (or 'auto' for detection)

    Returns:
        Structured review result with findings and severity ratings
    """
    client = get_openai_client()

    # Truncate oversized diffs
    lines = diff_content.split("\n")
    if len(lines) > Config.MAX_DIFF_LINES:
        diff_content = "\n".join(lines[:Config.MAX_DIFF_LINES])
        diff_content += f"\n\n... [truncated: {len(lines) - Config.MAX_DIFF_LINES} lines omitted]"

    system_prompt = """You are an expert code reviewer specializing in enterprise software quality.
Analyze the provided code diff and return a JSON response with:

1. "summary": Brief overall assessment
2. "findings": Array of issues found, each with:
   - "type": one of "bug", "security", "performance", "style", "maintainability"
   - "severity": one of "critical", "high", "medium", "low", "info"
   - "file": affected file path
   - "line": approximate line number
   - "description": clear explanation of the issue
   - "suggestion": recommended fix
3. "score": Overall quality score 1-10
4. "language_detected": detected programming language
5. "metrics": {"additions": N, "deletions": N, "files_changed": N}

Focus on: security vulnerabilities, logic errors, null pointer risks, resource leaks,
race conditions, SQL injection, XSS, hardcoded secrets, and code complexity."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Language hint: {language}\n\nCode Diff:\n```\n{diff_content}\n```"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    review_result = json.loads(response.choices[0].message.content)
    review_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return review_result


def summarize_pull_request(pr_data: dict) -> dict:
    """
    Generate a comprehensive PR summary with key changes, risks, and recommendations.

    Args:
        pr_data: Pull request metadata including title, description, diff, files changed

    Returns:
        Structured PR summary with risk assessment and review recommendations
    """
    client = get_openai_client()

    system_prompt = """You are a senior engineering lead reviewing pull requests.
Generate a structured JSON summary with:

1. "title_summary": One-line summary of the PR purpose
2. "change_overview": 2-3 sentence description of what changed and why
3. "key_changes": Array of important changes grouped by category
4. "risk_areas": Array of potential risks with severity
5. "test_coverage_assessment": Assessment of testing adequacy
6. "review_recommendations": Specific areas reviewers should focus on
7. "breaking_changes": Any breaking changes identified (array)
8. "dependencies_affected": List of affected dependencies or services
9. "estimated_review_time_minutes": Estimated time to review"""

    pr_context = (
        f"PR Title: {pr_data.get('title', 'N/A')}\n"
        f"Description: {pr_data.get('description', 'N/A')}\n"
        f"Author: {pr_data.get('author', 'N/A')}\n"
        f"Target Branch: {pr_data.get('target_branch', 'main')}\n"
        f"Files Changed: {pr_data.get('files_changed', 'N/A')}\n\n"
        f"Diff:\n```\n{pr_data.get('diff', 'No diff provided')}\n```"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pr_context}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    summary = json.loads(response.choices[0].message.content)
    summary["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return summary


def analyze_incident_rca(incident_data: dict, logs: str) -> dict:
    """
    Perform root cause analysis from incident data and application logs.

    Args:
        incident_data: Incident metadata (severity, timeline, affected services)
        logs: Relevant application/infrastructure logs

    Returns:
        Structured RCA report with root cause, timeline, and remediation steps
    """
    client = get_openai_client()

    system_prompt = """You are a Site Reliability Engineer performing root cause analysis.
Analyze the incident data and logs to produce a JSON RCA report with:

1. "incident_summary": Brief description of what happened
2. "root_cause": Most likely root cause with confidence level
3. "contributing_factors": Array of contributing factors
4. "timeline": Array of events in chronological order with timestamps
5. "impact_assessment": {"severity": "...", "affected_users": N, "duration_minutes": N}
6. "remediation_steps": Array of immediate actions taken or needed
7. "prevention_recommendations": Long-term fixes to prevent recurrence
8. "related_changes": Recent deployments or config changes that may be related
9. "action_items": Array of follow-up tasks with owners and deadlines"""

    incident_context = (
        f"Incident ID: {incident_data.get('id', 'N/A')}\n"
        f"Severity: {incident_data.get('severity', 'N/A')}\n"
        f"Title: {incident_data.get('title', 'N/A')}\n"
        f"Start Time: {incident_data.get('start_time', 'N/A')}\n"
        f"End Time: {incident_data.get('end_time', 'Ongoing')}\n"
        f"Affected Services: {json.dumps(incident_data.get('affected_services', []))}\n"
        f"Description: {incident_data.get('description', 'N/A')}\n\n"
        f"Application Logs:\n```\n{logs}\n```"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": incident_context}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    rca_result = json.loads(response.choices[0].message.content)
    rca_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return rca_result


def assess_deployment_risk(deployment_data: dict) -> dict:
    """
    Assess risk level for a planned deployment with scoring and recommendations.

    Args:
        deployment_data: Deployment metadata including changes, environment, timing

    Returns:
        Risk assessment with score, factors, and go/no-go recommendation
    """
    client = get_openai_client()

    system_prompt = """You are a deployment risk analyst for enterprise systems.
Evaluate the planned deployment and return a JSON risk assessment:

1. "risk_score": Float 0.0-1.0 (0=no risk, 1=maximum risk)
2. "risk_level": "low", "medium", "high", or "critical"
3. "go_no_go": "go", "go_with_caution", or "no_go"
4. "risk_factors": Array of identified risks with individual scores
5. "mitigation_strategies": Recommended mitigations for each risk
6. "rollback_plan_assessment": Evaluation of rollback readiness
7. "recommended_deployment_window": Best time to deploy
8. "pre_deployment_checklist": Array of items to verify before deploying
9. "monitoring_recommendations": What to watch post-deployment
10. "confidence": Confidence level of the assessment (0.0-1.0)

Consider: change size, blast radius, time of deployment, recent incident history,
test coverage, rollback capability, and dependency impacts."""

    deploy_context = (
        f"Environment: {deployment_data.get('environment', 'N/A')}\n"
        f"Service: {deployment_data.get('service', 'N/A')}\n"
        f"Change Type: {deployment_data.get('change_type', 'N/A')}\n"
        f"Planned Time: {deployment_data.get('planned_time', 'N/A')}\n"
        f"Changes Summary: {deployment_data.get('changes_summary', 'N/A')}\n"
        f"Files Changed: {deployment_data.get('files_changed', 0)}\n"
        f"Lines Changed: {deployment_data.get('lines_changed', 0)}\n"
        f"Test Results: {json.dumps(deployment_data.get('test_results', {}))}\n"
        f"Dependencies: {json.dumps(deployment_data.get('dependencies', []))}\n"
        f"Rollback Plan: {deployment_data.get('rollback_plan', 'N/A')}\n"
        f"Recent Incidents: {json.dumps(deployment_data.get('recent_incidents', []))}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": deploy_context}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    risk_result = json.loads(response.choices[0].message.content)
    risk_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return risk_result


def generate_review_comments(review_result: dict) -> list[dict]:
    """
    Format review findings into actionable inline comments for PR integration.

    Args:
        review_result: Output from review_code_changes()

    Returns:
        List of formatted comment objects ready to post to a PR
    """
    comments = []

    severity_emoji = {
        "critical": "[CRITICAL]",
        "high": "[HIGH]",
        "medium": "[MEDIUM]",
        "low": "[LOW]",
        "info": "[INFO]"
    }

    for finding in review_result.get("findings", []):
        severity = finding.get("severity", "info")
        prefix = severity_emoji.get(severity, "[INFO]")

        comment_body = (
            f"{prefix} **{finding.get('type', 'general').upper()}**: "
            f"{finding.get('description', 'No description')}\n\n"
        )

        if finding.get("suggestion"):
            comment_body += f"**Suggestion:** {finding['suggestion']}\n"

        comments.append({
            "file": finding.get("file", ""),
            "line": finding.get("line", 1),
            "body": comment_body,
            "severity": severity,
            "type": finding.get("type", "general")
        })

    return comments


# ==============================================================================
# Persistence Helpers
# ==============================================================================

def save_review_record(review_id: str, review_type: str, request_data: dict, result: dict):
    """Save a review record to Cosmos DB for audit and analytics."""
    container = get_cosmos_container("reviews")

    record = {
        "id": review_id,
        "reviewType": review_type,
        "timestamp": datetime.utcnow().isoformat(),
        "request": request_data,
        "result": result,
        "partitionKey": review_type
    }

    container.create_item(body=record)
    logger.info(f"Saved {review_type} review record: {review_id}")


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="review-code", methods=["POST"])
async def review_code_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Code review endpoint - analyzes code diff for quality, bugs, and security.

    Request Body:
    {
        "diff": "unified diff content...",
        "language": "python",
        "repository": "org/repo-name",
        "pr_number": 123
    }

    Response:
    {
        "review_id": "...",
        "summary": "...",
        "findings": [...],
        "score": 8,
        "comments": [...]
    }
    """
    try:
        req_body = req.get_json()
        diff_content = req_body.get("diff")
        language = req_body.get("language", "auto")

        if not diff_content:
            return func.HttpResponse(
                json.dumps({"error": "Field 'diff' is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Reviewing code changes for {req_body.get('repository', 'unknown')}")

        # Perform AI code review
        review_result = review_code_changes(diff_content, language)

        # Generate formatted comments
        comments = generate_review_comments(review_result)
        review_result["comments"] = comments

        # Generate review ID and persist
        review_id = hashlib.md5(
            f"{req_body.get('repository', '')}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        review_result["review_id"] = review_id

        save_review_record(review_id, "code_review", req_body, review_result)

        return func.HttpResponse(
            json.dumps(review_result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing code review: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize-pr", methods=["POST"])
async def summarize_pr_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    PR summarization endpoint - generates structured summary with risk analysis.

    Request Body:
    {
        "title": "Add user authentication module",
        "description": "Implements OAuth2 flow...",
        "author": "developer@company.com",
        "target_branch": "main",
        "diff": "unified diff...",
        "files_changed": 12
    }

    Response:
    {
        "title_summary": "...",
        "change_overview": "...",
        "key_changes": [...],
        "risk_areas": [...]
    }
    """
    try:
        req_body = req.get_json()

        if not req_body.get("title"):
            return func.HttpResponse(
                json.dumps({"error": "Field 'title' is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Summarizing PR: {req_body.get('title', 'unknown')[:60]}")

        # Generate PR summary
        summary = summarize_pull_request(req_body)

        # Persist record
        summary_id = hashlib.md5(
            f"pr-{req_body.get('title', '')}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        summary["summary_id"] = summary_id

        save_review_record(summary_id, "pr_summary", req_body, summary)

        return func.HttpResponse(
            json.dumps(summary),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error summarizing PR: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="incident-rca", methods=["POST"])
async def incident_rca_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Incident RCA endpoint - analyzes incidents to determine root cause.

    Request Body:
    {
        "incident": {
            "id": "INC-2024-001",
            "severity": "P1",
            "title": "API gateway timeout",
            "start_time": "2024-01-15T10:30:00Z",
            "affected_services": ["api-gateway", "auth-service"]
        },
        "logs": "2024-01-15T10:29:55 ERROR Connection pool exhausted..."
    }

    Response:
    {
        "incident_summary": "...",
        "root_cause": "...",
        "remediation_steps": [...],
        "prevention_recommendations": [...]
    }
    """
    try:
        req_body = req.get_json()
        incident_data = req_body.get("incident")
        logs = req_body.get("logs", "")

        if not incident_data:
            return func.HttpResponse(
                json.dumps({"error": "Field 'incident' is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing RCA for incident: {incident_data.get('id', 'unknown')}")

        # Perform RCA analysis
        rca_result = analyze_incident_rca(incident_data, logs)

        # Persist record
        rca_id = hashlib.md5(
            f"rca-{incident_data.get('id', '')}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        rca_result["rca_id"] = rca_id

        save_review_record(rca_id, "incident_rca", req_body, rca_result)

        return func.HttpResponse(
            json.dumps(rca_result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error performing incident RCA: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="deployment-risk", methods=["POST"])
async def deployment_risk_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Deployment risk assessment endpoint - scores risk for planned deployments.

    Request Body:
    {
        "environment": "production",
        "service": "payment-service",
        "change_type": "feature",
        "planned_time": "2024-01-20T02:00:00Z",
        "changes_summary": "Add new payment provider integration",
        "files_changed": 25,
        "lines_changed": 480,
        "test_results": {"passed": 142, "failed": 0, "skipped": 3},
        "rollback_plan": "Revert to v2.3.1 via blue-green switch"
    }

    Response:
    {
        "risk_score": 0.45,
        "risk_level": "medium",
        "go_no_go": "go_with_caution",
        "risk_factors": [...],
        "mitigation_strategies": [...]
    }
    """
    try:
        req_body = req.get_json()

        if not req_body.get("service"):
            return func.HttpResponse(
                json.dumps({"error": "Field 'service' is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(
            f"Assessing deployment risk for {req_body.get('service')} "
            f"to {req_body.get('environment', 'unknown')}"
        )

        # Perform risk assessment
        risk_result = assess_deployment_risk(req_body)

        # Persist record
        risk_id = hashlib.md5(
            f"risk-{req_body.get('service', '')}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        risk_result["assessment_id"] = risk_id

        save_review_record(risk_id, "deployment_risk", req_body, risk_result)

        return func.HttpResponse(
            json.dumps(risk_result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error assessing deployment risk: {e}", exc_info=True)
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
            "service": "code-review-devops-copilot",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Service Bus Trigger for Async PR Review Processing
# ==============================================================================

@app.function_name(name="AsyncPRReviewProcessor")
@app.service_bus_queue_trigger(
    arg_name="message",
    queue_name="pr-review-queue",
    connection="SERVICE_BUS_CONNECTION"
)
async def async_pr_review_processor(message: func.ServiceBusMessage):
    """
    Triggered by Service Bus messages for asynchronous PR review processing.
    Handles large PRs and batch review requests without HTTP timeout constraints.

    Expected message format:
    {
        "pr_url": "https://github.com/org/repo/pull/123",
        "repository": "org/repo",
        "pr_number": 123,
        "callback_url": "https://webhook.site/...",
        "requested_by": "user@company.com",
        "review_scope": "full"
    }
    """
    try:
        message_body = message.get_body().decode("utf-8")
        pr_request = json.loads(message_body)

        pr_url = pr_request.get("pr_url")
        repository = pr_request.get("repository", "unknown")
        pr_number = pr_request.get("pr_number", 0)
        callback_url = pr_request.get("callback_url")

        logger.info(f"Processing async PR review: {repository}#{pr_number}")

        # Fetch PR data from GitHub API
        github_token = get_keyvault_client().get_secret("github-pat").value
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3.diff"
        }

        diff_response = requests.get(
            f"{Config.GITHUB_API_URL}/repos/{repository}/pulls/{pr_number}",
            headers=headers,
            timeout=30
        )
        diff_response.raise_for_status()
        diff_content = diff_response.text

        # Fetch PR metadata
        headers["Accept"] = "application/vnd.github.v3+json"
        meta_response = requests.get(
            f"{Config.GITHUB_API_URL}/repos/{repository}/pulls/{pr_number}",
            headers=headers,
            timeout=30
        )
        meta_response.raise_for_status()
        pr_metadata = meta_response.json()

        # Perform code review
        review_result = review_code_changes(diff_content)
        comments = generate_review_comments(review_result)

        # Generate PR summary
        pr_data = {
            "title": pr_metadata.get("title", ""),
            "description": pr_metadata.get("body", ""),
            "author": pr_metadata.get("user", {}).get("login", "unknown"),
            "target_branch": pr_metadata.get("base", {}).get("ref", "main"),
            "diff": diff_content,
            "files_changed": pr_metadata.get("changed_files", 0)
        }
        summary = summarize_pull_request(pr_data)

        # Combine results
        full_result = {
            "repository": repository,
            "pr_number": pr_number,
            "review": review_result,
            "comments": comments,
            "summary": summary,
            "processed_at": datetime.utcnow().isoformat(),
            "requested_by": pr_request.get("requested_by", "system")
        }

        # Persist review
        review_id = hashlib.md5(
            f"async-{repository}-{pr_number}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        full_result["review_id"] = review_id

        save_review_record(review_id, "async_pr_review", pr_request, full_result)

        # Send callback if provided
        if callback_url:
            try:
                requests.post(
                    callback_url,
                    json=full_result,
                    timeout=10
                )
                logger.info(f"Callback sent to {callback_url}")
            except Exception as cb_err:
                logger.warning(f"Failed to send callback: {cb_err}")

        logger.info(f"Async PR review completed: {repository}#{pr_number} (ID: {review_id})")

    except Exception as e:
        logger.error(f"Error processing async PR review: {e}", exc_info=True)
        raise
