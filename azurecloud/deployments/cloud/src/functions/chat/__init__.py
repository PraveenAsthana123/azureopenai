"""
RAG Chat Function - Azure Functions HTTP trigger.

Handles chat requests with RAG retrieval and response generation.
"""

import azure.functions as func
import json
import logging
import os
import uuid
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# Initialize clients
credential = DefaultAzureCredential()

# Azure OpenAI client
aoai_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
    api_version="2024-02-15-preview"
)

# Azure Search client
search_client = SearchClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    index_name=os.environ.get("AZURE_SEARCH_INDEX", "rag-multimodal-index"),
    credential=credential
)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main chat endpoint.

    POST /api/chat
    {
        "question": "string",
        "session_id": "string (optional)",
        "user_id": "string",
        "stream": false,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    """
    logger.info("Chat request received")

    try:
        # Parse request
        req_body = req.get_json()
        question = req_body.get("question")
        session_id = req_body.get("session_id") or str(uuid.uuid4())
        user_id = req_body.get("user_id", "anonymous")
        temperature = req_body.get("temperature", 0.7)
        max_tokens = req_body.get("max_tokens", 1000)

        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Question is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Get user from token (Entra ID)
        user_claims = _get_user_claims(req)
        if user_claims:
            user_id = user_claims.get("oid", user_id)

        # 1. Generate query embedding
        embedding_response = aoai_client.embeddings.create(
            model=os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
            input=question
        )
        query_embedding = embedding_response.data[0].embedding

        # 2. Hybrid search in Azure AI Search
        vector_query = VectorizedQuery(
            vector=query_embedding,
            fields="content_vector",
            k_nearest_neighbors=5
        )

        search_results = search_client.search(
            search_text=question,
            vector_queries=[vector_query],
            top=5,
            query_type="semantic",
            semantic_configuration_name="default",
            select=["id", "content_text", "title", "metadata", "created_at"]
        )

        # 3. Build context from search results
        context_parts = []
        sources = []
        min_score = float(os.environ.get("MIN_RELEVANCE_SCORE", "0.7"))

        for i, result in enumerate(search_results):
            score = result.get("@search.score", 0)
            if score >= min_score:
                content = result.get("content_text", "")
                title = result.get("title", f"Source {i+1}")
                context_parts.append(f"[{title}]: {content}")
                sources.append({
                    "id": result.get("id"),
                    "title": title,
                    "score": round(score, 4),
                    "metadata": result.get("metadata", {})
                })

        context = "\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # 4. Build messages
        system_prompt = """You are a helpful assistant that answers questions based on the provided context.

Rules:
- Only use information from the provided sources
- Cite sources when making claims: [Source Title]
- If information is not in the context, say so
- Be concise but complete
- Maintain a professional tone"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]

        # 5. Generate response
        chat_deployment = os.environ.get("CHAT_DEPLOYMENT", "gpt-4o-mini")

        completion = aoai_client.chat.completions.create(
            model=chat_deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        answer = completion.choices[0].message.content

        # 6. Build response
        response = {
            "answer": answer,
            "sources": sources,
            "session_id": session_id,
            "model": chat_deployment,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
                "sources_found": len(sources)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Log metrics for monitoring
        _log_metrics(
            user_id=user_id,
            session_id=session_id,
            tokens_used=completion.usage.total_tokens,
            sources_found=len(sources),
            latency_ms=0  # Would need to track timing
        )

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _get_user_claims(req: func.HttpRequest) -> dict:
    """Extract user claims from Entra ID token."""
    # In production, Azure Functions with EasyAuth populates these headers
    claims = {}

    if "X-MS-CLIENT-PRINCIPAL-ID" in req.headers:
        claims["oid"] = req.headers["X-MS-CLIENT-PRINCIPAL-ID"]

    if "X-MS-CLIENT-PRINCIPAL-NAME" in req.headers:
        claims["name"] = req.headers["X-MS-CLIENT-PRINCIPAL-NAME"]

    return claims


def _log_metrics(
    user_id: str,
    session_id: str,
    tokens_used: int,
    sources_found: int,
    latency_ms: int
):
    """Log custom metrics to Application Insights."""
    from opencensus.ext.azure import metrics_exporter
    from opencensus.stats import aggregation, measure, stats, view

    # This would be set up once at module level in production
    logger.info(
        "RAG Metrics",
        extra={
            "custom_dimensions": {
                "user_id": user_id,
                "session_id": session_id,
                "tokens_used": tokens_used,
                "sources_found": sources_found,
                "latency_ms": latency_ms
            }
        }
    )
