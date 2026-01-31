"""
Real-Time Analytics Dashboard - Azure Functions
================================================
Streaming analytics with natural language to KQL translation,
anomaly detection on live telemetry, and GenAI executive summaries
for enterprise dashboards powered by Azure Data Explorer.
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
from openai import AzureOpenAI
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder

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
    ADX_CLUSTER_URL = os.getenv("ADX_CLUSTER_URL")
    ADX_DATABASE = os.getenv("ADX_DATABASE", "telemetrydb")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configuration
    GPT_MODEL = "gpt-4o"

    # Analytics parameters
    ANOMALY_SENSITIVITY = float(os.getenv("ANOMALY_SENSITIVITY", "2.5"))
    DASHBOARD_LOOKBACK_HOURS = int(os.getenv("DASHBOARD_LOOKBACK_HOURS", "24"))
    MAX_KQL_ROWS = 10000
    ALERT_COOLDOWN_MINUTES = 15


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_kusto_client = None
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


def get_kusto_client() -> KustoClient:
    """Get Azure Data Explorer (Kusto) client."""
    global _kusto_client
    if _kusto_client is None:
        kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
            Config.ADX_CLUSTER_URL,
            get_credential()
        )
        _kusto_client = KustoClient(kcsb)
    return _kusto_client


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client("analyticsdashboard")
    return database.get_container_client(container_name)


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def natural_language_to_kql(nl_query: str) -> dict:
    """
    Convert a natural language question into a KQL query using Azure OpenAI.

    Args:
        nl_query: Natural language analytics question from the user.

    Returns:
        Dict with generated KQL query and explanation.
    """
    client = get_openai_client()

    system_prompt = """You are an expert Azure Data Explorer (Kusto) query translator.
Convert the user's natural language question into a valid KQL query.

Available tables and schemas:
- Telemetry: Timestamp (datetime), MetricName (string), MetricValue (real), ResourceId (string), Region (string), Tags (dynamic)
- Requests: Timestamp (datetime), Endpoint (string), StatusCode (int), DurationMs (real), UserId (string), Region (string)
- Errors: Timestamp (datetime), ErrorCode (string), Message (string), Severity (string), ServiceName (string), StackTrace (string)
- Deployments: Timestamp (datetime), ServiceName (string), Version (string), Environment (string), Status (string), DeployedBy (string)

RULES:
1. Output ONLY valid KQL, no markdown fences
2. Always include a reasonable time filter using Timestamp
3. Limit results to 10000 rows unless aggregating
4. Prefer summarize for analytical questions
5. Use render operator for visualization hints when appropriate

Respond in JSON format:
{"kql": "<the KQL query>", "explanation": "<brief explanation of the query>"}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": nl_query}
        ],
        max_tokens=1024,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    logger.info(f"NL-to-KQL translation complete: {nl_query[:60]}...")
    return result


def execute_kql_query(kql_query: str) -> dict:
    """
    Execute a KQL query against Azure Data Explorer.

    Args:
        kql_query: Valid KQL query string.

    Returns:
        Dict with column names and row data from the query result.
    """
    client = get_kusto_client()

    response = client.execute(Config.ADX_DATABASE, kql_query)
    primary_results = response.primary_results[0]

    columns = [col.column_name for col in primary_results.columns]
    rows = []
    for row in primary_results:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Serialize datetime objects for JSON compatibility
            if isinstance(value, datetime):
                value = value.isoformat()
            row_dict[col] = value
        rows.append(row_dict)

    logger.info(f"KQL query returned {len(rows)} rows across {len(columns)} columns")
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows)
    }


def detect_anomalies(metric_data: list[dict]) -> dict:
    """
    Identify anomalies in streaming metric data using Azure OpenAI.

    Args:
        metric_data: List of dicts with keys Timestamp, MetricName, MetricValue.

    Returns:
        Dict containing detected anomalies and analysis narrative.
    """
    client = get_openai_client()

    system_prompt = """You are an expert anomaly detection analyst for cloud infrastructure metrics.
Analyze the provided time-series metric data and identify anomalies.

For each anomaly found, provide:
- timestamp: when the anomaly occurred
- metric_name: which metric is anomalous
- metric_value: the observed value
- expected_range: what normal range looks like
- severity: "critical", "warning", or "info"
- description: short human-readable explanation

Respond in JSON:
{"anomalies": [...], "summary": "<overall analysis>", "anomaly_count": <int>}
"""

    # Prepare metric data as a compact string for the prompt
    data_summary = json.dumps(metric_data[:500], default=str)

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze the following metric data for anomalies:\n{data_summary}"}
        ],
        max_tokens=2048,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    logger.info(f"Anomaly detection complete: {result.get('anomaly_count', 0)} anomalies found")
    return result


def generate_executive_summary(dashboard_data: dict) -> dict:
    """
    Generate a GenAI narrative executive summary of dashboard metrics.

    Args:
        dashboard_data: Dict with dashboard KPIs, trends, and alert counts.

    Returns:
        Dict with narrative summary and key highlights.
    """
    client = get_openai_client()

    system_prompt = """You are a senior cloud platform analyst writing an executive summary
for leadership. Given the dashboard metrics below, produce a concise narrative that:

1. Highlights the top 3 most important observations
2. Calls out any concerning trends or anomalies
3. Provides actionable recommendations
4. Uses professional, non-technical language suitable for C-level executives

Respond in JSON:
{
    "summary": "<narrative paragraph>",
    "highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
    "risk_level": "low" | "medium" | "high",
    "recommendations": ["<rec 1>", "<rec 2>"]
}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dashboard data:\n{json.dumps(dashboard_data, default=str)}"}
        ],
        max_tokens=2048,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result["generated_at"] = datetime.utcnow().isoformat()
    result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    logger.info("Executive summary generated successfully")
    return result


def create_alert(anomaly_data: dict) -> dict:
    """
    Persist an alert record in Cosmos DB from a detected anomaly.

    Args:
        anomaly_data: Dict with anomaly details (severity, metric_name, etc.).

    Returns:
        The created alert document.
    """
    container = get_cosmos_container("alerts")

    alert_id = hashlib.md5(
        f"{anomaly_data.get('metric_name', 'unknown')}-{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()

    alert = {
        "id": alert_id,
        "partitionKey": anomaly_data.get("severity", "warning"),
        "metricName": anomaly_data.get("metric_name", "unknown"),
        "metricValue": anomaly_data.get("metric_value"),
        "expectedRange": anomaly_data.get("expected_range", "N/A"),
        "severity": anomaly_data.get("severity", "warning"),
        "description": anomaly_data.get("description", ""),
        "status": "open",
        "createdAt": datetime.utcnow().isoformat(),
        "acknowledgedAt": None,
        "resolvedAt": None
    }

    container.create_item(body=alert)
    logger.info(f"Alert created: {alert_id} severity={alert['severity']}")
    return alert


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="nl-query", methods=["POST"])
async def nl_query_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Natural language to KQL query endpoint.

    Request Body:
    {
        "query": "Show me average request latency by region for the last 6 hours"
    }

    Response:
    {
        "kql": "...",
        "explanation": "...",
        "results": { "columns": [...], "rows": [...] },
        "usage": {...}
    }
    """
    try:
        req_body = req.get_json()
        nl_query = req_body.get("query")

        if not nl_query:
            return func.HttpResponse(
                json.dumps({"error": "query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"NL query received: {nl_query[:80]}...")

        # Step 1: Translate natural language to KQL
        translation = natural_language_to_kql(nl_query)

        # Step 2: Execute the generated KQL
        kql = translation["kql"]
        query_results = execute_kql_query(kql)

        response_data = {
            "kql": kql,
            "explanation": translation.get("explanation", ""),
            "results": query_results,
            "usage": translation.get("usage", {})
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing NL query: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="anomaly-detect", methods=["POST"])
async def anomaly_detect_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Anomaly detection endpoint.

    Request Body:
    {
        "metric_data": [
            {"Timestamp": "...", "MetricName": "cpu_percent", "MetricValue": 95.2},
            ...
        ],
        "create_alerts": true
    }

    Response:
    {
        "anomalies": [...],
        "summary": "...",
        "alerts_created": [...]
    }
    """
    try:
        req_body = req.get_json()
        metric_data = req_body.get("metric_data")
        should_create_alerts = req_body.get("create_alerts", False)

        if not metric_data or not isinstance(metric_data, list):
            return func.HttpResponse(
                json.dumps({"error": "metric_data (list) is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Anomaly detection requested for {len(metric_data)} data points")

        # Detect anomalies via OpenAI
        detection_result = detect_anomalies(metric_data)

        # Optionally create alerts for detected anomalies
        alerts_created = []
        if should_create_alerts and detection_result.get("anomalies"):
            for anomaly in detection_result["anomalies"]:
                if anomaly.get("severity") in ("critical", "warning"):
                    alert = create_alert(anomaly)
                    alerts_created.append(alert)

        response_data = {
            "anomalies": detection_result.get("anomalies", []),
            "anomaly_count": detection_result.get("anomaly_count", 0),
            "summary": detection_result.get("summary", ""),
            "alerts_created": alerts_created,
            "usage": detection_result.get("usage", {})
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="executive-summary", methods=["POST"])
async def executive_summary_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    GenAI executive summary endpoint.

    Request Body:
    {
        "dashboard_data": {
            "total_requests": 1450000,
            "error_rate_percent": 0.42,
            "p99_latency_ms": 320,
            "active_alerts": 3,
            "deployment_count_24h": 7,
            "top_errors": [...],
            "region_breakdown": {...}
        }
    }

    Response:
    {
        "summary": "...",
        "highlights": [...],
        "risk_level": "low",
        "recommendations": [...]
    }
    """
    try:
        req_body = req.get_json()
        dashboard_data = req_body.get("dashboard_data")

        if not dashboard_data:
            return func.HttpResponse(
                json.dumps({"error": "dashboard_data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Executive summary generation requested")

        result = generate_executive_summary(dashboard_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating executive summary: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="dashboard-data", methods=["GET"])
async def dashboard_data_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch aggregated dashboard data from Azure Data Explorer.

    Query Parameters:
        lookback_hours (int): Hours of data to retrieve (default: 24)
    """
    try:
        lookback_hours = int(req.params.get("lookback_hours", Config.DASHBOARD_LOOKBACK_HOURS))

        logger.info(f"Fetching dashboard data for last {lookback_hours} hours")

        # Aggregate request metrics
        requests_kql = f"""
        Requests
        | where Timestamp > ago({lookback_hours}h)
        | summarize
            TotalRequests = count(),
            AvgDurationMs = avg(DurationMs),
            P99DurationMs = percentile(DurationMs, 99),
            ErrorCount = countif(StatusCode >= 500),
            ErrorRate = round(100.0 * countif(StatusCode >= 500) / count(), 2)
          by bin(Timestamp, 1h), Region
        | order by Timestamp desc
        """
        request_metrics = execute_kql_query(requests_kql)

        # Aggregate error breakdown
        errors_kql = f"""
        Errors
        | where Timestamp > ago({lookback_hours}h)
        | summarize Count = count() by ErrorCode, Severity, ServiceName
        | order by Count desc
        | take 20
        """
        error_breakdown = execute_kql_query(errors_kql)

        # Active alerts from Cosmos DB
        alerts_container = get_cosmos_container("alerts")
        open_alerts = list(alerts_container.query_items(
            query="SELECT * FROM c WHERE c.status = 'open' ORDER BY c.createdAt DESC",
            enable_cross_partition_query=True
        ))

        response_data = {
            "request_metrics": request_metrics,
            "error_breakdown": error_breakdown,
            "active_alerts": open_alerts,
            "active_alert_count": len(open_alerts),
            "lookback_hours": lookback_hours,
            "generated_at": datetime.utcnow().isoformat()
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
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
            "service": "realtime-analytics-dashboard",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger for Streaming Telemetry Processing
# ==============================================================================

@app.function_name(name="StreamingTelemetryProcessor")
@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="telemetry-stream",
    connection="EVENT_HUB_CONNECTION"
)
async def streaming_telemetry_processor(events: func.EventHubEvent):
    """
    Triggered by incoming telemetry events on the Event Hub.
    Performs real-time anomaly screening and persists alerts when thresholds
    are exceeded.
    """
    try:
        # Event Hub may deliver a batch; normalize to list
        if not isinstance(events, list):
            events = [events]

        logger.info(f"Processing batch of {len(events)} telemetry events")

        metric_batch = []
        for event in events:
            body = event.get_body().decode("utf-8")
            data = json.loads(body)
            metric_batch.append({
                "Timestamp": data.get("Timestamp", datetime.utcnow().isoformat()),
                "MetricName": data.get("MetricName", "unknown"),
                "MetricValue": data.get("MetricValue", 0),
                "ResourceId": data.get("ResourceId", ""),
                "Region": data.get("Region", "unknown")
            })

        # Run anomaly detection on the batch
        if metric_batch:
            detection_result = detect_anomalies(metric_batch)

            # Create alerts for critical and warning anomalies
            anomalies = detection_result.get("anomalies", [])
            for anomaly in anomalies:
                if anomaly.get("severity") in ("critical", "warning"):
                    create_alert(anomaly)
                    logger.warning(
                        f"Alert raised: {anomaly.get('metric_name')} "
                        f"severity={anomaly.get('severity')}"
                    )

        logger.info(f"Telemetry batch processing complete: {len(metric_batch)} events")

    except Exception as e:
        logger.error(f"Error processing telemetry stream: {e}", exc_info=True)
        raise
