# ============================================================================
# Project 11 - Legal Contract Analyzer - Unit Tests
# All external calls mocked | pytest | CUAD_v1 clause validation
# ============================================================================

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import exceptions as cosmos_exceptions


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_clauses():
    """Sample clause list for testing."""
    return [
        {"clause_type": "Parties", "text": "ACME Corp and Widget Inc.", "confidence": 0.95, "position": 1},
        {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.92, "position": 5},
        {"clause_type": "Non-Compete", "text": "12 month non-compete within 50 miles", "confidence": 0.88, "position": 12},
        {"clause_type": "Cap On Liability", "text": "Liability capped at $1M", "confidence": 0.91, "position": 20},
        {"clause_type": "Termination For Convenience", "text": "30 days written notice", "confidence": 0.87, "position": 25},
    ]


@pytest.fixture
def sample_contract_text():
    """Sample contract text for testing."""
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
    """Sample template from Cosmos DB."""
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
    """Create a mock HTTP request."""
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


# ============================================================================
# TestContractExtraction
# ============================================================================

class TestContractExtraction:
    """Tests for contract text extraction via Document Intelligence."""

    @patch("function_app.get_document_intelligence_client")
    def test_extract_text_success(self, mock_get_client):
        """Test successful text extraction from a contract document."""
        from function_app import extract_contract_text

        # Mock Document Intelligence response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_line = MagicMock()
        mock_line.content = "This is a sample contract line."

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.lines = [mock_line]
        mock_page.width = 8.5
        mock_page.height = 11.0

        mock_table_cell = MagicMock()
        mock_table_cell.row_index = 0
        mock_table_cell.column_index = 0
        mock_table_cell.content = "Cell Value"

        mock_table = MagicMock()
        mock_table.row_count = 1
        mock_table.column_count = 1
        mock_table.cells = [mock_table_cell]

        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        mock_result.tables = [mock_table]
        mock_result.signatures = []

        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller

        result = extract_contract_text("https://storage.blob.core.windows.net/contracts/test.pdf")

        assert "text" in result
        assert "pages" in result
        assert result["page_count"] == 1
        assert len(result["tables"]) == 1
        assert "sample contract" in result["text"]

    def test_extract_invalid_url(self, mock_http_request):
        """Test that missing blob_url returns 400."""
        from function_app import analyze_contract

        req = mock_http_request(body={})
        response = analyze_contract(req)

        assert response.status_code == 400
        body = json.loads(response.get_body())
        assert "error" in body


# ============================================================================
# TestClauseIdentification
# ============================================================================

class TestClauseIdentification:
    """Tests for CUAD clause identification."""

    @patch("function_app.get_openai_client")
    def test_identify_clauses_success(self, mock_get_client, sample_contract_text):
        """Test successful clause identification from contract text."""
        from function_app import identify_clauses

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Parties", "text": "ACME Corp and Widget Inc.", "confidence": 0.95, "position": 1},
                {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.92, "position": 5},
                {"clause_type": "Non-Compete", "text": "12 months, 50 miles", "confidence": 0.88, "position": 12},
                {"clause_type": "Cap On Liability", "text": "Capped at $1M", "confidence": 0.91, "position": 20},
                {"clause_type": "Termination For Convenience", "text": "30 days notice", "confidence": 0.87, "position": 25},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        clauses = identify_clauses(sample_contract_text)

        assert len(clauses) == 5
        for clause in clauses:
            assert "clause_type" in clause
            assert "text" in clause
            assert "confidence" in clause

    def test_identify_all_cuad_types(self):
        """Verify CUAD_CLAUSE_TYPES has exactly 41 entries."""
        from function_app import CUAD_CLAUSE_TYPES

        assert len(CUAD_CLAUSE_TYPES) == 41
        assert "Document Name" in CUAD_CLAUSE_TYPES
        assert "Parties" in CUAD_CLAUSE_TYPES
        assert "Third Party Beneficiary" in CUAD_CLAUSE_TYPES

    @patch("function_app.get_openai_client")
    def test_clause_confidence_range(self, mock_get_client, sample_contract_text):
        """Test that all clause confidence values are between 0.0 and 1.0."""
        from function_app import identify_clauses

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "clauses": [
                {"clause_type": "Parties", "text": "Test", "confidence": 0.95, "position": 1},
                {"clause_type": "Governing Law", "text": "Test", "confidence": 0.72, "position": 2},
                {"clause_type": "Non-Compete", "text": "Test", "confidence": 0.55, "position": 3},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        clauses = identify_clauses(sample_contract_text)

        for clause in clauses:
            assert 0.0 <= clause["confidence"] <= 1.0


# ============================================================================
# TestRiskAssessment
# ============================================================================

class TestRiskAssessment:
    """Tests for contract risk assessment."""

    @patch("function_app.get_openai_client")
    def test_assess_risk_high(self, mock_get_client):
        """Test high/critical risk detection for uncapped liability."""
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        clauses = [
            {"clause_type": "Uncapped Liability", "text": "No liability cap", "confidence": 0.95, "position": 10},
            {"clause_type": "Non-Compete", "text": "Unlimited non-compete", "confidence": 0.90, "position": 15},
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_risk_score": 9,
            "risk_level": "critical",
            "risks": [
                {"clause_type": "Uncapped Liability", "severity": "critical", "description": "No liability cap", "recommendation": "Add liability cap"},
                {"clause_type": "Non-Compete", "severity": "high", "description": "Unlimited scope", "recommendation": "Limit scope"},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = assess_risk(clauses)

        assert result["risk_level"] in ("critical", "high")
        assert result["overall_risk_score"] >= 7

    @patch("function_app.get_openai_client")
    def test_assess_risk_low(self, mock_get_client):
        """Test low risk for standard clauses."""
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        clauses = [
            {"clause_type": "Governing Law", "text": "State of Delaware", "confidence": 0.95, "position": 5},
            {"clause_type": "Cap On Liability", "text": "Capped at $2M", "confidence": 0.92, "position": 20},
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_risk_score": 2,
            "risk_level": "low",
            "risks": []
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = assess_risk(clauses)

        assert result["risk_level"] == "low"
        assert result["overall_risk_score"] <= 3

    @patch("function_app.get_openai_client")
    def test_risk_score_range(self, mock_get_client, sample_clauses):
        """Test that overall risk score is between 1 and 10."""
        from function_app import assess_risk

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_risk_score": 5,
            "risk_level": "medium",
            "risks": [{"clause_type": "Non-Compete", "severity": "medium", "description": "Test", "recommendation": "Review"}]
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = assess_risk(sample_clauses)

        assert 1 <= result["overall_risk_score"] <= 10


# ============================================================================
# TestContractSummary
# ============================================================================

class TestContractSummary:
    """Tests for contract summary generation."""

    @patch("function_app.get_openai_client")
    def test_generate_summary_success(self, mock_get_client, sample_contract_text, sample_clauses):
        """Test successful summary generation."""
        from function_app import generate_summary

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "executive_summary": "Master Services Agreement between ACME Corp and Widget Inc.",
            "key_highlights": ["Non-compete clause", "Liability cap at $1M"],
            "action_items": ["Review non-compete terms", "Confirm liability cap"],
            "parties": ["ACME Corporation", "Widget Inc."],
            "dates": {"agreement_date": "2025-01-01", "effective_date": "2025-01-01"},
            "financial_terms": {"liability_cap": "$1,000,000"},
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_summary(sample_contract_text, sample_clauses)

        assert "executive_summary" in result
        assert "key_highlights" in result
        assert "action_items" in result
        assert isinstance(result["key_highlights"], list)

    @patch("function_app.get_openai_client")
    def test_summary_includes_parties(self, mock_get_client, sample_contract_text, sample_clauses):
        """Test that summary includes parties field."""
        from function_app import generate_summary

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "executive_summary": "Agreement between two parties.",
            "key_highlights": [],
            "action_items": [],
            "parties": ["ACME Corporation", "Widget Inc."],
            "dates": {},
            "financial_terms": {},
        })
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_summary(sample_contract_text, sample_clauses)

        assert "parties" in result
        assert len(result["parties"]) >= 1


# ============================================================================
# TestTemplateComparison
# ============================================================================

class TestTemplateComparison:
    """Tests for template comparison."""

    @patch("function_app.get_cosmos_container")
    def test_compare_success(self, mock_get_container, sample_clauses, sample_template):
        """Test successful template comparison."""
        from function_app import compare_to_template

        mock_container = MagicMock()
        mock_container.read_item.return_value = sample_template
        mock_get_container.return_value = mock_container

        result = compare_to_template(sample_clauses, "template-nda-standard")

        assert "compliance_percentage" in result
        assert "deviations" in result
        assert isinstance(result["deviations"], list)
        assert "approval_needed" in result
        assert isinstance(result["compliance_percentage"], float)

    @patch("function_app.get_cosmos_container")
    def test_compare_template_not_found(self, mock_get_container, sample_clauses):
        """Test 404 when template is not found in Cosmos DB."""
        from function_app import compare_to_template

        mock_container = MagicMock()
        mock_container.read_item.side_effect = cosmos_exceptions.CosmosResourceNotFoundError(
            status_code=404, message="Not found"
        )
        mock_get_container.return_value = mock_container

        with pytest.raises(cosmos_exceptions.CosmosResourceNotFoundError):
            compare_to_template(sample_clauses, "nonexistent-template")


# ============================================================================
# TestObligationTracking
# ============================================================================

class TestObligationTracking:
    """Tests for obligation tracking."""

    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_track_obligations_success(self, mock_get_client, mock_get_container, sample_clauses):
        """Test successful obligation extraction and tracking."""
        from function_app import track_obligations

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "obligations": [
                {"obligation_id": "obl-1", "description": "Deliver services", "clause_type": "Minimum Commitment", "deadline": "2025-06-01", "responsible_party": "Provider", "obligation_type": "delivery", "priority": "high", "status": "pending"},
                {"obligation_id": "obl-2", "description": "Pay invoices within 30 days", "clause_type": "Price Restrictions", "deadline": "ongoing", "responsible_party": "Client", "obligation_type": "payment", "priority": "medium", "status": "pending"},
                {"obligation_id": "obl-3", "description": "Provide quarterly audit report", "clause_type": "Audit Rights", "deadline": "2025-03-31", "responsible_party": "Provider", "obligation_type": "reporting", "priority": "medium", "status": "pending"},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        obligations = track_obligations("contract-123", sample_clauses)

        assert len(obligations) == 3
        for obligation in obligations:
            assert "deadline" in obligation
            assert "responsible_party" in obligation

    @patch("function_app.get_cosmos_container")
    @patch("function_app.get_openai_client")
    def test_obligations_stored_in_cosmos(self, mock_get_client, mock_get_container, sample_clauses):
        """Test that obligations are stored in Cosmos DB."""
        from function_app import track_obligations

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "obligations": [
                {"obligation_id": "obl-1", "description": "Test obligation", "clause_type": "Audit Rights", "deadline": "2025-06-01", "responsible_party": "Provider", "obligation_type": "reporting", "priority": "high", "status": "pending"},
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response

        mock_container = MagicMock()
        mock_get_container.return_value = mock_container

        track_obligations("contract-456", sample_clauses)

        mock_container.create_item.assert_called_once()
        call_args = mock_container.create_item.call_args
        stored_item = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
        assert stored_item["contractId"] == "contract-456"


# ============================================================================
# TestConfig
# ============================================================================

class TestConfig:
    """Tests for configuration defaults."""

    def test_config_defaults(self):
        """Verify default configuration values."""
        from function_app import Config

        assert Config.GPT_MODEL == "gpt-4o"
        assert Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert Config.SEARCH_INDEX == "contracts-index"

    def test_cuad_clause_types_count(self):
        """Verify CUAD_CLAUSE_TYPES has exactly 41 entries."""
        from function_app import CUAD_CLAUSE_TYPES

        assert len(CUAD_CLAUSE_TYPES) == 41


# ============================================================================
# TestHealthCheck
# ============================================================================

class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self, mock_http_request):
        """Test health endpoint returns healthy status with timestamp."""
        from function_app import health_check

        req = mock_http_request(method="GET")
        response = health_check(req)

        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert body["status"] == "healthy"
        assert "timestamp" in body
        assert body["version"] == "1.0.0"


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
