"""
LLM Service - Unified interface for multiple LLM providers.

Supports:
- Ollama (local, offline)
- Azure OpenAI (cloud)
- OpenAI API (cloud)

Automatically connects to Azure services from desktop when configured.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion."""
        pass

    @abstractmethod
    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is available."""
        pass


class OllamaService(BaseLLMService):
    """
    Ollama local LLM service.

    Run locally with: ollama run llama3.2
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion using Ollama."""
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if stream:
            return self._stream_chat(client, payload)

        response = await client.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        async with client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "message" in data:
                        yield data["message"].get("content", "")

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        client = await self._get_client()

        texts = [text] if isinstance(text, str) else text
        embeddings = []

        for t in texts:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": t}
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])

        return embeddings

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available models in Ollama."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]


class AzureOpenAIService(BaseLLMService):
    """
    Azure OpenAI service.

    Connects to Azure OpenAI from desktop using API key or managed identity.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        chat_deployment: str = "gpt-4o-mini",
        embedding_deployment: str = "text-embedding-3-large",
        use_managed_identity: bool = False
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.api_version = api_version
        self.chat_deployment = chat_deployment
        self.embedding_deployment = embedding_deployment
        self.use_managed_identity = use_managed_identity
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Get Azure AD token for managed identity."""
        if self.api_key:
            return self.api_key

        if self._token:
            return self._token

        # Use Azure Identity for managed identity
        from azure.identity.aio import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token = await credential.get_token("https://cognitiveservices.azure.com/.default")
        self._token = token.token
        return self._token

    async def _get_headers(self) -> dict:
        """Get request headers."""
        if self.api_key:
            return {"api-key": self.api_key}
        else:
            token = await self._get_token()
            return {"Authorization": f"Bearer {token}"}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion using Azure OpenAI."""
        client = await self._get_client()
        headers = await self._get_headers()

        url = (
            f"{self.endpoint}/openai/deployments/{self.chat_deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if stream:
            return self._stream_chat(client, url, headers, payload)

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses."""
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and not line.endswith("[DONE]"):
                    import json
                    data = json.loads(line[6:])
                    if data["choices"] and data["choices"][0].get("delta", {}).get("content"):
                        yield data["choices"][0]["delta"]["content"]

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using Azure OpenAI."""
        client = await self._get_client()
        headers = await self._get_headers()

        url = (
            f"{self.endpoint}/openai/deployments/{self.embedding_deployment}"
            f"/embeddings?api-version={self.api_version}"
        )

        texts = [text] if isinstance(text, str) else text

        response = await client.post(
            url,
            json={"input": texts},
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def health_check(self) -> bool:
        """Check if Azure OpenAI is accessible."""
        try:
            client = await self._get_client()
            headers = await self._get_headers()
            # Simple request to check connectivity
            response = await client.get(
                f"{self.endpoint}/openai/models?api-version={self.api_version}",
                headers=headers
            )
            return response.status_code in [200, 401]  # 401 means endpoint works but auth issue
        except Exception as e:
            logger.warning(f"Azure OpenAI health check failed: {e}")
            return False


class AnthropicService(BaseLLMService):
    """
    Anthropic Claude API service.

    Use Claude models directly from Anthropic API.
    Can be called from Azure deployments.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 120
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.anthropic.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
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
        """Generate chat completion using Claude."""
        client = await self._get_client()

        # Extract system message and convert format
        system = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system:
            payload["system"] = system

        if stream:
            return self._stream_chat(client, payload)

        response = await client.post(
            f"{self.base_url}/messages",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses from Claude."""
        payload["stream"] = True

        async with client.stream(
            "POST",
            f"{self.base_url}/messages",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if "text" in delta:
                                yield delta["text"]
                    except json.JSONDecodeError:
                        continue

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """
        Claude doesn't have native embeddings.
        Use a fallback or raise error.
        """
        raise NotImplementedError(
            "Anthropic Claude does not provide embeddings. "
            "Use a separate embedding service (Azure OpenAI, OpenAI, or local)."
        )

    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/messages",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False


class OpenAIService(BaseLLMService):
    """
    OpenAI API service (non-Azure).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small"
    ):
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model
        self.base_url = "https://api.openai.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=60,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate chat completion using OpenAI."""
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if stream:
            # Similar streaming implementation
            pass

        response = await client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI."""
        client = await self._get_client()
        texts = [text] if isinstance(text, str) else text

        response = await client.post(
            f"{self.base_url}/embeddings",
            json={"model": self.embedding_model, "input": texts}
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception:
            return False


# =============================================================================
# Factory Function
# =============================================================================

def create_llm_service(settings) -> BaseLLMService:
    """
    Create LLM service based on settings.

    Args:
        settings: Configuration settings object

    Returns:
        LLM service instance
    """
    from config.settings import LLMProvider

    if settings.llm_provider == LLMProvider.OLLAMA:
        return OllamaService(
            base_url=settings.ollama.base_url,
            model=settings.ollama.model,
            embedding_model=settings.ollama.embedding_model,
            timeout=settings.ollama.timeout
        )

    elif settings.llm_provider == LLMProvider.AZURE_OPENAI:
        return AzureOpenAIService(
            endpoint=settings.azure_openai.endpoint,
            api_key=settings.azure_openai.api_key,
            api_version=settings.azure_openai.api_version,
            chat_deployment=settings.azure_openai.chat_deployment,
            embedding_deployment=settings.azure_openai.embedding_deployment,
            use_managed_identity=settings.azure_openai.use_managed_identity
        )

    elif settings.llm_provider == LLMProvider.OPENAI:
        return OpenAIService(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            embedding_model=settings.openai.embedding_model
        )

    elif settings.llm_provider == LLMProvider.ANTHROPIC:
        return AnthropicService(
            api_key=settings.anthropic.api_key,
            model=settings.anthropic.model,
            timeout=settings.anthropic.timeout
        )

    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
