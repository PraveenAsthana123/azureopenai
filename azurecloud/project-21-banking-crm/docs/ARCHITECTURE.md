# Project 21: Banking CRM Solution

## Executive Summary

An AI-powered Banking CRM platform designed for enterprise financial institutions to deliver unified customer relationship management across all banking product lines. The system provides a Customer 360 view spanning deposits, loans, credit cards, and investment portfolios, enabling relationship managers with AI-driven next-best-action recommendations, churn prediction models, and a GenAI-powered copilot. The platform automates KYC/AML compliance workflows, performs real-time customer sentiment analysis, generates cross-sell/upsell propensity scores, and produces regulatory reports compliant with Basel III/IV frameworks. Built on Azure with strict PCI DSS and SOX compliance, the solution processes millions of customer interactions daily while maintaining the highest standards of financial data security and auditability.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         BANKING CRM SOLUTION - AI-POWERED PLATFORM                    │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   RM Portal     │     │ Customer Self-  │     │  Branch Kiosk   │
│  (React/Next.js)│     │ Service Portal  │     │  (Embedded App) │
│  - Client Mgmt  │     │ (Angular SPA)   │     │  - Queue Mgmt   │
│  - Pipeline     │     │ - Account View  │     │  - Quick Service │
│  - Copilot Chat │     │ - Support Chat  │     │  - ID Verify    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL +    │
                    │    Geo-filtering)       │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Entra ID       │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (OAuth2/OIDC,  │   │  (Real-time     │
│   Auth, Policies│   │   RBAC, MFA)    │   │   Notifications)│
│   PCI Headers)  │   │                 │   │                 │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌────────────────────────────────────────────────────────────────────┐
         │  │                    PRIVATE VNET (10.0.0.0/16)                       │
         │  │                                                                     │
         │  │  ┌──────────────────────────────────────────────────────────────┐   │
         │  │  │              Application Subnet (10.0.1.0/24)                │   │
         ▼  │  │                                                              │   │
┌───────────┴──┴──────┐                                                       │   │
│  Azure Functions    │    ┌──────────────────┐    ┌──────────────────┐        │   │
│  (CRM Orchestrator) │    │  Azure OpenAI    │    │  Azure ML        │        │   │
│                     │    │  (GPT-4o)        │    │  (ML Workspace)  │        │   │
│  - Customer API     │◄───┤  - RM Copilot    │    │  - Churn Model   │        │   │
│  - NBA Engine       │    │  - Sentiment     │    │  - Propensity    │        │   │
│  - KYC Workflow     │    │  - Summarization │    │  - Risk Scoring  │        │   │
│  - Compliance API   │    │  Private Link    │    │  - CLV Prediction│        │   │
│  - Campaign Mgmt    │    └──────────────────┘    └────────┬─────────┘        │   │
└────────┬────────────┘                                     │                  │   │
         │                  ┌──────────────────┐            │                  │   │
         ├─────────────────►│  Azure AI Search │◄───────────┘                  │   │
         │                  │  (Customer KB)   │                               │   │
         │                  │  - Product Docs  │                               │   │
         │                  │  - Policy Search │                               │   │
         │                  │  - FAQ Semantic  │                               │   │
         │                  └──────────────────┘                               │   │
         │                                                                     │   │
         │  ┌──────────────────────────────────────────────────────────────┐   │   │
         │  │                 Data Subnet (10.0.2.0/24)                    │   │   │
         │  │                                                              │   │   │
         │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │   │
         │  │  │  Cosmos DB   │  │  Redis Cache │  │  ADLS Gen2       │   │   │   │
         │  │  │  (Customer   │  │  (Session,   │  │  (Data Lake)     │   │   │   │
         │  │  │   Profiles,  │  │   NBA Cache, │  │  - Raw Zone      │   │   │   │
         │  │  │   Interact-  │  │   Customer   │  │  - Curated Zone  │   │   │   │
         │  │  │   ions, KYC) │  │   360 Cache) │  │  - Analytics Zone│   │   │   │
         │  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │   │
         │  │                                                              │   │   │
         │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │   │
         │  │  │  Blob Storage│  │  Synapse      │  │  Purview         │   │   │   │
         │  │  │  (Documents, │  │  Analytics   │  │  (Data Catalog,  │   │   │   │
         │  │  │   KYC Docs,  │  │  (Regulatory │  │   Lineage,       │   │   │   │
         │  │  │   Reports)   │  │   Reporting) │  │   Classification)│   │   │   │
         │  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │   │
         │  └──────────────────────────────────────────────────────────────┘   │   │
         │                                                                     │   │
         │  ┌──────────────────────────────────────────────────────────────┐   │   │
         │  │            Integration Subnet (10.0.3.0/24)                  │   │   │
         │  │                                                              │   │   │
         │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │   │
         │  │  │  Event Hub   │  │  Stream       │  │  Data Factory    │   │   │   │
         │  │  │  (Customer   │  │  Analytics   │  │  (ETL from Core  │   │   │   │
         │  │  │   Events,    │  │  (Real-time  │  │   Banking, Card  │   │   │   │
         │  │  │   Txn Stream)│  │   Scoring)   │  │   Systems, Loans)│   │   │   │
         │  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │   │
         │  │                                                              │   │   │
         │  │  ┌──────────────┐  ┌──────────────┐                         │   │   │
         │  │  │  Key Vault   │  │  Power BI    │                         │   │   │
         │  │  │  (Secrets,   │  │  (Dashboards,│                         │   │   │
         │  │  │   Certs, CMK)│  │   Basel III/ │                         │   │   │
         │  │  │              │  │   IV Reports)│                         │   │   │
         │  │  └──────────────┘  └──────────────┘                         │   │   │
         │  └──────────────────────────────────────────────────────────────┘   │   │
         └────────────────────────────────────────────────────────────────────┘   │
                                                                                  │
┌─────────────────────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────────────────┐
│   │                        OBSERVABILITY LAYER                               │
│   │                                                                          │
│   │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  │ App Insights│  │ Log Analytics│  │ Azure Monitor│  │ Defender for │  │
│   │  │ (APM,       │  │ (Centralized │  │ (Metrics,    │  │ Cloud        │  │
│   │  │  Tracing)   │  │  Logs, KQL)  │  │  Alerts)     │  │ (Security)   │  │
│   │  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│   └─────────────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────────────────┐
│   │                     EXTERNAL INTEGRATIONS                                │
│   │                                                                          │
│   │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  │ Core Banking│  │ Card Mgmt    │  │ Loan Orig.   │  │ Investment   │  │
│   │  │ System      │  │ System       │  │ System       │  │ Platform     │  │
│   │  │ (Temenos/   │  │ (Marqeta/    │  │ (Finastra/   │  │ (Wealth Mgmt │  │
│   │  │  Finacle)   │  │  Fiserv)     │  │  FIS)        │  │  Platform)   │  │
│   │  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│   └─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     FLOW 1: CUSTOMER ONBOARDING                               │
└──────────────────────────────────────────────────────────────────────────────┘

    New Customer Application
          │
          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. APIM Auth    │────►│ 2. KYC/AML      │────►│ 3. Document     │
│ (mTLS + JWT)    │     │ Workflow Engine  │     │ Intelligence    │
│                 │     │ (Azure Functions)│     │ (ID Extraction) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                         ┌────────────────────────────────┼────────────────┐
                         │                                │                │
                         ▼                                ▼                ▼
                  ┌───────────────┐              ┌──────────────┐  ┌────────────┐
                  │ 4a. AML       │              │ 4b. Identity │  │ 4c. Risk   │
                  │ Screening     │              │ Verification │  │ Assessment │
                  │ (Watchlists)  │              │ (Biometric)  │  │ (ML Model) │
                  └───────┬───────┘              └──────┬───────┘  └──────┬─────┘
                          │                             │                 │
                          └─────────────────────────────┼─────────────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │ 5. Create Profile│
                                               │ (Cosmos DB +     │
                                               │  Customer 360)   │
                                               └────────┬─────────┘
                                                        │
                                               ┌────────▼─────────┐
                                               │ 6. Welcome       │
                                               │ Campaign Trigger │
                                               │ (Event Hub)      │
                                               └──────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│                FLOW 2: NEXT-BEST-ACTION RECOMMENDATION                        │
└──────────────────────────────────────────────────────────────────────────────┘

    RM Opens Customer Profile
          │
          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Load         │────►│ 2. Aggregate    │────►│ 3. Real-time    │
│ Customer 360    │     │ Transaction     │     │ Feature Store   │
│ (Cosmos DB +    │     │ History         │     │ (Redis Cache)   │
│  Redis Cache)   │     │ (Synapse Query) │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────┐
                                               │ 4. Propensity   │
                                               │ Scoring Engine  │
                                               │ (Azure ML)      │
                                               │ - Cross-sell    │
                                               │ - Upsell        │
                                               │ - Churn Risk    │
                                               └────────┬────────┘
                                                        │
                         ┌──────────────────────────────┼──────────────────┐
                         │                              │                  │
                         ▼                              ▼                  ▼
                  ┌───────────────┐           ┌──────────────┐   ┌──────────────┐
                  │ 5a. Product   │           │ 5b. Retention│   │ 5c. GPT-4o   │
                  │ Recommend.    │           │ Actions      │   │ Personalized │
                  │ (ML Model)    │           │ (Churn Risk) │   │ Talking Points│
                  └───────┬───────┘           └──────┬───────┘   └──────┬───────┘
                          │                          │                  │
                          └──────────────────────────┼──────────────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ 6. NBA Card      │
                                            │ Display in       │
                                            │ RM Portal        │
                                            └──────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│                   FLOW 3: KYC/AML COMPLIANCE                                  │
└──────────────────────────────────────────────────────────────────────────────┘

    Scheduled / Event-Triggered Review
          │
          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 1. Customer     │────►│ 2. Data Factory │────►│ 3. AML          │
│ Risk Trigger    │     │ Pull Latest     │     │ Transaction     │
│ (Event Hub /    │     │ Records (Core   │     │ Monitoring      │
│  Timer Trigger) │     │ Banking ETL)    │     │ (Stream Analyt.)│
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────┐
                                               │ 4. Anomaly      │
                                               │ Detection       │
                                               │ (Azure ML +     │
                                               │  Rules Engine)  │
                                               └────────┬────────┘
                                                        │
                                 ┌──────────────────────┼──────────────────┐
                                 │                      │                  │
                                 ▼                      ▼                  ▼
                          ┌────────────┐        ┌────────────┐     ┌────────────┐
                          │ 5a. SAR    │        │ 5b. Case   │     │ 5c. Audit  │
                          │ Filing     │        │ Management │     │ Trail      │
                          │ (Auto-gen) │        │ Queue      │     │ (Immutable │
                          │            │        │            │     │  Log Store)│
                          └────────────┘        └────────────┘     └────────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │ 6. Regulatory    │
                                               │ Report (Basel    │
                                               │ III/IV via       │
                                               │ Power BI)        │
                                               └──────────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| RM Portal | React + Next.js + TypeScript | Relationship manager workspace with customer 360 view, pipeline management, and AI copilot |
| Customer Self-Service | Angular SPA | Customer-facing portal for account overview, support chat, and document upload |
| Branch Kiosk | Embedded React App | In-branch digital touchpoint for queue management, quick services, and ID verification |

### 2. API Gateway Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Azure Front Door | WAF + CDN + SSL + Geo-filtering | Global load balancing, DDoS protection, PCI-compliant edge security |
| APIM Gateway | OAuth2/JWT, mTLS, Rate Limiting | API management, request validation, PCI DSS header enforcement |
| Azure SignalR | Serverless Mode | Real-time notifications for alerts, customer activity, and compliance events |
| Entra ID | OAuth2/OIDC, Conditional Access, MFA | Identity provider with role-based access for RM, compliance, and admin personas |

### 3. Application Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| CRM Orchestrator | Azure Functions (Python 3.11) | Core CRM logic: customer APIs, NBA engine, campaign management |
| KYC Workflow Engine | Azure Functions (Durable) | Long-running KYC/AML onboarding and periodic review workflows |
| Compliance API | Azure Functions (.NET 8) | Regulatory reporting endpoints, SAR filing automation, audit trail management |
| Campaign Manager | Azure Functions (Python 3.11) | Retention campaign orchestration, churn intervention triggers |

### 4. AI/ML Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | RM Copilot conversations, customer sentiment analysis, meeting summaries |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for customer knowledge base and semantic search |
| Azure ML - Churn Model | XGBoost / LightGBM | Customer churn prediction with 30/60/90-day risk scores |
| Azure ML - Propensity Model | Neural Network (PyTorch) | Cross-sell/upsell propensity scoring across product lines |
| Azure ML - Risk Scoring | Gradient Boosted Trees | Customer risk assessment for KYC/AML compliance |
| Azure ML - CLV Model | Survival Analysis | Customer lifetime value prediction for segmentation |
| Stream Analytics | Real-time SQL | Real-time scoring of transaction patterns for anomaly detection |
| Azure AI Search | Semantic Ranker + Vector | Customer knowledge base search, product documentation retrieval |

### 5. Data Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Cosmos DB | Multi-region, Strong consistency | Customer profiles, interactions, KYC records, relationship history |
| Redis Cache | P1 Premium, 6GB | Session management, Customer 360 cache, NBA result cache, feature store |
| ADLS Gen2 | Hot/Cool tiers, hierarchical namespace | Data lake with raw, curated, and analytics zones |
| Synapse Analytics | Dedicated SQL Pool (DW200c) | Regulatory reporting, Basel III/IV analytics, historical analysis |
| Blob Storage | Hot tier, immutable storage | KYC documents, compliance reports, customer correspondence |
| Azure AI Search | S1, 3 replicas | Vector index for product knowledge base and policy documents |
| Purview | Standard | Data catalog, lineage tracking, PII classification, governance policies |

### 6. Integration Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Event Hub | Standard, 8 partitions | Real-time customer event streaming (transactions, logins, interactions) |
| Data Factory | Managed VNET IR | ETL pipelines from core banking, card management, loan origination systems |
| Power BI | Premium Per User | Executive dashboards, Basel III/IV reports, campaign performance analytics |
| Stream Analytics | 6 SU | Real-time transaction scoring, anomaly detection, event processing |

### 7. Security Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Key Vault | Premium, HSM-backed | Encryption keys (CMK), certificates, API secrets, connection strings |
| Private Link | All PaaS services | Network isolation, no public internet exposure for data services |
| Managed Identity | System-assigned | Zero-credential service-to-service authentication |
| Entra ID | Conditional Access + PIM | Just-in-time privileged access, MFA enforcement, risk-based policies |
| Purview | Data Classification | Automated PII/financial data discovery, sensitivity labeling |

---

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                 SECURITY LAYERS - PCI DSS & SOX COMPLIANT                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                                   │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Azure Front  │  │ WAF Policy   │  │ DDoS         │  │ Geo-filtering    │   │
│ │ Door         │  │ (OWASP 3.2 + │  │ Protection   │  │ (Restrict to     │   │
│ │              │  │  PCI Custom  │  │ Standard     │  │  Operating       │   │
│ │              │  │  Rules)      │  │              │  │  Regions Only)   │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 1: Install and maintain a firewall configuration                  │
│ PCI DSS Req 6: Develop and maintain secure systems                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                                    │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Entra ID     │  │ Conditional  │  │ MFA          │  │ PIM (Just-in-    │   │
│ │ (SSO + RBAC) │  │ Access       │  │ Enforcement  │  │ Time Access for  │   │
│ │ - RM Role    │  │ (Device +    │  │ (All Users + │  │ Admin/Compliance │   │
│ │ - Compliance │  │  Location +  │  │  Service     │  │ Roles, Time-     │   │
│ │ - Admin      │  │  Risk-based) │  │  Accounts)   │  │ bound Elevation) │   │
│ │ - Auditor    │  │              │  │              │  │                  │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 7: Restrict access to cardholder data by business need-to-know   │
│ PCI DSS Req 8: Identify and authenticate access to system components          │
│ SOX Section 302: Corporate responsibility for financial reports               │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                     │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ VNET         │  │ NSG Rules    │  │ Private Link │  │ Network Watcher  │   │
│ │ Isolation    │  │ (Deny-All    │  │ (All PaaS    │  │ (Flow Logs,      │   │
│ │ (3 Subnets:  │  │  Default,    │  │  Services    │  │  Traffic         │   │
│ │  App/Data/   │  │  Whitelist   │  │  Zero Public │  │  Analytics,      │   │
│ │  Integration)│  │  Required)   │  │  Endpoints)  │  │  Packet Capture) │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 1: Network segmentation between CDE and non-CDE                  │
│ PCI DSS Req 2: Do not use vendor-supplied defaults                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY                                                        │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Encryption   │  │ Key Vault    │  │ Dynamic Data │  │ Purview          │   │
│ │ at Rest:     │  │ (HSM-backed  │  │ Masking      │  │ (Auto PII        │   │
│ │  AES-256     │  │  CMK, Auto-  │  │ (SSN, Acct#, │  │  Discovery,      │   │
│ │ In Transit:  │  │  Rotation)   │  │  Card PAN,   │  │  Sensitivity     │   │
│ │  TLS 1.3     │  │              │  │  DOB Masking)│  │  Labels, Data    │   │
│ │              │  │              │  │              │  │  Lineage)        │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 3: Protect stored cardholder data (PAN encryption/masking)        │
│ PCI DSS Req 4: Encrypt transmission of cardholder data across open networks   │
│ SOX Section 404: Internal controls over financial reporting data integrity    │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                                 │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Managed      │  │ RBAC         │  │ API          │  │ Content          │   │
│ │ Identity     │  │ (Fine-grain  │  │ Throttling   │  │ Filtering        │   │
│ │ (Zero Creds  │  │  Per-Field   │  │ (Per-User,   │  │ (Azure OpenAI    │   │
│ │  in Code,    │  │  Access to   │  │  Per-Product │  │  Responsible AI, │   │
│ │  Auto-Rotate)│  │  PII/Fin.    │  │  Rate Limits)│  │  PII Redaction   │   │
│ │              │  │  Data)       │  │              │  │  in Prompts)     │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 6: Secure application development lifecycle (SDLC)                │
│ PCI DSS Req 10: Log and monitor all access to cardholder data                 │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING, AUDIT & COMPLIANCE                                       │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Defender for │  │ Sentinel     │  │ Immutable    │  │ Compliance       │   │
│ │ Cloud        │  │ (SIEM/SOAR,  │  │ Audit Logs   │  │ Manager          │   │
│ │ (Threat      │  │  Automated   │  │ (365-day     │  │ (PCI DSS, SOX,   │   │
│ │  Detection,  │  │  Playbooks,  │  │  Retention,  │  │  GDPR, Basel     │   │
│ │  Vuln Scan)  │  │  Correlation)│  │  Tamper-     │  │  III/IV Assess-  │   │
│ │              │  │              │  │  proof WORM) │  │  ment Dashboard) │   │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                                               │
│ PCI DSS Req 10: Track and monitor all access to network resources             │
│ PCI DSS Req 11: Regularly test security systems and processes                 │
│ SOX Section 802: Criminal penalties for altering documents (immutable logs)   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy - Banking CRM Solution

environments:
  development:
    subscription: dev-banking-crm-subscription
    resource_group: rg-banking-crm-dev
    location: eastus
    sku_tier: basic
    features:
      - synthetic_data_only
      - relaxed_network_rules
      - shared_openai_endpoint
    cosmos_db:
      consistency: session
      throughput: serverless
    redis: C1_basic

  staging:
    subscription: staging-banking-crm-subscription
    resource_group: rg-banking-crm-stg
    location: eastus
    sku_tier: standard
    features:
      - anonymized_production_data
      - full_network_isolation
      - dedicated_openai_endpoint
      - pci_dss_controls_enabled
    cosmos_db:
      consistency: bounded_staleness
      throughput: autoscale_4000RU
    redis: P1_premium

  uat:
    subscription: uat-banking-crm-subscription
    resource_group: rg-banking-crm-uat
    location: eastus
    sku_tier: standard
    features:
      - full_compliance_testing
      - penetration_testing_enabled
      - sox_audit_controls
      - regulatory_report_validation
    cosmos_db:
      consistency: strong
      throughput: autoscale_8000RU
    redis: P1_premium

  production:
    subscription: prod-banking-crm-subscription
    resource_group: rg-banking-crm-prod
    location: eastus
    secondary_location: westus2
    sku_tier: premium
    features:
      - multi_region_active_passive
      - full_pci_dss_sox_compliance
      - immutable_audit_logging
      - hsm_backed_encryption
      - break_glass_emergency_access
    cosmos_db:
      consistency: strong
      throughput: autoscale_20000RU
      multi_region: true
    redis: P3_premium_clustered
    synapse: DW200c_dedicated

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 5
  health_check_path: /health
  approval_gates:
    - security_scan_passed
    - compliance_check_passed
    - performance_baseline_met
    - data_protection_validated
  rollback_triggers:
    - error_rate_threshold: 1%
    - latency_p99_threshold: 3000ms
    - compliance_violation_detected: true

ci_cd_pipeline:
  provider: Azure DevOps
  stages:
    - build_and_unit_test
    - sast_scan (Checkmarx)
    - container_scan (Trivy)
    - deploy_to_dev
    - integration_tests
    - deploy_to_staging
    - pci_compliance_scan
    - performance_tests
    - deploy_to_uat
    - sox_audit_validation
    - manual_approval (Change Advisory Board)
    - deploy_to_production
    - smoke_tests
    - monitoring_validation
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go (500K req/mo) | ~$4,000-8,000 |
| Azure ML Workspace | Standard (4 models deployed) | ~$1,500 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions | Premium EP2 (3 instances) | ~$600 |
| Cosmos DB | Autoscale 20,000 RU, multi-region | ~$2,500 |
| Event Hub | Standard (8 partitions, 20 TU) | ~$500 |
| Stream Analytics | 6 Streaming Units | ~$450 |
| Data Factory | Managed VNET IR, 500 activities/day | ~$400 |
| ADLS Gen2 | Hot/Cool (5 TB) | ~$200 |
| Synapse Analytics | DW200c Dedicated Pool | ~$1,800 |
| Redis Cache | P3 Premium Clustered (26 GB) | ~$800 |
| Blob Storage | Hot (2 TB) + Immutable | ~$50 |
| Key Vault | Premium HSM-backed | ~$50 |
| APIM | Standard | ~$150 |
| Power BI | Premium Per User (20 users) | ~$400 |
| Application Insights | Pay-as-you-go (50 GB/mo) | ~$150 |
| Log Analytics | Pay-as-you-go (100 GB/mo) | ~$300 |
| Azure Monitor | Metrics + Alerts | ~$100 |
| Purview | Standard | ~$500 |
| Private Link | 15 endpoints | ~$150 |
| Azure Front Door | Premium | ~$350 |
| Defender for Cloud | Plan 2 | ~$200 |
| **Total Estimated** | | **~$15,100-19,100** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why Cosmos DB for Customer Profiles over SQL?**
   - Schema flexibility for diverse banking products (deposits, loans, cards, investments) with varying attribute sets
   - Multi-region replication with strong consistency for financial data integrity
   - Sub-10ms reads for Customer 360 real-time assembly
   - Change feed enables event-driven architecture for downstream NBA and compliance systems

2. **Why a Dedicated Churn Model vs. Generic AI?**
   - Banking churn has domain-specific signals (declining balances, reduced login frequency, competitor rate shopping)
   - Custom XGBoost model trained on historical attrition data yields 92% AUC vs. generic approaches at 78%
   - Explainability requirements for regulatory scrutiny (SHAP values for model interpretability)
   - 30/60/90-day prediction windows enable tiered retention strategies

3. **Why Event Hub + Stream Analytics for Real-time Scoring?**
   - Transaction velocity patterns require sub-second anomaly detection for AML compliance
   - Event Hub handles 1M+ events/second with ordered processing per partition (customer key)
   - Stream Analytics provides windowed aggregations (tumbling, hopping) for pattern detection
   - Decouples event ingestion from processing, enabling replay for audit and investigation

4. **Why Separate KYC/AML Workflow as Durable Functions?**
   - KYC onboarding involves multi-step orchestration (document verification, watchlist screening, risk scoring) that can span hours or days
   - Durable Functions provide checkpoint/resume for long-running workflows
   - Built-in retry policies for external API calls (identity verification, sanctions screening)
   - Human-in-the-loop approval patterns for high-risk customer escalations

5. **Why GPT-4o as RM Copilot Instead of Fine-tuned Model?**
   - Rapid iteration on prompts vs. months-long fine-tuning cycles
   - RAG approach grounds responses in actual customer data and product knowledge base
   - Content filtering and PII redaction in prompts protects sensitive financial data
   - System prompts enforce regulatory language compliance and disclosure requirements

6. **Why Synapse Analytics for Regulatory Reporting?**
   - Basel III/IV reports require complex aggregations across massive datasets (capital adequacy, liquidity ratios)
   - Dedicated SQL pools ensure predictable query performance for regulatory deadlines
   - Native integration with Power BI for auditor-facing dashboards
   - Separation from operational Cosmos DB workload prevents regulatory queries from impacting CRM performance

7. **Security Architecture for Financial Services**
   - PCI DSS compliance requires network segmentation (3-subnet topology isolates cardholder data)
   - SOX compliance demands immutable audit logs with 7-year retention (Blob Storage WORM policy)
   - HSM-backed Key Vault for customer-managed encryption keys (regulatory requirement)
   - Dynamic data masking ensures PAN, SSN, and DOB are never exposed to unauthorized roles

### Scalability Considerations

- **Cosmos DB autoscale** with partition key on customer ID distributes load evenly across 20,000+ RU/s, scaling to 100,000 RU/s during peak hours (month-end, tax season)
- **Redis Cache clustering** provides sub-millisecond Customer 360 reads, reducing Cosmos DB RU consumption by 70% for repeat profile access
- **Event Hub partitioning** on customer ID ensures ordered event processing per customer while parallelizing across 8+ partitions for throughput
- **Azure Functions Premium plan** with pre-warmed instances eliminates cold starts for latency-sensitive NBA scoring and KYC workflows
- **AI Search replicas** (3 minimum) distribute semantic search load for concurrent RM portal queries across product knowledge base
- **Stream Analytics** scales horizontally with streaming units to handle transaction volume spikes during business hours
- **Data Factory** parallelizes ETL pipelines from multiple core banking systems with managed VNET integration runtime for secure data movement
- **Azure ML batch endpoints** pre-compute churn and propensity scores nightly for all customers, with real-time endpoints for on-demand scoring during RM interactions
- **Synapse dedicated pool** pauses during non-business hours and scales up during regulatory reporting windows (quarterly, annually)
- **Multi-region Cosmos DB** with automatic failover provides RPO of zero and RTO under 1 minute for business continuity in financial services

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2C / B2B (Banker Desktop + Customer App)
- **Visibility:** Banker Desktop + Customer App — relationship managers, compliance officers, and retail banking customers
- **Project Score:** 9.5 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | PCI DSS Segmentation | 3-subnet CDE isolation (App/Data/Integration) |
| Network | Private Link | All PaaS services via private endpoints, zero public exposure |
| Identity | KYC/AML Verification | Multi-factor customer identity verification with biometric |
| Identity | PIM Privileged Access | Just-in-time access for compliance and admin roles |
| Data | PCI DSS Encryption | PAN tokenization, AES-256 encryption, TLS 1.3 |
| Data | TDE (Transparent Data Encryption) | All databases encrypted at rest with CMK via HSM |
| Data | Dynamic Data Masking | SSN, PAN, DOB masking for non-privileged roles |
| Data | SOX Immutable Logs | 7-year WORM retention for financial audit trails |
| Application | Content Filtering | PII redaction in Azure OpenAI prompts |
| Application | RBAC Per-Field | Fine-grained field-level access to PII and financial data |
| Monitoring | Sentinel SIEM | Automated playbooks for fraud and compliance alerts |
| Monitoring | Defender for Cloud | Continuous vulnerability scanning and threat detection |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Basel III/IV | Enforced | Capital adequacy, liquidity ratio, and leverage reporting |
| BSA/AML | Enforced | Bank Secrecy Act anti-money laundering program compliance |
| FFIEC | Aligned | Federal Financial Institutions Examination Council guidelines |
| ECOA | Enforced | Equal Credit Opportunity Act — fair lending compliance |
| GLBA | Enforced | Gramm-Leach-Bliley Act — financial privacy rule |
| PCI DSS | Certified | Payment Card Industry Data Security Standard Level 1 |
| SOX | Audited | Sarbanes-Oxley Sections 302, 404, 802 compliance |
| GDPR | Enforced | EU data subject rights for international banking customers |

### Regulatory Applicability
- **Basel III/IV:** Capital adequacy, liquidity coverage ratio, net stable funding ratio
- **BSA/AML:** Suspicious Activity Reports (SAR), Currency Transaction Reports (CTR)
- **FFIEC:** IT examination handbook, cybersecurity assessment tool
- **ECOA / Fair Lending:** Non-discriminatory lending model monitoring
- **GLBA:** Financial privacy rule, safeguards rule, pretexting protection
- **PCI DSS v4.0:** Cardholder data environment protection (12 requirements)
- **SOX:** Internal controls over financial reporting, immutable audit logs
- **GDPR/CCPA:** Cross-border data protection for international customers
