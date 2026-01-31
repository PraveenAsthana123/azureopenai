"""
Contact Center Knowledge Base - Comprehensive Tests
====================================================
3-tier testing: Positive, Negative, and Functional tests
for knowledge search, agent suggestions, gap detection,
FAQ generation, article authoring, and freshness scoring.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["azure.search.documents"] = MagicMock()
sys.modules["azure.search.documents.models"] = MagicMock()
sys.modules["openai"] = MagicMock()

import function_app


@pytest.fixture
def mock_http_request():
    def _make_request(body=None, method="POST", route_params=None):
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
    data = {
        "id": "kb-article-001",
        "title": "Password Reset Procedure",
        "content": "To reset a password, navigate to Account Settings > Security > Reset Password.",
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


class TestPositive_KnowledgeSearch:
    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_returns_ranked_articles(self, mock_embed, mock_search, sample_search_result):
        mock_embed.return_value = [0.1] * 1536
        mock_client = MagicMock()
        mock_client.search.return_value = [sample_search_result]
        mock_search.return_value = mock_client

        results = function_app.search_knowledge_base("How to reset password?", top_k=5)
        assert len(results) == 1
        assert results[0]["title"] == "Password Reset Procedure"
        assert results[0]["score"] == 0.93
        assert results[0]["reranker_score"] == 3.2

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_with_category_filter(self, mock_embed, mock_search, sample_search_result):
        mock_embed.return_value = [0.1] * 1536
        mock_client = MagicMock()
        mock_client.search.return_value = [sample_search_result]
        mock_search.return_value = mock_client

        results = function_app.search_knowledge_base("password help", top_k=3)
        assert len(results) >= 1
        assert results[0]["category"] == "Account Management"


class TestPositive_AgentSuggestions:
    @patch("function_app.get_openai_client")
    @patch("function_app.search_knowledge_base")
    def test_suggestions_with_full_context(self, mock_search, mock_openai):
        mock_search.return_value = [
            {"id": "kb-1", "title": "Refund Policy", "content": "Refunds within 30 days...", "score": 0.91}
        ]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Offer the customer a full refund since purchase was within 30-day window."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_agent_suggestions(
            "Customer asking about refund for recent purchase",
            customer_context={"tier": "gold", "product": "Premium Plan", "previous_contacts": 2}
        )
        assert len(result["suggested_articles"]) == 1
        assert "coaching_tip" in result
        assert "timestamp" in result

    @patch("function_app.get_openai_client")
    @patch("function_app.search_knowledge_base")
    def test_suggestions_no_matching_articles(self, mock_search, mock_openai):
        mock_search.return_value = []
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "No specific articles found. Use general troubleshooting."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_agent_suggestions(
            "Customer asks about a rare product issue",
            customer_context={"tier": "standard"}
        )
        assert len(result["suggested_articles"]) == 0
        assert "coaching_tip" in result


class TestPositive_ArticleAuthoring:
    @patch("function_app.get_openai_client")
    def test_author_article_with_all_fields(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Password Reset Procedures",
            "summary": "Step-by-step guide for password resets.",
            "content": "## Overview\nThis covers the password reset process...",
            "category": "Account Management",
            "tags": ["password", "security"],
            "internal_notes": "Verify identity first.",
            "customer_facing_version": "You can reset your password in Settings."
        })
        mock_response.usage.prompt_tokens = 250; mock_response.usage.completion_tokens = 300; mock_response.usage.total_tokens = 550
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.author_article("Password Reset Procedures", "Internal doc: password reset requires identity verification...")
        assert result["title"] == "Password Reset Procedures"
        assert result["status"] == "draft"
        assert result["usage"]["total_tokens"] == 550
        assert "internal_notes" in result
        assert "customer_facing_version" in result


class TestPositive_FreshnessScoring:
    def test_fresh_article_scores_high(self):
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

    def test_stale_article_scores_low(self):
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

    def test_moderate_age_article(self):
        mid_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
        article = {
            "id": "kb-003",
            "lastUpdated": mid_date,
            "positiveFeedbackCount": 20,
            "negativeFeedbackCount": 5,
            "viewCount": 100,
            "flaggedInaccurate": False
        }
        result = function_app.score_article_freshness(article)
        assert 40 <= result["freshness_score"] <= 90


class TestNegative_KnowledgeSearch:
    def test_search_missing_query_returns_400(self, mock_http_request):
        req = mock_http_request(body={"top_k": 5})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.search_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_returns_zero_results(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_client = MagicMock(); mock_client.search.return_value = []
        mock_search.return_value = mock_client
        results = function_app.search_knowledge_base("zzz_nonexistent_zzz")
        assert len(results) == 0

    def test_search_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.search_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


class TestNegative_AgentSuggestions:
    def test_suggestions_missing_transcript(self, mock_http_request):
        req = mock_http_request(body={"customer_context": {}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.agent_suggest_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    @patch("function_app.get_openai_client")
    @patch("function_app.search_knowledge_base")
    def test_suggestions_openai_error(self, mock_search, mock_openai):
        mock_search.return_value = []
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Service unavailable")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Service unavailable"):
            function_app.generate_agent_suggestions("test transcript", customer_context={})


class TestNegative_GapDetection:
    def test_detect_gaps_empty_transcripts(self, mock_http_request):
        req = mock_http_request(body={"call_transcripts": []})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.detect_gaps_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


class TestNegative_FAQGeneration:
    def test_generate_faq_empty_transcripts(self, mock_http_request):
        req = mock_http_request(body={"transcripts": []})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.generate_faq_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


class TestNegative_ArticleAuthoring:
    def test_author_article_missing_topic(self, mock_http_request):
        req = mock_http_request(body={"source_content": "some content"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.author_article_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    @patch("function_app.get_openai_client")
    def test_author_article_openai_error(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.author_article("Test Topic", "Test content")


class TestFunctional_KnowledgePipeline:
    @patch("function_app.search_knowledge_base")
    @patch("function_app.get_openai_client")
    def test_gap_detection_full_flow(self, mock_openai, mock_search):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "topics": [
                {"topic": "International Shipping", "example_question": "Do you ship to Canada?"},
                {"topic": "Gift Card Balance", "example_question": "How to check gift card balance?"}
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        mock_search.side_effect = [
            [{"reranker_score": 1.0}],
            [{"reranker_score": 0.2}]
        ]

        result = function_app.detect_knowledge_gaps([
            "Customer asked about shipping to Canada...",
            "Customer wanted to check gift card balance..."
        ])
        assert result["gaps_detected"] == 2
        assert result["transcripts_analysed"] == 2

    @patch("function_app.get_openai_client")
    def test_faq_generation_produces_drafts(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "faqs": [
                {"question": "How to reset password?", "answer": "Go to Account Settings > Security.", "category": "Account Management", "tags": ["password"]},
                {"question": "Refund policy?", "answer": "Full refunds within 30 days.", "category": "Billing", "tags": ["refund"]},
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

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_faq(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Timeout")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Timeout"):
            function_app.generate_faq_from_transcripts(["test transcript"])

    def test_config_defaults(self):
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "knowledge-articles-index"
        assert function_app.Config.TOP_K == 5
        assert function_app.Config.FRESHNESS_DECAY_DAYS == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
