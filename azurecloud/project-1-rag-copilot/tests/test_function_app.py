"""
Enterprise RAG Knowledge Copilot - Unit Tests
==============================================
Comprehensive tests for RAG pipeline functions
with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock all Azure SDK modules before importing function_app
sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.keyvault.secrets"] = MagicMock()
sys.modules["azure.search.documents"] = MagicMock()
sys.modules["azure.search.documents.models"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()

import function_app


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_documents():
    """Sample retrieved documents for RAG pipeline."""
    return [
        {
            "id": "doc-1",
            "content": "Employees are entitled to 15 days of paid vacation per year.",
            "title": "HR Policy Manual",
            "source": "policies/hr-policy.pdf",
            "page": 12,
            "score": 0.95,
            "reranker_score": 0.88
        },
        {
            "id": "doc-2",
            "content": "Vacation requests must be submitted 2 weeks in advance.",
            "title": "HR Policy Manual",
            "source": "policies/hr-policy.pdf",
            "page": 13,
            "score": 0.87,
            "reranker_score": 0.82
        }
    ]


@pytest.fixture
def sample_chat_history():
    """Sample conversation history."""
    return [
        {"role": "user", "content": "What is the vacation policy?"},
        {"role": "assistant", "content": "Employees get 15 days of paid vacation per year."}
    ]


@pytest.fixture
def mock_http_request():
    """Factory for creating mock HTTP requests."""
    def _make_request(body: dict = None, method: str = "POST", route_params: dict = None, params: dict = None):
        req = MagicMock()
        req.method = method
        req.route_params = route_params or {}
        req.params = params or {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


# ==============================================================================
# Test Embedding Generation
# ==============================================================================

class TestEmbeddingGeneration:
    """Tests for embedding generation."""

    @patch("function_app.get_openai_client")
    def test_generate_embedding_success(self, mock_openai):
        """Test generating an embedding vector."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_embedding("test text")

        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once_with(
            input="test text",
            model="text-embedding-ada-002"
        )


# ==============================================================================
# Test Document Retrieval
# ==============================================================================

class TestDocumentRetrieval:
    """Tests for hybrid document search retrieval."""

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_retrieve_documents_success(self, mock_embed, mock_search):
        """Test retrieving documents with hybrid search."""
        mock_embed.return_value = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: {
            "id": "doc-1",
            "content": "Vacation policy content here.",
            "title": "HR Policy",
            "source": "hr-policy.pdf",
            "page": 5,
            "@search.score": 0.92,
            "@search.reranker_score": 0.85
        }.get(key, None)
        mock_result.get = lambda key, default=None: {
            "id": "doc-1",
            "content": "Vacation policy content here.",
            "title": "HR Policy",
            "source": "hr-policy.pdf",
            "page": 5,
            "@search.score": 0.92,
            "@search.reranker_score": 0.85
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_result]
        mock_search.return_value = mock_client

        results = function_app.retrieve_documents("vacation policy", top_k=5)

        assert len(results) == 1
        assert results[0]["title"] == "HR Policy"
        assert results[0]["score"] == 0.92

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_retrieve_documents_empty(self, mock_embed, mock_search):
        """Test retrieval returns empty list when no results."""
        mock_embed.return_value = [0.1] * 1536
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_search.return_value = mock_client

        results = function_app.retrieve_documents("nonexistent topic")
        assert len(results) == 0


# ==============================================================================
# Test Prompt Building
# ==============================================================================

class TestPromptBuilding:
    """Tests for augmented prompt construction."""

    def test_build_prompt_with_documents(self, sample_documents):
        """Test building prompt with retrieved documents."""
        messages = function_app.build_augmented_prompt("What is vacation policy?", sample_documents)

        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert "HR Policy Manual" in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "What is vacation policy?"

    def test_build_prompt_with_history(self, sample_documents, sample_chat_history):
        """Test building prompt includes chat history."""
        messages = function_app.build_augmented_prompt(
            "How do I request time off?",
            sample_documents,
            sample_chat_history
        )

        assert len(messages) >= 4  # system + 2 history + user
        assert messages[-1]["content"] == "How do I request time off?"


# ==============================================================================
# Test Response Generation
# ==============================================================================

class TestResponseGeneration:
    """Tests for GPT-4o response generation."""

    @patch("function_app.get_openai_client")
    def test_generate_response_success(self, mock_openai):
        """Test generating a response from GPT-4o."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "According to the HR policy, employees get 15 days vacation."
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 700
        mock_response.model = "gpt-4o"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        messages = [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": "What is the vacation policy?"}
        ]

        result = function_app.generate_response(messages)

        assert "content" in result
        assert "vacation" in result["content"].lower()
        assert result["usage"]["total_tokens"] == 700
        assert result["finish_reason"] == "stop"


# ==============================================================================
# Test Session Management
# ==============================================================================

class TestSessionManagement:
    """Tests for session creation and history."""

    @patch("function_app.get_cosmos_container")
    def test_create_new_session(self, mock_cosmos):
        """Test creating a new session."""
        mock_container = MagicMock()
        mock_cosmos.return_value = mock_container

        session = function_app.get_or_create_session("user@company.com")

        assert "id" in session
        assert session["userId"] == "user@company.com"
        assert "createdAt" in session
        mock_container.create_item.assert_called_once()

    @patch("function_app.get_cosmos_container")
    def test_get_existing_session(self, mock_cosmos):
        """Test retrieving an existing session."""
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            "id": "session-123",
            "userId": "user@company.com",
            "createdAt": "2024-01-15T10:00:00",
            "messageCount": 5
        }
        mock_cosmos.return_value = mock_container

        session = function_app.get_or_create_session("user@company.com", "session-123")

        assert session["id"] == "session-123"
        assert session["messageCount"] == 5

    @patch("function_app.get_cosmos_container")
    def test_get_chat_history(self, mock_cosmos):
        """Test retrieving chat history."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {
                "sessionId": "session-123",
                "userMessage": "What is vacation policy?",
                "assistantMessage": "Employees get 15 days.",
                "timestamp": "2024-01-15T10:00:00"
            }
        ]
        mock_cosmos.return_value = mock_container

        history = function_app.get_chat_history("session-123")

        assert len(history) == 2  # user + assistant
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"


# ==============================================================================
# Test Caching
# ==============================================================================

class TestCaching:
    """Tests for Redis caching."""

    @patch("function_app.get_redis_client")
    def test_cache_hit(self, mock_redis):
        """Test cache hit returns cached response."""
        cached_data = json.dumps({"answer": "Cached answer", "sources": []})
        mock_client = MagicMock()
        mock_client.get.return_value = cached_data
        mock_redis.return_value = mock_client

        result = function_app.get_cached_response("hash123")

        assert result["answer"] == "Cached answer"

    @patch("function_app.get_redis_client")
    def test_cache_miss(self, mock_redis):
        """Test cache miss returns None."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = function_app.get_cached_response("hash456")

        assert result is None

    @patch("function_app.get_redis_client")
    def test_cache_write(self, mock_redis):
        """Test writing to cache."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        function_app.cache_response("hash789", {"answer": "test"}, ttl=3600)

        mock_client.setex.assert_called_once()


# ==============================================================================
# Test Chat Endpoint
# ==============================================================================

class TestChatEndpoint:
    """Tests for the main chat HTTP endpoint."""

    def test_chat_missing_query(self, mock_http_request):
        """Test chat endpoint returns 400 when query is missing."""
        req = mock_http_request(body={"user_id": "test@company.com"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Config
# ==============================================================================

class TestConfig:
    """Tests for configuration defaults."""

    def test_config_defaults(self):
        """Test Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "documents-index"
        assert function_app.Config.TOP_K == 5
        assert function_app.Config.MAX_TOKENS == 4096
        assert function_app.Config.TEMPERATURE == 0.7

    def test_config_env_vars(self):
        """Test environment variable config attributes."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT",
            "COSMOS_ENDPOINT",
            "KEY_VAULT_URL",
            "REDIS_HOST"
        ]
        for attr in env_attrs:
            value = getattr(function_app.Config, attr)
            assert value is None or isinstance(value, str)


# ==============================================================================
# Test Health Check
# ==============================================================================

class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self, mock_http_request):
        """Test health endpoint returns healthy status."""
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.health_check(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        body = json.loads(call_args[0][0])
        assert body["status"] == "healthy"
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
