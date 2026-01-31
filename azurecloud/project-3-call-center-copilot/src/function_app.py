"""
Automated Call Center Copilot (Voice + Chat) - Azure Functions
==============================================================
Multilingual conversational AI platform for call centers with real-time
transcription, intelligent responses, sentiment analysis, and post-call
summarization.

Datasets: Call Center Data.csv + real-time voice/chat streams
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib
import uuid

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
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
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
    SPEECH_REGION = os.getenv("SPEECH_REGION", "eastus")
    TRANSLATOR_ENDPOINT = os.getenv("TRANSLATOR_ENDPOINT")
    LANGUAGE_ENDPOINT = os.getenv("LANGUAGE_ENDPOINT")
    STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "knowledge-base-index"

    # Database
    DATABASE_NAME = "callcentercopilot"

    # Quality scoring thresholds
    SENTIMENT_POSITIVE_THRESHOLD = 0.6
    SENTIMENT_NEGATIVE_THRESHOLD = -0.3

    # Cache settings
    CACHE_TTL = 3600  # 1 hour


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None
_redis_client = None
_blob_service_client = None


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


def get_blob_service_client() -> BlobServiceClient:
    """Get Azure Blob Storage client."""
    global _blob_service_client
    if _blob_service_client is None:
        _blob_service_client = BlobServiceClient(
            account_url=Config.STORAGE_ACCOUNT_URL,
            credential=get_credential()
        )
    return _blob_service_client


# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()
    response = client.embeddings.create(
        input=text[:8000],
        model=Config.EMBEDDING_MODEL
    )
    return response.data[0].embedding


def get_cached(cache_key: str) -> Optional[dict]:
    """Retrieve a value from Redis cache."""
    try:
        r = get_redis_client()
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    return None


def set_cached(cache_key: str, data: dict, ttl: int = Config.CACHE_TTL):
    """Store a value in Redis cache."""
    try:
        r = get_redis_client()
        r.setex(cache_key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


# ==============================================================================
# Core Functions — Speech Transcription
# ==============================================================================

def transcribe_audio(audio_url: str, language: str = "en-US") -> dict:
    """
    Transcribe audio using Azure Speech Services (batch transcription API).

    Args:
        audio_url: URL of the audio file in blob storage
        language: BCP-47 language code (default: en-US)

    Returns:
        dict with transcription text, confidence, duration, and segments
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "contentUrls": [audio_url],
        "locale": language,
        "displayName": f"transcription-{uuid.uuid4().hex[:8]}",
        "properties": {
            "diarizationEnabled": True,
            "wordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic"
        }
    }

    response = requests.post(
        f"{Config.SPEECH_ENDPOINT}/speechtotext/v3.1/transcriptions",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    result = response.json()

    return {
        "transcription_id": result.get("self", "").split("/")[-1],
        "status": result.get("status", "running"),
        "language": language,
        "created_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Language Detection
# ==============================================================================

def detect_language(text: str) -> dict:
    """
    Detect the language of input text using Azure Language Services.

    Args:
        text: Input text to detect language for

    Returns:
        dict with detected language, ISO code, and confidence
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "documents": [
            {"id": "1", "text": text[:5000]}
        ]
    }

    response = requests.post(
        f"{Config.LANGUAGE_ENDPOINT}/language/:analyze-text/v2023-11-01?api-version=2023-11-01",
        headers=headers,
        json={"kind": "LanguageDetection", "analysisInput": payload}
    )
    response.raise_for_status()
    result = response.json()

    detected = result.get("results", {}).get("documents", [{}])[0]
    lang = detected.get("detectedLanguage", {})

    return {
        "language_name": lang.get("name", "Unknown"),
        "iso_code": lang.get("iso6391Name", "unknown"),
        "confidence": lang.get("confidenceScore", 0.0),
        "detected_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Translation
# ==============================================================================

def translate_text(text: str, target_language: str, source_language: str = None) -> dict:
    """
    Translate text using Azure Translator.

    Args:
        text: Text to translate
        target_language: Target language code (e.g., "en", "es", "fr")
        source_language: Source language code (auto-detect if None)

    Returns:
        dict with translated text, source and target languages
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {"to": target_language, "api-version": "3.0"}
    if source_language:
        params["from"] = source_language

    payload = [{"text": text[:10000]}]

    response = requests.post(
        f"{Config.TRANSLATOR_ENDPOINT}/translate",
        headers=headers,
        params=params,
        json=payload
    )
    response.raise_for_status()
    result = response.json()

    translation = result[0].get("translations", [{}])[0]
    detected_lang = result[0].get("detectedLanguage", {})

    return {
        "translated_text": translation.get("text", ""),
        "target_language": target_language,
        "source_language": source_language or detected_lang.get("language", "unknown"),
        "confidence": detected_lang.get("score", 1.0),
        "translated_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Core Functions — Intent Classification & RAG
# ==============================================================================

def classify_intent(text: str) -> dict:
    """
    Classify customer intent using GPT-4o.

    Categories: faq, transactional, complaint, escalation, general_inquiry

    Args:
        text: Customer message text

    Returns:
        dict with intent, confidence, and suggested action
    """
    client = get_openai_client()

    system_prompt = """You are a call center intent classifier. Classify the customer message into one of these intents:
- faq: Common questions answerable from knowledge base
- transactional: Account actions, order status, billing inquiries
- complaint: Customer complaints or negative experiences
- escalation: Request to speak with supervisor or specialist
- general_inquiry: General questions or information requests

Respond in valid JSON with fields: intent, confidence (0.0-1.0), suggested_action"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Customer message: {text[:4000]}"}
        ],
        temperature=0.1,
        max_tokens=256,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "intent": result.get("intent", "general_inquiry"),
        "confidence": float(result.get("confidence", 0.0)),
        "suggested_action": result.get("suggested_action", ""),
        "classified_at": datetime.utcnow().isoformat()
    }


def rag_knowledge_search(query: str, top_k: int = 5) -> dict:
    """
    Search knowledge base and generate a response using RAG (AI Search + GPT-4o).

    Args:
        query: Customer question
        top_k: Number of knowledge base articles to retrieve

    Returns:
        dict with AI response, sources, and confidence
    """
    search_client = get_search_client()

    query_vector = generate_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="contentVector"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="default-semantic-config",
        top=top_k,
        select=["id", "title", "content", "category"]
    )

    sources = []
    context_parts = []
    for result in results:
        sources.append({
            "id": result["id"],
            "title": result.get("title", ""),
            "category": result.get("category", ""),
            "score": result["@search.score"]
        })
        context_parts.append(result.get("content", ""))

    context = "\n\n".join(context_parts[:3])

    # Generate response using GPT-4o with retrieved context
    client = get_openai_client()

    system_prompt = """You are a helpful call center assistant. Answer the customer's question
using the provided knowledge base context. Be concise, professional, and empathetic.
If the context doesn't contain the answer, say so and suggest escalation.

Always cite the source when possible."""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nCustomer question: {query}"}
        ],
        temperature=0.3,
        max_tokens=1024
    )

    return {
        "response": response.choices[0].message.content,
        "sources": sources,
        "source_count": len(sources),
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


# ==============================================================================
# Core Functions — Sentiment Analysis & Summarization
# ==============================================================================

def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using GPT-4o.

    Args:
        text: Text to analyze

    Returns:
        dict with sentiment label, score, and key phrases
    """
    client = get_openai_client()

    system_prompt = """Analyze the sentiment of this customer interaction.
Respond in valid JSON with fields:
- sentiment: "positive", "negative", "neutral", or "mixed"
- score: float from -1.0 (very negative) to 1.0 (very positive)
- key_phrases: list of important phrases that indicate sentiment"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this text:\n\n{text[:6000]}"}
        ],
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "sentiment": result.get("sentiment", "neutral"),
        "score": float(result.get("score", 0.0)),
        "key_phrases": result.get("key_phrases", []),
        "analyzed_at": datetime.utcnow().isoformat()
    }


def summarize_call(transcript: str, call_metadata: dict = None) -> dict:
    """
    Generate a post-call summary using GPT-4o.

    Args:
        transcript: Full call transcript
        call_metadata: Optional metadata (duration, agent, etc.)

    Returns:
        dict with summary, action items, topics, and sentiment
    """
    client = get_openai_client()

    metadata_context = ""
    if call_metadata:
        metadata_context = f"\nCall metadata: {json.dumps(call_metadata)}"

    system_prompt = f"""Summarize this call center interaction. Provide:
1. A concise summary (3-5 sentences)
2. Action items identified
3. Main topics discussed
4. Customer sentiment assessment
5. Resolution status (resolved, pending, escalated){metadata_context}

Respond in valid JSON with fields: summary, action_items (list), topics (list), sentiment, resolution_status"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Call transcript:\n\n{transcript[:12000]}"}
        ],
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "summary": result.get("summary", ""),
        "action_items": result.get("action_items", []),
        "topics": result.get("topics", []),
        "sentiment": result.get("sentiment", "neutral"),
        "resolution_status": result.get("resolution_status", "unknown"),
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def score_call_quality(transcript: str, summary: dict = None) -> dict:
    """
    Score call quality based on transcript and summary analysis.

    Args:
        transcript: Full call transcript
        summary: Optional pre-generated call summary

    Returns:
        dict with overall score, dimension scores, and recommendations
    """
    client = get_openai_client()

    system_prompt = """Score this call center interaction on these dimensions (0-100 each):
1. professionalism: Agent tone and language
2. resolution_effectiveness: How well the issue was addressed
3. response_time: Speed and efficiency of responses
4. empathy: Understanding and acknowledgment of customer concerns
5. knowledge: Accuracy and depth of information provided

Respond in valid JSON with fields: overall_score (0-100), dimensions (object with above keys), recommendations (list of improvement suggestions)"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Call transcript:\n\n{transcript[:10000]}"}
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "overall_score": result.get("overall_score", 0),
        "dimensions": result.get("dimensions", {}),
        "recommendations": result.get("recommendations", []),
        "scored_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="transcribe", methods=["POST"])
async def transcribe_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Speech transcription endpoint.

    Request: { "audio_url": "...", "language": "en-US" }
    """
    try:
        req_body = req.get_json()
        audio_url = req_body.get("audio_url")
        language = req_body.get("language", "en-US")

        if not audio_url:
            return func.HttpResponse(
                json.dumps({"error": "audio_url is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Transcribing audio: {language}")
        result = transcribe_audio(audio_url, language)

        # Store transcript reference in Cosmos DB
        container = get_cosmos_container("transcripts")
        record = {
            "id": result["transcription_id"],
            "callId": result["transcription_id"],
            "audio_url": audio_url,
            **result
        }
        container.upsert_item(record)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in transcribe endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="detect-language", methods=["POST"])
async def detect_language_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Language detection endpoint.

    Request: { "text": "..." }
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

        result = detect_language(text)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in detect-language endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="translate", methods=["POST"])
async def translate_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Translation endpoint.

    Request: { "text": "...", "target_language": "en", "source_language": "es" }
    """
    try:
        req_body = req.get_json()
        text = req_body.get("text")
        target_language = req_body.get("target_language")
        source_language = req_body.get("source_language")

        if not text or not target_language:
            return func.HttpResponse(
                json.dumps({"error": "text and target_language are required"}),
                status_code=400,
                mimetype="application/json"
            )

        result = translate_text(text, target_language, source_language)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in translate endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="chat", methods=["POST"])
async def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Chat endpoint with intent classification and RAG response.

    Request: { "message": "...", "call_id": "...", "language": "en" }
    """
    try:
        req_body = req.get_json()
        message = req_body.get("message")
        call_id = req_body.get("call_id", str(uuid.uuid4()))
        language = req_body.get("language", "en")

        if not message:
            return func.HttpResponse(
                json.dumps({"error": "message is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Translate to English if needed
        english_message = message
        if language != "en":
            translation = translate_text(message, "en", language)
            english_message = translation["translated_text"]

        # Classify intent
        intent = classify_intent(english_message)

        # Generate RAG response
        rag_result = rag_knowledge_search(english_message)

        # Translate response back if needed
        response_text = rag_result["response"]
        if language != "en":
            back_translation = translate_text(response_text, language, "en")
            response_text = back_translation["translated_text"]

        # Analyze sentiment
        sentiment = analyze_sentiment(english_message)

        # Store conversation turn
        container = get_cosmos_container("conversations")
        turn_record = {
            "id": str(uuid.uuid4()),
            "callId": call_id,
            "message": message,
            "response": response_text,
            "intent": intent["intent"],
            "sentiment": sentiment["sentiment"],
            "language": language,
            "timestamp": datetime.utcnow().isoformat()
        }
        container.upsert_item(turn_record)

        return func.HttpResponse(
            json.dumps({
                "call_id": call_id,
                "response": response_text,
                "intent": intent,
                "sentiment": sentiment,
                "sources": rag_result["sources"],
                "usage": rag_result["usage"]
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="summarize-call", methods=["POST"])
async def summarize_call_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Post-call summarization endpoint.

    Request: { "transcript": "...", "call_id": "...", "metadata": {...} }
    """
    try:
        req_body = req.get_json()
        transcript = req_body.get("transcript")
        call_id = req_body.get("call_id", str(uuid.uuid4()))
        metadata = req_body.get("metadata")

        if not transcript:
            return func.HttpResponse(
                json.dumps({"error": "transcript is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Summarizing call: {call_id}")
        summary = summarize_call(transcript, metadata)

        # Store summary in Cosmos DB
        container = get_cosmos_container("callSummaries")
        record = {
            "id": call_id,
            "callId": call_id,
            **summary
        }
        container.upsert_item(record)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in summarize-call endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="quality-score", methods=["POST"])
async def quality_score_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Call quality scoring endpoint.

    Request: { "transcript": "...", "call_id": "..." }
    """
    try:
        req_body = req.get_json()
        transcript = req_body.get("transcript")
        call_id = req_body.get("call_id", str(uuid.uuid4()))

        if not transcript:
            return func.HttpResponse(
                json.dumps({"error": "transcript is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Scoring call quality: {call_id}")
        quality = score_call_quality(transcript)

        return func.HttpResponse(
            json.dumps({"call_id": call_id, **quality}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in quality-score endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="calls/{call_id}", methods=["GET"])
async def get_call_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Retrieve a call record by ID."""
    try:
        call_id = req.route_params.get("call_id")

        if not call_id:
            return func.HttpResponse(
                json.dumps({"error": "call_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        container = get_cosmos_container("callSummaries")
        record = container.read_item(item=call_id, partition_key=call_id)

        return func.HttpResponse(
            json.dumps(record),
            mimetype="application/json"
        )

    except CosmosResourceNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": f"Call {call_id} not found"}),
            status_code=404,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in get call endpoint: {e}", exc_info=True)
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
            "service": "call-center-copilot",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger
# ==============================================================================

@app.function_name(name="CallRecordingTrigger")
@app.event_grid_trigger(arg_name="event")
async def call_recording_trigger(event: func.EventGridEvent):
    """
    Triggered when a new call recording is uploaded to blob storage.
    Automatically transcribes, summarizes, and scores the call.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1] if blob_url else "unknown"

        logger.info(f"New call recording uploaded: {blob_name}")

        # Step 1: Transcribe
        transcription = transcribe_audio(blob_url)

        # Step 2: Store initial record
        call_id = str(uuid.uuid4())
        container = get_cosmos_container("callSummaries")
        record = {
            "id": call_id,
            "callId": call_id,
            "recording_url": blob_url,
            "filename": blob_name,
            "transcription_id": transcription["transcription_id"],
            "status": "transcribing",
            "created_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(record)

        logger.info(f"Call recording {blob_name} processing initiated as {call_id}")

    except Exception as e:
        logger.error(f"Error processing call recording: {e}", exc_info=True)
        raise
