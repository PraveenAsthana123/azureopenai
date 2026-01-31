"""
IoT Predictive Maintenance Platform - Azure Functions
=====================================================
Predictive maintenance for manufacturing equipment using
sensor data, ML predictions, and GenAI-powered insights.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
import redis
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
    STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
    IOT_HUB_HOSTNAME = os.getenv("IOT_HUB_HOSTNAME")
    ML_ENDPOINT = os.getenv("ML_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    DATABASE_NAME = "predictive-maintenance"
    CACHE_TTL = 3600

    # Thresholds
    ANOMALY_THRESHOLD = 0.85
    RUL_CRITICAL_DAYS = 7
    RUL_WARNING_DAYS = 30


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_cosmos_client = None
_redis_client = None
_blob_client = None


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


def get_blob_client():
    """Get Blob Service client."""
    global _blob_client
    if _blob_client is None:
        _blob_client = BlobServiceClient(
            account_url=Config.STORAGE_ACCOUNT_URL,
            credential=get_credential()
        )
    return _blob_client


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def predict_remaining_useful_life(device_id: str, sensor_data: dict) -> dict:
    """
    Call Azure ML endpoint to predict Remaining Useful Life (RUL).

    Args:
        device_id: Equipment device identifier
        sensor_data: Current sensor readings

    Returns:
        RUL prediction with confidence and severity
    """
    credential = get_credential()
    token = credential.get_token("https://ml.azure.com/.default").token

    payload = {
        "input_data": {
            "columns": list(sensor_data.keys()),
            "data": [list(sensor_data.values())]
        }
    }

    response = requests.post(
        f"{Config.ML_ENDPOINT}/score",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        prediction = response.json()
        rul_days = prediction.get("rul_days", 999)

        if rul_days <= Config.RUL_CRITICAL_DAYS:
            severity = "critical"
        elif rul_days <= Config.RUL_WARNING_DAYS:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "device_id": device_id,
            "rul_days": rul_days,
            "confidence": prediction.get("confidence", 0.0),
            "severity": severity,
            "predicted_failure_date": (datetime.utcnow() + timedelta(days=rul_days)).isoformat(),
            "predicted_at": datetime.utcnow().isoformat()
        }
    else:
        logger.error(f"ML prediction failed: {response.status_code}")
        return {"device_id": device_id, "error": "Prediction failed", "status_code": response.status_code}


def detect_anomaly(device_id: str, sensor_data: dict) -> dict:
    """
    Detect anomalies in sensor data using statistical thresholds
    and ML-based analysis.

    Args:
        device_id: Equipment device identifier
        sensor_data: Current sensor readings

    Returns:
        Anomaly detection result with affected sensors
    """
    redis_client = get_redis_client()

    # Get historical baselines from Redis cache
    baseline_key = f"baseline:{device_id}"
    cached_baseline = redis_client.get(baseline_key)

    if cached_baseline:
        baseline = json.loads(cached_baseline)
    else:
        baseline = {
            "vibration_x": {"mean": 2.0, "std": 0.5},
            "vibration_y": {"mean": 1.5, "std": 0.4},
            "vibration_z": {"mean": 1.0, "std": 0.3},
            "temperature": {"mean": 65.0, "std": 5.0},
            "spindle_speed": {"mean": 12000, "std": 500},
            "power_consumption": {"mean": 8.0, "std": 1.5}
        }

    anomalies = []
    anomaly_score = 0.0

    for sensor_name, value in sensor_data.items():
        if sensor_name in baseline:
            mean = baseline[sensor_name]["mean"]
            std = baseline[sensor_name]["std"]
            z_score = abs(value - mean) / std if std > 0 else 0

            if z_score > 3.0:
                anomalies.append({
                    "sensor": sensor_name,
                    "value": value,
                    "z_score": round(z_score, 2),
                    "expected_range": f"{mean - 2*std:.1f} - {mean + 2*std:.1f}",
                    "severity": "high" if z_score > 5.0 else "medium"
                })
                anomaly_score = max(anomaly_score, min(z_score / 5.0, 1.0))

    is_anomalous = anomaly_score >= Config.ANOMALY_THRESHOLD

    return {
        "device_id": device_id,
        "is_anomalous": is_anomalous,
        "anomaly_score": round(anomaly_score, 3),
        "anomalies": anomalies,
        "sensors_checked": len(sensor_data),
        "detected_at": datetime.utcnow().isoformat()
    }


def generate_maintenance_recommendation(device_id: str, prediction: dict,
                                          anomaly_result: dict, maintenance_history: list) -> dict:
    """
    Generate AI-powered maintenance recommendations using GPT-4o.

    Args:
        device_id: Equipment identifier
        prediction: RUL prediction result
        anomaly_result: Anomaly detection result
        maintenance_history: Recent maintenance records

    Returns:
        Structured recommendation with priority and actions
    """
    client = get_openai_client()

    system_prompt = """You are an expert industrial maintenance advisor. Analyze equipment
sensor data, ML predictions, and maintenance history to provide actionable recommendations.

Respond as JSON with:
- summary: Plain English summary of equipment health
- priority: critical, high, medium, or low
- recommended_actions: List of specific maintenance actions
- root_cause_analysis: Likely cause of any detected issues
- spare_parts: List of parts that may need replacement
- estimated_downtime_hours: Estimated repair time
- safety_warnings: Any safety considerations
- next_inspection_date: When to next inspect"""

    user_prompt = f"""Equipment: {device_id}

RUL Prediction:
{json.dumps(prediction, indent=2)}

Anomaly Detection:
{json.dumps(anomaly_result, indent=2)}

Recent Maintenance History:
{json.dumps(maintenance_history, indent=2)}

Provide maintenance recommendations."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1024,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    recommendation = json.loads(response.choices[0].message.content)
    recommendation["device_id"] = device_id
    recommendation["generated_at"] = datetime.utcnow().isoformat()
    recommendation["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return recommendation


def get_equipment_status(device_id: str) -> dict:
    """
    Get comprehensive equipment health status.

    Args:
        device_id: Equipment identifier

    Returns:
        Equipment status with latest readings, prediction, and recommendation
    """
    # Check Redis cache first
    redis_client = get_redis_client()
    cached = redis_client.get(f"equipment:status:{device_id}")
    if cached:
        return json.loads(cached)

    # Get latest readings from Cosmos DB
    container = get_cosmos_container("telemetry")
    query = (
        "SELECT TOP 1 * FROM c WHERE c.deviceId = @deviceId "
        "ORDER BY c.timestamp DESC"
    )

    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@deviceId", "value": device_id}],
        enable_cross_partition_query=True
    ))

    if not items:
        return {"device_id": device_id, "status": "no_data"}

    latest = items[0]

    # Get maintenance history
    maint_container = get_cosmos_container("maintenance")
    maint_query = (
        "SELECT * FROM c WHERE c.deviceId = @deviceId "
        "ORDER BY c.completedAt DESC OFFSET 0 LIMIT 5"
    )

    history = list(maint_container.query_items(
        query=maint_query,
        parameters=[{"name": "@deviceId", "value": device_id}],
        enable_cross_partition_query=True
    ))

    status = {
        "device_id": device_id,
        "latest_reading": latest,
        "maintenance_history": history,
        "retrieved_at": datetime.utcnow().isoformat()
    }

    # Cache for 5 minutes
    redis_client.setex(f"equipment:status:{device_id}", 300, json.dumps(status, default=str))

    return status


def get_fleet_overview() -> dict:
    """
    Get overview of all equipment health across the fleet.

    Returns:
        Fleet-wide summary with counts by severity
    """
    container = get_cosmos_container("predictions")
    query = (
        "SELECT c.deviceId, c.rul_days, c.severity, c.predicted_at "
        "FROM c WHERE c.predicted_at >= @since "
        "ORDER BY c.rul_days ASC"
    )

    since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    predictions = list(container.query_items(
        query=query,
        parameters=[{"name": "@since", "value": since}],
        enable_cross_partition_query=True
    ))

    critical = [p for p in predictions if p.get("severity") == "critical"]
    warning = [p for p in predictions if p.get("severity") == "warning"]
    normal = [p for p in predictions if p.get("severity") == "normal"]

    return {
        "total_equipment": len(predictions),
        "critical_count": len(critical),
        "warning_count": len(warning),
        "normal_count": len(normal),
        "critical_devices": [p["deviceId"] for p in critical],
        "warning_devices": [p["deviceId"] for p in warning[:10]],
        "generated_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="predict", methods=["POST"])
async def predict_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Predict RUL for a device."""
    try:
        body = req.get_json()
        device_id = body.get("device_id")
        sensor_data = body.get("sensor_data")

        if not device_id or not sensor_data:
            return func.HttpResponse(
                json.dumps({"error": "device_id and sensor_data are required"}),
                status_code=400,
                mimetype="application/json"
            )

        prediction = predict_remaining_useful_life(device_id, sensor_data)

        # Store prediction
        container = get_cosmos_container("predictions")
        container.upsert_item(body={
            "id": f"{device_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "deviceId": device_id,
            **prediction
        })

        return func.HttpResponse(
            json.dumps(prediction),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="anomaly", methods=["POST"])
async def anomaly_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Detect anomalies in sensor data."""
    try:
        body = req.get_json()
        device_id = body.get("device_id")
        sensor_data = body.get("sensor_data")

        if not device_id or not sensor_data:
            return func.HttpResponse(
                json.dumps({"error": "device_id and sensor_data are required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = detect_anomaly(device_id, sensor_data)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="recommend", methods=["POST"])
async def recommend_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Generate maintenance recommendation for a device."""
    try:
        body = req.get_json()
        device_id = body.get("device_id")
        prediction = body.get("prediction")
        anomaly_result = body.get("anomaly_result")
        maintenance_history = body.get("maintenance_history", [])

        if not device_id or not prediction:
            return func.HttpResponse(
                json.dumps({"error": "device_id and prediction are required"}),
                status_code=400,
                mimetype="application/json"
            )

        recommendation = generate_maintenance_recommendation(
            device_id, prediction, anomaly_result or {}, maintenance_history
        )

        return func.HttpResponse(
            json.dumps(recommendation),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Recommendation failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="equipment/{device_id}", methods=["GET"])
async def equipment_status_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Get equipment health status."""
    try:
        device_id = req.route_params.get("device_id")
        status = get_equipment_status(device_id)

        return func.HttpResponse(
            json.dumps(status, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Equipment status failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="fleet", methods=["GET"])
async def fleet_overview_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Get fleet-wide equipment health overview."""
    try:
        overview = get_fleet_overview()

        return func.HttpResponse(
            json.dumps(overview),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Fleet overview failed: {e}", exc_info=True)
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
            "service": "iot-predictive-maintenance",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger - Sensor Data Processing
# ==============================================================================

@app.function_name(name="SensorDataProcessor")
@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="sensor-data",
    connection="EVENT_HUB_CONNECTION",
    cardinality="many"
)
async def sensor_data_processor(events: List[func.EventHubEvent]):
    """
    Process incoming sensor telemetry from IoT Hub via Event Hub.
    Performs anomaly detection and triggers alerts for critical readings.
    """
    for event in events:
        try:
            telemetry = json.loads(event.get_body().decode("utf-8"))
            device_id = telemetry.get("deviceId")
            sensors = telemetry.get("sensors", {})

            logger.info(f"Processing telemetry for device {device_id}")

            # Store raw telemetry
            container = get_cosmos_container("telemetry")
            container.create_item(body={
                "id": f"{device_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
                "deviceId": device_id,
                "sensors": sensors,
                "metadata": telemetry.get("metadata", {}),
                "timestamp": telemetry.get("timestamp", datetime.utcnow().isoformat())
            })

            # Run anomaly detection
            anomaly = detect_anomaly(device_id, sensors)

            if anomaly["is_anomalous"]:
                logger.warning(f"Anomaly detected for device {device_id}: score={anomaly['anomaly_score']}")

                # Store anomaly alert
                alert_container = get_cosmos_container("alerts")
                alert_container.create_item(body={
                    "id": f"alert-{device_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    "deviceId": device_id,
                    "type": "anomaly",
                    "anomaly_score": anomaly["anomaly_score"],
                    "anomalies": anomaly["anomalies"],
                    "status": "open",
                    "createdAt": datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error processing sensor data: {e}", exc_info=True)
