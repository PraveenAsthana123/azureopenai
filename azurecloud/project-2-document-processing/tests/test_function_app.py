"""
Intelligent Document Processing - Unit Tests
=============================================
Comprehensive tests for document extraction, classification, validation,
and summarization with mocked Azure services.
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
sys.modules["azure.ai.formrecognizer"] = MagicMock()
sys.modules["azure.storage.blob"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()

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
def sample_extraction():
    """Sample Document Intelligence extraction result."""
    return {
        "text": "INVOICE\nInvoice Number: INV-2024-001\nDate: 2024-01-15\nVendor: Acme Corp\nAmount: $5,000.00\nDescription: Cloud services for Q1 2024",
        "page_count": 1,
        "pages": [
            {"page_number": 1, "text": "INVOICE...", "width": 8.5, "height": 11}
        ],
        "tables": [],
        "key_value_pairs": [
            {"key": "invoice number", "value": "INV-2024-001", "confidence": 0.95},
            {"key": "date", "value": "2024-01-15", "confidence": 0.92},
            {"key": "vendor", "value": "Acme Corp", "confidence": 0.90},
            {"key": "amount", "value": "$5,000.00", "confidence": 0.93}
        ],
        "model_id": "prebuilt-invoice",
        "extracted_at": datetime.utcnow().isoformat()
    }


# ==============================================================================
# Test Document Extraction
# ==============================================================================

class TestDocumentExtraction:
    """Tests for document text extraction via Document Intelligence."""

    @patch("function_app.get_document_intelligence_client")
    def test_extract_document_success(self, mock_di):
        """Test extracting text from a document via Document Intelligence."""
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 8.5
        mock_page.height = 11.0
        mock_line = MagicMock()
        mock_line.content = "Invoice Number: INV-2024-001"
        mock_page.lines = [mock_line]

        mock_kvp = MagicMock()
        mock_kvp.key.content = "Invoice Number"
        mock_kvp.value.content = "INV-2024-001"
        mock_kvp.confidence = 0.95

        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        mock_result.tables = []
        mock_result.key_value_pairs = [mock_kvp]

        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client

        result = function_app.extract_document(
            "https://storage.blob.core.windows.net/incoming/test.pdf"
        )

        assert result["page_count"] == 1
        assert "Invoice Number" in result["text"]
        assert len(result["key_value_pairs"]) == 1
        assert result["key_value_pairs"][0]["confidence"] == 0.95
        assert "extracted_at" in result

    def test_extract_missing_url(self, mock_http_request):
        """Test extract endpoint returns 400 when blob_url is missing."""
        req = mock_http_request(body={"model_id": "prebuilt-layout"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.extract_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400
        body = json.loads(call_args[0][0])
        assert "error" in body


# ==============================================================================
# Test Document Classification
# ==============================================================================

class TestDocumentClassification:
    """Tests for GPT-4o document classification."""

    @patch("function_app.get_openai_client")
    def test_classify_invoice(self, mock_openai):
        """Test classification of an invoice document."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "invoice",
            "confidence": 0.92,
            "reasoning": "Contains invoice number, vendor, and amount fields"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.classify_document("Invoice Number: INV-001\nAmount: $5000")

        assert result["category"] == "invoice"
        assert result["confidence"] == 0.92
        assert result["routing"] == "auto_process"
        assert "classified_at" in result

    @patch("function_app.get_openai_client")
    def test_classify_medium_confidence(self, mock_openai):
        """Test classification with medium confidence routes to human review."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "contract",
            "confidence": 0.72,
            "reasoning": "Appears to be a contract but missing key clauses"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.classify_document("Agreement between parties...")

        assert result["category"] == "contract"
        assert result["routing"] == "human_review"

    @patch("function_app.get_openai_client")
    def test_classify_low_confidence(self, mock_openai):
        """Test classification with low confidence routes to manual review."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "form",
            "confidence": 0.45,
            "reasoning": "Unclear document type"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.classify_document("Some ambiguous text...")

        assert result["routing"] == "manual_review"
        assert result["confidence"] < 0.60


# ==============================================================================
# Test Validation
# ==============================================================================

class TestValidation:
    """Tests for document validation against business rules."""

    def test_validate_valid_document(self, sample_extraction):
        """Test validation passes for a complete invoice."""
        result = function_app.validate_document(sample_extraction, "invoice")

        assert result["category"] == "invoice"
        assert result["fields_checked"] == 4
        assert "validated_at" in result

    def test_validate_empty_document(self):
        """Test validation fails for an empty document."""
        empty_extraction = {
            "text": "",
            "page_count": 0,
            "pages": [],
            "tables": [],
            "key_value_pairs": []
        }

        result = function_app.validate_document(empty_extraction, "invoice")

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("empty" in e.lower() for e in result["errors"])


# ==============================================================================
# Test Summarization
# ==============================================================================

class TestSummarization:
    """Tests for GPT-4o document summarization."""

    @patch("function_app.get_openai_client")
    def test_summarize_success(self, mock_openai):
        """Test document summarization generates summary and key points."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Invoice from Acme Corp for $5,000 cloud services in Q1 2024.",
            "key_points": ["Amount: $5,000", "Vendor: Acme Corp"],
            "action_items": ["Process payment by due date"],
            "word_count": 42
        })
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_document("Invoice text...", "invoice")

        assert "summary" in result
        assert len(result["key_points"]) == 2
        assert result["category"] == "invoice"
        assert result["usage"]["total_tokens"] == 300

    def test_summarize_missing_text(self, mock_http_request):
        """Test summarize endpoint returns 400 when text is missing."""
        req = mock_http_request(body={"category": "invoice"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.summarize_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Document Search
# ==============================================================================

class TestDocumentSearch:
    """Tests for hybrid document search."""

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_success(self, mock_embed, mock_search):
        """Test searching indexed documents."""
        mock_embed.return_value = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: {
            "id": "doc-1",
            "title": "Acme Invoice Q1",
            "category": "invoice",
            "summary": "Q1 invoice from Acme Corp",
            "source": "incoming/invoice.pdf",
            "status": "processed",
            "@search.score": 0.95,
            "@search.reranker_score": 0.88
        }.get(key, None)
        mock_result.get = lambda key, default=None: {
            "id": "doc-1",
            "title": "Acme Invoice Q1",
            "category": "invoice",
            "summary": "Q1 invoice from Acme Corp",
            "source": "incoming/invoice.pdf",
            "status": "processed",
            "@search.score": 0.95,
            "@search.reranker_score": 0.88
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_result]
        mock_search.return_value = mock_client

        results = function_app.search_documents("acme invoice", top_k=5)

        assert len(results) == 1
        assert results[0]["title"] == "Acme Invoice Q1"
        assert results[0]["category"] == "invoice"
        assert results[0]["score"] == 0.95

    def test_search_missing_query(self, mock_http_request):
        """Test search endpoint returns 400 when query is missing."""
        req = mock_http_request(body={"top_k": 5})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.search_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test Configuration
# ==============================================================================

class TestConfig:
    """Tests for the Config class defaults and thresholds."""

    def test_config_defaults(self):
        """Test that Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "documents-index"
        assert function_app.Config.DATABASE_NAME == "docprocessor"
        assert function_app.Config.CACHE_TTL == 3600

    def test_config_classification_thresholds(self):
        """Test classification threshold values."""
        assert function_app.Config.HIGH_CONFIDENCE_THRESHOLD == 0.85
        assert function_app.Config.MEDIUM_CONFIDENCE_THRESHOLD == 0.60
        assert len(function_app.Config.DOCUMENT_CATEGORIES) == 5
        assert "invoice" in function_app.Config.DOCUMENT_CATEGORIES


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
        assert body["service"] == "document-processing"
        assert "timestamp" in body
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
