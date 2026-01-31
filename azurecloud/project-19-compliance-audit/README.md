# Project 19: Compliance Audit Automation

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat)
![Azure Policy](https://img.shields.io/badge/Azure%20Policy-Compliance-red?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-yellow?style=flat)
![SOC 2](https://img.shields.io/badge/SOC%202-Type%20II-green?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade compliance audit automation platform that leverages Azure OpenAI GPT-4o to automate evidence collection, control testing, audit trail analysis, and GenAI-powered audit report generation. The system continuously monitors Azure environments using Azure Policy and Azure Resource Graph, collects compliance evidence via automated pipelines, and generates comprehensive audit reports aligned with SOC 2 Type II, ISO 27001, NIST 800-53, and PCI DSS frameworks. Azure Document Intelligence extracts structured data from compliance artifacts, while AI Search enables semantic retrieval across the full evidence corpus for auditor-assisted investigation.

## Architecture

```
Evidence Collection Pipeline:
Azure Policy + Resource Graph + Sentinel --> Data Factory (Orchestration)
                                                  |
                              +-------------------+-------------------+
                              |                   |                   |
                        Document Intel      Log Analytics       Config State
                        (OCR/Parse)         (Query Audit)       (Resource Graph)
                              |                   |                   |
                              +-------------------+-------------------+
                                                  |
                                    Cosmos DB (Evidence Store + Audit Trail)
                                                  |
                                    AI Search (Semantic Evidence Index)

Audit Report Generation:
Auditor Request --> APIM Auth --> Framework Selection --> Control Mapping
                                                              |
                                               Evidence Query (Cosmos DB)
                                                              |
                                               AI Search (Semantic Retrieval)
                                                              |
                                               GPT-4o (Report Narrative)
                                                              |
                                               Deliver Report (PDF/Word/Blob)
```

**Key Components:**
- **Auditor Portal** (React + TypeScript) -- Compliance dashboard, evidence review, report configuration
- **Executive Dashboard** (Power BI Embedded) -- Real-time compliance posture, trend analysis, risk heatmaps
- **GRC Integration** (REST/GraphQL) -- Integration with ServiceNow, Archer, OneTrust
- **Azure Functions** (Python 3.11) -- Evidence collection, control testing, report generation, trail analysis

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Audit report narrative generation, finding summarization |
| Azure OpenAI (text-embedding-ada-002) | Vector embeddings for evidence semantic search |
| Azure Document Intelligence | Parse compliance certificates, audit letters, policy PDFs |
| Azure AI Search | Hybrid search across evidence corpus with semantic ranking |
| Azure Policy | Compliance state assessment across subscriptions |
| Azure Resource Graph | Real-time resource inventory and configuration state |
| Azure Cosmos DB | Audit trails, control results, evidence metadata (strong consistency) |
| Azure Blob Storage | Evidence artifacts with immutable WORM policies and legal hold |
| Azure Data Factory | Scheduled evidence collection orchestration across sources |
| Azure Sentinel | Security event correlation, incident evidence |
| Azure Defender for Cloud | Security posture scoring, regulatory compliance view |
| Azure Purview | Data catalog, lineage tracking, sensitivity labels |
| Azure Key Vault | HSM-backed secrets, certificates, encryption keys |
| Application Insights | APM, dependency tracking |
| Log Analytics | 365-day retention centralized audit logging |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- Azure Policy assignments configured
- Log Analytics workspace provisioned

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-19-compliance-audit

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
LOG_ANALYTICS_WORKSPACE_ID=<workspace-id>
SUBSCRIPTION_ID=<your-subscription-id>
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

# Run integration tests
python -m pytest test_integration.py -v

# Test health endpoint
curl https://<function-app>.azurewebsites.net/api/health
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID (OAuth2/OIDC) with Conditional Access, MFA enforcement for all users, and Auditor-specific role assignments
- **Authorization**: Fine-grained RBAC separating Auditor, Admin, and Compliance Officer roles; PIM (Privileged Identity Management) for just-in-time audit system administration
- **Managed Identity**: System-assigned managed identity for zero-credential service-to-service authentication across all services
- **Network Isolation**: Dedicated VNet with 3 subnets (Application, Data, Integration); all PaaS services behind Private Link with no public endpoints; NSG rules default deny-all
- **Perimeter**: Azure Front Door with WAF (OWASP 3.2), DDoS Protection, geo-filtering, and IP allow-listing

### Encryption

- **Data at Rest**: AES-256 encryption for all services; HSM-backed Customer-Managed Keys (CMK) via Key Vault (FIPS 140-2 Level 2)
- **Data in Transit**: TLS 1.3 enforced for all service communication
- **Key Management**: Azure Key Vault Premium (HSM-backed) with soft delete, purge protection, and automated key rotation
- **Evidence Integrity**: Immutable Blob Storage (WORM) with time-based retention policies (7-year regulatory retention) and legal hold support

### Monitoring

- **Application Insights**: APM with distributed tracing across evidence collection, control testing, and report generation workflows
- **Log Analytics**: 365-day retention with centralized KQL queries for cross-subscription audit log aggregation (50GB/day ingestion)
- **Alerts**: Azure Monitor with smart detection alerts for compliance state changes, evidence collection failures, and posture degradation
- **Dashboards**: Power BI Embedded for real-time compliance posture, trend analysis, and risk heatmaps; SOC dashboard for compliance visualization

### Visualization

- **Executive Dashboard**: Power BI Embedded with real-time compliance posture, framework-level trend analysis, and risk heatmaps
- **Auditor Portal**: React-based interface for evidence review, control testing, and report configuration
- **Defender for Cloud**: Built-in regulatory compliance dashboard for continuous posture assessment

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across all evidence collection and report generation pipelines
- **Correlation IDs**: End-to-end correlation for every compliance scan, evidence collection, and audit report request
- **Audit Logs**: Activity logs with 365-day immutable retention; tamper-proof audit ledger in Cosmos DB (append-only)
- **Evidence Chain**: Cryptographic chain of custody for all evidence artifacts; Purview sensitivity labels and data lineage tracking

### Accuracy

- **Model Evaluation**: Audit report generation accuracy validated against human-authored benchmark reports; finding classification precision measured per framework
- **Confidence Thresholds**: Control test results include confidence scores (0.0 to 1.0); low-confidence findings flagged for auditor review
- **Validation**: Framework control mappings validated against official SOC 2, ISO 27001, NIST 800-53, and PCI DSS v4.0 control catalogs

### Explainability

- Control test results include specific findings, identified gaps, and remediation recommendations with evidence references
- Audit reports map every finding to specific framework controls with evidence citations
- Compliance posture assessments include key strengths, improvement areas, and top risks with mitigation strategies

### Responsibility

- **Content Filtering**: Azure OpenAI content safety ensures no sensitive data leaks into generated report narratives
- **Bias Detection**: Automated compliance assessments monitored for systematic scoring bias across resource types and subscription segments
- **Human-in-the-Loop**: Auditors review and approve all AI-generated report drafts before finalization; GPT-4o assists but does not replace human judgment
- **Separation of Duties**: Audit independence enforced -- separation between audit system operations and compliance assessment roles

### Interpretability

- **Feature Importance**: Compliance posture assessments show control-level pass/fail breakdown with per-control evidence counts
- **Decision Transparency**: Control test results explain the reasoning behind PASS/FAIL/PARTIAL verdicts with supporting evidence references
- **Risk Scoring**: Risk levels (LOW/MEDIUM/HIGH/CRITICAL) include contributing factors and remediation priorities

### Portability

- **Containerization**: Azure Functions deployable as Docker containers for local development and testing
- **Infrastructure as Code**: Full Terraform configuration in `infra/` for reproducible multi-environment deployments (dev, staging, production)
- **Multi-Cloud Considerations**: Compliance frameworks (SOC 2, ISO 27001, NIST, PCI DSS) are cloud-agnostic; evidence collection patterns transferable to AWS Config or GCP Security Command Center
- **Data Export**: Audit reports exportable as PDF/Word; evidence data exportable from Cosmos DB and Blob Storage for external GRC systems

## Project Structure

```
project-19-compliance-audit/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (evidence, control test, audit, report, posture)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/collect-evidence` | Collect compliance evidence for a control from Azure resources |
| POST | `/api/test-control` | Test control effectiveness using AI analysis of collected evidence |
| POST | `/api/audit-trail` | Analyze activity logs for compliance violations and anomalies |
| POST | `/api/generate-report` | Generate comprehensive GenAI-powered audit report |
| POST | `/api/compliance-posture` | Overall compliance posture assessment for a framework |
| GET | `/api/health` | Health check with supported frameworks listing |
| Timer | `ScheduledComplianceScan` | Weekly automated posture scan across all frameworks (Monday 06:00 UTC) |

## License

This project is licensed under the MIT License.
