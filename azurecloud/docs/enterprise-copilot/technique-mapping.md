# Enterprise Copilot - Technique to Implementation Mapping

## Overview

This document maps each technique used in the Enterprise Copilot project to specific algorithms, models, and Azure services for implementation.

---

## Search & Retrieval Techniques

| Technique | Algorithm/Model | Azure Service | Implementation Details |
|-----------|----------------|---------------|----------------------|
| **BM25 Ranking** | BM25F (Okapi BM25) | Azure AI Search | Built-in keyword search, tune `k1` (1.2-2.0) and `b` (0.75) |
| **Vector Search** | HNSW (Hierarchical Navigable Small World) | Azure AI Search | Configure `m=4`, `efConstruction=400`, `efSearch=500` |
| **Hybrid Search** | RRF (Reciprocal Rank Fusion) | Azure AI Search | Combine vector + BM25 scores, `k=60` default |
| **Semantic Ranking** | Cross-Encoder Transformer | Azure AI Search Semantic Ranker | Enable `queryType=semantic`, configure semantic config |
| **Re-ranking** | MMR (Maximal Marginal Relevance) | Custom code | Balance relevance vs diversity, `lambda=0.5` |
| **Query Expansion** | LLM-based synonyms | Azure OpenAI GPT-4o | Generate query variants for broader recall |

### Hybrid Search Configuration
```json
{
  "search": "employee vacation policy",
  "vectorQueries": [{
    "kind": "vector",
    "vector": [0.1, 0.2, ...],
    "fields": "chunk_vector",
    "k": 50
  }],
  "queryType": "semantic",
  "semanticConfiguration": "semantic-config",
  "top": 10
}
```

---

## Embedding & Vectorization

| Technique | Model | Dimensions | Use Case |
|-----------|-------|------------|----------|
| **Document Embedding** | text-embedding-3-large | 3072 | Primary chunk embeddings |
| **Query Embedding** | text-embedding-3-large | 3072 | Query-time vectorization |
| **Title Embedding** | text-embedding-3-small | 1536 | Lightweight title vectors |
| **Image Embedding** | CLIP (clip-vit-base-patch32) | 512 | Future: image search |

### Embedding Best Practices
- **Batch size**: 16-32 texts per API call
- **Rate limiting**: 1000 RPM for text-embedding-3-large
- **Caching**: Hash-based caching for unchanged chunks
- **Normalization**: Normalize vectors for cosine similarity

---

## Chunking Strategies

| Strategy | Algorithm | Best For | Parameters |
|----------|-----------|----------|------------|
| **Fixed-size** | Token-based split | General text | `chunk_size=512`, `overlap=64` |
| **Sentence** | NLTK/spaCy sentence tokenizer | Conversational content | Respect sentence boundaries |
| **Paragraph** | Double-newline split | Structured documents | Merge small paragraphs |
| **Heading-aware** | Markdown header parsing | Technical docs | Preserve section hierarchy |
| **Semantic** | Embedding similarity clustering | Mixed content | Cluster by topic similarity |

### Recommended: Heading-Aware Chunking
```python
config = ChunkingConfig(
    strategy=ChunkingStrategy.HEADING_AWARE,
    max_tokens=512,
    min_tokens=50,
    overlap_tokens=64,
    include_heading_in_chunk=True
)
```

---

## Intent Detection & Query Classification

| Technique | Model/Method | When to Use |
|-----------|--------------|-------------|
| **Rule-based** | Regex + keyword matching | Simple, deterministic intents |
| **Zero-shot Classification** | GPT-4o with instruction prompt | Flexible, new intent types |
| **Few-shot Classification** | GPT-4o with examples | High accuracy needed |
| **Fine-tuned Classifier** | BERT/RoBERTa fine-tuned | High volume, latency-sensitive |

### Intent Classification Prompt
```
Classify the user's intent into one of these categories:
- qa: Factual question answering
- summarize: Document or topic summarization
- compare: Comparing policies or options
- procedural: How-to or process questions
- clarify: Follow-up or clarification

Query: "{query}"
Intent:
```

---

## LLM Techniques

| Technique | Implementation | Purpose |
|-----------|----------------|---------|
| **RAG (Retrieval-Augmented Generation)** | Custom orchestrator | Ground responses in documents |
| **Chain-of-Thought** | System prompt instruction | Complex reasoning |
| **Grounding Constraints** | System prompt rules | Prevent hallucination |
| **Citation Injection** | Context formatting | Source attribution |
| **Token Budget Management** | tiktoken counting | Optimize context window |

### System Prompt Template
```
You are an enterprise knowledge assistant. Follow these rules strictly:

1. ONLY answer based on the provided context
2. If the context doesn't contain the answer, say "I don't have information about that"
3. ALWAYS cite your sources using [Source N] format
4. Be concise and professional
5. Never make up information not in the context

Context:
{retrieved_chunks}

User Question: {query}
```

---

## Security Techniques

| Technique | Implementation | Azure Service |
|-----------|----------------|---------------|
| **RBAC (Role-Based Access Control)** | Group membership filtering | Entra ID + AI Search filters |
| **ABAC (Attribute-Based Access Control)** | Metadata-based filters | AI Search filter expressions |
| **Security Trimming** | Query-time ACL filtering | `$filter=acl_groups/any(g: search.in(g, '{groups}'))` |
| **Document Classification** | Sensitivity labels | Microsoft Purview |
| **PII Detection** | Content safety scanning | Azure AI Content Safety |

### RBAC Filter Expression
```python
user_groups = ["HR-Team", "All-Employees"]
filter_expr = f"acl_groups/any(g: search.in(g, '{','.join(user_groups)}'))"
```

---

## Evaluation Techniques

| Metric | Algorithm | Implementation |
|--------|-----------|----------------|
| **Retrieval Precision@K** | Count relevant in top-k | `relevant_in_k / k` |
| **nDCG (Normalized DCG)** | Discounted cumulative gain | scikit-learn `ndcg_score` |
| **Groundedness** | LLM-as-judge | GPT-4o evaluates context support |
| **Faithfulness** | NLI model | Check entailment |
| **Hallucination Rate** | LLM detection | GPT-4o identifies fabrications |
| **Answer Relevance** | LLM scoring | GPT-4o rates relevance 0-1 |

### Evaluation Thresholds
| Metric | Pass Threshold | Block Threshold |
|--------|----------------|-----------------|
| Grounding Score | ≥ 0.85 | < 0.70 |
| Hallucination Rate | ≤ 0.05 | > 0.15 |
| Retrieval Precision@5 | ≥ 0.70 | < 0.50 |
| Answer Relevance | ≥ 0.80 | < 0.60 |

---

## Observability Techniques

| Technique | Tool | Purpose |
|-----------|------|---------|
| **Distributed Tracing** | Azure App Insights | End-to-end request tracking |
| **Metric Collection** | Prometheus + Grafana | Performance monitoring |
| **Log Aggregation** | Azure Log Analytics | Centralized logging |
| **Drift Detection** | Custom metrics | Model/retrieval degradation |
| **Alerting** | Azure Monitor Alerts | Proactive issue detection |

### Key Metrics to Track
```yaml
metrics:
  - query_latency_p50_ms
  - query_latency_p95_ms
  - query_latency_p99_ms
  - cache_hit_rate
  - retrieval_empty_rate
  - llm_token_usage
  - error_rate_by_type
  - user_satisfaction_score
```

---

## Document Processing Techniques

| Technique | Tool/Service | File Types |
|-----------|--------------|------------|
| **PDF Extraction** | Azure AI Document Intelligence | PDF |
| **OCR** | Azure AI Document Intelligence | Scanned PDFs, images |
| **Table Extraction** | Document Intelligence Layout | PDF with tables |
| **Office Documents** | python-docx, python-pptx | DOCX, PPTX |
| **HTML/Web** | BeautifulSoup, Trafilatura | HTML, web pages |
| **Markdown** | markdown-it | MD files |

### Document Intelligence Configuration
```python
from azure.ai.formrecognizer import DocumentAnalysisClient

client = DocumentAnalysisClient(endpoint, credential)
poller = client.begin_analyze_document(
    "prebuilt-layout",  # or "prebuilt-read" for OCR
    document=file_content
)
result = poller.result()
```

---

## Caching Strategies

| Cache Type | Storage | TTL | Use Case |
|------------|---------|-----|----------|
| **Answer Cache** | Cosmos DB | 1 hour | Identical query responses |
| **Retrieval Cache** | Cosmos DB | 30 min | Search results |
| **Embedding Cache** | Redis / Cosmos DB | 7 days | Pre-computed embeddings |
| **Session Cache** | Cosmos DB | 24 hours | Conversation context |

### Cache Key Generation
```python
import hashlib

def generate_cache_key(query: str, filters: dict) -> str:
    normalized = query.lower().strip()
    filter_str = json.dumps(filters, sort_keys=True)
    content = f"{normalized}:{filter_str}"
    return hashlib.sha256(content.encode()).hexdigest()
```

---

## Performance Optimization

| Technique | Implementation | Impact |
|-----------|----------------|--------|
| **Async Processing** | asyncio / aiohttp | 2-3x throughput |
| **Connection Pooling** | httpx.AsyncClient | Reduced latency |
| **Batch Embedding** | Batch API calls | 5-10x faster |
| **Index Partitioning** | AI Search partitions | Scale to millions |
| **Query Caching** | Cosmos DB | 50-80% cache hit |
| **Streaming Responses** | SSE / WebSocket | Perceived latency |

---

## Model Selection Guide

| Use Case | Recommended Model | Alternative |
|----------|-------------------|-------------|
| **Generation** | GPT-4o | GPT-4o-mini (cost) |
| **Embeddings** | text-embedding-3-large | text-embedding-3-small |
| **Classification** | GPT-4o-mini | Fine-tuned BERT |
| **Reranking** | Semantic Ranker | Cross-encoder |
| **Vision** | GPT-4o (vision) | Azure Vision |
| **Safety** | Azure Content Safety | GPT-4o moderation |

---

## Cost Optimization

| Technique | Savings | Trade-off |
|-----------|---------|-----------|
| Use GPT-4o-mini for classification | 90% | Slight accuracy drop |
| Cache answers (1hr TTL) | 50-80% | Stale responses |
| Smaller embeddings (1536 vs 3072) | 50% storage | Lower accuracy |
| Batch processing off-peak | 20-30% | Higher latency |
| Token budget limits | Variable | Truncated context |

---

## Quick Reference: Azure Services

| Capability | Azure Service |
|------------|---------------|
| LLM Generation | Azure OpenAI (GPT-4o) |
| Embeddings | Azure OpenAI (text-embedding-3) |
| Vector Search | Azure AI Search |
| Document OCR | Azure AI Document Intelligence |
| Safety | Azure AI Content Safety |
| Orchestration | Azure AI Foundry |
| Frontend | Copilot Studio |
| Caching | Azure Cosmos DB |
| Secrets | Azure Key Vault |
| Monitoring | Azure Monitor / App Insights |
| Auth | Microsoft Entra ID |

---

*Document Version: 1.0*
*Last Updated: 2025-01-15*
