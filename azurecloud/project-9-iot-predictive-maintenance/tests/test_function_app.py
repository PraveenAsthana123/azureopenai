"""
IoT Predictive Maintenance Platform - Unit Tests
=================================================
Comprehensive tests for predictive maintenance functions
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
sys.modules["azure.storage.blob"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["requests"] = MagicMock()

import function_app


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_sensor_data():
    """Sample sensor readings from a CNC machine."""
    return {
        "vibration_x": 2.34,
        "vibration_y": 1.87,
        "vibration_z": 0.92,
        "temperature": 67.5,
        "spindle_speed": 12000,
        "power_consumption": 8.7
    }


@pytest.fixture
def sample_anomalous_sensor_data():
    """Sensor data with anomalous readings."""
    return {
        "vibration_x": 8.5,
        "vibration_y": 6.2,
        "temperature": 95.0,
        "spindle_speed": 12000,
        "power_consumption": 15.0
    }


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
# Test Anomaly Detection
# ==============================================================================

class TestAnomalyDetection:
    """Tests for anomaly detection in sensor data."""

    @patch("function_app.get_redis_client")
    def test_normal_readings(self, mock_redis, sample_sensor_data):
        """Test that normal readings are not flagged as anomalous."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = function_app.detect_anomaly("cnc_001", sample_sensor_data)

        assert result["device_id"] == "cnc_001"
        assert result["is_anomalous"] is False
        assert result["anomaly_score"] < function_app.Config.ANOMALY_THRESHOLD

    @patch("function_app.get_redis_client")
    def test_anomalous_readings(self, mock_redis, sample_anomalous_sensor_data):
        """Test that anomalous readings are detected."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = function_app.detect_anomaly("cnc_002", sample_anomalous_sensor_data)

        assert result["is_anomalous"] is True
        assert len(result["anomalies"]) > 0
        assert result["anomaly_score"] >= function_app.Config.ANOMALY_THRESHOLD

    @patch("function_app.get_redis_client")
    def test_anomaly_details(self, mock_redis, sample_anomalous_sensor_data):
        """Test that anomaly details include sensor info."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = function_app.detect_anomaly("cnc_003", sample_anomalous_sensor_data)

        for anomaly in result["anomalies"]:
            assert "sensor" in anomaly
            assert "z_score" in anomaly
            assert "severity" in anomaly

    def test_anomaly_missing_fields(self, mock_http_request):
        """Test endpoint returns 400 when fields are missing."""
        req = mock_http_request(body={"device_id": "cnc_001"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.anomaly_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test RUL Prediction
# ==============================================================================

class TestRULPrediction:
    """Tests for Remaining Useful Life prediction."""

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_critical(self, mock_requests, mock_cred, sample_sensor_data):
        """Test prediction returning critical severity."""
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rul_days": 3, "confidence": 0.91}
        mock_requests.post.return_value = mock_response

        result = function_app.predict_remaining_useful_life("cnc_001", sample_sensor_data)

        assert result["rul_days"] == 3
        assert result["severity"] == "critical"
        assert result["confidence"] == 0.91

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_warning(self, mock_requests, mock_cred, sample_sensor_data):
        """Test prediction returning warning severity."""
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rul_days": 15, "confidence": 0.85}
        mock_requests.post.return_value = mock_response

        result = function_app.predict_remaining_useful_life("cnc_001", sample_sensor_data)

        assert result["severity"] == "warning"

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_normal(self, mock_requests, mock_cred, sample_sensor_data):
        """Test prediction returning normal severity."""
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred.return_value.get_token.return_value = mock_token

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rul_days": 120, "confidence": 0.78}
        mock_requests.post.return_value = mock_response

        result = function_app.predict_remaining_useful_life("cnc_001", sample_sensor_data)

        assert result["severity"] == "normal"

    def test_predict_missing_fields(self, mock_http_request):
        """Test endpoint returns 400 when fields are missing."""
        req = mock_http_request(body={"sensor_data": {}})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.predict_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Maintenance Recommendation
# ==============================================================================

class TestMaintenanceRecommendation:
    """Tests for AI maintenance recommendations."""

    @patch("function_app.get_openai_client")
    def test_generate_recommendation(self, mock_openai):
        """Test generating maintenance recommendations."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Bearing degradation detected. Replace within 5 days.",
            "priority": "high",
            "recommended_actions": ["Replace main bearing", "Inspect spindle alignment"],
            "root_cause_analysis": "Excessive vibration indicates bearing wear.",
            "spare_parts": ["SKF-6205 bearing"],
            "estimated_downtime_hours": 4,
            "safety_warnings": ["Lock out power before maintenance"],
            "next_inspection_date": "2024-02-01"
        })
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 500
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        prediction = {"rul_days": 5, "severity": "critical"}
        anomaly = {"is_anomalous": True, "anomalies": [{"sensor": "vibration_x"}]}
        history = [{"type": "bearing_replacement", "completedAt": "2023-06-15"}]

        result = function_app.generate_maintenance_recommendation(
            "cnc_001", prediction, anomaly, history
        )

        assert result["priority"] == "high"
        assert len(result["recommended_actions"]) == 2
        assert result["device_id"] == "cnc_001"
        assert result["usage"]["total_tokens"] == 500

    def test_recommend_missing_fields(self, mock_http_request):
        """Test endpoint returns 400 when fields are missing."""
        req = mock_http_request(body={"device_id": "cnc_001"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.recommend_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Fleet Overview
# ==============================================================================

class TestFleetOverview:
    """Tests for fleet-wide equipment monitoring."""

    @patch("function_app.get_cosmos_container")
    def test_fleet_overview(self, mock_cosmos):
        """Test fleet overview aggregation."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {"deviceId": "cnc_001", "rul_days": 3, "severity": "critical", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "cnc_002", "rul_days": 15, "severity": "warning", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "pump_001", "rul_days": 90, "severity": "normal", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "pump_002", "rul_days": 120, "severity": "normal", "predicted_at": "2024-01-15T10:00:00"}
        ]
        mock_cosmos.return_value = mock_container

        result = function_app.get_fleet_overview()

        assert result["total_equipment"] == 4
        assert result["critical_count"] == 1
        assert result["warning_count"] == 1
        assert result["normal_count"] == 2
        assert "cnc_001" in result["critical_devices"]


# ==============================================================================
# Test Config
# ==============================================================================

class TestConfig:
    """Tests for configuration defaults."""

    def test_config_defaults(self):
        """Test Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.DATABASE_NAME == "predictive-maintenance"
        assert function_app.Config.ANOMALY_THRESHOLD == 0.85
        assert function_app.Config.RUL_CRITICAL_DAYS == 7
        assert function_app.Config.RUL_WARNING_DAYS == 30

    def test_config_env_vars(self):
        """Test environment variable config attributes."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT", "COSMOS_ENDPOINT",
            "STORAGE_ACCOUNT_URL", "IOT_HUB_HOSTNAME",
            "ML_ENDPOINT", "REDIS_HOST", "KEY_VAULT_URL"
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
        assert body["service"] == "iot-predictive-maintenance"
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
