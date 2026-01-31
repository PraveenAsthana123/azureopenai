"""
Contact Center Knowledge Base - Azure Functions
================================================
AI-powered knowledge management for contact centers.
Provides real-time article suggestions, knowledge gap detection,
FAQ generation from call transcripts, and GenAI-assisted authoring.
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
from azure.search.documents.models import VectorizedQuery
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
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "knowledge-articles-index"

    # Knowledge base parameters
    TOP_K = 5
    SEMANTIC_CONFIG = "kb-semantic-config"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3
    FRESHNESS_DECAY_DAYS = 90


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
    database = _cosmos_client.get_database_client("contactcenter-kb")
    return database.get_container_client(container_name)


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()

    response = client.embeddings.create(
        input=text,
        model=Config.EMBEDDING_MODEL
    )

    return response.data[0].embedding


def search_knowledge_base(query: str, top_k: int = Config.TOP_K) -> list[dict]:
    """
    Hybrid vector + keyword search for relevant knowledge articles.

    Args:
        query: Agent or customer search query
        top_k: Number of articles to retrieve

    Returns:
        List of relevant knowledge articles with metadata and scores
    """
    search_client = get_search_client()

    # Generate query embedding for vector search
    query_vector = generate_embedding(query)

    # Create vector query component
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="contentVector"
    )

    # Execute hybrid search with semantic ranking
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name=Config.SEMANTIC_CONFIG,
        top=top_k,
        select=[
            "id", "title", "content", "category", "tags",
            "lastUpdated", "author", "articleStatus", "viewCount"
        ]
    )

    articles = []
    for result in results:
        articles.append({
            "id": result["id"],
            "title": result.get("title", "Untitled"),
            "content": result["content"],
            "category": result.get("category", "General"),
            "tags": result.get("tags", []),
            "lastUpdated": result.get("lastUpdated", ""),
            "author": result.get("author", "Unknown"),
            "articleStatus": result.get("articleStatus", "published"),
            "viewCount": result.get("viewCount", 0),
            "score": result["@search.score"],
            "reranker_score": result.get("@search.reranker_score", 0)
        })

    return articles


def generate_agent_suggestions(
    transcript_segment: str,
    customer_context: Optional[dict] = None
) -> dict:
    """
    Generate real-time article suggestions during live calls.

    Analyses the latest transcript segment and optional customer context
    to surface the most relevant knowledge articles for the agent.

    Args:
        transcript_segment: Recent portion of the call transcript
        customer_context: Optional dict with customer tier, history, product info

    Returns:
        Dict with suggested articles and a concise coaching tip
    """
    # Search knowledge base using transcript content as query
    articles = search_knowledge_base(transcript_segment, top_k=3)

    # Build context-aware prompt for coaching tip
    context_info = ""
    if customer_context:
        context_info = (
            f"\nCustomer tier: {customer_context.get('tier', 'standard')}"
            f"\nProduct: {customer_context.get('product', 'N/A')}"
            f"\nPrevious contacts: {customer_context.get('previous_contacts', 0)}"
        )

    article_summaries = "\n".join(
        f"- {a['title']}: {a['content'][:200]}" for a in articles
    )

    client = get_openai_client()
    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a contact center coaching assistant. Based on the "
                    "live transcript and knowledge articles, provide a brief "
                    "coaching tip (2-3 sentences) to help the agent resolve "
                    "the customer issue effectively."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Transcript segment:\n{transcript_segment}\n"
                    f"{context_info}\n\n"
                    f"Relevant articles:\n{article_summaries}"
                )
            }
        ],
        max_tokens=256,
        temperature=Config.TEMPERATURE
    )

    return {
        "suggested_articles": [
            {"id": a["id"], "title": a["title"], "score": a["score"]}
            for a in articles
        ],
        "coaching_tip": response.choices[0].message.content,
        "timestamp": datetime.utcnow().isoformat()
    }


def detect_knowledge_gaps(call_transcripts: list[str]) -> dict:
    """
    Identify topics where agents lack supporting knowledge articles.

    Analyses a batch of call transcripts to find recurring questions
    or issues that have no matching articles in the knowledge base.

    Args:
        call_transcripts: List of recent call transcript texts

    Returns:
        Dict with identified gaps, each with topic and frequency estimate
    """
    client = get_openai_client()

    combined = "\n---\n".join(call_transcripts[:20])

    # Step 1: Extract recurring themes / questions from transcripts
    extraction_response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an analyst reviewing contact center call transcripts. "
                    "Extract distinct customer questions or topics that appear "
                    "repeatedly. Return a JSON array of objects with keys: "
                    "'topic' (short label) and 'example_question' (representative "
                    "customer question). Return at most 10 topics."
                )
            },
            {"role": "user", "content": combined}
        ],
        max_tokens=1024,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    try:
        topics = json.loads(extraction_response.choices[0].message.content)
        topic_list = topics.get("topics", topics.get("results", []))
    except (json.JSONDecodeError, AttributeError):
        topic_list = []

    # Step 2: For each topic, check if knowledge base has coverage
    gaps = []
    for topic in topic_list:
        query = topic.get("example_question", topic.get("topic", ""))
        if not query:
            continue
        results = search_knowledge_base(query, top_k=2)
        max_score = max((r["reranker_score"] for r in results), default=0)
        if max_score < 1.5:
            gaps.append({
                "topic": topic.get("topic", query),
                "example_question": query,
                "best_match_score": max_score,
                "coverage": "missing" if max_score < 0.5 else "weak"
            })

    return {
        "gaps_detected": len(gaps),
        "gaps": gaps,
        "transcripts_analysed": len(call_transcripts),
        "timestamp": datetime.utcnow().isoformat()
    }


def generate_faq_from_transcripts(transcripts: list[str]) -> dict:
    """
    Auto-generate FAQ articles from recurring call patterns.

    Args:
        transcripts: List of call transcript texts

    Returns:
        Dict with generated FAQ entries ready for review and publication
    """
    client = get_openai_client()

    combined = "\n---\n".join(transcripts[:30])

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledge base author for a contact center. "
                    "Analyse the call transcripts and generate FAQ articles. "
                    "Return a JSON object with key 'faqs' containing an array. "
                    "Each FAQ has: 'question', 'answer', 'category', 'tags' "
                    "(array of keyword strings). Write clear, professional "
                    "answers suitable for both agents and self-service portals."
                )
            },
            {"role": "user", "content": combined}
        ],
        max_tokens=2048,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    try:
        faqs_payload = json.loads(response.choices[0].message.content)
        faq_list = faqs_payload.get("faqs", [])
    except (json.JSONDecodeError, AttributeError):
        faq_list = []

    # Enrich each FAQ with metadata
    enriched = []
    for faq in faq_list:
        enriched.append({
            "id": hashlib.md5(faq.get("question", "").encode()).hexdigest(),
            "question": faq.get("question", ""),
            "answer": faq.get("answer", ""),
            "category": faq.get("category", "General"),
            "tags": faq.get("tags", []),
            "status": "draft",
            "generatedAt": datetime.utcnow().isoformat(),
            "source": "auto-generated-from-transcripts"
        })

    return {
        "faq_count": len(enriched),
        "faqs": enriched,
        "timestamp": datetime.utcnow().isoformat()
    }


def author_article(topic: str, source_content: str) -> dict:
    """
    GenAI-assisted knowledge article creation.

    Takes a topic and optional source material (e.g. product docs, emails)
    and produces a structured knowledge article draft.

    Args:
        topic: Article topic or title
        source_content: Raw source material to base the article on

    Returns:
        Dict with structured article draft and metadata
    """
    client = get_openai_client()

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior knowledge base author for a contact center. "
                    "Create a well-structured knowledge article. Return JSON with: "
                    "'title', 'summary' (2-3 sentence overview), 'content' "
                    "(full article body in markdown), 'category', 'tags' (array), "
                    "'internal_notes' (tips for agents), 'customer_facing_version' "
                    "(simplified version suitable for self-service)."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n\n"
                    f"Source material:\n{source_content}"
                )
            }
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    try:
        article = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, AttributeError):
        article = {"title": topic, "content": "", "error": "Generation failed"}

    article_id = hashlib.md5(f"{topic}-{datetime.utcnow().isoformat()}".encode()).hexdigest()

    return {
        "id": article_id,
        "title": article.get("title", topic),
        "summary": article.get("summary", ""),
        "content": article.get("content", ""),
        "category": article.get("category", "General"),
        "tags": article.get("tags", []),
        "internal_notes": article.get("internal_notes", ""),
        "customer_facing_version": article.get("customer_facing_version", ""),
        "status": "draft",
        "createdAt": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def score_article_freshness(article: dict) -> dict:
    """
    Score an article's freshness based on feedback, age, and accuracy signals.

    Args:
        article: Article dict with lastUpdated, feedback, viewCount, etc.

    Returns:
        Dict with freshness score (0-100) and actionable recommendation
    """
    score = 100.0

    # Age decay: lose points for each day past the freshness window
    last_updated = article.get("lastUpdated", "")
    if last_updated:
        try:
            updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            age_days = (datetime.now(updated_dt.tzinfo) - updated_dt).days
            if age_days > Config.FRESHNESS_DECAY_DAYS:
                overage = age_days - Config.FRESHNESS_DECAY_DAYS
                score -= min(overage * 0.5, 40)
        except (ValueError, TypeError):
            score -= 10  # Penalise missing/invalid date

    # Negative feedback signal
    negative_feedback = article.get("negativeFeedbackCount", 0)
    positive_feedback = article.get("positiveFeedbackCount", 0)
    total_feedback = negative_feedback + positive_feedback
    if total_feedback > 0:
        negative_ratio = negative_feedback / total_feedback
        score -= negative_ratio * 30

    # Low view count may indicate irrelevance
    view_count = article.get("viewCount", 0)
    if view_count < 10:
        score -= 5

    # Accuracy flag from manual reviews
    if article.get("flaggedInaccurate", False):
        score -= 25

    score = max(0, min(100, score))

    # Determine recommendation
    if score >= 80:
        recommendation = "current"
    elif score >= 50:
        recommendation = "review_recommended"
    elif score >= 25:
        recommendation = "update_required"
    else:
        recommendation = "retire_or_rewrite"

    return {
        "article_id": article.get("id", "unknown"),
        "freshness_score": round(score, 1),
        "recommendation": recommendation,
        "evaluated_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="search", methods=["POST"])
async def search_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Knowledge base search endpoint.

    Request Body:
    {
        "query": "How do I reset a customer password?",
        "top_k": 5
    }
    """
    try:
        req_body = req.get_json()
        query = req_body.get("query")
        top_k = req_body.get("top_k", Config.TOP_K)

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Knowledge search: {query[:80]}...")

        articles = search_knowledge_base(query, top_k=top_k)

        return func.HttpResponse(
            json.dumps({
                "query": query,
                "results": articles,
                "count": len(articles),
                "timestamp": datetime.utcnow().isoformat()
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="agent-suggest", methods=["POST"])
async def agent_suggest_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Real-time agent suggestions during live calls.

    Request Body:
    {
        "transcript_segment": "Customer is asking about refund policy...",
        "customer_context": {
            "tier": "gold",
            "product": "Premium Plan",
            "previous_contacts": 3
        }
    }
    """
    try:
        req_body = req.get_json()
        transcript_segment = req_body.get("transcript_segment")
        customer_context = req_body.get("customer_context")

        if not transcript_segment:
            return func.HttpResponse(
                json.dumps({"error": "transcript_segment is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info("Generating agent suggestions for live call")

        suggestions = generate_agent_suggestions(
            transcript_segment, customer_context
        )

        return func.HttpResponse(
            json.dumps(suggestions),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in agent-suggest endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="detect-gaps", methods=["POST"])
async def detect_gaps_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Knowledge gap detection from call transcripts.

    Request Body:
    {
        "call_transcripts": [
            "Transcript text 1...",
            "Transcript text 2..."
        ]
    }
    """
    try:
        req_body = req.get_json()
        call_transcripts = req_body.get("call_transcripts", [])

        if not call_transcripts:
            return func.HttpResponse(
                json.dumps({"error": "call_transcripts array is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Detecting knowledge gaps from {len(call_transcripts)} transcripts")

        gaps = detect_knowledge_gaps(call_transcripts)

        return func.HttpResponse(
            json.dumps(gaps),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in detect-gaps endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="generate-faq", methods=["POST"])
async def generate_faq_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    FAQ generation from call transcripts.

    Request Body:
    {
        "transcripts": [
            "Transcript text 1...",
            "Transcript text 2..."
        ]
    }
    """
    try:
        req_body = req.get_json()
        transcripts = req_body.get("transcripts", [])

        if not transcripts:
            return func.HttpResponse(
                json.dumps({"error": "transcripts array is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating FAQs from {len(transcripts)} transcripts")

        faqs = generate_faq_from_transcripts(transcripts)

        return func.HttpResponse(
            json.dumps(faqs),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in generate-faq endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="author-article", methods=["POST"])
async def author_article_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    AI-assisted article authoring.

    Request Body:
    {
        "topic": "Password Reset Procedures",
        "source_content": "Internal doc text or notes..."
    }
    """
    try:
        req_body = req.get_json()
        topic = req_body.get("topic")
        source_content = req_body.get("source_content", "")

        if not topic:
            return func.HttpResponse(
                json.dumps({"error": "topic is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Authoring article for topic: {topic}")

        article = author_article(topic, source_content)

        # Persist draft to Cosmos DB
        try:
            container = get_cosmos_container("articles")
            container.create_item(body=article)
            logger.info(f"Article draft saved: {article['id']}")
        except Exception as db_err:
            logger.warning(f"Failed to persist article draft: {db_err}")
            article["persist_warning"] = "Draft generated but not saved to database"

        return func.HttpResponse(
            json.dumps(article),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in author-article endpoint: {e}", exc_info=True)
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
            "service": "contact-center-knowledge-base",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger for Transcript Uploads
# ==============================================================================

@app.function_name(name="TranscriptUploadTrigger")
@app.event_grid_trigger(arg_name="event")
async def transcript_upload_trigger(event: func.EventGridEvent):
    """
    Triggered when a new call transcript is uploaded to blob storage.
    Initiates knowledge base enrichment pipeline.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url", "")
        blob_name = blob_url.split("/")[-1] if blob_url else "unknown"

        logger.info(f"New transcript uploaded: {blob_name}")

        # Log event to Cosmos DB for tracking
        container = get_cosmos_container("transcriptEvents")
        container.create_item(body={
            "id": hashlib.md5(f"{blob_name}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "blobUrl": blob_url,
            "blobName": blob_name,
            "eventType": event.event_type,
            "status": "received",
            "receivedAt": datetime.utcnow().isoformat()
        })

        logger.info(f"Transcript event logged for enrichment pipeline: {blob_name}")

    except Exception as e:
        logger.error(f"Error processing transcript upload event: {e}", exc_info=True)
        raise
