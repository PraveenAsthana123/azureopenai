# Data Governance Framework — Azure OpenAI Enterprise RAG Platform

> **Enterprise Data Governance for AI-Driven Knowledge Retrieval**
>
> Aligned with CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF

---

## Table of Contents

1. [Data Ownership Matrix](#1-data-ownership-matrix)
2. [Data Catalog Structure](#2-data-catalog-structure)
3. [Data Lineage](#3-data-lineage)
4. [Data Quality Framework](#4-data-quality-framework)
5. [Data Classification Policy](#5-data-classification-policy)
6. [Data Retention Schedule](#6-data-retention-schedule)
7. [Data Access Request Workflow](#7-data-access-request-workflow)
8. [Data Steward Responsibilities](#8-data-steward-responsibilities)
9. [Master Data Management](#9-master-data-management)
10. [Data Lifecycle Management](#10-data-lifecycle-management)
11. [Data Quality Metrics & Monitoring](#11-data-quality-metrics--monitoring)
12. [Data Anomaly Detection](#12-data-anomaly-detection)
13. [GDPR/CCPA Data Subject Rights](#13-gdprccpa-data-subject-rights)
14. [Data Breach Response Procedure](#14-data-breach-response-procedure)
15. [Cross-References](#15-cross-references)

---

## 1. Data Ownership Matrix

Every data domain within the platform has an assigned **Data Owner** (accountable), **Data Steward** (responsible for day-to-day quality), and a defined **Classification** and **Retention** policy.

| Data Domain | Owner | Steward | Classification | Retention |
|-------------|-------|---------|----------------|-----------|
| **Customer Documents** | Head of Operations | Document Ops Lead | Confidential | 7 years |
| **Policy & Compliance** | Chief Compliance Officer | Compliance Analyst | Restricted | 10 years |
| **HR Knowledge Base** | CHRO | HR Systems Lead | Confidential | 5 years |
| **Financial Reports** | CFO | Finance Data Lead | Restricted | 7 years (SOX) |
| **Product Documentation** | VP Engineering | Tech Writing Lead | Internal | 3 years |
| **Marketing Content** | CMO | Content Ops Manager | Public | 2 years |
| **IT Runbooks** | CTO | Platform Ops Lead | Internal | Until superseded |
| **Legal Documents** | General Counsel | Legal Ops Analyst | Restricted | 10 years |
| **Research & Analytics** | Chief Data Officer | Analytics Lead | Confidential | 5 years |
| **Conversation Logs** | Platform Team Lead | AI Ops Engineer | Confidential | 90 days |
| **Audit Events** | CISO | Security Ops Lead | Restricted | 7 years |
| **Embeddings & Indexes** | Platform Team Lead | ML Ops Engineer | Internal | Until reindexed |

### Ownership Escalation Path

```
Data Steward (daily quality)
    │
    ▼
Data Owner (domain accountability)
    │
    ▼
Data Governance Council (cross-domain disputes)
    │
    ▼
AI Governance Board (strategic decisions)
```

---

## 2. Data Catalog Structure

### Microsoft Purview Integration

The platform leverages **Microsoft Purview** as the central data catalog, providing unified data discovery, classification, and lineage tracking across all Azure services.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Microsoft Purview                            │
├─────────────────┬──────────────────┬────────────────────────────┤
│   Data Map      │   Data Catalog   │   Data Estate Insights     │
│   (Discovery)   │   (Glossary)     │   (Analytics)              │
├─────────────────┼──────────────────┼────────────────────────────┤
│ • Azure Blob    │ • Business Terms │ • Classification coverage  │
│ • Cosmos DB     │ • Definitions    │ • Sensitivity distribution │
│ • AI Search     │ • Relationships  │ • Ownership gaps           │
│ • SQL Database  │ • Stewards       │ • Stale asset detection    │
└─────────────────┴──────────────────┴────────────────────────────┘
```

### Purview Collections Hierarchy

| Collection | Scope | Assets Registered | Scan Frequency |
|------------|-------|-------------------|----------------|
| **Enterprise RAG** (root) | All platform assets | -- | -- |
| ├── **Raw Documents** | Source PDFs, DOCX, HTML | Azure Blob containers | Daily |
| ├── **Processed Data** | Extracted text, metadata JSON | Azure Blob processed/ | Daily |
| ├── **Chunked Data** | Segmented text chunks | Cosmos DB chunks container | Daily |
| ├── **Embeddings** | Vector representations | Azure AI Search index | Weekly |
| ├── **Conversation Data** | User sessions, queries | Cosmos DB conversations | Weekly |
| └── **Audit & Logs** | Audit events, telemetry | Log Analytics workspace | Monthly |

### Glossary Terms

| Term | Definition | Domain | Steward |
|------|-----------|--------|---------|
| **Chunk** | A segment of a source document (typically 512-1024 tokens) used for retrieval | Platform | ML Ops Engineer |
| **Embedding** | Dense vector representation of a text chunk (1536 or 3072 dimensions) | Platform | ML Ops Engineer |
| **Retrieval Score** | Relevance score (0-1) assigned to a chunk for a given query | Platform | AI Ops Engineer |
| **Grounding** | Process of anchoring LLM responses to source documents | AI | AI Ops Engineer |
| **PII Entity** | Personally Identifiable Information detected by Presidio/Azure AI Language | Security | Security Ops Lead |
| **Document Freshness** | Time since last update relative to effectiveDate metadata | Quality | Document Ops Lead |
| **Canonical Source** | The single authoritative version of a document across all systems | MDM | Data Steward |

### Classification Labels in Purview

| Label | Sensitivity | Auto-Applied | Scan Rule |
|-------|-------------|--------------|-----------|
| `sensitivity/public` | Public | Yes | Default classification rule |
| `sensitivity/internal` | Internal | Yes | Internal keyword patterns |
| `sensitivity/confidential` | Confidential | Yes | PII entity detection |
| `sensitivity/restricted` | Restricted | No | Manual + AI-assisted review |
| `pii/detected` | Confidential+ | Yes | Presidio NER scan |
| `financial/sox-regulated` | Restricted | Yes | SOX keyword + metadata match |
| `legal/privilege` | Restricted | No | Manual legal review |

---

## 3. Data Lineage

### End-to-End Lineage: Source to Response

The following diagram traces a document from its original source through every transformation stage in the RAG pipeline, ending with the generated response delivered to the user.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   SOURCE     │    │     RAW      │    │  PROCESSED   │    │   CHUNKED    │
│              │    │              │    │              │    │              │
│ • SharePoint │───▶│ Azure Blob   │───▶│ Azure Blob   │───▶│ Cosmos DB    │
│ • File Share │    │ raw/         │    │ processed/   │    │ chunks       │
│ • API Feed   │    │              │    │              │    │ container    │
│ • Email      │    │ Original     │    │ Extracted    │    │              │
│ • Database   │    │ binary files │    │ text + meta  │    │ 512-1024 tok │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                         ┌─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   EMBEDDED   │    │   INDEXED    │    │  RETRIEVED   │    │   RESPONSE   │
│              │    │              │    │              │    │              │
│ Azure OpenAI │───▶│ Azure AI     │───▶│ Top-K chunks │───▶│ Azure OpenAI │
│ Embedding    │    │ Search       │    │ + reranking  │    │ GPT-4o       │
│ Model        │    │              │    │              │    │              │
│              │    │ Vector +     │    │ Semantic      │    │ Grounded     │
│ 3072-dim     │    │ keyword index│    │ ranker       │    │ answer       │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Lineage Metadata Schema

Each document carries lineage metadata through every stage:

```json
{
  "lineage": {
    "sourceId": "sharepoint://sites/policies/aml-policy-v4.pdf",
    "sourceSystem": "SharePoint Online",
    "ingestTimestamp": "2024-11-15T08:00:00Z",
    "rawBlobPath": "raw/policies/aml-policy-v4.pdf",
    "processedBlobPath": "processed/policies/aml-policy-v4.json",
    "extractionMethod": "azure-document-intelligence-v4",
    "chunkIds": ["chunk_001", "chunk_002", "chunk_045"],
    "chunkingStrategy": "semantic",
    "embeddingModel": "text-embedding-3-large",
    "embeddingDimension": 3072,
    "indexName": "enterprise-rag-index",
    "indexTimestamp": "2024-11-15T08:15:00Z",
    "piiScanResult": "clean",
    "classificationLabel": "sensitivity/confidential",
    "version": 4,
    "effectiveDate": "2024-10-01",
    "purviewAssetId": "purview://assets/aml-policy-v4"
  }
}
```

### Lineage Tracking in Purview

| Stage | Azure Service | Purview Asset Type | Lineage Connector |
|-------|---------------|--------------------|--------------------|
| Source | SharePoint / File Share | Data Source | Built-in connector |
| Raw | Azure Blob Storage | Azure Blob | Built-in connector |
| Processed | Azure Blob Storage | Azure Blob | Custom lineage API |
| Chunked | Cosmos DB | NoSQL Document | Custom lineage API |
| Embedded | Azure OpenAI | Custom Asset | Custom lineage API |
| Indexed | Azure AI Search | Custom Asset | Custom lineage API |
| Response | Azure OpenAI | Custom Asset | Audit event linkage |

---

## 4. Data Quality Framework

### Quality Dimensions

| Dimension | Definition | Metric | Target | Measurement Method | Frequency |
|-----------|-----------|--------|--------|-------------------|-----------|
| **Accuracy** | Data correctly represents the real-world entity | Error rate in extracted text vs. source | < 2% | OCR confidence + human spot-check | Weekly |
| **Completeness** | All required fields and sections are present | % documents with all metadata fields populated | > 98% | Schema validation on ingest | Per batch |
| **Timeliness** | Data reflects the most current version | Avg. delay from source update to index refresh | < 4 hours | Timestamp diff: source vs. index | Daily |
| **Consistency** | Same data does not conflict across stores | % chunks matching canonical source hash | 100% | Hash comparison: blob vs. index | Weekly |
| **Validity** | Data conforms to defined formats and rules | % records passing schema validation | > 99.5% | JSON Schema + business rule checks | Per batch |
| **Uniqueness** | No unintended duplicate records exist | Duplicate chunk ratio across index | < 0.5% | MinHash dedup scan | Weekly |
| **Provenance** | Origin and transformation history is traceable | % documents with complete lineage metadata | 100% | Lineage field completeness check | Daily |

### Quality Scoring Model

Each document receives a composite **Data Quality Score (DQS)** on a 0-100 scale:

```
DQS = (Accuracy × 0.25) + (Completeness × 0.20) + (Timeliness × 0.15)
    + (Consistency × 0.15) + (Validity × 0.10) + (Uniqueness × 0.10)
    + (Provenance × 0.05)

Quality Tiers:
  90-100  →  Gold    (production-ready, no issues)
  75-89   →  Silver  (usable, minor issues flagged)
  50-74   →  Bronze  (review required before use)
  0-49    →  Reject  (quarantined, not indexed)
```

### Quality Gate Enforcement

| Pipeline Stage | Gate | Fail Action |
|---------------|------|-------------|
| Ingestion | File type + size validation | Reject to dead-letter queue |
| Extraction | OCR confidence > 80% | Route to manual review |
| Metadata | Required fields present | Block until remediated |
| Chunking | Chunk size within bounds | Re-chunk with fallback strategy |
| Embedding | Vector dimension check | Re-embed with correct model |
| Indexing | Schema conformance | Reject, alert Data Steward |
| Retrieval | Relevance score > threshold | Filter from results, log anomaly |

---

## 5. Data Classification Policy

### Classification Levels

| Level | Definition | Examples | Controls | Labeling |
|-------|-----------|----------|----------|----------|
| **Public** | Information approved for unrestricted distribution | Marketing brochures, press releases, public FAQ | No special controls; standard access logging | `sensitivity/public` — green label |
| **Internal** | Information for internal use; not harmful if exposed but not intended for public | IT runbooks, product docs, internal wikis, meeting notes | Entra ID authentication required; no external sharing | `sensitivity/internal` — blue label |
| **Confidential** | Sensitive business information; disclosure causes measurable harm | Customer data, financial forecasts, HR records, contracts | RBAC with least-privilege; encryption at rest (CMK); audit logging; DLP policies | `sensitivity/confidential` — amber label |
| **Restricted** | Highly sensitive; regulatory or legal obligations; severe harm if disclosed | PII datasets, PCI card data, SOX financial records, legal privilege, trade secrets | MFA + Privileged Identity Management; CMK encryption; network isolation; real-time monitoring; DLP block | `sensitivity/restricted` — red label |

### Classification Decision Tree

```
Contains PII?
├── Yes ──▶ Contains PCI / health / regulated data?
│           ├── Yes ──▶ RESTRICTED
│           └── No  ──▶ CONFIDENTIAL
└── No  ──▶ Approved for public distribution?
            ├── Yes ──▶ PUBLIC
            └── No  ──▶ Contains business-sensitive content?
                        ├── Yes ──▶ CONFIDENTIAL
                        └── No  ──▶ INTERNAL
```

### Auto-Classification Rules

| Rule Name | Detection Method | Classification Assigned | Confidence Threshold |
|-----------|-----------------|------------------------|---------------------|
| PII Detection | Azure AI Language NER + Presidio | Confidential (minimum) | > 0.85 |
| Credit Card Numbers | Regex + Luhn check | Restricted | > 0.99 |
| SOX Financial Keywords | Keyword dictionary + metadata | Restricted | > 0.90 |
| Legal Privilege | Manual review flag + keyword | Restricted | Manual only |
| Internal Watermark | Document metadata property | Internal | > 0.95 |
| Public Approval Tag | SharePoint approval workflow | Public | Workflow complete |

---

## 6. Data Retention Schedule

### Consolidated Retention Table

| Data Type | Storage Location | Retention Period | Archive Policy | Deletion Method | Legal Hold Override |
|-----------|-----------------|-----------------|----------------|-----------------|---------------------|
| **Source Documents** | Azure Blob (raw/) | 7 years | Move to Cool tier at 1 year; Archive at 3 years | Soft delete + 30-day recovery → permanent purge | Yes |
| **Processed Text** | Azure Blob (processed/) | 7 years | Align with source document | Cascade delete with source | Yes |
| **Chunks** | Cosmos DB | Until reindexed + 90 days | Not archived (regenerable) | TTL policy auto-delete | Yes |
| **Embeddings** | Azure AI Search | Until reindexed | Not archived (regenerable) | Index rebuild excludes stale | No |
| **Conversation Logs** | Cosmos DB | 90 days | Not archived | TTL auto-delete | Yes |
| **Session Data** | Cosmos DB | 30 days | Not archived | TTL auto-delete | No |
| **Feedback Records** | Cosmos DB | 1 year | Archive to Blob at 6 months | Soft delete after archive | Yes |
| **Audit Events** | Cosmos DB + Log Analytics | 7 years | Archive to Blob at 1 year | Pseudonymize PII, retain record | Always retained |
| **Telemetry / Metrics** | Application Insights | 90 days | Export to Log Analytics (2 years) | Auto-purge by workspace policy | No |
| **PII Scan Results** | Cosmos DB | 1 year | Archive with source lineage | Cascade with source document | Yes |
| **Model Evaluation Logs** | Azure Blob | 3 years | Cool tier at 6 months | Soft delete + purge | No |
| **User Consent Records** | Cosmos DB | Duration of relationship + 3 years | Archive at account closure | Hard delete after retention | Yes |

### Retention Enforcement

```yaml
# Azure Blob Storage lifecycle management policy
policy:
  name: "rag-platform-retention-policy"
  rules:
    - name: "raw-documents-lifecycle"
      filters: { blobTypes: ["blockBlob"], prefixMatch: ["raw/"] }
      actions:
        tierToCool: { daysAfterModification: 365 }
        tierToArchive: { daysAfterModification: 1095 }
        delete: { daysAfterModification: 2555 }
    - name: "processed-documents-lifecycle"
      filters: { blobTypes: ["blockBlob"], prefixMatch: ["processed/"] }
      actions:
        tierToCool: { daysAfterModification: 365 }
        delete: { daysAfterModification: 2555 }
```

---

## 7. Data Access Request Workflow

### Access Request Flowchart

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   REQUEST    │    │   APPROVAL   │    │ PROVISIONING │    │    AUDIT     │
│              │    │              │    │              │    │              │
│ User submits │───▶│ Auto-route   │───▶│ Entra ID     │───▶│ Access event │
│ access form  │    │ to approver  │    │ group/role   │    │ logged       │
│ via portal   │    │ based on     │    │ assignment   │    │              │
│              │    │ data class.  │    │              │    │ Periodic     │
│ Specify:     │    │              │    │ JIT where    │    │ access       │
│ • Data domain│    │ SLA:         │    │ applicable   │    │ review       │
│ • Justificat.│    │ Internal: 1d │    │              │    │ triggered    │
│ • Duration   │    │ Confid.: 3d  │    │ Notification │    │              │
│ • Scope      │    │ Restrict: 5d │    │ sent to user │    │ Quarterly    │
│              │    │              │    │              │    │ recertificat.│
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                    │
       │                   │                   │                    │
       ▼                   ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        ServiceNow / Azure DevOps Ticket                  │
│   Tracks: request ID, requestor, approver, decision, provision date,     │
│           expiry date, access scope, quarterly review status             │
└──────────────────────────────────────────────────────────────────────────┘
```

### Approval Matrix

| Data Classification | Approver | Additional Approval | Max Duration | Review Cycle |
|--------------------|----------|---------------------|--------------|-------------|
| **Public** | Auto-approved | None | Permanent | Annual |
| **Internal** | Data Steward | None | 1 year | Semi-annual |
| **Confidential** | Data Owner | None | 6 months | Quarterly |
| **Restricted** | Data Owner | CISO or Compliance Officer | 90 days (JIT preferred) | Monthly |

### Access Revocation Triggers

| Trigger | Action | Timeline |
|---------|--------|----------|
| Role change / transfer | Revoke domain-specific access | Within 24 hours |
| Employment termination | Revoke all access | Immediate |
| Access duration expired | Auto-revoke via PIM | At expiry |
| Quarterly review — no justification | Revoke and notify manager | Within 5 business days |
| Security incident involving data | Emergency revoke | Immediate |

---

## 8. Data Steward Responsibilities

### Steward Accountability Matrix

| Domain | Steward Role | Key Responsibilities |
|--------|-------------|---------------------|
| **Customer Documents** | Document Ops Lead | Validate document extraction quality; manage versioning; ensure freshness SLA; coordinate with source system owners |
| **Policy & Compliance** | Compliance Analyst | Verify regulatory document accuracy; manage effective dates; ensure superseded docs are archived; coordinate legal review |
| **HR Knowledge Base** | HR Systems Lead | Enforce PII masking; manage employee data lifecycle; ensure consent compliance; coordinate with HRIS team |
| **Financial Reports** | Finance Data Lead | Validate SOX-regulated data; manage quarterly reporting cycles; ensure segregation of duties; coordinate with audit team |
| **Product Documentation** | Tech Writing Lead | Manage doc versioning; coordinate release-aligned updates; ensure API doc accuracy; handle deprecation notices |
| **Marketing Content** | Content Ops Manager | Manage brand compliance; ensure approval workflows; coordinate campaign content lifecycle; handle public classification |
| **IT Runbooks** | Platform Ops Lead | Maintain operational accuracy; manage incident-driven updates; coordinate with SRE team; ensure runbook testing |
| **Legal Documents** | Legal Ops Analyst | Enforce privilege classification; manage contract lifecycle; coordinate with outside counsel; handle litigation holds |
| **Research & Analytics** | Analytics Lead | Validate analytical models; manage experiment data; ensure reproducibility; coordinate with data science team |
| **Conversation Logs** | AI Ops Engineer | Monitor conversation quality; manage TTL enforcement; ensure PII scrubbing; coordinate with privacy team |
| **Audit Events** | Security Ops Lead | Ensure audit completeness; manage retention compliance; coordinate with internal audit; handle regulatory inquiries |

---

## 9. Master Data Management

### Document Deduplication

The platform enforces a **single canonical source** for each document to prevent conflicting versions from entering the RAG index.

```
┌──────────────────────────────────────────────────────────────────┐
│                  Document Deduplication Pipeline                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Ingest Queue ──▶ Hash Computation ──▶ Dedup Check ──▶ Decision │
│                   (SHA-256 + SimHash)  (Cosmos DB      │         │
│                                        dedup registry) │         │
│                                                        ▼         │
│                                              ┌─────────────────┐ │
│                                              │ New document?   │ │
│                                              │ Yes → Index     │ │
│                                              │ No  → Version?  │ │
│                                              │   Newer → Update│ │
│                                              │   Same  → Skip  │ │
│                                              │   Older → Skip  │ │
│                                              └─────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Deduplication Methods

| Method | Purpose | Implementation | Scope |
|--------|---------|---------------|-------|
| **SHA-256 Hash** | Exact duplicate detection | Hash of raw file bytes | Cross-source ingestion |
| **SimHash** | Near-duplicate detection | Similarity hash of extracted text | Within same domain |
| **MinHash + LSH** | Chunk-level dedup | Locality-sensitive hashing on chunk text | Index maintenance |
| **Metadata Match** | Logical duplicate detection | Match on title + source + effectiveDate | Canonical source resolution |

### Versioning Strategy

```json
{
  "documentId": "doc-aml-policy",
  "canonicalSourceId": "sharepoint://sites/policies/aml-policy.pdf",
  "activeVersion": 4,
  "versions": [
    { "version": 4, "effectiveDate": "2024-10-01", "status": "active",
      "blobPath": "raw/policies/aml-policy-v4.pdf", "indexedChunks": 45 },
    { "version": 3, "effectiveDate": "2024-01-15", "status": "superseded",
      "blobPath": "raw/policies/aml-policy-v3.pdf", "indexedChunks": 0 }
  ],
  "retainSuperseded": true,
  "retentionPolicy": "7-year"
}
```

### Canonical Source Resolution Rules

| Scenario | Resolution | Outcome |
|----------|-----------|---------|
| Same document from multiple sources | Priority: SharePoint > File Share > Email | Highest priority source becomes canonical |
| Version conflict (same source) | Compare effectiveDate | Most recent effectiveDate wins |
| Version conflict (cross-source) | Escalate to Data Steward | Manual resolution within 48 hours |
| Duplicate chunk detected at index time | Keep first indexed; flag second | Dedup report generated |
| Stale document (no update beyond SLA) | Alert Data Steward | Review and confirm or retire |

---

## 10. Data Lifecycle Management

### Lifecycle Stages with Azure Services

```
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│  CREATION  │  │ PROCESSING │  │  STORAGE   │  │  ARCHIVE   │  │  DELETION  │
│            │  │            │  │            │  │            │  │            │
│ Azure Blob │  │ Azure      │  │ Azure Blob │  │ Azure Blob │  │ Lifecycle  │
│ Storage    │  │ Functions  │  │ (Hot/Cool) │  │ (Archive)  │  │ Management │
│ (raw/)     │  │ + Doc      │  │ Cosmos DB  │  │            │  │ Policy     │
│            │  │ Intelligence│  │ AI Search  │  │ Cosmos DB  │  │            │
│ Event Grid │  │            │  │            │  │ Analytical │  │ Soft Delete│
│ trigger    │  │ Presidio   │  │ Key Vault  │  │ Store      │  │ + Purge    │
│            │  │ PII scan   │  │ (CMK)      │  │            │  │            │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │               │               │
      ▼               ▼               ▼               ▼               ▼
  Ingest via      Extract text,    Serve queries,   Long-term       Permanent
  connectors      classify,        real-time        retention,      removal per
  or upload       chunk, embed     retrieval        compliance      retention
  API                                                               schedule
```

### Lifecycle Policy per Data Category

| Data Category | Creation | Processing | Active Storage | Archive | Deletion |
|---------------|----------|-----------|---------------|---------|----------|
| **Source Documents** | Blob upload / connector sync | Doc Intelligence extraction | Hot tier (0-365 days) | Archive tier (365-2555 days) | Purge at 2555 days |
| **Processed Text** | Azure Function output | Schema validation | Hot tier (0-365 days) | Cascade with source | Cascade with source |
| **Chunks** | Chunking pipeline | Embedding generation | Cosmos DB (active) | Not archived (regenerable) | TTL: reindex + 90d |
| **Embeddings** | Azure OpenAI API | Index upsert | AI Search (active) | Not archived (regenerable) | Index rebuild |
| **Conversations** | User interaction | PII scan + log | Cosmos DB (0-90 days) | Not archived | TTL: 90 days |
| **Audit Events** | System-generated | Enrichment + correlation | Cosmos DB (0-365 days) | Blob archive (365-2555 days) | Pseudonymize at 2555d |

### Lifecycle Transition Automation

```yaml
# Azure Event Grid + Functions lifecycle automation
lifecycle_triggers:
  creation:
    event: "Microsoft.Storage.BlobCreated"
    handler: "func-document-ingest"
    actions: [register_in_purview, classify_sensitivity, start_processing_pipeline]
  processing_complete:
    event: "custom.DocumentProcessed"
    handler: "func-post-process"
    actions: [validate_quality_gates, update_lineage_metadata, trigger_embedding]
  archive_transition:
    event: "timer.daily"
    handler: "func-lifecycle-manager"
    actions: [check_retention_policies, transition_eligible_blobs, update_purview]
  deletion:
    event: "timer.daily"
    handler: "func-deletion-manager"
    actions: [check_legal_holds, execute_soft_delete, log_deletion_event]
```

---

## 11. Data Quality Metrics & Monitoring

### KQL Queries for Data Quality Checks

**Document Extraction Quality:**

```kql
// Monitor OCR confidence scores across document types
CustomMetrics
| where Name == "document_extraction_confidence"
| where Timestamp > ago(7d)
| extend docType = tostring(CustomDimensions.documentType)
| summarize
    avgConfidence = avg(Value),
    minConfidence = min(Value),
    p95Confidence = percentile(Value, 95),
    totalDocs = count()
  by docType, bin(Timestamp, 1d)
| where avgConfidence < 0.85
| order by avgConfidence asc
```

**Chunk Quality and Completeness:**

```kql
// Detect documents with missing or malformed chunks
CustomEvents
| where Name == "chunk_created"
| where Timestamp > ago(24h)
| extend documentId = tostring(CustomDimensions.documentId),
         chunkCount = toint(CustomDimensions.chunkCount),
         avgChunkSize = todouble(CustomDimensions.avgChunkTokens)
| summarize totalChunks = sum(chunkCount),
            avgSize = avg(avgChunkSize),
            docs = dcount(documentId)
| where avgSize < 100 or avgSize > 2000
```

**Index Freshness Check:**

```kql
// Identify stale documents not reindexed within SLA
let freshnessThreshold = 4h;
CustomEvents
| where Name == "document_indexed"
| where Timestamp > ago(7d)
| extend documentId = tostring(CustomDimensions.documentId),
         sourceModified = todatetime(CustomDimensions.sourceModifiedTime),
         indexedTime = Timestamp
| extend staleness = indexedTime - sourceModified
| where staleness > freshnessThreshold
| project documentId, sourceModified, indexedTime, staleness
| order by staleness desc
| take 50
```

### Quality Monitoring Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Extraction quality drop | Avg. OCR confidence < 0.80 over 1 hour | Sev 2 | Page Data Steward + ML Ops |
| Embedding failure spike | Success rate < 99% over 15 min | Sev 1 | Page Platform On-Call |
| Index staleness breach | Any document > 4 hours stale | Sev 3 | Notify Data Steward |
| DQS below threshold | Domain avg. DQS < 75 | Sev 2 | Quarantine + notify Owner |
| Dedup anomaly | Duplicate ratio > 2% in batch | Sev 3 | Flag batch for review |
| Schema validation failure | > 5% records fail validation in batch | Sev 2 | Halt pipeline, alert Ops |

---

## 12. Data Anomaly Detection

### Anomaly Detection Rules

| Anomaly Type | Detection Method | Threshold | Action |
|-------------|-----------------|-----------|--------|
| **Volume Spike** | Z-score on daily ingest count | > 3 standard deviations | Alert Data Steward; hold batch for review |
| **Volume Drop** | Z-score on daily ingest count | > 2 standard deviations below mean | Alert Data Steward; verify source connectivity |
| **Schema Drift** | Compare ingest schema to registered schema | Any new/missing field | Block ingest; notify Data Steward |
| **Classification Shift** | % documents per classification level vs. baseline | > 10% shift in any level | Alert Security; review classification rules |
| **PII Leak** | PII detected in fields marked PII-free | Any detection | Quarantine document; alert Security Ops |
| **Embedding Drift** | Cosine similarity of new embeddings vs. centroid | Average similarity < 0.70 | Alert ML Ops; investigate model or data change |
| **Chunk Size Anomaly** | Chunk token count outside expected range | < 50 or > 2048 tokens | Route to manual review; adjust chunking config |
| **Duplicate Surge** | Duplicate ratio in single batch | > 5% duplicates | Halt batch; investigate source system |
| **Latency Anomaly** | Processing time per document vs. rolling average | > 3x rolling average | Alert Platform Ops; check service health |
| **Quality Score Drop** | Domain DQS week-over-week change | > 10-point drop | Escalate to Data Owner; root cause analysis |
| **Source Connectivity** | Connector health check failure | 3 consecutive failures | Alert Platform Ops; switch to backup connector |
| **Metadata Completeness** | % records missing required metadata fields | > 2% in batch | Reject batch; notify source system owner |

### Anomaly Detection Implementation

```python
# anomaly_detector.py — Core detection methods
import numpy as np
from azure.monitor.query import MetricsQueryClient
from azure.identity import DefaultAzureCredential

class DataAnomalyDetector:
    """Detects anomalies in the RAG data pipeline."""

    VOLUME_ZSCORE_THRESHOLD = 3.0
    EMBEDDING_SIMILARITY_THRESHOLD = 0.70
    CHUNK_SIZE_BOUNDS = (50, 2048)

    def detect_volume_anomaly(self, daily_counts: list[int]) -> dict:
        """Detect unusual ingest volume using Z-score."""
        mean, std = np.mean(daily_counts), np.std(daily_counts)
        if std == 0:
            return {"anomaly": False}
        zscore = (daily_counts[-1] - mean) / std
        return {"anomaly": abs(zscore) > self.VOLUME_ZSCORE_THRESHOLD,
                "zscore": round(zscore, 2),
                "direction": "spike" if zscore > 0 else "drop"}

    def detect_embedding_drift(self, new_embeddings: np.ndarray,
                                centroid: np.ndarray) -> dict:
        """Detect drift in embedding space vs. domain centroid."""
        sims = np.dot(new_embeddings, centroid) / (
            np.linalg.norm(new_embeddings, axis=1) * np.linalg.norm(centroid))
        avg_sim = float(np.mean(sims))
        return {"anomaly": avg_sim < self.EMBEDDING_SIMILARITY_THRESHOLD,
                "avg_similarity": round(avg_sim, 4)}
```

---

## 13. GDPR/CCPA Data Subject Rights

> **Cross-reference:** For full GDPR implementation details, consent management, and PCI-DSS compliance, see [DATA-PRIVACY-COMPLIANCE.md](../security/DATA-PRIVACY-COMPLIANCE.md).

### Data Subject Rights Matrix

| Right | GDPR Article | CCPA Section | Implementation | SLA |
|-------|-------------|-------------|----------------|-----|
| **Right of Access** | Art. 15 | 1798.100 | DSAR portal → automated data export from Cosmos DB, Blob, Log Analytics | 30 days |
| **Right to Rectification** | Art. 16 | — | Source document update → reprocess → reindex pipeline | 15 days |
| **Right to Erasure** | Art. 17 | 1798.105 | Deletion pipeline: Cosmos DB → Blob → Search Index → Log pseudonymization | 30 days |
| **Right to Restriction** | Art. 18 | — | Flag user records → exclude from processing → retain in storage | 5 business days |
| **Right to Portability** | Art. 20 | 1798.100 | Export to JSON/CSV → encrypted transfer via Azure Blob SAS token | 30 days |
| **Right to Object** | Art. 21 | 1798.120 | Opt-out flag in user profile → exclude from analytics/AI training | 5 business days |
| **Automated Decision Opt-Out** | Art. 22 | 1798.185 | Route to human review queue; disable AI-only decisions for user | Immediate |

### DSAR Processing Workflow

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Data Subject Access Request (DSAR)                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. INTAKE              2. IDENTITY           3. DATA                  │
│  ┌──────────────┐       ┌──────────────┐      ┌──────────────┐        │
│  │ DSAR Portal  │──────▶│ Entra ID     │─────▶│ Automated    │        │
│  │ or Privacy   │       │ verification │      │ data search  │        │
│  │ email        │       │ + MFA        │      │ across all   │        │
│  └──────────────┘       └──────────────┘      │ data stores  │        │
│                                                └──────┬───────┘        │
│                                                       │                │
│  4. REVIEW              5. EXECUTE            6. CONFIRM               │
│  ┌──────────────┐       ┌──────────────┐      ┌──────────────┐        │
│  │ Privacy team │──────▶│ Access: export│─────▶│ Send report  │        │
│  │ reviews data │       │ Erase: delete │      │ to data      │        │
│  │ scope        │       │ Rectify: fix  │      │ subject      │        │
│  └──────────────┘       │ Port: package │      │              │        │
│                         └──────────────┘      │ Log in audit │        │
│                                                └──────────────┘        │
└────────────────────────────────────────────────────────────────────────┘
```

### Erasure Implementation Details

| Data Store | Erasure Method | Verification | Exceptions |
|-----------|---------------|-------------|------------|
| **Cosmos DB (conversations)** | Hard delete by partition key (userId) | Query returns 0 results | Legal hold check first |
| **Cosmos DB (feedback)** | Hard delete by userId index | Query returns 0 results | Anonymize if needed for model improvement |
| **Azure Blob (user uploads)** | Soft delete → permanent purge after 30 days | Blob existence check | Legal hold blocks purge |
| **Azure AI Search** | Remove documents by userId filter → partial reindex | Search returns 0 for userId | N/A |
| **Log Analytics** | Pseudonymize userId → hash; retain log structure | Grep for original userId returns 0 | Audit logs retained with pseudonym |
| **Application Insights** | Purge API for specific user telemetry | Purge status confirmed | 30-day propagation delay |

---

## 14. Data Breach Response Procedure

> **Cross-reference:** For full incident response playbook and security escalation procedures, see [SECURITY-COMPLIANCE.md](../security/SECURITY-COMPLIANCE.md) and [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md).

### Breach Classification

| Severity | Definition | Examples | Response SLA |
|----------|-----------|----------|-------------|
| **Critical (P1)** | Confirmed exfiltration of Restricted data; regulatory notification required | PII dataset exposed; PCI data leaked; credentials compromised | Contain: 1 hour; Notify: 72 hours (GDPR) |
| **High (P2)** | Confirmed unauthorized access to Confidential data; potential exfiltration | Insider accessed unauthorized domain; API key exposed | Contain: 4 hours; Investigate: 24 hours |
| **Medium (P3)** | Anomalous access pattern; no confirmed exfiltration | Unusual query volume; failed auth spike; classification bypass | Investigate: 24 hours; Report: 72 hours |
| **Low (P4)** | Policy violation with no data exposure | Access without valid justification; expired access used | Review: 5 business days |

### Breach Response Flowchart

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   DETECT     │    │   CONTAIN    │    │ INVESTIGATE  │    │   NOTIFY     │
│              │    │              │    │              │    │              │
│ Anomaly      │───▶│ Isolate      │───▶│ Root cause   │───▶│ DPA within   │
│ detection    │    │ affected     │    │ analysis     │    │ 72 hours     │
│ alert fires  │    │ resources    │    │              │    │ (GDPR)       │
│              │    │              │    │ Forensic     │    │              │
│ Security Ops │    │ Revoke       │    │ evidence     │    │ Affected     │
│ triages      │    │ compromised  │    │ preservation │    │ individuals  │
│              │    │ credentials  │    │              │    │ without      │
│              │    │              │    │ Impact       │    │ undue delay  │
│              │    │ Block        │    │ assessment   │    │              │
│              │    │ exfiltration │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                                                           │
       └───────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────┐
                         │    REMEDIATE     │
                         │                  │
                         │ Patch root cause │
                         │ Strengthen       │
                         │ controls         │
                         │ Update policies  │
                         │ Post-mortem      │
                         │ report           │
                         └──────────────────┘
```

### Breach Response Checklist

| Step | Action | Owner | Deadline |
|------|--------|-------|----------|
| 1 | Activate incident response team | CISO | Immediate |
| 2 | Isolate affected systems / revoke access | Security Ops | Within 1 hour (P1) |
| 3 | Preserve forensic evidence (snapshots, logs) | Security Ops | Within 2 hours |
| 4 | Assess scope: data types, volume, subjects affected | Privacy + Security | Within 24 hours |
| 5 | Notify Data Protection Authority (GDPR Art. 33) | DPO | Within 72 hours |
| 6 | Notify affected data subjects (GDPR Art. 34) | Privacy Team | Without undue delay |
| 7 | Remediate root cause | Platform Team | Per RCA timeline |
| 8 | Post-mortem; update controls and policies | All stakeholders | Within 2 weeks |
| 9 | Verify remediation effectiveness | Internal Audit | Within 60 days |

---

## 15. Cross-References

### Related Documents

| Document | Location | Relevance |
|----------|----------|-----------|
| **Data Privacy & Compliance** | [DATA-PRIVACY-COMPLIANCE.md](../security/DATA-PRIVACY-COMPLIANCE.md) | GDPR/PCI-DSS/SOX compliance details; PII handling; consent management; deletion workflows |
| **Responsible AI Framework** | [RESPONSIBLE-AI.md](../governance/RESPONSIBLE-AI.md) | Explainability; model cards; bias testing; ethical AI principles |
| **AI Governance Guide** | [AI-GOVERNANCE.md](../governance/AI-GOVERNANCE.md) | Governance board structure; AI use case lifecycle; risk management |
| **Security Compliance** | [SECURITY-COMPLIANCE.md](../security/SECURITY-COMPLIANCE.md) | Security controls; incident response; encryption; network security |
| **Security Layers** | [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) | Defense-in-depth architecture; identity; network; data layer controls |
| **Operations Guide** | [OPERATIONS-GUIDE.md](../operations/OPERATIONS-GUIDE.md) | Monitoring; alerting; runbooks; SRE practices |
| **Architecture Guide** | [ARCHITECTURE-GUIDE.md](../architecture/ARCHITECTURE-GUIDE.md) | System architecture; service topology; data flow design |
| **Edge Cases & Data Types** | [EDGE-CASES-DATA-TYPES.md](../reference/EDGE-CASES-DATA-TYPES.md) | Document type handling; special format processing |
| **FinOps & Cost Management** | [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) | Storage cost optimization aligned with retention policies |

### Framework Alignment Summary

| Framework | Relevant Controls | Coverage in This Document |
|-----------|------------------|--------------------------|
| **ISO/IEC 42001** | A.7 (Data for AI), A.8 (AI System Lifecycle) | Sections 1-6, 9-10 |
| **NIST AI RMF** | Map 3.4 (Data), Measure 2.6 (Data Quality) | Sections 4, 11-12 |
| **CMMI Level 3** | Data Management (DM), Configuration Management (CM) | Sections 8-9 |
| **GDPR** | Art. 5, 6, 15-22, 25, 30, 33-34 | Sections 5-7, 13-14 |
| **CCPA** | 1798.100, 1798.105, 1798.110, 1798.120 | Section 13 |
| **SOX** | Section 302, 404 (data integrity controls) | Sections 1, 4, 6 |
| **PCI-DSS** | Req. 3 (stored data), Req. 7 (access control) | Sections 5-7 |

---

## Document Control

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Approved By** | Data Governance Council |
| **Next Review** | 2024-04 |

---

*This document is part of the Azure OpenAI Enterprise RAG Platform documentation suite. For the complete documentation index, see [INDEX.md](../INDEX.md).*
