"""
Call Center Copilot - Comprehensive Tests
==========================================
3-tier testing: Positive, Negative, and Functional tests
for speech transcription, language detection, intent classification,
RAG, summarization, and quality scoring.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

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
def sample_transcript():
    return (
        "Agent: Thank you for calling support. How can I help?\n"
        "Customer: I'm having trouble logging into my account.\n"
        "Agent: I can help with that. Can you verify your email?\n"
        "Customer: Sure, it's john@example.com.\n"
        "Agent: I've sent a password reset link to your email."
    )


class TestPositive_Transcription:
    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_transcribe_with_language(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock()
        mock_response.json.return_value = {"self": "https://speech.api/transcriptions/tx-456", "status": "running"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.transcribe_audio("https://storage.blob.core.windows.net/recordings/call_es.wav", language="es-ES")
        assert result["transcription_id"] == "tx-456"
        assert result["status"] == "running"

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_transcribe_default_language(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock()
        mock_response.json.return_value = {"self": "https://speech.api/transcriptions/tx-789", "status": "running"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.transcribe_audio("https://storage.blob.core.windows.net/recordings/call.wav")
        assert result["language"] == "en-US"


class TestPositive_LanguageDetection:
    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_detect_french(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"documents": [{"detectedLanguage": {"name": "French", "iso6391Name": "fr", "confidenceScore": 0.96}}]}}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.detect_language("Bonjour, j'ai besoin d'aide")
        assert result["language_name"] == "French"
        assert result["iso_code"] == "fr"

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_detect_english_high_confidence(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"documents": [{"detectedLanguage": {"name": "English", "iso6391Name": "en", "confidenceScore": 0.99}}]}}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        result = function_app.detect_language("Hello, I need help with my account")
        assert result["confidence"] >= 0.95


class TestPositive_IntentClassification:
    @patch("function_app.get_openai_client")
    def test_classify_billing_intent(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"intent": "billing_inquiry", "confidence": 0.91, "suggested_action": "Transfer to billing"})
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_intent("I want to know about my last bill")
        assert result["intent"] == "billing_inquiry"
        assert "classified_at" in result

    @patch("function_app.get_openai_client")
    def test_classify_technical_support_intent(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"intent": "technical_support", "confidence": 0.87, "suggested_action": "Troubleshoot"})
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_intent("My internet keeps disconnecting")
        assert result["intent"] == "technical_support"


class TestPositive_CallSummarization:
    @patch("function_app.get_openai_client")
    def test_summarize_with_action_items(self, mock_openai, sample_transcript):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Customer had login issues. Agent sent password reset link.",
            "action_items": ["Monitor account"], "topics": ["account access"],
            "sentiment": "neutral", "resolution_status": "resolved"
        })
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 150
        mock_response.usage.total_tokens = 450
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.summarize_call(sample_transcript)
        assert result["resolution_status"] == "resolved"
        assert result["usage"]["total_tokens"] == 450


class TestNegative_Transcription:
    def test_transcribe_missing_url_returns_400(self, mock_http_request):
        req = mock_http_request(body={"language": "en-US"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.transcribe_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_transcribe_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.transcribe_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_transcribe_service_error(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_requests.post.side_effect = Exception("Speech service unavailable")
        with pytest.raises(Exception, match="Speech service unavailable"):
            function_app.transcribe_audio("https://storage.blob.core.windows.net/test.wav")


class TestNegative_LanguageDetection:
    def test_detect_missing_text_returns_400(self, mock_http_request):
        req = mock_http_request(body={})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.detect_language_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_detect_language_service_error(self, mock_cred, mock_requests):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_requests.post.side_effect = Exception("Language service error")
        with pytest.raises(Exception, match="Language service error"):
            function_app.detect_language("test text")


class TestNegative_ChatEndpoint:
    def test_chat_missing_message_returns_400(self, mock_http_request):
        req = mock_http_request(body={"call_id": "test-123"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.chat_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_chat_empty_message_returns_400(self, mock_http_request):
        req = mock_http_request(body={"message": "", "call_id": "test-123"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.chat_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_summarize_missing_transcript_returns_400(self, mock_http_request):
        req = mock_http_request(body={"call_id": "test-123"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.summarize_call_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_quality_score_missing_transcript_returns_400(self, mock_http_request):
        req = mock_http_request(body={"call_id": "test-123"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.quality_score_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400


class TestFunctional_CallCenterPipeline:
    @patch("function_app.get_openai_client")
    @patch("function_app.requests")
    @patch("function_app.get_credential")
    def test_detect_language_then_classify_intent(self, mock_cred, mock_requests, mock_openai):
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token
        mock_lang_response = MagicMock()
        mock_lang_response.json.return_value = {"results": {"documents": [{"detectedLanguage": {"name": "English", "iso6391Name": "en", "confidenceScore": 0.99}}]}}
        mock_lang_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_lang_response

        lang_result = function_app.detect_language("I need help with my billing")
        assert lang_result["iso_code"] == "en"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"intent": "billing_inquiry", "confidence": 0.91, "suggested_action": "Route to billing"})
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        intent_result = function_app.classify_intent("I need help with my billing")
        assert intent_result["intent"] == "billing_inquiry"

    @patch("function_app.get_openai_client")
    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_rag_search_then_summarize(self, mock_embed, mock_search, mock_openai):
        mock_embed.return_value = [0.1] * 1536
        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: {"id": "kb-1", "title": "Billing FAQ", "content": "Bills are sent monthly.", "category": "billing", "@search.score": 0.92}.get(key, None)
        mock_result.get = lambda key, default=None: {"id": "kb-1", "title": "Billing FAQ", "content": "Bills are sent monthly.", "category": "billing", "@search.score": 0.92}.get(key, default)
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [mock_result]
        mock_search.return_value = mock_search_client
        mock_client = MagicMock()
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = "Bills are sent monthly on the 1st."
        mock_chat_response.usage.prompt_tokens = 100
        mock_chat_response.usage.completion_tokens = 30
        mock_chat_response.usage.total_tokens = 130
        mock_client.chat.completions.create.return_value = mock_chat_response
        mock_openai.return_value = mock_client

        rag_result = function_app.rag_knowledge_search("When are bills sent?")
        assert "response" in rag_result
        assert len(rag_result["sources"]) >= 1

    @patch("function_app.get_openai_client")
    def test_summarize_then_quality_score(self, mock_openai, sample_transcript):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Login issue resolved.", "action_items": ["Monitor"], "topics": ["account"], "sentiment": "neutral", "resolution_status": "resolved"})
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 400
        mock_client.chat.completions.create.return_value = mock_response
        summary = function_app.summarize_call(sample_transcript)
        assert summary["resolution_status"] == "resolved"

        mock_qscore_response = MagicMock()
        mock_qscore_response.choices = [MagicMock()]
        mock_qscore_response.choices[0].message.content = json.dumps({"overall_score": 85, "dimensions": {"professionalism": 90, "resolution_effectiveness": 85, "response_time": 80, "empathy": 88, "knowledge": 82}, "recommendations": ["Offer follow-up"]})
        mock_client.chat.completions.create.return_value = mock_qscore_response
        quality = function_app.score_call_quality(sample_transcript)
        assert quality["overall_score"] == 85
        assert len(quality["dimensions"]) == 5

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_rag(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.classify_intent("test message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
