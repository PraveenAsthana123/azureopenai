# Project 15: HR Talent Intelligence Platform

## Executive Summary

An enterprise-grade HR Talent Intelligence Platform powered by Azure OpenAI that automates resume screening, performs skill gap analysis, enables internal mobility matching, and supports strategic workforce planning. The system leverages GPT-4o for natural language understanding of resumes and job descriptions, Azure AI Search for semantic talent matching, Document Intelligence for resume parsing, and Azure ML for predictive workforce analytics. All candidate PII is protected end-to-end with encryption, data masking, and strict RBAC controls compliant with GDPR, EEOC, and SOC 2 requirements.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        HR TALENT INTELLIGENCE PLATFORM                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   HR Portal     │     │   Hiring Mgr    │     │   Employee      │
│  (React/Next)   │     │   Dashboard     │     │   Self-Service  │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (Frontend)     │   │  (Real-time     │
│   Auth, PII     │   │                 │   │   Notifications)│
│   Filtering)    │   │                 │   │                 │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌────────────────────────────────────────────────────────────────┐
         │  │                   PRIVATE VNET (10.0.0.0/16)                   │
         │  │  ┌──────────────────────────────────────────────────────────┐  │
         │  │  │              Application Subnet (10.0.1.0/24)           │  │
         ▼  │  │                                                         │  │
┌───────────┴──┴───┐                                                     │  │
│ Azure Functions  │◄──────────────────────────────────────────────────┐ │  │
│ (Talent Engine)  │                                                   │ │  │
│                  │    ┌──────────────────┐   ┌──────────────────┐    │ │  │
│ - Resume Screen  │    │  Azure OpenAI    │   │  Azure ML        │    │ │  │
│ - Skill Gap      │◄───┤  (GPT-4o)       │   │  (Workforce      │    │ │  │
│ - Mobility Match │    │  Private Link    │   │   Prediction)    │    │ │  │
│ - Workforce Plan │    └──────────────────┘   └──────────────────┘    │ │  │
└────────┬─────────┘                                                   │ │  │
         │                                                             │ │  │
         │              ┌──────────────────┐                           │ │  │
         ├─────────────►│  Azure AI Search │◄──────────────────────────┘ │  │
         │              │  (Talent Index)  │                             │  │
         │              │  - Skill Vectors │                             │  │
         │              │  - Resume Search │                             │  │
         │              │  - Job Matching  │                             │  │
         │              └────────┬─────────┘                            │  │
         │                       │                                      │  │
         │  ┌────────────────────┼───────────────────────────────────┐  │  │
         │  │           Data Subnet (10.0.2.0/24)                    │  │  │
         │  │                    │                                    │  │  │
         │  │    ┌───────────────┼───────────────────┐               │  │  │
         │  │    │               │                   │               │  │  │
         │  │    ▼               ▼                   ▼               │  │  │
         │  │ ┌──────────┐ ┌──────────────┐  ┌────────────────┐     │  │  │
         │  │ │ Cosmos DB│ │ ADLS Gen2    │  │ Redis Cache    │     │  │  │
         │  │ │(Profiles,│ │ (Resume Lake,│  │ (Match Cache,  │     │  │  │
         │  │ │ Skills,  │ │  Analytics)  │  │  Session State)│     │  │  │
         │  │ │ History) │ │              │  │                │     │  │  │
         │  │ └──────────┘ └──────────────┘  └────────────────┘     │  │  │
         │  └────────────────────────────────────────────────────────┘  │  │
         │                                                              │  │
         │  ┌────────────────────────────────────────────────────────┐  │  │
         │  │        Integration Subnet (10.0.3.0/24)                │  │  │
         │  │                                                        │  │  │
         │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │  │
         │  │  │  Key Vault   │  │ Document     │  │ Data Factory │ │  │  │
         │  │  │  (Secrets,   │  │ Intelligence │  │ (ATS/HRIS    │ │  │  │
         │  │  │   PII Keys)  │  │ (Resume OCR) │  │  Ingestion)  │ │  │  │
         │  │  └──────────────┘  └──────────────┘  └──────────────┘ │  │  │
         │  └────────────────────────────────────────────────────────┘  │  │
         └──────────────────────────────────────────────────────────────┘  │
                                                                           │
┌──────────────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────────────┐
│   │              RESUME INGESTION & PROCESSING PIPELINE                  │
│   │                                                                      │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐               │
│   │  │ ATS      │    │ Email    │    │ Azure Blob       │               │
│   │  │ Connector│    │ Parsing  │    │ (Resume Drop)    │               │
│   │  │(Workday/ │    │ Service  │    │                  │               │
│   │  │ SAP SF)  │    │          │    │                  │               │
│   │  └─────┬────┘    └────┬─────┘    └────────┬─────────┘               │
│   │        │              │                    │                         │
│   │        └──────────────┼────────────────────┘                        │
│   │                       ▼                                              │
│   │              ┌─────────────────┐                                     │
│   │              │  Event Grid     │                                     │
│   │              │  (Blob Events)  │                                     │
│   │              └────────┬────────┘                                     │
│   │                       ▼                                              │
│   │              ┌─────────────────┐                                     │
│   │              │ Durable Function │                                    │
│   │              │ (Resume Pipeline)│                                    │
│   │              └────────┬────────┘                                     │
│   │                       │                                              │
│   │        ┌──────────────┼──────────────────┐                          │
│   │        ▼              ▼                  ▼                           │
│   │  ┌──────────┐  ┌─────────────┐  ┌──────────────────┐               │
│   │  │ Doc Intel│  │ PII Redact  │  │ Skill Extraction │               │
│   │  │ (Resume  │  │ (Mask SSN,  │  │ (GPT-4o Entity   │               │
│   │  │  OCR)    │  │  DOB, Addr) │  │  Recognition)    │               │
│   │  └──────────┘  └─────────────┘  └──────────────────┘               │
│   │                       │                                              │
│   │                       ▼                                              │
│   │        ┌──────────────┼──────────────────┐                          │
│   │        ▼              ▼                  ▼                           │
│   │  ┌──────────┐  ┌─────────────┐  ┌──────────────────┐               │
│   │  │ Embedding│  │ Cosmos DB   │  │ AI Search Index  │               │
│   │  │ (ada-002)│  │ (Profile)   │  │ (Talent Vectors) │               │
│   │  └──────────┘  └─────────────┘  └──────────────────┘               │
│   └─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY LAYER                                │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │ App Insights │  │ Log Analytics│  │ Azure Monitor                │   │
│  │ (APM)        │  │ (Logs)       │  │ (Metrics/Alerts)             │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘   │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │ Prompt Flow  │  │ Cost Mgmt    │  │ Defender for Cloud           │   │
│  │ Tracing      │  │ Dashboard    │  │ (PII Leak Detection)         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RESUME SCREENING FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

    Resume Upload                                       Screening Result
        │                                                    ▲
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 1. Blob Store │                                   │ 8. Score &    │
│ (Resume Drop) │                                   │ Rank Output   │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 2. Document   │                                   │ 7. GPT-4o     │
│ Intelligence  │                                   │ Evaluation    │
│ (OCR/Parse)   │                                   │ (Fit Score)   │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 3. PII        │                                   │ 6. Augment    │
│ Detection &   │                                   │ with Job Desc │
│ Redaction     │                                   │ Requirements  │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐     ┌───────────────┐             ┌───────────────┐
│ 4. Skill      │────►│ 5. Embed &    │────────────►│ Candidate     │
│ Extraction    │     │ Vector Index  │             │ Profile       │
│ (GPT-4o NER)  │     │ (AI Search)   │             │               │
└───────────────┘     └───────────────┘             └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    SKILL GAP ANALYSIS FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

    Employee Profile                                   Gap Report
        │                                                 ▲
        ▼                                                 │
┌───────────────┐                                 ┌───────────────┐
│ 1. Fetch      │                                 │ 7. Generate   │
│ Current Skills│                                 │ Learning Plan │
│ (Cosmos DB)   │                                 │ (GPT-4o)      │
└───────┬───────┘                                 └───────┬───────┘
        │                                                  │
        ▼                                                  │
┌───────────────┐                                 ┌───────────────┐
│ 2. Fetch Role │                                 │ 6. Prioritize │
│ Requirements  │                                 │ & Recommend   │
│ (AI Search)   │                                 │ Training      │
└───────┬───────┘                                 └───────┬───────┘
        │                                                  │
        ▼                                                  │
┌───────────────┐     ┌───────────────┐           ┌───────────────┐
│ 3. Normalize  │────►│ 4. Compare    │──────────►│ 5. Identify   │
│ Skill Vectors │     │ Embeddings    │           │ Gaps & Scores │
│ (ada-002)     │     │ (Cosine Sim)  │           │               │
└───────────────┘     └───────────────┘           └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                 INTERNAL MOBILITY MATCHING FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

    Open Position                                    Matched Candidates
        │                                                  ▲
        ▼                                                  │
┌───────────────┐     ┌───────────────┐           ┌───────────────┐
│ 1. Parse Job  │────►│ 2. Semantic   │──────────►│ 3. Rank &     │
│ Requirements  │     │ Search Talent │           │ Score Matches │
│ (GPT-4o)      │     │ Pool (AI Srch)│           │ (GPT-4o)      │
└───────────────┘     └───────────────┘           └───────┬───────┘
                                                           │
                                                           ▼
                                                  ┌───────────────┐
                                                  │ 4. Azure ML   │
                                                  │ Retention Risk│
                                                  │ Prediction    │
                                                  └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| HR Portal | React + TypeScript | Recruiter and HR analyst interface |
| Hiring Manager Dashboard | React + Power BI Embedded | Candidate review and workforce insights |
| Employee Self-Service | React Native (Web/Mobile) | Internal mobility, skill profiles |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL termination | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits, PII filter | API management, request validation |
| SignalR | Serverless mode | Real-time screening status notifications |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Talent Engine | Azure Functions (Python 3.11) | Resume screening, matching, skill analysis |
| Resume Pipeline | Durable Functions | Resume ingestion and processing orchestration |
| Workforce Planner | Azure Functions | Headcount forecasting and analytics |
| Notification Service | Azure Functions | Candidate/recruiter email and push alerts |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Resume evaluation, skill extraction, gap analysis |
| Azure OpenAI | text-embedding-ada-002 | Skill and resume vector embeddings |
| Document Intelligence | prebuilt-layout + custom model | Resume OCR, structured data extraction |
| AI Search | Semantic ranker + vector search | Talent pool search, job-candidate matching |
| Azure ML | Custom scikit-learn + LightGBM | Attrition prediction, workforce demand forecast |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Serverless, multi-partition | Candidate profiles, skill graphs, screening history |
| ADLS Gen2 | Hot + Cool tiers, hierarchical namespace | Resume data lake, analytics datasets |
| Azure Blob Storage | Hot tier, soft delete, versioning | Raw resume storage (PDF, DOCX) |
| Redis Cache | P1 Premium, VNET-integrated | Match result caching, session state |
| AI Search | S1 tier, 3 replicas | Talent vector index, job requisition index |

### 6. Integration Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Data Factory | Managed VNET, scheduled triggers | ATS/HRIS data ingestion (Workday, SAP SF) |
| Event Grid | System topic on Blob Storage | Resume upload event routing |
| Key Vault | RBAC, soft delete, purge protection | Secrets, PII encryption keys, certificates |

### 7. Security & Compliance Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication, role assignment |
| Managed Identity | System-assigned for all services | Zero-credential service-to-service auth |
| Private Link | All PaaS services | Network isolation, no public endpoints |
| Microsoft Purview | Sensitivity labels, data catalog | PII classification, data lineage tracking |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
│                  (HR DATA & PII PROTECTION FOCUS)                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (Allowed Regions│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO/OIDC)  │  │ Access      │  │ Enforcement │  │ time HR Admin)  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                                          │
│ Role Matrix:  HR Admin | Recruiter | Hiring Manager | Employee (Self)    │
│               Full PII   Masked PII  Anonymized       Own Profile Only   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                                          │
│ Private Link: OpenAI | AI Search | Cosmos DB | ADLS | Key Vault | Redis │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: PII & DATA SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ PII Masking │  │ Purview         │  │
│ │ at Rest +   │  │ (CMK for    │  │ (SSN, DOB,  │  │ (Sensitivity    │  │
│ │ Transit     │  │  PII data)  │  │  Address,   │  │  Labels, Data   │  │
│ │ (TLS 1.3)   │  │             │  │  Phone)     │  │  Classification)│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                                          │
│ PII Flow: Resume -> Detect PII -> Redact/Tokenize -> Store Encrypted    │
│           Original PII stored separately with CMK in Key Vault           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain │  │ Throttling  │  │ Filtering       │  │
│ │ (Zero Cred) │  │  HR Roles)  │  │ (per user)  │  │ (Bias Guard)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                                          │
│ Bias Guardrails: No age/gender/ethnicity in scoring prompts              │
│ Audit Trail: Every screening decision logged with explainability         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING, AUDIT & COMPLIANCE                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM +     │  │ (PII Access │  │ Manager (GDPR,  │  │
│ │             │  │  PII Alerts)│  │  Tracking)  │  │  EEOC, SOC 2)   │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                                          │
│ Data Retention: Candidate data auto-purged after 24 months (GDPR)        │
│ Right to Erasure: Automated deletion pipeline via Data Factory            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-hr-talent-intel-dev
    location: eastus
    sku_tier: basic
    pii_encryption: software-key
    data_residency: us-only

  staging:
    subscription: staging-subscription
    resource_group: rg-hr-talent-intel-stg
    location: eastus
    sku_tier: standard
    pii_encryption: hsm-key
    data_residency: us-only

  production:
    subscription: prod-subscription
    resource_group: rg-hr-talent-intel-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    pii_encryption: hsm-key
    data_residency: us-only

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  pre_deploy_checks:
    - pii_scan: true
    - bias_test: true
    - rbac_validation: true

azure_services:
  compute:
    - azure_functions:
        plan: premium-ep2
        runtime: python-3.11
        vnet_integrated: true
    - azure_ml:
        compute: standard-ds3-v2
        nodes: 2

  ai:
    - azure_openai:
        model: gpt-4o-2024-08-06
        deployment: hr-talent-gpt4o
        tpm_quota: 120000
    - azure_openai:
        model: text-embedding-ada-002
        deployment: hr-talent-embeddings
        tpm_quota: 350000
    - document_intelligence:
        tier: s0
        custom_model: resume-parser-v2

  data:
    - cosmos_db:
        api: nosql
        consistency: session
        regions: [eastus, westus2]
    - adls_gen2:
        replication: grs
        hierarchical_namespace: true
    - redis_cache:
        sku: premium-p1
        clustering: enabled
    - ai_search:
        tier: s1
        replicas: 3
        partitions: 2

  security:
    - key_vault:
        sku: premium
        hsm_backed: true
    - private_link:
        services: [openai, search, cosmos, adls, redis, keyvault]
    - managed_identity:
        type: system-assigned
    - entra_id:
        app_roles: [HRAdmin, Recruiter, HiringManager, Employee]

  observability:
    - app_insights:
        sampling: 25
        pii_scrubbing: enabled
    - log_analytics:
        retention_days: 365
        pii_query_audit: true
    - azure_monitor:
        alert_rules:
          - pii_access_anomaly
          - screening_bias_drift
          - model_latency_p95
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go (120K TPM) | ~$3,000-6,000 |
| Azure OpenAI (ada-002) | Pay-as-you-go (350K TPM) | ~$500-1,000 |
| Azure AI Search | S1 (3 replicas, 2 partitions) | ~$1,500 |
| Azure Functions | Premium EP2 | ~$350 |
| Azure ML | DS3v2 (2 nodes) | ~$400 |
| Cosmos DB | Serverless (multi-region) | ~$200 |
| ADLS Gen2 | GRS (2TB) | ~$90 |
| Blob Storage | Hot (500GB, versioned) | ~$15 |
| Redis Cache | P1 Premium | ~$250 |
| Data Factory | Managed VNET runtime | ~$300 |
| Document Intelligence | S0 | ~$150 |
| Key Vault | Premium (HSM) | ~$10 |
| APIM | Standard | ~$150 |
| App Insights + Log Analytics | Pay-as-you-go | ~$150 |
| Azure Monitor | Alerts + metrics | ~$50 |
| Private Link (8 endpoints) | Standard | ~$60 |
| **Total Estimated** | | **~$7,175-10,175** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why GPT-4o for Resume Screening instead of a traditional ML classifier?**
   - GPT-4o understands nuanced job requirements and non-standard resume formats
   - Handles diverse resume structures without retraining (PDF, DOCX, LinkedIn exports)
   - Provides explainable scoring with natural language justification for each decision
   - Easily adapts to new roles/industries via prompt engineering rather than relabeling data

2. **Why Azure AI Search for Talent Matching?**
   - Hybrid search combines keyword matching (exact job titles, certifications) with semantic vectors
   - Skill embeddings enable fuzzy matching ("React" matches "ReactJS", "React.js")
   - Semantic ranker provides cross-encoder reranking for high-precision candidate shortlists
   - Built-in faceting for filtering by location, experience level, availability

3. **Why Cosmos DB over SQL for Candidate Profiles?**
   - Schema flexibility handles varying resume structures and skill taxonomies
   - Multi-region replication for global HR operations with low latency
   - Change feed enables real-time updates to AI Search talent index
   - Serverless mode keeps costs proportional to actual screening volume

4. **How is PII Protected End-to-End?**
   - Document Intelligence extracts structured data; PII detection runs immediately
   - SSN, DOB, address, phone are tokenized and stored separately with CMK encryption
   - AI Search indexes only redacted profiles; GPT-4o never sees raw PII
   - Role-based data masking: recruiters see partial info, hiring managers see anonymized view
   - GDPR right-to-erasure pipeline auto-purges candidate data after 24 months

5. **How Do You Prevent Bias in AI Screening?**
   - Prompts explicitly exclude age, gender, ethnicity, and name from scoring criteria
   - Azure OpenAI content filtering configured with custom bias-detection policies
   - Azure ML monitors screening score distributions for demographic drift
   - Every screening decision is logged with full prompt and reasoning for audit
   - Regular bias testing in CI/CD pipeline before model deployment

6. **Why Azure ML for Workforce Planning?**
   - LightGBM models predict attrition risk using engagement and tenure signals
   - Time-series forecasting for headcount demand by department and skill cluster
   - Integrates with GPT-4o for natural language workforce planning summaries
   - MLflow tracking ensures model versioning and reproducibility

### Scalability Considerations

- AI Search replicas scale read throughput during peak hiring seasons
- Functions Premium plan ensures VNET integration with zero cold starts
- Redis Cache reduces redundant embedding calls for repeated skill lookups
- Cosmos DB auto-scales RUs during bulk resume ingestion campaigns
- Data Factory parallelizes ATS/HRIS sync across multiple source systems
- ADLS Gen2 partitioned by date and department for efficient analytics queries

### Key Metrics & SLAs

- Resume screening latency: < 8 seconds per resume (P95)
- Skill gap analysis response: < 3 seconds (cached), < 10 seconds (uncached)
- Internal mobility match accuracy: > 85% relevance (top-5 candidates)
- System availability: 99.9% uptime SLA
- PII access audit: 100% logged, < 1 hour alert response
- Bias drift detection: weekly automated reports, < 5% variance threshold

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (HR Operations + Talent Management)
- **Visibility:** HR Team + Hiring Managers — human resources and authorized hiring personnel
- **Project Score:** 8.5 / 10 (High)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | OpenAI, Cognitive Search, SQL, Storage via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | HR role hierarchy with need-to-know access |
| Data | PII Protection | Employee/candidate PII encrypted and access-controlled |
| Data | Bias Detection | AI model bias monitoring for protected characteristics |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | HR data encryption keys, integration credentials |
| Application | AI Fairness | Fairness metrics tracked per protected class |
| Application | Anonymization | Candidate data anonymized for initial screening |
| Monitoring | Access Audit | All employee data access logged and reviewed |
| Monitoring | Bias Alerts | Automated alerts for statistical bias in AI outputs |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| EEOC Compliance | Enforced | Equal Employment Opportunity monitoring and reporting |
| NYC LL144 | Compliant | Automated employment decision tool bias audit |
| Labor Law | Aligned | Federal and state labor law compliance |
| AI Transparency | Required | Candidates informed of AI use in hiring process |
| Data Minimization | Enforced | Only job-relevant data collected and processed |
| Retention Limits | Policy-based | Candidate data retained per jurisdiction requirements |

### Regulatory Applicability
- **EEOC Guidelines:** Non-discrimination in AI-assisted hiring
- **NYC Local Law 144:** Bias audit for automated employment decisions
- **GDPR Article 22:** Automated individual decision-making protections
- **CCPA:** California consumer privacy for employee/candidate data
- **Title VII / ADA:** Anti-discrimination in employment practices
- **State AI Laws:** Emerging state-level AI in employment regulations
