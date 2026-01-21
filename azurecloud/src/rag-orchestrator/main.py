"""
Enterprise RAG Orchestrator - FastAPI Application
Production-ready API for RAG queries with authentication, rate limiting, and observability.
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import structlog
from azure.cosmos.aio import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field
from starlette.responses import Response

from rag_chain import RAGOrchestrator, RAGResponse, UserContext

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "rag_requests_total",
    "Total RAG requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)
CACHE_HITS = Counter("rag_cache_hits_total", "Cache hit count")
CACHE_MISSES = Counter("rag_cache_misses_total", "Cache miss count")


# Request/Response models
class QueryRequest(BaseModel):
    """RAG query request."""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    filters: dict[str, Any] = Field(default_factory=dict, description="Search filters")
    session_id: str | None = Field(None, description="Session ID for conversation context")
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation turns",
    )
    include_citations: bool = Field(True, description="Include source citations")
    max_chunks: int = Field(5, ge=1, le=20, description="Maximum context chunks")


class QueryResponse(BaseModel):
    """RAG query response."""
    answer: str
    citations: list[dict[str, Any]]
    confidence: float
    intent: str
    query_rewritten: str
    cached: bool
    latency_ms: float
    request_id: str
    timestamp: str


class FeedbackRequest(BaseModel):
    """User feedback on response."""
    query_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_type: str = Field(..., pattern="^(helpful|not_helpful|inaccurate|incomplete|other)$")
    feedback_text: str | None = None
    session_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    dependencies: dict[str, str]


# Application state
class AppState:
    orchestrator: RAGOrchestrator | None = None
    cosmos_client: CosmosClient | None = None
    healthy: bool = False


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting RAG Orchestrator...")

    try:
        # Initialize credentials
        credential = DefaultAzureCredential()

        # Load secrets from Key Vault
        key_vault_url = os.getenv("KEY_VAULT_URL")
        if key_vault_url:
            secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
            # Secrets would be loaded here if needed
            await secret_client.close()

        # Initialize RAG orchestrator
        app_state.orchestrator = RAGOrchestrator(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT", ""),
            cosmos_endpoint=os.getenv("COSMOS_ENDPOINT", ""),
            cosmos_database=os.getenv("COSMOS_DATABASE", "genai_platform"),
        )
        await app_state.orchestrator.initialize()

        # Initialize Cosmos client for feedback
        cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
        if cosmos_endpoint:
            app_state.cosmos_client = CosmosClient(cosmos_endpoint, credential)

        app_state.healthy = True
        logger.info("RAG Orchestrator initialized successfully")

        yield

    finally:
        # Cleanup
        logger.info("Shutting down RAG Orchestrator...")
        if app_state.cosmos_client:
            await app_state.cosmos_client.close()
        app_state.healthy = False


# Create FastAPI app
app = FastAPI(
    title="Enterprise RAG Orchestrator",
    description="Production RAG API with Azure OpenAI and AI Search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "").split(",") or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request logging and metrics
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Log requests and collect metrics."""
    start_time = time.perf_counter()
    request_id = request.headers.get("X-Request-Id", str(time.time()))

    # Add request context
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        user_id=request.headers.get("X-User-Id", "anonymous"),
    )

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        logger.error("request_failed", request_id=request_id, error=str(e))
        status = 500
        raise

    finally:
        latency = time.perf_counter() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(latency)

        logger.info(
            "request_completed",
            request_id=request_id,
            status=status,
            latency_ms=latency * 1000,
        )

    return response


def get_user_context(request: Request) -> UserContext:
    """Extract user context from request headers (set by APIM)."""
    return UserContext(
        user_id=request.headers.get("X-User-Id", "anonymous"),
        user_name=request.headers.get("X-User-Name", ""),
        groups=request.headers.get("X-User-Groups", "[]"),
        roles=request.headers.get("X-User-Roles", "[]"),
    )


@app.post("/query", response_model=QueryResponse)
async def query(
    request: Request,
    body: QueryRequest,
    user: UserContext = Depends(get_user_context),
):
    """
    Process a RAG query.

    Returns an answer grounded in retrieved documents with citations.
    """
    if not app_state.orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")

    request_id = request.headers.get("X-Request-Id", str(time.time()))
    start_time = time.perf_counter()

    try:
        result: RAGResponse = await app_state.orchestrator.process_query(
            query=body.query,
            user=user,
            session_id=body.session_id,
            conversation_history=body.conversation_history,
            filters=body.filters,
        )

        # Track cache metrics
        if result.cached:
            CACHE_HITS.inc()
        else:
            CACHE_MISSES.inc()

        latency_ms = (time.perf_counter() - start_time) * 1000

        return QueryResponse(
            answer=result.answer,
            citations=[
                {
                    "document_id": c.document_id,
                    "title": c.title,
                    "excerpt": c.excerpt,
                    "relevance_score": c.relevance_score,
                }
                for c in result.citations
            ] if body.include_citations else [],
            confidence=result.confidence,
            intent=result.intent,
            query_rewritten=result.query_rewritten,
            cached=result.cached,
            latency_ms=latency_ms,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error("query_failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail="Query processing failed")


@app.post("/feedback", status_code=202)
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    user: UserContext = Depends(get_user_context),
):
    """Submit feedback on a RAG response."""
    if not app_state.cosmos_client:
        raise HTTPException(status_code=503, detail="Feedback service not available")

    try:
        database = app_state.cosmos_client.get_database_client(
            os.getenv("COSMOS_DATABASE", "genai_platform")
        )
        container = database.get_container_client("user_feedback")

        feedback_doc = {
            "id": f"{user.user_id}-{body.query_id}-{int(time.time())}",
            "user_id": user.user_id,
            "query_id": body.query_id,
            "session_id": body.session_id,
            "rating": body.rating,
            "feedback_type": body.feedback_type,
            "feedback_text": body.feedback_text,
            "created_at": datetime.utcnow().isoformat(),
        }

        await container.create_item(feedback_doc)

        return {"status": "accepted", "feedback_id": feedback_doc["id"]}

    except Exception as e:
        logger.error("feedback_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save feedback")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    dependencies = {}

    # Check orchestrator
    if app_state.orchestrator:
        dependencies["orchestrator"] = "healthy"
    else:
        dependencies["orchestrator"] = "unhealthy"

    # Check Cosmos
    if app_state.cosmos_client:
        dependencies["cosmos"] = "healthy"
    else:
        dependencies["cosmos"] = "not_configured"

    overall_status = "healthy" if app_state.healthy else "unhealthy"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
    )


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    if not app_state.healthy:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-Id", ""),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
    )
