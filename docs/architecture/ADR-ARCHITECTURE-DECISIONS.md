# Architecture Decision Records (ADR)

> **Key Architecture Decisions for Azure OpenAI Enterprise Platform**
>
> Format: MADR (Markdown Any Decision Records)

---

## Table of Contents

1. [ADR-001: Model Selection](#adr-001-model-selection)
2. [ADR-002: Search Strategy](#adr-002-search-strategy)
3. [ADR-003: Chunking Strategy](#adr-003-chunking-strategy)
4. [ADR-004: Caching Layer](#adr-004-caching-layer)
5. [ADR-005: Compute Platform](#adr-005-compute-platform)
6. [ADR-006: Data Store](#adr-006-data-store)
7. [ADR-007: Authentication](#adr-007-authentication)
8. [ADR-008: Multi-Tenant Architecture](#adr-008-multi-tenant-architecture)

---

## ADR-001: Model Selection

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-15 |
| **Deciders** | Architecture Team, AI Ethics Committee |
| **Category** | AI Services |

### Context

The platform requires LLM capabilities for RAG answer generation, query rewriting, summarization, and complex reasoning. Multiple Azure OpenAI models are available with varying cost, latency, and quality trade-offs.

### Decision

Deploy a **multi-model routing strategy** using GPT-4o as the primary model and GPT-4o-mini as the cost-optimized secondary model.

| Model | Use Case | Temperature | Max Tokens | Cost (per 1K tokens) |
|-------|----------|-------------|------------|----------------------|
| **GPT-4o** | RAG answers, complex reasoning | 0.1 | 2000–4000 | $0.005 input / $0.015 output |
| **GPT-4o-mini** | Query rewriting, summarization | 0.2–0.3 | 500–1000 | $0.00015 input / $0.0006 output |
| **text-embedding-3-large** | Vector embeddings (3072 dims) | N/A | N/A | $0.00013 per 1K tokens |

### Model Routing Logic

```
User Query
    │
    ▼
┌─────────────────────┐
│  Intent Classifier   │
│  (GPT-4o-mini)      │
└──────────┬──────────┘
           │
     ┌─────┼─────┐
     ▼     ▼     ▼
  Simple  Standard  Complex
     │     │        │
     ▼     ▼        ▼
  4o-mini  4o      4o (high tokens)
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| GPT-4o only | Simplest routing | 10x higher cost for simple queries | Cost prohibitive at scale |
| GPT-4o-mini only | Lowest cost | Lower quality for complex reasoning | Quality trade-off unacceptable |
| GPT-4 Turbo | Strong reasoning | Higher latency than GPT-4o | Latency budget exceeded |
| Open-source (Llama) | No per-token cost | Self-hosting complexity, no SLA | Operational overhead, compliance risk |

### Consequences

- **Positive**: 60–70% cost reduction by routing simple queries to GPT-4o-mini
- **Positive**: Best quality for complex reasoning via GPT-4o
- **Negative**: Routing logic adds ~50ms latency
- **Negative**: Two models to monitor and manage
- **Risk**: Model deprecation requires migration planning

---

## ADR-002: Search Strategy

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-15 |
| **Deciders** | Architecture Team |
| **Category** | Retrieval Pipeline |

### Context

RAG retrieval quality directly impacts answer accuracy. Options include pure vector search, keyword search (BM25), or hybrid combining both. Azure AI Search supports all three approaches natively.

### Decision

Use **hybrid search (vector + BM25) with semantic reranking** as the default retrieval strategy.

```
Query
  │
  ├──► Vector Search (cosine similarity, HNSW index)
  │         Weight: 0.6
  │
  ├──► BM25 Keyword Search (full-text index)
  │         Weight: 0.4
  │
  └──► Reciprocal Rank Fusion (RRF)
           │
           ▼
       Semantic Reranker (cross-encoder)
           │
           ▼
       Top-K Results (k=8)
```

### Search Configuration

```json
{
  "queryType": "semantic",
  "semanticConfiguration": "enterprise-semantic",
  "search": "<keyword query>",
  "vectors": [{
    "value": "<embedding vector>",
    "fields": "chunkVector",
    "k": 50
  }],
  "top": 8,
  "select": "id,chunkText,source,department,effectiveDate,page"
}
```

### Alternatives Considered

| Alternative | Retrieval Precision | Recall | Latency | Reason Rejected |
|-------------|-------------------|--------|---------|-----------------|
| Vector-only | 72% | 68% | ~150ms | Misses exact keyword matches (acronyms, IDs) |
| BM25-only | 65% | 60% | ~50ms | No semantic understanding |
| **Hybrid + Rerank** | **85%** | **80%** | **~350ms** | **Selected** |
| Multi-index fusion | 82% | 78% | ~500ms | Complexity not justified |

### Consequences

- **Positive**: Best retrieval quality across query types
- **Positive**: Handles both semantic and keyword-exact queries
- **Negative**: Higher latency (~350ms vs ~150ms for vector-only)
- **Negative**: Semantic reranker adds cost ($0.003 per query)
- **Mitigation**: Cache frequent queries to offset latency and cost

---

## ADR-003: Chunking Strategy

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-20 |
| **Deciders** | Architecture Team, Data Engineering |
| **Category** | Data Processing |

### Context

Document chunking strategy directly affects retrieval quality. Chunks must be small enough for embedding precision but large enough to preserve context. Different document types have different optimal strategies.

### Decision

Use **heading-aware semantic chunking** with a default target of 512 tokens (range 400–1500 depending on document type) and 10–15% overlap.

### Chunking Strategy by Document Type

| Document Type | Method | Target Size | Overlap | Boundary Markers |
|---------------|--------|-------------|---------|------------------|
| Policies / SOPs | Semantic sections | 700–1200 tokens | 10–15% | Headings, numbered sections |
| Contracts / Legal | Clause-based | 400–800 tokens | 15–20% | Article, Section, Clause |
| Technical Manuals | Hybrid | 800–1500 tokens | 10% | Code blocks preserved whole |
| Scanned PDFs | Layout-aware | 500–900 tokens | 15% | Page boundaries |
| Tables | Table-to-text | Per table | 0% | Full table as single chunk |
| FAQs | Q&A pairs | Per pair | 0% | Question + answer together |

### Chunking Pipeline

```
Document
    │
    ▼
┌──────────────┐
│ Format Detection │  (PDF, DOCX, XLSX, image)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Document Intel │  (OCR, layout, structure extraction)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Heading/Section │  (Detect logical boundaries)
│  Detection      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Semantic Split │  (Split at boundaries, respect size)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Overlap Inject │  (Add context overlap between chunks)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Metadata Enrich│  (Source, page, section, department)
└──────────────┘
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| Fixed 512 tokens | Simple, predictable | Breaks mid-sentence, no semantic awareness | Quality loss |
| Sentence-level | Preserves sentences | Too granular, high index size | Storage and cost |
| Full-page | Simple | Too large for precise retrieval | Low precision |
| **Heading-aware 512** | **Semantic boundaries** | **Complexity in implementation** | **Selected** |

### Consequences

- **Positive**: Higher retrieval precision due to semantically coherent chunks
- **Positive**: Configurable per document type
- **Negative**: More complex chunking pipeline
- **Negative**: Requires Document Intelligence for structure extraction
- **Risk**: Poorly structured documents degrade to fixed-size fallback

---

## ADR-004: Caching Layer

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-22 |
| **Deciders** | Architecture Team |
| **Category** | Performance |

### Context

LLM inference and search queries are the most expensive operations. Caching identical or similar queries can reduce cost by 30–50% and improve latency for repeat queries.

### Decision

Use **Azure Cache for Redis** (Premium tier in prod) with tiered TTLs for different cache levels.

### Cache Architecture

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  L1: Query Cache             │  Key: hash(query + filters + user_groups)
│  TTL: 15–30 min             │  Value: Final answer JSON
│  Hit Rate Target: 20–30%    │
└──────────┬──────────────────┘
           │ Miss
           ▼
┌─────────────────────────────┐
│  L2: Retrieval Cache         │  Key: hash(query + filters)
│  TTL: 30–60 min             │  Value: Top-K chunk IDs + scores
│  Hit Rate Target: 40–50%    │
└──────────┬──────────────────┘
           │ Miss
           ▼
┌─────────────────────────────┐
│  L3: Embedding Cache         │  Key: hash(docId + chunkHash + model)
│  TTL: 30 days               │  Value: Embedding vector (3072 dims)
│  Hit Rate Target: 90%+      │
└─────────────────────────────┘
```

### Cache Invalidation

| Trigger | Invalidated Cache | Method |
|---------|-------------------|--------|
| Document updated | L1, L2 for affected doc | Event-driven (Blob trigger) |
| Index rebuild | All L2 | Scheduled flush |
| Model change | All L1, L2, L3 | Manual flush |
| TTL expiry | Individual entry | Automatic |
| User reports bad answer | Specific L1 entry | Manual delete |

### Redis Configuration

```yaml
Azure Cache for Redis:
  SKU: Premium P1 (prod) / Basic C1 (dev)
  Memory: 6 GB (prod) / 250 MB (dev)
  Network: Private Endpoint
  Persistence: RDB (every 60 min)
  Eviction: allkeys-lru
  TLS: Required
  Clustering: Disabled (single shard sufficient)
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| In-memory (app-level) | Zero latency | Lost on restart, no sharing | Not durable |
| Cosmos DB cache | Infinite TTL | Higher latency (~10ms vs ~1ms) | Latency |
| Azure Front Door cache | CDN-level | Only for static responses | Not applicable to dynamic AI |
| **Redis** | **Sub-ms latency, TTL, eviction** | **Additional service** | **Selected** |

### Consequences

- **Positive**: 30–50% reduction in OpenAI API costs
- **Positive**: Sub-5ms cache hit latency vs 2–3s for full pipeline
- **Negative**: Cache staleness risk (mitigated by short TTLs)
- **Negative**: Additional infrastructure to manage
- **Risk**: Cache poisoning if invalidation fails

---

## ADR-005: Compute Platform

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-10 |
| **Deciders** | Architecture Team, Platform Team |
| **Category** | Infrastructure |

### Context

The platform needs compute for: (1) long-running AI workloads and APIs, (2) event-driven document processing, (3) scheduled jobs. Options include AKS, Azure Functions, App Service, or Container Apps.

### Decision

Use **AKS (Private Cluster) + Azure Functions (Elastic Premium)** as a dual compute platform.

| Workload Type | Compute | Rationale |
|---------------|---------|-----------|
| API Gateway / Chat Backend | AKS | Long-running, stateful, WebSocket support |
| RAG Pipeline Orchestration | AKS | Complex workflows, sidecar patterns |
| Document Ingestion | Azure Functions (Durable) | Event-driven, auto-scale to zero |
| Scheduled Jobs (indexer, cleanup) | Azure Functions (Timer) | Cron-based, serverless |
| Evaluation Pipeline | AKS (batch job) | GPU-optional, long-running |

### AKS Configuration

```yaml
Cluster:
  Type: Private Cluster
  Network Plugin: Azure CNI
  Network Policy: Calico
  Identity: System Managed Identity
  RBAC: Azure AD integrated

Node Pools:
  system:
    VM: Standard_D2s_v3 (dev) / D4s_v3 (prod)
    Scale: 2–4 (dev) / 3–6 (prod)
  workload:
    VM: Standard_D4s_v3
    Scale: 1–10
    Labels: workload=ai-services
    Taints: ai-only=true:NoSchedule

Add-ons:
  - Azure Policy
  - Key Vault Secrets Provider (CSI)
  - Container Insights
  - Workload Identity
  - KEDA (event-driven autoscaler)
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| AKS only | Single platform | Overhead for event-driven tasks | Over-provisioning |
| Functions only | Fully serverless | 10-min execution limit, cold starts | Not suitable for APIs |
| Container Apps | Simpler than AKS | Less control, fewer networking options | Enterprise features lacking |
| App Service | Simple PaaS | No container orchestration | Scalability limits |

### Consequences

- **Positive**: Best-fit compute for each workload type
- **Positive**: AKS provides full Kubernetes ecosystem
- **Positive**: Functions scales to zero for infrequent workloads
- **Negative**: Two compute platforms to operate
- **Risk**: Skill gap for Kubernetes operations

---

## ADR-006: Data Store

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-12 |
| **Deciders** | Architecture Team, Data Engineering |
| **Category** | Data |

### Context

The platform requires storage for: (1) source documents, (2) processed chunks and embeddings, (3) conversation history, (4) user sessions, (5) audit logs, (6) evaluation results.

### Decision

Use **Cosmos DB (NoSQL API)** for transactional data and **Azure Data Lake Gen2** for document and analytics storage.

### Data Store Mapping

| Data Type | Store | Partition Key | TTL | Rationale |
|-----------|-------|---------------|-----|-----------|
| Conversations | Cosmos DB | `/userId` | 90 days | Low-latency read/write |
| User Sessions | Cosmos DB | `/sessionId` | 24 hours | Transient, fast lookup |
| Evaluation Results | Cosmos DB | `/evaluationId` | None | Query by model, date |
| Feedback | Cosmos DB | `/queryId` | None | Analytics |
| Audit Logs | Cosmos DB + Data Lake | `/tenantId` | 7 years (archive) | Compliance |
| Source Documents | Data Lake Gen2 | N/A | Lifecycle policy | Large binary files |
| Processed Chunks | Data Lake Gen2 | N/A | 30 days | Intermediate artifacts |
| Embeddings | AI Search Index | N/A | N/A | Vector search |

### Cosmos DB Schema — Conversations

```json
{
  "id": "conv-uuid",
  "userId": "user@company.com",
  "tenantId": "tenant-001",
  "sessionId": "session-uuid",
  "messages": [
    {
      "role": "user",
      "content": "What is the AML policy?",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Based on the AML policy document...",
      "citations": [{"docId": "doc123", "page": 5}],
      "confidence": 0.92,
      "tokensUsed": {"input": 1200, "output": 450},
      "timestamp": "2025-01-15T10:30:03Z"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "department": "Compliance",
    "queryCount": 1
  },
  "_ts": 1705312200,
  "ttl": 7776000
}
```

### Data Lake Structure

```
Storage Account (Data Lake Gen2)
├── raw/                    # Original uploads
│   ├── pdf/
│   ├── docx/
│   ├── xlsx/
│   └── images/
├── processed/              # Chunked + enriched
│   ├── chunks/
│   ├── metadata/
│   └── failed/
├── embeddings/             # Vector embeddings (backup)
│   ├── full/
│   └── chunks/
├── audit-logs/             # Immutable audit trail
│   ├── access/
│   ├── changes/
│   └── ai-usage/
└── evaluations/            # Eval datasets + results
    ├── golden-sets/
    └── results/
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| SQL Database | Strong schema | Rigid for AI workloads | Schema evolution friction |
| Cosmos DB only | Single store | Expensive for large blobs | Cost at scale |
| Data Lake only | Cheapest | No transactional guarantees | Session/conversation needs |
| **Cosmos DB + Data Lake** | **Best fit per workload** | **Two stores to manage** | **Selected** |

### Consequences

- **Positive**: Cosmos DB provides <10ms reads for conversations
- **Positive**: Data Lake provides cost-effective storage for large documents
- **Positive**: Lifecycle policies automate data management
- **Negative**: Two data platforms to manage
- **Risk**: Data consistency between stores (mitigated by event-driven sync)

---

## ADR-007: Authentication

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-08 |
| **Deciders** | Architecture Team, Security Team |
| **Category** | Security |

### Context

The platform accesses 15+ Azure services. Traditional API key management is error-prone and creates security risks. Azure provides Managed Identity as a keyless alternative.

### Decision

Use **Managed Identity exclusively** with zero API keys stored anywhere in the platform.

### Authentication Matrix

| Source | Target | Auth Method | Identity Type |
|--------|--------|-------------|---------------|
| AKS Pod | Azure OpenAI | Workload Identity | User-assigned MI |
| AKS Pod | Key Vault | Workload Identity | User-assigned MI |
| AKS Pod | Storage | Workload Identity | User-assigned MI |
| Azure Function | Azure OpenAI | System MI | System-assigned MI |
| Azure Function | AI Search | System MI | System-assigned MI |
| Azure Function | Cosmos DB | System MI | System-assigned MI |
| CI/CD Pipeline | Azure Resources | Service Principal | Federated (OIDC) |
| Users | Application | Entra ID | SSO + MFA |
| Partner APIs | APIM | OAuth 2.0 | Client credentials |

### Zero API Key Enforcement

```yaml
Policy Enforcement:
  Azure Policy:
    - "Deny API key access to Cognitive Services"
    - "Deny storage account key access"
    - "Require managed identity on AKS"

  CI/CD Checks:
    - Scan for hardcoded keys (gitleaks)
    - Validate no Key Vault secrets contain API keys
    - Audit RBAC assignments quarterly

  Runtime:
    - All SDK calls use DefaultAzureCredential
    - No connection strings with keys
    - Token-based auth for all service-to-service
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| API keys in Key Vault | Simple | Rotation burden, leak risk | Security risk |
| Service principals | Flexible | Secret management | Operational overhead |
| **Managed Identity** | **Zero secrets, auto-rotation** | **Azure-only** | **Selected** |
| Certificate auth | Strong | Certificate lifecycle | Complexity |

### Consequences

- **Positive**: Zero secrets to rotate or leak
- **Positive**: Automatic token lifecycle management
- **Positive**: Compliant with zero-trust principles
- **Negative**: Azure-only (no multi-cloud portability)
- **Negative**: Slightly more complex initial setup
- **Risk**: MI token caching issues require proper SDK usage

---

## ADR-008: Multi-Tenant Architecture

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-01-25 |
| **Deciders** | Architecture Team, Product Team |
| **Category** | Platform Architecture |

### Context

The platform must support multiple business units (B2E), external partners (B2B), and customer-facing applications (B2C) with data isolation, independent scaling, and per-tenant configuration.

### Decision

Use a **shared infrastructure, isolated data** multi-tenant model with tenant-scoped access controls at the data layer.

### Tenant Isolation Model

```
┌─────────────────────────────────────────────────────────┐
│                  Shared Compute Layer                      │
│              (AKS, Functions, APIM)                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Tenant A │  │ Tenant B │  │ Tenant C │              │
│  │ (B2E)    │  │ (B2B)    │  │ (B2C)    │              │
│  ├──────────┤  ├──────────┤  ├──────────┤              │
│  │ Data     │  │ Data     │  │ Data     │              │
│  │ Partition│  │ Partition│  │ Partition│              │
│  │          │  │          │  │          │              │
│  │ AI Search│  │ AI Search│  │ AI Search│              │
│  │ Filter:  │  │ Filter:  │  │ Filter:  │              │
│  │ tenantA  │  │ tenantB  │  │ tenantC  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │              Cosmos DB                            │     │
│  │  Partition Key: /tenantId                        │     │
│  │  Cross-partition queries: Disabled by default    │     │
│  └─────────────────────────────────────────────────┘     │
│                                                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │          Storage (Data Lake Gen2)                 │     │
│  │  Container per tenant: tenant-a/, tenant-b/      │     │
│  │  RBAC: Scoped to container                       │     │
│  └─────────────────────────────────────────────────┘     │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Tenant Configuration

```json
{
  "tenantId": "tenant-001",
  "name": "Internal HR",
  "type": "B2E",
  "config": {
    "model": "gpt-4o",
    "maxTokensPerQuery": 4000,
    "rateLimitPerMinute": 100,
    "allowedDepartments": ["HR", "Legal"],
    "contentFilters": "standard",
    "dataRetentionDays": 90,
    "piiHandling": "mask",
    "slaTarget": "99.9%"
  }
}
```

### Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|-------------|------|------|-----------------|
| Separate infra per tenant | Strongest isolation | 3x cost, operational burden | Cost prohibitive |
| Shared everything | Lowest cost | Data leakage risk, noisy neighbor | Security risk |
| **Shared compute, isolated data** | **Balance of cost and security** | **Middleware complexity** | **Selected** |

### Consequences

- **Positive**: Cost-efficient shared compute
- **Positive**: Strong data isolation via partition keys and filters
- **Positive**: Per-tenant configuration and rate limiting
- **Negative**: Risk of noisy neighbor on shared compute (mitigated by rate limits)
- **Negative**: More complex middleware for tenant context propagation
- **Risk**: Tenant filter bypass could leak data (mitigated by defense-in-depth)

---

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| 001 | Model Selection | Accepted | 2025-01-15 |
| 002 | Search Strategy | Accepted | 2025-01-15 |
| 003 | Chunking Strategy | Accepted | 2025-01-20 |
| 004 | Caching Layer | Accepted | 2025-01-22 |
| 005 | Compute Platform | Accepted | 2025-01-10 |
| 006 | Data Store | Accepted | 2025-01-12 |
| 007 | Authentication | Accepted | 2025-01-08 |
| 008 | Multi-Tenant Architecture | Accepted | 2025-01-25 |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Architecture Team |
| Review | Quarterly |
