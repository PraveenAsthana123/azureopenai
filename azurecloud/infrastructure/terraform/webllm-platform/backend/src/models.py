"""
Pydantic models for API requests and responses.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Request body for chat completions."""
    messages: list[ChatMessage]
    model: Optional[str] = None
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.95, ge=0, le=1)
    stream: bool = False

    # Routing hints
    tier: Optional[Literal["browser", "on_premise", "cloud"]] = None
    privacy_level: str = "medium"
    latency_requirement: str = "medium"


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response from chat completions."""
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(__import__("time").time()))
    model: str
    choices: list[dict]
    usage: dict
    tier: str
    latency_ms: int


class GenerationResult(BaseModel):
    """Result from a generation request."""
    content: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str = "stop"


class RoutingDecision(BaseModel):
    """Routing decision for a request."""
    tier: Literal["browser", "on_premise", "cloud"]
    model: str
    reason: str
    estimated_latency_ms: int
    estimated_cost: float


class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    name: str
    tier: Literal["browser", "on_premise", "cloud"]
    provider: str
    max_context: int
    available: bool
    description: Optional[str] = None


class HealthStatus(BaseModel):
    """Health status for a component."""
    healthy: bool
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    browser: HealthStatus
    on_premise: HealthStatus
    cloud: HealthStatus
    redis: HealthStatus
    cosmos: HealthStatus


class UsageStats(BaseModel):
    """Usage statistics."""
    total_requests: int
    browser_requests: int
    on_premise_requests: int
    cloud_requests: int
    avg_latency_ms: float
    total_tokens: int
    estimated_cost: float
    error_rate: float
