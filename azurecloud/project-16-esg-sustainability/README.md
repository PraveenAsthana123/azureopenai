# ESG & Sustainability Reporter

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![Synapse Analytics](https://img.shields.io/badge/Synapse%20Analytics-SQL%20Pools-blue)
![Document Intelligence](https://img.shields.io/badge/Document%20Intelligence-OCR-orange)
![Power BI](https://img.shields.io/badge/Power%20BI-Embedded-yellow)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-NoSQL-purple)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

An enterprise-grade ESG (Environmental, Social, and Governance) and Sustainability Reporting platform that automates the extraction of ESG data from corporate reports, performs carbon footprint analytics using the GHG Protocol (Scope 1/2/3), ensures regulatory compliance with CSRD and TCFD frameworks, and leverages Azure OpenAI GPT-4o for GenAI narrative generation. The system ingests sustainability reports, annual filings, and environmental datasets through Azure Document Intelligence, stores structured ESG metrics in Cosmos DB and ADLS Gen2 (Bronze/Silver/Gold Medallion architecture), runs analytics via Synapse Analytics, and produces compliance-ready reports with AI-generated narratives surfaced through Power BI Embedded dashboards.

## Architecture

```
Data Sources
  - Corporate Reports (PDF/CSV)
  - Public ESG APIs (CDP, GRI)
  - Azure Blob Drop Zone
        |
        v
  Data Factory (Orchestrator)
        |
        v
  Azure Functions (ESG Pipeline)
  +-----+-----+-----+
  |           |           |
  v           v           v
Doc Intel    ESG Metric   Carbon Footprint
(PDF/Table   Parser       Calculator
 Extract)    (GPT-4o)     (GHG Protocol)
        |
        v
  ADLS Gen2 (Bronze/Silver/Gold)
        |
        v
  Synapse Analytics (Aggregation)
        |
        v
  Azure Functions (ESG Orchestrator)
  - Data Extractor (Durable)
  - Compliance Engine (CSRD/TCFD)
  - Narrative Generator (GPT-4o)
  - Carbon Calculator
        |
  +-----+-----+-----+
  |           |           |
  v           v           v
Azure        Azure AI     Cosmos DB
OpenAI       Search       (ESG Metrics,
(GPT-4o)     (Regulation  Compliance,
              DB/Framework Audit Trail)
              Reference)
        |
        v
  Report Assembly (PDF/XBRL)
        |
        v
  User Interfaces
  - React ESG Dashboard
  - Power BI Embedded (KPIs)
  - API Consumers (CDP, MSCI)
```

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | ESG narrative generation, entity extraction, compliance assessment |
| Azure OpenAI (ada-002) | Regulatory document embeddings for retrieval |
| Azure Document Intelligence | PDF/table extraction from sustainability reports (prebuilt-layout + custom) |
| Azure AI Search (S1) | Regulatory reference search (CSRD, TCFD, GRI) with semantic ranker |
| Azure Functions (Python 3.11) | ESG orchestrator, data extractor, carbon calculator, narrative generator, compliance engine |
| Azure Cosmos DB | ESG metrics, compliance scores, audit trail (serverless) |
| ADLS Gen2 | Bronze/Silver/Gold lakehouse for ESG data (Hot/Cool tiers) |
| Azure Synapse Analytics | ESG aggregation, carbon analytics, trend analysis (DW200c) |
| Azure Data Factory | ETL/ELT pipelines for ESG data ingestion (Managed VNET IR) |
| Microsoft Purview | Data catalog, lineage tracking, ESG data classification |
| Power BI Embedded (A2) | Interactive sustainability dashboards and KPI visualization |
| Azure Blob Storage | Raw report uploads (PDF, CSV, XBRL) |
| Azure Key Vault | Secrets, certificates, encryption keys |
| Azure Front Door | Global load balancing, WAF, SSL termination |
| Azure APIM | API management with OAuth2/JWT auth (100 RPM) |

## Prerequisites

- Azure Subscription with Contributor access
- Azure OpenAI resource with GPT-4o and text-embedding-ada-002 deployed
- Azure Document Intelligence (S0 tier)
- Azure Synapse Analytics workspace with dedicated SQL pool (DW200c)
- ADLS Gen2 storage account with hierarchical namespace
- Microsoft Purview account
- Python 3.11+
- Azure Functions Core Tools v4
- Terraform >= 1.5
- Azure CLI >= 2.50

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-16-esg-sustainability

# Set required environment variables
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export AZURE_SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
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

### 4. Extract ESG Metrics

```bash
# Extract metrics from a sustainability report
curl -X POST http://localhost:7071/api/extract-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "In FY2025, Contoso reduced GHG emissions by 15%...",
    "framework": "CSRD"
  }'

# Calculate carbon footprint
curl -X POST http://localhost:7071/api/carbon-footprint \
  -H "Content-Type: application/json" \
  -d '{
    "activity_data": {
      "scope_1": {"natural_gas_m3": 50000, "diesel_litre": 12000},
      "scope_2": {"electricity_kwh": 2000000},
      "scope_3": {"air_travel_km": 500000, "road_freight_tonne_km": 1000000}
    }
  }'
```

## Testing

```bash
cd tests

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -v -k "test_extract"         # ESG metric extraction tests
pytest -v -k "test_carbon"          # Carbon footprint calculation tests
pytest -v -k "test_compliance"      # Regulatory compliance tests
pytest -v -k "test_narrative"       # Narrative generation tests
pytest -v -k "test_report"          # Full report generation tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID SSO with Conditional Access; MFA enforcement for ESG data submission and approval workflows
- **Authorization**: Role separation: data collectors, analysts, approvers with multi-level sign-off for public ESG disclosures
- **RBAC**: ESG-specific roles with PIM (Privileged Identity Management) for just-in-time access
- **Managed Identity**: System-assigned managed identity for zero-credential access to all services including OpenAI, Cosmos DB, ADLS, Synapse, Purview, and Key Vault
- **Network Isolation**: Dedicated VNet with Application, Data, and Integration subnets; all PaaS services on Private Link with no public endpoints

### Encryption

- **Data at Rest**: AES-256 SSE for ADLS Gen2, Cosmos DB, Blob Storage, and Synapse; Customer-Managed Keys (CMK) via Key Vault
- **Data in Transit**: TLS 1.3 enforced for all service-to-service and client communications
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection for ESG data encryption keys and API credentials

### Monitoring

- **Application Insights**: APM for all Azure Functions, Document Intelligence calls, and OpenAI invocations
- **Log Analytics**: Centralized logging (50GB/day) with retention for audit and compliance
- **Alerts**: Azure Monitor alerts for pipeline failures, ESG data quality threshold breaches, and compliance gap detection
- **Dashboards**: Operations dashboard for ESG pipeline throughput, extraction quality scores, compliance rates, and cost management

### Visualization

- **Power BI Embedded**: A2 SKU with interactive sustainability dashboards; carbon emissions trends, ESG pillar scores, compliance status heatmaps, and board-ready KPI reports
- **React ESG Dashboard**: Main reporting interface for metric visualization, report assembly status, and framework compliance tracking
- **API Consumers**: REST/GraphQL endpoints for third-party ESG rating integrations (CDP, MSCI)

### Tracking

- **Data Lineage**: Full traceability from source document to published report via Microsoft Purview
- **Audit Trail**: Immutable, tamper-proof logs for all ESG data submissions and modifications in Cosmos DB
- **Processing Events**: Pipeline steps (document extraction, metric extraction, compliance check, narrative generation, report assembly) tracked per document
- **Request Tracing**: Correlation IDs across Data Factory, Functions, OpenAI, and Cosmos DB for end-to-end observability

### Accuracy

- **Data Quality Scoring**: Each metric extraction includes a data_quality_score (0.0-1.0) based on completeness and clarity of source data
- **Framework Validation**: Multi-stage validation against CSRD (11 requirements) and TCFD (10 requirements) with per-requirement status
- **Carbon Calculation**: GHG Protocol Corporate Standard methodology with published emission factors per activity type
- **Supported Frameworks**: CSRD, TCFD, GRI, SASB, IFRS S1, IFRS S2
- **Third-Party Assurance**: External assurance capability for published ESG metrics

### Explainability

- ESG metric extraction returns structured results organized by Environmental, Social, and Governance pillars with extraction notes explaining data provenance
- Compliance assessments provide per-requirement status (compliant/partial/gap) with evidence citations and specific recommendations for achieving full compliance
- Carbon footprint calculations show per-activity quantity, emission factor, and resulting tCO2e for full transparency
- GenAI narratives are structured with executive summary, environmental performance, social impact, governance highlights, and forward-looking statements

### Responsibility

- **Greenwashing Prevention**: Claims validated against source data with audit trail; content filtering prevents generation of misleading ESG claims
- **Human-in-the-Loop**: Multi-level approval workflows required before any public ESG disclosure; AI-generated narratives are reviewed by sustainability team
- **Data Integrity**: Checksums and validation for all ESG metric submissions; immutable audit logs prevent tampering
- **Content Filtering**: Azure OpenAI content safety prevents generation of unsubstantiated sustainability claims
- **Balanced Reporting**: Narrative generation prompt explicitly requires factual tone, precise language, and citation of specific metrics

### Interpretability

- Compliance assessment clearly maps each regulatory requirement to available evidence and gap status
- Carbon footprint calculations broken down by Scope 1 (direct), Scope 2 (indirect energy), and Scope 3 (value chain) with per-category detail
- ESG metrics organized by E/S/G pillars with standardized field names aligned to framework definitions
- Report assembly combines metrics, carbon footprint, compliance, and narrative sections into a cohesive, auditable document

### Portability

- **Containerization**: Azure Functions packaged as Docker containers; React dashboard deployable as Static Web App
- **Infrastructure as Code**: Full Terraform configuration in `infra/main.tf` with multi-environment support (dev: serverless Synapse, staging: DW100c, prod: DW200c with GRS)
- **Multi-Cloud Considerations**: Carbon calculation engine uses standard emission factors independent of Azure; core ESG logic adaptable to other cloud providers
- **Report Formats**: Output supports PDF and XBRL for cross-platform regulatory submission
- **CI/CD**: Blue-green deployment with pipeline validation gates for ESG data quality, compliance framework check, and carbon calculation regression testing

## Project Structure

```
project-16-esg-sustainability/
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
| POST | `/api/extract-metrics` | Extract ESG metrics from document text using specified framework |
| POST | `/api/carbon-footprint` | Calculate Scope 1/2/3 GHG emissions from activity data |
| POST | `/api/compliance-check` | Check ESG metrics against CSRD/TCFD regulatory requirements |
| POST | `/api/generate-report` | Generate full sustainability report (metrics + carbon + compliance + narrative) |
| GET | `/api/health` | Health check with supported frameworks list |
| Event | `ESGDocumentUploadTrigger` | Event Grid trigger for ESG document upload processing pipeline |

## License

This project is licensed under the MIT License.
