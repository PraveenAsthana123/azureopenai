# Demo Plan
## Enterprise GenAI Knowledge Copilot Platform

**Version:** 1.0
**Date:** November 2025

---

## 1. Demo Scenarios

### 1.1 Available Demos

| Scenario | Duration | Services Used |
|----------|----------|---------------|
| Invoice Processing | 20 min | Doc Intel, Cosmos, Search |
| Document Search Portal | 15 min | Doc Intel, Search, Storage |
| Image Analysis | 15 min | Computer Vision, Cosmos |
| Voice Transcription | 15 min | Speech, Search, Cosmos |

---

## 2. Demo Script: Invoice Processing

```python
from azure.ai.formrecognizer import DocumentAnalysisClient

# Process invoice
doc_client = DocumentAnalysisClient(
    endpoint="https://di-genai-copilot-dev-rwc3az.cognitiveservices.azure.com/",
    credential=AzureKeyCredential(key)
)

poller = doc_client.begin_analyze_document("prebuilt-invoice", invoice_bytes)
result = poller.result()

# Extract fields
invoice = result.documents[0]
print(f"Vendor: {invoice.fields.get('VendorName').value}")
print(f"Total: {invoice.fields.get('InvoiceTotal').value}")
print(f"Date: {invoice.fields.get('InvoiceDate').value}")
```

---

## 3. Demo Script: Image Analysis

```python
from azure.cognitiveservices.vision.computervision import ComputerVisionClient

cv_client = ComputerVisionClient(
    endpoint="https://cv-genai-copilot-dev-rwc3az.cognitiveservices.azure.com/",
    credentials=CognitiveServicesCredentials(key)
)

analysis = cv_client.analyze_image(
    image_url,
    visual_features=["Tags", "Description", "Objects"]
)

print(f"Description: {analysis.description.captions[0].text}")
print(f"Tags: {[tag.name for tag in analysis.tags]}")
```

---

## 4. Demo Script: Speech Transcription

```python
import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(
    subscription=speech_key,
    region="japaneast"
)

audio_config = speechsdk.AudioConfig(filename="meeting.wav")
recognizer = speechsdk.SpeechRecognizer(speech_config, audio_config)
result = recognizer.recognize_once()
print(f"Transcript: {result.text}")
```

---

## 5. Demo Script: AI Search

```python
from azure.search.documents import SearchClient

search_client = SearchClient(
    endpoint="https://search-genai-copilot-dev-rwc3az.search.windows.net",
    index_name="documents",
    credential=AzureKeyCredential(key)
)

results = search_client.search(
    search_text="quarterly financial report",
    top=10
)

for result in results:
    print(f"{result['title']}: {result['@search.score']}")
```

---

## 6. Demo Environment Setup

```bash
# Get API keys
export DOC_INTEL_KEY=$(az cognitiveservices account keys list \
    --name di-genai-copilot-dev-rwc3az \
    --resource-group rg-genai-copilot-dev-jpe \
    --query key1 -o tsv)

export CV_KEY=$(az cognitiveservices account keys list \
    --name cv-genai-copilot-dev-rwc3az \
    --resource-group rg-genai-copilot-dev-jpe \
    --query key1 -o tsv)

export SPEECH_KEY=$(az cognitiveservices account keys list \
    --name speech-genai-copilot-dev-rwc3az \
    --resource-group rg-genai-copilot-dev-jpe \
    --query key1 -o tsv)

export SEARCH_KEY=$(az search admin-key show \
    --service-name search-genai-copilot-dev-rwc3az \
    --resource-group rg-genai-copilot-dev-jpe \
    --query primaryKey -o tsv)
```
