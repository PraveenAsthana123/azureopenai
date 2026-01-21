# Low-Level Design (LLD) - Enterprise GenAI Knowledge Copilot

## 1. Component-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Channels                                   │
│                    (Teams / Web App / Copilot Studio)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API Management (APIM)                               │
│  • JWT Validation (Entra ID)                                                │
│  • Rate Limiting (100 calls/min per user)                                   │
│  • Routing to backend services                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  Pre-Retrieval    │    │   RAG Processor   │    │   Ingestion       │
│  (Azure Function) │    │ (Azure Function)  │    │ (Durable Func)    │
│                   │    │                   │    │                   │
│ • Intent detect   │    │ • Hybrid search   │    │ • OCR/Parse       │
│ • Query rewrite   │    │ • Reranking       │    │ • Chunking        │
│ • Metadata extract│    │ • Post-process    │    │ • Embedding       │
│ • ACL filtering   │    │ • LLM generation  │    │ • Indexing        │
└───────────────────┘    └───────────────────┘    └───────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   Azure OpenAI    │    │  Azure AI Search  │    │   Azure Cache     │
│                   │    │                   │    │    (Redis)        │
│ • GPT-4o          │    │ • Vector Index    │    │                   │
│ • GPT-4o-mini     │    │ • BM25 Keyword    │    │ • Query cache     │
│ • Embeddings      │    │ • Semantic Config │    │ • Retrieval cache │
└───────────────────┘    └───────────────────┘    └───────────────────┘
```

## 2. Data Flow - Runtime Query Processing

```
Step 1: User → Copilot Studio
        └── Query + Entra JWT token

Step 2: Copilot → APIM
        └── JWT validation, rate limiting

Step 3: APIM → Pre-Retrieval Function
        ├── Intent detection
        ├── Query rewrite (GPT-4o-mini)
        ├── Metadata extraction (region, dept, date)
        └── ACL filter building (user groups)

Step 4: Pre-Retrieval → Cache (Redis)
        └── Lookup cached results

Step 5: Pre-Retrieval → AI Search (if cache miss)
        └── Hybrid query (vector + BM25 + filters)

Step 6: AI Search → Reranker
        └── Cross-encoder reranking

Step 7: Reranker → Post-Retrieval
        ├── Deduplication
        ├── Temporal filtering
        ├── Conflict resolution
        └── Context compression

Step 8: Post-Retrieval → Azure OpenAI
        └── GPT-4o with context + system prompt

Step 9: OpenAI → Post-Retrieval
        └── Structured JSON response

Step 10: Post-Retrieval → Cache
         └── Store answer (15-30 min TTL)

Step 11: Post-Retrieval → Copilot → User
         └── Answer + citations
```

## 3. Chunking Strategy by Document Type

| Doc Type | Method | Target Size | Overlap | Boundaries |
|----------|--------|-------------|---------|------------|
| Policies/SOPs | Semantic sections | 700-1200 tokens | 10-15% | Headings, bullets |
| Contracts/Legal | Clause-based | 400-800 tokens | 15-20% | Article, Section, Clause |
| Manuals/Tech Docs | Hybrid | 800-1500 tokens | 10% | Code blocks preserved |
| Scanned PDFs | Layout-aware | 500-900 tokens | 15% | Page boundaries |
| Tables | Table-to-text | Per table | 0% | Full table |

### Chunk Record Schema (Azure AI Search)

```json
{
  "id": "doc123_chunk_045",
  "docId": "doc123",
  "chunkText": "...",
  "chunkVector": [0.012, 0.98, ...],
  "titleVector": [...],
  "source": "sharepoint",
  "path": "/Compliance/AML/policy_v4.pdf",
  "department": "Compliance",
  "region": "CA",
  "version": "v4",
  "effectiveDate": "2025-02-01T00:00:00Z",
  "piiClass": "none",
  "aclGroups": ["Compliance_Readers"],
  "page": 12,
  "lastUpdated": "2025-11-20T10:12:00Z"
}
```

## 4. Retrieval Pipeline

### Pre-Retrieval Processing

```python
# Input
raw_query = "latest AML onboarding policy for Canada"

# Output
{
  "normalizedQuery": "latest anti-money laundering (AML) onboarding policy for Canada",
  "filters": {
    "department": "Compliance",
    "region": "CA",
    "effectiveDate": {"gte": "2025-01-01"}
  },
  "topK": 8,
  "intent": "procedural",
  "securityGroups": ["Compliance_Readers", "CA_Employees"]
}
```

### Hybrid Search Query

```json
{
  "search": "latest AML onboarding policy",
  "searchMode": "any",
  "queryType": "semantic",
  "semanticConfiguration": "enterprise-semantic",
  "top": 8,
  "filter": "department eq 'Compliance' and region eq 'CA' and effectiveDate ge 2025-01-01",
  "vectors": [{
    "value": [0.1, 0.2, ...],
    "fields": "chunkVector",
    "k": 8
  }]
}
```

### Post-Retrieval Processing

| Step | Purpose | Implementation |
|------|---------|----------------|
| Dedup | Remove near-duplicates | Cosine similarity > 0.85 |
| Temporal | Prioritize latest | Sort by effectiveDate DESC |
| Conflict | Handle contradictions | Keep highest version |
| Compress | Reduce tokens | Summarize if > 4000 tokens |
| Score | Confidence measure | Grounding score calculation |

## 5. LLM Configuration

### Model Routing

| Task | Model | Temperature | Top-p | Max Tokens |
|------|-------|-------------|-------|------------|
| RAG Answer | GPT-4o | 0.1 | 0.5 | 2000 |
| Query Rewrite | GPT-4o-mini | 0.3 | 0.6 | 500 |
| Summarization | GPT-4o-mini | 0.2 | 0.5 | 1000 |
| Complex Reasoning | GPT-4o | 0.1 | 0.4 | 4000 |

### System Prompt Template

```
You are an enterprise AI assistant for {company_name}.

## Rules
1. Answer ONLY from provided context
2. Cite sources: [Source: docId, page X]
3. If info not in context: "I don't have information about this"
4. Be concise but complete

## Output Format (JSON)
{
  "answer": "...",
  "citations": [{"docId": "...", "page": 12}],
  "confidence": 0.92,
  "followups": ["..."]
}
```

## 6. Cache Strategy

| Cache Type | Key Pattern | TTL | Stored Value | Invalidation |
|------------|-------------|-----|--------------|--------------|
| Query | `q:{hash(query+filters)}` | 15-30 min | Final answer JSON | On doc update |
| Retrieval | `r:{hash(query+filters)}` | 30-60 min | Top-K chunk IDs | On index upsert |
| Embedding | `emb:{docId}:{chunkHash}:{model}` | 30 days | Embedding vector | On chunk change |

## 7. Security Implementation

### ACL Filtering

```python
# User context from JWT
user_groups = ["Compliance_Readers", "CA_Employees"]

# Search filter
filter = "aclGroups/any(g: g eq 'Compliance_Readers' or g eq 'CA_Employees')"
```

### PII Detection

| Category | Pattern | Action |
|----------|---------|--------|
| SSN | `\d{3}-\d{2}-\d{4}` | Mask: `***-**-****` |
| Credit Card | `\d{4}-\d{4}-\d{4}-\d{4}` | Mask: `****-****-****-1234` |
| Email | `*@*.*` | Partial mask: `j***@company.com` |

### Audit Logging

```json
{
  "timestamp": "2025-11-22T10:30:00Z",
  "userId": "user123",
  "queryHash": "sha256:abc...",
  "documentsAccessed": ["doc123", "doc456"],
  "responseGenerated": true,
  "piiDetected": false
}
```

## 8. Evaluation Metrics

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Groundedness | ≥ 0.80 | Answer supported by context |
| Relevance | ≥ 0.70 | Answer addresses query |
| Citation Accuracy | ≥ 0.90 | Citations match sources |
| Hallucination Rate | ≤ 0.10 | Unsupported claims |
| Retrieval Precision | ≥ 0.70 | Retrieved docs are relevant |
| Retrieval Recall | ≥ 0.60 | Relevant docs retrieved |

### Release Gate

```python
# Block deployment if:
if groundedness < 0.80 or hallucination_rate > 0.10:
    raise DeploymentBlocked("Evaluation metrics below threshold")
```

## 9. Monitoring & Observability

### Application Insights Metrics

- **LLM Metrics**: Latency, token usage, prompt failures
- **RAG Metrics**: Relevance scores, hit-rate, grounding scores
- **System Metrics**: API errors, retries, failures
- **Security Metrics**: Unauthorized access attempts, anomalies

### Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| High Latency | P95 > 5s | Notify on-call |
| Error Rate | > 5% | Auto-scale + notify |
| Groundedness Drop | < 0.7 | Block deployments |
| Token Spike | > 2x baseline | Cost review |

## 10. File Structure

```
backend/shared/
├── config.py          # Configuration management
├── chunking.py        # Document chunking service
├── retrieval.py       # Pre/Post retrieval processing
├── llm_service.py     # Azure OpenAI integration
├── reranker.py        # Cross-encoder reranking
├── security.py        # ACL, PII detection, audit
└── evaluation.py      # RAG evaluation framework

backend/azure-functions/
├── api-gateway/       # Public API endpoints
├── orchestrator/      # Workflow orchestration
├── ingestion/         # Document processing
└── rag-processor/     # RAG pipeline

infrastructure/terraform/
├── modules/
│   ├── networking/    # VNet, subnets, NSGs
│   ├── compute/       # VMs, Functions
│   ├── ai-services/   # OpenAI, Search, Doc Intel
│   ├── database/      # Cosmos DB
│   ├── storage/       # Blob storage
│   ├── cache/         # Redis cache
│   ├── api-management/# APIM
│   └── monitoring/    # App Insights, Key Vault
└── environments/
    ├── dev/
    └── prod/
```
