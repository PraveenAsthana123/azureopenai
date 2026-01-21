"""
Hybrid routing logic for WebLLM Platform.
"""

import re
from typing import AsyncGenerator, Literal, Optional

import structlog

from models import ChatMessage, GenerationResult, RoutingDecision

logger = structlog.get_logger()


class HybridRouter:
    """Routes requests to appropriate inference tier."""

    # Sensitive data patterns
    SENSITIVE_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{16}\b",  # Credit card
        r"\bpassword\s*[:=]\s*\S+",  # Password
        r"\b(secret|api[_-]?key|token)\s*[:=]\s*\S+",  # Secrets
        r"\b(confidential|private|sensitive)\b",  # Keywords
    ]

    # Code patterns
    CODE_PATTERNS = [
        r"```\w*\n",  # Code blocks
        r"\bdef\s+\w+\s*\(",  # Python functions
        r"\bfunction\s+\w+\s*\(",  # JS functions
        r"\bclass\s+\w+",  # Classes
        r"\b(import|from|require)\s+",  # Imports
    ]

    def __init__(self, azure_openai, mlc_llm, redis):
        self.azure_openai = azure_openai
        self.mlc_llm = mlc_llm
        self.redis = redis

    def determine_route(
        self,
        messages: list[dict],
        preferred_tier: Optional[str],
        privacy_level: str,
        latency_requirement: str,
    ) -> RoutingDecision:
        """Determine the best tier for a request."""

        # Extract last user message for analysis
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        message_length = len(last_message)

        # Check for explicit tier preference
        if preferred_tier:
            return RoutingDecision(
                tier=preferred_tier,
                model=self._get_model_for_tier(preferred_tier),
                reason="User preference",
                estimated_latency_ms=self._estimate_latency(preferred_tier),
                estimated_cost=self._estimate_cost(preferred_tier, message_length),
            )

        # Check for sensitive data
        contains_sensitive = self._contains_sensitive_data(last_message)

        if contains_sensitive or privacy_level == "high":
            return RoutingDecision(
                tier="on_premise",
                model="llama-3-1-70b",
                reason="Privacy-sensitive content - using on-premise",
                estimated_latency_ms=500,
                estimated_cost=0.0,
            )

        # Check for code-related tasks
        is_code_task = self._is_code_task(last_message)

        if is_code_task:
            return RoutingDecision(
                tier="on_premise",
                model="codellama-34b",
                reason="Code generation task - using specialized model",
                estimated_latency_ms=600,
                estimated_cost=0.0,
            )

        # Check latency requirements
        if latency_requirement == "low" and message_length < 500:
            return RoutingDecision(
                tier="on_premise",
                model="llama-3-1-8b",
                reason="Low latency requirement - using fast model",
                estimated_latency_ms=200,
                estimated_cost=0.0,
            )

        # Complex tasks go to cloud
        if message_length > 2000 or len(messages) > 10:
            return RoutingDecision(
                tier="cloud",
                model="gpt-4o",
                reason="Complex/long context - using GPT-4o",
                estimated_latency_ms=1000,
                estimated_cost=self._estimate_cost("cloud", message_length),
            )

        # Default: on-premise for cost optimization
        return RoutingDecision(
            tier="on_premise",
            model="llama-3-1-8b",
            reason="Default routing - cost optimized",
            estimated_latency_ms=300,
            estimated_cost=0.0,
        )

    def _contains_sensitive_data(self, text: str) -> bool:
        """Check if text contains sensitive data patterns."""
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_code_task(self, text: str) -> bool:
        """Check if the request is code-related."""
        code_keywords = [
            "write code", "implement", "function", "class",
            "debug", "fix bug", "refactor", "optimize",
            "python", "javascript", "typescript", "java",
        ]

        text_lower = text.lower()
        for keyword in code_keywords:
            if keyword in text_lower:
                return True

        for pattern in self.CODE_PATTERNS:
            if re.search(pattern, text):
                return True

        return False

    def _get_model_for_tier(self, tier: str) -> str:
        """Get default model for a tier."""
        models = {
            "browser": "Llama-3.1-8B-Instruct-q4f16_1-MLC",
            "on_premise": "llama-3-1-8b",
            "cloud": "gpt-4o",
        }
        return models.get(tier, "llama-3-1-8b")

    def _estimate_latency(self, tier: str) -> int:
        """Estimate latency for a tier in milliseconds."""
        latencies = {
            "browser": 1500,
            "on_premise": 300,
            "cloud": 1000,
        }
        return latencies.get(tier, 500)

    def _estimate_cost(self, tier: str, message_length: int) -> float:
        """Estimate cost for a request."""
        if tier != "cloud":
            return 0.0

        # Rough token estimation
        estimated_tokens = message_length / 4
        # GPT-4o pricing: ~$0.005 per 1K tokens (combined)
        return estimated_tokens * 0.000005

    async def generate(
        self,
        messages: list[dict],
        decision: RoutingDecision,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> GenerationResult:
        """Generate a response using the determined tier."""

        if decision.tier == "on_premise":
            return await self.mlc_llm.generate(
                model=decision.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        elif decision.tier == "cloud":
            return await self.azure_openai.generate(
                model=decision.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        else:
            raise ValueError(f"Unsupported tier for server-side generation: {decision.tier}")

    async def generate_stream(
        self,
        messages: list[dict],
        decision: RoutingDecision,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""

        if decision.tier == "on_premise":
            async for chunk in self.mlc_llm.generate_stream(
                model=decision.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                yield f"data: {chunk}\n\n"
        elif decision.tier == "cloud":
            async for chunk in self.azure_openai.generate_stream(
                model=decision.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                yield f"data: {chunk}\n\n"
        else:
            raise ValueError(f"Unsupported tier for streaming: {decision.tier}")

        yield "data: [DONE]\n\n"
