# HR Talent Intelligence Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![AI Search](https://img.shields.io/badge/AI%20Search-Semantic-blue)
![Azure ML](https://img.shields.io/badge/Azure%20ML-Predictions-purple)
![Document Intelligence](https://img.shields.io/badge/Document%20Intelligence-OCR-orange)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

An enterprise-grade HR Talent Intelligence Platform powered by Azure OpenAI that automates resume screening, performs skill gap analysis, enables internal mobility matching, and supports strategic workforce planning. The system leverages GPT-4o for natural language understanding of resumes and job descriptions, Azure AI Search for semantic talent matching with vector embeddings (text-embedding-ada-002), Document Intelligence for resume OCR parsing, and Azure ML for predictive workforce analytics (attrition prediction, demand forecasting). All candidate PII is protected end-to-end with encryption, data masking, and strict RBAC controls compliant with GDPR, EEOC, and SOC 2 requirements.

## Architecture

```
User Interfaces
  - HR Portal (React)
  - Hiring Manager Dashboard (Power BI Embedded)
  - Employee Self-Service (React Native)
        |
        v
  Azure Front Door (WAF + CDN + SSL)
        |
  +-----+-----+-----+
  |           |           |
  v           v           v
APIM         Static       SignalR
Gateway      Web App      (Real-time
(Auth, PII   (Frontend)   Notifications)
 Filter)
        |
        v
  Private VNet (10.0.0.0/16)
        |
  Azure Functions (Talent Engine)
  - Resume Screening (GPT-4o)
  - Skill Gap Analysis (GPT-4o)
  - Mobility Matching (GPT-4o + AI Search)
  - Workforce Planning (GPT-4o)
        |
  +-----+-----+-----+
  |           |           |
  v           v           v
Azure        Azure ML    Azure AI Search
OpenAI       (Workforce  (Talent Index)
(GPT-4o)     Prediction) - Skill Vectors
             (LightGBM)  - Resume Search
                          - Job Matching
        |
        v
  Data Layer
  - Cosmos DB (Profiles, Skills, History)
  - ADLS Gen2 (Resume Lake, Analytics)
  - Redis Cache (Match Cache, Session)
        |
  Integration Layer
  - Data Factory (ATS/HRIS: Workday, SAP SF)
  - Document Intelligence (Resume OCR)
  - Key Vault (PII Keys, Secrets)

  Resume Pipeline (Durable Functions):
  Upload --> Doc Intel OCR --> PII Redact --> Skill Extraction (GPT-4o)
  --> Embedding (ada-002) --> Cosmos DB Profile --> AI Search Index
```

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Resume evaluation, skill extraction, gap analysis, workforce planning |
| Azure OpenAI (ada-002) | Skill and resume vector embeddings for semantic matching |
| Azure AI Search (S1) | Hybrid talent pool search, job-candidate matching with semantic ranker |
| Azure Document Intelligence | Resume OCR and structured data extraction (prebuilt-layout + custom) |
| Azure ML | Attrition prediction (LightGBM), workforce demand forecasting |
| Azure Functions (Python 3.11) | Talent engine, resume pipeline (Durable Functions) |
| Azure Cosmos DB | Candidate profiles, skill graphs, screening history (serverless) |
| ADLS Gen2 | Resume data lake, analytics datasets (GRS replication) |
| Azure Data Factory | ATS/HRIS data ingestion (Workday, SAP SuccessFactors) |
| Azure Redis Cache (P1) | Match result caching, session state |
| Azure Key Vault (Premium HSM) | PII encryption keys, certificates |
| Azure Front Door | Global load balancing, WAF, DDoS protection |
| Azure APIM | API management with PII filtering |
| Azure SignalR | Real-time screening status notifications |
| Microsoft Purview | PII classification, sensitivity labels, data lineage |

## Prerequisites

- Azure Subscription with Contributor access
- Azure OpenAI resource with GPT-4o and text-embedding-ada-002 deployed
- Azure AI Search (S1 tier, 3 replicas, 2 partitions)
- Azure Document Intelligence (S0 tier)
- Azure ML workspace with DS3v2 compute
- Python 3.11+
- Azure Functions Core Tools v4
- Terraform >= 1.5
- Azure CLI >= 2.50

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-15-hr-talent-intelligence

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

### 4. Screen a Resume

```bash
curl -X POST http://localhost:7071/api/screen-resume \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Senior Data Engineer with 7 years of experience in Python, SQL, Spark, and Azure...",
    "job_requirements": {
      "title": "Senior Data Engineer",
      "required_skills": ["Python", "SQL", "Spark"],
      "preferred_skills": ["Azure", "Databricks"],
      "min_experience_years": 5,
      "education": "Bachelors in Computer Science"
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
pytest -v -k "test_screen"          # Resume screening tests
pytest -v -k "test_skill_gap"       # Skill gap analysis tests
pytest -v -k "test_mobility"        # Internal mobility matching tests
pytest -v -k "test_workforce"       # Workforce planning tests
pytest -v -k "test_embedding"       # Embedding generation tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID SSO/OIDC with Conditional Access and MFA enforcement
- **Authorization**: Role matrix with tiered PII access: HR Admin (Full PII), Recruiter (Masked PII), Hiring Manager (Anonymized), Employee (Own Profile Only)
- **RBAC**: Fine-grained HR roles (HRAdmin, Recruiter, HiringManager, Employee) defined as Entra ID App Roles
- **Managed Identity**: System-assigned managed identity for zero-credential access to all services including OpenAI, AI Search, Cosmos DB, ADLS, Redis, and Key Vault
- **Network Isolation**: Dedicated VNet (10.0.0.0/16) with Application, Data, and Integration subnets; all PaaS services on Private Link with no public endpoints

### Encryption

- **Data at Rest**: AES-256 SSE for all storage; PII data encrypted with HSM-backed Customer-Managed Keys (CMK) in Key Vault Premium
- **Data in Transit**: TLS 1.3 enforced for all communications
- **Key Management**: Azure Key Vault Premium with HSM-backed keys, soft delete, and purge protection; separate PII encryption keys managed per data classification
- **PII Tokenization**: SSN, DOB, address, and phone tokenized and stored separately from candidate profiles; originals encrypted with CMK

### Monitoring

- **Application Insights**: APM with 25% sampling and PII scrubbing enabled; distributed tracing across resume pipeline
- **Log Analytics**: 365-day retention with PII query auditing enabled
- **Alerts**: PII access anomaly detection, screening bias drift monitoring, model latency P95 alerts
- **Dashboards**: Screening throughput, skill match accuracy, pipeline latency, and bias metrics dashboards

### Visualization

- **Power BI Embedded**: Hiring Manager dashboard with workforce insights, candidate pipeline analytics, and diversity metrics
- **HR Portal (React)**: Recruiter interface for resume upload, analysis viewer, and candidate ranking
- **Employee Self-Service**: Internal mobility portal for skill profiles and career path exploration

### Tracking

- **Request Tracing**: End-to-end correlation IDs across Event Grid, Durable Functions, OpenAI, AI Search, and Cosmos DB
- **Screening Audit Trail**: Every screening decision logged in Cosmos DB with full prompt, reasoning, score, recommendation, and timestamp
- **PII Access Logging**: All access to candidate PII tracked with user identity, action, and timestamp; < 1 hour alert response
- **Prompt Flow Tracing**: Azure Prompt Flow integration for debugging and monitoring GenAI call chains

### Accuracy

- **Screening Latency**: < 8 seconds per resume (P95)
- **Skill Gap Analysis**: < 3 seconds (cached), < 10 seconds (uncached)
- **Mobility Match Accuracy**: > 85% relevance in top-5 candidate matches
- **Confidence Thresholds**: Resume screening threshold at 0.65; mobility match threshold at 0.70
- **Bias Drift Detection**: Weekly automated reports with < 5% variance threshold for demographic score distributions

### Explainability

- Resume screening results include overall score, matched skills, skill gaps, experience score, education match, recommendation (STRONG_MATCH / POTENTIAL_MATCH / NO_MATCH), and a 2-3 sentence justification
- Skill gap analysis categorizes gaps by priority (critical, important, nice-to-have) with specific learning paths, estimated weeks, and recommended certifications
- Internal mobility matching provides per-position fit scores with justification and growth areas identified
- Workforce planning includes risk factors with severity and mitigation, hiring plan with quarterly justification, and strategic alignment score

### Responsibility

- **Bias Prevention**: Prompts explicitly exclude age, gender, ethnicity, and name from scoring criteria; screening evaluations focus solely on skills, experience, and qualifications
- **Content Filtering**: Azure OpenAI content filtering with custom bias-detection policies; bias guardrails enforced in all prompts
- **AI Transparency**: Candidates informed of AI use in hiring process per NYC Local Law 144 requirements
- **EEOC Compliance**: Equal Employment Opportunity monitoring and reporting; regular bias audits
- **Data Minimization**: Only job-relevant data collected and processed; GDPR right-to-erasure pipeline auto-purges candidate data after 24 months
- **Fairness Metrics**: Azure ML monitors screening score distributions for demographic drift per protected class

### Interpretability

- Screening scores broken down into component scores: overall fit, experience relevance, education match, and per-skill matching
- Skill gap analysis provides granular view: matching skills, critical gaps, important gaps, nice-to-have gaps with estimated timelines
- Workforce planning outputs quarterly headcount forecasts, risk factors with severity ratings, and budget implications
- All recommendations linked to supporting data and reasoning

### Portability

- **Containerization**: Azure Functions packaged as Docker containers; React frontend deployable as Static Web App
- **Infrastructure as Code**: Full Terraform configuration in `infra/main.tf` with multi-environment support (dev/staging/prod with HSM tier escalation)
- **Multi-Cloud Considerations**: Core talent matching logic decoupled from Azure SDKs; vector search adaptable to other providers
- **CI/CD**: Blue-green deployment with pre-deploy checks for PII scan, bias test, and RBAC validation

## Project Structure

```
project-15-hr-talent-intelligence/
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
| POST | `/api/screen-resume` | AI-powered resume screening with scoring and recommendation |
| POST | `/api/skill-gap` | Skill gap analysis with learning path recommendations |
| POST | `/api/mobility-match` | Internal mobility matching using AI Search + GPT-4o |
| POST | `/api/workforce-plan` | GenAI-powered workforce planning insights |
| GET | `/api/health` | Health check endpoint |
| Event | `ResumeUploadTrigger` | Event Grid trigger for resume upload processing and indexing |

## License

This project is licensed under the MIT License.
