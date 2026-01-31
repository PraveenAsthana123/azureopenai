# Project 2: Intelligent Document Processing & Classification Pipeline

## Executive Summary

An enterprise document processing platform that automatically extracts, classifies, and routes documents using Azure Document Intelligence and custom ML models. Handles invoices, contracts, forms, and compliance documents with human-in-the-loop validation.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│              INTELLIGENT DOCUMENT PROCESSING & CLASSIFICATION                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT INGESTION LAYER                                   │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Email        │  │ SharePoint   │  │ SFTP/FTP     │  │ API Upload             │   │
│  │ (Logic Apps) │  │ (Connector)  │  │ (Data Factory│  │ (Functions)            │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                  │                      │               │
│         └─────────────────┴──────────────────┴──────────────────────┘               │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │  Azure Blob Storage │                                   │
│                           │  (Landing Zone)     │                                   │
│                           │  /incoming/         │                                   │
│                           └──────────┬──────────┘                                   │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │    Event Grid       │                                   │
│                           │  (Blob Created)     │                                   │
│                           └──────────┬──────────┘                                   │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    DOCUMENT PROCESSING ORCHESTRATOR                                  │
│                    (Durable Functions)                                               │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │   Orchestrator      │                                   │
│                           │   Function          │                                   │
│                           └──────────┬──────────┘                                   │
│                                      │                                              │
│         ┌────────────────────────────┼────────────────────────────┐                │
│         │                            │                            │                │
│         ▼                            ▼                            ▼                │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐            │
│  │ 1. EXTRACTION   │      │ 2. CLASSIFICATION│     │ 3. VALIDATION   │            │
│  │                 │      │                 │      │                 │            │
│  │ Document Intel. │      │ Azure ML Model  │      │ Business Rules  │            │
│  │ - Layout        │      │ - Custom CNN    │      │ - Schema check  │            │
│  │ - Invoice       │      │ - Categories:   │      │ - Required flds │            │
│  │ - Receipt       │      │   * Invoice     │      │ - Value ranges  │            │
│  │ - ID Document   │      │   * Contract    │      │ - Cross-field   │            │
│  │ - Custom model  │      │   * Form        │      │                 │            │
│  │                 │      │   * Compliance  │      │                 │            │
│  │ Output:         │      │   * HR Doc      │      │ Output:         │            │
│  │ - Text          │      │                 │      │ - Valid/Invalid │            │
│  │ - Tables        │      │ Output:         │      │ - Errors list   │            │
│  │ - Key-Values    │      │ - Category      │      │ - Confidence    │            │
│  │ - Confidence    │      │ - Confidence    │      │                 │            │
│  └────────┬────────┘      └────────┬────────┘      └────────┬────────┘            │
│           │                        │                        │                      │
│           └────────────────────────┼────────────────────────┘                      │
│                                    │                                               │
│                         ┌──────────▼──────────┐                                    │
│                         │  Confidence Check   │                                    │
│                         │  (Threshold: 0.85)  │                                    │
│                         └──────────┬──────────┘                                    │
│                                    │                                               │
│                    ┌───────────────┼───────────────┐                              │
│                    │               │               │                              │
│                    ▼               ▼               ▼                              │
│             ┌───────────┐   ┌───────────┐   ┌───────────┐                         │
│             │ HIGH      │   │ MEDIUM    │   │ LOW       │                         │
│             │ (≥0.85)   │   │ (0.6-0.85)│   │ (<0.6)    │                         │
│             │           │   │           │   │           │                         │
│             │ Auto-     │   │ Human     │   │ Manual    │                         │
│             │ Process   │   │ Review    │   │ Review    │                         │
│             └─────┬─────┘   └─────┬─────┘   └─────┬─────┘                         │
│                   │               │               │                               │
└───────────────────┼───────────────┼───────────────┼───────────────────────────────┘
                    │               │               │
                    │               ▼               │
                    │    ┌─────────────────────┐    │
                    │    │  HUMAN REVIEW UI    │    │
                    │    │  (Power Apps/React) │    │
                    │    │                     │    │
                    │    │  - View document    │    │
                    │    │  - Correct fields   │    │
                    │    │  - Approve/Reject   │    │
                    │    │  - Feedback loop    │    │
                    │    └──────────┬──────────┘    │
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────────────┐
│                    POST-PROCESSING & ROUTING                                       │
│                                    │                                              │
│                         ┌──────────▼──────────┐                                   │
│                         │   Route by Type     │                                   │
│                         └──────────┬──────────┘                                   │
│                                    │                                              │
│         ┌──────────────────────────┼──────────────────────────┐                  │
│         │                          │                          │                  │
│         ▼                          ▼                          ▼                  │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐          │
│  │ INVOICES        │      │ CONTRACTS       │      │ COMPLIANCE      │          │
│  │                 │      │                 │      │                 │          │
│  │ → SAP/D365      │      │ → SharePoint    │      │ → Compliance DB │          │
│  │ → AP Workflow   │      │ → Legal Review  │      │ → Audit Trail   │          │
│  │ → Payment Queue │      │ → Expiry Track  │      │ → Alert System  │          │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘          │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────┐
│                           DATA & METADATA STORE                                    │
│                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                          Cosmos DB                                           │  │
│  │                                                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ documents    │  │ extractions  │  │ reviews      │  │ audit_logs     │  │  │
│  │  │              │  │              │  │              │  │                │  │  │
│  │  │ - id         │  │ - doc_id     │  │ - doc_id     │  │ - timestamp    │  │  │
│  │  │ - filename   │  │ - fields     │  │ - reviewer   │  │ - action       │  │  │
│  │  │ - category   │  │ - confidence │  │ - decision   │  │ - user         │  │  │
│  │  │ - status     │  │ - model_ver  │  │ - corrections│  │ - changes      │  │  │
│  │  │ - blob_url   │  │ - timestamp  │  │ - feedback   │  │                │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
│  ┌──────────────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ ADLS Gen2 (Processed Documents)  │  │ Azure SQL (Reporting)                  │ │
│  │                                  │  │                                        │ │
│  │ /processed/{category}/{date}/   │  │ - Processing metrics                   │ │
│  │ /archived/{year}/{month}/       │  │ - Classification accuracy              │ │
│  │ /failed/{date}/                 │  │ - Review statistics                    │ │
│  └──────────────────────────────────┘  └────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────┐
│                           ML MODEL TRAINING PIPELINE                               │
│                                                                                    │
│  Human Review Feedback                                                             │
│         │                                                                          │
│         ▼                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐               │
│  │ Collect Training│───►│ Azure ML        │───►│ Register New    │               │
│  │ Data (Weekly)   │    │ Training Pipeline│    │ Model Version   │               │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘               │
│                                                          │                        │
│                                                          ▼                        │
│                                               ┌─────────────────┐                 │
│                                               │ A/B Deploy      │                 │
│                                               │ (Canary 10%)    │                 │
│                                               └─────────────────┘                 │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Document Classification Categories

| Category | Document Types | Key Fields Extracted |
|----------|----------------|---------------------|
| **Invoice** | Vendor invoices, Utility bills | Invoice #, Date, Amount, Vendor, Line items |
| **Contract** | Service agreements, NDAs, SOWs | Parties, Effective date, Term, Value, Clauses |
| **Form** | Application forms, Request forms | Form type, Applicant, Date, Fields |
| **Compliance** | KYC docs, AML forms, Audit docs | Entity, Date, Compliance type, Risk level |
| **HR Document** | Resumes, Offer letters, Reviews | Name, Position, Department, Date |

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Document Intelligence | OCR, Layout analysis, Pre-built models |
| Azure ML | Custom classification model |
| Durable Functions | Workflow orchestration |
| Event Grid | Event-driven triggers |
| Blob Storage | Document storage |
| ADLS Gen2 | Processed document lake |
| Cosmos DB | Metadata, extraction results |
| Logic Apps | Email ingestion, notifications |
| Power Apps | Human review interface |
| Key Vault | Secrets management |

---

## Processing Pipeline Flow

```
Document Upload
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│                    EXTRACTION PHASE                           │
│                                                               │
│  1. Detect document type (PDF, Image, TIFF)                  │
│  2. Call Document Intelligence (Layout + Pre-built)          │
│  3. Extract: Text, Tables, Key-Value pairs                   │
│  4. Store raw extraction in Cosmos DB                        │
└───────────────────────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│                 CLASSIFICATION PHASE                          │
│                                                               │
│  1. Generate document embedding                              │
│  2. Call Azure ML classification endpoint                    │
│  3. Get category + confidence score                          │
│  4. Apply category-specific extraction rules                 │
└───────────────────────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│                  VALIDATION PHASE                             │
│                                                               │
│  1. Schema validation (required fields)                      │
│  2. Business rule validation                                 │
│  3. Cross-reference checks (vendor exists, etc.)            │
│  4. Calculate overall confidence                             │
└───────────────────────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────────────────────┐
│                   ROUTING PHASE                               │
│                                                               │
│  High Confidence (≥85%): Auto-process                        │
│  Medium Confidence (60-85%): Human review queue              │
│  Low Confidence (<60%): Manual processing queue              │
└───────────────────────────────────────────────────────────────┘
```

---

## Interview Talking Points

### Architecture Decisions

1. **Why Durable Functions over Logic Apps for orchestration?**
   - Complex branching logic
   - Better error handling and retry policies
   - Code-based (testable, version controlled)
   - Fan-out/fan-in for parallel processing

2. **Why custom ML model instead of just Document Intelligence?**
   - Domain-specific classification needs
   - Continuous improvement from human feedback
   - Handle edge cases not covered by pre-built models

3. **Human-in-the-loop design benefits:**
   - Catches ML errors before downstream impact
   - Generates training data for model improvement
   - Compliance requirement for financial documents

4. **Why Cosmos DB for metadata?**
   - Flexible schema for different document types
   - Sub-10ms lookups for status checks
   - Change feed for real-time updates

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2B / B2E (Business-to-Business + Business-to-Employee)
- **Visibility:** Internal + Partner Portal — employees and authorized partners
- **Project Score:** 8.0 / 10 (Standard)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Private Link | Document Intelligence, Storage, Cosmos DB via private endpoints |
| Network | VNet Isolation | Dedicated VNet with NSG rules, no public endpoints |
| Identity | Managed Identity | System-assigned MI for all inter-service communication |
| Identity | RBAC | Per-resource role assignments; document-level access control |
| Data | Encryption at Rest | AES-256 for all stored documents and metadata |
| Data | Encryption in Transit | TLS 1.2+ on all connections |
| Data | Key Vault | OCR keys, storage keys, connection strings in Key Vault |
| Data | PII Redaction | Automated PII detection and redaction before indexing |
| Application | Content Validation | Document format validation and malware scanning on upload |
| Monitoring | Log Analytics | Full processing pipeline audit trail |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Data Classification | Confidential | Processed documents may contain PII, financial data |
| Document Retention | Policy-driven | Configurable retention per document type (1-7 years) |
| PII Handling | Automated redaction | PII detected and masked before downstream processing |
| Data Lineage | Tracked | Full lineage from upload → extraction → classification → routing |
| Processing Audit | Complete | Every document processing step logged with timestamps |
| Human-in-the-Loop | Confidence-based | Low-confidence extractions routed for human review |

### Regulatory Applicability
- **GDPR:** PII redaction, right to erasure for personal documents
- **SOC 2 Type II:** Processing audit trail
- **Industry-specific:** Configurable per document type (healthcare, financial, legal)
