# Project 7: Healthcare Clinical Copilot

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=flat&logo=openai&logoColor=white)
![HIPAA](https://img.shields.io/badge/HIPAA-Compliant-green?style=flat)
![FHIR R4](https://img.shields.io/badge/FHIR-R4-red?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-Python_3.11-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

A HIPAA-compliant clinical decision support system that empowers healthcare professionals with AI-driven insights at the point of care. The platform integrates Azure OpenAI GPT-4o for clinical reasoning and patient summary generation, Azure Health Data Services (FHIR R4) for standardized patient data exchange, and structured medical NER for entity extraction from clinical notes. Key capabilities include real-time drug interaction checking, automated patient summary generation from electronic health records, differential diagnosis assistance, and evidence-based clinical Q&A with guideline citations. The system enforces end-to-end PHI protection through encryption, private networking, comprehensive audit trails, and a signed Business Associate Agreement (BAA) with Microsoft Azure.

---

## Architecture

```
Clinician Interfaces (Web Portal, EHR Plugin, Mobile App)
        |
   Azure Front Door (WAF + CDN + SSL + Geo-filtering)
        |
   APIM Gateway (OAuth2 + SMART on FHIR Scopes + Audit Logging)
        |
   Private VNet (10.0.0.0/16)
   +-------+-------+-------+
   |       |       |       |
 Azure   Azure   Azure   Text Analytics
 Functions OpenAI  AI     for Health
 (Clinical (GPT-4o) Search (Medical NER)
  Engine)          (Medical
                    Index)
   |
   +-------+-------+-------+
   |       |       |       |
 FHIR R4  Cosmos  Redis   Blob Storage
 Server   DB      Cache   (PHI Docs)
 (Health  (Audit  (Query
  Data    Trails) Cache)
  Svc)
        |
   Clinical Data Ingestion Pipeline
   (HL7 FHIR + EHR Systems + Event Grid + Durable Functions)
        |
   Observability Layer
   (App Insights + Log Analytics + Sentinel + Defender for Cloud)
```

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Clinical reasoning, patient summaries, drug interaction analysis |
| Azure Health Data Services | FHIR R4 server for standardized patient data (conditions, meds, labs) |
| Text Analytics for Health | Medical NER: conditions (ICD-10), medications (RxNorm), anatomy (SNOMED CT) |
| Azure AI Search | Hybrid search over clinical guidelines, drug databases, ICD-10 codes |
| Azure Cosmos DB | Clinical session audit trails, interaction history (immutable, 7-year retention) |
| Azure Cache for Redis | FHIR query cache, frequently accessed patient context |
| Azure Blob Storage | PHI documents, clinical notes, imaging reports (CMK encrypted) |
| Azure Key Vault | CMK keys for PHI encryption, secrets, certificates (HSM-backed) |
| Azure Front Door | WAF, CDN, SSL termination, geo-filtering (US-only for PHI residency) |
| Azure APIM | OAuth2/JWT, SMART on FHIR scopes, rate limiting, PHI audit logging |
| Application Insights | APM with PHI-safe telemetry |
| Log Analytics | Centralized HIPAA-compliant logs (7-year retention) |
| Microsoft Sentinel | SIEM for PHI access anomaly detection |
| Defender for Cloud | HIPAA/HITRUST benchmark, vulnerability scanning |

---

## Prerequisites

- **Azure Subscription** with HIPAA BAA signed with Microsoft
- **Azure OpenAI Service** with GPT-4o deployment
- **Azure Health Data Services** workspace with FHIR R4 server provisioned
- **Azure AI Search** (S2 tier recommended for clinical workloads)
- **Azure Cosmos DB** with multi-region replication
- **Azure Key Vault** (Premium tier with HSM-backed keys)
- **Python 3.11+**
- **Azure Functions Core Tools v4**
- **Azure CLI** (authenticated)

---

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-7-healthcare-clinical-copilot

# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://<openai-resource>.openai.azure.com/"
export FHIR_ENDPOINT="https://<workspace>-<fhir>.fhir.azurehealthcareapis.com"
export COSMOS_ENDPOINT="https://<cosmos-account>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<keyvault-name>.vault.azure.net/"
export REDIS_HOST="<redis-name>.redis.cache.windows.net"
```

### 2. Install dependencies

```bash
cd src
pip install -r requirements.txt
```

### 3. Run locally (synthetic data only -- no real PHI in dev)

```bash
func start
```

### 4. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -var-file="env/prod.tfvars"
terraform apply -var-file="env/prod.tfvars"
```

### 5. Deploy function app

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

---

## Testing

```bash
# Run unit tests (uses synthetic/mock patient data)
cd tests
python -m pytest -v

# Run tests with coverage
python -m pytest --cov=src --cov-report=html -v

# IMPORTANT: Never use real PHI in test environments.
# All test fixtures must use synthetic patient data.
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Entra ID SSO with SMART on FHIR scopes; OAuth2/OIDC for clinician access; MFA required for all PHI access
- **Authorization**: Role-based clinical data access (Physician, Nurse, Lab Tech, Admin roles); ABAC for FHIR resource-level permissions
- **RBAC**: Fine-grained per-FHIR-resource RBAC; Break-Glass emergency access with full audit trail and auto-revocation
- **Managed Identity**: System-assigned managed identity for all Azure service authentication -- zero secrets in code
- **Network Isolation**: Dedicated healthcare VNet with 3 subnets (Application, Data, Integration); all PaaS services via Private Link; NSG deny-all default with least-privilege rules; geo-filtering restricts to US for PHI data residency
- **BAA Compliance**: Business Associate Agreements signed with all data processors

### Encryption

- **Data at Rest**: AES-256 encryption for all PHI stores; Customer-Managed Keys (CMK) via HSM-backed Key Vault for Cosmos DB, Blob Storage, FHIR Server
- **Data in Transit**: TLS 1.3 enforced on all endpoints; mutual TLS for service-to-service calls
- **Key Management**: Key Vault Premium with HSM-backed keys; crypto-shredding capability (revoking key renders all PHI unreadable); key rotation policies enforced
- **Backup Encryption**: Geo-redundant backups with encryption; 7-year HIPAA retention minimum

### Monitoring

- **Application Insights**: APM with PHI-safe telemetry (no PHI logged); distributed tracing across FHIR, OpenAI, and NER calls
- **Log Analytics**: Centralized HIPAA-compliant logging with 7-year retention; Kusto queries for compliance reporting
- **Alerts**: Critical alerts for PHI access anomalies, FHIR server errors, OpenAI latency spikes; SMS/Email/Teams notifications
- **Dashboards**: Azure Monitor compliance dashboard; Defender for Cloud HIPAA/HITRUST benchmark scoring; cost management dashboard
- **Sentinel SIEM**: Security event correlation with healthcare-specific threat intelligence; automated breach detection

### Visualization

- **Clinician Portal**: React-based web interface for clinical decision support
- **EHR Integration**: SMART on FHIR embedded widgets within Epic, Cerner, and other EHR systems
- **Compliance Dashboard**: Azure Monitor dashboard tracking HIPAA benchmark compliance scores and PHI access patterns

### Tracking

- **Request Tracing**: Application Insights distributed tracing with correlation IDs spanning FHIR queries, NER extraction, and GPT-4o generation
- **Correlation IDs**: Each clinical session gets a unique `session_id` tracked across all query, entity extraction, and response interactions
- **Audit Logs**: Immutable PHI access audit trail in Cosmos DB with timestamp, session ID, patient ID, query, and compliance flags (HIPAA, HITECH); every profile access logged with purpose
- **Breach Notification**: Automated 60-day breach notification workflow per HIPAA Section 164.404

### Accuracy

- **Model Evaluation**: Clinical response quality validated against established guidelines (AHA, ADA, NCCN)
- **Confidence Thresholds**: Drug interaction severity scoring (contraindicated, major, moderate, minor, none); NER temperature set to 0.1 for near-deterministic entity extraction
- **Validation**: JSON schema validation on all GPT-4o responses; FHIR R4 resource schema validation; ICD-10, RxNorm, SNOMED CT code mapping for entity standardization
- **Clinical Disclaimer**: Every response includes mandatory disclaimer: "Clinical decision support only. Review by licensed provider required."

### Explainability

- **Citation-Backed Responses**: Clinical answers include `[Source: guideline_name, Year]` citations to established medical guidelines
- **Entity Transparency**: NER extraction returns categorized entities (conditions, medications, procedures, lab values, allergies, vitals) with explicit ICD-10/RxNorm codes
- **Drug Interaction Detail**: Each interaction includes `drug_pair`, `severity`, `mechanism`, `description`, and `recommendation` for full pharmacological transparency
- **Clinical Narrative**: Patient summaries include structured sections (active conditions, current medications, care gaps) alongside a human-readable clinical narrative

### Responsibility

- **Content Filtering**: Azure OpenAI content safety filters prevent generation of harmful medical advice
- **Scope Boundaries**: System prompts enforce that the AI supports but does not replace clinical judgment; never provides definitive diagnoses
- **PHI De-Identification**: HIPAA Safe Harbor method for research data; automated de-identification pipeline
- **Minimum Necessary**: PHI access scoped to minimum necessary data for the clinical function
- **FDA Awareness**: AI/ML model governance aligned with FDA Software as Medical Device (SaMD) guidance

### Interpretability

- **Structured Output**: All clinical responses return structured JSON with separate fields for entities, citations, narrative, and metadata
- **Feature Importance**: NER extraction shows which medical entities were identified and how they influenced the clinical response
- **Decision Transparency**: Drug interaction checks provide pharmacological mechanism explanations, not just severity flags
- **Session History**: Full session interaction history retrievable for clinical audit and review

### Portability

- **Infrastructure as Code**: Terraform modules in `infra/` for full HIPAA-compliant environment provisioning
- **Containerization**: Azure Functions can be containerized for AKS deployment; all configuration externalized via environment variables
- **FHIR Interoperability**: FHIR R4 standard ensures portability across EHR systems (Epic, Cerner, AllScripts)
- **Multi-Environment**: Blue-green deployment strategy with staging-to-production manual approval gates for HIPAA change control

---

## Project Structure

```
project-7-healthcare-clinical-copilot/
|-- docs/
|   +-- ARCHITECTURE.md
|-- infra/
|   +-- main.tf
|-- src/
|   +-- function_app.py
|-- tests/
+-- README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/clinical-query` | Main clinical Q&A with entity extraction and guideline citations |
| POST | `/api/drug-check` | Check drug-drug interactions with severity scoring |
| POST | `/api/patient-summary` | Generate structured clinical summary from FHIR patient data |
| GET | `/api/sessions/{session_id}/history` | Retrieve clinical session history for audit |
| GET | `/api/health` | Health check (includes HIPAA/HITECH compliance flags) |

---

## License

This project is licensed under the MIT License.
