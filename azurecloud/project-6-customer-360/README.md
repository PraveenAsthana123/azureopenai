# Project 6: Customer 360 / Document Summarization Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=flat&logo=openai&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-Python_3.11-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Cosmos DB](https://img.shields.io/badge/Cosmos_DB-Serverless-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

A unified customer data platform that consolidates multi-source data into comprehensive customer profiles, enabling AI-powered document summarization, CSV data analysis, and intelligent document search. The platform leverages Azure Document Intelligence for text extraction from PDF/DOCX/image files, Azure OpenAI GPT-4o for summarization and insight generation, and Azure AI Search for hybrid vector + keyword retrieval across indexed document summaries. It also supports real-time personalization, churn prediction, and customer lifetime value analysis through integrated ML models.

---

## Architecture

```
Data Sources (CRM, E-Commerce, Support, Marketing)
        |
   Azure Data Factory (Batch ETL + CDC)
        |
   +----+----+----+
   |    |    |    |
  ADLS  Event Cosmos DB
  Gen2  Hub   (Profiles)
        |
  Identity Resolution Engine
  (Deterministic + Probabilistic Matching)
        |
  Unified Customer Profile
  (Demographics, Transactions, ML Scores, Consent)
        |
  +-----+------+
  |            |
Azure ML    Azure OpenAI (GPT-4o)
(Churn,     (Personalized Content,
 CLV,        Document Summarization)
 Reco)       |
             |
  Azure AI Search (Hybrid Vector + Keyword)
        |
  Azure Functions API Layer
        |
  Activation & Delivery
  (Real-time API, Email, Web/Mobile, CRM Sync)
        |
  Power BI Dashboards
```

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Document summarization, CSV analysis, personalized content |
| Azure Document Intelligence | Text extraction from PDF, DOCX, TIFF, images |
| Azure AI Search | Hybrid vector + semantic search over document summaries |
| Azure Cosmos DB | Customer profiles, document summary storage |
| Azure Cache for Redis | Response caching (1-hour TTL) |
| Azure Blob Storage | Document storage, CSV uploads |
| Azure Event Grid | Trigger auto-summarization on document upload |
| Azure Data Factory | Batch ETL, CDC pipelines for customer data |
| ADLS Gen2 | Raw data lake |
| Azure ML | Churn prediction, CLV, recommendation models |
| Azure Key Vault | Secrets, encryption keys, connection strings |
| Power BI | Customer 360 dashboards, segment analysis |

---

## Prerequisites

- **Azure Subscription** with the following resources provisioned:
  - Azure OpenAI Service (GPT-4o and text-embedding-ada-002 deployments)
  - Azure Document Intelligence
  - Azure AI Search (S1 or higher with semantic ranker enabled)
  - Azure Cosmos DB (serverless, SQL API)
  - Azure Cache for Redis (P1 Premium, SSL enabled)
  - Azure Blob Storage
  - Azure Key Vault
- **Python 3.11+**
- **Azure Functions Core Tools v4**
- **Azure CLI** (authenticated)

---

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-6-customer-360

# Copy environment template and fill in values
cp .env.example .env
# Set: AZURE_OPENAI_ENDPOINT, AZURE_SEARCH_ENDPOINT, COSMOS_ENDPOINT,
#      DOCUMENT_INTELLIGENCE_ENDPOINT, STORAGE_ACCOUNT_URL,
#      REDIS_HOST, KEY_VAULT_URL
```

### 2. Install dependencies

```bash
cd src
pip install -r requirements.txt
```

### 3. Run locally

```bash
func start
```

### 4. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -var-file="env/dev.tfvars"
terraform apply -var-file="env/dev.tfvars"
```

### 5. Deploy function app

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

---

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run comprehensive integration tests
python -m pytest test_comprehensive.py -v

# Run all tests with coverage
python -m pytest --cov=src --cov-report=html -v
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure AD / Entra ID OAuth2/OIDC for user access; function-level auth keys for API endpoints
- **Authorization**: Consent-based data access gated by customer consent records; RBAC for internal operations
- **RBAC**: Fine-grained role assignments for data analysts, marketers, and administrators
- **Managed Identity**: System-assigned managed identity for all service-to-service calls (OpenAI, Cosmos DB, Search, Storage, Redis)
- **Network Isolation**: All data services accessed via Private Link endpoints within a dedicated VNet; NSG rules enforce least-privilege network access

### Encryption

- **Data at Rest**: AES-256 server-side encryption (SSE) for Blob Storage and Cosmos DB; field-level encryption for PII fields (name, email, phone)
- **Customer-Managed Keys (CMK)**: Key Vault stores CMKs for all data stores; key rotation policies enforced
- **Data in Transit**: TLS 1.2+ enforced on all service endpoints; Redis SSL on port 6380
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection for all secrets and encryption keys

### Monitoring

- **Application Insights**: APM for Azure Functions with custom telemetry tracking token usage, latency, and error rates
- **Log Analytics**: Centralized log workspace aggregating function logs, Cosmos DB diagnostics, and search query metrics
- **Alerts**: Configured for high error rates, latency spikes, cache miss ratios, and budget thresholds
- **Dashboards**: Azure Monitor dashboards for real-time operational health; cost management dashboard for token spend

### Visualization

- **Power BI**: Embedded dashboards for Customer 360 View, Segment Analysis, and Campaign Performance
- **API Endpoints**: `/health` endpoint for operational status; search results returned with relevance scores and reranker scores

### Tracking

- **Request Tracing**: Application Insights distributed tracing with correlation IDs across Document Intelligence, OpenAI, and Search calls
- **Correlation IDs**: Each summarization request generates a unique `document_id` (UUID) tracked through extraction, summarization, storage, and indexing
- **Audit Logs**: All profile access logged with purpose; Event Grid triggers logged with blob URL and processing status

### Accuracy

- **Model Evaluation**: GPT-4o summarization quality measured via ROUGE scores against human-generated summaries
- **Confidence Thresholds**: Search results include `@search.score` and `@search.reranker_score` for relevance ranking
- **Validation**: JSON schema validation on all GPT-4o responses via `response_format: json_object`; CSV parsing validates column structure before analysis
- **Caching**: MD5-based cache keys prevent redundant processing; cache TTL of 3600 seconds ensures freshness

### Explainability

- **Summary Metadata**: Each summary includes `key_points`, `topics`, and `word_count` to help users understand what the AI extracted
- **Analysis Types**: Users can select `executive`, `detailed`, or `bullet` summary types to control output granularity
- **CSV Insights**: AI-generated `insights`, `patterns`, and `recommendations` provide transparent reasoning for data analysis conclusions
- **Token Usage**: Every response includes `usage` metrics (prompt/completion/total tokens) for cost transparency

### Responsibility

- **Content Filtering**: Azure OpenAI content safety filters enabled for all GPT-4o calls
- **Bias Detection**: Identity resolution matching rules audited for accuracy and bias in customer profile merging
- **Consent Management**: Centralized consent preferences tracked and enforced; personalization opt-out available
- **GDPR/CCPA**: Automated right-to-erasure pipeline; do-not-sell flag enforcement; data subject access requests supported
- **Temperature Controls**: Conservative temperature settings (0.3-0.4) to reduce hallucination in summaries

### Interpretability

- **Feature Importance**: CSV analysis surfaces column-level patterns and correlations that drive insights
- **Decision Transparency**: Summary `topics` and `key_points` fields show what the model identified as important
- **Search Scoring**: Hybrid search returns both vector similarity scores and semantic reranker scores for result transparency

### Portability

- **Infrastructure as Code**: Terraform modules in `infra/` for full environment provisioning
- **Containerization**: Azure Functions run on managed infrastructure; can be containerized for AKS deployment
- **Multi-Cloud Considerations**: Core logic uses standard Python libraries; OpenAI client can be swapped for direct OpenAI API
- **Environment Configuration**: All service endpoints and credentials externalized via environment variables

---

## Project Structure

```
project-6-customer-360/
|-- data/
|   +-- WA_Fn-UseC_-Telco-Customer-Churn.csv
|-- docs/
|   +-- ARCHITECTURE.md
|-- infra/
|   +-- main.tf
|-- src/
|   +-- function_app.py
|-- tests/
|   |-- test_function_app.py
|   +-- test_comprehensive.py
+-- README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/summarize` | Summarize a document from Blob Storage URL (PDF/DOCX/image) |
| POST | `/api/summarize/text` | Summarize raw text directly (no Document Intelligence) |
| POST | `/api/summarize/csv` | Analyze and summarize CSV data with AI insights |
| GET | `/api/documents/{document_id}` | Retrieve a stored document summary by ID |
| POST | `/api/search` | Hybrid vector + semantic search over indexed summaries |
| GET | `/api/health` | Health check endpoint |
| -- | `DocumentUploadTrigger` | Event Grid trigger: auto-summarize on blob upload |

---

## License

This project is licensed under the MIT License.
