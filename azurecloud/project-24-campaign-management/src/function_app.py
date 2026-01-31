"""
AI Campaign Management Platform - Azure Functions
==================================================
Main orchestration functions for GenAI-powered campaign creation,
audience segmentation, content generation, and performance optimization.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
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
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    ML_ENDPOINT = os.getenv("ML_ENDPOINT")
    COMMUNICATION_ENDPOINT = os.getenv("COMMUNICATION_ENDPOINT")

    # Model configurations
    GPT_MODEL = "gpt-4o"

    # Campaign parameters
    MAX_CONTENT_VARIANTS = 5
    DEFAULT_CONFIDENCE_THRESHOLD = 0.95
    MAX_TOKENS = 4096
    TEMPERATURE = 0.7


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
    database = _cosmos_client.get_database_client("campaignmanagement")
    return database.get_container_client(container_name)


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def create_campaign(brief: str, objectives: list[str]) -> dict:
    """
    GenAI-assisted campaign creation with content variants.

    Args:
        brief: Campaign brief describing the product/service and goals
        objectives: List of campaign objectives (awareness, conversion, etc.)

    Returns:
        Campaign plan with strategy, timeline, and content variants
    """
    client = get_openai_client()

    system_prompt = """You are an expert marketing strategist. Given a campaign brief
and objectives, produce a comprehensive campaign plan in JSON with keys:
- campaign_name: catchy campaign name
- strategy: high-level strategy summary
- target_channels: list of recommended channels (email, sms, push, in_app, social)
- timeline_days: suggested campaign duration in days
- content_variants: list of up to 5 variant objects each with headline, body_preview, cta
- kpi_targets: dict of KPI name to target value
- estimated_reach: estimated audience reach number
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Brief: {brief}\nObjectives: {', '.join(objectives)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    campaign_plan = json.loads(response.choices[0].message.content)

    campaign_id = hashlib.md5(
        f"{brief}-{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()

    campaign_record = {
        "id": campaign_id,
        "brief": brief,
        "objectives": objectives,
        "plan": campaign_plan,
        "status": "draft",
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

    container = get_cosmos_container("campaigns")
    container.create_item(body=campaign_record)

    logger.info(f"Campaign created: {campaign_id}")
    return campaign_record


def segment_audience(criteria: dict, campaign_type: str) -> dict:
    """
    AI audience segmentation with propensity scoring.

    Args:
        criteria: Segmentation criteria (demographics, behaviour, etc.)
        campaign_type: Type of campaign (acquisition, retention, upsell, winback)

    Returns:
        Audience segments with propensity scores and recommended actions
    """
    client = get_openai_client()

    system_prompt = """You are a customer analytics expert. Given segmentation criteria
and campaign type, produce audience segments in JSON with keys:
- segments: list of segment objects each with:
    - segment_name: descriptive name
    - description: who is in this segment
    - estimated_size: estimated number of users
    - propensity_score: float 0-1 likelihood of conversion
    - recommended_channel: best channel to reach this segment
    - recommended_frequency: messaging frequency suggestion
    - exclusion_rules: list of exclusion criteria
- total_addressable_audience: total across segments
- suppression_recommendations: list of audiences to suppress
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Criteria: {json.dumps(criteria)}\nCampaign Type: {campaign_type}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    segmentation = json.loads(response.choices[0].message.content)

    segmentation_id = hashlib.md5(
        f"seg-{campaign_type}-{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()

    return {
        "id": segmentation_id,
        "criteria": criteria,
        "campaign_type": campaign_type,
        "result": segmentation,
        "createdAt": datetime.utcnow().isoformat()
    }


def generate_campaign_content(campaign_data: dict, channel: str) -> dict:
    """
    GenAI content generation for email, SMS, push, and in-app per channel.

    Args:
        campaign_data: Campaign details including brief, audience, and tone
        channel: Target channel (email, sms, push, in_app)

    Returns:
        Generated content variants tailored to the channel
    """
    client = get_openai_client()

    channel_specs = {
        "email": "Generate email content with subject line (max 60 chars), preview text (max 90 chars), headline, body (HTML-friendly), and CTA button text.",
        "sms": "Generate SMS content (max 160 chars) with a clear CTA and opt-out notice placeholder.",
        "push": "Generate push notification with title (max 40 chars) and body (max 120 chars) with urgency.",
        "in_app": "Generate in-app message with headline (max 30 chars), body (max 150 chars), primary CTA, and optional secondary CTA."
    }

    spec = channel_specs.get(channel, channel_specs["email"])

    system_prompt = f"""You are a world-class copywriter specializing in {channel} marketing.
{spec}
Return JSON with keys:
- variants: list of {Config.MAX_CONTENT_VARIANTS} content variant objects
- personalization_tokens: list of recommended personalization fields
- compliance_notes: any regulatory notes for this channel
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Campaign: {json.dumps(campaign_data)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.8,
        response_format={"type": "json_object"}
    )

    content = json.loads(response.choices[0].message.content)

    return {
        "channel": channel,
        "content": content,
        "generatedAt": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def optimize_ab_test(test_data: dict) -> dict:
    """
    A/B test analysis and winner selection using statistical methods.

    Args:
        test_data: Dict with variant_a and variant_b performance metrics

    Returns:
        Analysis result with winner, confidence, and recommendations
    """
    client = get_openai_client()

    system_prompt = """You are a statistician specializing in marketing experimentation.
Analyze A/B test results and provide a recommendation in JSON with keys:
- winner: "variant_a", "variant_b", or "no_winner"
- confidence_level: float 0-1 representing statistical confidence
- lift_percentage: percentage improvement of winner over loser
- sample_size_adequate: boolean indicating if sample size is sufficient
- metric_analysis: dict of each metric with p_value and effect_size
- recommendation: actionable recommendation text
- next_steps: list of suggested follow-up actions
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Test Data: {json.dumps(test_data)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    analysis = json.loads(response.choices[0].message.content)

    return {
        "test_data": test_data,
        "analysis": analysis,
        "analyzedAt": datetime.utcnow().isoformat()
    }


def predict_campaign_roi(campaign_data: dict) -> dict:
    """
    Predictive ROI modeling for campaign planning.

    Args:
        campaign_data: Campaign details including budget, channels, and audience

    Returns:
        ROI predictions with confidence intervals and scenario analysis
    """
    client = get_openai_client()

    system_prompt = """You are a marketing analytics expert. Given campaign parameters,
predict ROI outcomes in JSON with keys:
- predicted_roi: float representing expected return on investment
- confidence_interval: dict with lower and upper bounds
- scenario_analysis: list of scenarios (optimistic, baseline, pessimistic) each with roi, revenue, cost
- key_drivers: list of factors most impacting ROI
- risk_factors: list of risks that could reduce ROI
- break_even_point: dict with days and spend to break even
- ltv_impact: estimated long-term value impact
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Campaign Data: {json.dumps(campaign_data)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    prediction = json.loads(response.choices[0].message.content)

    return {
        "campaign_data": campaign_data,
        "prediction": prediction,
        "predictedAt": datetime.utcnow().isoformat()
    }


def allocate_budget(campaigns: list[dict], total_budget: float) -> dict:
    """
    AI-optimized budget allocation across campaigns.

    Args:
        campaigns: List of campaign dicts with expected performance metrics
        total_budget: Total budget to allocate

    Returns:
        Optimized budget allocation per campaign with rationale
    """
    client = get_openai_client()

    system_prompt = f"""You are a marketing budget optimization expert. Given a set of
campaigns and a total budget of {total_budget}, allocate budget to maximize overall ROI.
Return JSON with keys:
- allocations: list of objects with campaign_id, allocated_budget, percentage, expected_roi
- total_expected_roi: aggregate ROI across all campaigns
- optimization_rationale: explanation of allocation strategy
- rebalancing_triggers: list of conditions that should trigger reallocation
- diminishing_returns_thresholds: dict of campaign_id to max effective spend
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Campaigns: {json.dumps(campaigns)}\nTotal Budget: {total_budget}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    allocation = json.loads(response.choices[0].message.content)

    return {
        "total_budget": total_budget,
        "campaign_count": len(campaigns),
        "allocation": allocation,
        "allocatedAt": datetime.utcnow().isoformat()
    }


def analyze_campaign_performance(campaign_id: str) -> dict:
    """
    Performance analytics with GenAI insights for a campaign.

    Args:
        campaign_id: Unique campaign identifier

    Returns:
        Performance metrics, trends, and AI-generated insights
    """
    container = get_cosmos_container("campaigns")

    try:
        campaign = container.read_item(item=campaign_id, partition_key=campaign_id)
    except Exception:
        return {"error": f"Campaign {campaign_id} not found"}

    events_container = get_cosmos_container("campaignEvents")
    events_query = "SELECT * FROM c WHERE c.campaignId = @campaignId"
    events = list(events_container.query_items(
        query=events_query,
        parameters=[{"name": "@campaignId", "value": campaign_id}],
        enable_cross_partition_query=True
    ))

    metrics = {
        "total_sends": sum(1 for e in events if e.get("type") == "send"),
        "total_opens": sum(1 for e in events if e.get("type") == "open"),
        "total_clicks": sum(1 for e in events if e.get("type") == "click"),
        "total_conversions": sum(1 for e in events if e.get("type") == "conversion"),
        "total_unsubscribes": sum(1 for e in events if e.get("type") == "unsubscribe")
    }

    if metrics["total_sends"] > 0:
        metrics["open_rate"] = metrics["total_opens"] / metrics["total_sends"]
        metrics["click_rate"] = metrics["total_clicks"] / metrics["total_sends"]
        metrics["conversion_rate"] = metrics["total_conversions"] / metrics["total_sends"]
        metrics["unsubscribe_rate"] = metrics["total_unsubscribes"] / metrics["total_sends"]

    client = get_openai_client()
    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": "You are a campaign analytics expert. Analyze metrics and provide insights in JSON with keys: summary, strengths, weaknesses, recommendations, trend_analysis."},
            {"role": "user", "content": f"Campaign: {json.dumps(campaign.get('plan', {}))}\nMetrics: {json.dumps(metrics)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    insights = json.loads(response.choices[0].message.content)

    return {
        "campaign_id": campaign_id,
        "metrics": metrics,
        "insights": insights,
        "analyzedAt": datetime.utcnow().isoformat()
    }


def map_customer_journey(customer_id: str) -> dict:
    """
    Customer journey visualization data.

    Args:
        customer_id: Unique customer identifier

    Returns:
        Journey map with touchpoints, channels, and engagement timeline
    """
    container = get_cosmos_container("campaignEvents")

    query = "SELECT * FROM c WHERE c.customerId = @customerId ORDER BY c.timestamp ASC"
    touchpoints = list(container.query_items(
        query=query,
        parameters=[{"name": "@customerId", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    journey_stages = []
    for tp in touchpoints:
        journey_stages.append({
            "timestamp": tp.get("timestamp"),
            "channel": tp.get("channel"),
            "event_type": tp.get("type"),
            "campaign_id": tp.get("campaignId"),
            "content_variant": tp.get("variant"),
            "device": tp.get("device", "unknown")
        })

    client = get_openai_client()
    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": "Analyze the customer journey and return JSON with keys: journey_summary, current_stage (awareness/consideration/decision/retention), engagement_score (0-100), next_best_action, channel_preference, churn_risk (low/medium/high)."},
            {"role": "user", "content": f"Touchpoints: {json.dumps(journey_stages)}"}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    analysis = json.loads(response.choices[0].message.content)

    return {
        "customer_id": customer_id,
        "touchpoints": journey_stages,
        "analysis": analysis,
        "mappedAt": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="create-campaign", methods=["POST"])
async def create_campaign_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new AI-assisted marketing campaign."""
    try:
        req_body = req.get_json()
        brief = req_body.get("brief")
        objectives = req_body.get("objectives", [])

        if not brief:
            return func.HttpResponse(
                json.dumps({"error": "Campaign brief is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Creating campaign from brief: {brief[:50]}...")
        result = create_campaign(brief, objectives)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating campaign: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="segment-audience", methods=["POST"])
async def segment_audience_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Segment audience using AI-driven propensity scoring."""
    try:
        req_body = req.get_json()
        criteria = req_body.get("criteria", {})
        campaign_type = req_body.get("campaign_type", "acquisition")

        if not criteria:
            return func.HttpResponse(
                json.dumps({"error": "Segmentation criteria are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Segmenting audience for campaign type: {campaign_type}")
        result = segment_audience(criteria, campaign_type)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error segmenting audience: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="generate-content", methods=["POST"])
async def generate_content_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Generate channel-specific campaign content using GenAI."""
    try:
        req_body = req.get_json()
        campaign_data = req_body.get("campaign_data", {})
        channel = req_body.get("channel", "email")

        if not campaign_data:
            return func.HttpResponse(
                json.dumps({"error": "Campaign data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating {channel} content for campaign")
        result = generate_campaign_content(campaign_data, channel)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating content: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="optimize-ab", methods=["POST"])
async def optimize_ab_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Analyze A/B test results and select a winner."""
    try:
        req_body = req.get_json()
        test_data = req_body.get("test_data", {})

        if not test_data:
            return func.HttpResponse(
                json.dumps({"error": "Test data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Analyzing A/B test results")
        result = optimize_ab_test(test_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error optimizing A/B test: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="predict-roi", methods=["POST"])
async def predict_roi_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Predict campaign ROI with scenario analysis."""
    try:
        req_body = req.get_json()
        campaign_data = req_body.get("campaign_data", {})

        if not campaign_data:
            return func.HttpResponse(
                json.dumps({"error": "Campaign data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Predicting campaign ROI")
        result = predict_campaign_roi(campaign_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error predicting ROI: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="allocate-budget", methods=["POST"])
async def allocate_budget_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Optimize budget allocation across campaigns."""
    try:
        req_body = req.get_json()
        campaigns = req_body.get("campaigns", [])
        total_budget = req_body.get("total_budget", 0)

        if not campaigns or total_budget <= 0:
            return func.HttpResponse(
                json.dumps({"error": "Campaigns list and positive total_budget are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Allocating budget of {total_budget} across {len(campaigns)} campaigns")
        result = allocate_budget(campaigns, total_budget)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error allocating budget: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="performance", methods=["POST"])
async def performance_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Analyze campaign performance with AI-generated insights."""
    try:
        req_body = req.get_json()
        campaign_id = req_body.get("campaign_id")

        if not campaign_id:
            return func.HttpResponse(
                json.dumps({"error": "campaign_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing performance for campaign: {campaign_id}")
        result = analyze_campaign_performance(campaign_id)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error analyzing performance: {e}", exc_info=True)
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
            "service": "ai-campaign-management",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger for Real-Time Campaign Event Processing
# ==============================================================================

@app.function_name(name="CampaignEventProcessor")
@app.event_hub_message_trigger(
    arg_name="event",
    event_hub_name="campaign-events",
    connection="EVENT_HUB_CONNECTION"
)
async def campaign_event_processor(event: func.EventHubEvent):
    """
    Triggered by real-time campaign events from Event Hub.
    Processes send, open, click, conversion, and unsubscribe events
    to update campaign metrics and trigger automated actions.
    """
    try:
        event_body = json.loads(event.get_body().decode("utf-8"))
        event_type = event_body.get("type")
        campaign_id = event_body.get("campaignId")
        customer_id = event_body.get("customerId")

        logger.info(f"Processing campaign event: {event_type} for campaign {campaign_id}")

        # Persist event to Cosmos DB
        container = get_cosmos_container("campaignEvents")
        event_record = {
            "id": hashlib.md5(
                f"{campaign_id}-{customer_id}-{event_type}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest(),
            "campaignId": campaign_id,
            "customerId": customer_id,
            "type": event_type,
            "channel": event_body.get("channel"),
            "variant": event_body.get("variant"),
            "device": event_body.get("device", "unknown"),
            "metadata": event_body.get("metadata", {}),
            "timestamp": event_body.get("timestamp", datetime.utcnow().isoformat()),
            "processedAt": datetime.utcnow().isoformat()
        }
        container.create_item(body=event_record)

        # Trigger automated actions based on event type
        if event_type == "unsubscribe":
            logger.info(f"Customer {customer_id} unsubscribed from campaign {campaign_id}")
            # Suppress customer from future sends in this campaign
            campaigns_container = get_cosmos_container("campaigns")
            try:
                campaign = campaigns_container.read_item(
                    item=campaign_id, partition_key=campaign_id
                )
                suppressions = campaign.get("suppressions", [])
                if customer_id not in suppressions:
                    suppressions.append(customer_id)
                    campaign["suppressions"] = suppressions
                    campaign["updatedAt"] = datetime.utcnow().isoformat()
                    campaigns_container.replace_item(item=campaign_id, body=campaign)
            except Exception as suppress_err:
                logger.warning(f"Failed to update suppression list: {suppress_err}")

        elif event_type == "conversion":
            logger.info(f"Conversion recorded for customer {customer_id} in campaign {campaign_id}")

        logger.info(f"Campaign event processed successfully: {event_record['id']}")

    except Exception as e:
        logger.error(f"Error processing campaign event: {e}", exc_info=True)
        raise
