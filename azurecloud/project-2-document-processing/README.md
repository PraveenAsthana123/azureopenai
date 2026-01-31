# Intelligent Document Processing & Classification Pipeline

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-00A4EF?style=flat&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise document processing platform that automatically extracts, classifies, validates, and routes documents using Azure Document Intelligence and Azure OpenAI GPT-4o. The pipeline handles invoices, contracts, forms, compliance documents, and HR records with confidence-based routing -- high-confidence results are auto-processed, medium-confidence items are queued for human review, and low-confidence documents require manual intervention. The system supports multi-format ingestion (PDF, DOCX, TIFF, images) through Event Grid-triggered Durable Functions.

## Architecture

```
Document Sources (Email / SharePoint / SFTP / API Upload)
        |
   Azure Blob Storage (Landing Zone)
        |
   Event Grid (Blob Created)
        |
   Durable Functions Orchestrator
        |
   +----+----+----+----+
   |         |         |         |
Extract   Classify  Validate  Summarize
(Doc       (GPT-4o)  (Business  (GPT-4o)
 Intel.)              Rules)
        |
   Confidence Router
   |         |          |
 >=0.85    0.60-0.85   <0.60
 Auto-     Human       Manual
 Process   Review      Review
        |
   Cosmos DB (Metadata) + AI Search (Index) + Audit Logs
```

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o, text-embedding-ada-002 | Document classification, summarization, embeddings |
| Azure Document Intelligence | prebuilt-layout, prebuilt-invoice | OCR, layout analysis, key-value extraction |
| Azure AI Search | S1 | Hybrid search over processed documents |
| Azure Cosmos DB | Serverless | Document metadata, extraction results, review queue, audit logs |
| Azure Blob Storage | Hot tier | Document landing zone and processed storage |
| Azure Cache for Redis | Premium | Extraction result caching (1-hour TTL) |
| Azure Event Grid | Standard | Blob upload event triggers |
| Azure Key Vault | Standard | Secrets and connection strings |
| Azure Functions | Premium EP1 (Python 3.11) | Processing orchestration and API endpoints |
| Application Insights | Pay-as-you-go | Pipeline telemetry and monitoring |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50
- Terraform >= 1.5
- Python 3.11+
- Azure OpenAI resource with GPT-4o deployment
- Azure Document Intelligence resource

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-2-document-processing

# Copy environment template
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### 2. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Install dependencies and run locally

```bash
cd ../src
pip install -r requirements.txt

func start
```

### 4. Process a document

```bash
# Extract text and structure from a document
curl -X POST http://localhost:7071/api/extract \
  -H "Content-Type: application/json" \
  -d '{"blob_url": "https://yourstorage.blob.core.windows.net/incoming/invoice.pdf"}'

# Classify the extracted text
curl -X POST http://localhost:7071/api/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Invoice #12345...", "document_id": "doc-001"}'
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run comprehensive integration tests
python -m pytest test_comprehensive.py -v

# Run all tests with coverage
python -m pytest --cov=src --cov-report=term-missing
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID for user and service authentication; function-level auth keys for API access
- **Authorization**: Per-resource RBAC role assignments; document-level access control in Cosmos DB
- **Managed Identity**: System-assigned managed identity for all inter-service communication -- no stored credentials
- **Network Isolation**: Dedicated VNet with NSG rules; Document Intelligence, Storage, and Cosmos DB accessed via Private Link endpoints; no public endpoints
- **Content Validation**: Document format validation and malware scanning on upload before processing

### Encryption

- **Data at Rest**: AES-256 encryption for all stored documents and metadata across Blob Storage, Cosmos DB, and ADLS Gen2
- **Data in Transit**: TLS 1.2+ enforced on all connections between services
- **Key Management**: Azure Key Vault stores OCR keys, storage keys, and connection strings with RBAC access control

### Monitoring

- **Application Insights**: End-to-end pipeline telemetry tracking extraction, classification, and validation latency
- **Log Analytics**: Full processing audit trail with per-document step-by-step logging and timestamps
- **Alerts**: Alerts on processing failures, classification confidence drops, and queue depth for human review
- **Dashboards**: Azure Monitor workbooks for pipeline throughput, classification accuracy, and review backlog

### Visualization

- **Power BI**: Dashboards for processing metrics, classification accuracy trends, and review statistics connected to Azure SQL reporting layer
- **Power Apps**: Human review interface for medium-confidence document corrections and approval workflows

### Tracking

- **Request Tracing**: Correlation IDs assigned per document at ingestion, propagated through every pipeline stage
- **Data Lineage**: Full lineage tracked from upload through extraction, classification, validation, and routing
- **Audit Logs**: Immutable audit records in Cosmos DB for every document processing action with timestamps and user attribution

### Accuracy

- **Classification Confidence**: GPT-4o classification returns confidence scores (0.0-1.0) with reasoning
- **Confidence Thresholds**: High (>=0.85) auto-process, Medium (0.60-0.85) human review, Low (<0.60) manual review
- **Validation Rules**: Category-specific field validation (required fields, value ranges, cross-field consistency)
- **Feedback Loop**: Human review corrections feed back into model improvement pipeline

### Explainability

- **Classification Reasoning**: GPT-4o provides natural language reasoning for every classification decision
- **Validation Reports**: Detailed error lists showing which required fields are missing or invalid
- **Routing Transparency**: Each document record includes classification category, confidence, and routing decision

### Responsibility

- **PII Redaction**: Automated PII detection and redaction before downstream processing and indexing
- **Human-in-the-Loop**: Confidence-based routing ensures low-confidence extractions are reviewed by humans before action
- **Data Loss Prevention**: DLP policies prevent sensitive data leakage through the processing pipeline

### Interpretability

- **Field-Level Confidence**: Document Intelligence returns per-field confidence scores for extracted key-value pairs
- **Category-Specific Rules**: Transparent validation rules defined per document category (invoice, contract, form, compliance, HR)
- **Processing Trace**: Every document includes a complete processing record: extraction model used, classification result, validation outcome

### Portability

- **Infrastructure as Code**: Terraform modules for all Azure resources with environment-specific variables
- **Containerization**: Azure Functions compatible with container deployment for hybrid scenarios
- **Format Agnostic**: Pipeline supports PDF, DOCX, TIFF, PNG, and JPEG inputs through Document Intelligence
- **Modular Design**: Each processing stage (extract, classify, validate, summarize) is an independent function endpoint

## Project Structure

```
project-2-document-processing/
|-- data/
|   +-- customer_shopping_data.csv   # Sample dataset for testing
|-- docs/
|   +-- ARCHITECTURE.md             # Detailed architecture documentation
|-- infra/
|   +-- main.tf                     # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py             # Azure Functions: extract, classify, validate, summarize, search
|-- tests/
|   |-- test_function_app.py        # Unit tests for all endpoints
|   +-- test_comprehensive.py       # Integration and pipeline tests
+-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/extract` | Extract text, tables, and key-value pairs from a document |
| `POST` | `/api/classify` | Classify extracted text into a document category |
| `POST` | `/api/validate` | Validate extracted fields against business rules |
| `POST` | `/api/summarize` | Generate an executive summary of document content |
| `POST` | `/api/search` | Hybrid search across indexed processed documents |
| `GET` | `/api/documents/{document_id}` | Retrieve a document record by ID |
| `GET` | `/api/health` | Health check -- returns service status and version |
| Event Grid | `DocumentUploadTrigger` | Auto-triggered on blob upload; runs full extract-classify-validate pipeline |

### POST /api/extract

**Request:**
```json
{
  "blob_url": "https://storage.blob.core.windows.net/incoming/invoice.pdf",
  "model_id": "prebuilt-layout"
}
```

**Response:**
```json
{
  "id": "doc-uuid",
  "text": "extracted text...",
  "page_count": 3,
  "tables": [],
  "key_value_pairs": [{"key": "Invoice #", "value": "12345", "confidence": 0.97}],
  "model_id": "prebuilt-layout",
  "extracted_at": "2024-01-15T10:30:00Z"
}
```

### POST /api/classify

**Request:**
```json
{
  "text": "Invoice #12345 from Vendor Corp...",
  "document_id": "doc-001"
}
```

**Response:**
```json
{
  "id": "doc-001",
  "category": "invoice",
  "confidence": 0.92,
  "reasoning": "Document contains invoice number, vendor details, and line items",
  "routing": "auto_process",
  "classified_at": "2024-01-15T10:30:05Z"
}
```

## License

This project is licensed under the MIT License.
