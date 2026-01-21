# Testing Plan
## Enterprise GenAI Knowledge Copilot Platform

**Version:** 1.0
**Date:** November 2025

---

## 1. Testing Strategy

| Category | Purpose | Coverage |
|----------|---------|----------|
| Infrastructure | Terraform validation | 100% |
| Unit Tests | Function testing | 80% |
| API Tests | Endpoint validation | 100% |
| Integration | Service interactions | 90% |
| Performance | Load testing | Critical paths |
| Security | Vulnerability testing | All endpoints |

---

## 2. Infrastructure Tests

```bash
#!/bin/bash
# infrastructure-test.sh

RG="rg-genai-copilot-dev-jpe"

# Test Resource Group
echo -n "Testing Resource Group... "
RG_STATE=$(az group show --name $RG --query "properties.provisioningState" -o tsv)
[ "$RG_STATE" == "Succeeded" ] && echo "PASS" || echo "FAIL"

# Test AI Services
for service in di-genai-copilot-dev-rwc3az cv-genai-copilot-dev-rwc3az speech-genai-copilot-dev-rwc3az; do
    echo -n "Testing $service... "
    STATE=$(az cognitiveservices account show --name $service --resource-group $RG \
        --query "properties.provisioningState" -o tsv)
    [ "$STATE" == "Succeeded" ] && echo "PASS" || echo "FAIL"
done

# Test AI Search
echo -n "Testing AI Search... "
SEARCH_STATE=$(az search service show --name search-genai-copilot-dev-rwc3az \
    --resource-group $RG --query "status" -o tsv)
[ "$SEARCH_STATE" == "running" ] && echo "PASS" || echo "FAIL"
```

---

## 3. API Tests

```python
# api_tests.py
import pytest
from azure.ai.formrecognizer import DocumentAnalysisClient

class TestDocumentIntelligence:
    def test_api_health(self, client):
        assert client is not None

    def test_analyze_document(self, client):
        with open("sample.pdf", "rb") as f:
            result = client.begin_analyze_document("prebuilt-layout", f).result()
        assert result is not None
        assert len(result.pages) > 0
```

---

## 4. Integration Tests

```python
# integration_tests.py
@pytest.mark.integration
def test_document_to_search_pipeline(doc_client, search_client):
    # Process document
    result = doc_client.begin_analyze_document("prebuilt-invoice", doc).result()

    # Index in search
    search_client.upload_documents([{
        "id": "test-doc",
        "content": result.content
    }])

    # Verify searchable
    results = list(search_client.search("test"))
    assert len(results) > 0
```

---

## 5. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific category
pytest -m unit
pytest -m integration
```
