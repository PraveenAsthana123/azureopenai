"""
Document Summarization Platform - Unit Tests
=============================================
Comprehensive tests for document and CSV summarization functions
with mocked Azure services.
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
def sample_extraction():
    """Sample Document Intelligence extraction result."""
    return {
        "text": "This is a sample document about quarterly revenue. The company earned $5M in Q1 2024. Key highlights include growth in cloud services and expansion into new markets.",
        "page_count": 3,
        "pages": [
            {"page_number": 1, "text": "This is a sample document about quarterly revenue.", "width": 8.5, "height": 11},
            {"page_number": 2, "text": "The company earned $5M in Q1 2024.", "width": 8.5, "height": 11},
            {"page_number": 3, "text": "Key highlights include growth in cloud services.", "width": 8.5, "height": 11}
        ],
        "tables": [
            {"row_count": 3, "column_count": 2, "cells": [
                {"row": 0, "column": 0, "content": "Quarter"},
                {"row": 0, "column": 1, "content": "Revenue"},
                {"row": 1, "column": 0, "content": "Q1"},
                {"row": 1, "column": 1, "content": "$5M"}
            ]}
        ],
        "extracted_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_summary_result():
    """Sample GPT-4o summarization result."""
    return {
        "summary": "The quarterly report shows $5M revenue in Q1 2024 with strong cloud growth.",
        "key_points": [
            "Revenue reached $5M in Q1 2024",
            "Cloud services driving growth",
            "Expansion into new markets"
        ],
        "topics": ["revenue", "cloud services", "market expansion"],
        "word_count": 42,
        "summary_type": "executive",
        "generated_at": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 150,
            "total_tokens": 350
        }
    }


@pytest.fixture
def sample_csv_text():
    """Sample CSV content (subset of Telco-Customer-Churn format)."""
    return """customerID,gender,SeniorCitizen,Partner,tenure,MonthlyCharges,TotalCharges,Churn
7590-VHVEG,Female,0,Yes,1,29.85,29.85,No
5575-GNVDE,Male,0,No,34,56.95,1889.5,No
3668-QPYBK,Male,0,No,2,53.85,108.15,Yes"""


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
# Test Document Extraction
# ==============================================================================

class TestDocumentExtraction:
    """Tests for the document text extraction function."""

    @patch("function_app.get_document_intelligence_client")
    def test_extract_text_success(self, mock_di):
        """Test extracting text from a PDF via Document Intelligence."""
        # Setup mock
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 8.5
        mock_page.height = 11.0
        mock_line = MagicMock()
        mock_line.content = "Sample document text content."
        mock_page.lines = [mock_line]

        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        mock_result.tables = []

        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_di.return_value = mock_client

        # Execute
        result = function_app.extract_document_text("https://storage.blob.core.windows.net/docs/test.pdf")

        # Assert
        assert result["page_count"] == 1
        assert "Sample document text content." in result["text"]
        assert len(result["pages"]) == 1
        assert "extracted_at" in result

    def test_extract_missing_url(self, mock_http_request):
        """Test summarize endpoint returns 400 when blob_url is missing."""
        req = mock_http_request(body={"title": "Test"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.summarize_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400
        body = json.loads(call_args[0][0])
        assert "error" in body


# ==============================================================================
# Test Document Summarization
# ==============================================================================

class TestDocumentSummarization:
    """Tests for GPT-4o document summarization."""

    @patch("function_app.get_openai_client")
    def test_summarize_executive(self, mock_openai):
        """Test executive summary generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "This report covers Q1 2024 financial results.",
            "key_points": ["Revenue grew 15%", "Cloud expansion"],
            "topics": ["finance", "cloud"],
            "word_count": 500
        })
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_document("Sample text here...", "executive")

        assert "summary" in result
        assert len(result["key_points"]) == 2
        assert result["summary_type"] == "executive"
        assert result["usage"]["total_tokens"] == 300

    @patch("function_app.get_openai_client")
    def test_summarize_bullet(self, mock_openai):
        """Test bullet-point summary generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "- Point 1\n- Point 2\n- Point 3",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "topics": ["topic1"],
            "word_count": 200
        })
        mock_response.usage.prompt_tokens = 180
        mock_response.usage.completion_tokens = 80
        mock_response.usage.total_tokens = 260
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_document("Some text...", "bullet")

        assert result["summary_type"] == "bullet"
        assert len(result["key_points"]) == 3

    def test_summarize_text_missing(self, mock_http_request):
        """Test summarize/text endpoint returns 400 when text is missing."""
        req = mock_http_request(body={"title": "Test"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.summarize_text_endpoint(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400


# ==============================================================================
# Test CSV Summarization
# ==============================================================================

class TestCsvSummarization:
    """Tests for CSV data analysis and summarization."""

    @patch("function_app.get_openai_client")
    def test_summarize_csv_overview(self, mock_openai, sample_csv_text):
        """Test CSV overview analysis with Telco churn data format."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Telco customer dataset with 3 rows showing customer demographics, services, and churn status.",
            "insights": ["Month-to-month contracts correlate with higher churn", "Senior citizens show different patterns"],
            "patterns": ["Churn rate varies by tenure"],
            "recommendations": ["Target at-risk customers"]
        })
        mock_response.usage.prompt_tokens = 250
        mock_response.usage.completion_tokens = 120
        mock_response.usage.total_tokens = 370
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_csv_data(sample_csv_text, "overview")

        assert result["data_stats"]["row_count"] == 3
        assert result["data_stats"]["column_count"] == 8
        assert "customerID" in result["data_stats"]["columns"]
        assert result["analysis_type"] == "overview"
        assert len(result["insights"]) == 2
        assert result["usage"]["total_tokens"] == 370

    @patch("function_app.get_openai_client")
    def test_summarize_csv_insights(self, mock_openai, sample_csv_text):
        """Test CSV insights analysis."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Business insights from telco data.",
            "insights": ["Focus retention on early-tenure customers"],
            "patterns": ["Price sensitivity in month-to-month"],
            "recommendations": ["Implement loyalty program"]
        })
        mock_response.usage.prompt_tokens = 230
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 330
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = function_app.summarize_csv_data(sample_csv_text, "insights")

        assert result["analysis_type"] == "insights"
        assert len(result["recommendations"]) > 0

    def test_summarize_csv_missing(self, mock_http_request):
        """Test summarize/csv endpoint returns 400 when csv_text is missing."""
        req = mock_http_request(body={"title": "Test"})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.summarize_csv_endpoint(req)
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
            "title": "Q1 Revenue Report",
            "summary": "Quarterly financial summary",
            "source": "uploads/report.pdf",
            "page_count": 5,
            "@search.score": 0.95,
            "@search.reranker_score": 0.88
        }.get(key, None)
        mock_result.get = lambda key, default=None: {
            "id": "doc-1",
            "title": "Q1 Revenue Report",
            "summary": "Quarterly financial summary",
            "source": "uploads/report.pdf",
            "page_count": 5,
            "@search.score": 0.95,
            "@search.reranker_score": 0.88
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_result]
        mock_search.return_value = mock_client

        results = function_app.search_documents("revenue report", top_k=5)

        assert len(results) == 1
        assert results[0]["title"] == "Q1 Revenue Report"
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
# Test Document Retrieval
# ==============================================================================

class TestDocumentRetrieval:
    """Tests for retrieving stored document summaries."""

    @patch("function_app.get_cosmos_container")
    def test_get_document_success(self, mock_cosmos):
        """Test retrieving a stored document summary from Cosmos DB."""
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            "id": "doc-123",
            "documentId": "doc-123",
            "title": "Test Document",
            "summary": "A test summary.",
            "key_points": ["Point 1"],
            "topics": ["testing"],
            "source": "upload",
            "created_at": "2024-01-15T10:00:00"
        }
        mock_cosmos.return_value = mock_container

        result = function_app.get_document_summary("doc-123")

        assert result["title"] == "Test Document"
        assert result["summary"] == "A test summary."
        assert len(result["key_points"]) == 1

    @patch("function_app.get_cosmos_container")
    def test_get_document_not_found(self, mock_cosmos):
        """Test 404 when document does not exist."""
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            status_code=404,
            message="Not found"
        )
        mock_cosmos.return_value = mock_container

        with pytest.raises(CosmosResourceNotFoundError):
            function_app.get_document_summary("nonexistent-id")


# ==============================================================================
# Test Configuration
# ==============================================================================

class TestConfig:
    """Tests for the Config class defaults and environment variable names."""

    def test_config_defaults(self):
        """Test that Config has correct default values."""
        assert function_app.Config.GPT_MODEL == "gpt-4o"
        assert function_app.Config.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert function_app.Config.SEARCH_INDEX == "documents-index"
        assert function_app.Config.DATABASE_NAME == "docsummarizer"
        assert function_app.Config.CACHE_TTL == 3600

    def test_config_env_vars(self):
        """Test that all environment variable config attributes are strings or None."""
        env_attrs = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT",
            "COSMOS_ENDPOINT",
            "DOCUMENT_INTELLIGENCE_ENDPOINT",
            "STORAGE_ACCOUNT_URL",
            "REDIS_HOST",
            "KEY_VAULT_URL"
        ]
        for attr in env_attrs:
            value = getattr(function_app.Config, attr)
            assert value is None or isinstance(value, str), (
                f"Config.{attr} should be str or None, got {type(value)}"
            )


# ==============================================================================
# Test Health Check
# ==============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, mock_http_request):
        """Test health endpoint returns status healthy with timestamp."""
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            function_app.health_check(req)
        )

        call_args = function_app.func.HttpResponse.call_args
        body = json.loads(call_args[0][0])
        assert body["status"] == "healthy"
        assert "timestamp" in body
        assert body["version"] == "1.0.0"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
