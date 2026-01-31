"""
IoT Predictive Maintenance Platform - Comprehensive Tests
=========================================================
3-tier testing: Positive, Negative, and Functional tests
for anomaly detection, RUL prediction, and maintenance recommendations.
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
def normal_sensor_data():
    return {"vibration_x": 2.34, "vibration_y": 1.87, "vibration_z": 0.92, "temperature": 67.5, "spindle_speed": 12000, "power_consumption": 8.7}


@pytest.fixture
def critical_sensor_data():
    return {"vibration_x": 8.5, "vibration_y": 6.2, "vibration_z": 4.0, "temperature": 95.0, "spindle_speed": 12000, "power_consumption": 15.0}


class TestPositive_AnomalyDetection:
    @patch("function_app.get_redis_client")
    def test_normal_readings_not_anomalous(self, mock_redis, normal_sensor_data):
        mock_client = MagicMock(); mock_client.get.return_value = None; mock_redis.return_value = mock_client
        result = function_app.detect_anomaly("cnc_001", normal_sensor_data)
        assert result["device_id"] == "cnc_001"
        assert result["is_anomalous"] is False

    @patch("function_app.get_redis_client")
    def test_critical_readings_detected(self, mock_redis, critical_sensor_data):
        mock_client = MagicMock(); mock_client.get.return_value = None; mock_redis.return_value = mock_client
        result = function_app.detect_anomaly("cnc_002", critical_sensor_data)
        assert result["is_anomalous"] is True
        assert len(result["anomalies"]) > 0

    @patch("function_app.get_redis_client")
    def test_anomaly_includes_sensor_details(self, mock_redis, critical_sensor_data):
        mock_client = MagicMock(); mock_client.get.return_value = None; mock_redis.return_value = mock_client
        result = function_app.detect_anomaly("cnc_003", critical_sensor_data)
        for anomaly in result["anomalies"]:
            assert "sensor" in anomaly
            assert "z_score" in anomaly
            assert "severity" in anomaly


class TestPositive_RULPrediction:
    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_normal_rul(self, mock_requests, mock_cred, normal_sensor_data):
        mock_token = MagicMock(); mock_token.token = "test-token"; mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock(); mock_response.status_code = 200; mock_response.json.return_value = {"rul_days": 120, "confidence": 0.82}
        mock_requests.post.return_value = mock_response
        result = function_app.predict_remaining_useful_life("cnc_001", normal_sensor_data)
        assert result["rul_days"] == 120
        assert result["severity"] == "normal"

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_boundary_warning(self, mock_requests, mock_cred, normal_sensor_data):
        mock_token = MagicMock(); mock_token.token = "test-token"; mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock(); mock_response.status_code = 200; mock_response.json.return_value = {"rul_days": 30, "confidence": 0.85}
        mock_requests.post.return_value = mock_response
        result = function_app.predict_remaining_useful_life("cnc_001", normal_sensor_data)
        assert result["rul_days"] == 30

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_boundary_critical(self, mock_requests, mock_cred, normal_sensor_data):
        mock_token = MagicMock(); mock_token.token = "test-token"; mock_cred.return_value.get_token.return_value = mock_token
        mock_response = MagicMock(); mock_response.status_code = 200; mock_response.json.return_value = {"rul_days": 7, "confidence": 0.90}
        mock_requests.post.return_value = mock_response
        result = function_app.predict_remaining_useful_life("cnc_001", normal_sensor_data)
        assert result["rul_days"] == 7


class TestPositive_MaintenanceRecommendation:
    @patch("function_app.get_openai_client")
    def test_recommendation_with_full_context(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Bearing wear.", "priority": "high", "recommended_actions": ["Replace bearing", "Check alignment"], "root_cause_analysis": "Vibration.", "spare_parts": ["SKF-6205"], "estimated_downtime_hours": 4, "safety_warnings": ["Lock out power"], "next_inspection_date": "2024-02-01"})
        mock_response.usage.prompt_tokens = 300; mock_response.usage.completion_tokens = 200; mock_response.usage.total_tokens = 500
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.generate_maintenance_recommendation("cnc_001", {"rul_days": 5, "severity": "critical"}, {"is_anomalous": True, "anomalies": [{"sensor": "vibration_x"}]}, [{"type": "bearing_replacement", "completedAt": "2023-06-15"}])
        assert result["priority"] == "high"
        assert result["device_id"] == "cnc_001"
        assert len(result["recommended_actions"]) == 2


class TestNegative_AnomalyDetection:
    def test_anomaly_missing_sensor_data_returns_400(self, mock_http_request):
        req = mock_http_request(body={"device_id": "cnc_001"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.anomaly_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_anomaly_missing_device_id_returns_400(self, mock_http_request):
        req = mock_http_request(body={"sensor_data": {"temperature": 70}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.anomaly_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_anomaly_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.anomaly_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400


class TestNegative_RULPrediction:
    def test_predict_missing_fields_returns_400(self, mock_http_request):
        req = mock_http_request(body={"sensor_data": {}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.predict_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.get_credential")
    @patch("function_app.requests")
    def test_predict_ml_service_error(self, mock_requests, mock_cred, normal_sensor_data):
        mock_token = MagicMock(); mock_token.token = "test-token"; mock_cred.return_value.get_token.return_value = mock_token
        mock_requests.post.side_effect = Exception("ML endpoint unavailable")
        with pytest.raises(Exception, match="ML endpoint unavailable"):
            function_app.predict_remaining_useful_life("cnc_001", normal_sensor_data)


class TestNegative_Recommendations:
    def test_recommend_missing_fields_returns_400(self, mock_http_request):
        req = mock_http_request(body={"device_id": "cnc_001"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.recommend_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.get_openai_client")
    def test_recommend_openai_error(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Service error")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Service error"):
            function_app.generate_maintenance_recommendation("cnc_001", {"rul_days": 5}, {"is_anomalous": True, "anomalies": []}, [])


class TestFunctional_IoTPipeline:
    @patch("function_app.get_openai_client")
    @patch("function_app.get_credential")
    @patch("function_app.requests")
    @patch("function_app.get_redis_client")
    def test_full_ingest_to_recommend_pipeline(self, mock_redis, mock_requests, mock_cred, mock_openai, critical_sensor_data):
        mock_redis_client = MagicMock(); mock_redis_client.get.return_value = None; mock_redis.return_value = mock_redis_client
        anomaly = function_app.detect_anomaly("cnc_001", critical_sensor_data)
        assert anomaly["is_anomalous"] is True

        mock_token = MagicMock(); mock_token.token = "test-token"; mock_cred.return_value.get_token.return_value = mock_token
        mock_ml = MagicMock(); mock_ml.status_code = 200; mock_ml.json.return_value = {"rul_days": 3, "confidence": 0.91}
        mock_requests.post.return_value = mock_ml
        prediction = function_app.predict_remaining_useful_life("cnc_001", critical_sensor_data)
        assert prediction["severity"] == "critical"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Urgent replacement.", "priority": "critical", "recommended_actions": ["Emergency replacement"], "root_cause_analysis": "Severe vibration.", "spare_parts": ["SKF-6205"], "estimated_downtime_hours": 6, "safety_warnings": ["Lock out power"], "next_inspection_date": "2024-01-20"})
        mock_response.usage.prompt_tokens = 400; mock_response.usage.completion_tokens = 250; mock_response.usage.total_tokens = 650
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        recommendation = function_app.generate_maintenance_recommendation("cnc_001", prediction, anomaly, [])
        assert recommendation["priority"] == "critical"

    @patch("function_app.get_cosmos_container")
    def test_fleet_overview_aggregation(self, mock_cosmos):
        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {"deviceId": "cnc_001", "rul_days": 3, "severity": "critical", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "cnc_002", "rul_days": 15, "severity": "warning", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "pump_001", "rul_days": 90, "severity": "normal", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "pump_002", "rul_days": 200, "severity": "normal", "predicted_at": "2024-01-15T10:00:00"},
            {"deviceId": "cnc_003", "rul_days": 5, "severity": "critical", "predicted_at": "2024-01-15T10:00:00"}
        ]
        mock_cosmos.return_value = mock_container
        result = function_app.get_fleet_overview()
        assert result["total_equipment"] == 5
        assert result["critical_count"] == 2
        assert result["warning_count"] == 1
        assert result["normal_count"] == 2

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_recommendation(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.generate_maintenance_recommendation("cnc_001", {"rul_days": 5}, {"is_anomalous": True, "anomalies": []}, [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
