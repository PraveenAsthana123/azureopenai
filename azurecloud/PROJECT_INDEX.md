# Azure Enterprise AI/ML Portfolio - Complete Project Index

## Overview

This portfolio contains **26 enterprise-grade Azure projects** demonstrating end-to-end architecture skills across AI, ML, Data Engineering, and Cloud Infrastructure.

---

## Projects At A Glance

| # | Project | Key Technologies | Primary Use Case |
|---|---------|------------------|------------------|
| 1 | [RAG Knowledge Copilot](./project-1-rag-copilot/) | Azure OpenAI, AI Search, Functions | Enterprise document Q&A |
| 2 | [Document Processing](./project-2-document-processing/) | Document Intelligence, Azure ML | Intelligent document classification |
| 3 | [Call Center Copilot](./project-3-call-center-copilot/) | Speech Services, Translator, OpenAI | Multilingual voice/chat AI |
| 4 | [Agentic Platform](./project-4-agentic-platform/) | OpenAI Function Calling, Durable Functions | Multi-step workflow automation |
| 5 | [Fraud Detection](./project-5-fraud-detection/) | Azure ML, Stream Analytics, OpenAI | Real-time fraud scoring + explainability |
| 6 | [Customer 360](./project-6-customer-360/) | Data Factory, Azure ML, Cosmos DB | Unified customer profiles + personalization |
| 7 | [Healthcare Clinical Copilot](./project-7-healthcare-clinical-copilot/) | Azure Health Data Services, OpenAI, Text Analytics for Health | HIPAA-compliant clinical decision support |
| 8 | [Supply Chain Optimizer](./project-8-supply-chain-optimizer/) | Azure ML, Event Hub, OpenAI, Data Factory | Demand forecasting + inventory optimization |
| 9 | [IoT Predictive Maintenance](./project-9-iot-predictive-maintenance/) | IoT Hub, Azure ML, Stream Analytics | Equipment failure prediction |
| 10 | [Code Review & DevOps Copilot](./project-10-code-review-copilot/) | Azure OpenAI, Service Bus, DevOps API | AI-powered code review + incident RCA |
| 11 | [Legal Contract Analyzer](./project-11-legal-contract-analyzer/) | Document Intelligence, OpenAI, AI Search | Contract clause extraction + risk |
| 12 | [Real-Time Analytics Dashboard](./project-12-realtime-analytics-dashboard/) | Azure Data Explorer, OpenAI, Stream Analytics | NL-to-KQL + anomaly alerting |
| 13 | [Data Lakehouse](./project-13-data-lakehouse/) | Synapse, ADLS Gen2, Delta Lake | NL-to-SQL analytics |
| 14 | [Multi-Region DR](./project-14-multi-region-dr/) | Traffic Manager, Cosmos DB, Front Door | Disaster recovery for AI platforms |
| 15 | [HR Talent Intelligence](./project-15-hr-talent-intelligence/) | Azure OpenAI, AI Search, Document Intelligence | Resume screening + workforce planning |
| 16 | [ESG & Sustainability Reporter](./project-16-esg-sustainability/) | Document Intelligence, OpenAI, Synapse, Purview | ESG data extraction + compliance reporting |
| 17 | [Knowledge Graph Builder](./project-17-knowledge-graph/) | Cosmos DB Gremlin, OpenAI, AI Search | Entity extraction + graph-enhanced RAG |
| 18 | [Multi-Modal Content Platform](./project-18-multimodal-content/) | Azure AI Vision, DALL-E 3, Speech, OpenAI | Image/video/audio analysis + generation |
| 19 | [Compliance Audit Automation](./project-19-compliance-audit/) | Azure Policy, Resource Graph, OpenAI, Sentinel | Automated evidence collection + audit reports |
| 20 | [Energy & Utilities Smart Grid](./project-20-energy-smart-grid/) | IoT Hub, Azure ML, Stream Analytics, OpenAI | Smart meter analytics + load forecasting |
| 21 | [Banking CRM Solution](./project-21-banking-crm/) | Azure OpenAI, Azure ML, Event Hub, Synapse | Customer 360 + NBA + KYC/AML compliance |
| 22 | [AI Contact Center Platform](./project-22-contact-center/) | Communication Services, Speech, OpenAI, SignalR | Omnichannel AI contact center |
| 23 | [Contact Center Knowledge Base](./project-23-knowledge-base-contact-center/) | Azure OpenAI, AI Search, Bot Service, Speech | AI knowledge management for agents |
| 24 | [AI Campaign Management](./project-24-campaign-management/) | Azure OpenAI, Azure ML, Communication Services | GenAI campaign creation + multi-channel orchestration |
| 25 | [Digital Marketing & Product Intelligence](./project-25-digital-marketing/) | Azure OpenAI, DALL-E 3, Azure ML, CDN | Product content + SEO + attribution |
| 26 | [Voice AI Outbound Platform](./project-26-voice-ai-outbound/) | Communication Services, Speech, OpenAI, Service Bus | AI outbound voice calling + TCPA compliance |

---

## Business Domain Classification

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS DOMAIN CLASSIFICATION                             │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  B2C (Business-to-Consumer)          B2B (Business-to-Business)                    │
│  End-customer facing solutions       Enterprise / partner facing solutions         │
│  ├── 3  Call Center Copilot          ├── 2  Document Processing                    │
│  ├── 5  Fraud Detection              ├── 5  Fraud Detection                        │
│  ├── 6  Customer 360                 ├── 6  Customer 360                           │
│  ├── 7  Healthcare Clinical Copilot  ├── 7  Healthcare Clinical Copilot            │
│  ├── 14 Multi-Region DR             ├── 8  Supply Chain Optimizer                  │
│  ├── 18 Multi-Modal Content          ├── 9  IoT Predictive Maintenance             │
│  ├── 20 Energy Smart Grid            ├── 11 Legal Contract Analyzer                │
│  ├── 21 Banking CRM                  ├── 14 Multi-Region DR                        │
│  ├── 22 Contact Center               ├── 16 ESG & Sustainability                   │
│  ├── 24 Campaign Management          ├── 18 Multi-Modal Content                    │
│  ├── 25 Digital Marketing            ├── 20 Energy Smart Grid                      │
│  └── 26 Voice AI Outbound            ├── 21 Banking CRM                            │
│                                       ├── 24 Campaign Management                    │
│  B2E (Business-to-Employee)           └── 25 Digital Marketing                      │
│  Internal workforce solutions                                                       │
│  ├── 1  RAG Knowledge Copilot                                                       │
│  ├── 2  Document Processing                                                         │
│  ├── 3  Call Center Copilot                                                         │
│  ├── 4  Agentic Platform                                                            │
│  ├── 9  IoT Predictive Maintenance                                                  │
│  ├── 10 Code Review Copilot                                                         │
│  ├── 11 Legal Contract Analyzer                                                     │
│  ├── 12 RT Analytics Dashboard                                                      │
│  ├── 13 Data Lakehouse                                                              │
│  ├── 15 HR Talent Intelligence                                                      │
│  ├── 16 ESG & Sustainability                                                        │
│  ├── 17 Knowledge Graph                                                             │
│  ├── 19 Compliance Audit                                                            │
│  ├── 22 Contact Center (Agent Assist)                                               │
│  └── 23 Knowledge Base CC                                                           │
│                                                                                     │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Business Domain, Security, Governance, Visibility & Score Matrix

| # | Project | Domain | Visibility | Score | Security Controls | Governance & Compliance |
|---|---------|--------|------------|-------|-------------------|------------------------|
| 1 | RAG Knowledge Copilot | B2E | Internal | 8.5/10 | RBAC, Private Link, Managed Identity, Key Vault, AES-256 at-rest, TLS 1.2 | Data classification, DLP policies, Content access audit trail, Document retention |
| 2 | Document Processing | B2B / B2E | Internal + Partner Portal | 8.0/10 | RBAC, Private Link, Key Vault, Document encryption, VNet isolation | Document retention schedules, PII redaction, Data lineage, Processing audit trail |
| 3 | Call Center Copilot | B2C / B2E | Customer-Facing + Internal | 9.0/10 | PCI DSS, Call recording encryption, DTMF masking, Key Vault, TLS 1.2 | GDPR/CCPA consent, Agent QA compliance, Transcript retention (7yr), Language accessibility |
| 4 | Agentic Platform | B2E | Internal | 8.5/10 | Function-level auth, RBAC, Managed Identity, Approval gates, Key Vault | Workflow audit trail, Human-in-the-loop policies, Action logging, Change management |
| 5 | Fraud Detection | B2C / B2B | Internal (Ops) + Regulatory | 9.5/10 | PCI DSS Level 1, SOX controls, Data masking, TDE, Key Vault, Network isolation | SOX audit, FinCEN/SAR reporting, Model governance, Explainability requirements |
| 6 | Customer 360 | B2C / B2B | Customer-Facing + Internal | 9.0/10 | GDPR Art.17, CCPA, PII encryption, Consent-based access, Data masking | Consent management, Data subject rights, Cross-border transfer (SCCs), Retention policies |
| 7 | Healthcare Clinical Copilot | B2C / B2B | Clinical Staff + Patient Portal | 9.5/10 | HIPAA/BAA, PHI encryption, Access audit logs, Break-glass access, Key Vault | HIPAA audit, BAA compliance, PHI minimum necessary, Clinical data retention (6yr+), IRB |
| 8 | Supply Chain Optimizer | B2B | Partner Portal + Internal | 8.5/10 | Supply chain data isolation, OAuth 2.0, Key Vault, VNet peering | Vendor compliance, Trade compliance (export controls), Data sharing agreements, SLA governance |
| 9 | IoT Predictive Maintenance | B2B / B2E | Field Ops + Internal Dashboard | 8.0/10 | X.509 device certificates, Device provisioning, Edge encryption, Key Vault | Asset lifecycle (ISO 55000), Sensor calibration audit, OT/IT boundary policies |
| 10 | Code Review Copilot | B2E | Internal (Engineering) | 8.0/10 | SAST/DAST, Code scanning, Secrets detection, Key Vault, Private endpoints | SDLC governance, Code quality gates, IP protection, OSS license compliance |
| 11 | Legal Contract Analyzer | B2B / B2E | Legal Team + External Counsel | 8.5/10 | Attorney-client privilege, Document classification, Encryption, Key Vault | Legal hold, Jurisdiction-specific retention, Matter management, Privilege log |
| 12 | RT Analytics Dashboard | B2E | Executive + Internal | 8.5/10 | Row-level security, Query rate limiting, Key Vault, Private endpoints, AAD | Data access governance, Query audit logging, Dashboard publishing policies |
| 13 | Data Lakehouse | B2E | Internal (Data Team) | 8.0/10 | Column-level security, Dynamic masking, ACL on ADLS, Key Vault, VNet | Purview catalog, Data lineage, Data quality rules, Zone-based governance |
| 14 | Multi-Region DR | B2B / B2C | Ops + SRE | 9.0/10 | Geo-fencing, Cross-region encryption, Failover auth, Key Vault replication | RPO/RTO compliance, DR testing schedule, Geo-residency, BCP governance |
| 15 | HR Talent Intelligence | B2E | HR Team + Hiring Managers | 8.5/10 | PII protection, EEOC compliance, Bias detection, Key Vault, Anonymization | EEOC/EEO-1, AI bias audit (NYC LL144), Employee data retention, GDPR (EU) |
| 16 | ESG & Sustainability | B2B / B2E | Public (Investors) + Internal | 9.0/10 | Data integrity controls, Audit-grade lineage, Key Vault, Immutable logs | CSRD, TCFD, GRI, SEC climate disclosure, Scope 1/2/3 governance, Third-party assurance |
| 17 | Knowledge Graph | B2E | Internal (Data & Research) | 7.5/10 | Entity access control, Graph traversal limits, Key Vault, Private endpoints | Ontology governance, Entity lifecycle, Relationship validation, Quality scoring |
| 18 | Multi-Modal Content | B2C / B2B | Public (Marketing) + Internal | 8.5/10 | Content safety filters, DRM, Watermarking, Key Vault, CDN token auth | Brand compliance, Copyright/IP, WCAG 2.1, Content moderation, Usage rights |
| 19 | Compliance Audit | B2E | Audit Committee + Internal | 9.5/10 | Sentinel SIEM, Defender for Cloud, Immutable evidence, Key Vault, PIM | SOC 2 II, ISO 27001, HIPAA, PCI DSS, NIST CSF, FedRAMP, Evidence chain-of-custody |
| 20 | Energy Smart Grid | B2B / B2C | Utility Ops + Consumer Portal | 9.0/10 | NERC CIP, SCADA isolation, OT/IT segmentation, Key Vault, X.509 | NERC CIP-002–014, FERC regulation, Grid reliability, Meter data privacy, CIP |
| 21 | Banking CRM | B2C / B2B | Banker Desktop + Customer App | 9.5/10 | KYC/AML, PCI DSS Level 1, SOX, Data masking, TDE, Key Vault, Network isolation | Basel III/IV, BSA/AML, FFIEC, ECOA, GLBA, OCC/FDIC regulatory exams |
| 22 | Contact Center | B2C / B2E | Customer-Facing + Agent Desktop | 9.0/10 | Call recording encryption, PCI DSS, DTMF suppression, Key Vault, WAF | Call recording consent, QA scoring, TCPA, ADA accessibility, Agent certification |
| 23 | Knowledge Base CC | B2E | Agent Desktop + Self-Service | 8.0/10 | Content auth workflows, RBAC, Key Vault, Private endpoints, Bot auth | Article lifecycle, Content accuracy SLAs, SME review governance, Version control |
| 24 | Campaign Management | B2C / B2B | Marketing Team + Analytics | 8.5/10 | CAN-SPAM, GDPR consent enforcement, List hygiene, Key Vault, Rate limiting | CAN-SPAM, GDPR e-Privacy, CASL, Consent management, Opt-out governance |
| 25 | Digital Marketing | B2C / B2B | Public (Web) + Marketing Team | 8.5/10 | Brand safety filters, DLP, CDN signed URLs, Key Vault, WAF | FTC guidelines, IAB ad standards, SEO white-hat, Product claim accuracy, IP |
| 26 | Voice AI Outbound | B2C | Outbound Ops + Compliance | 9.0/10 | TCPA, DNC registry, Call recording consent, Key Vault, Voice biometric privacy | TCPA §227, DNC (FTC), State mini-TCPA, STIR/SHAKEN, FCC robocall, TSR |

### Score Legend

| Score Range | Rating | Meaning |
|-------------|--------|---------|
| 9.5 – 10.0 | **Critical** | Highest regulatory/financial risk; mandatory compliance frameworks; real-time fraud/health/financial decisions |
| 9.0 – 9.4 | **High** | Customer-facing with significant compliance; handles PII/PHI/PCI data; multi-regulation scope |
| 8.5 – 8.9 | **Elevated** | Important business function; moderate regulatory exposure; handles sensitive internal data |
| 8.0 – 8.4 | **Standard** | Internal productivity tool; lower regulatory burden; primarily employee-facing |
| 7.5 – 7.9 | **Foundation** | Infrastructure/enabler project; indirect business impact; supports other projects |

### Visibility Legend

| Visibility Level | Description |
|------------------|-------------|
| **Public** | Externally visible to customers, investors, or the general public |
| **Customer-Facing** | Directly interacts with customers (portals, voice, chat) |
| **Partner Portal** | Accessible by business partners or vendors |
| **Internal** | Employee-only access (specific teams noted) |
| **Regulatory** | Visible to auditors, regulators, or compliance bodies |

---

## Security Architecture (All Projects)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS (DEFENSE-IN-DEPTH)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 1: Network Security                                              │
│  ├── Private VNet (10.0.0.0/16) with NSG rules                         │
│  ├── Private Endpoints for all PaaS services                            │
│  ├── Azure Firewall / WAF (public-facing projects)                      │
│  ├── DDoS Protection Standard                                           │
│  └── VNet service endpoints + peering                                   │
│                                                                         │
│  Layer 2: Identity & Access                                             │
│  ├── Entra ID (Azure AD) for all authentication                        │
│  ├── Managed Identity (system-assigned) — zero secrets in code          │
│  ├── RBAC (least privilege) — per-resource role assignments             │
│  ├── Conditional Access policies                                        │
│  └── Privileged Identity Management (PIM) for admin roles               │
│                                                                         │
│  Layer 3: Data Protection                                               │
│  ├── Encryption at rest — AES-256 (platform-managed or CMK)             │
│  ├── Encryption in transit — TLS 1.2+ enforced                          │
│  ├── Key Vault for secrets, keys, certificates                          │
│  ├── Dynamic data masking (PII/PHI/PCI fields)                          │
│  └── Azure Information Protection labeling                              │
│                                                                         │
│  Layer 4: Application Security                                          │
│  ├── OWASP Top 10 mitigations                                           │
│  ├── Input validation & output encoding                                 │
│  ├── Content safety filters (Azure AI Content Safety)                   │
│  ├── API rate limiting via APIM                                         │
│  └── Prompt injection protections (GenAI projects)                      │
│                                                                         │
│  Layer 5: Monitoring & Detection                                        │
│  ├── Microsoft Defender for Cloud                                       │
│  ├── Azure Sentinel (SIEM) — security analytics                        │
│  ├── Log Analytics — centralized audit logs                             │
│  ├── Application Insights — runtime telemetry                           │
│  └── Azure Monitor alerts — anomaly detection                           │
│                                                                         │
│  Layer 6: Governance & Compliance                                       │
│  ├── Azure Policy — enforce guardrails at scale                         │
│  ├── Azure Purview — data catalog & lineage                             │
│  ├── Resource locks — prevent accidental deletion                       │
│  ├── Tagging policies — cost/ownership tracking                         │
│  └── Regulatory compliance dashboards (Defender for Cloud)              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Governance Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENTERPRISE GOVERNANCE FRAMEWORK                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DATA GOVERNANCE                                                        │
│  ├── Classification: Public / Internal / Confidential / Restricted      │
│  ├── Lineage: Purview tracks data from source → consumption             │
│  ├── Quality: Automated data quality rules per zone                     │
│  ├── Retention: Policy-driven lifecycle (hot → cool → archive → delete) │
│  ├── Residency: Geo-fenced per regulation (EU, US, APAC)               │
│  └── Catalog: Self-service discovery via Purview                        │
│                                                                         │
│  AI/ML GOVERNANCE                                                       │
│  ├── Model Registry: Azure ML tracks versions, lineage, metrics         │
│  ├── Responsible AI: Fairness, transparency, accountability dashboards  │
│  ├── Bias Auditing: Pre-deploy bias checks (HR/lending/insurance)       │
│  ├── Explainability: SHAP/LIME + GenAI explanations for all models      │
│  ├── Drift Detection: Automated model performance monitoring            │
│  └── Human-in-the-Loop: Approval gates for high-risk decisions          │
│                                                                         │
│  REGULATORY COMPLIANCE MAP                                              │
│  ├── GDPR/CCPA/CPRA  → Projects 3, 6, 15, 22, 24, 25, 26              │
│  ├── HIPAA/HITECH     → Project 7, 19                                  │
│  ├── PCI DSS          → Projects 3, 5, 21, 22                          │
│  ├── SOX              → Projects 5, 21                                 │
│  ├── Basel III/IV     → Project 21                                     │
│  ├── BSA/AML          → Projects 5, 21                                 │
│  ├── TCPA/DNC         → Projects 22, 26                                │
│  ├── CAN-SPAM/CASL    → Project 24                                     │
│  ├── CSRD/TCFD/GRI    → Project 16                                     │
│  ├── NERC CIP         → Project 20                                     │
│  ├── SOC 2/ISO 27001  → Project 19 (+ applicable to all)               │
│  ├── EEOC/LL144       → Project 15                                     │
│  ├── FTC Guidelines   → Project 25                                     │
│  └── NIST CSF/800-53  → Projects 14, 19 (framework for all)            │
│                                                                         │
│  OPERATIONAL GOVERNANCE                                                 │
│  ├── IaC Only: All resources via Terraform (no portal changes)          │
│  ├── GitOps: PR-based deployments with approval gates                   │
│  ├── Tagging: Environment, Project, Owner, CostCenter, DataClass        │
│  ├── Cost Management: Budgets + alerts per resource group               │
│  ├── SLA/SLO/SLI: Defined per project tier (P1/P2/P3)                  │
│  └── Incident Management: PagerDuty/ServiceNow integration              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Project Summaries

### Project 1: Enterprise RAG Knowledge Copilot
**Directory:** `project-1-rag-copilot/`

Enterprise knowledge assistant enabling natural language Q&A over company documents with citation support.

**Key Features:** Hybrid search, Document ingestion pipeline, Multi-turn conversations

**Azure Services:** Azure OpenAI, AI Search, Document Intelligence, Functions, Cosmos DB, Key Vault, APIM

---

### Project 2: Intelligent Document Processing
**Directory:** `project-2-document-processing/`

Automated document extraction, classification, and routing with human-in-the-loop validation.

**Key Features:** OCR extraction, ML classification, Confidence-based routing, Feedback loop

**Azure Services:** Document Intelligence, Azure ML, Event Grid, Durable Functions, Cosmos DB, Power Apps

---

### Project 3: Automated Call Center Copilot
**Directory:** `project-3-call-center-copilot/`

Multilingual conversational AI for call centers with real-time transcription and intelligent responses.

**Key Features:** 100+ languages, Real-time STT/TTS, Agent assist, Post-call summarization

**Azure Services:** Speech Services, Translator, Azure OpenAI, SignalR, Bot Framework, Cosmos DB

---

### Project 4: GenAI Agentic Automation Platform
**Directory:** `project-4-agentic-platform/`

Multi-agent system executing enterprise workflows through natural language using function calling.

**Key Features:** ReAct pattern, 25+ tools, Human-in-the-loop, Multi-system integration

**Azure Services:** Azure OpenAI (Function Calling), Durable Functions, Logic Apps, APIM, Graph API

---

### Project 5: Financial Fraud Detection Platform
**Directory:** `project-5-fraud-detection/`

Real-time fraud detection with ML ensemble models and GenAI-powered explainability.

**Key Features:** <200ms latency, 96% detection rate, GenAI explanations, Rules engine

**Azure Services:** Azure ML, Event Hub, Stream Analytics, Azure OpenAI, Synapse, Cosmos DB

---

### Project 6: Customer 360 Personalization Engine
**Directory:** `project-6-customer-360/`

Unified customer data platform with identity resolution and AI-powered personalization.

**Key Features:** Identity resolution, RFM scoring, Churn prediction, Recommendation engine

**Azure Services:** Data Factory, Azure ML, Cosmos DB, Azure OpenAI, Event Hub, Power BI

---

### Project 7: Healthcare Clinical Copilot
**Directory:** `project-7-healthcare-clinical-copilot/`

HIPAA-compliant clinical decision support system providing medical NER, drug interaction checks, and AI-generated patient summaries from FHIR health records.

**Key Features:** Medical NER (Text Analytics for Health), Drug interaction detection, Patient summary generation, FHIR integration, HIPAA/BAA compliance

**Azure Services:** Azure OpenAI, Azure Health Data Services (FHIR), Text Analytics for Health, AI Search, Functions, Cosmos DB, Key Vault, APIM

---

### Project 8: Supply Chain Optimizer
**Directory:** `project-8-supply-chain-optimizer/`

AI-powered supply chain optimization platform providing demand forecasting, inventory optimization, and supplier risk scoring with GenAI-generated insights.

**Key Features:** AutoML demand forecasting, Reorder point optimization, Supplier risk scoring, GenAI narrative insights, Real-time supply event processing

**Azure Services:** Azure ML, Azure OpenAI, Event Hub, Stream Analytics, Data Factory, ADLS Gen2, Synapse, Cosmos DB, Functions

---

### Project 9: IoT Predictive Maintenance
**Directory:** `project-9-iot-predictive-maintenance/`

IoT platform predicting equipment failures using sensor data and ML models.

**Key Features:** Edge processing, RUL prediction, Anomaly detection, GenAI insights

**Azure Services:** IoT Hub, IoT Edge, Event Hub, Stream Analytics, Azure ML, Azure OpenAI

---

### Project 10: Code Review & DevOps Copilot
**Directory:** `project-10-code-review-copilot/`

AI-powered DevOps assistant providing automated code review, PR summarization, incident root cause analysis, and deployment risk scoring.

**Key Features:** AI code review (quality, bugs, security), PR summarization, Incident RCA, Deployment risk analysis, Azure DevOps + GitHub integration

**Azure Services:** Azure OpenAI, AI Search, Service Bus, Functions, Cosmos DB, Key Vault, Redis Cache, APIM

---

### Project 11: Legal Contract Analyzer
**Directory:** `project-11-legal-contract-analyzer/`

AI-powered contract analysis extracting clauses, identifying risks, and comparing versions.

**Key Features:** Clause extraction, Risk scoring, Version comparison, Playbook compliance

**Azure Services:** Document Intelligence, Azure OpenAI, AI Search, Functions, Cosmos DB

---

### Project 12: Real-Time Analytics Dashboard
**Directory:** `project-12-realtime-analytics-dashboard/`

Streaming analytics platform with natural language to KQL query translation, real-time anomaly detection, and GenAI-narrated executive summaries.

**Key Features:** NL-to-KQL translation, Real-time anomaly alerting, GenAI executive summaries, Live dashboard with SignalR, Streaming data processing

**Azure Services:** Azure Data Explorer, Azure OpenAI, Event Hub, Stream Analytics, Functions, Cosmos DB, SignalR, Key Vault

---

### Project 13: Enterprise Data Lakehouse
**Directory:** `project-13-data-lakehouse/`

Unified data platform with Medallion architecture and natural language analytics.

**Key Features:** Bronze/Silver/Gold layers, Delta Lake, NL-to-SQL, Data governance

**Azure Services:** Synapse Analytics, ADLS Gen2, Data Factory, Azure OpenAI, Purview

---

### Project 14: Multi-Region Disaster Recovery
**Directory:** `project-14-multi-region-dr/`

Multi-region DR architecture for AI platforms with automated failover and GenAI reporting.

**Key Features:** Active-active Cosmos DB, Geo-replicated AI Search, Automated failover, DR reports

**Azure Services:** Front Door, Traffic Manager, Cosmos DB, RA-GRS Storage, Azure Monitor

---

### Project 15: HR Talent Intelligence Platform
**Directory:** `project-15-hr-talent-intelligence/`

AI-driven HR platform for resume screening, skill gap analysis, internal mobility matching, and workforce planning with GenAI-powered recommendations.

**Key Features:** AI resume screening with scoring, Skill gap analysis with learning paths, Internal mobility matching, Workforce planning insights, Vector search on talent profiles

**Azure Services:** Azure OpenAI, AI Search, Document Intelligence, Azure ML, Functions, Cosmos DB, Data Factory, ADLS Gen2, Key Vault

---

### Project 16: ESG & Sustainability Reporter
**Directory:** `project-16-esg-sustainability/`

ESG reporting platform that extracts sustainability metrics from corporate reports, calculates carbon footprints (Scope 1/2/3), checks CSRD/TCFD compliance, and generates GenAI narratives for sustainability disclosures.

**Key Features:** ESG metric extraction (CSRD, TCFD, GRI), Carbon footprint analytics (Scope 1/2/3), Regulatory compliance checking, GenAI sustainability narrative generation, Data governance with Purview

**Azure Services:** Azure OpenAI, Document Intelligence, AI Search, Synapse, Data Factory, ADLS Gen2, Purview, Functions, Cosmos DB, Key Vault

---

### Project 17: Knowledge Graph Builder
**Directory:** `project-17-knowledge-graph/`

Automated knowledge graph construction from documents with entity/relationship extraction, graph-enhanced RAG queries, and ontology management.

**Key Features:** AI entity/relationship extraction, Cosmos DB Gremlin graph storage, Graph-enhanced RAG (vector + graph traversal), Ontology CRUD management, Document-to-graph ingestion pipeline

**Azure Services:** Azure OpenAI, Cosmos DB (Gremlin API), AI Search, Document Intelligence, Data Factory, Functions, Key Vault, Redis Cache

---

### Project 18: Multi-Modal Content Platform
**Directory:** `project-18-multimodal-content/`

Multi-modal AI platform for image, video, and audio analysis and generation, brand content creation, accessibility tagging, and creative GenAI workflows.

**Key Features:** Image analysis + DALL-E 3 generation, Video indexing + scene extraction, Audio transcription, Accessibility alt-text tagging, Brand-aligned content creation

**Azure Services:** Azure OpenAI (GPT-4o + DALL-E 3), Azure AI Vision, Azure AI Speech, Video Indexer, CDN, Media Services, Functions, Cosmos DB, Key Vault

---

### Project 19: Compliance Audit Automation
**Directory:** `project-19-compliance-audit/`

Automated compliance audit platform that collects evidence from Azure resources, tests controls against frameworks (SOC2, ISO 27001), analyzes audit trails, and generates comprehensive audit reports with GenAI.

**Key Features:** Automated evidence collection (Resource Graph), AI control testing, Audit trail analysis (Log Analytics), GenAI audit report generation, Multi-framework support (SOC2, ISO 27001, HIPAA)

**Azure Services:** Azure OpenAI, Azure Policy, Resource Graph, Document Intelligence, Sentinel, Defender for Cloud, Log Analytics, Functions, Cosmos DB, AI Search, Key Vault

---

### Project 20: Energy & Utilities Smart Grid
**Directory:** `project-20-energy-smart-grid/`

Smart grid analytics platform for energy utilities providing smart meter analysis, load forecasting, outage prediction, and GenAI-powered grid optimization recommendations.

**Key Features:** Smart meter data analytics, ML load forecasting, Outage prediction from sensor anomalies, GenAI grid optimization recommendations, Real-time telemetry processing, Grid health scoring

**Azure Services:** Azure OpenAI, IoT Hub, IoT Edge, Event Hub, Stream Analytics, Azure ML, Time Series Insights, ADLS Gen2, Synapse, Functions, Cosmos DB, Key Vault

---

### Project 21: Banking CRM Solution
**Directory:** `project-21-banking-crm/`

AI-powered banking CRM platform providing Customer 360 unified view, next-best-action recommendations, churn prediction, KYC/AML compliance automation, and a GenAI-powered relationship manager copilot.

**Key Features:** Customer 360 (deposits/loans/cards/investments), AI next-best-action, Churn prediction + retention, KYC/AML screening, RM copilot with briefings, Cross-sell propensity scoring, Basel III/IV regulatory reporting

**Azure Services:** Azure OpenAI, Azure ML, AI Search, Event Hub, Stream Analytics, Data Factory, ADLS Gen2, Synapse, Cosmos DB, Functions, Redis Cache, Purview, Key Vault

---

### Project 22: AI Contact Center Platform
**Directory:** `project-22-contact-center/`

Enterprise omnichannel AI contact center with real-time speech transcription, intelligent routing, agent assist, auto-responses, quality management, and supervisor dashboards.

**Key Features:** Omnichannel (voice/chat/email/social), Real-time STT in 100+ languages, Intelligent skill-based routing, Agent assist with knowledge suggestions, Post-call summarization, GenAI auto-responses, Quality scoring, IVR deflection

**Azure Services:** Azure OpenAI, Communication Services, Speech Services, Translator, AI Search, Bot Service, SignalR, Event Hub, Stream Analytics, Functions, Cosmos DB, Key Vault

---

### Project 23: Contact Center Knowledge Base
**Directory:** `project-23-knowledge-base-contact-center/`

AI-powered knowledge management system for contact centers enabling semantic search, real-time agent article suggestions, automated FAQ generation from call transcripts, and knowledge gap detection.

**Key Features:** GenAI article authoring, Semantic + vector search, Real-time agent suggestions during calls, Knowledge gap detection from transcripts, Auto-generated FAQs, Content freshness scoring, Feedback-driven ranking

**Azure Services:** Azure OpenAI, AI Search, Bot Service, Speech Services, SignalR, Functions, Cosmos DB, Blob Storage, Redis Cache, Key Vault

---

### Project 24: AI Campaign Management Platform
**Directory:** `project-24-campaign-management/`

Enterprise campaign management platform with GenAI-powered campaign creation, audience segmentation, multi-channel orchestration (email/SMS/push/in-app), A/B test optimization, and predictive ROI modeling.

**Key Features:** GenAI campaign creation, AI audience segmentation, Multi-channel content generation, A/B test optimization, Predictive ROI, Budget allocation optimization, Customer journey mapping, Campaign performance analytics

**Azure Services:** Azure OpenAI, Azure ML, Communication Services, Notification Hubs, Event Hub, Data Factory, ADLS Gen2, Synapse, Cosmos DB, Functions, Redis Cache, Key Vault

---

### Project 25: Digital Marketing & Product Intelligence Platform
**Directory:** `project-25-digital-marketing/`

AI-powered digital marketing platform for product promotion with GenAI content generation, SEO optimization, social media scheduling, dynamic pricing, review sentiment analysis, and multi-touch attribution modeling.

**Key Features:** GenAI product descriptions, SEO content optimization, Social media content calendar, DALL-E 3 product visuals, Dynamic pricing recommendations, Review sentiment analysis, Multi-touch attribution, Landing page optimization

**Azure Services:** Azure OpenAI (GPT-4o + DALL-E 3), Azure ML, AI Search, AI Language, Event Hub, Data Factory, ADLS Gen2, Synapse, CDN, Cosmos DB, Functions, Key Vault

---

### Project 26: Voice AI Outbound Platform
**Directory:** `project-26-voice-ai-outbound/`

AI-powered outbound voice platform for proactive customer engagement with GenAI-scripted calls, neural TTS, real-time conversation steering, TCPA/DNC compliance, voicemail detection, and sentiment-based escalation.

**Key Features:** GenAI call script generation, Neural voice TTS/STT, Real-time conversation steering, TCPA/DNC compliance (Redis-cached), Voicemail detection + message drop, AI call outcome classification, Sentiment-based human escalation, Optimal call scheduling

**Azure Services:** Azure OpenAI, Communication Services, Speech Services, AI Language, Bot Service, Service Bus, Event Hub, Stream Analytics, Cosmos DB, Functions, Redis Cache, Key Vault

---

## Azure Services Master Coverage

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE AZURE SERVICES COVERAGE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  AI/ML Services                              Data Services                       │
│  ├── Azure OpenAI [1,3-13,15-26]             ├── Synapse [5,8,13,16,20,21,24,25] │
│  ├── AI Search [1,7,10,11,15-17,19,21,23,25] ├── ADLS Gen2 [2,5,6,8,9,13,15,16, │
│  ├── Document Intelligence [1,2,7,11,        │    20,21,24,25]                    │
│  │    15,16,17,19]                            ├── Cosmos DB [ALL]                 │
│  ├── Speech Services [3,18,22,23,26]         ├── Event Hub [5,6,8,9,12,20-22,    │
│  ├── Translator [3,22]                       │    24-26]                          │
│  ├── Azure ML [2,5,6,8,9,15,20,21,24,25]    ├── Data Factory [6,8,13,15-17,19,  │
│  ├── Text Analytics for Health [7]           │    21,24,25]                       │
│  ├── Azure AI Vision [18]                    ├── Redis [4,7,10,14,15,17,18,21,   │
│  ├── Azure AI Language [25,26]               │    22,23,26]                       │
│  ├── Video Indexer [18]                      ├── Azure Data Explorer [12]         │
│  ├── DALL-E 3 [18,25]                        ├── Time Series Insights [20]        │
│  └── Communication Services [22,24,26]       └── Service Bus [10,26]             │
│                                                                                  │
│  Compute Services                            Integration Services                │
│  ├── Azure Functions [ALL]                   ├── Logic Apps [2,4]                │
│  ├── Durable Functions [1,2,4]               ├── APIM [1,3,4,7,8,10-12,15]      │
│  ├── AKS [2]                                 ├── Graph API [4]                   │
│  ├── Stream Analytics [5,8,9,12,20,21,22,26] ├── SignalR [3,12,22,23]            │
│  ├── IoT Hub/Edge [9,20]                     ├── CDN [18,25]                     │
│  ├── Media Services [18]                     ├── Bot Service [22,23,26]          │
│  └── Notification Hubs [24]                  └── Event Grid [23]                 │
│                                                                                  │
│  Security & Identity                         Observability                       │
│  ├── Key Vault [ALL]                         ├── App Insights [ALL]              │
│  ├── Managed Identity [ALL]                  ├── Log Analytics [ALL]             │
│  ├── Private Link [ALL]                      ├── Azure Monitor [ALL]             │
│  ├── Entra ID [ALL]                          ├── Power BI [5,6,8,9,21,22,26]    │
│  ├── Azure Policy [19]                       └── Sentinel [19]                   │
│  └── Defender for Cloud [19]                                                     │
│                                                                                  │
│  Governance & Compliance                     DR & Global                         │
│  ├── Purview [13,16,21]                      ├── Front Door [14]                 │
│  ├── Azure Health Data Services [7]          ├── Traffic Manager [14]            │
│  └── Resource Graph [19]                     └── Geo-Replication [14]            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Deployment

```bash
# Deploy any project
cd project-{N}-{name}/infra
terraform init
terraform apply -var="environment=dev"
```

---

## Interview Resources

See **[INTERVIEW_GUIDE.md](./INTERVIEW_GUIDE.md)** for:
- Resume-ready project descriptions
- Technical deep-dive Q&A
- Architecture talking points
- Portfolio roadmap

---

## Cost Estimation (Dev Environment)

| Project | Monthly Cost (USD) |
|---------|-------------------|
| 1 - RAG Knowledge Copilot | $400-1,000 |
| 2 - Document Processing | $500-1,200 |
| 3 - Call Center Copilot | $600-1,500 |
| 4 - Agentic Platform | $400-1,000 |
| 5 - Fraud Detection | $600-1,500 |
| 6 - Customer 360 | $500-1,200 |
| 7 - Healthcare Clinical Copilot | $700-1,800 |
| 8 - Supply Chain Optimizer | $600-1,500 |
| 9 - IoT Predictive Maintenance | $500-1,200 |
| 10 - Code Review & DevOps Copilot | $400-1,000 |
| 11 - Legal Contract Analyzer | $400-1,000 |
| 12 - Real-Time Analytics Dashboard | $700-1,800 |
| 13 - Data Lakehouse | $600-1,500 |
| 14 - Multi-Region DR | $800-2,000 |
| 15 - HR Talent Intelligence | $500-1,200 |
| 16 - ESG & Sustainability Reporter | $600-1,500 |
| 17 - Knowledge Graph Builder | $500-1,200 |
| 18 - Multi-Modal Content Platform | $800-2,000 |
| 19 - Compliance Audit Automation | $500-1,200 |
| 20 - Energy & Utilities Smart Grid | $700-1,800 |
| 21 - Banking CRM Solution | $800-2,000 |
| 22 - AI Contact Center Platform | $900-2,500 |
| 23 - Contact Center Knowledge Base | $500-1,200 |
| 24 - AI Campaign Management | $700-1,800 |
| 25 - Digital Marketing & Product Intelligence | $700-1,800 |
| 26 - Voice AI Outbound Platform | $800-2,000 |
| **Full Portfolio** | **$15,000-38,000** |

*Production: 3-5x higher depending on scale*
