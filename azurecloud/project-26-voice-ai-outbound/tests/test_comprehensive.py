"""
Voice AI Outbound Platform - Comprehensive Tests
=================================================
3-tier testing: Positive, Negative, and Functional tests
for script generation, DNC compliance, voicemail detection,
call outcome classification, sentiment analysis, and conversation steering.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["requests"] = MagicMock()

import function_app


@pytest.fixture
def sample_campaign_data():
    return {
        "campaign_id": "camp-001",
        "name": "Q1 Renewal Campaign",
        "product": "Enterprise Cloud Suite",
        "objective": "Renew expiring subscriptions",
        "talking_points": ["New features", "Loyalty discount", "Dedicated support"]
    }


@pytest.fixture
def sample_customer_profile():
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
    return """Agent: Hi Jane, this is Alex from CloudSoft. How are you today?
Customer: I'm fine, thanks. What's this about?
Agent: I'm calling about your Enterprise Cloud subscription that's coming up for renewal.
Customer: Right, I've been meaning to look into that. We've been happy with the service.
Agent: That's great to hear! We have some new features and a loyalty discount I'd like to share.
Customer: Sure, I'm interested. What's the discount?"""


@pytest.fixture
def mock_http_request():
    def _make_request(body=None, method="POST"):
        req = MagicMock()
        req.method = method
        req.route_params = {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


class TestPositive_ScriptGeneration:
    @patch("function_app.get_openai_client")
    def test_generate_script_all_fields(self, mock_openai, sample_campaign_data, sample_customer_profile):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "opening": "Hi Jane, this is Alex from CloudSoft.",
            "value_proposition": "Loyalty discount for enterprise customers.",
            "talking_points": ["New features", "20% discount"],
            "objection_responses": {"too_expensive": "Flexible payment plans available."},
            "closing": "Shall I send the renewal quote?",
            "voicemail_script": "Hi Jane, this is Alex from CloudSoft about your renewal."
        })
        mock_response.model = "gpt-4o"
        mock_response.usage.total_tokens = 500
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_call_script(sample_campaign_data, sample_customer_profile)
        assert "opening" in result
        assert "voicemail_script" in result
        assert "objection_responses" in result
        assert result["metadata"]["campaign_id"] == "camp-001"
        assert result["metadata"]["customer_id"] == "cust-12345"

    @patch("function_app.get_openai_client")
    def test_generate_script_includes_talking_points(self, mock_openai, sample_campaign_data, sample_customer_profile):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "opening": "Hello.", "value_proposition": "Great deal.",
            "talking_points": ["New features", "Loyalty discount", "Dedicated support"],
            "objection_responses": {}, "closing": "Thanks.", "voicemail_script": "Leave a message."
        })
        mock_response.model = "gpt-4o"
        mock_response.usage.total_tokens = 350
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.generate_call_script(sample_campaign_data, sample_customer_profile)
        assert len(result["talking_points"]) == 3


class TestPositive_DNCCompliance:
    @patch("function_app.get_redis_client")
    def test_compliant_number_passes_all(self, mock_redis):
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
    def test_compliant_number_low_frequency(self, mock_redis):
        mock_client = MagicMock()
        mock_client.sismember.return_value = False
        mock_client.hget.return_value = None
        mock_client.get.return_value = "2"
        mock_redis.return_value = mock_client

        result = function_app.check_dnc_compliance("+15559998888")
        assert result["is_compliant"] is True
        assert result["frequency_compliant"] is True


class TestPositive_VoicemailDetection:
    def test_voicemail_with_tone_leave_message(self):
        analysis = {
            "tone_detected": True, "silence_duration_ms": 3000,
            "greeting_duration_ms": 5000, "speech_pattern": "automated_greeting",
            "campaign_allows_voicemail": True
        }
        result = function_app.detect_voicemail(analysis)
        assert result["is_voicemail"] is True
        assert result["action"] == "leave_message"
        assert result["confidence"] == 0.95

    def test_live_person_detected(self):
        analysis = {
            "tone_detected": False, "silence_duration_ms": 500,
            "greeting_duration_ms": 1000, "speech_pattern": "conversational"
        }
        result = function_app.detect_voicemail(analysis)
        assert result["is_voicemail"] is False
        assert result["action"] == "proceed_live"

    def test_voicemail_campaign_disallows(self):
        analysis = {
            "tone_detected": True, "silence_duration_ms": 6000,
            "greeting_duration_ms": 4000, "speech_pattern": "automated_greeting",
            "campaign_allows_voicemail": False
        }
        result = function_app.detect_voicemail(analysis)
        assert result["is_voicemail"] is True
        assert result["action"] == "hangup_retry"


class TestPositive_SentimentAnalysis:
    @patch("function_app.get_openai_client")
    def test_positive_sentiment(self, mock_openai, sample_transcript):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_sentiment": "positive", "sentiment_score": 0.75, "trend": "improving",
            "key_moments": [], "customer_emotions": ["interested", "engaged"],
            "risk_level": "low", "recommendation": "Continue with current approach"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.analyze_call_sentiment(sample_transcript)
        assert result["overall_sentiment"] == "positive"
        assert result["risk_level"] == "low"
        assert "analyzed_at" in result


class TestNegative_ScriptGeneration:
    def test_generate_script_missing_fields(self, mock_http_request):
        req = mock_http_request(body={"campaign_data": {"id": "test"}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.generate_script_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_generate_script_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.generate_script_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    @patch("function_app.get_openai_client")
    def test_generate_script_openai_error(self, mock_openai, sample_campaign_data, sample_customer_profile):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Service unavailable")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Service unavailable"):
            function_app.generate_call_script(sample_campaign_data, sample_customer_profile)


class TestNegative_DNCCompliance:
    @patch("function_app.get_redis_client")
    def test_federal_dnc_blocked(self, mock_redis):
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
        mock_client = MagicMock()
        mock_client.sismember.return_value = False
        mock_client.hget.return_value = None
        mock_client.get.return_value = "5"
        mock_redis.return_value = mock_client

        result = function_app.check_dnc_compliance("+15551112222")
        assert result["is_compliant"] is False
        assert result["frequency_compliant"] is False

    def test_compliance_missing_phone(self, mock_http_request):
        req = mock_http_request(body={"some_field": "value"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.check_compliance_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


class TestNegative_CallOutcome:
    def test_classify_missing_transcript(self, mock_http_request):
        req = mock_http_request(body={"call_data": {"call_id": "c1"}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.classify_outcome_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


class TestFunctional_VoiceAIPipeline:
    @patch("function_app.get_redis_client")
    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_compliance_then_script_then_classify(self, mock_openai, mock_cosmos, mock_redis, sample_campaign_data, sample_customer_profile, sample_transcript):
        # Step 1: Check compliance
        mock_redis_client = MagicMock()
        mock_redis_client.sismember.return_value = False
        mock_redis_client.hget.return_value = None
        mock_redis_client.get.return_value = "0"
        mock_redis.return_value = mock_redis_client

        compliance = function_app.check_dnc_compliance(sample_customer_profile["phone_number"])
        assert compliance["is_compliant"] is True

        # Step 2: Generate script
        mock_client = MagicMock()
        mock_script_resp = MagicMock()
        mock_script_resp.choices = [MagicMock()]
        mock_script_resp.choices[0].message.content = json.dumps({
            "opening": "Hi Jane.", "value_proposition": "Great deal.",
            "talking_points": ["Discount"], "objection_responses": {},
            "closing": "Thanks.", "voicemail_script": "Leave a message."
        })
        mock_script_resp.model = "gpt-4o"
        mock_script_resp.usage.total_tokens = 400
        mock_client.chat.completions.create.return_value = mock_script_resp
        mock_openai.return_value = mock_client

        script = function_app.generate_call_script(sample_campaign_data, sample_customer_profile)
        assert "opening" in script

        # Step 3: Classify outcome
        mock_outcome_resp = MagicMock()
        mock_outcome_resp.choices = [MagicMock()]
        mock_outcome_resp.choices[0].message.content = json.dumps({
            "outcome": "sale_completed", "confidence": 0.92,
            "summary": "Customer agreed to renewal.",
            "follow_up_actions": ["Send contract"],
            "customer_interest_score": 9, "next_best_action": "Email contract"
        })
        mock_client.chat.completions.create.return_value = mock_outcome_resp

        mock_container = MagicMock()
        mock_cosmos.return_value = mock_container

        call_data = {"call_id": "call-001", "campaign_id": "camp-001", "phone_number": "+15551234567"}
        outcome = function_app.classify_call_outcome(call_data, sample_transcript)
        assert outcome["outcome"] == "sale_completed"
        assert outcome["call_id"] == "call-001"

    @patch("function_app.get_redis_client")
    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_dnc_request_adds_to_internal_list(self, mock_openai, mock_cosmos, mock_redis):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "outcome": "do_not_call", "confidence": 0.98,
            "summary": "Customer requested to not be called.",
            "follow_up_actions": ["Add to DNC"], "customer_interest_score": 0,
            "next_best_action": "Remove from campaigns"
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

    @patch("function_app.get_openai_client")
    def test_conversation_steering(self, mock_openai, sample_transcript):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "suggested_response": "We're offering 20% off for loyal customers.",
            "strategy": "consultative", "script_deviation": False,
            "escalation_needed": False, "escalation_reason": None, "confidence": 0.85
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        script = {"talking_points": ["Loyalty discount", "New features"]}
        result = function_app.steer_conversation(sample_transcript, script, "positive")
        assert result["strategy"] == "consultative"
        assert result["escalation_needed"] is False
        assert "generated_at" in result

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_sentiment(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.analyze_call_sentiment("test transcript")

    def test_config_defaults(self):
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.MAX_CALL_DURATION_SECONDS == 600
        assert function_app.Config.VOICEMAIL_DETECTION_TIMEOUT_MS == 5000
        assert function_app.Config.MAX_RETRY_ATTEMPTS == 3
        assert function_app.Config.CALL_THROTTLE_PER_MINUTE == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
