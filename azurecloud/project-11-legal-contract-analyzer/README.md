# Legal Contract Analyzer

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![Document Intelligence](https://img.shields.io/badge/Document%20Intelligence-OCR-blue)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-NoSQL-purple)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

An AI-powered contract analysis platform that extracts key clauses, identifies risks, compares contract versions, and provides intelligent summaries using Azure Document Intelligence and Azure OpenAI GPT-4o. The system processes the CUAD v1 dataset (510 contracts, 41 clause types) and supports automated clause identification, risk scoring (1-10 severity), obligation tracking, and semantic contract search via Azure AI Search. Contracts are ingested from email attachments, SharePoint, API uploads, or CLM systems and processed through a Durable Functions pipeline.

## Architecture

```
Contract Sources (Email / SharePoint / API / CLM)
        |
        v
  Azure Blob Storage (/contracts/inbox/)
        |
        v
  Event Grid Trigger
        |
        v
  Durable Functions Orchestrator
        |
  +-----+-----+-----+
  |           |           |
  v           v           v
Extraction   Classification   Clause Analysis
(Doc Intel)  (Contract Type)  (CUAD 41 Types)
        |
        v
  Azure OpenAI GPT-4o
  - Clause Extraction
  - Risk Assessment (1-10)
  - Summary Generation
        |
        v
  Advanced Analysis
  - Version Compare (Semantic Diff)
  - Playbook Check (Compliance %)
  - Semantic Search (AI Search)
        |
        v
  Data Storage
  - Cosmos DB (contracts, clauses, risks)
  - AI Search (vector + full-text index)
  - Blob Storage (originals, processed, versions)
        |
        v
  User Interfaces
  - React Web Portal
  - APIM REST API
  - Power BI Dashboard
```

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Clause analysis, risk assessment, summary generation, obligation tracking |
| Azure Document Intelligence | OCR and layout extraction from contract PDFs |
| Azure AI Search | Hybrid vector + keyword search on contract index |
| Azure Functions (Python 3.11) | Contract processing pipeline (Durable Functions) |
| Azure Cosmos DB | Contract metadata, clauses, risks, templates, obligations |
| Azure Blob Storage | Original and processed document storage |
| Azure Event Grid | Blob upload event routing to processing pipeline |
| Azure Key Vault | Document encryption keys, signing certificates |
| Azure API Management | API gateway with rate limiting and auth |
| Power BI | Contract portfolio, risk distribution, expiry calendar |

## Prerequisites

- Azure Subscription with Contributor access
- Azure OpenAI resource with GPT-4o and text-embedding-ada-002 deployed
- Azure Document Intelligence (S0 tier)
- Azure AI Search (S1 tier)
- Azure Cosmos DB (Serverless)
- Python 3.11+
- Azure Functions Core Tools v4
- Terraform >= 1.5 (for infrastructure provisioning)
- Azure CLI >= 2.50

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-11-legal-contract-analyzer

# Copy environment template
cp .env.example .env

# Set required environment variables
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export AZURE_SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-doc-intel>.cognitiveservices.azure.com/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
export STORAGE_ACCOUNT_URL="https://<your-storage>.blob.core.windows.net"
```

### 2. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Install Dependencies and Run Locally

```bash
cd ../src
pip install -r requirements.txt
func start
```

### 4. Upload a Contract for Analysis

```bash
# Full analysis pipeline
curl -X POST http://localhost:7071/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"blob_url": "https://<storage>.blob.core.windows.net/contracts/inbox/sample.pdf"}'
```

## Testing

```bash
cd tests

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -v -k "test_extract"        # Document extraction tests
pytest -v -k "test_clauses"        # Clause identification tests
pytest -v -k "test_risk"           # Risk assessment tests
pytest -v -k "test_compare"        # Template comparison tests
pytest -v -k "test_obligations"    # Obligation tracking tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID OAuth2/OIDC for user authentication; Function-level auth keys for API endpoints
- **Authorization**: Matter-based RBAC scoped to specific legal matters and teams; Ethical walls enforced for conflict screening
- **RBAC**: HR Admin, Legal Team, External Counsel roles with tiered access to contracts
- **Managed Identity**: System-assigned managed identity for zero-secret access to OpenAI, AI Search, Cosmos DB, Blob Storage, and Key Vault
- **Network Isolation**: Dedicated VNet with NSG rules; all services accessed via Private Link with no public endpoints

### Encryption

- **Data at Rest**: AES-256 SSE for Blob Storage and Cosmos DB; Customer-Managed Keys (CMK) available via Key Vault for sensitive documents
- **Data in Transit**: TLS 1.3 enforced for all service-to-service and client communications
- **Key Management**: Azure Key Vault with soft delete and purge protection for document encryption keys and signing certificates

### Monitoring

- **Application Insights**: APM tracing for all Function executions, Document Intelligence calls, and OpenAI invocations
- **Log Analytics**: Centralized logging with 365-day retention for compliance; legal hold tracking events
- **Alerts**: Azure Monitor alerts for pipeline failures, risk threshold breaches, and SLA violations
- **Dashboards**: Azure Monitor dashboards for contract processing throughput, latency percentiles, and error rates

### Visualization

- **Power BI Dashboard**: Contract portfolio overview, risk distribution heatmap, expiry calendar, and compliance metrics
- **React Web Portal**: Interactive contract analysis viewer, search interface, and export reports
- **API (APIM)**: RESTful endpoints for programmatic integration with CLM systems

### Tracking

- **Request Tracing**: End-to-end correlation IDs across Event Grid, Functions, OpenAI, and Cosmos DB operations
- **Audit Logs**: Complete chain of custody for all legal documents; privilege access logging
- **Legal Hold Tracking**: Preservation obligations tracked and enforced automatically

### Accuracy

- **Model Evaluation**: CUAD v1 dataset (510 contracts, 41 clause types) used for clause identification benchmarking
- **Confidence Thresholds**: Clause identification returns confidence scores (0.0-1.0); classification confidence target of 95%
- **Validation**: Template comparison produces compliance percentage; deviations flagged with severity levels
- **Risk Scoring**: Standardized 1-10 severity scale with defined criteria per risk type (unlimited liability, auto-renewal, IP assignment)

### Explainability

- Each clause extraction includes the exact text, clause type, confidence score, and position in the document
- Risk assessments provide severity, description, and actionable recommendation for every identified risk
- Executive summaries include key highlights and action items derived from the analysis
- Template comparison outputs deviation details with contract text vs. template text side-by-side

### Responsibility

- **Content Filtering**: Azure OpenAI content safety enabled for all prompts and responses
- **Data Residency**: All contract data stays within the Azure tenant; no training on customer data
- **Human-in-the-Loop**: AI analysis presented as advisory; legal professionals make final decisions
- **Attorney-Client Privilege**: Privileged documents tagged, access-controlled, and logged via automated privilege tracking

### Interpretability

- Clause identification maps to the 41 standardized CUAD clause categories for consistent taxonomy
- Risk assessment explains each risk type with criteria, severity rating, and mitigation recommendations
- Template comparison shows compliance percentage with per-clause deviation breakdowns
- Obligation tracking attributes each obligation to its source clause with deadline and responsible party

### Portability

- **Containerization**: Azure Functions packaged as Docker containers for consistent deployment
- **Infrastructure as Code**: Full Terraform configuration in `infra/main.tf` for reproducible deployments
- **Multi-Cloud Considerations**: Core logic abstracted from Azure SDK; Document Intelligence and OpenAI calls can be swapped for alternative providers
- **CI/CD**: Azure DevOps pipelines with lint, test, deploy-infra, deploy-functions stages

## Project Structure

```
project-11-legal-contract-analyzer/
|-- data/
|   |-- CUAD_v1/
|       |-- CUAD_v1.json
|       |-- CUAD_v1_README.txt
|       |-- full_contract_pdf/
|       |   |-- Part_I/
|       |   |-- Part_II/
|       |   |-- Part_III/
|       |-- full_contract_txt/
|       |-- label_group_xlsx/
|       |-- master_clauses.csv
|-- docs/
|   |-- ARCHITECTURE.md
|-- infra/
|   |-- main.tf
|-- src/
|   |-- function_app.py
|-- tests/
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Full contract analysis: extract + clauses + risk + summary |
| POST | `/api/clauses` | Identify CUAD clause types in contract text |
| POST | `/api/risk` | Risk assessment for provided clauses |
| POST | `/api/compare` | Compare contract clauses against a template |
| POST | `/api/obligations` | Track obligations for a contract |
| POST | `/api/search` | Hybrid search (vector + keyword) on contracts index |
| GET | `/api/health` | Health check endpoint |
| Event | `ContractUploadTrigger` | Event Grid trigger for blob uploads to /contracts/inbox/ |

## License

This project is licensed under the MIT License.
