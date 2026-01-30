# Retrieval & Performance Architecture

> **Pre-Retrieval, Search, Post-Retrieval, Latency, and Performance Optimization**
>
> End-to-End RAG Pipeline Performance Guide

---

## Table of Contents

1. [Pre-Retrieval Processing](#pre-retrieval-processing)
2. [Search Strategies](#search-strategies)
3. [Post-Retrieval Processing](#post-retrieval-processing)
4. [Latency Budget Breakdown](#latency-budget-breakdown)
5. [Performance Optimization](#performance-optimization)
6. [Service-Level Latency Targets](#service-level-latency-targets)

---

## Pre-Retrieval Processing

### Pipeline Overview

```
User Query: "latest AML onboarding policy for Canada"
    │
    ├── 1. Spell Correction
    │   └── "latest AML onboarding policy for Canada" (no change)
    │
    ├── 2. Intent Classification
    │   └── Intent: "procedural" (confidence: 0.92)
    │
    ├── 3. Query Expansion
    │   └── "anti-money laundering (AML) onboarding policy Canada current version"
    │
    ├── 4. Query Rewriting
    │   └── LLM rewrites for search optimization
    │
    ├── 5. Metadata Extraction
    │   └── {department: "Compliance", region: "CA", recency: "latest"}
    │
    └── 6. ACL Filter Building
        └── {aclGroups: ["Compliance_Readers", "CA_Employees"]}
```

### Intent Classification

| Intent | Description | Model Routing | Top-K | Example |
|--------|-------------|---------------|-------|---------|
| **Factual** | Specific fact lookup | GPT-4o-mini | 5 | "What is the max transaction limit?" |
| **Procedural** | Step-by-step process | GPT-4o | 8 | "How do I onboard a new client?" |
| **Comparative** | Compare two things | GPT-4o | 10 | "Differences between AML and KYC?" |
| **Analytical** | Complex reasoning | GPT-4o (high tokens) | 12 | "Why did compliance reject case X?" |
| **Conversational** | Follow-up, clarification | GPT-4o-mini | 5 | "Can you explain that in simpler terms?" |
| **Off-topic** | Not related to domain | N/A (reject) | 0 | "What's the weather?" |

### Query Rewriting

```python
# Query rewriting using GPT-4o-mini
rewrite_prompt = """
Rewrite the user query for optimal search retrieval.
Rules:
1. Expand acronyms (AML → anti-money laundering)
2. Add synonyms where helpful
3. Remove filler words
4. Preserve intent and specificity
5. Keep under 100 words

User query: {raw_query}
Rewritten query:
"""
```

| Original Query | Rewritten Query | Improvement |
|---------------|-----------------|-------------|
| "AML policy" | "anti-money laundering (AML) policy document current version" | Acronym expansion, recency signal |
| "how 2 onboard customer" | "customer onboarding process steps procedure" | Typo correction, term expansion |
| "compare AML vs KYC" | "comparison anti-money laundering (AML) versus know your customer (KYC) differences" | Acronym expansion, structured comparison |

### Query Expansion

```yaml
Expansion Techniques:
  Acronym Expansion:
    - AML → Anti-Money Laundering
    - KYC → Know Your Customer
    - PII → Personally Identifiable Information
    - SLA → Service Level Agreement

  Synonym Injection:
    - policy → policy, guideline, standard, procedure
    - onboarding → onboarding, enrollment, registration
    - latest → latest, current, most recent, up-to-date

  Domain Term Mapping:
    - "compliance training" → compliance training, mandatory education, regulatory certification
    - "risk assessment" → risk assessment, risk evaluation, risk analysis

  Expansion Source: Custom domain dictionary + LLM-generated synonyms
```

### Spell Correction

| Method | Use Case | Latency | Accuracy |
|--------|----------|---------|----------|
| **Symspell** | Fast fuzzy matching | < 5ms | 90% for common typos |
| **Azure AI Search suggestions** | Index-aware correction | < 20ms | 85% for domain terms |
| **LLM-based correction** | Complex misspellings | ~100ms | 98% (part of rewrite step) |

---

## Search Strategies

### Hybrid Search Architecture

```
Rewritten Query
    │
    ├──────────────────────┐
    │                      │
    ▼                      ▼
┌──────────────┐    ┌──────────────┐
│ Vector Search│    │ BM25 Keyword │
│              │    │   Search     │
│ Cosine       │    │              │
│ Similarity   │    │ TF-IDF       │
│ HNSW Index   │    │ Full-text    │
│              │    │ Index        │
│ k=50         │    │ top=50       │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └───────┬───────────┘
               │
               ▼
       ┌───────────────┐
       │ Reciprocal    │
       │ Rank Fusion   │  RRF(d) = Σ 1/(k + rank_i(d))
       │ (RRF)         │  k = 60 (default)
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │ Semantic       │  Cross-encoder reranking
       │ Reranker       │  Re-scores top 50 → top 8
       └───────┬───────┘
               │
               ▼
       Top-K Results (k=8)
```

### Search Strategy Comparison

| Strategy | How It Works | Strengths | Weaknesses | When to Use |
|----------|-------------|-----------|------------|-------------|
| **Cosine Similarity** | Compare query embedding to document embeddings | Semantic understanding, handles paraphrasing | Misses exact keywords, acronyms | General semantic queries |
| **BM25 (Keyword)** | Term frequency / inverse document frequency | Exact term matching, fast | No semantic understanding | Exact term lookup, IDs, codes |
| **Hybrid (Vector + BM25)** | Combine both with RRF fusion | Best of both worlds | Higher latency | Default for all queries |
| **Semantic Reranking** | Cross-encoder rescores results | Highest quality ranking | Adds ~100ms latency | After hybrid search |

### Vector Search Configuration

```yaml
Vector Index:
  Algorithm: HNSW (Hierarchical Navigable Small World)
  Dimensions: 3072 (text-embedding-3-large)
  Metric: Cosine similarity
  Parameters:
    m: 4 (connections per node)
    efConstruction: 400 (build-time quality)
    efSearch: 500 (query-time quality)

  Performance:
    Index Build: ~2 hours for 100K documents
    Query Latency: 20-50ms for top-50
    Recall@50: 95%+ (with efSearch=500)
```

### BM25 Configuration

```yaml
Full-Text Index:
  Analyzer: Standard Lucene (English)
  Fields:
    - chunkText (searchable, weight: 5)
    - title (searchable, weight: 3)
    - department (filterable)
    - region (filterable)
    - effectiveDate (filterable, sortable)
    - tenantId (filterable)
    - aclGroups (filterable, collection)

  Scoring Profile:
    - Boost recent documents (effectiveDate proximity)
    - Boost title matches (weight: 3x)
```

### Semantic Reranker

```yaml
Semantic Configuration:
  Name: enterprise-semantic
  Fields:
    titleField: title
    contentFields: [chunkText]
    keywordFields: [department, region]

  Reranker:
    Type: Cross-encoder (Azure built-in)
    Input: Top 50 from RRF fusion
    Output: Top 8 rescored results
    Latency: 60-100ms
    Cost: $0.003 per query
```

### Filter Strategies

| Filter Type | Field | Example | Purpose |
|-------------|-------|---------|---------|
| **Tenant** | `tenantId` | `tenantId eq 'tenant-001'` | Data isolation (mandatory) |
| **ACL** | `aclGroups` | `aclGroups/any(g: g eq 'Compliance_Readers')` | Permission enforcement |
| **Department** | `department` | `department eq 'Compliance'` | Scope narrowing |
| **Region** | `region` | `region eq 'CA'` | Geographic filtering |
| **Date** | `effectiveDate` | `effectiveDate ge 2025-01-01` | Recency filtering |
| **Document type** | `docType` | `docType eq 'policy'` | Type-specific retrieval |
| **PII class** | `piiClass` | `piiClass eq 'none'` | Exclude PII documents (B2C) |

---

## Post-Retrieval Processing

### Post-Retrieval Pipeline

```
Search Results (top-K)
    │
    ├── 1. Deduplication (MMR)
    │   └── Remove near-duplicate chunks (cosine > 0.85)
    │
    ├── 2. Relevance Filtering
    │   └── Drop results below score threshold (< 0.50)
    │
    ├── 3. Temporal Filtering
    │   └── Prefer latest version when duplicates exist
    │
    ├── 4. Conflict Resolution
    │   └── Flag contradicting documents, keep latest
    │
    ├── 5. Context Compression
    │   └── If total tokens > 4000, summarize lower-ranked chunks
    │
    ├── 6. Citation Extraction
    │   └── Prepare source metadata for citations
    │
    └── 7. Prompt Assembly
        └── System prompt + context + query → LLM
```

### Maximal Marginal Relevance (MMR)

```python
# MMR for diversity in search results
# Balance: relevance vs diversity
lambda_param = 0.7  # Higher = more relevance, Lower = more diversity

def mmr_select(query_embedding, candidates, k=8, lambda_param=0.7):
    selected = []
    for _ in range(k):
        best_score = -inf
        best_candidate = None
        for candidate in candidates:
            relevance = cosine_sim(query_embedding, candidate.embedding)
            diversity = max(cosine_sim(candidate.embedding, s.embedding) for s in selected) if selected else 0
            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity
            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate = candidate
        selected.append(best_candidate)
        candidates.remove(best_candidate)
    return selected
```

### Relevance Filtering

| Score Range | Action | User Message |
|-------------|--------|-------------|
| ≥ 0.80 | Include in context | (High confidence) |
| 0.60–0.79 | Include with lower weight | (Moderate confidence) |
| 0.50–0.59 | Include only if < 3 results above | (Low confidence) |
| < 0.50 | Exclude | "Limited information found" |
| 0 results above 0.50 | No context provided | "I don't have information about this" |

### Context Compression

```yaml
Compression Strategy:
  Trigger: Total context tokens > 4000

  Methods:
    1. Extractive: Remove least relevant sentences from lower-ranked chunks
    2. Abstractive: LLM-summarize lower-ranked chunks (GPT-4o-mini)
    3. Truncation: Hard cut at token limit (last resort)

  Priority: Keep top-3 chunks intact, compress ranks 4-8
  Target: Reduce to 3500 tokens (leave room for query + system prompt)
```

### Citation Extraction

```json
{
  "citations": [
    {
      "index": 1,
      "docId": "doc-aml-policy-v4",
      "title": "AML Onboarding Policy v4",
      "page": 12,
      "section": "3.2 Customer Due Diligence",
      "relevanceScore": 0.94,
      "effectiveDate": "2025-02-01",
      "department": "Compliance"
    },
    {
      "index": 2,
      "docId": "doc-kyc-guidelines",
      "title": "KYC Guidelines 2025",
      "page": 5,
      "section": "2.1 Identity Verification",
      "relevanceScore": 0.87,
      "effectiveDate": "2025-01-15",
      "department": "Compliance"
    }
  ]
}
```

---

## Latency Budget Breakdown

### End-to-End Query Latency

```
Component                      Budget    P50     P95     P99
─────────────────────────────────────────────────────────────
API Gateway (APIM)             20ms      10ms    15ms    25ms
├── JWT validation             10ms       5ms     8ms    12ms
└── Rate limit check            5ms       3ms     5ms     8ms

Pre-Retrieval                 200ms     100ms   180ms   250ms
├── Intent classification      50ms      30ms    45ms    60ms
├── Query rewriting (LLM)     120ms      60ms   110ms   150ms
└── Metadata extraction        30ms      10ms    25ms    40ms

Embedding Generation           50ms      30ms    45ms    60ms
└── text-embedding-3-large     50ms      30ms    45ms    60ms

Search (Hybrid)               200ms     120ms   180ms   250ms
├── Vector search (HNSW)       80ms      50ms    70ms   100ms
├── BM25 keyword search        40ms      20ms    35ms    50ms
├── RRF fusion                 10ms       5ms     8ms    15ms
└── Filter application         20ms      10ms    18ms    25ms

Semantic Reranking            100ms      60ms    90ms   120ms
└── Cross-encoder rerank      100ms      60ms    90ms   120ms

Post-Retrieval                 50ms      30ms    45ms    60ms
├── MMR deduplication          15ms       8ms    12ms    18ms
├── Relevance filtering         5ms       3ms     5ms     8ms
├── Context compression        20ms      12ms    18ms    25ms
└── Prompt assembly            10ms       5ms     8ms    12ms

LLM Generation               2000ms    1200ms  1800ms  2500ms
├── Prompt build               10ms       5ms     8ms    12ms
├── API call (GPT-4o)        1900ms    1100ms  1700ms  2400ms
└── Response parse             30ms      15ms    25ms    40ms

Response Formatting            30ms      15ms    25ms    40ms
├── Citation formatting        10ms       5ms     8ms    12ms
├── PII scan (output)          15ms       8ms    12ms    20ms
└── Response serialization      5ms       3ms     5ms     8ms

─────────────────────────────────────────────────────────────
TOTAL                        2650ms    1565ms  2380ms  3305ms
─────────────────────────────────────────────────────────────
```

### Latency Distribution

```
|          Component           |  % of Total  |  Optimization Potential  |
|------------------------------|-------------|------------------------|
| LLM Generation               |    75%      | Model routing, streaming |
| Search + Rerank              |    11%      | Cache, index tuning     |
| Pre-Retrieval                |     8%      | Cache intents, batching |
| Post-Retrieval               |     2%      | Parallel processing     |
| Embedding                    |     2%      | Cache embeddings        |
| API Gateway + Response       |     2%      | Minimal                 |
```

### Cache Impact on Latency

| Cache Level | Hit Rate | Latency (Hit) | Latency (Miss) | Avg Latency |
|-------------|----------|---------------|----------------|-------------|
| L1: Query cache | 20–30% | 5ms | 2650ms | ~2120ms |
| L2: Retrieval cache | 40–50% | 2050ms (skip search) | 2650ms | ~2350ms |
| L3: Embedding cache | 90%+ | 2600ms (skip embed) | 2650ms | ~2605ms |

---

## Performance Optimization

### Caching Strategy

```
┌─────────────────────────────────────────────────────┐
│                 Cache Hierarchy                       │
├─────────────────────────────────────────────────────┤
│                                                       │
│  L1: Full Answer Cache                               │
│  ├── Key: hash(query + filters + user_groups)        │
│  ├── Value: Complete response JSON                   │
│  ├── TTL: 15-30 min                                 │
│  ├── Hit → Return immediately (5ms)                 │
│  └── Savings: Skip entire pipeline                  │
│                                                       │
│  L2: Retrieval Cache                                 │
│  ├── Key: hash(normalized_query + filters)           │
│  ├── Value: Top-K chunk IDs + scores                │
│  ├── TTL: 30-60 min                                 │
│  ├── Hit → Skip search, go to LLM (2050ms)         │
│  └── Savings: ~600ms search + rerank                │
│                                                       │
│  L3: Embedding Cache                                 │
│  ├── Key: hash(text + model_version)                 │
│  ├── Value: Embedding vector (3072 floats)          │
│  ├── TTL: 30 days                                   │
│  ├── Hit → Skip embedding API call                  │
│  └── Savings: ~50ms per query                       │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### Connection Pooling

| Service | Pool Size (Dev) | Pool Size (Prod) | Timeout | Keep-Alive |
|---------|----------------|-------------------|---------|-----------|
| Azure OpenAI | 5 | 20 | 30s | 60s |
| AI Search | 5 | 15 | 10s | 30s |
| Cosmos DB | 5 | 50 | 5s | 120s |
| Redis | 5 | 20 | 3s | 60s |
| Key Vault | 2 | 5 | 5s | 300s |

### Batch Processing

| Operation | Batch Size | Latency (Single) | Latency (Batch) | Savings |
|-----------|-----------|-------------------|------------------|---------|
| Embedding generation | 16 texts | 50ms × 16 = 800ms | 200ms | 75% |
| Document indexing | 100 docs | Varies | Parallel with 10 workers | 90% |
| PII scanning | 10 texts | 15ms × 10 = 150ms | 50ms | 67% |
| Evaluation | 50 queries | 3s × 50 = 150s | 30s (10 parallel) | 80% |

### Async Patterns

```python
# Parallel execution of independent operations
async def process_query(query: str, user_context: UserContext):
    # Step 1: Parallel pre-retrieval tasks
    intent_task = asyncio.create_task(classify_intent(query))
    rewrite_task = asyncio.create_task(rewrite_query(query))
    embed_task = asyncio.create_task(generate_embedding(query))

    intent, rewritten_query, query_embedding = await asyncio.gather(
        intent_task, rewrite_task, embed_task
    )

    # Step 2: Search (depends on embedding + rewritten query)
    results = await hybrid_search(query_embedding, rewritten_query, user_context.filters)

    # Step 3: Parallel post-retrieval
    reranked = await rerank(query_embedding, results)
    deduplicated = mmr_select(query_embedding, reranked)

    # Step 4: Generate answer
    answer = await generate_answer(query, deduplicated, intent)

    # Step 5: Parallel final processing
    pii_task = asyncio.create_task(scan_pii(answer.text))
    cache_task = asyncio.create_task(cache_answer(query, answer))
    audit_task = asyncio.create_task(log_audit(query, answer))

    await asyncio.gather(pii_task, cache_task, audit_task)
    return answer
```

### Streaming Response

```yaml
Streaming Configuration:
  Enabled: Yes (for B2E, B2C chat interfaces)
  Protocol: Server-Sent Events (SSE)
  Benefit: First token visible in ~500ms instead of waiting for full 2500ms

  Flow:
    1. Pre-retrieval + search completes (~500ms)
    2. Start streaming LLM response token-by-token
    3. User sees first words while generation continues
    4. Post-processing applied after full response

  Constraints:
    - PII scan runs on full response (buffered)
    - Citations appended after streaming completes
    - Confidence score calculated post-stream
```

---

## Service-Level Latency Targets

### By Tier

| Tier | P50 Target | P95 Target | P99 Target | Max Concurrent |
|------|-----------|-----------|-----------|----------------|
| **B2E (Internal)** | < 2s | < 5s | < 10s | 200 users |
| **B2B Silver** | < 2s | < 5s | < 8s | 500 req/min |
| **B2B Gold** | < 1.5s | < 3s | < 5s | 2000 req/min |
| **B2C (Customer)** | < 2s | < 4s | < 8s | 1000 sessions |

### By Query Type

| Query Type | Expected Latency | Reason |
|-----------|-----------------|--------|
| Simple factual | 1.5–2.5s | GPT-4o-mini, fewer tokens |
| Procedural | 2–4s | GPT-4o, more context |
| Comparative | 3–5s | GPT-4o, multiple sources |
| Analytical | 4–8s | GPT-4o, complex reasoning |
| Cached (L1 hit) | < 10ms | Direct cache return |

### Degradation Thresholds

| Metric | Normal | Degraded | Critical | Action |
|--------|--------|----------|----------|--------|
| P95 latency | < 5s | 5–8s | > 8s | Scale up, alert |
| Error rate | < 1% | 1–5% | > 5% | Circuit breaker, alert |
| Cache hit rate | > 20% | 10–20% | < 10% | Investigate cache health |
| OpenAI 429 rate | < 1% | 1–5% | > 5% | Throttle, queue, alert |
| Search latency | < 500ms | 500ms–1s | > 1s | Scale search units |

### Performance Monitoring Dashboard

```yaml
Key Metrics (Real-Time):
  - Total queries/sec
  - P50, P95, P99 latency
  - Error rate (%)
  - Cache hit rate (L1, L2, L3)
  - OpenAI token consumption rate
  - Search QPS and latency
  - Active connections per service

Alerts:
  - P95 > 7s for 5 min → Warning
  - P95 > 10s for 5 min → Critical
  - Error rate > 5% for 2 min → Critical
  - OpenAI 429 > 5% for 5 min → Warning
  - Cache hit < 10% for 15 min → Warning
```

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Platform Team |
| Review | Quarterly |
| Related | [Architecture Guide](ARCHITECTURE-GUIDE.md), [ADR Decisions](ADR-ARCHITECTURE-DECISIONS.md) |
