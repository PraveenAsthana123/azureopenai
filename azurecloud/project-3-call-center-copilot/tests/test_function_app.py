"""
Call Center Copilot - Unit Tests
================================
Comprehensive tests for speech transcription, language detection,
intent classification, RAG, summarization, and quality scoring
with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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
sys.modules["azure.cosmos.exceptions"] = MagicMock()
sys.modules["azure.storage.blob"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["requests"] = MagicMock()

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


# ==============================================================================
# Test Transcription
# ==============================================================================

class TestTranscription:
    """Tests for speech transcription via Azure Speech Services."""

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_transcribe_audio_success(self, mock_cred, mock_requests):
        """Test successful audio transcription request."""
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "self": "https://speech.api/transcriptions/tx-123",
            "status": "running"
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.transcribe_audio(
            "https://storage.blob.core.windows.net/recordings/call.wav"
        )

        assert result["transcription_id"] == "tx-123"
        assert result["status"] == "running"
        assert result["language"] == "en-US"
        assert "created_at" in result

    def test_transcribe_missing_url(self, mock_http_request):
        """Test transcribe endpoint returns 400 when audio_url is missing."""
        req = mock_http_request(body={"language": "en-US"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.transcribe_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400
        body = json.loads(call_args[0][0])
        assert "error" in body


# ==============================================================================
# Test Language Detection
# ==============================================================================

class TestLanguageDetection:
    """Tests for language detection via Azure Language Services."""

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_detect_language_success(self, mock_cred, mock_requests):
        """Test successful language detection."""
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "documents": [{
                    "detectedLanguage": {
                        "name": "Spanish",
                        "iso6391Name": "es",
                        "confidenceScore": 0.98
                    }
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.detect_language("Hola, necesito ayuda con mi cuenta")

        assert result["language_name"] == "Spanish"
        assert result["iso_code"] == "es"
        assert result["confidence"] == 0.98
        assert "detected_at" in result

    def test_detect_language_missing_text(self, mock_http_request):
        """Test detect-language endpoint returns 400 when text is missing."""
        req = mock_http_request(body={})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.detect_language_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Intent Classification
# ==============================================================================

class TestIntentClassification:
    """Tests for GPT-4o intent classification."""

    @patch("function_app.get_openai_client")
    def test_classify_faq_intent(self, mock_openai):
        """Test classification of FAQ-type customer message."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "faq",
            "confidence": 0.89,
            "suggested_action": "Search knowledge base for answer"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.classify_intent("What are your business hours?")

        assert result["intent"] == "faq"
        assert result["confidence"] == 0.89
        assert "classified_at" in result

    @patch("function_app.get_openai_client")
    def test_classify_complaint_intent(self, mock_openai):
        """Test classification of complaint message."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "complaint",
            "confidence": 0.94,
            "suggested_action": "Escalate to retention team"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.classify_intent(
            "I am very disappointed with the service. This is unacceptable!"
        )

        assert result["intent"] == "complaint"
        assert result["confidence"] > 0.9


# ==============================================================================
# Test RAG Response
# ==============================================================================

class TestRAGResponse:
    """Tests for RAG knowledge base search and response generation."""

    @patch("function_app.get_openai_client")
    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_rag_search_success(self, mock_embed, mock_search, mock_openai):
        """Test RAG pipeline with search and GPT response."""
        mock_embed.return_value = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: {
            "id": "kb-1",
            "title": "Business Hours",
            "content": "Our business hours are Monday-Friday 9am-5pm EST.",
            "category": "general",
            "@search.score": 0.92
        }.get(key, None)
        mock_result.get = lambda key, default=None: {
            "id": "kb-1",
            "title": "Business Hours",
            "content": "Our business hours are Monday-Friday 9am-5pm EST.",
            "category": "general",
            "@search.score": 0.92
        }.get(key, default)

        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [mock_result]
        mock_search.return_value = mock_search_client

        mock_client = MagicMock()
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = (
            "Our business hours are Monday through Friday, 9am to 5pm Eastern Time."
        )
        mock_chat_response.usage.prompt_tokens = 150
        mock_chat_response.usage.completion_tokens = 30
        mock_chat_response.usage.total_tokens = 180
        mock_client.chat.completions.create.return_value = mock_chat_response
        mock_openai.return_value = mock_client

        result = function_app.rag_knowledge_search("What are your hours?")

        assert "response" in result
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "Business Hours"
        assert result["usage"]["total_tokens"] == 180

    def test_chat_missing_message(self, mock_http_request):
        """Test chat endpoint returns 400 when message is missing."""
        req = mock_http_request(body={"call_id": "test-123"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.chat_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Call Summarization
# ==============================================================================

class TestCallSummarization:
    """Tests for post-call summarization."""

    @patch("function_app.get_openai_client")
    def test_summarize_call_success(self, mock_openai):
        """Test post-call summarization generates summary and action items."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Customer called about billing issue. Agent resolved by applying credit.",
            "action_items": ["Apply $50 credit to account", "Follow up in 7 days"],
            "topics": ["billing", "credit"],
            "sentiment": "neutral",
            "resolution_status": "resolved"
        })
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 150
        mock_response.usage.total_tokens = 450
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_call(
            "Agent: How can I help?\nCustomer: I have a billing issue..."
        )

        assert "summary" in result
        assert len(result["action_items"]) == 2
        assert result["resolution_status"] == "resolved"
        assert result["usage"]["total_tokens"] == 450

    def test_summarize_call_missing_transcript(self, mock_http_request):
        """Test summarize-call endpoint returns 400 when transcript is missing."""
        req = mock_http_request(body={"call_id": "test-123"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.summarize_call_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Quality Scoring
# ==============================================================================

class TestQualityScoring:
    """Tests for call quality scoring."""

    @patch("function_app.get_openai_client")
    def test_quality_score_success(self, mock_openai):
        """Test quality scoring returns scores and recommendations."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_score": 82,
            "dimensions": {
                "professionalism": 90,
                "resolution_effectiveness": 80,
                "response_time": 75,
                "empathy": 85,
                "knowledge": 80
            },
            "recommendations": [
                "Reduce hold times between responses",
                "Offer proactive solutions"
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.score_call_quality(
            "Agent: Thank you for calling...\nCustomer: I need help..."
        )

        assert result["overall_score"] == 82
        assert len(result["dimensions"]) == 5
        assert result["dimensions"]["professionalism"] == 90
        assert len(result["recommendations"]) == 2
        assert "scored_at" in result

    def test_quality_score_missing_transcript(self, mock_http_request):
        """Test quality-score endpoint returns 400 when transcript is missing."""
        req = mock_http_request(body={"call_id": "test-123"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.quality_score_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Configuration
# ==============================================================================

class TestConfig:
    """Tests for the Config class defaults."""

    def test_config_defaults(self):
        """Test that Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "knowledge-base-index"
        assert function_app.Config.DATABASE_NAME == "callcentercopilot"
        assert function_app.Config.CACHE_TTL == 3600

    def test_config_env_vars(self):
        """Test that all environment variable config attributes are strings or None."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT",
            "COSMOS_ENDPOINT",
            "SPEECH_ENDPOINT",
            "TRANSLATOR_ENDPOINT",
            "LANGUAGE_ENDPOINT",
            "STORAGE_ACCOUNT_URL",
            "REDIS_HOST",
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
        assert body["service"] == "call-center-copilot"
        assert "timestamp" in body
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
