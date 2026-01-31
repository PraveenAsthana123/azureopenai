"""
Intelligent Document Processing - Comprehensive Tests
=====================================================
3-tier testing: Positive, Negative, and Functional tests
for document extraction, classification, validation, and summarization.
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
sys.modules["azure.ai.formrecognizer"] = MagicMock()
sys.modules["azure.storage.blob"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["redis"] = MagicMock()

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
def sample_extraction():
    return {
        "text": "INVOICE\nInvoice Number: INV-2024-001\nDate: 2024-01-15\nVendor: Acme Corp\nAmount: $5,000.00",
        "page_count": 1,
        "pages": [{"page_number": 1, "text": "INVOICE...", "width": 8.5, "height": 11}],
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


@pytest.fixture
def sample_contract_extraction():
    return {
        "text": "AGREEMENT between ACME Corp and Widget Inc. Effective Date: 2024-01-01.",
        "page_count": 5,
        "pages": [{"page_number": i, "text": f"Page {i} content", "width": 8.5, "height": 11} for i in range(1, 6)],
        "tables": [],
        "key_value_pairs": [
            {"key": "party_a", "value": "ACME Corp", "confidence": 0.91},
            {"key": "party_b", "value": "Widget Inc", "confidence": 0.89}
        ],
        "model_id": "prebuilt-layout",
        "extracted_at": datetime.utcnow().isoformat()
    }


class TestPositive_DocumentExtraction:
    @patch("function_app.get_document_intelligence_client")
    def test_extract_with_layout_model(self, mock_di):
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 8.5
        mock_page.height = 11.0
        mock_line = MagicMock()
        mock_line.content = "Contract Agreement for Services"
        mock_page.lines = [mock_line]
        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        mock_result.tables = []
        mock_result.key_value_pairs = []
        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client

        result = function_app.extract_document("https://storage.blob.core.windows.net/incoming/contract.pdf")
        assert result["page_count"] == 1
        assert "Contract" in result["text"]
        assert "extracted_at" in result

    @patch("function_app.get_document_intelligence_client")
    def test_extract_multipage_document(self, mock_di):
        mock_client = MagicMock()
        pages = []
        for i in range(1, 4):
            mock_page = MagicMock()
            mock_page.page_number = i
            mock_page.width = 8.5
            mock_page.height = 11.0
            mock_line = MagicMock()
            mock_line.content = f"Page {i} content."
            mock_page.lines = [mock_line]
            pages.append(mock_page)
        mock_result = MagicMock()
        mock_result.pages = pages
        mock_result.tables = []
        mock_result.key_value_pairs = []
        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client

        result = function_app.extract_document("https://storage.blob.core.windows.net/incoming/multipage.pdf")
        assert result["page_count"] == 3


class TestPositive_Classification:
    @patch("function_app.get_openai_client")
    def test_classify_receipt(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "receipt", "confidence": 0.91, "reasoning": "Contains purchase total"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_document("Receipt Total: $42.50\nPayment: Visa ending 4567")
        assert result["category"] == "receipt"
        assert result["routing"] == "auto_process"

    @patch("function_app.get_openai_client")
    def test_classify_report(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "report", "confidence": 0.88, "reasoning": "Contains quarterly analysis"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_document("Q1 2024 Financial Report\nRevenue: $5M")
        assert result["category"] == "report"
        assert result["routing"] == "auto_process"

    @patch("function_app.get_openai_client")
    def test_classify_boundary_high_confidence(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "invoice", "confidence": 0.85, "reasoning": "Matches invoice pattern"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_document("Invoice #12345")
        assert result["routing"] == "auto_process"
        assert "classified_at" in result


class TestPositive_Validation:
    def test_validate_complete_invoice(self, sample_extraction):
        result = function_app.validate_document(sample_extraction, "invoice")
        assert result["category"] == "invoice"
        assert result["fields_checked"] == 4

    def test_validate_contract(self, sample_contract_extraction):
        result = function_app.validate_document(sample_contract_extraction, "contract")
        assert result["category"] == "contract"


class TestNegative_DocumentExtraction:
    def test_extract_missing_url_returns_400(self, mock_http_request):
        req = mock_http_request(body={"model_id": "prebuilt-layout"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.extract_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_extract_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.extract_endpoint(req))
        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    @patch("function_app.get_document_intelligence_client")
    def test_extract_service_error(self, mock_di):
        mock_client = MagicMock()
        mock_client.begin_analyze_document_from_url.side_effect = Exception("Document Intelligence service unavailable")
        mock_di.return_value = mock_client
        with pytest.raises(Exception, match="Document Intelligence service unavailable"):
            function_app.extract_document("https://storage.blob.core.windows.net/test.pdf")


class TestNegative_Classification:
    @patch("function_app.get_openai_client")
    def test_classify_confidence_zero(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "unknown", "confidence": 0.0, "reasoning": "Cannot determine"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.classify_document("Random gibberish")
        assert result["routing"] == "manual_review"

    @patch("function_app.get_openai_client")
    def test_classify_openai_timeout(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Request timeout")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Request timeout"):
            function_app.classify_document("Some document text")


class TestNegative_Validation:
    def test_validate_empty_document(self):
        empty = {"text": "", "page_count": 0, "pages": [], "tables": [], "key_value_pairs": []}
        result = function_app.validate_document(empty, "invoice")
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_no_key_value_pairs(self):
        extraction = {"text": "Some random text", "page_count": 1, "pages": [{"page_number": 1}], "tables": [], "key_value_pairs": []}
        result = function_app.validate_document(extraction, "invoice")
        assert result["fields_checked"] == 0


class TestNegative_Search:
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
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_search.return_value = mock_client
        results = function_app.search_documents("zzz_nonexistent_topic_zzz")
        assert len(results) == 0


class TestFunctional_DocumentPipeline:
    @patch("function_app.get_openai_client")
    @patch("function_app.get_document_intelligence_client")
    def test_extract_then_classify_flow(self, mock_di, mock_openai):
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 8.5
        mock_page.height = 11.0
        mock_line = MagicMock()
        mock_line.content = "Invoice Number: INV-2024-001 Amount: $5,000"
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

        extraction = function_app.extract_document("https://storage.blob.core.windows.net/test.pdf")
        assert extraction["page_count"] == 1

        mock_oai_client = MagicMock()
        mock_oai_response = MagicMock()
        mock_oai_response.choices = [MagicMock()]
        mock_oai_response.choices[0].message.content = json.dumps({
            "category": "invoice", "confidence": 0.92, "reasoning": "Contains invoice number"
        })
        mock_oai_client.chat.completions.create.return_value = mock_oai_response
        mock_openai.return_value = mock_oai_client

        classification = function_app.classify_document(extraction["text"])
        assert classification["category"] == "invoice"
        assert classification["routing"] == "auto_process"

    @patch("function_app.get_openai_client")
    def test_classify_then_validate_flow(self, mock_openai, sample_extraction):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "invoice", "confidence": 0.92, "reasoning": "Contains invoice fields"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        classification = function_app.classify_document(sample_extraction["text"])
        assert classification["routing"] == "auto_process"

        validation = function_app.validate_document(sample_extraction, classification["category"])
        assert validation["category"] == "invoice"
        assert validation["fields_checked"] == 4

    @patch("function_app.get_openai_client")
    def test_summarize_with_token_tracking(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Invoice from Acme Corp.", "key_points": ["Amount: $5,000", "Vendor: Acme Corp"],
            "action_items": ["Process payment"], "word_count": 30
        })
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_document("Invoice text...", "invoice")
        assert result["usage"]["total_tokens"] == 300
        assert len(result["key_points"]) == 2

    @patch("function_app.get_openai_client")
    def test_classification_routing_thresholds(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        mock_response.choices[0].message.content = json.dumps({"category": "invoice", "confidence": 0.90, "reasoning": "Clear"})
        mock_client.chat.completions.create.return_value = mock_response
        assert function_app.classify_document("Invoice #123")["routing"] == "auto_process"

        mock_response.choices[0].message.content = json.dumps({"category": "contract", "confidence": 0.72, "reasoning": "Maybe"})
        assert function_app.classify_document("Agreement...")["routing"] == "human_review"

        mock_response.choices[0].message.content = json.dumps({"category": "form", "confidence": 0.45, "reasoning": "Unclear"})
        assert function_app.classify_document("Ambiguous")["routing"] == "manual_review"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
