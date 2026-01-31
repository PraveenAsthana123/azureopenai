# Project 21: Banking CRM Solution

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat)
![PCI DSS](https://img.shields.io/badge/PCI%20DSS-Compliant-red?style=flat)
![Basel III/IV](https://img.shields.io/badge/Basel-III%2FIV-green?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-yellow?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An AI-powered Banking CRM platform designed for enterprise financial institutions to deliver unified customer relationship management across all banking product lines. The system provides a Customer 360 view spanning deposits, loans, credit cards, and investment portfolios, enabling relationship managers with AI-driven next-best-action recommendations, churn prediction models, and a GenAI-powered copilot. The platform automates KYC/AML compliance workflows, performs real-time customer sentiment analysis, generates cross-sell/upsell propensity scores, and produces regulatory reports compliant with Basel III/IV frameworks. Built on Azure with strict PCI DSS and SOX compliance.

## Architecture

```
RM Portal / Customer Self-Service / Branch Kiosk
                    |
             Azure Front Door (WAF + PCI Headers)
                    |
        +-----------+-----------+
        |           |           |
   APIM Gateway  Entra ID    SignalR
   (mTLS, JWT)  (OAuth2/MFA) (Real-time)
        |
   Azure Functions (CRM Orchestrator)
        |
   +----+----+----+----+----+
   |    |    |    |    |    |
  C360  NBA  KYC  Churn CrossSell  <-- Azure OpenAI (GPT-4o) + Azure ML
   |    |    |    |    |    |
   +----+----+----+----+----+
        |
   +----+----+----+----+----+
   |    |    |    |    |    |
Cosmos Redis ADLS Synapse Blob   <-- Data Layer
  DB  Cache  Gen2 Analytics Storage
        |
   Event Hub + Stream Analytics  <-- Real-time Event Processing
        |
   Power BI (Basel III/IV Reports) + External Integrations (Core Banking)
```

**Key Components:**
- **RM Portal** (React + Next.js) -- Relationship manager workspace with Customer 360, pipeline management, and AI copilot
- **Customer Self-Service** (Angular SPA) -- Account overview, support chat, document upload
- **Branch Kiosk** (Embedded React) -- Queue management, quick services, ID verification
- **Azure Functions** (Python 3.11 / .NET 8) -- CRM orchestrator, KYC workflow, compliance API, campaign management

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | RM Copilot, sentiment analysis, meeting summaries, NBA recommendations |
| Azure OpenAI (text-embedding-ada-002) | Vector embeddings for customer knowledge base |
| Azure ML (XGBoost, LightGBM, PyTorch) | Churn prediction, propensity scoring, risk assessment, CLV prediction |
| Azure AI Search | Customer knowledge base search, product documentation retrieval |
| Azure Cosmos DB (Strong consistency) | Customer profiles, interactions, KYC records, relationship history |
| Azure Redis Cache (P3 Clustered) | Session management, Customer 360 cache, NBA result cache, feature store |
| Azure Data Lake Storage Gen2 | Data lake with raw, curated, and analytics zones |
| Azure Synapse Analytics (DW200c) | Basel III/IV regulatory reporting, historical analysis |
| Azure Blob Storage | KYC documents, compliance reports, customer correspondence |
| Azure Event Hub | Real-time customer event streaming (transactions, logins, interactions) |
| Azure Stream Analytics | Real-time transaction scoring, anomaly detection |
| Azure Data Factory | ETL from core banking, card management, and loan origination systems |
| Power BI (Premium) | Executive dashboards, Basel III/IV reports, campaign analytics |
| Azure Purview | Data catalog, lineage tracking, PII classification |
| Azure Key Vault (HSM) | Encryption keys (CMK), certificates, API secrets |
| Application Insights | APM, distributed tracing |
| Azure Defender for Cloud | Continuous vulnerability scanning and threat detection |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- .NET 8 SDK (for Compliance API)
- Node.js >= 18 (for frontend)
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- PCI DSS-compliant network configuration

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-21-banking-crm

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Copy environment template and configure
cp .env.example .env
```

### Environment Variables

```bash
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
COSMOS_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/
ML_ENDPOINT=https://<your-ml-endpoint>.azureml.ms
REDIS_HOST=<your-redis>.redis.cache.windows.net
EVENT_HUB_CONNECTION=<event-hub-connection-string>
```

### Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Deploy Application

```bash
cd src
func azure functionapp publish <your-function-app-name>
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run integration tests (uses synthetic data only in dev)
python -m pytest test_integration.py -v

# Test health endpoint
curl https://<function-app>.azurewebsites.net/api/health
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID (OAuth2/OIDC) with Conditional Access (device + location + risk-based) and MFA enforcement for all users and service accounts
- **Authorization**: Fine-grained per-field RBAC for PII and financial data access; role hierarchy: RM, Compliance, Admin, Auditor; PIM for just-in-time privileged access with time-bound elevation
- **Managed Identity**: System-assigned managed identity with auto-rotation for zero-credential service-to-service authentication
- **Network Isolation**: PCI DSS-compliant 3-subnet topology (App/Data/Integration) isolating the Cardholder Data Environment (CDE); all PaaS services behind Private Link with zero public endpoints; NSG deny-all default with explicit allow rules; Network Watcher with flow logs and traffic analytics
- **PCI DSS Compliance**: WAF with OWASP 3.2 + PCI custom rules; PAN tokenization; mTLS for API gateway; header enforcement per PCI requirements

### Encryption

- **Data at Rest**: AES-256 encryption for all databases (Cosmos DB TDE, Synapse TDE, Blob Storage SSE); HSM-backed Customer-Managed Keys (CMK) with auto-rotation
- **Data in Transit**: TLS 1.3 enforced for all communication; mTLS for APIM gateway connections
- **Key Management**: Azure Key Vault Premium (HSM-backed) for encryption keys, certificates, and API secrets; automated key rotation policies
- **Dynamic Data Masking**: SSN, PAN (Primary Account Number), and DOB automatically masked for non-privileged roles; PAN tokenization before storage per PCI DSS Req 3

### Monitoring

- **Application Insights**: APM with distributed tracing across all CRM endpoints, ML model calls, and OpenAI interactions (50GB/month)
- **Log Analytics**: Centralized logging with 365-day retention for PCI DSS and SOX audit trail requirements (100GB/month)
- **Alerts**: Azure Monitor alerts for error rate (>1% threshold), P99 latency (>3000ms), compliance violations, and AML escalation triggers
- **Security Monitoring**: Azure Sentinel SIEM with automated playbooks for fraud and compliance alerts; Defender for Cloud continuous vulnerability scanning

### Visualization

- **Power BI Dashboard**: Basel III/IV regulatory reports, capital adequacy ratios, liquidity metrics, campaign performance analytics
- **RM Portal**: Customer 360 view with relationship health scores, NBA cards, and pipeline management
- **Compliance Dashboard**: PCI DSS, SOX, and GDPR compliance posture with risk heatmaps

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across all customer interactions, NBA scoring, KYC workflows, and regulatory reports
- **Correlation IDs**: End-to-end correlation from APIM through Functions, Cosmos DB, ML endpoints, and OpenAI for every customer request
- **Audit Logs**: Immutable audit logs with 7-year WORM retention (SOX Section 802); all access to cardholder data tracked per PCI DSS Req 10
- **KYC Screening Audit**: Every KYC/AML screening result persisted with model version, risk score, and compliance officer review status

### Accuracy

- **Churn Model**: Custom XGBoost model trained on historical attrition data yields 92% AUC; 30/60/90-day prediction windows evaluated separately
- **Propensity Scoring**: Neural network (PyTorch) cross-sell/upsell propensity evaluated with lift curves and calibration plots
- **Risk Scoring**: Gradient Boosted Trees for KYC/AML risk assessment with configurable thresholds (AML: 0.70, Churn: 0.65)
- **Automated Retraining**: Azure ML pipeline with champion/challenger model comparison; retraining triggered by data drift detection

### Explainability

- Next-best-action recommendations include rationale based on customer data, expected impact (revenue, satisfaction, retention), and urgency level
- Churn predictions include contributing factors with positive/negative impact weights and early warning signals
- KYC/AML screening results include detailed risk flags, suspicious patterns, regulatory references, and a narrative summary for compliance officers

### Responsibility

- **Content Filtering**: PII redaction in Azure OpenAI prompts prevents sensitive financial data from being exposed; Responsible AI filters enabled
- **Fair Lending**: ECOA compliance monitoring ensures non-discriminatory lending recommendations; propensity models evaluated for demographic bias
- **Human-in-the-Loop**: High-risk KYC/AML escalations require human compliance officer review; NBA recommendations are advisory
- **Regulatory Language**: System prompts enforce regulatory language compliance and disclosure requirements in all customer-facing AI outputs

### Interpretability

- **SHAP Values**: Churn and propensity models provide SHAP feature importance values for regulatory scrutiny and auditor review
- **Decision Transparency**: NBA engine separates ML propensity scores from GPT-4o personalized talking points, allowing RM to understand the quantitative and qualitative inputs
- **Model Cards**: Each deployed ML model has documented performance metrics, training data characteristics, and known limitations

### Portability

- **Containerization**: Azure Functions deployable as Docker containers; ML models exportable via MLflow for alternative serving
- **Infrastructure as Code**: Full Terraform configuration in `infra/` for reproducible deployments across 4 environments (dev, staging, UAT, production)
- **Multi-Cloud Considerations**: CRM patterns transferable; OpenAI API compatible with non-Azure endpoints; PCI DSS and Basel III/IV frameworks are cloud-agnostic
- **Data Export**: Customer 360 data exportable via API; regulatory reports generated as PDF/Excel; Cosmos DB change feed enables CDC to external systems

## Project Structure

```
project-21-banking-crm/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (customer-360, NBA, churn, KYC, RM insights, cross-sell)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/customer-360` | Build unified Customer 360 view across all banking products |
| POST | `/api/next-best-action` | AI-driven next-best-action recommendation for a customer |
| POST | `/api/churn-predict` | Churn risk scoring with contributing factors and retention actions |
| POST | `/api/kyc-screen` | KYC/AML screening with suspicious activity detection |
| POST | `/api/rm-insights` | Generate RM copilot briefing with talking points and action items |
| POST | `/api/cross-sell` | Cross-sell/upsell propensity scoring across product lines |
| GET | `/api/health` | Health check with endpoint listing |
| Event Hub | `CustomerEventProcessor` | Real-time processing of customer events (transactions, life events, meetings) |

## License

This project is licensed under the MIT License.
