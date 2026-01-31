"""
Document Summarization Platform - Comprehensive Tests
=====================================================
3-tier testing: Positive, Negative, and Functional tests
for document and CSV summarization with mocked Azure services.
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
def sample_csv_text():
    return """customerID,gender,SeniorCitizen,Partner,tenure,MonthlyCharges,TotalCharges,Churn
7590-VHVEG,Female,0,Yes,1,29.85,29.85,No
5575-GNVDE,Male,0,No,34,56.95,1889.5,No
3668-QPYBK,Male,0,No,2,53.85,108.15,Yes
9237-HQITU,Female,0,Yes,45,70.70,3046.05,No
2775-SEFEE,Male,1,No,8,99.65,820.5,Yes"""


class TestPositive_DocumentExtraction:
    @patch("function_app.get_document_intelligence_client")
    def test_extract_multipage_pdf(self, mock_di):
        mock_client = MagicMock()
        pages = []
        for i in range(1, 4):
            p = MagicMock(); p.page_number = i; p.width = 8.5; p.height = 11.0
            l = MagicMock(); l.content = f"Page {i}: Quarterly revenue data."
            p.lines = [l]; pages.append(p)
        mock_result = MagicMock(); mock_result.pages = pages; mock_result.tables = []
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client
        result = function_app.extract_document_text("https://storage.blob.core.windows.net/docs/report.pdf")
        assert result["page_count"] == 3
        assert len(result["pages"]) == 3

    @patch("function_app.get_document_intelligence_client")
    def test_extract_document_with_tables(self, mock_di):
        mock_client = MagicMock()
        p = MagicMock(); p.page_number = 1; p.width = 8.5; p.height = 11.0
        l = MagicMock(); l.content = "Revenue Report"; p.lines = [l]
        t = MagicMock(); t.row_count = 2; t.column_count = 2
        c = MagicMock(); c.row_index = 0; c.column_index = 0; c.content = "Q1"; t.cells = [c]
        mock_result = MagicMock(); mock_result.pages = [p]; mock_result.tables = [t]
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client
        result = function_app.extract_document_text("https://storage.blob.core.windows.net/docs/table.pdf")
        assert result["page_count"] == 1


class TestPositive_DocumentSummarization:
    @patch("function_app.get_openai_client")
    def test_summarize_executive_with_all_fields(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Strong growth.", "key_points": ["Revenue up 15%", "Cloud expansion", "New markets"], "topics": ["revenue"], "word_count": 500})
        mock_response.usage.prompt_tokens = 200; mock_response.usage.completion_tokens = 100; mock_response.usage.total_tokens = 300
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.summarize_document("Report text...", "executive")
        assert result["summary_type"] == "executive"
        assert len(result["key_points"]) == 3
        assert result["usage"]["total_tokens"] == 300

    @patch("function_app.get_openai_client")
    def test_summarize_detailed(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Detailed analysis.", "key_points": ["Revenue: $5M", "Costs: $3M", "Profit: $2M"], "topics": ["finance"], "word_count": 1000})
        mock_response.usage.prompt_tokens = 400; mock_response.usage.completion_tokens = 200; mock_response.usage.total_tokens = 600
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.summarize_document("Detailed report...", "detailed")
        assert len(result["key_points"]) == 3


class TestPositive_CsvSummarization:
    @patch("function_app.get_openai_client")
    def test_csv_trend_analysis(self, mock_openai, sample_csv_text):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Churn trends.", "insights": ["Short tenure = churn"], "patterns": [], "recommendations": ["Offer annual plans"]})
        mock_response.usage.prompt_tokens = 250; mock_response.usage.completion_tokens = 120; mock_response.usage.total_tokens = 370
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.summarize_csv_data(sample_csv_text, "trends")
        assert result["analysis_type"] == "trends"

    @patch("function_app.get_openai_client")
    def test_csv_overview_with_stats(self, mock_openai, sample_csv_text):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"summary": "Overview.", "insights": ["Mix"], "patterns": [], "recommendations": []})
        mock_response.usage.prompt_tokens = 200; mock_response.usage.completion_tokens = 80; mock_response.usage.total_tokens = 280
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        result = function_app.summarize_csv_data(sample_csv_text, "overview")
        assert result["data_stats"]["row_count"] == 5
        assert result["data_stats"]["column_count"] == 8


class TestNegative_Extraction:
    def test_summarize_missing_blob_url_returns_400(self, mock_http_request):
        req = mock_http_request(body={"title": "Test"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.summarize_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_summarize_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.summarize_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.get_document_intelligence_client")
    def test_extract_service_error(self, mock_di):
        mock_client = MagicMock()
        mock_client.begin_analyze_document_from_url.side_effect = Exception("Service unavailable")
        mock_di.return_value = mock_client
        with pytest.raises(Exception, match="Service unavailable"):
            function_app.extract_document_text("https://storage.blob.core.windows.net/test.pdf")


class TestNegative_Summarization:
    def test_summarize_text_missing_returns_400(self, mock_http_request):
        req = mock_http_request(body={"title": "Test"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.summarize_text_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_summarize_csv_missing_returns_400(self, mock_http_request):
        req = mock_http_request(body={"title": "Test"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.summarize_csv_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.get_openai_client")
    def test_summarize_openai_timeout(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Request timeout")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Request timeout"):
            function_app.summarize_document("Some text", "executive")


class TestNegative_SearchRetrieval:
    def test_search_missing_query_returns_400(self, mock_http_request):
        req = mock_http_request(body={"top_k": 5})
        import asyncio
        asyncio.get_event_loop().run_until_complete(function_app.search_endpoint(req))
        assert function_app.func.HttpResponse.call_args[1]["status_code"] == 400

    @patch("function_app.get_cosmos_container")
    def test_get_document_not_found(self, mock_cosmos):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(status_code=404, message="Not found")
        mock_cosmos.return_value = mock_container
        with pytest.raises(CosmosResourceNotFoundError):
            function_app.get_document_summary("nonexistent-id")

    @patch("function_app.get_search_client")
    @patch("function_app.generate_embedding")
    def test_search_returns_zero_results(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1] * 1536
        mock_client = MagicMock(); mock_client.search.return_value = []
        mock_search.return_value = mock_client
        results = function_app.search_documents("zzz_nonexistent_zzz")
        assert len(results) == 0


class TestFunctional_SummarizationPipeline:
    @patch("function_app.get_openai_client")
    @patch("function_app.get_document_intelligence_client")
    def test_extract_then_summarize_flow(self, mock_di, mock_openai):
        mock_client = MagicMock()
        p = MagicMock(); p.page_number = 1; p.width = 8.5; p.height = 11.0
        l = MagicMock(); l.content = "Q1 2024 Revenue: $5M with 15% growth."; p.lines = [l]
        mock_result = MagicMock(); mock_result.pages = [p]; mock_result.tables = []
        mock_poller = MagicMock(); mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client
        extraction = function_app.extract_document_text("https://storage.blob.core.windows.net/test.pdf")
        assert extraction["page_count"] == 1

        mock_oai = MagicMock()
        mock_oai_resp = MagicMock()
        mock_oai_resp.choices = [MagicMock()]
        mock_oai_resp.choices[0].message.content = json.dumps({"summary": "Q1 revenue $5M.", "key_points": ["Revenue: $5M"], "topics": ["revenue"], "word_count": 30})
        mock_oai_resp.usage.prompt_tokens = 150; mock_oai_resp.usage.completion_tokens = 80; mock_oai_resp.usage.total_tokens = 230
        mock_oai.chat.completions.create.return_value = mock_oai_resp
        mock_openai.return_value = mock_oai
        summary = function_app.summarize_document(extraction["text"], "executive")
        assert summary["summary_type"] == "executive"

    @patch("function_app.get_cosmos_container")
    def test_store_then_retrieve_document(self, mock_cosmos):
        mock_container = MagicMock()
        mock_container.read_item.return_value = {"id": "doc-100", "title": "Revenue Report", "summary": "Strong Q1.", "key_points": ["Revenue up"], "topics": ["finance"], "source": "upload", "created_at": "2024-01-15T10:00:00"}
        mock_cosmos.return_value = mock_container
        result = function_app.get_document_summary("doc-100")
        assert result["title"] == "Revenue Report"

    @patch("function_app.get_openai_client")
    def test_csv_analysis_all_types(self, mock_openai, sample_csv_text):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        for analysis_type in ["overview", "insights"]:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({"summary": f"Analysis: {analysis_type}", "insights": ["Insight 1"], "patterns": [], "recommendations": []})
            mock_response.usage.prompt_tokens = 200; mock_response.usage.completion_tokens = 80; mock_response.usage.total_tokens = 280
            mock_client.chat.completions.create.return_value = mock_response
            result = function_app.summarize_csv_data(sample_csv_text, analysis_type)
            assert result["analysis_type"] == analysis_type

    @patch("function_app.get_openai_client")
    def test_error_propagation_in_summarization(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client
        with pytest.raises(Exception, match="Rate limit exceeded"):
            function_app.summarize_document("test text", "executive")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
