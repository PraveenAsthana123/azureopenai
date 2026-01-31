"""
Legal Contract Analyzer - Comprehensive Tests
===============================================
3-tier testing: Positive, Negative, and Functional tests
for contract extraction, clause identification, risk assessment,
summary generation, template comparison, and obligation tracking.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import exceptions as cosmos_exceptions


@pytest.fixture
def sample_clauses():
    return [
        {"clause_type": "Parties", "text": "ACME Corp and Widget Inc.", "confidence": 0.95, "position": 1},
        {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.92, "position": 5},
        {"clause_type": "Non-Compete", "text": "12 month non-compete within 50 miles", "confidence": 0.88, "position": 12},
        {"clause_type": "Cap On Liability", "text": "Liability capped at $1M", "confidence": 0.91, "position": 20},
        {"clause_type": "Termination For Convenience", "text": "30 days written notice", "confidence": 0.87, "position": 25},
    ]


@pytest.fixture
def sample_contract_text():
    return (
        "MASTER SERVICES AGREEMENT\n\n"
        "This Agreement is entered into as of January 1, 2025 between "
        "ACME Corporation ('Client') and Widget Inc. ('Provider').\n\n"
        "1. GOVERNING LAW: This agreement shall be governed by the laws of "
        "the State of Delaware.\n\n"
        "2. NON-COMPETE: Provider agrees not to engage in competing business "
        "within 50 miles for a period of 12 months.\n\n"
        "3. LIABILITY: Total liability under this agreement shall not exceed $1,000,000.\n\n"
        "4. TERMINATION: Either party may terminate with 30 days written notice."
    )


@pytest.fixture
def sample_template():
    return {
        "id": "template-nda-standard",
        "templateId": "template-nda-standard",
        "name": "Standard NDA Template",
        "clauses": [
            {"clause_type": "Parties", "expected_text": "ACME Corp and Widget Inc.", "deviation_severity": "low"},
            {"clause_type": "Governing Law", "expected_text": "State of Delaware", "deviation_severity": "medium"},
            {"clause_type": "Non-Compete", "expected_text": "12 month non-compete within 100 miles", "deviation_severity": "high"},
            {"clause_type": "Cap On Liability", "expected_text": "Liability capped at $2M", "deviation_severity": "high"},
        ],
    }


@pytest.fixture
def mock_http_request():
    def _create_request(body=None, method="POST", url="http://localhost"):
        req = MagicMock(spec=func.HttpRequest)
        req.method = method
        req.url = url
        if body:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _create_request


class TestPositive_ContractExtraction:
    @patch("function_app.get_document_intelligence_client")
    def test_extract_multipage_contract(self, mock_di):
        from function_app import extract_contract_text

        mock_client = MagicMock()
        mock_di.return_value = mock_client
        pages = []
        for i in range(1, 6):
            p = MagicMock(); p.page_number = i; p.width = 8.5; p.height = 11.0
            l = MagicMock(); l.content = f"Page {i}: Contract terms and conditions."
            p.lines = [l]; pages.append(p)
        mock_result = MagicMock(); mock_result.pages = pages; mock_result.tables = []; mock_result.signatures = []
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller

        result = extract_contract_text("https://storage.blob.core.windows.net/contracts/msa.pdf")
        assert result["page_count"] == 5
        assert len(result["pages"]) == 5

    @patch("function_app.get_document_intelligence_client")
    def test_extract_contract_with_tables(self, mock_di):
        from function_app import extract_contract_text

        mock_client = MagicMock()
        mock_di.return_value = mock_client
        p = MagicMock(); p.page_number = 1; p.width = 8.5; p.height = 11.0
        l = MagicMock(); l.content = "Payment Schedule"; p.lines = [l]
        t = MagicMock(); t.row_count = 3; t.column_count = 2
        c = MagicMock(); c.row_index = 0; c.column_index = 0; c.content = "Q1"
        t.cells = [c]
        mock_result = MagicMock(); mock_result.pages = [p]; mock_result.tables = [t]; mock_result.signatures = []
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller

        result = extract_contract_text("https://storage.blob.core.windows.net/contracts/schedule.pdf")
        assert result["page_count"] == 1
        assert len(result["tables"]) == 1


class TestPositive_ClauseIdentification:
    @patch("function_app.get_openai_client")
    def test_identify_all_clause_fields(self, mock_openai, sample_contract_text):
        from function_app import identify_clauses

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Parties", "text": "ACME Corp and Widget Inc.", "confidence": 0.95, "position": 1},
                {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.92, "position": 5},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        clauses = identify_clauses(sample_contract_text)
        assert len(clauses) == 2
        for clause in clauses:
            assert "clause_type" in clause
            assert "text" in clause
            assert "confidence" in clause
            assert "position" in clause

    def test_cuad_clause_types_count(self):
        from function_app import CUAD_CLAUSE_TYPES
        assert len(CUAD_CLAUSE_TYPES) == 41
        assert "Parties" in CUAD_CLAUSE_TYPES
        assert "Document Name" in CUAD_CLAUSE_TYPES
        assert "Third Party Beneficiary" in CUAD_CLAUSE_TYPES

    @patch("function_app.get_openai_client")
    def test_clause_confidence_all_valid(self, mock_openai, sample_contract_text):
        from function_app import identify_clauses

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Parties", "text": "Test", "confidence": 0.99, "position": 1},
                {"clause_type": "Non-Compete", "text": "Test", "confidence": 0.50, "position": 2},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        clauses = identify_clauses(sample_contract_text)
        for clause in clauses:
            assert 0.0 <= clause["confidence"] <= 1.0


class TestPositive_RiskAssessment:
    @patch("function_app.get_openai_client")
    def test_assess_risk_medium(self, mock_openai, sample_clauses):
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_risk_score": 5,
            "risk_level": "medium",
            "risks": [{"clause_type": "Non-Compete", "severity": "medium", "description": "Scope could be broader", "recommendation": "Review"}]
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = assess_risk(sample_clauses)
        assert result["risk_level"] == "medium"
        assert 1 <= result["overall_risk_score"] <= 10

    @patch("function_app.get_openai_client")
    def test_assess_risk_low_standard_clauses(self, mock_openai):
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        clauses = [
            {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.95, "position": 5},
            {"clause_type": "Cap On Liability", "text": "Capped at $2M", "confidence": 0.92, "position": 20},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_risk_score": 2, "risk_level": "low", "risks": []
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = assess_risk(clauses)
        assert result["risk_level"] == "low"
        assert result["overall_risk_score"] <= 3


class TestPositive_SummaryGeneration:
    @patch("function_app.get_openai_client")
    def test_generate_summary_all_fields(self, mock_openai, sample_contract_text, sample_clauses):
        from function_app import generate_summary

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "executive_summary": "MSA between ACME Corp and Widget Inc.",
            "key_highlights": ["Non-compete clause", "Liability cap at $1M"],
            "action_items": ["Review non-compete terms"],
            "parties": ["ACME Corporation", "Widget Inc."],
            "dates": {"agreement_date": "2025-01-01"},
            "financial_terms": {"liability_cap": "$1,000,000"},
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_summary(sample_contract_text, sample_clauses)
        assert "executive_summary" in result
        assert "key_highlights" in result
        assert "parties" in result
        assert isinstance(result["key_highlights"], list)
        assert len(result["parties"]) == 2


class TestPositive_TemplateComparison:
    @patch("function_app.get_cosmos_container")
    def test_compare_with_deviations(self, mock_cosmos, sample_clauses, sample_template):
        from function_app import compare_to_template

        mock_container = MagicMock()
        mock_container.read_item.return_value = sample_template
        mock_cosmos.return_value = mock_container

        result = compare_to_template(sample_clauses, "template-nda-standard")
        assert "compliance_percentage" in result
        assert "deviations" in result
        assert isinstance(result["compliance_percentage"], float)
        assert "approval_needed" in result


class TestNegative_ContractExtraction:
    def test_analyze_missing_blob_url(self, mock_http_request):
        from function_app import analyze_contract

        req = mock_http_request(body={})
        response = analyze_contract(req)
        assert response.status_code == 400
        body = json.loads(response.get_body())
        assert "error" in body

    def test_analyze_malformed_json(self, mock_http_request):
        from function_app import analyze_contract

        req = mock_http_request(body=None)
        response = analyze_contract(req)
        assert response.status_code == 400

    @patch("function_app.get_document_intelligence_client")
    def test_extract_service_error(self, mock_di):
        from function_app import extract_contract_text

        mock_client = MagicMock()
        mock_client.begin_analyze_document_from_url.side_effect = Exception("Document Intelligence unavailable")
        mock_di.return_value = mock_client
        with pytest.raises(Exception, match="Document Intelligence unavailable"):
            extract_contract_text("https://storage.blob.core.windows.net/test.pdf")


class TestNegative_ClauseIdentification:
    @patch("function_app.get_openai_client")
    def test_identify_clauses_openai_error(self, mock_openai, sample_contract_text):
        from function_app import identify_clauses

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            identify_clauses(sample_contract_text)


class TestNegative_RiskAssessment:
    @patch("function_app.get_openai_client")
    def test_assess_risk_openai_timeout(self, mock_openai, sample_clauses):
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Request timeout")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Request timeout"):
            assess_risk(sample_clauses)


class TestNegative_TemplateComparison:
    @patch("function_app.get_cosmos_container")
    def test_compare_template_not_found(self, mock_cosmos, sample_clauses):
        from function_app import compare_to_template

        mock_container = MagicMock()
        mock_container.read_item.side_effect = cosmos_exceptions.CosmosResourceNotFoundError(
            status_code=404, message="Not found"
        )
        mock_cosmos.return_value = mock_container
        with pytest.raises(cosmos_exceptions.CosmosResourceNotFoundError):
            compare_to_template(sample_clauses, "nonexistent-template")


class TestFunctional_ContractPipeline:
    @patch("function_app.get_openai_client")
    @patch("function_app.get_document_intelligence_client")
    def test_extract_then_identify_clauses(self, mock_di, mock_openai, sample_contract_text):
        from function_app import extract_contract_text, identify_clauses

        mock_client = MagicMock()
        mock_di.return_value = mock_client
        p = MagicMock(); p.page_number = 1; p.width = 8.5; p.height = 11.0
        l = MagicMock(); l.content = sample_contract_text; p.lines = [l]
        mock_result = MagicMock(); mock_result.pages = [p]; mock_result.tables = []; mock_result.signatures = []
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller

        extraction = extract_contract_text("https://storage.blob.core.windows.net/contracts/test.pdf")
        assert extraction["page_count"] == 1

        mock_oai = MagicMock()
        mock_openai.return_value = mock_oai
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Parties", "text": "ACME Corp and Widget Inc.", "confidence": 0.95, "position": 1},
                {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.92, "position": 5},
            ]
        })
        mock_oai.chat.completions.create.return_value = mock_response

        clauses = identify_clauses(extraction["text"])
        assert len(clauses) == 2

    @patch("function_app.get_openai_client")
    def test_identify_then_assess_risk(self, mock_openai, sample_contract_text):
        from function_app import identify_clauses, assess_risk

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_clause_resp = MagicMock()
        mock_clause_resp.choices = [MagicMock()]
        mock_clause_resp.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Uncapped Liability", "text": "No cap", "confidence": 0.93, "position": 10},
                {"clause_type": "Non-Compete", "text": "Unlimited scope", "confidence": 0.90, "position": 15},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_clause_resp
        clauses = identify_clauses(sample_contract_text)

        mock_risk_resp = MagicMock()
        mock_risk_resp.choices = [MagicMock()]
        mock_risk_resp.choices[0].message.content = json.dumps({
            "overall_risk_score": 8, "risk_level": "high",
            "risks": [{"clause_type": "Uncapped Liability", "severity": "critical", "description": "No cap", "recommendation": "Add cap"}]
        })
        mock_client.chat.completions.create.return_value = mock_risk_resp
        risk = assess_risk(clauses)
        assert risk["risk_level"] in ("high", "critical")
        assert risk["overall_risk_score"] >= 7

    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_obligations_stored_in_cosmos(self, mock_openai, mock_cosmos, sample_clauses):
        from function_app import track_obligations

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "obligations": [
                {"obligation_id": "obl-1", "description": "Deliver services", "clause_type": "Minimum Commitment", "deadline": "2025-06-01", "responsible_party": "Provider", "obligation_type": "delivery", "priority": "high", "status": "pending"},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        mock_container = MagicMock()
        mock_cosmos.return_value = mock_container

        obligations = track_obligations("contract-789", sample_clauses)
        assert len(obligations) == 1
        assert obligations[0]["responsible_party"] == "Provider"
        mock_container.create_item.assert_called_once()

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_risk_assessment(self, mock_openai):
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Service unavailable")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Service unavailable"):
            assess_risk([{"clause_type": "Test", "text": "Test", "confidence": 0.9, "position": 1}])

    def test_health_endpoint_returns_200(self, mock_http_request):
        from function_app import health_check

        req = mock_http_request(method="GET")
        response = health_check(req)
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert body["status"] == "healthy"
        assert body["version"] == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
