"""
Enterprise RAG Knowledge Copilot - Comprehensive Tests
======================================================
3-tier testing: Positive, Negative, and Functional tests
for RAG pipeline with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, call
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
def mock_http_request():
    """Factory for creating mock HTTP requests."""
    def _make_request(body=None, method="POST", route_params=None, params=None):
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
        },
        {
            "id": "doc-3",
            "content": "Remote work policy allows up to 3 days per week.",
            "title": "Remote Work Guidelines",
            "source": "policies/remote-work.pdf",
            "page": 1,
            "score": 0.72,
            "reranker_score": 0.68
        }
    ]


@pytest.fixture
def sample_chat_history():
    """Sample conversation history."""
    return [
        {"role": "user", "content": "What is the vacation policy?"},
        {"role": "assistant", "content": "Employees get 15 days of paid vacation per year."}
    ]


# ==============================================================================
# Positive Tests - Embedding Generation
# ==============================================================================

class TestPositive_EmbeddingGeneration:
    """Happy-path tests for embedding generation with valid inputs."""

    @patch("function_app.get_openai_client")
    def test_generate_embedding_valid_all_params(self, mock_openai):
        """Test embedding generation with full valid text."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_embedding("What is the company vacation policy for full-time employees?")

        assert len(result) == 1536
        assert all(isinstance(v, float) for v in result)
        mock_client.embeddings.create.assert_called_once()

    @patch("function_app.get_openai_client")
    def test_generate_embedding_minimal_text(self, mock_openai):
        """Test embedding generation with minimal single-word input."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.05] * 1536
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_embedding("hello")

        assert len(result) == 1536

    @patch("function_app.get_openai_client")
    def test_generate_embedding_uses_correct_model(self, mock_openai):
        """Test that embedding uses the configured model name."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        function_app.generate_embedding("test text")

        mock_client.embeddings.create.assert_called_once_with(
            input="test text",
            model="text-embedding-ada-002"
        )


# ==============================================================================
# Positive Tests - Document Retrieval
# ==============================================================================

class TestPositive_DocumentRetrieval:
    """Happy-path tests for document retrieval with valid inputs."""

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_retrieve_documents_with_top_k(self, mock_embed, mock_search):
        """Test retrieving documents with explicit top_k parameter."""
        mock_embed.return_value = [0.1] * 1536
        mock_result = MagicMock()
        mock_result.get = lambda key, default=None: {
            "id": "doc-1", "content": "Policy text", "title": "Policy",
            "source": "policy.pdf", "page": 1,
            "@search.score": 0.92, "@search.reranker_score": 0.85
        }.get(key, default)
        mock_result.__getitem__ = lambda self, key: {
            "id": "doc-1", "content": "Policy text", "title": "Policy",
            "source": "policy.pdf", "page": 1,
            "@search.score": 0.92, "@search.reranker_score": 0.85
        }[key]

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_result]
        mock_search.return_value = mock_client

        results = function_app.retrieve_documents("vacation policy", top_k=3)

        assert len(results) >= 1
        assert results[0]["score"] == 0.92

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_retrieve_documents_multiple_results(self, mock_embed, mock_search):
        """Test retrieving multiple documents returns all results."""
        mock_embed.return_value = [0.1] * 1536

        results_data = [
            {"id": f"doc-{i}", "content": f"Content {i}", "title": f"Title {i}",
             "source": f"file{i}.pdf", "page": i,
             "@search.score": 0.95 - (i * 0.05), "@search.reranker_score": 0.88 - (i * 0.03)}
            for i in range(3)
        ]
        mock_results = []
        for data in results_data:
            m = MagicMock()
            m.get = lambda key, default=None, d=data: d.get(key, default)
            m.__getitem__ = lambda self, key, d=data: d[key]
            mock_results.append(m)

        mock_client = MagicMock()
        mock_client.search.return_value = mock_results
        mock_search.return_value = mock_client

        results = function_app.retrieve_documents("company policies", top_k=5)

        assert len(results) == 3


# ==============================================================================
# Positive Tests - Response Generation
# ==============================================================================

class TestPositive_ResponseGeneration:
    """Happy-path tests for GPT-4o response generation."""

    @patch("function_app.get_openai_client")
    def test_generate_response_with_token_tracking(self, mock_openai):
        """Test response generation tracks token usage correctly."""
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

        assert result["usage"]["prompt_tokens"] == 500
        assert result["usage"]["completion_tokens"] == 200
        assert result["usage"]["total_tokens"] == 700
        assert result["finish_reason"] == "stop"

    @patch("function_app.get_openai_client")
    def test_generate_response_content_present(self, mock_openai):
        """Test response contains expected content field."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The policy states 15 vacation days."
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.model = "gpt-4o"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        messages = [{"role": "user", "content": "Tell me about vacation."}]
        result = function_app.generate_response(messages)

        assert "content" in result
        assert len(result["content"]) > 0


# ==============================================================================
# Positive Tests - Caching
# ==============================================================================

class TestPositive_Caching:
    """Happy-path tests for Redis caching."""

    @patch("function_app.get_redis_client")
    def test_cache_hit_returns_full_response(self, mock_redis):
        """Test cache hit returns complete cached response with sources."""
        cached_data = json.dumps({
            "answer": "Cached answer about vacation policy",
            "sources": [{"title": "HR Policy", "page": 12}],
            "usage": {"total_tokens": 700}
        })
        mock_client = MagicMock()
        mock_client.get.return_value = cached_data
        mock_redis.return_value = mock_client

        result = function_app.get_cached_response("hash123")

        assert result["answer"] == "Cached answer about vacation policy"
        assert len(result["sources"]) == 1
        assert result["usage"]["total_tokens"] == 700

    @patch("function_app.get_redis_client")
    def test_cache_write_with_ttl(self, mock_redis):
        """Test cache write stores data with correct TTL."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        function_app.cache_response("hash789", {"answer": "test"}, ttl=7200)

        mock_client.setex.assert_called_once()
        args = mock_client.setex.call_args
        assert args[0][1] == 7200 or args[1].get("time") == 7200


# ==============================================================================
# Negative Tests - Embedding Generation
# ==============================================================================

class TestNegative_EmbeddingGeneration:
    """Error handling tests for embedding generation."""

    @patch("function_app.get_openai_client")
    def test_embedding_service_error(self, mock_openai):
        """Test embedding generation handles OpenAI service errors."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("OpenAI service unavailable")
        mock_openai.return_value = mock_client

        with pytest.raises(Exception, match="OpenAI service unavailable"):
            function_app.generate_embedding("test text")


# ==============================================================================
# Negative Tests - Chat Endpoint
# ==============================================================================

class TestNegative_ChatEndpoint:
    """Error handling tests for the chat endpoint."""

    def test_chat_missing_query_returns_400(self, mock_http_request):
        """Test chat endpoint returns 400 when query is missing."""
        req = mock_http_request(body={"user_id": "test@company.com"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_chat_empty_query_returns_400(self, mock_http_request):
        """Test chat endpoint returns 400 for empty query string."""
        req = mock_http_request(body={"query": "", "user_id": "test@company.com"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_chat_malformed_json(self, mock_http_request):
        """Test chat endpoint handles malformed JSON body."""
        req = mock_http_request(body=None)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_chat_missing_user_id(self, mock_http_request):
        """Test chat endpoint handles missing user_id."""
        req = mock_http_request(body={"query": "What is vacation policy?"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Negative Tests - Session Management
# ==============================================================================

class TestNegative_SessionManagement:
    """Error handling tests for session management."""

    @patch("function_app.get_cosmos_container")
    def test_session_cosmos_error(self, mock_cosmos):
        """Test session creation handles Cosmos DB errors."""
        mock_container = MagicMock()
        mock_container.create_item.side_effect = Exception("Cosmos DB unavailable")
        mock_cosmos.return_value = mock_container

        with pytest.raises(Exception, match="Cosmos DB unavailable"):
            function_app.get_or_create_session("user@company.com")

    @patch("function_app.get_cosmos_container")
    def test_session_not_found(self, mock_cosmos):
        """Test retrieving a non-existent session raises error."""
        mock_container = MagicMock()
        mock_container.read_item.side_effect = Exception("Not found")
        mock_cosmos.return_value = mock_container

        with pytest.raises(Exception):
            function_app.get_or_create_session("user@company.com", "nonexistent-session")


# ==============================================================================
# Negative Tests - Caching
# ==============================================================================

class TestNegative_Caching:
    """Error handling tests for Redis caching."""

    @patch("function_app.get_redis_client")
    def test_cache_redis_connection_error(self, mock_redis):
        """Test cache handles Redis connection errors gracefully."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Redis connection refused")
        mock_redis.return_value = mock_client

        with pytest.raises(Exception, match="Redis connection refused"):
            function_app.get_cached_response("hash123")


# ==============================================================================
# Functional Tests - Full RAG Pipeline
# ==============================================================================

class TestFunctional_RAGPipeline:
    """End-to-end functional tests for the RAG pipeline flow."""

    @patch("function_app.get_redis_client")
    @patch("function_app.get_openai_client")
    @patch("function_app.get_search_client")
    def test_full_chat_flow_cache_miss(self, mock_search, mock_openai, mock_redis):
        """Test complete chat flow: cache miss -> retrieve -> generate -> cache write."""
        # Cache miss
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None
        mock_redis.return_value = mock_redis_client

        # Search results
        mock_result = MagicMock()
        mock_result.get = lambda key, default=None: {
            "id": "doc-1", "content": "15 days vacation policy",
            "title": "HR Policy", "source": "hr.pdf", "page": 1,
            "@search.score": 0.92, "@search.reranker_score": 0.85
        }.get(key, default)
        mock_result.__getitem__ = lambda self, key: {
            "id": "doc-1", "content": "15 days vacation policy",
            "title": "HR Policy", "source": "hr.pdf", "page": 1,
            "@search.score": 0.92, "@search.reranker_score": 0.85
        }[key]
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [mock_result]
        mock_search.return_value = mock_search_client

        # OpenAI response (for both embedding and chat)
        mock_client = MagicMock()
        mock_embed_resp = MagicMock()
        mock_embed_resp.data = [MagicMock()]
        mock_embed_resp.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_embed_resp

        mock_chat_resp = MagicMock()
        mock_chat_resp.choices = [MagicMock()]
        mock_chat_resp.choices[0].message.content = "Employees get 15 days vacation."
        mock_chat_resp.choices[0].finish_reason = "stop"
        mock_chat_resp.usage.prompt_tokens = 500
        mock_chat_resp.usage.completion_tokens = 100
        mock_chat_resp.usage.total_tokens = 600
        mock_chat_resp.model = "gpt-4o"
        mock_client.chat.completions.create.return_value = mock_chat_resp
        mock_openai.return_value = mock_client

        # Execute pipeline steps
        embedding = function_app.generate_embedding("vacation policy")
        assert len(embedding) == 1536

        docs = function_app.retrieve_documents("vacation policy", top_k=5)
        assert len(docs) >= 1

        messages = function_app.build_augmented_prompt("What is vacation policy?", docs)
        assert len(messages) >= 2

        response = function_app.generate_response(messages)
        assert "content" in response
        assert response["usage"]["total_tokens"] == 600

    def test_build_prompt_integrates_documents_and_history(self, sample_documents, sample_chat_history):
        """Test prompt builder integrates documents and history correctly."""
        messages = function_app.build_augmented_prompt(
            "How do I request time off?",
            sample_documents,
            sample_chat_history
        )

        # System message with context
        assert messages[0]["role"] == "system"
        # History messages
        history_messages = [m for m in messages[1:-1] if m["role"] in ("user", "assistant")]
        assert len(history_messages) >= 2
        # Final user message
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "How do I request time off?"

    @patch("function_app.get_cosmos_container")
    def test_session_create_and_retrieve_flow(self, mock_cosmos):
        """Test creating a session then retrieving chat history."""
        mock_container = MagicMock()
        mock_container.create_item.return_value = None
        mock_container.query_items.return_value = [
            {
                "sessionId": "session-abc",
                "userMessage": "What is vacation policy?",
                "assistantMessage": "Employees get 15 days.",
                "timestamp": "2024-01-15T10:00:00"
            }
        ]
        mock_cosmos.return_value = mock_container

        session = function_app.get_or_create_session("user@company.com")
        assert "id" in session

        history = function_app.get_chat_history("session-abc")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    @patch("function_app.get_openai_client")
    def test_response_error_propagation(self, mock_openai):
        """Test that OpenAI errors propagate correctly through the pipeline."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client

        messages = [{"role": "user", "content": "test"}]
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.generate_response(messages)


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
