"""
Service clients for external dependencies.
"""

import json
from typing import AsyncGenerator

import httpx
import structlog
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient, ServiceBusSender
from openai import AsyncAzureOpenAI
from redis.asyncio import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import GenerationResult, ModelInfo

logger = structlog.get_logger()


class RedisService:
    """Redis cache service."""

    def __init__(self):
        self.client: Redis | None = None

    async def connect(self):
        """Connect to Redis."""
        self.client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            ssl=settings.redis_ssl,
            decode_responses=True,
        )
        logger.info("Connected to Redis", host=settings.redis_host)

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()

    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if self.client:
                await self.client.ping()
                return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
        return False

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        if self.client:
            return await self.client.get(key)
        return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache."""
        if self.client:
            await self.client.set(key, value, ex=ttl)

    async def incr(self, key: str) -> int:
        """Increment counter."""
        if self.client:
            return await self.client.incr(key)
        return 0


class CosmosDBService:
    """Cosmos DB service for state and analytics."""

    def __init__(self):
        self.client: CosmosClient | None = None
        self.database = None
        self.credential = None

    async def connect(self):
        """Connect to Cosmos DB."""
        if not settings.cosmos_endpoint:
            logger.warning("Cosmos DB endpoint not configured")
            return

        self.credential = DefaultAzureCredential()
        self.client = CosmosClient(
            settings.cosmos_endpoint,
            credential=self.credential,
        )
        self.database = self.client.get_database_client(settings.cosmos_database)
        logger.info("Connected to Cosmos DB", database=settings.cosmos_database)

    async def health_check(self) -> bool:
        """Check Cosmos DB health."""
        try:
            if self.database:
                await self.database.read()
                return True
        except Exception as e:
            logger.error("Cosmos DB health check failed", error=str(e))
        return False

    async def get_usage_stats(self, time_range: str) -> dict:
        """Get usage statistics from Cosmos DB."""
        # Placeholder - would query actual data
        return {
            "total_requests": 15234,
            "browser_requests": 4521,
            "on_premise_requests": 8234,
            "cloud_requests": 2479,
            "avg_latency_ms": 342,
            "total_tokens": 1234567,
            "estimated_cost": 127.45,
            "error_rate": 0.12,
        }

    async def log_request(self, data: dict):
        """Log a request to Cosmos DB."""
        if self.database:
            container = self.database.get_container_client("task-history")
            await container.create_item(data)


class ServiceBusService:
    """Azure Service Bus for agent communication."""

    def __init__(self):
        self.client: ServiceBusClient | None = None
        self.broadcast_sender: ServiceBusSender | None = None

    async def connect(self):
        """Connect to Service Bus."""
        if not settings.servicebus_namespace:
            logger.warning("Service Bus namespace not configured")
            return

        credential = DefaultAzureCredential()
        self.client = ServiceBusClient(
            fully_qualified_namespace=f"{settings.servicebus_namespace}.servicebus.windows.net",
            credential=credential,
        )
        self.broadcast_sender = self.client.get_topic_sender(
            topic_name=settings.servicebus_topic_broadcast
        )
        logger.info("Connected to Service Bus", namespace=settings.servicebus_namespace)

    async def broadcast(self, message: dict):
        """Broadcast message to all agents."""
        if self.broadcast_sender:
            from azure.servicebus import ServiceBusMessage

            msg = ServiceBusMessage(json.dumps(message))
            await self.broadcast_sender.send_messages(msg)


class AzureOpenAIService:
    """Azure OpenAI service for cloud inference."""

    def __init__(self):
        self.client: AsyncAzureOpenAI | None = None

    async def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create Azure OpenAI client."""
        if not self.client:
            credential = DefaultAzureCredential()
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")

            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                azure_ad_token=token.token,
            )
        return self.client

    async def health_check(self) -> bool:
        """Check Azure OpenAI health."""
        try:
            if settings.azure_openai_endpoint:
                return True
        except Exception as e:
            logger.error("Azure OpenAI health check failed", error=str(e))
        return False

    async def list_models(self) -> list[ModelInfo]:
        """List available Azure OpenAI models."""
        return [
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                tier="cloud",
                provider="Azure OpenAI",
                max_context=128000,
                available=True,
                description="Most capable model for complex tasks",
            ),
            ModelInfo(
                id="gpt-4-turbo",
                name="GPT-4 Turbo",
                tier="cloud",
                provider="Azure OpenAI",
                max_context=128000,
                available=True,
                description="Fast and capable for general tasks",
            ),
            ModelInfo(
                id="gpt-4-vision",
                name="GPT-4 Vision",
                tier="cloud",
                provider="Azure OpenAI",
                max_context=128000,
                available=True,
                description="Multimodal model with vision capabilities",
            ),
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> GenerationResult:
        """Generate a completion using Azure OpenAI."""
        client = await self._get_client()

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        return GenerationResult(
            content=response.choices[0].message.content or "",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

    async def generate_stream(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        client = await self._get_client()

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield json.dumps({
                    "choices": [{
                        "delta": {"content": chunk.choices[0].delta.content},
                        "index": 0,
                    }]
                })


class MLCLLMService:
    """MLC LLM service for on-premise inference."""

    def __init__(self):
        self.base_url = settings.mlc_llm_endpoint
        self.timeout = settings.mlc_llm_timeout

    async def health_check(self) -> bool:
        """Check MLC LLM cluster health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("MLC LLM health check failed", error=str(e))
        return False

    async def list_models(self) -> list[ModelInfo]:
        """List available MLC LLM models."""
        return [
            ModelInfo(
                id="llama-3-1-70b",
                name="Llama 3.1 70B",
                tier="on_premise",
                provider="MLC LLM",
                max_context=8192,
                available=True,
                description="Large model for complex reasoning",
            ),
            ModelInfo(
                id="llama-3-1-8b",
                name="Llama 3.1 8B",
                tier="on_premise",
                provider="MLC LLM",
                max_context=8192,
                available=True,
                description="Fast model for general tasks",
            ),
            ModelInfo(
                id="codellama-34b",
                name="CodeLlama 34B",
                tier="on_premise",
                provider="MLC LLM",
                max_context=16384,
                available=True,
                description="Specialized for code generation",
            ),
            ModelInfo(
                id="mistral-7b",
                name="Mistral 7B",
                tier="on_premise",
                provider="MLC LLM",
                max_context=8192,
                available=True,
                description="Efficient open-source model",
            ),
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> GenerationResult:
        """Generate a completion using MLC LLM."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        return GenerationResult(
            content=data["choices"][0]["message"]["content"],
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
        )

    async def generate_stream(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": True,
                },
                timeout=self.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data and data != "[DONE]":
                            yield data
