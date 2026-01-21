"""
UCP Portal Backend API - Universal Control Plane for WebLLM Platform
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from config import settings
from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse,
    ModelInfo,
    RoutingDecision,
    UsageStats,
)
from router import HybridRouter
from services import (
    AzureOpenAIService,
    CosmosDBService,
    MLCLLMService,
    RedisService,
    ServiceBusService,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "webllm_requests_total",
    "Total number of requests",
    ["tier", "model", "status"],
)
REQUEST_LATENCY = Histogram(
    "webllm_request_latency_seconds",
    "Request latency in seconds",
    ["tier", "model"],
)
TOKENS_PROCESSED = Counter(
    "webllm_tokens_processed_total",
    "Total tokens processed",
    ["tier", "model", "direction"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    logger.info("Starting UCP Portal Backend")

    # Initialize services
    app.state.redis = RedisService()
    app.state.cosmos = CosmosDBService()
    app.state.servicebus = ServiceBusService()
    app.state.azure_openai = AzureOpenAIService()
    app.state.mlc_llm = MLCLLMService()
    app.state.router = HybridRouter(
        azure_openai=app.state.azure_openai,
        mlc_llm=app.state.mlc_llm,
        redis=app.state.redis,
    )

    await app.state.redis.connect()
    await app.state.cosmos.connect()

    yield

    # Cleanup
    logger.info("Shutting down UCP Portal Backend")
    await app.state.redis.disconnect()


app = FastAPI(
    title="WebLLM Platform - UCP Portal API",
    description="Universal Control Plane for hybrid LLM inference",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )

    return response


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Check health of all services."""
    redis_healthy = await request.app.state.redis.health_check()
    cosmos_healthy = await request.app.state.cosmos.health_check()
    mlc_healthy = await request.app.state.mlc_llm.health_check()
    azure_healthy = await request.app.state.azure_openai.health_check()

    return HealthResponse(
        status="healthy" if all([redis_healthy, cosmos_healthy]) else "degraded",
        browser={"healthy": True, "message": "Client-side inference"},
        on_premise={
            "healthy": mlc_healthy,
            "message": "MLC LLM cluster" if mlc_healthy else "MLC LLM unavailable",
        },
        cloud={
            "healthy": azure_healthy,
            "message": "Azure OpenAI" if azure_healthy else "Azure OpenAI unavailable",
        },
        redis={"healthy": redis_healthy},
        cosmos={"healthy": cosmos_healthy},
    )


@app.get("/ready")
async def readiness_check(request: Request):
    """Kubernetes readiness probe."""
    redis_healthy = await request.app.state.redis.health_check()
    if not redis_healthy:
        raise HTTPException(status_code=503, detail="Redis not ready")
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/models", response_model=list[ModelInfo])
async def list_models(request: Request) -> list[ModelInfo]:
    """List all available models across tiers."""
    models = []

    # Browser models
    browser_models = [
        ModelInfo(
            id="Llama-3.1-8B-Instruct-q4f16_1-MLC",
            name="Llama 3.1 8B",
            tier="browser",
            provider="WebLLM",
            max_context=4096,
            available=True,
        ),
        ModelInfo(
            id="Phi-3-mini-4k-instruct-q4f16_1-MLC",
            name="Phi-3 Mini",
            tier="browser",
            provider="WebLLM",
            max_context=4096,
            available=True,
        ),
    ]
    models.extend(browser_models)

    # On-premise models
    on_premise_models = await request.app.state.mlc_llm.list_models()
    models.extend(on_premise_models)

    # Cloud models
    cloud_models = await request.app.state.azure_openai.list_models()
    models.extend(cloud_models)

    return models


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
):
    """
    OpenAI-compatible chat completions endpoint with hybrid routing.
    """
    start_time = time.time()
    router: HybridRouter = request.app.state.router

    try:
        # Determine routing
        decision = router.determine_route(
            messages=body.messages,
            preferred_tier=body.tier,
            privacy_level=body.privacy_level,
            latency_requirement=body.latency_requirement,
        )

        logger.info(
            "routing_decision",
            tier=decision.tier,
            model=decision.model,
            reason=decision.reason,
        )

        # Handle streaming
        if body.stream:
            return StreamingResponse(
                router.generate_stream(
                    messages=body.messages,
                    decision=decision,
                    max_tokens=body.max_tokens,
                    temperature=body.temperature,
                    top_p=body.top_p,
                ),
                media_type="text/event-stream",
            )

        # Non-streaming response
        response = await router.generate(
            messages=body.messages,
            decision=decision,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
        )

        latency = time.time() - start_time

        # Record metrics
        REQUEST_COUNT.labels(
            tier=decision.tier,
            model=decision.model,
            status="success",
        ).inc()
        REQUEST_LATENCY.labels(
            tier=decision.tier,
            model=decision.model,
        ).observe(latency)

        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            model=decision.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content,
                    },
                    "finish_reason": "stop",
                }
            ],
            usage={
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.prompt_tokens + response.completion_tokens,
            },
            tier=decision.tier,
            latency_ms=round(latency * 1000),
        )

    except Exception as e:
        REQUEST_COUNT.labels(
            tier=body.tier or "auto",
            model="unknown",
            status="error",
        ).inc()

        logger.error("chat_completion_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/routing/decide", response_model=RoutingDecision)
async def get_routing_decision(
    request: Request,
    message: str,
    privacy_level: str = "medium",
    latency_requirement: str = "medium",
) -> RoutingDecision:
    """Preview routing decision without making a request."""
    router: HybridRouter = request.app.state.router

    decision = router.determine_route(
        messages=[{"role": "user", "content": message}],
        preferred_tier=None,
        privacy_level=privacy_level,
        latency_requirement=latency_requirement,
    )

    return decision


@app.get("/v1/stats", response_model=UsageStats)
async def get_usage_stats(
    request: Request,
    time_range: str = "24h",
) -> UsageStats:
    """Get usage statistics."""
    redis: RedisService = request.app.state.redis
    cosmos: CosmosDBService = request.app.state.cosmos

    stats = await cosmos.get_usage_stats(time_range)

    return UsageStats(
        total_requests=stats.get("total_requests", 0),
        browser_requests=stats.get("browser_requests", 0),
        on_premise_requests=stats.get("on_premise_requests", 0),
        cloud_requests=stats.get("cloud_requests", 0),
        avg_latency_ms=stats.get("avg_latency_ms", 0),
        total_tokens=stats.get("total_tokens", 0),
        estimated_cost=stats.get("estimated_cost", 0.0),
        error_rate=stats.get("error_rate", 0.0),
    )


@app.post("/v1/agents/broadcast")
async def broadcast_to_agents(
    request: Request,
    message: dict,
):
    """Broadcast message to all agents via Service Bus."""
    servicebus: ServiceBusService = request.app.state.servicebus
    await servicebus.broadcast(message)
    return {"status": "sent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        workers=settings.workers,
    )
