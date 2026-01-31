# Project 19: Compliance Audit Automation

## Executive Summary

An enterprise-grade compliance audit automation platform that leverages Azure OpenAI GPT-4o to automate evidence collection, control testing, audit trail analysis, and GenAI-powered audit report generation. The system continuously monitors Azure environments using Azure Policy and Azure Resource Graph, collects compliance evidence via automated pipelines, and generates comprehensive audit reports aligned with SOC 2 Type II, ISO 27001, NIST 800-53, and PCI DSS frameworks. Azure Document Intelligence extracts structured data from uploaded compliance artifacts, while AI Search enables semantic retrieval across the full evidence corpus for auditor-assisted investigation.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       COMPLIANCE AUDIT AUTOMATION PLATFORM                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Auditor Portal │     │  Executive      │     │  API Consumers  │
│  (React/Next)   │     │  Dashboard      │     │  (GRC Systems)  │
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
│  (Rate Limit,   │   │  (Auditor UI)   │   │  (Real-time     │
│   Auth, Audit)  │   │                 │   │   Notifications)│
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)              │
         │  │  ┌─────────────────────────────────────────────┐    │
         │  │  │         Application Subnet                  │    │
         ▼  │  │         (10.0.1.0/24)                       │    │
┌───────────┴──┴───┐                                         │    │
│ Azure Functions  │◄──────────────────────────────────────┐ │    │
│ (Audit Engine)   │                                       │ │    │
│                  │    ┌─────────────────┐                 │ │    │
│ - Evidence       │    │  Azure OpenAI   │                 │ │    │
│   Collector      │◄───┤  (GPT-4o)       │                 │ │    │
│ - Control Tester │    │  Private Link   │                 │ │    │
│ - Report Gen     │    └─────────────────┘                 │ │    │
│ - Trail Analyzer │                                        │ │    │
└────────┬─────────┘    ┌─────────────────┐                 │ │    │
         │              │  Azure AI Search │◄───────────────┘ │    │
         ├─────────────►│  (Evidence Index)│                  │    │
         │              │  - Hybrid Search │                  │    │
         │              │  - Semantic Rank │                  │    │
         │              └────────┬────────┘                  │    │
         │                       │                            │    │
         │  ┌────────────────────┼────────────────────────┐  │    │
         │  │         Data Subnet (10.0.2.0/24)           │  │    │
         │  │                    │                         │  │    │
         │  │    ┌───────────────┼───────────────┐        │  │    │
         │  │    │               │               │        │  │    │
         │  │    ▼               ▼               ▼        │  │    │
         │  │ ┌──────┐     ┌──────────┐    ┌──────────┐   │  │    │
         │  │ │ Blob │     │ Cosmos DB│    │ Purview  │   │  │    │
         │  │ │Store │     │(Audit    │    │(Data     │   │  │    │
         │  │ │(Evid)│     │ Trails)  │    │ Catalog) │   │  │    │
         │  │ └──────┘     └──────────┘    └──────────┘   │  │    │
         │  └─────────────────────────────────────────────┘  │    │
         │                                                    │    │
         │  ┌─────────────────────────────────────────────┐  │    │
         │  │     Integration Subnet (10.0.3.0/24)        │  │    │
         │  │                                             │  │    │
         │  │  ┌─────────────┐   ┌─────────────────────┐  │  │    │
         │  │  │  Key Vault  │   │ Document Intel.     │  │  │    │
         │  │  │  (Secrets)  │   │ (Evidence Parsing)  │  │  │    │
         │  │  └─────────────┘   └─────────────────────┘  │  │    │
         │  └─────────────────────────────────────────────┘  │    │
         └────────────────────────────────────────────────────┘    │
                                                                   │
┌──────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │            EVIDENCE COLLECTION PIPELINE                      │
│   │                                                              │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│   │  │ Azure Policy │  │ Resource     │  │ Azure Sentinel   │   │
│   │  │ (Compliance  │  │ Graph        │  │ (Security Logs)  │   │
│   │  │  State)      │  │ (Inventory)  │  │                  │   │
│   │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│   │         │                  │                    │            │
│   │         └──────────────────┼────────────────────┘            │
│   │                            ▼                                 │
│   │              ┌──────────────────────┐                        │
│   │              │  Data Factory        │                        │
│   │              │  (Orchestration)     │                        │
│   │              └──────────┬───────────┘                        │
│   │                         │                                    │
│   │          ┌──────────────┼──────────────┐                     │
│   │          ▼              ▼              ▼                     │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────────┐         │
│   │  │ Document   │  │ Log        │  │ Config State   │         │
│   │  │ Intelligence│ │ Analytics  │  │ Snapshots      │         │
│   │  │ (OCR/Parse)│  │ (Query)    │  │ (Resource Graph)│        │
│   │  └────────────┘  └────────────┘  └────────────────┘         │
│   │                         │                                    │
│   │                         ▼                                    │
│   │              ┌──────────────────────┐                        │
│   │              │ Cosmos DB            │                        │
│   │              │ (Evidence Store +    │                        │
│   │              │  Audit Trail)        │                        │
│   │              └──────────────────────┘                        │
│   └──────────────────────────────────────────────────────────────┘
│
│   ┌──────────────────────────────────────────────────────────────┐
│   │            COMPLIANCE MONITORING LAYER                        │
│   │                                                               │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│   │  │ Azure Monitor│  │ Log Analytics│  │ Defender for     │    │
│   │  │ (Metrics/    │  │ (Central     │  │ Cloud (Security  │    │
│   │  │  Alerts)     │  │  Logging)    │  │  Posture)        │    │
│   │  └──────────────┘  └──────────────┘  └──────────────────┘    │
│   │                                                               │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│   │  │ Sentinel     │  │ Cost Mgmt   │  │ Purview          │    │
│   │  │ (SIEM/SOAR)  │  │ Dashboard    │  │ (Data Governance)│    │
│   │  └──────────────┘  └──────────────┘  └──────────────────┘    │
│   └──────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  EVIDENCE COLLECTION FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

  Scheduled Trigger / Policy Event
        │
        ▼
┌───────────────┐                                  ┌───────────────┐
│ 1. Data       │                                  │ 8. Store in   │
│ Factory       │                                  │ Cosmos DB     │
│ Orchestration │                                  │ (Audit Trail) │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. Azure      │                                  │ 7. Classify   │
│ Resource Graph│                                  │ & Tag         │
│ (Inventory)   │                                  │ (Purview)     │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Azure      │──────────────────────────────────│ 6. Normalize  │
│ Policy State  │                                  │ Evidence      │
│ (Compliance)  │                                  │ (Functions)   │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. Log        │─────►│ 5. Document   │─────────►│ Structured    │
│ Analytics     │      │ Intelligence  │          │ Evidence      │
│ (Audit Logs)  │      │ (Parse Certs) │          │ Artifacts     │
└───────────────┘      └───────────────┘          └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                  AUDIT REPORT GENERATION FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

  Auditor Request / Scheduled Report
        │
        ▼
┌───────────────┐                                  ┌───────────────┐
│ 1. APIM Auth  │                                  │ 8. Deliver    │
│ (JWT/OAuth2 + │                                  │ Report (PDF/  │
│  Audit Role)  │                                  │ Word/Blob)    │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. Framework  │                                  │ 7. GPT-4o     │
│ Selection     │                                  │ Report Gen    │
│ (SOC2/ISO/PCI)│                                  │ (Narrative)   │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Control    │──────────────────────────────────│ 6. Augment    │
│ Mapping       │                                  │ with Evidence │
│ (Framework)   │                                  │ (RAG)         │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. Evidence   │─────►│ 5. AI Search  │─────────►│ Retrieved     │
│ Query         │      │ (Semantic     │          │ Evidence      │
│ (Cosmos DB)   │      │  Retrieval)   │          │ Artifacts     │
└───────────────┘      └───────────────┘          └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Auditor Portal | React + TypeScript | Compliance dashboard, evidence review, report configuration |
| Executive Dashboard | Power BI Embedded | Real-time compliance posture, trend analysis, risk heatmaps |
| GRC API Integration | REST/GraphQL | Inbound/outbound integration with ServiceNow, Archer, OneTrust |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL, Geo-filtering | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits, Audit logging | API management, authentication, request tracing |
| SignalR | Serverless mode | Real-time audit status notifications |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Audit Engine | Azure Functions (Python 3.11) | Evidence collection, control testing, report generation |
| Evidence Collector | Durable Functions (Fan-out) | Parallel evidence gathering across Azure subscriptions |
| Control Tester | Azure Functions (Timer + HTTP) | Automated control validation against framework criteria |
| Report Generator | Azure Functions (Durable) | GenAI-powered audit report assembly and formatting |
| Trail Analyzer | Azure Functions (Event-driven) | Continuous audit trail monitoring and anomaly detection |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Audit report narrative generation, finding summarization |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for evidence semantic search |
| Document Intelligence | prebuilt-layout + custom models | Parse compliance certificates, audit letters, policy PDFs |
| AI Search | Semantic ranker + vector index | Hybrid search across evidence corpus |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Blob Storage | Hot + Cool tiers, immutable policies, versioning | Evidence artifact storage with legal hold |
| Azure AI Search | S1 tier, 3 replicas | Semantic evidence index for auditor queries |
| Cosmos DB | Provisioned (multi-region) | Audit trails, control results, evidence metadata |
| Azure Purview | Standard | Data catalog, lineage tracking, sensitivity labels |

### 6. Compliance Data Sources

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Policy | Built-in + custom definitions | Compliance state assessment across subscriptions |
| Azure Resource Graph | Cross-subscription queries | Real-time resource inventory and configuration state |
| Log Analytics | Centralized workspace, 365-day retention | Audit log aggregation, KQL-based evidence queries |
| Azure Sentinel | Connected to Log Analytics | Security event correlation, incident evidence |
| Defender for Cloud | Continuous assessment | Security posture scoring, regulatory compliance view |

### 7. Integration Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Data Factory | Scheduled + event-driven pipelines | Evidence collection orchestration across sources |
| Key Vault | RBAC, HSM-backed, soft delete, purge protection | Secrets, certificates, encryption key management |
| Managed Identity | System-assigned for all services | Zero-credential service-to-service authentication |
| Entra ID | OAuth2/OIDC, Conditional Access, PIM | Auditor authentication, role-based access, just-in-time |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│              AUDIT-GRADE SECURITY LAYERS (SOC 2 / ISO 27001)             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (Allowed Regions│  │
│ │             │  │ Custom Rules│  │ Standard    │  │  + IP Allow)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS (ZERO TRUST)                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO + RBAC)│  │ Access      │  │ Enforcement │  │ time Auditor    │  │
│ │ Auditor Role│  │ Policy      │  │ (All Users) │  │ Elevation)      │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Deny All   │  │ Link (All   │  │ Endpoints       │  │
│ │ (3 Subnets) │  │  Default)   │  │ PaaS Svc)   │  │ (Storage/KV)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY (AUDIT EVIDENCE INTEGRITY)                        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ Immutable   │  │ Purview         │  │
│ │ at Rest +   │  │ (HSM-backed │  │ Blob (WORM  │  │ (Sensitivity    │  │
│ │ Transit     │  │  CMK)       │  │  + Legal    │  │  Labels +       │  │
│ │ (TLS 1.3)   │  │             │  │  Hold)      │  │  Classification)│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain │  │ Throttling  │  │ Filtering       │  │
│ │ (System     │  │  Auditor vs │  │ (Per-user   │  │ (Azure OpenAI   │  │
│ │  Assigned)  │  │  Admin)     │  │  Quotas)    │  │  Safety)        │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: AUDIT TRAIL & CONTINUOUS COMPLIANCE                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Activity    │  │ Tamper-proof    │  │
│ │ for Cloud   │  │ (SIEM/SOAR  │  │ Logs (365d  │  │ Audit Ledger   │  │
│ │ (Regulatory │  │  Automated  │  │  Retention, │  │ (Cosmos DB +   │  │
│ │  Dashboard) │  │  Playbooks) │  │  Immutable) │  │  Append-Only)  │  │
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
    resource_group: rg-compliance-audit-dev
    location: eastus
    sku_tier: basic
    log_retention_days: 30
    evidence_retention: 90d

  staging:
    subscription: staging-subscription
    resource_group: rg-compliance-audit-stg
    location: eastus
    sku_tier: standard
    log_retention_days: 180
    evidence_retention: 365d

  production:
    subscription: prod-subscription
    resource_group: rg-compliance-audit-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    log_retention_days: 365
    evidence_retention: 2555d  # 7-year regulatory retention

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  compliance_gate: true  # Block deploy if compliance checks fail

azure_policy_assignments:
  - name: audit-platform-baseline
    scope: /subscriptions/prod-subscription
    definitions:
      - allowed-locations
      - enforce-private-endpoints
      - enforce-encryption-at-rest
      - enforce-diagnostic-settings
      - enforce-tagging-compliance

data_factory_pipelines:
  evidence_collection:
    schedule: "0 */6 * * *"  # Every 6 hours
    sources:
      - azure_policy_state
      - resource_graph_inventory
      - log_analytics_audit_logs
      - sentinel_security_events
      - defender_compliance_scores

  report_generation:
    schedule: "0 2 1 * *"  # Monthly at 2 AM on the 1st
    frameworks:
      - SOC2_Type_II
      - ISO_27001
      - NIST_800_53
      - PCI_DSS_v4

cosmos_db:
  consistency_level: strong
  backup_policy: continuous
  partition_key: /frameworkId
  ttl_policy: -1  # No expiry for audit records
  change_feed: enabled

blob_storage:
  immutability_policy:
    type: time-based
    retention_days: 2555  # 7 years
    legal_hold: enabled
  versioning: enabled
  soft_delete_days: 365
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$1,500-3,000 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions | Premium EP1 (x2) | ~$400 |
| Cosmos DB | Provisioned 10K RU/s | ~$580 |
| Blob Storage | Hot 500GB + Cool 5TB | ~$120 |
| Document Intelligence | S0 (5K pages/mo) | ~$250 |
| Data Factory | Orchestration runs | ~$150 |
| Log Analytics | 365-day retention, 50GB/day | ~$350 |
| Azure Monitor | Metrics + Alerts | ~$100 |
| Azure Sentinel | 50GB/day ingestion | ~$500 |
| Defender for Cloud | Plan 2 (all resources) | ~$300 |
| Key Vault | Premium (HSM-backed) | ~$15 |
| APIM | Standard | ~$150 |
| Azure Purview | Standard | ~$500 |
| Private Link | 10 endpoints | ~$75 |
| Azure Policy | Free (built-in) | $0 |
| Azure Resource Graph | Free (queries) | $0 |
| **Total Estimated** | | **~$5,740-7,240** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why automate compliance evidence collection?**
   - Manual evidence collection for SOC 2 Type II audits typically takes 200+ hours per cycle
   - Automated pipelines reduce collection time to minutes with continuous, real-time evidence
   - Eliminates human error in evidence gathering and ensures completeness across all controls
   - Azure Policy and Resource Graph provide authoritative, API-driven compliance state

2. **Why Azure OpenAI GPT-4o for audit report generation?**
   - Generates narrative audit findings that map evidence to specific framework controls
   - RAG pattern grounds all generated content in actual collected evidence, reducing hallucination
   - Auditors review and approve AI-generated drafts rather than writing from scratch
   - Supports multiple framework templates (SOC 2, ISO 27001, NIST, PCI DSS) with a single model
   - Content filtering ensures no sensitive data leaks into report narratives

3. **Why Cosmos DB for audit trails instead of SQL?**
   - Append-only document model aligns with immutable audit trail requirements
   - Strong consistency guarantees ensure audit record integrity
   - Multi-region replication for disaster recovery without data loss
   - Change feed enables real-time audit event streaming to downstream systems
   - Flexible schema supports evidence from diverse sources (policies, logs, configs)

4. **Why immutable Blob Storage for evidence artifacts?**
   - WORM (Write Once Read Many) compliance meets SEC 17a-4 and FINRA requirements
   - Legal hold support for litigation preservation
   - Time-based retention policies enforce 7-year regulatory retention
   - Versioning provides complete evidence history with tamper detection

5. **Security Considerations for Audit-Grade Platform**
   - All services behind Private Link with no public endpoints
   - Managed Identity eliminates credential storage across all service connections
   - HSM-backed Key Vault for encryption key management (FIPS 140-2 Level 2)
   - Purview classifies and labels evidence data with sensitivity classifications
   - Sentinel SOAR playbooks auto-respond to security anomalies in audit data
   - Defender for Cloud provides continuous regulatory compliance dashboard

6. **Why Data Factory for evidence collection orchestration?**
   - Native connectors to Azure Policy, Resource Graph, and Log Analytics
   - Built-in retry, monitoring, and alerting for pipeline failures
   - Parameterized pipelines support multiple compliance frameworks
   - Data lineage tracking through Purview integration
   - Scheduled and event-driven triggers for continuous evidence collection

### Scalability Considerations

- Data Factory parallel pipelines for multi-subscription evidence collection
- Azure Functions Premium plan for VNET integration and no cold starts
- AI Search replicas for concurrent auditor query workloads
- Cosmos DB auto-scale RU/s for burst evidence ingestion during audit periods
- Blob Storage tiering moves aged evidence to Cool/Archive for cost optimization
- Log Analytics workspace supports cross-workspace queries for multi-tenant audits

### Compliance Framework Coverage

- **SOC 2 Type II**: Trust Service Criteria (Security, Availability, Confidentiality, Processing Integrity, Privacy)
- **ISO 27001**: Annex A controls with automated evidence mapping to 93 control categories
- **NIST 800-53**: Comprehensive control families with continuous monitoring
- **PCI DSS v4.0**: Automated scope assessment and evidence collection for 12 requirement areas
- **Custom Frameworks**: Extensible control mapping engine for organization-specific policies

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Internal Audit + Compliance Platform)
- **Visibility:** Audit Committee + Internal — internal audit, compliance officers, and board
- **Project Score:** 9.5 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | Sentinel, Defender, Log Analytics, OpenAI via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | Privileged Access | PIM for audit system administration |
| Data | Immutable Evidence | WORM storage for audit evidence and findings |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Evidence Chain | Cryptographic chain of custody for all evidence |
| Data | Key Vault | Audit encryption keys, signing certificates |
| Application | Sentinel Integration | Real-time security event aggregation and correlation |
| Application | Defender Integration | Threat and vulnerability assessment data feeds |
| Monitoring | SOC Dashboard | Real-time compliance posture and risk visualization |
| Monitoring | Alert Correlation | Cross-framework compliance violation detection |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| SOC 2 Type II | Managed | Continuous SOC 2 control monitoring and evidence collection |
| ISO 27001 | Managed | ISMS control assessment and certification support |
| NIST CSF | Aligned | NIST Cybersecurity Framework assessment automation |
| FedRAMP | Supported | Federal risk authorization control mapping |
| Audit Independence | Enforced | Separation of duties between audit and operations |
| Finding Remediation | Tracked | Remediation timelines with escalation workflows |

### Regulatory Applicability
- **SOC 2 Type II:** Service organization control assessment
- **ISO 27001:** Information security management system certification
- **NIST Cybersecurity Framework:** Federal cybersecurity standards
- **FedRAMP:** Federal Risk and Authorization Management Program
- **SOX Section 404:** Internal control over financial reporting
- **PCI DSS:** Payment Card Industry compliance assessment
