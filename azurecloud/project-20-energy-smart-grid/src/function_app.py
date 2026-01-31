"""
Energy & Utilities Smart Grid - Azure Functions
================================================
Smart meter analytics, load forecasting, outage prediction,
and GenAI-driven grid optimization for energy utilities.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
from azure.iot.hub import IoTHubRegistryManager
import numpy as np

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
    IOT_HUB_CONNECTION = os.getenv("IOT_HUB_CONNECTION")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    ML_ENDPOINT = os.getenv("ML_ENDPOINT")
    EVENT_HUB_CONNECTION = os.getenv("EVENT_HUB_CONNECTION")

    # Model configuration
    GPT_MODEL = "gpt-4o"

    # Grid parameters
    ANOMALY_THRESHOLD = 2.5
    HEALTH_SCORE_WEIGHTS = {
        "voltage_stability": 0.25,
        "load_balance": 0.20,
        "frequency_deviation": 0.20,
        "outage_rate": 0.15,
        "equipment_health": 0.20
    }


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_cosmos_client = None
_iothub_manager = None


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
    database = _cosmos_client.get_database_client("smartgrid")
    return database.get_container_client(container_name)


def get_iothub_manager() -> IoTHubRegistryManager:
    """Get IoT Hub registry manager."""
    global _iothub_manager
    if _iothub_manager is None:
        _iothub_manager = IoTHubRegistryManager(Config.IOT_HUB_CONNECTION)
    return _iothub_manager


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def analyze_meter_data(meter_id: str, readings: List[dict]) -> dict:
    """
    Analyze smart meter data for consumption patterns and anomalies.

    Args:
        meter_id: Unique identifier of the smart meter
        readings: List of meter reading dicts with timestamp, kwh, voltage, current

    Returns:
        Analysis result with patterns, anomalies, and statistics
    """
    if not readings:
        return {"meter_id": meter_id, "status": "no_data", "anomalies": []}

    kwh_values = np.array([r.get("kwh", 0.0) for r in readings])
    voltage_values = np.array([r.get("voltage", 0.0) for r in readings])

    mean_kwh = float(np.mean(kwh_values))
    std_kwh = float(np.std(kwh_values))
    mean_voltage = float(np.mean(voltage_values))
    std_voltage = float(np.std(voltage_values))

    # Detect anomalies using z-score threshold
    anomalies = []
    for i, reading in enumerate(readings):
        kwh_zscore = abs(reading.get("kwh", 0.0) - mean_kwh) / std_kwh if std_kwh > 0 else 0
        voltage_zscore = abs(reading.get("voltage", 0.0) - mean_voltage) / std_voltage if std_voltage > 0 else 0

        if kwh_zscore > Config.ANOMALY_THRESHOLD:
            anomalies.append({
                "type": "consumption_spike",
                "timestamp": reading.get("timestamp"),
                "value": reading.get("kwh"),
                "z_score": round(kwh_zscore, 2)
            })
        if voltage_zscore > Config.ANOMALY_THRESHOLD:
            anomalies.append({
                "type": "voltage_deviation",
                "timestamp": reading.get("timestamp"),
                "value": reading.get("voltage"),
                "z_score": round(voltage_zscore, 2)
            })

    # Peak usage detection
    peak_idx = int(np.argmax(kwh_values))
    trough_idx = int(np.argmin(kwh_values))

    return {
        "meter_id": meter_id,
        "status": "analyzed",
        "statistics": {
            "mean_kwh": round(mean_kwh, 3),
            "std_kwh": round(std_kwh, 3),
            "max_kwh": round(float(np.max(kwh_values)), 3),
            "min_kwh": round(float(np.min(kwh_values)), 3),
            "mean_voltage": round(mean_voltage, 2),
            "total_consumption": round(float(np.sum(kwh_values)), 3)
        },
        "peak_reading": readings[peak_idx],
        "trough_reading": readings[trough_idx],
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "reading_count": len(readings)
    }


def forecast_load(region: str, historical_data: List[dict], weather_data: dict) -> dict:
    """
    Forecast electrical load for a region using historical and weather data with OpenAI.

    Args:
        region: Grid region identifier
        historical_data: Historical load readings with timestamp and load_mw
        weather_data: Weather forecast with temperature, humidity, wind_speed

    Returns:
        Load forecast with hourly predictions and confidence intervals
    """
    client = get_openai_client()

    # Summarize historical patterns for prompt
    load_values = [d.get("load_mw", 0) for d in historical_data[-48:]]
    recent_avg = sum(load_values) / len(load_values) if load_values else 0
    recent_max = max(load_values) if load_values else 0
    recent_min = min(load_values) if load_values else 0

    prompt = f"""You are an energy grid load forecasting expert. Analyze the following data and
provide a 24-hour load forecast in JSON format.

Region: {region}
Recent load statistics (last 48 readings):
- Average: {recent_avg:.1f} MW
- Peak: {recent_max:.1f} MW
- Minimum: {recent_min:.1f} MW

Weather forecast:
- Temperature: {weather_data.get('temperature', 'N/A')} F
- Humidity: {weather_data.get('humidity', 'N/A')}%
- Wind speed: {weather_data.get('wind_speed', 'N/A')} mph
- Conditions: {weather_data.get('conditions', 'N/A')}

Return a JSON object with:
- "hourly_forecast": array of 24 objects with "hour", "predicted_mw", "lower_bound", "upper_bound"
- "peak_hour": hour of expected peak demand
- "peak_mw": expected peak demand in MW
- "risk_level": "low", "medium", or "high"
- "summary": brief text summary
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a power grid load forecasting analyst. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2048,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    forecast = json.loads(response.choices[0].message.content)
    forecast["region"] = region
    forecast["generated_at"] = datetime.utcnow().isoformat()
    forecast["model"] = Config.GPT_MODEL

    return forecast


def predict_outage(grid_sector: str, sensor_data: List[dict]) -> dict:
    """
    Predict potential outages from sensor anomalies in a grid sector.

    Args:
        grid_sector: Grid sector identifier
        sensor_data: List of sensor readings with sensor_id, type, value, threshold

    Returns:
        Outage prediction with risk score and affected components
    """
    alerts = []
    risk_scores = []

    for sensor in sensor_data:
        sensor_id = sensor.get("sensor_id", "unknown")
        sensor_type = sensor.get("type", "unknown")
        value = sensor.get("value", 0)
        threshold = sensor.get("threshold", 100)
        normal_range_low = sensor.get("normal_range_low", 0)
        normal_range_high = sensor.get("normal_range_high", threshold)

        # Calculate deviation from normal range
        if value > normal_range_high:
            deviation = (value - normal_range_high) / (threshold - normal_range_high) if threshold != normal_range_high else 1.0
            severity = min(deviation, 1.0)
            alerts.append({
                "sensor_id": sensor_id,
                "type": sensor_type,
                "value": value,
                "severity": round(severity, 2),
                "message": f"{sensor_type} reading {value} exceeds normal range (>{normal_range_high})"
            })
            risk_scores.append(severity)
        elif value < normal_range_low:
            deviation = (normal_range_low - value) / normal_range_low if normal_range_low != 0 else 1.0
            severity = min(deviation, 1.0)
            alerts.append({
                "sensor_id": sensor_id,
                "type": sensor_type,
                "value": value,
                "severity": round(severity, 2),
                "message": f"{sensor_type} reading {value} below normal range (<{normal_range_low})"
            })
            risk_scores.append(severity)
        else:
            risk_scores.append(0.0)

    # Aggregate risk score for the sector
    overall_risk = float(np.mean(risk_scores)) if risk_scores else 0.0
    max_risk = float(np.max(risk_scores)) if risk_scores else 0.0

    if max_risk > 0.8:
        risk_level = "critical"
    elif max_risk > 0.5:
        risk_level = "high"
    elif overall_risk > 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "grid_sector": grid_sector,
        "overall_risk_score": round(overall_risk, 3),
        "max_risk_score": round(max_risk, 3),
        "risk_level": risk_level,
        "alerts": alerts,
        "alert_count": len(alerts),
        "sensors_evaluated": len(sensor_data),
        "predicted_at": datetime.utcnow().isoformat()
    }


def generate_optimization_recommendations(grid_data: dict) -> dict:
    """
    Generate GenAI recommendations for grid optimization.

    Args:
        grid_data: Current grid state including load, capacity, renewables, storage

    Returns:
        Optimization recommendations from GPT-4o
    """
    client = get_openai_client()

    prompt = f"""You are an expert energy grid optimization advisor. Analyze the current grid state
and provide actionable optimization recommendations in JSON format.

Current Grid State:
- Total Load: {grid_data.get('total_load_mw', 'N/A')} MW
- Total Capacity: {grid_data.get('total_capacity_mw', 'N/A')} MW
- Renewable Generation: {grid_data.get('renewable_mw', 'N/A')} MW
- Fossil Generation: {grid_data.get('fossil_mw', 'N/A')} MW
- Battery Storage Level: {grid_data.get('storage_level_pct', 'N/A')}%
- Grid Frequency: {grid_data.get('frequency_hz', 'N/A')} Hz
- Active Outages: {grid_data.get('active_outages', 0)}
- Demand Response Available: {grid_data.get('demand_response_mw', 'N/A')} MW
- Carbon Intensity: {grid_data.get('carbon_intensity_gco2_kwh', 'N/A')} gCO2/kWh

Return a JSON object with:
- "recommendations": array of objects with "priority" (1-5), "category", "action", "expected_impact", "implementation_time"
- "efficiency_score": current grid efficiency 0-100
- "carbon_reduction_potential_pct": potential carbon reduction percentage
- "cost_savings_potential_pct": potential cost savings percentage
- "summary": brief executive summary
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a grid optimization expert. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=3000,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result["generated_at"] = datetime.utcnow().isoformat()
    result["model"] = Config.GPT_MODEL

    return result


def calculate_grid_health_score(metrics: dict) -> dict:
    """
    Compute overall grid health score from operational metrics.

    Args:
        metrics: Dict with voltage_stability, load_balance, frequency_deviation,
                 outage_rate, equipment_health (each 0-100)

    Returns:
        Weighted health score and per-component breakdown
    """
    weights = Config.HEALTH_SCORE_WEIGHTS
    component_scores = {}
    weighted_total = 0.0

    for component, weight in weights.items():
        score = float(metrics.get(component, 0))
        score = max(0.0, min(100.0, score))
        component_scores[component] = {
            "score": round(score, 1),
            "weight": weight,
            "weighted_score": round(score * weight, 2)
        }
        weighted_total += score * weight

    overall_score = round(weighted_total, 1)

    if overall_score >= 90:
        status = "excellent"
    elif overall_score >= 75:
        status = "good"
    elif overall_score >= 60:
        status = "fair"
    elif overall_score >= 40:
        status = "degraded"
    else:
        status = "critical"

    return {
        "overall_score": overall_score,
        "status": status,
        "components": component_scores,
        "evaluated_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="meter-analysis", methods=["POST"])
async def meter_analysis_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Smart meter analysis endpoint.

    Request Body:
    {
        "meter_id": "METER-001",
        "readings": [{"timestamp": "...", "kwh": 1.5, "voltage": 240.1, "current": 6.2}, ...]
    }
    """
    try:
        req_body = req.get_json()
        meter_id = req_body.get("meter_id")
        readings = req_body.get("readings", [])

        if not meter_id:
            return func.HttpResponse(
                json.dumps({"error": "meter_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing meter data for {meter_id} with {len(readings)} readings")

        result = analyze_meter_data(meter_id, readings)

        # Persist analysis to Cosmos DB
        try:
            container = get_cosmos_container("meterAnalysis")
            result["id"] = hashlib.md5(
                f"{meter_id}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            container.create_item(body=result)
        except Exception as e:
            logger.warning(f"Failed to persist meter analysis: {e}")

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in meter analysis: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="load-forecast", methods=["POST"])
async def load_forecast_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Load forecasting endpoint.

    Request Body:
    {
        "region": "REGION-WEST-01",
        "historical_data": [{"timestamp": "...", "load_mw": 450.5}, ...],
        "weather_data": {"temperature": 95, "humidity": 40, "wind_speed": 12, "conditions": "clear"}
    }
    """
    try:
        req_body = req.get_json()
        region = req_body.get("region")
        historical_data = req_body.get("historical_data", [])
        weather_data = req_body.get("weather_data", {})

        if not region:
            return func.HttpResponse(
                json.dumps({"error": "region is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating load forecast for region {region}")

        result = forecast_load(region, historical_data, weather_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in load forecast: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="outage-predict", methods=["POST"])
async def outage_predict_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Outage prediction endpoint.

    Request Body:
    {
        "grid_sector": "SECTOR-12A",
        "sensor_data": [{"sensor_id": "S001", "type": "transformer_temp", "value": 85, "threshold": 100, "normal_range_low": 30, "normal_range_high": 75}, ...]
    }
    """
    try:
        req_body = req.get_json()
        grid_sector = req_body.get("grid_sector")
        sensor_data = req_body.get("sensor_data", [])

        if not grid_sector:
            return func.HttpResponse(
                json.dumps({"error": "grid_sector is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Predicting outages for sector {grid_sector} with {len(sensor_data)} sensors")

        result = predict_outage(grid_sector, sensor_data)

        # Persist critical predictions
        if result["risk_level"] in ("critical", "high"):
            try:
                container = get_cosmos_container("outageAlerts")
                result["id"] = hashlib.md5(
                    f"{grid_sector}-{datetime.utcnow().isoformat()}".encode()
                ).hexdigest()
                container.create_item(body=result)
            except Exception as e:
                logger.warning(f"Failed to persist outage alert: {e}")

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in outage prediction: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="grid-optimize", methods=["POST"])
async def grid_optimize_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Grid optimization recommendations endpoint.

    Request Body:
    {
        "total_load_mw": 1200,
        "total_capacity_mw": 1800,
        "renewable_mw": 400,
        "fossil_mw": 800,
        "storage_level_pct": 65,
        "frequency_hz": 60.02,
        "active_outages": 2,
        "demand_response_mw": 150,
        "carbon_intensity_gco2_kwh": 320
    }
    """
    try:
        grid_data = req.get_json()

        if not grid_data:
            return func.HttpResponse(
                json.dumps({"error": "Grid data payload is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Generating grid optimization recommendations")

        result = generate_optimization_recommendations(grid_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in grid optimization: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="grid-health", methods=["GET"])
async def grid_health_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Grid health score endpoint.

    Query Parameters:
        voltage_stability, load_balance, frequency_deviation,
        outage_rate, equipment_health (each 0-100)
    """
    try:
        metrics = {
            "voltage_stability": float(req.params.get("voltage_stability", 85)),
            "load_balance": float(req.params.get("load_balance", 80)),
            "frequency_deviation": float(req.params.get("frequency_deviation", 90)),
            "outage_rate": float(req.params.get("outage_rate", 75)),
            "equipment_health": float(req.params.get("equipment_health", 82))
        }

        result = calculate_grid_health_score(metrics)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error computing grid health: {e}", exc_info=True)
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
            "service": "energy-smart-grid",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger - Real-time Meter Reading Processing
# ==============================================================================

@app.function_name(name="MeterReadingProcessor")
@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="meter-readings",
    connection="EVENT_HUB_CONNECTION",
    cardinality="many"
)
async def meter_reading_processor(events: List[func.EventHubEvent]):
    """
    Process real-time smart meter readings from Event Hub.
    Batches are analyzed for anomalies and stored in Cosmos DB.
    """
    try:
        readings_by_meter = {}

        for event in events:
            reading = json.loads(event.get_body().decode("utf-8"))
            meter_id = reading.get("meter_id", "unknown")

            if meter_id not in readings_by_meter:
                readings_by_meter[meter_id] = []
            readings_by_meter[meter_id].append(reading)

        logger.info(f"Processing {len(events)} readings from {len(readings_by_meter)} meters")

        container = get_cosmos_container("meterReadings")

        for meter_id, readings in readings_by_meter.items():
            # Quick anomaly check on batch
            kwh_values = [r.get("kwh", 0) for r in readings]
            if kwh_values:
                mean_val = sum(kwh_values) / len(kwh_values)
                max_val = max(kwh_values)

                if mean_val > 0 and max_val > mean_val * 3:
                    logger.warning(
                        f"Anomaly detected for meter {meter_id}: "
                        f"max={max_val}, mean={mean_val:.2f}"
                    )

            # Persist readings batch
            batch_doc = {
                "id": hashlib.md5(
                    f"{meter_id}-{datetime.utcnow().isoformat()}".encode()
                ).hexdigest(),
                "meter_id": meter_id,
                "readings": readings,
                "count": len(readings),
                "ingested_at": datetime.utcnow().isoformat()
            }
            container.create_item(body=batch_doc)

    except Exception as e:
        logger.error(f"Error processing meter readings: {e}", exc_info=True)
        raise


# ==============================================================================
# IoT Hub Trigger - Device Telemetry Processing
# ==============================================================================

@app.function_name(name="GridDeviceTelemetry")
@app.event_hub_message_trigger(
    arg_name="event",
    event_hub_name="grid-telemetry",
    connection="IOT_HUB_CONNECTION",
    cardinality="one"
)
async def grid_device_telemetry(event: func.EventHubEvent):
    """
    Process device telemetry from IoT Hub (grid sensors, transformers, switches).
    Evaluates readings against thresholds and triggers outage alerts.
    """
    try:
        telemetry = json.loads(event.get_body().decode("utf-8"))
        device_id = telemetry.get("device_id", "unknown")
        device_type = telemetry.get("device_type", "sensor")
        readings = telemetry.get("readings", {})

        logger.info(f"Telemetry from {device_type} device {device_id}")

        # Evaluate critical thresholds
        alerts = []
        if device_type == "transformer":
            temp = readings.get("temperature_c", 0)
            oil_level = readings.get("oil_level_pct", 100)
            if temp > 85:
                alerts.append({"type": "overheating", "value": temp, "threshold": 85})
            if oil_level < 20:
                alerts.append({"type": "low_oil", "value": oil_level, "threshold": 20})

        elif device_type == "line_sensor":
            sag = readings.get("line_sag_mm", 0)
            current = readings.get("current_a", 0)
            if sag > 500:
                alerts.append({"type": "excessive_sag", "value": sag, "threshold": 500})
            if current > readings.get("rated_current_a", 1000):
                alerts.append({"type": "overcurrent", "value": current, "threshold": readings.get("rated_current_a", 1000)})

        elif device_type == "switch":
            operation_count = readings.get("operation_count", 0)
            if operation_count > readings.get("max_operations", 10000):
                alerts.append({"type": "maintenance_due", "value": operation_count})

        # Persist telemetry
        container = get_cosmos_container("deviceTelemetry")
        doc = {
            "id": hashlib.md5(
                f"{device_id}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest(),
            "device_id": device_id,
            "device_type": device_type,
            "readings": readings,
            "alerts": alerts,
            "alert_count": len(alerts),
            "received_at": datetime.utcnow().isoformat()
        }
        container.create_item(body=doc)

        if alerts:
            logger.warning(
                f"Device {device_id} generated {len(alerts)} alerts: "
                f"{[a['type'] for a in alerts]}"
            )

    except Exception as e:
        logger.error(f"Error processing device telemetry: {e}", exc_info=True)
        raise
