"""
Supply Chain Optimizer - Azure Functions
========================================
Demand forecasting, inventory optimization, and supplier risk scoring
powered by Azure OpenAI and real-time supply chain event processing.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
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
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    ML_ENDPOINT = os.getenv("ML_ENDPOINT")

    # Model configurations
    GPT_MODEL = "gpt-4o"

    # Supply chain parameters
    DEFAULT_LEAD_TIME_DAYS = 14
    SAFETY_STOCK_MULTIPLIER = 1.5
    REORDER_POINT_SERVICE_LEVEL = 0.95
    RISK_SCORE_THRESHOLD = 0.7
    FORECAST_HORIZON_DAYS = 90


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
    database = _cosmos_client.get_database_client("supplychain")
    return database.get_container_client(container_name)


def get_keyvault_client() -> SecretClient:
    """Get Azure Key Vault secret client."""
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

def forecast_demand(product_id: str, historical_data: List[Dict]) -> Dict:
    """
    Use Azure OpenAI to analyze demand patterns and generate a forecast.

    Args:
        product_id: Product identifier
        historical_data: List of dicts with 'date' and 'quantity' fields

    Returns:
        Forecast result with predicted quantities and confidence intervals
    """
    client = get_openai_client()

    # Compute basic statistical features from historical data
    quantities = [entry["quantity"] for entry in historical_data]
    mean_demand = float(np.mean(quantities))
    std_demand = float(np.std(quantities))
    trend = float(np.polyfit(range(len(quantities)), quantities, 1)[0])

    system_prompt = """You are a supply chain demand forecasting analyst.
Analyze the provided historical demand data and produce a structured JSON forecast.
Consider seasonality, trend, and any anomalies in the data.

Return ONLY valid JSON with the following structure:
{
    "forecast": [{"date": "YYYY-MM-DD", "predicted_quantity": N, "lower_bound": N, "upper_bound": N}],
    "trend": "increasing|decreasing|stable",
    "seasonality_detected": true|false,
    "confidence": 0.0-1.0,
    "summary": "brief narrative"
}"""

    user_prompt = (
        f"Product: {product_id}\n"
        f"Historical data points: {len(historical_data)}\n"
        f"Mean demand: {mean_demand:.1f}, Std dev: {std_demand:.1f}, Trend slope: {trend:.3f}\n"
        f"Recent data (last 10): {json.dumps(historical_data[-10:])}\n"
        f"Forecast horizon: {Config.FORECAST_HORIZON_DAYS} days"
    )

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    forecast_result = json.loads(response.choices[0].message.content)
    forecast_result["product_id"] = product_id
    forecast_result["generated_at"] = datetime.utcnow().isoformat()
    forecast_result["statistical_features"] = {
        "mean": mean_demand,
        "std": std_demand,
        "trend_slope": trend,
        "data_points": len(historical_data)
    }

    return forecast_result


def optimize_inventory(product_id: str, current_stock: int, forecast: Dict) -> Dict:
    """
    Calculate optimal inventory levels with reorder points using forecast data.

    Args:
        product_id: Product identifier
        current_stock: Current stock quantity on hand
        forecast: Forecast output from forecast_demand()

    Returns:
        Inventory optimization recommendations
    """
    # Extract predicted quantities from forecast
    predicted_quantities = [
        entry["predicted_quantity"]
        for entry in forecast.get("forecast", [])
    ]

    if not predicted_quantities:
        return {"error": "No forecast data available for optimization"}

    daily_demand_mean = float(np.mean(predicted_quantities))
    daily_demand_std = float(np.std(predicted_quantities))
    lead_time = Config.DEFAULT_LEAD_TIME_DAYS

    # Safety stock = z-score * std(demand) * sqrt(lead_time)
    z_score = 1.65  # ~95% service level
    safety_stock = int(np.ceil(
        z_score * daily_demand_std * np.sqrt(lead_time)
    ))

    # Reorder point = (average daily demand * lead time) + safety stock
    reorder_point = int(np.ceil(daily_demand_mean * lead_time + safety_stock))

    # Economic order quantity (EOQ) approximation
    annual_demand = daily_demand_mean * 365
    holding_cost_rate = 0.25  # 25% of unit cost per year
    ordering_cost = 50.0  # flat cost per order
    unit_cost = 10.0  # placeholder unit cost
    eoq = int(np.ceil(np.sqrt(
        (2 * annual_demand * ordering_cost) / (unit_cost * holding_cost_rate)
    )))

    # Days of supply remaining
    days_of_supply = (
        int(current_stock / daily_demand_mean) if daily_demand_mean > 0 else 999
    )

    # Determine action
    if current_stock <= safety_stock:
        action = "URGENT_REORDER"
        urgency = "critical"
    elif current_stock <= reorder_point:
        action = "REORDER"
        urgency = "high"
    elif days_of_supply < lead_time * 1.5:
        action = "MONITOR"
        urgency = "medium"
    else:
        action = "ADEQUATE"
        urgency = "low"

    return {
        "product_id": product_id,
        "current_stock": current_stock,
        "daily_demand_mean": round(daily_demand_mean, 2),
        "daily_demand_std": round(daily_demand_std, 2),
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "economic_order_quantity": eoq,
        "days_of_supply": days_of_supply,
        "lead_time_days": lead_time,
        "recommended_action": action,
        "urgency": urgency,
        "optimized_at": datetime.utcnow().isoformat()
    }


def score_supplier_risk(supplier_id: str, supplier_data: Dict) -> Dict:
    """
    Generate a risk score using OpenAI analysis of supplier metrics.

    Args:
        supplier_id: Supplier identifier
        supplier_data: Dict containing supplier metrics (on_time_rate,
            quality_rate, financial_stability, geographic_risk, etc.)

    Returns:
        Risk assessment with overall score and breakdown
    """
    client = get_openai_client()

    system_prompt = """You are a supply chain risk management expert.
Analyze the supplier data and produce a structured risk assessment in JSON.

Return ONLY valid JSON:
{
    "overall_risk_score": 0.0-1.0 (1.0 = highest risk),
    "risk_category": "low|medium|high|critical",
    "risk_factors": [{"factor": "name", "score": 0.0-1.0, "detail": "explanation"}],
    "mitigation_recommendations": ["recommendation1", "recommendation2"],
    "summary": "brief narrative assessment"
}"""

    user_prompt = (
        f"Supplier ID: {supplier_id}\n"
        f"Supplier Metrics:\n{json.dumps(supplier_data, indent=2)}"
    )

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"}
    )

    risk_result = json.loads(response.choices[0].message.content)
    risk_result["supplier_id"] = supplier_id
    risk_result["assessed_at"] = datetime.utcnow().isoformat()

    # Persist assessment to Cosmos DB
    try:
        container = get_cosmos_container("supplierRiskScores")
        risk_result["id"] = hashlib.md5(
            f"{supplier_id}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        container.create_item(body=risk_result)
    except Exception as e:
        logger.warning(f"Failed to persist risk score: {e}")

    return risk_result


def generate_supply_chain_insights(data: Dict) -> Dict:
    """
    Generate GenAI narrative insights about overall supply chain health.

    Args:
        data: Aggregated supply chain data (inventory levels, supplier
              scores, demand forecasts, recent events)

    Returns:
        Narrative insights and actionable recommendations
    """
    client = get_openai_client()

    system_prompt = """You are a senior supply chain strategist providing
executive-level insights. Analyze the supply chain data and produce a
comprehensive health assessment in JSON.

Return ONLY valid JSON:
{
    "health_score": 0.0-1.0 (1.0 = excellent),
    "status": "healthy|at_risk|degraded|critical",
    "key_insights": ["insight1", "insight2", "insight3"],
    "risk_alerts": ["alert1", "alert2"],
    "recommendations": [{"priority": "high|medium|low", "action": "description"}],
    "narrative": "executive summary paragraph"
}"""

    user_prompt = f"Supply Chain Data Snapshot:\n{json.dumps(data, indent=2, default=str)}"

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    insights = json.loads(response.choices[0].message.content)
    insights["generated_at"] = datetime.utcnow().isoformat()

    return insights


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="demand-forecast", methods=["POST"])
async def demand_forecast_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Demand forecasting endpoint.

    Request Body:
    {
        "product_id": "SKU-12345",
        "historical_data": [{"date": "2024-01-01", "quantity": 100}, ...]
    }
    """
    try:
        req_body = req.get_json()
        product_id = req_body.get("product_id")
        historical_data = req_body.get("historical_data")

        if not product_id or not historical_data:
            return func.HttpResponse(
                json.dumps({"error": "product_id and historical_data are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating demand forecast for product {product_id}")

        result = forecast_demand(product_id, historical_data)

        # Persist forecast to Cosmos DB
        try:
            container = get_cosmos_container("demandForecasts")
            result["id"] = hashlib.md5(
                f"{product_id}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            container.create_item(body=result)
        except Exception as e:
            logger.warning(f"Failed to persist forecast: {e}")

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in demand forecast: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="inventory-optimize", methods=["POST"])
async def inventory_optimize_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Inventory optimization endpoint.

    Request Body:
    {
        "product_id": "SKU-12345",
        "current_stock": 500,
        "forecast": { ... forecast object from demand-forecast ... }
    }
    """
    try:
        req_body = req.get_json()
        product_id = req_body.get("product_id")
        current_stock = req_body.get("current_stock")
        forecast = req_body.get("forecast")

        if not product_id or current_stock is None or not forecast:
            return func.HttpResponse(
                json.dumps({"error": "product_id, current_stock, and forecast are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Optimizing inventory for product {product_id}")

        result = optimize_inventory(product_id, current_stock, forecast)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in inventory optimization: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="supplier-risk", methods=["POST"])
async def supplier_risk_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Supplier risk scoring endpoint.

    Request Body:
    {
        "supplier_id": "SUP-001",
        "supplier_data": {
            "on_time_delivery_rate": 0.92,
            "quality_pass_rate": 0.98,
            "financial_stability_score": 0.75,
            "geographic_risk": "medium",
            "single_source": false,
            "contract_expiry": "2025-12-31"
        }
    }
    """
    try:
        req_body = req.get_json()
        supplier_id = req_body.get("supplier_id")
        supplier_data = req_body.get("supplier_data")

        if not supplier_id or not supplier_data:
            return func.HttpResponse(
                json.dumps({"error": "supplier_id and supplier_data are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Scoring supplier risk for {supplier_id}")

        result = score_supplier_risk(supplier_id, supplier_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in supplier risk scoring: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="supply-insights", methods=["POST"])
async def supply_insights_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    GenAI supply chain insights endpoint.

    Request Body:
    {
        "inventory_summary": {...},
        "supplier_scores": [...],
        "demand_forecasts": [...],
        "recent_events": [...]
    }
    """
    try:
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Supply chain data payload is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Generating supply chain insights")

        result = generate_supply_chain_insights(req_body)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating supply insights: {e}", exc_info=True)
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
            "service": "supply-chain-optimizer",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger for Real-Time Supply Chain Events
# ==============================================================================

@app.function_name(name="SupplyChainEventProcessor")
@app.event_hub_message_trigger(
    arg_name="event",
    event_hub_name="supplychain-events",
    connection="EVENT_HUB_CONNECTION"
)
async def supply_chain_event_trigger(event: func.EventHubEvent):
    """
    Process real-time supply chain events from Event Hub.

    Events include shipment delays, stock alerts, supplier
    status changes, and quality incidents.
    """
    try:
        event_body = json.loads(event.get_body().decode("utf-8"))
        event_type = event_body.get("event_type")
        payload = event_body.get("payload", {})

        logger.info(f"Processing supply chain event: {event_type}")

        # Route event by type
        if event_type == "shipment_delay":
            logger.info(
                f"Shipment delay detected - Order: {payload.get('order_id')}, "
                f"Delay: {payload.get('delay_days')} days"
            )
            # Re-run inventory optimization for affected products
            for product_id in payload.get("affected_products", []):
                logger.info(f"Triggering re-optimization for {product_id}")

        elif event_type == "stock_alert":
            product_id = payload.get("product_id")
            current_level = payload.get("current_level")
            threshold = payload.get("threshold")
            logger.warning(
                f"Stock alert - Product: {product_id}, "
                f"Level: {current_level}, Threshold: {threshold}"
            )

        elif event_type == "supplier_status_change":
            supplier_id = payload.get("supplier_id")
            new_status = payload.get("new_status")
            logger.info(
                f"Supplier status change - Supplier: {supplier_id}, "
                f"New status: {new_status}"
            )

        elif event_type == "quality_incident":
            logger.warning(
                f"Quality incident reported - Supplier: {payload.get('supplier_id')}, "
                f"Severity: {payload.get('severity')}, "
                f"Batch: {payload.get('batch_id')}"
            )

        else:
            logger.info(f"Unhandled event type: {event_type}")

        # Persist event to Cosmos DB for audit trail
        try:
            container = get_cosmos_container("supplyChainEvents")
            event_record = {
                "id": hashlib.md5(
                    f"{event_type}-{datetime.utcnow().isoformat()}".encode()
                ).hexdigest(),
                "eventType": event_type,
                "payload": payload,
                "processedAt": datetime.utcnow().isoformat(),
                "enqueuedAt": event.enqueued_time.isoformat() if event.enqueued_time else None
            }
            container.create_item(body=event_record)
        except Exception as e:
            logger.warning(f"Failed to persist supply chain event: {e}")

        logger.info(f"Successfully processed event: {event_type}")

    except Exception as e:
        logger.error(f"Error processing supply chain event: {e}", exc_info=True)
        raise
