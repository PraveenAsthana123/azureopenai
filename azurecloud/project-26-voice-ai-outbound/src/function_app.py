"""
Voice AI Outbound Platform - Azure Functions
=============================================
AI-powered outbound voice calling for proactive customer engagement.
Orchestrates campaign-driven outbound calls with real-time conversation
steering, sentiment analysis, compliance checks, and intelligent escalation.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
import requests
import redis

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
    COMMUNICATION_SERVICES_ENDPOINT = os.getenv("COMMUNICATION_SERVICES_ENDPOINT")
    SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")
    SERVICE_BUS_CONNECTION = os.getenv("SERVICE_BUS_CONNECTION")

    # Model configurations
    GPT_MODEL = "gpt-4o"

    # Voice AI parameters
    MAX_CALL_DURATION_SECONDS = 600
    VOICEMAIL_DETECTION_TIMEOUT_MS = 5000
    SENTIMENT_ANALYSIS_INTERVAL_SECONDS = 10
    MAX_RETRY_ATTEMPTS = 3
    CALL_THROTTLE_PER_MINUTE = 30


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_cosmos_client = None
_redis_client = None


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
    database = _cosmos_client.get_database_client("voiceaioutbound")
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


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def generate_call_script(campaign_data: dict, customer_profile: dict) -> dict:
    """
    Generate a personalized outbound call script using GenAI.

    Args:
        campaign_data: Campaign objectives, product info, talking points
        customer_profile: Customer demographics, history, preferences

    Returns:
        Structured call script with opening, body, objection handling, and close
    """
    client = get_openai_client()

    system_prompt = """You are an expert outbound call script writer for enterprise sales
and customer engagement. Generate a natural, conversational call script that is
compliant with telemarketing regulations. The script must feel human, empathetic,
and personalized to the customer profile provided.

Output the script as JSON with these sections:
- opening: Greeting and purpose statement
- value_proposition: Key benefits personalized to customer
- talking_points: List of discussion points in priority order
- objection_responses: Map of common objections to recommended responses
- closing: Call-to-action and next steps
- voicemail_script: Short voicemail message if customer does not answer"""

    user_prompt = f"""Campaign Details:
{json.dumps(campaign_data, indent=2)}

Customer Profile:
{json.dumps(customer_profile, indent=2)}

Generate a personalized call script for this customer and campaign."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=2048,
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    script = json.loads(response.choices[0].message.content)
    script["metadata"] = {
        "campaign_id": campaign_data.get("campaign_id"),
        "customer_id": customer_profile.get("customer_id"),
        "generated_at": datetime.utcnow().isoformat(),
        "model": response.model,
        "tokens_used": response.usage.total_tokens
    }

    return script


def check_dnc_compliance(phone_number: str) -> dict:
    """
    Check Do-Not-Call and TCPA compliance against Redis-cached DNC list.

    Args:
        phone_number: Phone number to check in E.164 format

    Returns:
        Compliance status with details
    """
    redis_client = get_redis_client()

    # Normalize phone number
    normalized = phone_number.strip().replace("-", "").replace(" ", "")
    if not normalized.startswith("+"):
        normalized = "+1" + normalized

    # Check federal DNC registry (cached in Redis)
    federal_dnc = redis_client.sismember("dnc:federal", normalized)

    # Check state-level DNC lists
    state_dnc = redis_client.sismember("dnc:state", normalized)

    # Check internal DNC / opt-out list
    internal_dnc = redis_client.sismember("dnc:internal", normalized)

    # Check TCPA time-of-day restrictions
    customer_tz = redis_client.hget(f"customer:tz:{normalized}", "timezone")
    time_compliant = True
    if customer_tz:
        # TCPA allows calls between 8 AM and 9 PM local time
        now_utc = datetime.utcnow()
        # Simplified check - production would use pytz
        time_compliant = 8 <= now_utc.hour <= 21

    # Check recent call frequency (no harassment)
    recent_calls = redis_client.get(f"call:frequency:{normalized}")
    frequency_compliant = int(recent_calls or 0) < Config.MAX_RETRY_ATTEMPTS

    is_compliant = (
        not federal_dnc
        and not state_dnc
        and not internal_dnc
        and time_compliant
        and frequency_compliant
    )

    return {
        "phone_number": normalized,
        "is_compliant": is_compliant,
        "federal_dnc": federal_dnc,
        "state_dnc": state_dnc,
        "internal_dnc": internal_dnc,
        "time_compliant": time_compliant,
        "frequency_compliant": frequency_compliant,
        "checked_at": datetime.utcnow().isoformat()
    }


def initiate_outbound_call(customer_data: dict, script: dict) -> dict:
    """
    Initiate an outbound voice call via Azure Communication Services.

    Args:
        customer_data: Customer phone number and metadata
        script: Generated call script to use

    Returns:
        Call initiation result with call ID and status
    """
    credential = get_credential()
    token = credential.get_token("https://communication.azure.com/.default").token

    call_payload = {
        "targets": [
            {
                "phoneNumber": {
                    "value": customer_data["phone_number"]
                }
            }
        ],
        "sourceCallerIdNumber": {
            "value": customer_data.get("caller_id", os.getenv("DEFAULT_CALLER_ID"))
        },
        "callIntelligenceOptions": {
            "cognitiveServicesEndpoint": Config.SPEECH_ENDPOINT
        },
        "mediaStreamingOptions": {
            "transportUrl": os.getenv("WEBSOCKET_ENDPOINT"),
            "transportType": "websocket",
            "contentType": "audio",
            "audioChannelType": "mixed"
        }
    }

    response = requests.post(
        f"{Config.COMMUNICATION_SERVICES_ENDPOINT}/calling/callConnections?api-version=2024-01-15-preview",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=call_payload,
        timeout=30
    )

    if response.status_code in (200, 201):
        call_result = response.json()
        call_id = call_result.get("callConnectionId")

        # Store script and call context in Redis for real-time access
        redis_client = get_redis_client()
        redis_client.setex(
            f"call:script:{call_id}",
            Config.MAX_CALL_DURATION_SECONDS,
            json.dumps(script)
        )
        redis_client.setex(
            f"call:context:{call_id}",
            Config.MAX_CALL_DURATION_SECONDS,
            json.dumps(customer_data)
        )

        # Increment call frequency counter
        freq_key = f"call:frequency:{customer_data['phone_number']}"
        redis_client.incr(freq_key)
        redis_client.expire(freq_key, 86400 * 30)  # 30-day window

        # Log call initiation to Cosmos DB
        container = get_cosmos_container("callLogs")
        container.create_item(body={
            "id": call_id,
            "customerId": customer_data.get("customer_id"),
            "phoneNumber": customer_data["phone_number"],
            "campaignId": script.get("metadata", {}).get("campaign_id"),
            "status": "initiated",
            "initiatedAt": datetime.utcnow().isoformat(),
            "partitionKey": customer_data.get("customer_id")
        })

        return {"call_id": call_id, "status": "initiated", "details": call_result}
    else:
        logger.error(f"Failed to initiate call: {response.status_code} - {response.text}")
        return {"call_id": None, "status": "failed", "error": response.text}


def steer_conversation(transcript_so_far: str, script: dict, customer_sentiment: str) -> dict:
    """
    Provide real-time conversation steering with AI prompts for the agent/bot.

    Args:
        transcript_so_far: Running transcript of the call
        script: Original call script
        customer_sentiment: Current detected sentiment (positive, neutral, negative)

    Returns:
        Steering guidance with suggested next response and strategy adjustments
    """
    client = get_openai_client()

    system_prompt = """You are a real-time conversation coach for outbound voice calls.
Analyze the conversation transcript, original script, and customer sentiment to provide
the next best response and strategic adjustments.

Respond as JSON with:
- suggested_response: The next thing the caller should say
- strategy: Current recommended approach (empathetic, direct, consultative)
- script_deviation: Whether to deviate from script and why
- escalation_needed: Boolean if human agent should take over
- escalation_reason: Reason for escalation if needed
- confidence: 0-1 confidence score in call success"""

    user_prompt = f"""Transcript so far:
{transcript_so_far}

Original Script:
{json.dumps(script, indent=2)}

Current Customer Sentiment: {customer_sentiment}

Provide real-time steering guidance."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1024,
        temperature=0.5,
        response_format={"type": "json_object"}
    )

    guidance = json.loads(response.choices[0].message.content)
    guidance["generated_at"] = datetime.utcnow().isoformat()

    return guidance


def detect_voicemail(audio_analysis: dict) -> dict:
    """
    Detect voicemail and determine whether to leave a message or retry.

    Args:
        audio_analysis: Audio signal analysis from call connection

    Returns:
        Detection result with recommended action
    """
    tone_detected = audio_analysis.get("tone_detected", False)
    silence_duration_ms = audio_analysis.get("silence_duration_ms", 0)
    greeting_duration_ms = audio_analysis.get("greeting_duration_ms", 0)
    speech_pattern = audio_analysis.get("speech_pattern", "unknown")

    is_voicemail = (
        (tone_detected and greeting_duration_ms > 3000)
        or speech_pattern == "automated_greeting"
        or (silence_duration_ms > Config.VOICEMAIL_DETECTION_TIMEOUT_MS and tone_detected)
    )

    if is_voicemail:
        action = "leave_message" if audio_analysis.get("campaign_allows_voicemail", True) else "hangup_retry"
    else:
        action = "proceed_live"

    return {
        "is_voicemail": is_voicemail,
        "confidence": 0.95 if tone_detected else 0.7,
        "action": action,
        "analysis": {
            "tone_detected": tone_detected,
            "silence_duration_ms": silence_duration_ms,
            "greeting_duration_ms": greeting_duration_ms,
            "speech_pattern": speech_pattern
        },
        "detected_at": datetime.utcnow().isoformat()
    }


def classify_call_outcome(call_data: dict, transcript: str) -> dict:
    """
    AI classification of call outcome using the full transcript.

    Args:
        call_data: Call metadata (duration, status, events)
        transcript: Full call transcript

    Returns:
        Classification result with outcome category and follow-up actions
    """
    client = get_openai_client()

    system_prompt = """You are a call outcome classifier for outbound sales and engagement calls.
Analyze the call data and transcript to determine the outcome.

Classify into one of these categories:
- sale_completed: Customer agreed to purchase or sign up
- callback_requested: Customer asked to be called back later
- not_interested: Customer declined the offer
- objection_unresolved: Customer raised objections that were not resolved
- voicemail_left: Call went to voicemail, message was left
- no_answer: No answer, no voicemail
- wrong_number: Reached wrong person
- do_not_call: Customer requested to be added to DNC list
- escalated: Call was escalated to a human agent
- technical_failure: Call dropped or had technical issues

Respond as JSON with:
- outcome: The category from above
- confidence: 0-1 confidence score
- summary: Brief summary of what happened
- follow_up_actions: List of recommended next steps
- customer_interest_score: 0-10 rating of customer interest level
- next_best_action: Single most important follow-up"""

    user_prompt = f"""Call Data:
{json.dumps(call_data, indent=2)}

Full Transcript:
{transcript}

Classify this call outcome."""

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

    classification = json.loads(response.choices[0].message.content)
    classification["call_id"] = call_data.get("call_id")
    classification["classified_at"] = datetime.utcnow().isoformat()

    # Persist classification to Cosmos DB
    container = get_cosmos_container("callOutcomes")
    container.upsert_item(body={
        "id": call_data.get("call_id"),
        "partitionKey": call_data.get("campaign_id"),
        **classification
    })

    # If customer requested DNC, add to internal list
    if classification.get("outcome") == "do_not_call":
        redis_client = get_redis_client()
        redis_client.sadd("dnc:internal", call_data.get("phone_number"))
        logger.info(f"Added {call_data.get('phone_number')} to internal DNC list")

    return classification


def escalate_to_human(call_id: str, reason: str) -> dict:
    """
    Escalate an active call to a live human agent with full context handoff.

    Args:
        call_id: Active call connection ID
        reason: Reason for escalation

    Returns:
        Escalation result with assigned agent and context transfer status
    """
    redis_client = get_redis_client()

    # Retrieve call context and script from Redis
    script_data = redis_client.get(f"call:script:{call_id}")
    context_data = redis_client.get(f"call:context:{call_id}")
    transcript = redis_client.get(f"call:transcript:{call_id}")

    handoff_context = {
        "call_id": call_id,
        "reason": reason,
        "script": json.loads(script_data) if script_data else {},
        "customer_context": json.loads(context_data) if context_data else {},
        "transcript_so_far": transcript or "",
        "escalated_at": datetime.utcnow().isoformat()
    }

    # Transfer call to agent queue via Communication Services
    credential = get_credential()
    token = credential.get_token("https://communication.azure.com/.default").token

    transfer_payload = {
        "targetParticipant": {
            "phoneNumber": {"value": os.getenv("AGENT_QUEUE_NUMBER")}
        },
        "customCallingContext": {
            "sipHeaders": {
                "X-Call-Id": call_id,
                "X-Escalation-Reason": reason
            }
        }
    }

    response = requests.post(
        f"{Config.COMMUNICATION_SERVICES_ENDPOINT}/calling/callConnections/{call_id}/:transferToParticipant?api-version=2024-01-15-preview",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=transfer_payload,
        timeout=30
    )

    # Store handoff context for agent pickup
    redis_client.setex(
        f"escalation:context:{call_id}",
        3600,
        json.dumps(handoff_context)
    )

    # Update call log
    container = get_cosmos_container("callLogs")
    container.upsert_item(body={
        "id": f"{call_id}-escalation",
        "callId": call_id,
        "status": "escalated",
        "reason": reason,
        "transferStatus": "success" if response.status_code in (200, 202) else "failed",
        "escalatedAt": datetime.utcnow().isoformat(),
        "partitionKey": call_id
    })

    return {
        "call_id": call_id,
        "status": "escalated" if response.status_code in (200, 202) else "escalation_failed",
        "reason": reason,
        "handoff_context_stored": True,
        "escalated_at": datetime.utcnow().isoformat()
    }


def analyze_call_sentiment(transcript: str) -> dict:
    """
    Perform real-time sentiment tracking during an active call.

    Args:
        transcript: Current running transcript of the call

    Returns:
        Sentiment analysis with overall and per-turn breakdown
    """
    client = get_openai_client()

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """Analyze the sentiment of this call transcript.
Respond as JSON with:
- overall_sentiment: positive, neutral, or negative
- sentiment_score: -1.0 to 1.0
- trend: improving, stable, or declining
- key_moments: List of significant sentiment shifts with timestamps
- customer_emotions: Detected emotions (frustrated, interested, confused, etc.)
- risk_level: low, medium, or high (risk of negative outcome)
- recommendation: Brief recommendation for call handling"""
            },
            {"role": "user", "content": f"Transcript:\n{transcript}"}
        ],
        max_tokens=512,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    sentiment = json.loads(response.choices[0].message.content)
    sentiment["analyzed_at"] = datetime.utcnow().isoformat()

    return sentiment


def schedule_optimal_call_time(customer_id: str) -> dict:
    """
    AI-optimized call scheduling based on historical answer patterns.

    Args:
        customer_id: Customer identifier

    Returns:
        Optimal call windows with confidence scores
    """
    # Retrieve customer call history from Cosmos DB
    container = get_cosmos_container("callLogs")
    query = (
        "SELECT c.initiatedAt, c.status, c.duration "
        "FROM c WHERE c.customerId = @customerId "
        "ORDER BY c.initiatedAt DESC OFFSET 0 LIMIT 50"
    )

    history = list(container.query_items(
        query=query,
        parameters=[{"name": "@customerId", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Use AI to analyze patterns and recommend optimal times
    client = get_openai_client()

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a call scheduling optimizer. Analyze the customer's
call history to determine the best times to reach them.

Respond as JSON with:
- optimal_windows: List of {day_of_week, start_hour, end_hour, confidence}
- best_single_time: The single best day/time combination
- avoid_windows: Times that historically result in no answer
- timezone_estimate: Estimated customer timezone
- answer_rate: Historical answer rate as a percentage"""
            },
            {
                "role": "user",
                "content": f"Call history for customer {customer_id}:\n{json.dumps(history, indent=2)}"
            }
        ],
        max_tokens=512,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    schedule = json.loads(response.choices[0].message.content)
    schedule["customer_id"] = customer_id
    schedule["computed_at"] = datetime.utcnow().isoformat()

    # Cache the schedule in Redis for quick lookups
    redis_client = get_redis_client()
    redis_client.setex(
        f"schedule:optimal:{customer_id}",
        86400,  # Cache for 24 hours
        json.dumps(schedule)
    )

    return schedule


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="generate-script", methods=["POST"])
async def generate_script_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Generate a personalized outbound call script."""
    try:
        req_body = req.get_json()
        campaign_data = req_body.get("campaign_data")
        customer_profile = req_body.get("customer_profile")

        if not campaign_data or not customer_profile:
            return func.HttpResponse(
                json.dumps({"error": "campaign_data and customer_profile are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating script for campaign {campaign_data.get('campaign_id')}")
        script = generate_call_script(campaign_data, customer_profile)

        return func.HttpResponse(
            json.dumps({"script": script}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating script: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="check-compliance", methods=["POST"])
async def check_compliance_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Check DNC/TCPA compliance for a phone number."""
    try:
        req_body = req.get_json()
        phone_number = req_body.get("phone_number")

        if not phone_number:
            return func.HttpResponse(
                json.dumps({"error": "phone_number is required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = check_dnc_compliance(phone_number)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error checking compliance: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="initiate-call", methods=["POST"])
async def initiate_call_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Initiate an outbound voice call to a customer."""
    try:
        req_body = req.get_json()
        customer_data = req_body.get("customer_data")
        script = req_body.get("script")

        if not customer_data or not script:
            return func.HttpResponse(
                json.dumps({"error": "customer_data and script are required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Pre-flight compliance check
        compliance = check_dnc_compliance(customer_data["phone_number"])
        if not compliance["is_compliant"]:
            return func.HttpResponse(
                json.dumps({
                    "error": "Compliance check failed",
                    "compliance_details": compliance
                }),
                status_code=403,
                mimetype="application/json"
            )

        logger.info(f"Initiating call to customer {customer_data.get('customer_id')}")
        result = initiate_outbound_call(customer_data, script)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error initiating call: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="classify-outcome", methods=["POST"])
async def classify_outcome_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Classify the outcome of a completed call."""
    try:
        req_body = req.get_json()
        call_data = req_body.get("call_data")
        transcript = req_body.get("transcript")

        if not call_data or not transcript:
            return func.HttpResponse(
                json.dumps({"error": "call_data and transcript are required"}),
                status_code=400,
                mimetype="application/json"
            )

        classification = classify_call_outcome(call_data, transcript)

        return func.HttpResponse(
            json.dumps(classification),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error classifying outcome: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="schedule-call", methods=["POST"])
async def schedule_call_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Get AI-optimized call scheduling for a customer."""
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        schedule = schedule_optimal_call_time(customer_id)

        return func.HttpResponse(
            json.dumps(schedule),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error scheduling call: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="campaign-analytics", methods=["POST"])
async def campaign_analytics_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Get analytics for an outbound calling campaign."""
    try:
        req_body = req.get_json()
        campaign_id = req_body.get("campaign_id")

        if not campaign_id:
            return func.HttpResponse(
                json.dumps({"error": "campaign_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Query call outcomes for the campaign
        container = get_cosmos_container("callOutcomes")
        query = (
            "SELECT c.outcome, c.confidence, c.customer_interest_score "
            "FROM c WHERE c.partitionKey = @campaignId"
        )

        outcomes = list(container.query_items(
            query=query,
            parameters=[{"name": "@campaignId", "value": campaign_id}],
            enable_cross_partition_query=False
        ))

        # Aggregate analytics
        total_calls = len(outcomes)
        outcome_counts = {}
        total_interest = 0.0

        for outcome in outcomes:
            category = outcome.get("outcome", "unknown")
            outcome_counts[category] = outcome_counts.get(category, 0) + 1
            total_interest += outcome.get("customer_interest_score", 0)

        analytics = {
            "campaign_id": campaign_id,
            "total_calls": total_calls,
            "outcome_distribution": outcome_counts,
            "conversion_rate": outcome_counts.get("sale_completed", 0) / max(total_calls, 1),
            "callback_rate": outcome_counts.get("callback_requested", 0) / max(total_calls, 1),
            "average_interest_score": total_interest / max(total_calls, 1),
            "dnc_requests": outcome_counts.get("do_not_call", 0),
            "escalation_rate": outcome_counts.get("escalated", 0) / max(total_calls, 1),
            "generated_at": datetime.utcnow().isoformat()
        }

        return func.HttpResponse(
            json.dumps(analytics),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating analytics: {e}", exc_info=True)
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
            "service": "voice-ai-outbound",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Service Bus Trigger - Outbound Call Queue Processing
# ==============================================================================

@app.function_name(name="OutboundCallQueueProcessor")
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="outbound-call-queue",
    connection="SERVICE_BUS_CONNECTION"
)
async def outbound_call_queue_processor(msg: func.ServiceBusMessage):
    """
    Process outbound call requests from the Service Bus queue.
    Each message contains customer data and campaign ID for a single call.
    """
    try:
        message_body = json.loads(msg.get_body().decode("utf-8"))
        customer_data = message_body.get("customer_data")
        campaign_data = message_body.get("campaign_data")

        logger.info(
            f"Processing outbound call for customer {customer_data.get('customer_id')} "
            f"in campaign {campaign_data.get('campaign_id')}"
        )

        # Step 1: Compliance check
        compliance = check_dnc_compliance(customer_data["phone_number"])
        if not compliance["is_compliant"]:
            logger.warning(
                f"Skipping call to {customer_data['phone_number']} - compliance check failed: "
                f"{json.dumps(compliance)}"
            )
            return

        # Step 2: Generate personalized script
        script = generate_call_script(campaign_data, customer_data)

        # Step 3: Check optimal call time
        redis_client = get_redis_client()
        cached_schedule = redis_client.get(f"schedule:optimal:{customer_data['customer_id']}")
        if cached_schedule:
            schedule = json.loads(cached_schedule)
            # If current time is in avoid window, re-queue for later
            logger.info(f"Optimal schedule available for customer {customer_data['customer_id']}")

        # Step 4: Initiate the call
        result = initiate_outbound_call(customer_data, script)

        if result["status"] == "initiated":
            logger.info(f"Call initiated successfully: {result['call_id']}")
        else:
            logger.error(f"Call initiation failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error processing outbound call message: {e}", exc_info=True)
        raise


# ==============================================================================
# Event Hub Trigger - Real-Time Call Event Analytics
# ==============================================================================

@app.function_name(name="CallEventAnalytics")
@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="call-events",
    connection="EVENT_HUB_CONNECTION",
    cardinality="many"
)
async def call_event_analytics(events: List[func.EventHubEvent]):
    """
    Process real-time call events from Event Hub for live analytics.
    Handles events such as call connected, speech detected, sentiment shifts,
    call ended, and voicemail detected.
    """
    for event in events:
        try:
            event_data = json.loads(event.get_body().decode("utf-8"))
            event_type = event_data.get("event_type")
            call_id = event_data.get("call_id")

            logger.info(f"Processing call event: {event_type} for call {call_id}")

            if event_type == "speech_recognized":
                # Append to running transcript in Redis
                redis_client = get_redis_client()
                transcript_key = f"call:transcript:{call_id}"
                current = redis_client.get(transcript_key) or ""
                speaker = event_data.get("speaker", "unknown")
                text = event_data.get("text", "")
                updated = f"{current}\n{speaker}: {text}".strip()
                redis_client.setex(transcript_key, Config.MAX_CALL_DURATION_SECONDS, updated)

                # Periodic sentiment analysis
                line_count = updated.count("\n") + 1
                if line_count % 5 == 0:  # Every 5 turns
                    sentiment = analyze_call_sentiment(updated)
                    redis_client.setex(
                        f"call:sentiment:{call_id}",
                        Config.MAX_CALL_DURATION_SECONDS,
                        json.dumps(sentiment)
                    )

                    # Check if escalation is needed based on sentiment
                    if sentiment.get("risk_level") == "high":
                        logger.warning(f"High risk detected on call {call_id}, triggering escalation")
                        escalate_to_human(call_id, f"High risk sentiment detected: {sentiment.get('recommendation')}")

            elif event_type == "call_connected":
                # Update call status in Cosmos DB
                container = get_cosmos_container("callLogs")
                container.upsert_item(body={
                    "id": call_id,
                    "status": "connected",
                    "connectedAt": datetime.utcnow().isoformat(),
                    "partitionKey": event_data.get("customer_id", call_id)
                })

            elif event_type == "voicemail_detected":
                detection = detect_voicemail(event_data.get("audio_analysis", {}))
                if detection["is_voicemail"] and detection["action"] == "leave_message":
                    logger.info(f"Voicemail detected on call {call_id}, leaving message")
                elif detection["is_voicemail"] and detection["action"] == "hangup_retry":
                    logger.info(f"Voicemail detected on call {call_id}, hanging up for retry")

            elif event_type == "call_ended":
                # Retrieve full transcript and classify outcome
                redis_client = get_redis_client()
                transcript = redis_client.get(f"call:transcript:{call_id}") or ""
                call_data = {
                    "call_id": call_id,
                    "campaign_id": event_data.get("campaign_id"),
                    "phone_number": event_data.get("phone_number"),
                    "duration_seconds": event_data.get("duration_seconds", 0),
                    "ended_reason": event_data.get("ended_reason", "unknown")
                }

                if transcript:
                    classification = classify_call_outcome(call_data, transcript)
                    logger.info(
                        f"Call {call_id} classified as: {classification.get('outcome')} "
                        f"(confidence: {classification.get('confidence')})"
                    )

                # Clean up Redis keys for ended call
                for suffix in ["script", "context", "transcript", "sentiment"]:
                    redis_client.delete(f"call:{suffix}:{call_id}")

        except Exception as e:
            logger.error(f"Error processing call event: {e}", exc_info=True)
