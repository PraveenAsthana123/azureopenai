"""
Enterprise RAG Knowledge Copilot - Azure Functions
===================================================
Main orchestration functions for RAG-based document Q&A
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
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
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
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    REDIS_HOST = os.getenv("REDIS_HOST")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "documents-index"

    # RAG parameters
    TOP_K = 5
    SEMANTIC_CONFIG = "default-semantic-config"
    MAX_TOKENS = 4096
    TEMPERATURE = 0.7


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
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
    database = _cosmos_client.get_database_client("ragcopilot")
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
# Core RAG Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()

    response = client.embeddings.create(
        input=text,
        model=Config.EMBEDDING_MODEL
    )

    return response.data[0].embedding


def retrieve_documents(query: str, top_k: int = Config.TOP_K) -> list[dict]:
    """
    Retrieve relevant documents using hybrid search (vector + keyword).

    Args:
        query: User's search query
        top_k: Number of documents to retrieve

    Returns:
        List of relevant document chunks with metadata
    """
    search_client = get_search_client()

    # Generate query embedding
    query_vector = generate_embedding(query)

    # Create vector query
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
        select=["id", "content", "title", "source", "page", "chunk_id"]
    )

    documents = []
    for result in results:
        documents.append({
            "id": result["id"],
            "content": result["content"],
            "title": result.get("title", "Unknown"),
            "source": result.get("source", "Unknown"),
            "page": result.get("page", 0),
            "score": result["@search.score"],
            "reranker_score": result.get("@search.reranker_score", 0)
        })

    return documents


def build_augmented_prompt(query: str, documents: list[dict], chat_history: list[dict] = None) -> list[dict]:
    """
    Build the augmented prompt with retrieved context.

    Args:
        query: User's question
        documents: Retrieved relevant documents
        chat_history: Previous conversation turns

    Returns:
        Messages list for OpenAI chat completion
    """
    # System prompt with RAG instructions
    system_prompt = """You are an AI assistant for enterprise knowledge management.
Your role is to answer questions about company policies, procedures, and documentation.

INSTRUCTIONS:
1. Answer ONLY based on the provided context documents
2. If the context doesn't contain relevant information, say "I don't have information about that in the available documents"
3. Always cite your sources using [Source: document_name, Page: X] format
4. Be concise but comprehensive
5. If asked about multiple topics, address each one separately
6. Maintain a professional, helpful tone

CONTEXT DOCUMENTS:
"""

    # Add retrieved documents to context
    context_parts = []
    for i, doc in enumerate(documents, 1):
        context_parts.append(
            f"[Document {i}]\n"
            f"Title: {doc['title']}\n"
            f"Source: {doc['source']}, Page: {doc['page']}\n"
            f"Content: {doc['content']}\n"
        )

    system_prompt += "\n---\n".join(context_parts)

    messages = [{"role": "system", "content": system_prompt}]

    # Add chat history if available
    if chat_history:
        for turn in chat_history[-6:]:  # Keep last 3 turns (6 messages)
            messages.append(turn)

    # Add current user query
    messages.append({"role": "user", "content": query})

    return messages


def generate_response(messages: list[dict]) -> dict:
    """
    Generate response using Azure OpenAI GPT-4o.

    Args:
        messages: Prepared messages with context

    Returns:
        Generated response with metadata
    """
    client = get_openai_client()

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        stream=False
    )

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        },
        "model": response.model,
        "finish_reason": response.choices[0].finish_reason
    }


# ==============================================================================
# Session & History Management
# ==============================================================================

def get_or_create_session(user_id: str, session_id: Optional[str] = None) -> dict:
    """Get existing session or create new one."""
    container = get_cosmos_container("sessions")

    if session_id:
        try:
            session = container.read_item(item=session_id, partition_key=user_id)
            return session
        except Exception:
            pass

    # Create new session
    new_session = {
        "id": hashlib.md5(f"{user_id}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "userId": user_id,
        "createdAt": datetime.utcnow().isoformat(),
        "lastActivity": datetime.utcnow().isoformat(),
        "messageCount": 0
    }

    container.create_item(body=new_session)
    return new_session


def save_chat_turn(session_id: str, user_message: str, assistant_message: str, sources: list[dict]):
    """Save a conversation turn to Cosmos DB."""
    container = get_cosmos_container("chatHistory")

    chat_turn = {
        "id": hashlib.md5(f"{session_id}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "sessionId": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "userMessage": user_message,
        "assistantMessage": assistant_message,
        "sources": sources
    }

    container.create_item(body=chat_turn)


def get_chat_history(session_id: str, limit: int = 10) -> list[dict]:
    """Retrieve chat history for a session."""
    container = get_cosmos_container("chatHistory")

    query = f"SELECT * FROM c WHERE c.sessionId = @sessionId ORDER BY c.timestamp DESC OFFSET 0 LIMIT {limit}"

    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sessionId", "value": session_id}],
        enable_cross_partition_query=False
    ))

    # Convert to message format for OpenAI
    history = []
    for item in reversed(items):
        history.append({"role": "user", "content": item["userMessage"]})
        history.append({"role": "assistant", "content": item["assistantMessage"]})

    return history


# ==============================================================================
# Caching
# ==============================================================================

def get_cached_response(query_hash: str) -> Optional[dict]:
    """Check Redis cache for existing response."""
    try:
        redis_client = get_redis_client()
        cached = redis_client.get(f"rag:response:{query_hash}")
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")
    return None


def cache_response(query_hash: str, response: dict, ttl: int = 3600):
    """Cache response in Redis."""
    try:
        redis_client = get_redis_client()
        redis_client.setex(
            f"rag:response:{query_hash}",
            ttl,
            json.dumps(response)
        )
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="chat", methods=["POST"])
async def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main chat endpoint for RAG Q&A.

    Request Body:
    {
        "query": "What is the vacation policy?",
        "user_id": "user@company.com",
        "session_id": "optional-session-id"
    }

    Response:
    {
        "answer": "According to the HR policy document...",
        "sources": [...],
        "session_id": "...",
        "usage": {...}
    }
    """
    try:
        # Parse request
        req_body = req.get_json()
        query = req_body.get("query")
        user_id = req_body.get("user_id", "anonymous")
        session_id = req_body.get("session_id")

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "Query is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Processing query for user {user_id}: {query[:50]}...")

        # Check cache
        query_hash = hashlib.md5(f"{query}:{session_id}".encode()).hexdigest()
        cached = get_cached_response(query_hash)
        if cached:
            logger.info("Returning cached response")
            return func.HttpResponse(
                json.dumps(cached),
                mimetype="application/json"
            )

        # Get/create session
        session = get_or_create_session(user_id, session_id)

        # Get chat history
        chat_history = get_chat_history(session["id"]) if session_id else []

        # RAG Pipeline
        # 1. Retrieve relevant documents
        documents = retrieve_documents(query)

        if not documents:
            response_data = {
                "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing or ask about a different topic.",
                "sources": [],
                "session_id": session["id"],
                "usage": {"total_tokens": 0}
            }
            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json"
            )

        # 2. Build augmented prompt
        messages = build_augmented_prompt(query, documents, chat_history)

        # 3. Generate response
        generation_result = generate_response(messages)

        # 4. Prepare sources
        sources = [
            {
                "title": doc["title"],
                "source": doc["source"],
                "page": doc["page"],
                "relevance_score": doc["score"]
            }
            for doc in documents
        ]

        # 5. Save to history
        save_chat_turn(
            session["id"],
            query,
            generation_result["content"],
            sources
        )

        # 6. Prepare response
        response_data = {
            "answer": generation_result["content"],
            "sources": sources,
            "session_id": session["id"],
            "usage": generation_result["usage"]
        }

        # 7. Cache response
        cache_response(query_hash, response_data)

        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
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
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


@app.route(route="sessions/{session_id}/history", methods=["GET"])
async def get_session_history(req: func.HttpRequest) -> func.HttpResponse:
    """Get chat history for a session."""
    try:
        session_id = req.route_params.get("session_id")
        limit = int(req.params.get("limit", 20))

        container = get_cosmos_container("chatHistory")

        query = f"SELECT * FROM c WHERE c.sessionId = @sessionId ORDER BY c.timestamp DESC OFFSET 0 LIMIT {limit}"

        items = list(container.query_items(
            query=query,
            parameters=[{"name": "@sessionId", "value": session_id}],
            enable_cross_partition_query=False
        ))

        return func.HttpResponse(
            json.dumps({"history": items}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


# ==============================================================================
# Event Grid Trigger for Document Ingestion
# ==============================================================================

@app.function_name(name="DocumentIngestionTrigger")
@app.event_grid_trigger(arg_name="event")
async def document_ingestion_trigger(event: func.EventGridEvent):
    """
    Triggered when new document is uploaded to blob storage.
    Initiates the document processing pipeline.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1]

        logger.info(f"New document uploaded: {blob_name}")

        # TODO: Call Durable Functions orchestrator for document processing
        # This would include:
        # 1. Download document from blob
        # 2. Extract text using Document Intelligence
        # 3. Chunk the document
        # 4. Generate embeddings
        # 5. Index in Azure AI Search

        logger.info(f"Document processing initiated for: {blob_name}")

    except Exception as e:
        logger.error(f"Error processing document event: {e}", exc_info=True)
        raise
