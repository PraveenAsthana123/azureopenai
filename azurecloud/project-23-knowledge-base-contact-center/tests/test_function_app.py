"""
Contact Center Knowledge Base - Unit Tests
===========================================
Comprehensive tests for knowledge search, agent suggestions, gap detection,
FAQ generation, article authoring, and freshness scoring with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock all Azure SDK modules before importing function_app
sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["azure.search.documents"] = MagicMock()
sys.modules["azure.search.documents.models"] = MagicMock()
sys.modules["openai"] = MagicMock()

import function_app


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_http_request():
    """Factory for creating mock HTTP requests."""
    def _make_request(body: dict = None, method: str = "POST", route_params: dict = None):
        req = MagicMock()
        req.method = method
        req.route_params = route_params or {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


@pytest.fixture
def sample_search_result():
    """Sample AI Search result for knowledge article."""
    data = {
        "id": "kb-article-001",
        "title": "Password Reset Procedure",
        "content": "To reset a customer password, navigate to Account Settings > Security > Reset Password. Verify identity using the last 4 digits of SSN and date of birth.",
        "category": "Account Management",
        "tags": ["password", "security", "account"],
        "lastUpdated": "2024-10-15T10:00:00Z",
        "author": "J. Smith",
        "articleStatus": "published",
        "viewCount": 342,
        "@search.score": 0.93,
        "@search.reranker_score": 3.2
    }
    mock_result = MagicMock()
    mock_result.__getitem__ = lambda self, key: data[key]
    mock_result.get = lambda key, default=None: data.get(key, default)
    return mock_result


# ==============================================================================
# Test Knowledge Search
# ==============================================================================

class TestKnowledgeSearch:
    """Tests for hybrid vector + keyword knowledge base search."""

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_success(self, mock_embed, mock_search, sample_search_result):
        """Test searching knowledge base returns ranked articles."""
        mock_embed.return_value = [0.1] * 1536

        mock_client = MagicMock()
        mock_client.search.return_value = [sample_search_result]
        mock_search.return_value = mock_client

        results = function_app.search_knowledge_base("How to reset password?", top_k=5)

        assert len(results) == 1
        assert results[0]["title"] == "Password Reset Procedure"
        assert results[0]["category"] == "Account Management"
        assert results[0]["score"] == 0.93
        assert results[0]["reranker_score"] == 3.2

    def test_search_missing_query(self, mock_http_request):
        """Test search endpoint returns 400 when query is missing."""
        req = mock_http_request(body={"top_k": 5})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.search_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400
        body = json.loads(call_args[0][0])
        assert "error" in body


# ==============================================================================
# Test Agent Suggestions
# ==============================================================================

class TestAgentSuggestions:
    """Tests for real-time agent suggestion engine."""

    @patch("function_app.get_openai_client")
    @patch("function_app.search_knowledge_base")
    def test_suggestions_success(self, mock_search, mock_openai):
        """Test generating agent suggestions from live transcript."""
        mock_search.return_value = [
            {"id": "kb-1", "title": "Refund Policy", "content": "Refunds within 30 days...", "score": 0.91}
        ]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Offer the customer a full refund since the purchase was within the 30-day window."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_agent_suggestions(
            "Customer is asking about getting a refund for a recent purchase",
            customer_context={"tier": "gold", "product": "Premium Plan", "previous_contacts": 2}
        )

        assert len(result["suggested_articles"]) == 1
        assert result["suggested_articles"][0]["title"] == "Refund Policy"
        assert "coaching_tip" in result
        assert "timestamp" in result

    def test_suggestions_missing_transcript(self, mock_http_request):
        """Test agent-suggest endpoint returns 400 when transcript_segment is missing."""
        req = mock_http_request(body={"customer_context": {}})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.agent_suggest_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Knowledge Gap Detection
# ==============================================================================

class TestKnowledgeGaps:
    """Tests for knowledge gap detection from call transcripts."""

    @patch("function_app.search_knowledge_base")
    @patch("function_app.get_openai_client")
    def test_detect_gaps_success(self, mock_openai, mock_search):
        """Test gap detection identifies missing knowledge topics."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "topics": [
                {"topic": "International Shipping", "example_question": "Do you ship to Canada?"},
                {"topic": "Gift Card Balance", "example_question": "How do I check my gift card balance?"}
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # First topic has weak coverage, second has no coverage
        mock_search.side_effect = [
            [{"reranker_score": 1.0}],  # weak match
            [{"reranker_score": 0.2}]   # missing
        ]

        result = function_app.detect_knowledge_gaps([
            "Customer asked about shipping to Canada...",
            "Customer wanted to check gift card balance..."
        ])

        assert result["gaps_detected"] == 2
        assert result["transcripts_analysed"] == 2
        assert any(g["topic"] == "International Shipping" for g in result["gaps"])
        assert "timestamp" in result

    def test_detect_gaps_missing_transcripts(self, mock_http_request):
        """Test detect-gaps endpoint returns 400 when call_transcripts is empty."""
        req = mock_http_request(body={"call_transcripts": []})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.detect_gaps_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test FAQ Generation
# ==============================================================================

class TestFAQGeneration:
    """Tests for auto-generating FAQs from call transcripts."""

    @patch("function_app.get_openai_client")
    def test_generate_faq_success(self, mock_openai):
        """Test FAQ generation produces structured FAQ entries."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "faqs": [
                {
                    "question": "How do I reset my password?",
                    "answer": "Navigate to Account Settings > Security > Reset Password.",
                    "category": "Account Management",
                    "tags": ["password", "security"]
                },
                {
                    "question": "What is the refund policy?",
                    "answer": "Full refunds are available within 30 days of purchase.",
                    "category": "Billing",
                    "tags": ["refund", "billing"]
                }
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_faq_from_transcripts([
            "Customer asked how to reset password...",
            "Customer asked about refund policy..."
        ])

        assert result["faq_count"] == 2
        assert result["faqs"][0]["status"] == "draft"
        assert result["faqs"][0]["source"] == "auto-generated-from-transcripts"
        assert "question" in result["faqs"][0]
        assert "answer" in result["faqs"][0]

    def test_generate_faq_missing_transcripts(self, mock_http_request):
        """Test generate-faq endpoint returns 400 when transcripts is empty."""
        req = mock_http_request(body={"transcripts": []})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.generate_faq_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Article Authoring
# ==============================================================================

class TestArticleAuthoring:
    """Tests for GenAI-assisted article authoring."""

    @patch("function_app.get_openai_client")
    def test_author_article_success(self, mock_openai):
        """Test article authoring generates structured article draft."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Password Reset Procedures",
            "summary": "Step-by-step guide for agents to help customers reset passwords.",
            "content": "## Overview\nThis article covers the password reset process...",
            "category": "Account Management",
            "tags": ["password", "security", "account"],
            "internal_notes": "Verify identity before proceeding with reset.",
            "customer_facing_version": "You can reset your password by visiting Settings."
        })
        mock_response.usage.prompt_tokens = 250
        mock_response.usage.completion_tokens = 300
        mock_response.usage.total_tokens = 550
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.author_article(
            "Password Reset Procedures",
            "Internal doc: password reset requires identity verification..."
        )

        assert result["title"] == "Password Reset Procedures"
        assert result["status"] == "draft"
        assert result["category"] == "Account Management"
        assert "internal_notes" in result
        assert "customer_facing_version" in result
        assert result["usage"]["total_tokens"] == 550

    def test_author_article_missing_topic(self, mock_http_request):
        """Test author-article endpoint returns 400 when topic is missing."""
        req = mock_http_request(body={"source_content": "some content"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.author_article_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Freshness Scoring
# ==============================================================================

class TestFreshnessScoring:
    """Tests for article content freshness scoring."""

    def test_fresh_article_scores_high(self):
        """Test that a recently updated article with positive feedback scores high."""
        article = {
            "id": "kb-001",
            "lastUpdated": datetime.utcnow().isoformat(),
            "positiveFeedbackCount": 50,
            "negativeFeedbackCount": 2,
            "viewCount": 500,
            "flaggedInaccurate": False
        }

        result = function_app.score_article_freshness(article)

        assert result["freshness_score"] >= 80
        assert result["recommendation"] == "current"
        assert result["article_id"] == "kb-001"
        assert "evaluated_at" in result

    def test_stale_article_scores_low(self):
        """Test that an old article with negative feedback scores low."""
        old_date = (datetime.utcnow() - timedelta(days=300)).isoformat()
        article = {
            "id": "kb-002",
            "lastUpdated": old_date,
            "positiveFeedbackCount": 5,
            "negativeFeedbackCount": 20,
            "viewCount": 3,
            "flaggedInaccurate": True
        }

        result = function_app.score_article_freshness(article)

        assert result["freshness_score"] < 50
        assert result["recommendation"] in ("update_required", "retire_or_rewrite")


# ==============================================================================
# Test Configuration
# ==============================================================================

class TestConfig:
    """Tests for the Config class defaults."""

    def test_config_defaults(self):
        """Test that Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "knowledge-articles-index"
        assert function_app.Config.TOP_K == 5
        assert function_app.Config.FRESHNESS_DECAY_DAYS == 90

    def test_config_env_vars(self):
        """Test that all environment variable config attributes are strings or None."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT",
            "COSMOS_ENDPOINT",
            "KEY_VAULT_URL"
        ]
        for attr in env_attrs:
            value = getattr(function_app.Config, attr)
            assert value is None or isinstance(value, str), (
                f"Config.{attr} should be str or None, got {type(value)}"
            )


# ==============================================================================
# Test Health Check
# ==============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, mock_http_request):
        """Test health endpoint returns status healthy."""
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.health_check(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        body = json.loads(call_args[0][0])
        assert body["status"] == "healthy"
        assert body["service"] == "contact-center-knowledge-base"
        assert "timestamp" in body
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
