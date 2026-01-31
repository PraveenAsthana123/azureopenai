# Project 7: Healthcare Clinical Copilot

## Executive Summary

A HIPAA-compliant clinical decision support system that empowers healthcare professionals with AI-driven insights at the point of care. The platform integrates Azure OpenAI GPT-4o for clinical reasoning, Azure Health Data Services (FHIR R4) for standardized patient data exchange, and Text Analytics for Health for medical Named Entity Recognition (NER). Key capabilities include real-time drug interaction checking, automated patient summary generation from electronic health records, differential diagnosis assistance, and evidence-based treatment recommendations. The system enforces end-to-end PHI protection through encryption, private networking, comprehensive audit trails, and a signed Business Associate Agreement (BAA) with Microsoft Azure, ensuring full compliance with HIPAA, HITECH, and HL7 FHIR interoperability standards.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        HEALTHCARE CLINICAL COPILOT                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Clinician Web  │     │   EHR Plugin    │     │  Mobile App     │
│  Portal (React) │     │  (SMART on FHIR)│     │  (React Native) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL      │
                    │    + Geo-filtering)      │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (Frontend SPA) │   │  (Real-time     │
│   OAuth2, BAA   │   │                 │   │   Alerts)       │
│   Audit Logging)│   │                 │   │                 │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌──────────────────────────────────────────────────────────────┐
         │  │                PRIVATE VNET (10.0.0.0/16)                    │
         │  │  ┌────────────────────────────────────────────────────┐      │
         │  │  │           Application Subnet (10.0.1.0/24)        │      │
         ▼  │  │                                                    │      │
┌───────────┴──┴────┐                                               │      │
│ Azure Functions   │◄────────────────────────────────────────┐     │      │
│ (Clinical Engine) │                                         │     │      │
│                   │    ┌──────────────────┐                  │     │      │
│ - Query Router    │    │  Azure OpenAI    │                  │     │      │
│ - Summary Gen     │◄───┤  (GPT-4o)        │                  │     │      │
│ - Drug Check      │    │  Private Link    │                  │     │      │
│ - Diagnosis Aid   │    │  Content Filter  │                  │     │      │
│ - NER Pipeline    │    └──────────────────┘                  │     │      │
└────────┬──────────┘                                          │     │      │
         │              ┌──────────────────┐                   │     │      │
         ├─────────────►│  Azure AI Search │◄──────────────────┘     │      │
         │              │  (Medical Index)  │                        │      │
         │              │  - Clinical Docs  │                        │      │
         │              │  - Drug Database  │                        │      │
         │              │  - ICD-10 Codes   │                        │      │
         │              └────────┬─────────┘                        │      │
         │                       │                                   │      │
         │  ┌────────────────────┼───────────────────────────────┐  │      │
         │  │           Data Subnet (10.0.2.0/24)                │  │      │
         │  │                    │                                │  │      │
         │  │    ┌───────────────┼───────────────┬──────────┐    │  │      │
         │  │    │               │               │          │    │  │      │
         │  │    ▼               ▼               ▼          ▼    │  │      │
         │  │ ┌──────┐    ┌──────────┐    ┌───────┐  ┌────────┐ │  │      │
         │  │ │ Blob │    │ Cosmos DB│    │ Redis │  │ FHIR   │ │  │      │
         │  │ │Store │    │(Sessions │    │ Cache │  │ Server │ │  │      │
         │  │ │(PHI  │    │ + Audit  │    │(Query │  │(Health │ │  │      │
         │  │ │Docs) │    │ Trails)  │    │ Cache)│  │ Data   │ │  │      │
         │  │ └──────┘    └──────────┘    └───────┘  │Svc R4) │ │  │      │
         │  │                                        └────────┘ │  │      │
         │  └────────────────────────────────────────────────────┘  │      │
         │                                                          │      │
         │  ┌────────────────────────────────────────────────────┐  │      │
         │  │        Integration Subnet (10.0.3.0/24)            │  │      │
         │  │                                                    │  │      │
         │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │  │      │
         │  │  │  Key Vault   │  │ Text         │  │ Drug     │ │  │      │
         │  │  │  (Secrets +  │  │ Analytics    │  │Interact. │ │  │      │
         │  │  │   CMK Keys)  │  │ for Health   │  │  API     │ │  │      │
         │  │  │              │  │ (Medical NER)│  │          │ │  │      │
         │  │  └──────────────┘  └──────────────┘  └──────────┘ │  │      │
         │  └────────────────────────────────────────────────────┘  │      │
         └──────────────────────────────────────────────────────────┘      │
                                                                           │
┌──────────────────────────────────────────────────────────────────────────┘
│
│   ┌──────────────────────────────────────────────────────────────────────┐
│   │              CLINICAL DATA INGESTION PIPELINE                        │
│   │                                                                      │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│   │  │ HL7 FHIR     │  │ EHR Systems  │  │ Clinical Document       │   │
│   │  │ Endpoint     │  │ (Epic/Cerner)│  │ Upload (Blob Drop Zone) │   │
│   │  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│   │         │                  │                       │                │
│   │         └──────────────────┼───────────────────────┘                │
│   │                            ▼                                        │
│   │                  ┌─────────────────┐                                │
│   │                  │  Event Grid     │                                │
│   │                  │  (FHIR Events + │                                │
│   │                  │   Blob Events)  │                                │
│   │                  └────────┬────────┘                                │
│   │                           ▼                                         │
│   │                  ┌─────────────────┐                                │
│   │                  │ Durable Function│                                │
│   │                  │ (Orchestrator)  │                                │
│   │                  └────────┬────────┘                                │
│   │                           │                                         │
│   │        ┌──────────────────┼──────────────────┐                     │
│   │        ▼                  ▼                  ▼                     │
│   │  ┌───────────┐    ┌────────────┐     ┌────────────────┐            │
│   │  │ FHIR      │    │ Medical    │     │ PHI De-ID /    │            │
│   │  │ Resource   │    │ NER        │     │ Anonymization  │            │
│   │  │ Parsing    │    │ Extraction │     │ Pipeline       │            │
│   │  └─────┬─────┘    └─────┬──────┘     └───────┬────────┘            │
│   │        │                 │                    │                     │
│   │        └─────────────────┼────────────────────┘                    │
│   │                          ▼                                          │
│   │                  ┌─────────────────┐                                │
│   │                  │ Embed + Index   │                                │
│   │                  │ (AI Search)     │                                │
│   │                  └─────────────────┘                                │
│   └──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY LAYER                                 │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐    │
│  │ App Insights │  │Log Analytics │  │ Azure Monitor                │    │
│  │ (APM +       │  │ (Centralized │  │ (Metrics + Alerts +          │    │
│  │  PHI Audit)  │  │  HIPAA Logs) │  │  Compliance Dashboard)       │    │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘    │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐    │
│  │ Defender for │  │ Cost Mgmt   │  │ Sentinel (SIEM -             │    │
│  │ Cloud (HIPAA │  │ Dashboard    │  │  PHI Access Anomalies)       │    │
│  │  Benchmark)  │  │              │  │                              │    │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLINICAL QUERY FLOW                                    │
└─────────────────────────────────────────────────────────────────────────┘

    Clinician Query                                       Clinical Response
    (e.g., "Drug interactions                             (Structured answer
     for Patient 12345")                                   with citations)
        │                                                       ▲
        ▼                                                       │
┌───────────────┐                                      ┌───────────────┐
│ 1. APIM Auth  │                                      │ 9. Format +   │
│ (OAuth2 +     │                                      │ PHI Filter    │
│  SMART on FHIR│                                      │ Response      │
│  Scopes)      │                                      └───────┬───────┘
└───────┬───────┘                                              │
        │                                                       │
        ▼                                                       │
┌───────────────┐                                      ┌───────────────┐
│ 2. Audit Log  │                                      │ 8. Generate   │
│ (PHI Access   │                                      │ (GPT-4o with  │
│  Recorded)    │                                      │  Medical      │
└───────┬───────┘                                      │  System Prompt│
        │                                              └───────┬───────┘
        ▼                                                       │
┌───────────────┐                                      ┌───────────────┐
│ 3. Medical    │                                      │ 7. Augment    │
│ NER Extract   │                                      │ Prompt with   │
│ (Text Ana.    │                                      │ FHIR Data +   │
│  for Health)  │                                      │ Search Results│
└───────┬───────┘                                      └───────┬───────┘
        │                                                       │
        ▼                                                       │
┌───────────────┐     ┌───────────────┐               ┌───────────────┐
│ 4. Entity     │     │ 5b. FHIR      │               │ 6. Drug       │
│ Resolution    │────►│ Patient       │──────────────►│ Interaction   │
│ (ICD-10,      │     │ Lookup        │               │ Check API     │
│  RxNorm,      │     │ (Health Data  │               └───────────────┘
│  SNOMED CT)   │     │  Services)    │
└───────┬───────┘     └───────────────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ 5a. Embed     │────►│ Vector Search │
│ Query         │     │ (AI Search -  │
│ (ada-002)     │     │  Clinical KB) │
└───────────────┘     └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                PATIENT DATA INGESTION FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

FHIR Resource / Clinical Document Upload
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. FHIR       │────►│ 2. Event Grid │────►│ 3. Durable    │
│ Server /      │     │ Trigger       │     │ Function      │
│ Blob Storage  │     │               │     │ (Orchestrator)│
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                        ┌────────────────────────────┼──────────────────────┐
                        │                            │                      │
                        ▼                            ▼                      ▼
                  ┌───────────┐              ┌───────────┐          ┌───────────────┐
                  │ 4a. Parse │              │ 4b. NER   │          │ 4c. PHI       │
                  │ FHIR R4   │              │ Extract   │          │ De-Identify   │
                  │ Resources │              │ (Diagnoses│          │ (Safe Harbor  │
                  │           │              │  Meds,    │          │  Method)      │
                  └─────┬─────┘              │  Labs)    │          └───────┬───────┘
                        │                    └─────┬─────┘                  │
                        │                          │                        │
                        └──────────────────────────┼────────────────────────┘
                                                   │
                                                   ▼
                                            ┌───────────┐
                                            │ 5. Chunk  │
                                            │ + Embed   │
                                            │ Clinical  │
                                            │ Content   │
                                            └─────┬─────┘
                                                  │
                                                  ▼
                                            ┌───────────┐
                                            │ 6. Index  │
                                            │ in AI     │
                                            │ Search +  │
                                            │ Cosmos DB │
                                            └───────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Clinician Web Portal | React + TypeScript | Primary clinical decision support interface |
| EHR Plugin | SMART on FHIR | Embedded widget within Epic, Cerner, and other EHR systems |
| Mobile App | React Native | On-call and bedside access for clinicians |
| Real-time Alerts | Azure SignalR | Push notifications for critical drug interaction alerts |

### 2. API Gateway Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Azure Front Door | WAF + CDN + SSL + Geo-filter | Global load balancing, DDoS protection, edge security |
| APIM | OAuth2/JWT + SMART on FHIR scopes | API management, rate limiting, PHI access audit logging |
| API Versioning | APIM Revisions | Backward-compatible API evolution for EHR integrations |

### 3. Application Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Clinical Query Engine | Azure Functions (Python 3.11) | Routes clinical queries, orchestrates AI pipeline |
| Patient Summary Generator | Azure Functions | Generates discharge summaries and clinical narratives |
| Drug Interaction Checker | Azure Functions | Real-time contraindication and interaction detection |
| Diagnosis Assistant | Azure Functions | Differential diagnosis ranking from symptoms |
| Ingestion Orchestrator | Durable Functions | FHIR resource and clinical document processing |

### 4. AI/ML Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Clinical reasoning, summary generation, Q&A |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for clinical knowledge retrieval |
| Text Analytics for Health | Azure AI Language | Medical NER: conditions, medications, dosages, anatomy |
| Azure AI Search | Semantic ranker + Vector index | Hybrid search over clinical guidelines and drug databases |
| Drug Interaction API | Custom + RxNorm integration | Medication contraindication and severity scoring |

### 5. Data Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Azure Health Data Services | FHIR R4 Server | Standardized patient data (conditions, meds, labs, encounters) |
| Cosmos DB | Multi-region, serverless | Session state, audit trails, clinical interaction history |
| Azure Blob Storage | Hot tier, CMK encryption | PHI documents, clinical notes, imaging reports |
| Azure AI Search | S2 tier, 3 replicas | Vector index for clinical guidelines, ICD-10, RxNorm |
| Redis Cache | P1 Premium, VNET-injected | Frequently accessed patient context, drug lookup cache |

### 6. Security Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Key Vault | RBAC + soft delete + CMK | Secrets, certificates, customer-managed encryption keys |
| Private Link | All PaaS services | Zero public endpoint exposure for PHI workloads |
| Managed Identity | System-assigned | Passwordless service-to-service authentication |
| Entra ID | OAuth2/OIDC + SMART on FHIR | Clinician SSO, role-based clinical data access |
| Defender for Cloud | HIPAA/HITRUST benchmark | Continuous compliance monitoring, vulnerability scanning |
| PHI Audit Trail | Cosmos DB + Log Analytics | Immutable record of every PHI access event |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│              HIPAA-COMPLIANT SECURITY LAYERS                              │
│              (BAA signed with Microsoft Azure)                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2 │  │ Protection  │  │ (US-only for    │  │
│ │             │  │  + Custom   │  │ Standard    │  │  PHI residency) │  │
│ │             │  │  Health     │  │             │  │                 │  │
│ │             │  │  Rules)     │  │             │  │                 │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS (HIPAA Access Controls)                       │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO +      │  │ Access      │  │ Required    │  │  time access    │  │
│ │  SMART on   │  │ (Device     │  │ for all PHI │  │  for admin      │  │
│ │  FHIR)      │  │  Compliant) │  │  access)    │  │  operations)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│ ┌─────────────┐  ┌─────────────┐                                        │
│ │ RBAC Roles  │  │ Break-Glass │                                        │
│ │ (Physician, │  │ Emergency   │                                        │
│ │  Nurse, Lab,│  │ Access with │                                        │
│ │  Admin)     │  │ Full Audit  │                                        │
│ └─────────────┘  └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY (Zero Trust)                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Deny-all   │  │ Endpoints   │  │ Endpoints       │  │
│ │ (3 Subnets) │  │  default,   │  │ (All PaaS   │  │ (FHIR Server,  │  │
│ │             │  │  Least Priv)│  │  services)  │  │  OpenAI)        │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY (PHI Protection)                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ PHI De-     │  │ Data Loss       │  │
│ │ at Rest     │  │ (CMK for    │  │ Identifica- │  │ Prevention      │  │
│ │ (AES-256)   │  │  all PHI    │  │ tion (Safe  │  │ (DLP Policies   │  │
│ │ + Transit   │  │  stores)    │  │  Harbor)    │  │  for PHI)       │  │
│ │ (TLS 1.3)   │  │             │  │             │  │                 │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│ ┌─────────────┐  ┌─────────────┐                                        │
│ │ Backup      │  │ Data        │                                        │
│ │ Encryption  │  │ Retention   │                                        │
│ │ (Geo-       │  │ (7yr HIPAA  │                                        │
│ │  redundant) │  │  minimum)   │                                        │
│ └─────────────┘  └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain │  │ Throttling  │  │ Filtering       │  │
│ │ (No secrets │  │  per FHIR   │  │ (Per-user   │  │ (Azure OpenAI   │  │
│ │  in code)   │  │  resource)  │  │  + per-role)│  │  safety layer)  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│ ┌─────────────┐  ┌─────────────┐                                        │
│ │ Input       │  │ PHI Output  │                                        │
│ │ Sanitiza-   │  │ Filtering   │                                        │
│ │ tion        │  │ (Prevent    │                                        │
│ │             │  │  PHI leaks) │                                        │
│ └─────────────┘  └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE (HIPAA Audit Requirements)              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ PHI Access  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM -     │  │ Audit Logs  │  │ Manager         │  │
│ │ (HIPAA/     │  │  anomaly    │  │ (Immutable  │  │ (HIPAA +        │  │
│ │  HITRUST    │  │  detection  │  │  7yr        │  │  HITRUST        │  │
│ │  benchmark) │  │  for PHI)   │  │  retention) │  │  assessments)   │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
│ ┌─────────────┐  ┌─────────────┐                                        │
│ │ Breach      │  │ Automated   │                                        │
│ │ Notification│  │ Compliance  │                                        │
│ │ Workflow    │  │ Reporting   │                                        │
│ │ (60-day     │  │ (Quarterly) │                                        │
│ │  HIPAA req) │  │             │                                        │
│ └─────────────┘  └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy
# HIPAA-Compliant Healthcare Clinical Copilot

environments:
  development:
    subscription: dev-healthcare-subscription
    resource_group: rg-clinical-copilot-dev
    location: eastus
    sku_tier: basic
    phi_data: false  # Synthetic data only
    baa_required: false
    network:
      vnet_cidr: "10.0.0.0/16"
      private_endpoints: false

  staging:
    subscription: staging-healthcare-subscription
    resource_group: rg-clinical-copilot-stg
    location: eastus
    sku_tier: standard
    phi_data: true  # De-identified PHI for testing
    baa_required: true
    network:
      vnet_cidr: "10.1.0.0/16"
      private_endpoints: true
    compliance:
      hipaa_audit: enabled
      defender_benchmark: hipaa-hitrust

  production:
    subscription: prod-healthcare-subscription
    resource_group: rg-clinical-copilot-prod
    location: eastus
    secondary_location: westus2  # DR - paired region
    sku_tier: premium
    phi_data: true
    baa_required: true
    network:
      vnet_cidr: "10.2.0.0/16"
      private_endpoints: true
      nsg_flow_logs: enabled
    compliance:
      hipaa_audit: enabled
      defender_benchmark: hipaa-hitrust
      sentinel_siem: enabled
      data_retention_years: 7
      breach_notification_workflow: enabled

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 5  # Conservative for healthcare
  health_check_path: /health
  smoke_tests:
    - fhir_connectivity
    - openai_endpoint
    - drug_interaction_api
    - ner_pipeline
  approval_gates:
    staging_to_prod: manual  # Required for HIPAA change control
    security_scan: required
    hipaa_checklist: required
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go (200K tokens/day) | ~$3,000-6,000 |
| Azure Health Data Services (FHIR) | Standard (10K transactions/day) | ~$1,200 |
| Azure AI Search | S2 (3 replicas) | ~$1,500 |
| Text Analytics for Health | Standard (50K records/mo) | ~$500 |
| Azure Functions | Premium EP2 (VNET integrated) | ~$350 |
| Cosmos DB | Provisioned (10K RU/s, multi-region) | ~$600 |
| Azure Blob Storage | Hot (2TB, CMK encrypted) | ~$50 |
| Redis Cache | P1 Premium (VNET injected) | ~$250 |
| Key Vault | Premium (HSM-backed for PHI) | ~$30 |
| APIM | Standard | ~$150 |
| Application Insights | Pay-as-you-go | ~$150 |
| Log Analytics | Pay-as-you-go (7yr retention) | ~$300 |
| Azure Monitor + Sentinel | Pay-as-you-go | ~$200 |
| Defender for Cloud | Standard (HIPAA benchmark) | ~$100 |
| Private Link (8 endpoints) | Standard | ~$60 |
| Azure Front Door | Standard | ~$100 |
| **Total Estimated** | | **~$8,500-11,500** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why Azure Health Data Services (FHIR) as the patient data layer?**
   - FHIR R4 is the industry standard for healthcare interoperability mandated by CMS and ONC
   - Native integration with Epic, Cerner, and other major EHR systems via SMART on FHIR
   - Built-in HIPAA compliance with BAA coverage from Microsoft
   - Enables standardized access to patient conditions, medications, labs, and encounters

2. **Why Text Analytics for Health for medical NER instead of custom models?**
   - Pre-trained on millions of clinical documents with FDA-grade accuracy
   - Recognizes medical entities: conditions (ICD-10), medications (RxNorm), dosages, anatomy (SNOMED CT)
   - Negation detection (e.g., "no signs of pneumonia") prevents false positives
   - Managed service eliminates model training and MLOps overhead in a regulated environment

3. **Why GPT-4o with RAG instead of fine-tuning for clinical use?**
   - RAG provides grounded, citation-backed clinical recommendations that clinicians can verify
   - Clinical guidelines update frequently; RAG avoids expensive retraining cycles
   - System prompts enforce medical disclaimers, scope boundaries, and hallucination reduction
   - Content filtering prevents generation of harmful medical advice

4. **Why a separate Drug Interaction API?**
   - Drug-drug interactions require deterministic, rule-based checking (not probabilistic LLM output)
   - RxNorm integration provides FDA-recognized drug identifiers and interaction databases
   - Severity scoring (contraindicated, major, moderate, minor) follows clinical pharmacology standards
   - Liability and patient safety require auditable, explainable interaction results

5. **Why Customer-Managed Keys (CMK) for all data stores?**
   - HIPAA requires encryption of PHI at rest with organization-controlled keys
   - CMK in Key Vault (HSM-backed) gives the healthcare organization full key lifecycle control
   - Enables crypto-shredding: revoking the key renders all PHI permanently unreadable
   - Satisfies auditor requirements for encryption key management documentation

6. **Why Cosmos DB for audit trails instead of Log Analytics alone?**
   - Immutable audit records with TTL disabled ensure 7-year HIPAA retention
   - Low-latency queries for real-time PHI access monitoring dashboards
   - Multi-region replication guarantees audit trail survives regional failures
   - Structured JSON documents support complex compliance reporting queries

### Scalability Considerations

- **AI Search S2 tier with 3 replicas** handles concurrent clinical queries from hundreds of simultaneous users across hospital departments
- **Azure Functions Premium EP2** provides VNET integration, no cold starts, and pre-warmed instances for sub-second clinical response times
- **Redis Cache** reduces FHIR server load by caching frequently accessed patient context (with configurable TTL to reflect data freshness requirements)
- **Cosmos DB multi-region** enables active-active deployment for disaster recovery with RPO < 5 minutes for audit trail data
- **FHIR Server auto-scaling** handles burst loads during shift changes and morning rounds when clinician activity peaks
- **APIM rate limiting per role** ensures that batch analytics workloads do not starve real-time clinical decision support queries
- **Event Grid + Durable Functions** decouples ingestion from query serving, allowing large EHR data imports without degrading clinical query performance
- **Horizontal scaling of NER pipeline** via Azure Functions consumption plan handles variable volumes of clinical document ingestion

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2C / B2B (Clinical Staff + Patient Portal)
- **Visibility:** Clinical Staff + Patient Portal — healthcare providers and patient-facing features
- **Project Score:** 9.5 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated healthcare VNet, NSG rules, no public endpoints |
| Network | Private Link | FHIR API, OpenAI, Cosmos DB, Storage via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all Azure services |
| Identity | RBAC + ABAC | Role-based + attribute-based access for clinical roles |
| Data | PHI Encryption | AES-256 at rest, TLS 1.3 in transit for all PHI |
| Data | Break-Glass Access | Emergency access with full audit trail and auto-revocation |
| Data | De-identification | HIPAA Safe Harbor / Expert Determination for research data |
| Data | Key Vault | CMK for PHI encryption, certificate management |
| Application | BAA Compliance | Business Associate Agreements with all data processors |
| Application | Minimum Necessary | PHI access scoped to minimum necessary for clinical role |
| Monitoring | HIPAA Audit Logs | Immutable audit trail for all PHI access events |
| Monitoring | Sentinel | Security event correlation with healthcare threat intelligence |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| HIPAA Compliance | Enforced | Full HIPAA Privacy, Security, and Breach Notification Rules |
| BAA Management | Required | Business Associate Agreements with all third-party processors |
| PHI Minimum Necessary | Enforced | Access scoped to minimum data needed for clinical function |
| Data Retention | 6 years | PHI retained per HIPAA §164.530(j) minimum retention |
| Breach Notification | Automated | 60-day breach notification workflow per HIPAA §164.404 |
| Clinical AI Governance | FDA-aware | AI/ML model governance aligned with FDA SaMD guidance |

### Regulatory Applicability
- **HIPAA Privacy Rule:** Protected Health Information handling and disclosure
- **HIPAA Security Rule:** Administrative, physical, and technical safeguards
- **HITECH Act:** Breach notification and meaningful use requirements
- **FDA SaMD:** Software as Medical Device guidance for clinical AI
- **21 CFR Part 11:** Electronic records and signatures compliance
- **State Health Laws:** State-specific health data privacy requirements
