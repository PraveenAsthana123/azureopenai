"""
Voice AI Outbound Platform - Unit Tests
========================================
Comprehensive tests for voice AI outbound calling functions
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
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["requests"] = MagicMock()

import function_app


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_campaign_data():
    """Sample campaign configuration."""
    return {
        "campaign_id": "camp-001",
        "name": "Q1 Renewal Campaign",
        "product": "Enterprise Cloud Suite",
        "objective": "Renew expiring subscriptions",
        "talking_points": ["New features", "Loyalty discount", "Dedicated support"]
    }


@pytest.fixture
def sample_customer_profile():
    """Sample customer profile."""
    return {
        "customer_id": "cust-12345",
        "name": "Jane Smith",
        "company": "Acme Corp",
        "phone_number": "+15551234567",
        "tier": "enterprise",
        "subscription_end": "2024-03-31",
        "previous_interactions": 3
    }


@pytest.fixture
def sample_transcript():
    """Sample call transcript."""
    return """Agent: Hi Jane, this is Alex from CloudSoft. How are you today?
Customer: I'm fine, thanks. What's this about?
Agent: I'm calling about your Enterprise Cloud subscription that's coming up for renewal.
Customer: Right, I've been meaning to look into that. We've been happy with the service.
Agent: That's great to hear! We have some new features and a loyalty discount I'd like to share.
Customer: Sure, I'm interested. What's the discount?"""


@pytest.fixture
def mock_http_request():
    """Factory for creating mock HTTP requests."""
    def _make_request(body: dict = None, method: str = "POST"):
        req = MagicMock()
        req.method = method
        req.route_params = {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


# ==============================================================================
# Test Script Generation
# ==============================================================================

class TestScriptGeneration:
    """Tests for AI call script generation."""

    @patch("function_app.get_openai_client")
    def test_generate_script_success(self, mock_openai, sample_campaign_data, sample_customer_profile):
        """Test generating a personalized call script."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "opening": "Hi Jane, this is Alex from CloudSoft.",
            "value_proposition": "Loyalty discount for enterprise customers.",
            "talking_points": ["New features", "20% discount"],
            "objection_responses": {"too_expensive": "We offer flexible payment plans."},
            "closing": "Shall I send you the renewal quote?",
            "voicemail_script": "Hi Jane, this is Alex from CloudSoft about your renewal."
        })
        mock_response.model = "gpt-4o"
        mock_response.usage.total_tokens = 500
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_call_script(sample_campaign_data, sample_customer_profile)

        assert "opening" in result
        assert "voicemail_script" in result
        assert result["metadata"]["campaign_id"] == "camp-001"
        assert result["metadata"]["customer_id"] == "cust-12345"

    def test_generate_script_missing_fields(self, mock_http_request):
        """Test endpoint returns 400 when fields are missing."""
        req = mock_http_request(body={"campaign_data": {"id": "test"}})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.generate_script_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test DNC Compliance
# ==============================================================================

class TestDNCCompliance:
    """Tests for Do-Not-Call compliance checking."""

    @patch("function_app.get_redis_client")
    def test_compliant_number(self, mock_redis):
        """Test a number that passes all compliance checks."""
        mock_client = MagicMock()
        mock_client.sismember.return_value = False
        mock_client.hget.return_value = None
        mock_client.get.return_value = "0"
        mock_redis.return_value = mock_client

        result = function_app.check_dnc_compliance("+15551234567")

        assert result["is_compliant"] is True
        assert result["federal_dnc"] is False
        assert result["state_dnc"] is False
        assert result["internal_dnc"] is False

    @patch("function_app.get_redis_client")
    def test_federal_dnc_blocked(self, mock_redis):
        """Test a number on the federal DNC list."""
        mock_client = MagicMock()
        mock_client.sismember.side_effect = lambda key, val: key == "dnc:federal"
        mock_client.hget.return_value = None
        mock_client.get.return_value = "0"
        mock_redis.return_value = mock_client

        result = function_app.check_dnc_compliance("+15559876543")

        assert result["is_compliant"] is False
        assert result["federal_dnc"] is True

    @patch("function_app.get_redis_client")
    def test_frequency_exceeded(self, mock_redis):
        """Test a number that exceeded call frequency limit."""
        mock_client = MagicMock()
        mock_client.sismember.return_value = False
        mock_client.hget.return_value = None
        mock_client.get.return_value = "5"  # Exceeds MAX_RETRY_ATTEMPTS=3
        mock_redis.return_value = mock_client

        result = function_app.check_dnc_compliance("+15551112222")

        assert result["is_compliant"] is False
        assert result["frequency_compliant"] is False

    def test_compliance_missing_phone(self, mock_http_request):
        """Test endpoint returns 400 when phone_number is missing."""
        req = mock_http_request(body={"some_field": "value"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.check_compliance_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Voicemail Detection
# ==============================================================================

class TestVoicemailDetection:
    """Tests for voicemail detection logic."""

    def test_voicemail_with_tone(self):
        """Test voicemail detection when beep tone is detected."""
        analysis = {
            "tone_detected": True,
            "silence_duration_ms": 3000,
            "greeting_duration_ms": 5000,
            "speech_pattern": "automated_greeting",
            "campaign_allows_voicemail": True
        }

        result = function_app.detect_voicemail(analysis)

        assert result["is_voicemail"] is True
        assert result["action"] == "leave_message"
        assert result["confidence"] == 0.95

    def test_live_person_detected(self):
        """Test detection of a live person answering."""
        analysis = {
            "tone_detected": False,
            "silence_duration_ms": 500,
            "greeting_duration_ms": 1000,
            "speech_pattern": "conversational"
        }

        result = function_app.detect_voicemail(analysis)

        assert result["is_voicemail"] is False
        assert result["action"] == "proceed_live"

    def test_voicemail_hangup_retry(self):
        """Test voicemail detection when campaign disallows voicemail."""
        analysis = {
            "tone_detected": True,
            "silence_duration_ms": 6000,
            "greeting_duration_ms": 4000,
            "speech_pattern": "automated_greeting",
            "campaign_allows_voicemail": False
        }

        result = function_app.detect_voicemail(analysis)

        assert result["is_voicemail"] is True
        assert result["action"] == "hangup_retry"


# ==============================================================================
# Test Call Outcome Classification
# ==============================================================================

class TestCallOutcomeClassification:
    """Tests for AI-based call outcome classification."""

    @patch("function_app.get_redis_client")
    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_classify_sale_completed(self, mock_openai, mock_cosmos, mock_redis, sample_transcript):
        """Test classifying a successful sale call."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "outcome": "sale_completed",
            "confidence": 0.92,
            "summary": "Customer agreed to renewal with loyalty discount.",
            "follow_up_actions": ["Send renewal contract"],
            "customer_interest_score": 9,
            "next_best_action": "Email contract within 24 hours"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        mock_container = MagicMock()
        mock_cosmos.return_value = mock_container
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        call_data = {"call_id": "call-001", "campaign_id": "camp-001", "phone_number": "+15551234567"}
        result = function_app.classify_call_outcome(call_data, sample_transcript)

        assert result["outcome"] == "sale_completed"
        assert result["confidence"] == 0.92
        assert result["call_id"] == "call-001"

    @patch("function_app.get_redis_client")
    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_classify_dnc_request(self, mock_openai, mock_cosmos, mock_redis):
        """Test classifying a DNC request adds to internal DNC list."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "outcome": "do_not_call",
            "confidence": 0.98,
            "summary": "Customer explicitly requested to not be called again.",
            "follow_up_actions": ["Add to DNC list"],
            "customer_interest_score": 0,
            "next_best_action": "Remove from all campaigns"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        mock_container = MagicMock()
        mock_cosmos.return_value = mock_container
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        call_data = {"call_id": "call-002", "campaign_id": "camp-001", "phone_number": "+15559999999"}
        result = function_app.classify_call_outcome(call_data, "Customer: Please stop calling me.")

        assert result["outcome"] == "do_not_call"
        mock_redis_client.sadd.assert_called_with("dnc:internal", "+15559999999")


# ==============================================================================
# Test Sentiment Analysis
# ==============================================================================

class TestSentimentAnalysis:
    """Tests for call sentiment analysis."""

    @patch("function_app.get_openai_client")
    def test_analyze_positive_sentiment(self, mock_openai, sample_transcript):
        """Test sentiment analysis of a positive call."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_sentiment": "positive",
            "sentiment_score": 0.75,
            "trend": "improving",
            "key_moments": [],
            "customer_emotions": ["interested", "engaged"],
            "risk_level": "low",
            "recommendation": "Continue with current approach"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.analyze_call_sentiment(sample_transcript)

        assert result["overall_sentiment"] == "positive"
        assert result["risk_level"] == "low"
        assert "analyzed_at" in result


# ==============================================================================
# Test Conversation Steering
# ==============================================================================

class TestConversationSteering:
    """Tests for real-time conversation steering."""

    @patch("function_app.get_openai_client")
    def test_steer_conversation(self, mock_openai, sample_transcript):
        """Test conversation steering with script and sentiment."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "suggested_response": "That's great! We're offering 20% off for loyal customers like you.",
            "strategy": "consultative",
            "script_deviation": False,
            "escalation_needed": False,
            "escalation_reason": None,
            "confidence": 0.85
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        script = {"talking_points": ["Loyalty discount", "New features"]}
        result = function_app.steer_conversation(sample_transcript, script, "positive")

        assert result["strategy"] == "consultative"
        assert result["escalation_needed"] is False
        assert "generated_at" in result


# ==============================================================================
# Test Config
# ==============================================================================

class TestConfig:
    """Tests for configuration defaults."""

    def test_config_defaults(self):
        """Test Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.MAX_CALL_DURATION_SECONDS == 600
        assert function_app.Config.VOICEMAIL_DETECTION_TIMEOUT_MS == 5000
        assert function_app.Config.MAX_RETRY_ATTEMPTS == 3
        assert function_app.Config.CALL_THROTTLE_PER_MINUTE == 30

    def test_config_env_vars(self):
        """Test environment variable config attributes."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT",
            "COMMUNICATION_SERVICES_ENDPOINT",
            "SPEECH_ENDPOINT",
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
        assert body["service"] == "voice-ai-outbound"
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
