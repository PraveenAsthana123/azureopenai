# Project 16: ESG & Sustainability Reporter

## Executive Summary

An enterprise-grade ESG (Environmental, Social, and Governance) and Sustainability Reporting platform that automates the extraction of ESG data from corporate reports, performs carbon footprint analytics, ensures regulatory compliance with CSRD (Corporate Sustainability Reporting Directive) and TCFD (Task Force on Climate-related Financial Disclosures) frameworks, and leverages Azure OpenAI GPT-4o for GenAI narrative generation. The system ingests sustainability reports, annual filings, and environmental datasets through Azure Document Intelligence, stores structured ESG metrics in Cosmos DB and ADLS Gen2, runs analytics via Synapse Analytics, and produces compliance-ready reports with AI-generated narratives surfaced through Power BI dashboards.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        ESG & SUSTAINABILITY REPORTER PLATFORM                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Web Dashboard  │     │  Power BI       │     │  API Consumers  │
│  (React/Next)   │     │  (Embedded)     │     │  (REST/GraphQL) │
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
│   APIM Gateway  │   │  Static Web App │   │  Power BI       │
│  (Rate Limit,   │   │  (ESG Portal)   │   │  Service        │
│   Auth, Cache)  │   │                 │   │  (Dashboards)   │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)              │
         │  │  ┌─────────────────────────────────────────────┐    │
         │  │  │         Application Subnet                  │    │
         ▼  │  │         (10.0.1.0/24)                       │    │
┌───────────┴──┴───┐                                         │    │
│ Azure Functions  │◄──────────────────────────────────────┐ │    │
│ (ESG Orchestrator)│                                      │ │    │
│                  │    ┌─────────────────┐                 │ │    │
│ - Data Extractor │    │  Azure OpenAI   │                 │ │    │
│ - Compliance Eng │◄───┤  (GPT-4o)       │                 │ │    │
│ - Narrative Gen  │    │  Private Link   │                 │ │    │
│ - Carbon Calc    │    └─────────────────┘                 │ │    │
└────────┬─────────┘                                        │ │    │
         │              ┌─────────────────┐                 │ │    │
         ├─────────────►│  Azure AI Search │◄───────────────┘ │    │
         │              │  (ESG Index)     │                  │    │
         │              │  - Regulation DB │                  │    │
         │              │  - Framework Ref │                  │    │
         │              └────────┬────────┘                  │    │
         │                       │                            │    │
         │  ┌────────────────────┼────────────────────────┐  │    │
         │  │         Data Subnet (10.0.2.0/24)           │  │    │
         │  │                    │                         │  │    │
         │  │    ┌───────────────┼───────────────┐        │  │    │
         │  │    │               │               │        │  │    │
         │  │    ▼               ▼               ▼        │  │    │
         │  │ ┌──────────┐ ┌──────────┐  ┌─────────────┐ │  │    │
         │  │ │ Cosmos DB│ │  ADLS    │  │ Synapse     │ │  │    │
         │  │ │(ESG Data,│ │  Gen2    │  │ Analytics   │ │  │    │
         │  │ │ Metrics) │ │(Raw/Gold)│  │ (SQL Pools) │ │  │    │
         │  │ └──────────┘ └──────────┘  └─────────────┘ │  │    │
         │  │                                             │  │    │
         │  │ ┌──────────┐ ┌──────────┐  ┌─────────────┐ │  │    │
         │  │ │  Blob    │ │ Purview  │  │ Data Factory│ │  │    │
         │  │ │  Storage │ │ (Catalog)│  │ (ETL/ELT)   │ │  │    │
         │  │ └──────────┘ └──────────┘  └─────────────┘ │  │    │
         │  └─────────────────────────────────────────────┘  │    │
         │                                                    │    │
         │  ┌─────────────────────────────────────────────┐  │    │
         │  │     Integration Subnet (10.0.3.0/24)        │  │    │
         │  │                                             │  │    │
         │  │  ┌──────────────┐   ┌─────────────────────┐ │  │    │
         │  │  │  Key Vault   │   │ Document Intel.     │ │  │    │
         │  │  │  (Secrets)   │   │ (PDF/Report Extract)│ │  │    │
         │  │  └──────────────┘   └─────────────────────┘ │  │    │
         │  └─────────────────────────────────────────────┘  │    │
         └────────────────────────────────────────────────────┘    │
                                                                    │
┌───────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │              ESG DATA INGESTION PIPELINE                     │
│   │                                                              │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐       │
│   │  │ Corporate│    │ Public   │    │ Azure Blob       │       │
│   │  │ Reports  │    │ ESG APIs │    │ (Drop Zone)      │       │
│   │  │ (PDF/CSV)│    │ (CDP,GRI)│    │                  │       │
│   │  └─────┬────┘    └────┬─────┘    └────────┬─────────┘       │
│   │        │               │                   │                 │
│   │        └───────────────┼───────────────────┘                 │
│   │                        ▼                                     │
│   │              ┌─────────────────┐                             │
│   │              │  Data Factory   │                             │
│   │              │  (Orchestrator) │                             │
│   │              └────────┬────────┘                             │
│   │                       ▼                                      │
│   │              ┌─────────────────┐                             │
│   │              │ Azure Functions │                             │
│   │              │ (ESG Pipeline)  │                             │
│   │              └────────┬────────┘                             │
│   │                       │                                      │
│   │        ┌──────────────┼──────────────┐                       │
│   │        ▼              ▼              ▼                        │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│   │  │ Doc Intel│  │ ESG      │  │ Carbon       │               │
│   │  │ (Extract)│  │ Metric   │  │ Footprint    │               │
│   │  │          │  │ Parser   │  │ Calculator   │               │
│   │  └──────────┘  └──────────┘  └──────────────┘               │
│   │                       │                                      │
│   │                       ▼                                      │
│   │              ┌─────────────────┐    ┌─────────────────┐      │
│   │              │ ADLS Gen2       │───►│ Synapse         │      │
│   │              │ (Bronze/Silver/ │    │ Analytics       │      │
│   │              │  Gold Layers)   │    │ (Aggregation)   │      │
│   │              └─────────────────┘    └─────────────────┘      │
│   └──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                            │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor           │   │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)        │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ Purview     │  │ Cost Mgmt  │  │ Defender for Cloud      │   │
│  │ (Data Gov)  │  │ Dashboard   │  │ (Security)              │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ESG DATA EXTRACTION FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

    ESG Report (PDF/CSV)                          Structured ESG Metrics
          │                                              ▲
          ▼                                              │
┌───────────────┐                                ┌───────────────┐
│ 1. Blob Store │                                │ 8. Store to   │
│ (Upload)      │                                │ Cosmos DB     │
└───────┬───────┘                                └───────┬───────┘
        │                                                │
        ▼                                                │
┌───────────────┐                                ┌───────────────┐
│ 2. Data       │                                │ 7. Validate   │
│ Factory Trigger│                               │ Against Schema│
└───────┬───────┘                                └───────┬───────┘
        │                                                │
        ▼                                                │
┌───────────────┐                                ┌───────────────┐
│ 3. Document   │                                │ 6. Map to     │
│ Intelligence  │                                │ CSRD/TCFD     │
│ (OCR Extract) │                                │ Framework     │
└───────┬───────┘                                └───────┬───────┘
        │                                                │
        ▼                                                │
┌───────────────┐      ┌───────────────┐        ┌───────────────┐
│ 4. GPT-4o     │─────►│ 5. ESG Metric │───────►│ Carbon        │
│ (Entity       │      │ Extraction    │        │ Calculation   │
│  Extraction)  │      │ (Structured)  │        │ (Scope 1/2/3) │
└───────────────┘      └───────────────┘        └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    REPORT GENERATION FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

Compliance Report Request
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Select     │────►│ 2. Query      │────►│ 3. Aggregate  │
│ Framework     │     │ Cosmos DB /   │     │ via Synapse   │
│ (CSRD/TCFD)   │     │ ADLS Gen2     │     │ Analytics     │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                          ┌──────────────────────────┼────────────────────┐
                          │                          │                    │
                          ▼                          ▼                    ▼
                    ┌───────────┐          ┌───────────────┐     ┌───────────┐
                    │ 4a. AI    │          │ 4b. Chart     │     │ 4c. Gap   │
                    │ Search    │          │ Generation    │     │ Analysis  │
                    │ (Reg Ref) │          │ (Visuals)     │     │ (Missing) │
                    └─────┬─────┘          └─────┬─────┘        └─────┬─────┘
                          │                      │                    │
                          └──────────────────────┼────────────────────┘
                                                 │
                                                 ▼
                                          ┌───────────────┐
                                          │ 5. GPT-4o     │
                                          │ (Narrative    │
                                          │  Generation)  │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │ 6. Assemble   │
                                          │ Final Report  │
                                          │ (PDF/XBRL)    │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │ 7. Power BI   │
                                          │ Dashboard     │
                                          │ Publish       │
                                          └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| ESG Dashboard | React + TypeScript | Main reporting interface and metric visualization |
| Power BI Embedded | Power BI Service | Interactive sustainability dashboards and KPIs |
| API Consumers | REST/GraphQL | Third-party ESG rating integrations (CDP, MSCI) |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL Termination | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits (100 RPM) | API management, ESG endpoint routing |
| Static Web App | React SPA hosting | ESG portal frontend delivery |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| ESG Orchestrator | Azure Functions (Python 3.11) | Core ESG workflow coordination |
| Data Extractor | Azure Functions (Durable) | Document parsing and metric extraction |
| Carbon Calculator | Azure Functions | Scope 1/2/3 emissions computation (GHG Protocol) |
| Narrative Generator | Azure Functions | AI-driven ESG narrative authoring |
| Compliance Engine | Azure Functions | CSRD/TCFD framework validation and gap analysis |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | ESG narrative generation and entity extraction |
| Azure OpenAI | text-embedding-ada-002 | Regulatory document embeddings for retrieval |
| Document Intelligence | prebuilt-layout + custom | PDF/table extraction from sustainability reports |
| AI Search | Semantic ranker (S1) | Regulatory reference search (CSRD, TCFD, GRI) |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Serverless, multi-partition | ESG metrics, compliance scores, audit trail |
| ADLS Gen2 | Hot/Cool tiers, hierarchical NS | Bronze/Silver/Gold lakehouse for ESG data |
| Blob Storage | Hot tier, versioning enabled | Raw report uploads (PDF, CSV, XBRL) |
| Synapse Analytics | Dedicated SQL pool (DW100c) | ESG aggregation, carbon analytics, trend analysis |
| Data Factory | Managed VNET IR | ETL/ELT pipelines for ESG data ingestion |
| Purview | Standard account | Data catalog, lineage, ESG data classification |
| AI Search | S1, 2 replicas | Regulatory framework index, ESG knowledge base |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protect | Secrets, certificates, encryption keys |
| Private Link | All PaaS services | Network isolation, no public endpoints |
| Managed Identity | System-assigned | Zero-credential service-to-service auth |
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication, RBAC for ESG roles |
| Purview | Sensitivity labels | ESG data classification and governance |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
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
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time access)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ Data        │  │ Purview         │  │
│ │ at Rest/    │  │ (CMK)       │  │ Masking     │  │ (ESG Data       │  │
│ │ Transit     │  │             │  │ (PII/ESG)   │  │  Classification)│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (ESG Roles) │  │ Throttling  │  │ Filtering       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (Activity)  │  │ Manager (CSRD)  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-esg-reporter-dev
    location: eastus
    sku_tier: basic
    synapse_pool: none  # use serverless only
    adls_redundancy: LRS

  staging:
    subscription: staging-subscription
    resource_group: rg-esg-reporter-stg
    location: eastus
    sku_tier: standard
    synapse_pool: DW100c
    adls_redundancy: ZRS

  production:
    subscription: prod-subscription
    resource_group: rg-esg-reporter-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    synapse_pool: DW200c
    adls_redundancy: GRS

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  pipeline_validation:
    - esg_data_quality_gate
    - compliance_framework_check
    - carbon_calculation_regression
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$3,000-6,000 |
| Document Intelligence | S0 (Standard) | ~$500 |
| Azure Functions | Premium EP2 | ~$300 |
| Cosmos DB | Serverless (autoscale) | ~$200 |
| Azure AI Search | S1 (2 replicas) | ~$500 |
| ADLS Gen2 | Hot/Cool (5TB) | ~$120 |
| Synapse Analytics | DW200c (dedicated pool) | ~$1,800 |
| Data Factory | Managed VNET IR | ~$250 |
| Blob Storage | Hot (2TB) | ~$40 |
| Power BI Embedded | A2 SKU | ~$750 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Purview | Standard | ~$400 |
| Application Insights | Pay-as-you-go | ~$100 |
| Log Analytics | Pay-as-you-go (50GB/day) | ~$150 |
| Azure Monitor | Alerts + Metrics | ~$50 |
| Private Link | 10 endpoints | ~$75 |
| **Total Estimated** | | **~$8,400-11,400** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why GenAI for ESG Narrative Generation?**
   - CSRD and TCFD require detailed qualitative disclosures alongside quantitative metrics
   - GPT-4o generates consistent, regulation-aligned narrative sections from structured data
   - Human-in-the-loop review ensures accuracy before final submission
   - Reduces manual report authoring effort by 60-70% while maintaining compliance quality

2. **Why Document Intelligence for ESG Data Extraction?**
   - Sustainability reports are typically complex PDFs with tables, charts, and mixed layouts
   - Prebuilt-layout model handles multi-column table extraction critical for emissions data
   - Custom models trained on ESG-specific report formats (GRI, CDP questionnaires)
   - Combined with GPT-4o entity extraction for unstructured narrative sections

3. **Why Lakehouse Architecture (ADLS Gen2 + Synapse)?**
   - ESG data requires Bronze/Silver/Gold medallion layers for progressive enrichment
   - Bronze: raw extracted data; Silver: validated and standardized; Gold: framework-aligned metrics
   - Synapse dedicated pools enable complex carbon footprint aggregation across Scope 1/2/3
   - Supports historical trend analysis required by TCFD climate scenario modeling

4. **Why Cosmos DB for ESG Metrics?**
   - Schema flexibility accommodates diverse ESG frameworks (CSRD, TCFD, GRI, SASB)
   - Multi-partition key design partitions by company, reporting year, and framework
   - Change feed enables real-time compliance score updates when new data arrives
   - Global distribution supports multinational ESG reporting requirements

5. **Why Purview for Data Governance?**
   - ESG data lineage is critical for audit trails and regulatory assurance
   - Automatic classification of sensitive environmental and social metrics
   - Data catalog enables ESG analysts to discover and trust available datasets
   - Supports CSRD requirement for data quality and provenance documentation

6. **Security Considerations**
   - All services behind Private Link (no public endpoints exposed)
   - Managed Identity eliminates credential management across all services
   - Content filtering in Azure OpenAI prevents generation of misleading ESG claims
   - Purview sensitivity labels protect pre-publication ESG data from unauthorized access

### Scalability Considerations

- Synapse Analytics auto-pause for cost optimization during off-peak reporting periods
- Azure Functions Premium plan for VNET integration and zero cold starts during report generation
- ADLS Gen2 hierarchical namespace for efficient partition pruning on large ESG datasets
- Cosmos DB autoscale RU/s to handle spike during quarterly and annual reporting cycles
- Data Factory managed VNET integration runtime for secure, scalable ETL pipelines
- AI Search replicas scale horizontally for concurrent regulatory reference lookups
- Power BI Embedded capacity scales to support concurrent dashboard users during board reviews

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2B / B2E (Public Reporting + Internal Sustainability)
- **Visibility:** Public (Investors) + Internal — investor relations, sustainability team, and board
- **Project Score:** 9.0 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | OpenAI, Cosmos DB, Storage, Purview via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | Role separation: data collectors, analysts, approvers |
| Data | Data Integrity | Checksums and validation for ESG metrics |
| Data | Immutable Audit Logs | Tamper-proof logs for all ESG data submissions |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | ESG data encryption keys, API credentials |
| Application | Data Validation | Multi-stage validation for ESG metric submissions |
| Application | Approval Workflows | Multi-level sign-off for public ESG disclosures |
| Monitoring | Data Lineage | Full traceability from source to published report |
| Monitoring | Sentinel | Security monitoring for ESG data pipeline |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| CSRD Compliance | Aligned | Corporate Sustainability Reporting Directive readiness |
| TCFD Reporting | Implemented | Task Force on Climate-related Financial Disclosures |
| GRI Standards | Followed | Global Reporting Initiative metrics and frameworks |
| SEC Climate Rules | Prepared | SEC climate disclosure rule compliance preparation |
| Data Assurance | Third-party | External assurance for published ESG metrics |
| Greenwashing Prevention | Enforced | Claims validated against source data with audit trail |

### Regulatory Applicability
- **EU CSRD:** Corporate Sustainability Reporting Directive
- **TCFD:** Task Force on Climate-related Financial Disclosures
- **GRI Standards:** Global Reporting Initiative sustainability reporting
- **SEC Climate Rules:** US Securities and Exchange Commission climate disclosure
- **EU Taxonomy:** EU sustainable activities classification system
- **CDP:** Carbon Disclosure Project reporting requirements
