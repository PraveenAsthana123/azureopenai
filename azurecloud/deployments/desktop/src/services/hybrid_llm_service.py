"""
Hybrid LLM Service - Claude for chat + Azure/OpenAI for embeddings.

Since Claude doesn't provide embeddings, this service combines:
- Anthropic Claude for chat completions (high quality reasoning)
- Azure OpenAI or OpenAI for embeddings

This gives you the best of both worlds.
"""

import logging
from typing import AsyncGenerator, Optional

from src.services.llm_service import (
    BaseLLMService,
    AnthropicService,
    AzureOpenAIService,
    OpenAIService,
    OllamaService
)

logger = logging.getLogger(__name__)


class HybridClaudeService(BaseLLMService):
    """
    Hybrid service: Claude for chat, separate provider for embeddings.

    Example configurations:
    - Claude + Azure OpenAI embeddings (recommended for enterprise)
    - Claude + OpenAI embeddings (simple setup)
    - Claude + Ollama embeddings (fully local embeddings)
    """

    def __init__(
        self,
        # Claude settings
        anthropic_api_key: str,
        claude_model: str = "claude-sonnet-4-20250514",

        # Embedding provider settings
        embedding_provider: str = "azure_openai",  # "azure_openai", "openai", "ollama"

        # Azure OpenAI embeddings
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_embedding_deployment: str = "text-embedding-3-large",

        # OpenAI embeddings
        openai_api_key: Optional[str] = None,
        openai_embedding_model: str = "text-embedding-3-small",

        # Ollama embeddings
        ollama_base_url: str = "http://localhost:11434",
        ollama_embedding_model: str = "nomic-embed-text"
    ):
        # Initialize Claude for chat
        self.chat_service = AnthropicService(
            api_key=anthropic_api_key,
            model=claude_model
        )

        # Initialize embedding service based on provider
        self.embedding_provider = embedding_provider

        if embedding_provider == "azure_openai":
            if not azure_endpoint:
                raise ValueError("Azure OpenAI endpoint required for embeddings")
            self.embedding_service = AzureOpenAIService(
                endpoint=azure_endpoint,
                api_key=azure_api_key,
                embedding_deployment=azure_embedding_deployment
            )
        elif embedding_provider == "openai":
            if not openai_api_key:
                raise ValueError("OpenAI API key required for embeddings")
            self.embedding_service = OpenAIService(
                api_key=openai_api_key,
                embedding_model=openai_embedding_model
            )
        elif embedding_provider == "ollama":
            self.embedding_service = OllamaService(
                base_url=ollama_base_url,
                embedding_model=ollama_embedding_model
            )
        else:
            raise ValueError(f"Unknown embedding provider: {embedding_provider}")

        logger.info(f"Hybrid service initialized: Claude + {embedding_provider} embeddings")

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion using Claude."""
        return await self.chat_service.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using configured provider."""
        return await self.embedding_service.embed(text)

    async def health_check(self) -> bool:
        """Check if both services are available."""
        chat_ok = await self.chat_service.health_check()
        embed_ok = await self.embedding_service.health_check()

        if not chat_ok:
            logger.warning("Claude chat service unavailable")
        if not embed_ok:
            logger.warning(f"{self.embedding_provider} embedding service unavailable")

        return chat_ok and embed_ok

    async def get_status(self) -> dict:
        """Get detailed status of both services."""
        return {
            "chat": {
                "provider": "anthropic",
                "model": self.chat_service.model,
                "healthy": await self.chat_service.health_check()
            },
            "embeddings": {
                "provider": self.embedding_provider,
                "healthy": await self.embedding_service.health_check()
            }
        }


class AzureAIFoundryClaudeService(BaseLLMService):
    """
    Claude deployed through Azure AI Foundry.

    Uses Azure-hosted Claude endpoint instead of direct Anthropic API.
    Still requires separate embedding service.
    """

    def __init__(
        self,
        # Azure AI Foundry Claude endpoint
        endpoint: str,
        api_key: str,
        model: str = "claude-3-5-sonnet",

        # Embedding settings (Azure OpenAI)
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_key: Optional[str] = None,
        embedding_deployment: str = "text-embedding-3-large"
    ):
        import httpx

        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

        # Azure OpenAI for embeddings
        if azure_openai_endpoint:
            self.embedding_service = AzureOpenAIService(
                endpoint=azure_openai_endpoint,
                api_key=azure_openai_key,
                embedding_deployment=embedding_deployment
            )
        else:
            self.embedding_service = None

    async def _get_client(self):
        import httpx
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=120,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion using Azure-hosted Claude."""
        client = await self._get_client()

        # Azure AI Foundry uses OpenAI-compatible API
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if stream:
            return self._stream_chat(client, payload)

        response = await client.post(
            f"{self.endpoint}/v1/chat/completions",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _stream_chat(self, client, payload) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        async with client.stream(
            "POST",
            f"{self.endpoint}/v1/chat/completions",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and "[DONE]" not in line:
                    import json
                    try:
                        data = json.loads(line[6:])
                        if data["choices"] and data["choices"][0].get("delta", {}).get("content"):
                            yield data["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using Azure OpenAI."""
        if not self.embedding_service:
            raise NotImplementedError(
                "Embeddings require Azure OpenAI configuration"
            )
        return await self.embedding_service.embed(text)

    async def health_check(self) -> bool:
        """Check if Azure AI Foundry Claude is accessible."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Azure AI Foundry Claude health check failed: {e}")
            return False


def create_hybrid_claude_service(settings) -> HybridClaudeService:
    """
    Factory function to create hybrid Claude service from settings.

    Reads from settings and creates appropriate service configuration.
    """
    # Get Claude settings
    anthropic_settings = settings.anthropic

    # Determine embedding provider
    embedding_provider = getattr(anthropic_settings, 'embedding_provider', 'azure_openai')

    # Build kwargs based on embedding provider
    kwargs = {
        "anthropic_api_key": anthropic_settings.api_key,
        "claude_model": anthropic_settings.model,
        "embedding_provider": embedding_provider
    }

    if embedding_provider == "azure_openai":
        kwargs.update({
            "azure_endpoint": settings.azure_openai.endpoint,
            "azure_api_key": settings.azure_openai.api_key,
            "azure_embedding_deployment": settings.azure_openai.embedding_deployment
        })
    elif embedding_provider == "openai":
        kwargs.update({
            "openai_api_key": settings.openai.api_key,
            "openai_embedding_model": settings.openai.embedding_model
        })
    elif embedding_provider == "ollama":
        kwargs.update({
            "ollama_base_url": settings.ollama.base_url,
            "ollama_embedding_model": settings.ollama.embedding_model
        })

    return HybridClaudeService(**kwargs)
