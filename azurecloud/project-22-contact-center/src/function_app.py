"""
AI Contact Center Platform - Azure Functions
===================================================
Omnichannel contact center with real-time AI assist, transcription, and quality management
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
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
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
    SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
    TRANSLATOR_ENDPOINT = os.getenv("TRANSLATOR_ENDPOINT")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    COMMUNICATION_SERVICES_ENDPOINT = os.getenv("COMMUNICATION_SERVICES_ENDPOINT")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "knowledge-base-index"

    # Contact center parameters
    SENTIMENT_THRESHOLD_ESCALATION = 0.3
    QUALITY_SCORE_MIN = 70
    MAX_AUTO_RESPONSE_TOKENS = 1024
    MAX_SUMMARY_TOKENS = 2048


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
    database = _cosmos_client.get_database_client("contactcenter")
    return database.get_container_client(container_name)


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def transcribe_realtime(audio_stream: bytes) -> dict:
    """
    Real-time speech-to-text transcription using Azure Speech Services.

    Args:
        audio_stream: Raw audio bytes from the call

    Returns:
        Transcription result with text, language, and confidence
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "audio/wav",
        "Accept": "application/json"
    }

    response = requests.post(
        f"{Config.SPEECH_ENDPOINT}/speech/recognition/conversation/cognitiveservices/v1"
        "?language=en-US&format=detailed",
        headers=headers,
        data=audio_stream,
        timeout=30
    )
    response.raise_for_status()
    result = response.json()

    return {
        "text": result.get("DisplayText", ""),
        "language": result.get("Language", "en-US"),
        "confidence": result.get("NBest", [{}])[0].get("Confidence", 0.0),
        "duration_ms": result.get("Duration", 0),
        "offset_ms": result.get("Offset", 0)
    }


def translate_text(text: str, source_lang: str, target_lang: str) -> dict:
    """
    Real-time text translation using Azure Translator.

    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'en')
        target_lang: Target language code (e.g., 'es')

    Returns:
        Translation result with translated text and detected language
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = [{"text": text}]
    params = {"api-version": "3.0", "from": source_lang, "to": target_lang}

    response = requests.post(
        f"{Config.TRANSLATOR_ENDPOINT}/translate",
        headers=headers,
        params=params,
        json=body,
        timeout=15
    )
    response.raise_for_status()
    result = response.json()

    translation = result[0]["translations"][0]
    return {
        "translated_text": translation["text"],
        "target_language": translation["to"],
        "source_language": source_lang,
        "original_text": text
    }


def get_agent_assist_suggestions(transcript: str, customer_context: dict) -> dict:
    """
    Retrieve knowledge base articles and generate suggested responses for agent.

    Args:
        transcript: Current call/chat transcript
        customer_context: Customer profile and interaction history

    Returns:
        Agent assist suggestions with knowledge articles and recommended responses
    """
    # Search knowledge base for relevant articles
    query_vector = generate_embedding(transcript[-500:])
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=5,
        fields="contentVector"
    )

    search_client = get_search_client()
    results = search_client.search(
        search_text=transcript[-200:],
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="default-semantic-config",
        top=5,
        select=["id", "content", "title", "category", "resolution_steps"]
    )

    knowledge_articles = []
    for result in results:
        knowledge_articles.append({
            "id": result["id"],
            "title": result.get("title", ""),
            "content": result["content"],
            "category": result.get("category", "General"),
            "resolution_steps": result.get("resolution_steps", ""),
            "relevance_score": result["@search.score"]
        })

    # Generate suggested response using GPT-4o
    client = get_openai_client()
    system_prompt = """You are an AI assistant helping a contact center agent during a live interaction.
Based on the conversation transcript, customer context, and knowledge base articles, provide:
1. A concise summary of the customer issue
2. Two recommended responses the agent can use
3. Relevant resolution steps from the knowledge base
4. Any upsell or cross-sell opportunities if appropriate

Be direct, professional, and empathetic in suggested responses."""

    context_str = json.dumps(customer_context, default=str)
    articles_str = "\n\n".join(
        f"[Article: {a['title']}]\n{a['content']}\nResolution: {a['resolution_steps']}"
        for a in knowledge_articles[:3]
    )

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"TRANSCRIPT:\n{transcript}\n\n"
                f"CUSTOMER CONTEXT:\n{context_str}\n\n"
                f"KNOWLEDGE BASE ARTICLES:\n{articles_str}"
            )}
        ],
        max_tokens=Config.MAX_AUTO_RESPONSE_TOKENS,
        temperature=0.4
    )

    return {
        "suggestions": response.choices[0].message.content,
        "knowledge_articles": knowledge_articles,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def analyze_sentiment(text: str) -> dict:
    """
    Real-time customer sentiment analysis.

    Args:
        text: Text to analyze (transcript segment or message)

    Returns:
        Sentiment result with label, score, and escalation flag
    """
    client = get_openai_client()

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": (
                "Analyze the sentiment of the following customer text. "
                "Return a JSON object with: "
                '"sentiment" (positive/neutral/negative), '
                '"score" (float -1.0 to 1.0 where -1 is most negative), '
                '"emotions" (list of detected emotions), '
                '"escalation_recommended" (boolean if agent supervisor should be notified). '
                "Return ONLY valid JSON."
            )},
            {"role": "user", "content": text}
        ],
        max_tokens=256,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result["escalation_recommended"] = (
        result.get("escalation_recommended", False)
        or result.get("score", 0) < Config.SENTIMENT_THRESHOLD_ESCALATION
    )

    return {
        "sentiment": result.get("sentiment", "neutral"),
        "score": result.get("score", 0.0),
        "emotions": result.get("emotions", []),
        "escalation_recommended": result["escalation_recommended"],
        "analyzed_text_length": len(text)
    }


def generate_auto_response(channel: str, customer_query: str, context: dict) -> dict:
    """
    Generate AI auto-response for chat or email channels.

    Args:
        channel: Interaction channel ('chat', 'email', 'sms')
        customer_query: Customer's message or query
        context: Customer profile and interaction context

    Returns:
        Generated response with confidence score and channel formatting
    """
    client = get_openai_client()

    channel_instructions = {
        "chat": "Keep response concise (under 150 words). Use a friendly, conversational tone.",
        "email": "Use professional email formatting with greeting and sign-off. Be thorough but clear.",
        "sms": "Keep response under 160 characters. Be direct and include a callback option."
    }

    system_prompt = f"""You are an AI auto-responder for a contact center.
Channel: {channel}
Instructions: {channel_instructions.get(channel, channel_instructions['chat'])}

Customer context: {json.dumps(context, default=str)}

Generate a helpful, accurate response. If you cannot fully resolve the query,
acknowledge the issue and indicate that a human agent will follow up."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": customer_query}
        ],
        max_tokens=Config.MAX_AUTO_RESPONSE_TOKENS,
        temperature=0.5
    )

    return {
        "response_text": response.choices[0].message.content,
        "channel": channel,
        "requires_human_review": False,
        "confidence": 0.85,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def summarize_interaction(interaction_data: dict) -> dict:
    """
    Post-call/chat summarization with action items.

    Args:
        interaction_data: Full interaction data including transcript and metadata

    Returns:
        Structured summary with key topics, action items, and follow-ups
    """
    client = get_openai_client()

    system_prompt = """Summarize the following contact center interaction.
Return a JSON object with:
- "summary": concise summary (2-3 sentences)
- "customer_issue": primary issue description
- "resolution": how the issue was resolved (or 'unresolved')
- "action_items": list of follow-up action items
- "key_topics": list of main topics discussed
- "customer_sentiment_overall": overall sentiment (positive/neutral/negative)
- "call_disposition": disposition code (resolved, escalated, callback_scheduled, transferred)
Return ONLY valid JSON."""

    transcript = interaction_data.get("transcript", "")
    metadata = {
        "channel": interaction_data.get("channel", "voice"),
        "duration_seconds": interaction_data.get("duration_seconds", 0),
        "agent_id": interaction_data.get("agent_id", ""),
        "customer_id": interaction_data.get("customer_id", ""),
        "queue": interaction_data.get("queue", "general")
    }

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"INTERACTION METADATA:\n{json.dumps(metadata, default=str)}\n\n"
                f"TRANSCRIPT:\n{transcript}"
            )}
        ],
        max_tokens=Config.MAX_SUMMARY_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    summary = json.loads(response.choices[0].message.content)
    summary["interaction_id"] = interaction_data.get("interaction_id", "")
    summary["generated_at"] = datetime.utcnow().isoformat()

    # Persist summary to Cosmos DB
    try:
        container = get_cosmos_container("interactionSummaries")
        summary["id"] = hashlib.md5(
            f"{summary['interaction_id']}-{summary['generated_at']}".encode()
        ).hexdigest()
        summary["partitionKey"] = interaction_data.get("customer_id", "unknown")
        container.create_item(body=summary)
    except Exception as e:
        logger.warning(f"Failed to persist interaction summary: {e}")

    return summary


def score_quality(interaction_data: dict, transcript: str) -> dict:
    """
    AI quality scoring of agent interaction.

    Args:
        interaction_data: Interaction metadata (agent, channel, duration, etc.)
        transcript: Full interaction transcript

    Returns:
        Quality scorecard with category scores and improvement recommendations
    """
    client = get_openai_client()

    system_prompt = """You are a contact center quality analyst. Score the following agent interaction.
Return a JSON object with:
- "overall_score": integer 0-100
- "categories": object with category scores (0-100):
  - "greeting_closing": proper greeting and closing
  - "empathy": demonstrated empathy and active listening
  - "problem_resolution": effectiveness of issue resolution
  - "product_knowledge": accuracy and depth of product knowledge
  - "communication": clarity and professionalism
  - "compliance": adherence to required disclosures and procedures
  - "hold_transfer": proper hold and transfer procedures
- "strengths": list of what the agent did well
- "improvements": list of areas for improvement
- "coaching_notes": brief coaching recommendation for supervisor
- "compliance_flags": list of any compliance issues detected
Return ONLY valid JSON."""

    agent_info = {
        "agent_id": interaction_data.get("agent_id", ""),
        "channel": interaction_data.get("channel", "voice"),
        "duration_seconds": interaction_data.get("duration_seconds", 0),
        "queue": interaction_data.get("queue", "general"),
        "hold_count": interaction_data.get("hold_count", 0),
        "transfer_count": interaction_data.get("transfer_count", 0)
    }

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"AGENT METADATA:\n{json.dumps(agent_info, default=str)}\n\n"
                f"TRANSCRIPT:\n{transcript}"
            )}
        ],
        max_tokens=Config.MAX_SUMMARY_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    scorecard = json.loads(response.choices[0].message.content)
    scorecard["interaction_id"] = interaction_data.get("interaction_id", "")
    scorecard["agent_id"] = interaction_data.get("agent_id", "")
    scorecard["scored_at"] = datetime.utcnow().isoformat()

    # Persist scorecard to Cosmos DB
    try:
        container = get_cosmos_container("qualityScorecards")
        scorecard["id"] = hashlib.md5(
            f"{scorecard['interaction_id']}-{scorecard['scored_at']}".encode()
        ).hexdigest()
        scorecard["partitionKey"] = interaction_data.get("agent_id", "unknown")
        container.create_item(body=scorecard)
    except Exception as e:
        logger.warning(f"Failed to persist quality scorecard: {e}")

    return scorecard


def route_interaction(customer_data: dict, interaction_type: str) -> dict:
    """
    Intelligent skill-based routing for incoming interactions.

    Args:
        customer_data: Customer profile, history, and current context
        interaction_type: Type of interaction ('voice', 'chat', 'email', 'sms')

    Returns:
        Routing decision with target queue, priority, and reasoning
    """
    client = get_openai_client()

    system_prompt = """You are an intelligent contact center router. Based on customer data and
interaction type, determine the optimal routing.
Return a JSON object with:
- "target_queue": recommended queue name
- "priority": integer 1-5 (1=highest)
- "required_skills": list of agent skills needed
- "language": preferred language for the agent
- "estimated_handle_time_seconds": estimated handle time
- "reasoning": brief explanation of routing decision
- "vip_flag": boolean if customer is high-value
Return ONLY valid JSON."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"CUSTOMER DATA:\n{json.dumps(customer_data, default=str)}\n\n"
                f"INTERACTION TYPE: {interaction_type}"
            )}
        ],
        max_tokens=512,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    routing = json.loads(response.choices[0].message.content)
    routing["interaction_type"] = interaction_type
    routing["routed_at"] = datetime.utcnow().isoformat()

    return routing


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()

    response = client.embeddings.create(
        input=text,
        model=Config.EMBEDDING_MODEL
    )

    return response.data[0].embedding


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="agent-assist", methods=["POST"])
async def agent_assist_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Real-time agent assist suggestions endpoint.

    Request Body:
    {
        "transcript": "Customer: I need to change my billing address...",
        "customer_context": {"customer_id": "C123", "tier": "gold", "history": [...]}
    }
    """
    try:
        req_body = req.get_json()
        transcript = req_body.get("transcript")
        customer_context = req_body.get("customer_context", {})

        if not transcript:
            return func.HttpResponse(
                json.dumps({"error": "transcript is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Agent assist request, transcript length: {len(transcript)}")
        result = get_agent_assist_suggestions(transcript, customer_context)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in agent assist: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="auto-response", methods=["POST"])
async def auto_response_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    GenAI auto-response generation endpoint.

    Request Body:
    {
        "channel": "chat",
        "customer_query": "How do I reset my password?",
        "context": {"customer_id": "C123", "product": "enterprise-plan"}
    }
    """
    try:
        req_body = req.get_json()
        channel = req_body.get("channel", "chat")
        customer_query = req_body.get("customer_query")
        context = req_body.get("context", {})

        if not customer_query:
            return func.HttpResponse(
                json.dumps({"error": "customer_query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Auto-response request for channel: {channel}")
        result = generate_auto_response(channel, customer_query, context)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in auto-response: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize", methods=["POST"])
async def summarize_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Interaction summarization endpoint.

    Request Body:
    {
        "interaction_id": "INT-20240101-001",
        "transcript": "Agent: Thank you for calling...",
        "channel": "voice",
        "duration_seconds": 340,
        "agent_id": "A100",
        "customer_id": "C123",
        "queue": "billing"
    }
    """
    try:
        req_body = req.get_json()
        if not req_body.get("transcript"):
            return func.HttpResponse(
                json.dumps({"error": "transcript is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Summarize request for interaction: {req_body.get('interaction_id')}")
        result = summarize_interaction(req_body)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarization: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="quality-score", methods=["POST"])
async def quality_score_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Quality management scoring endpoint.

    Request Body:
    {
        "interaction_id": "INT-20240101-001",
        "transcript": "Agent: Thank you for calling...",
        "agent_id": "A100",
        "channel": "voice",
        "duration_seconds": 340,
        "hold_count": 1,
        "transfer_count": 0,
        "queue": "billing"
    }
    """
    try:
        req_body = req.get_json()
        transcript = req_body.get("transcript")

        if not transcript:
            return func.HttpResponse(
                json.dumps({"error": "transcript is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Quality score request for interaction: {req_body.get('interaction_id')}")
        result = score_quality(req_body, transcript)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in quality scoring: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="route", methods=["POST"])
async def route_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Intelligent routing endpoint.

    Request Body:
    {
        "customer_data": {"customer_id": "C123", "tier": "gold", "language": "en", ...},
        "interaction_type": "voice"
    }
    """
    try:
        req_body = req.get_json()
        customer_data = req_body.get("customer_data", {})
        interaction_type = req_body.get("interaction_type", "voice")

        if not customer_data:
            return func.HttpResponse(
                json.dumps({"error": "customer_data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Routing request for interaction type: {interaction_type}")
        result = route_interaction(customer_data, interaction_type)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in routing: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="sentiment", methods=["POST"])
async def sentiment_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Sentiment analysis endpoint.

    Request Body:
    {
        "text": "I have been waiting for 30 minutes and nobody has helped me!"
    }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")

        if not text:
            return func.HttpResponse(
                json.dumps({"error": "text is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Sentiment analysis request, text length: {len(text)}")
        result = analyze_sentiment(text)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}", exc_info=True)
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
            "service": "ai-contact-center-platform",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger for Real-Time Call Event Processing
# ==============================================================================

@app.function_name(name="CallEventProcessor")
@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="call-events",
    connection="EVENT_HUB_CONNECTION",
    cardinality="many",
    consumer_group="$Default"
)
@app.event_hub_output(
    arg_name="signalr_messages",
    event_hub_name="agent-updates",
    connection="EVENT_HUB_CONNECTION"
)
async def call_event_processor(events: func.EventHubEvent, signalr_messages: func.Out[str]):
    """
    Process real-time call events from Event Hub.

    Handles events such as:
    - call_started: Initialize transcription and sentiment tracking
    - transcript_segment: Process new transcript segment for sentiment and agent assist
    - call_ended: Generate summary and quality score
    - hold_started / hold_ended: Track hold metrics
    """
    agent_updates = []

    for event in events:
        try:
            event_data = json.loads(event.get_body().decode("utf-8"))
            event_type = event_data.get("event_type")
            interaction_id = event_data.get("interaction_id", "unknown")

            logger.info(f"Processing call event: {event_type} for {interaction_id}")

            if event_type == "transcript_segment":
                # Analyze sentiment of new transcript segment
                segment_text = event_data.get("text", "")
                sentiment_result = analyze_sentiment(segment_text)

                agent_update = {
                    "target": "agent-desktop",
                    "interaction_id": interaction_id,
                    "agent_id": event_data.get("agent_id"),
                    "update_type": "sentiment",
                    "data": sentiment_result,
                    "timestamp": datetime.utcnow().isoformat()
                }
                agent_updates.append(agent_update)

                # If sentiment is negative, trigger agent assist
                if sentiment_result.get("escalation_recommended"):
                    logger.warning(
                        f"Escalation recommended for interaction {interaction_id}, "
                        f"sentiment score: {sentiment_result.get('score')}"
                    )
                    agent_update_escalation = {
                        "target": "agent-desktop",
                        "interaction_id": interaction_id,
                        "agent_id": event_data.get("agent_id"),
                        "update_type": "escalation_alert",
                        "data": {
                            "message": "Customer sentiment is negative. Consider supervisor assist.",
                            "sentiment": sentiment_result
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    agent_updates.append(agent_update_escalation)

            elif event_type == "call_ended":
                # Generate post-call summary
                interaction_data = {
                    "interaction_id": interaction_id,
                    "transcript": event_data.get("full_transcript", ""),
                    "channel": event_data.get("channel", "voice"),
                    "duration_seconds": event_data.get("duration_seconds", 0),
                    "agent_id": event_data.get("agent_id", ""),
                    "customer_id": event_data.get("customer_id", ""),
                    "queue": event_data.get("queue", "general"),
                    "hold_count": event_data.get("hold_count", 0),
                    "transfer_count": event_data.get("transfer_count", 0)
                }

                summary = summarize_interaction(interaction_data)
                scorecard = score_quality(interaction_data, interaction_data["transcript"])

                agent_update = {
                    "target": "agent-desktop",
                    "interaction_id": interaction_id,
                    "agent_id": event_data.get("agent_id"),
                    "update_type": "call_completed",
                    "data": {
                        "summary": summary,
                        "quality_score": scorecard.get("overall_score", 0)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                agent_updates.append(agent_update)

            elif event_type == "call_started":
                agent_update = {
                    "target": "agent-desktop",
                    "interaction_id": interaction_id,
                    "agent_id": event_data.get("agent_id"),
                    "update_type": "call_started",
                    "data": {
                        "customer_id": event_data.get("customer_id"),
                        "channel": event_data.get("channel", "voice"),
                        "queue": event_data.get("queue", "general")
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                agent_updates.append(agent_update)

        except Exception as e:
            logger.error(f"Error processing call event: {e}", exc_info=True)

    # Send real-time updates to agent desktop via output binding
    if agent_updates:
        signalr_messages.set(json.dumps(agent_updates, default=str))
        logger.info(f"Sent {len(agent_updates)} agent desktop updates")


# ==============================================================================
# SignalR Output Binding for Real-Time Agent Desktop Updates
# ==============================================================================

@app.route(route="negotiate", methods=["POST"])
@app.generic_input_binding(
    arg_name="connectionInfo",
    type="signalRConnectionInfo",
    hub_name="agentDesktop",
    connection_string_setting="SIGNALR_CONNECTION"
)
async def negotiate(req: func.HttpRequest, connectionInfo: str) -> func.HttpResponse:
    """
    SignalR negotiate endpoint for agent desktop real-time connections.

    Returns connection info for the agent desktop to establish a SignalR connection
    for receiving real-time updates (sentiment, suggestions, alerts).
    """
    return func.HttpResponse(
        connectionInfo,
        mimetype="application/json"
    )


@app.route(route="broadcast-update", methods=["POST"])
@app.generic_output_binding(
    arg_name="signalRMessages",
    type="signalR",
    hub_name="agentDesktop",
    connection_string_setting="SIGNALR_CONNECTION"
)
async def broadcast_agent_update(req: func.HttpRequest, signalRMessages: func.Out[str]) -> func.HttpResponse:
    """
    Broadcast real-time update to agent desktop via SignalR.

    Request Body:
    {
        "agent_id": "A100",
        "update_type": "sentiment|suggestion|alert",
        "data": {...}
    }
    """
    try:
        req_body = req.get_json()
        agent_id = req_body.get("agent_id")
        update_type = req_body.get("update_type")
        data = req_body.get("data", {})

        if not agent_id or not update_type:
            return func.HttpResponse(
                json.dumps({"error": "agent_id and update_type are required"}),
                status_code=400,
                mimetype="application/json"
            )

        message = {
            "target": "agentUpdate",
            "arguments": [{
                "agent_id": agent_id,
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        signalRMessages.set(json.dumps(message, default=str))

        return func.HttpResponse(
            json.dumps({"status": "broadcast_sent", "agent_id": agent_id}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error broadcasting update: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
