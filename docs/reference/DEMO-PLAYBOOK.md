# Demo Playbook — Azure OpenAI Enterprise RAG Platform

> Comprehensive demo scenarios, scripts, and checklists for showcasing the Enterprise RAG Copilot platform across audiences and roles.

---

## Table of Contents

1. [Demo Scenarios by Audience](#1-demo-scenarios-by-audience)
2. [End-to-End RAG Demo](#2-end-to-end-rag-demo)
3. [Document Ingestion Demo](#3-document-ingestion-demo)
4. [Search & Retrieval Demo](#4-search--retrieval-demo)
5. [Security Demo](#5-security-demo)
6. [Monitoring & Observability Demo](#6-monitoring--observability-demo)
7. [Evaluation Demo](#7-evaluation-demo)
8. [Configuration Walkthrough](#8-configuration-walkthrough)
9. [Visualization & Reporting](#9-visualization--reporting)
10. [Transaction History & Audit Trail](#10-transaction-history--audit-trail)
11. [Scoring & Feedback](#11-scoring--feedback)
12. [Demo Environment Setup](#12-demo-environment-setup)
13. [Demo Checklist per Scenario](#13-demo-checklist-per-scenario)
14. [Role-Based Demo Tracks](#14-role-based-demo-tracks)

---

## 1. Demo Scenarios by Audience

### 1.1 Executive Demo (20 min)

**Goal:** Demonstrate ROI, value proposition, and strategic alignment.

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Show cost dashboard | Monthly cost per query: $0.03–$0.05, down from $0.46 at low volume |
| 2 | Live query: "What is our parental leave policy?" | Time-to-answer: hours → seconds |
| 3 | Show citation panel | 95% citation accuracy eliminates manual verification |
| 4 | Show adoption metrics | Target ≥60% adoption, ≥4.2/5 satisfaction |
| 5 | Show compliance dashboard | SOC 2, GDPR, ISO 42001 alignment |
| 6 | Show multi-tenant isolation | Department-level data boundaries |

**Key Metrics to Highlight:**
- 85% answer accuracy with grounding enforcement
- ≤3s P95 latency
- ≤5% hallucination rate
- 40% improvement in recall via hybrid search

### 1.2 Technical Architecture Demo (30 min)

**Goal:** Deep-dive into system design, data flow, and engineering decisions.

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Architecture diagram walkthrough | 6-layer security model, 3 parallel Azure Functions |
| 2 | Live trace through App Insights | 11-step query flow: Copilot → APIM → Functions → OpenAI → Response |
| 3 | Show Terraform modules | Infrastructure-as-code for all 29 Azure services |
| 4 | Show hybrid search config | Vector + BM25 + semantic ranking |
| 5 | Show model routing logic | GPT-4o for RAG (temp 0.1), GPT-4o-mini for rewrite (temp 0.3) |
| 6 | Show cache strategy | 3-tier: query (15–30 min), retrieval (30–60 min), embedding (30 days) |
| 7 | Show evaluation pipeline | Automated groundedness ≥0.80, hallucination ≤0.10 gates |

### 1.3 End-User Demo (15 min)

**Goal:** Show natural language interaction, citations, and conversational memory.

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Ask factual question | "What is the expense reimbursement process?" |
| 2 | Ask follow-up (multi-turn) | "What are the limits for international travel?" |
| 3 | Ask comparative question | "Compare our health plans" |
| 4 | Show citation links | Click-through to source documents |
| 5 | Submit feedback (thumbs up/down) | User satisfaction drives continuous improvement |
| 6 | Ask out-of-scope question | System declines gracefully with explanation |

### 1.4 Partner / API Integration Demo (25 min)

**Goal:** Showcase API capabilities, integration patterns, and extensibility.

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Show APIM developer portal | Self-service API key management |
| 2 | Call query API via Postman/curl | JSON response with answer, citations, confidence |
| 3 | Call ingestion API | Upload document, show processing pipeline |
| 4 | Show webhook notifications | Real-time status updates for async operations |
| 5 | Show rate limiting & quotas | Per-tenant limits: B2E 50/min, B2C 20/min |
| 6 | Show SDK examples | Python, C#, JavaScript integration samples |

---

## 2. End-to-End RAG Demo

### 2.1 Query Flow Walkthrough

```
User Query → Pre-Retrieval → Search → Rerank → LLM → Response
```

**Step-by-step:**

1. **Input Query**: User submits "What is our remote work policy for contractors?"
2. **Pre-Retrieval Processing**:
   - Intent detection: `factual_qa`
   - Query normalization: lowercase, spell-check, expansion
   - Metadata extraction: department=HR, document_type=policy
   - ACL filter building: `aclGroups IN ('All Employees', 'HR Team')`
   - Cache check: query hash lookup in Redis (TTL 15–30 min)
3. **Hybrid Search**:
   - Vector search: text-embedding-3-large (3072 dimensions)
   - BM25 keyword search: full-text index
   - Semantic ranking: Azure AI Search semantic ranker
   - Filter application: department, effective date, ACL groups
4. **Post-Retrieval Reranking**:
   - Deduplication: cosine similarity >0.85 → merge
   - Temporal prioritization: prefer latest effective date
   - Conflict handling: flag contradictory sources
   - Context compression: fit within 128K token window
   - Relevance scoring: top-K (K=8) selection
5. **LLM Generation**:
   - Model: GPT-4o (temperature 0.1, top-p 0.5)
   - System prompt: enforce context-only answers, require citations
   - Retrieved context injected into prompt
   - Max tokens: 2000
6. **Post-Processing**:
   - PII scan (Presidio): SSN, credit card, email masking
   - Content safety check: hate, sexual, violence, self-harm filters
   - Citation extraction and validation
   - Confidence scoring
7. **Response**:
   ```json
   {
     "answer": "Contractors may work remotely up to 3 days per week...",
     "citations": [
       {"title": "Remote Work Policy v3.2", "url": "...", "excerpt": "..."}
     ],
     "confidence": 0.87,
     "intent": "factual_qa",
     "followUpSuggestions": ["What about full-time employees?"]
   }
   ```

### 2.2 Demo Script

```bash
# 1. Submit query
curl -X POST https://apim-genai-copilot.azure-api.net/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our remote work policy?", "conversationId": "demo-001"}'

# 2. Show distributed trace
# Navigate to App Insights → Transaction Search → filter by operation_Id

# 3. Show cache behavior (repeat same query)
curl -X POST https://apim-genai-copilot.azure-api.net/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "What is our remote work policy?", "conversationId": "demo-001"}'
# Note: response time drops from ~2.5s to ~200ms (cache hit)
```

---

## 3. Document Ingestion Demo

### 3.1 Pipeline Flow

```
Upload → OCR/Parse → Chunk → Embed → Index → Verify
```

| Stage | Service | Details |
|-------|---------|---------|
| Upload | Azure Storage (Data Lake Gen2) | Max 100MB, supported: PDF, DOCX, XLSX, PPTX, TXT, CSV, HTML, images |
| OCR/Parse | Document Intelligence | Prebuilt-read model for scanned PDFs; layout model for structured docs |
| Chunk | Azure Functions | Strategy by doc type: policies 700–1200 tokens, contracts 400–800, manuals 800–1500 |
| Embed | Azure OpenAI | text-embedding-3-large (3072 dimensions) |
| Index | Azure AI Search | HNSW algorithm, hybrid index (vector + keyword + semantic) |
| Verify | Evaluation pipeline | Chunk quality, embedding coverage, search recall validation |

### 3.2 Demo Script

```bash
# 1. Upload document
curl -X POST https://apim-genai-copilot.azure-api.net/v1/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample-policy.pdf" \
  -F "metadata={\"department\":\"HR\",\"docType\":\"policy\",\"aclGroups\":[\"All Employees\"]}"

# 2. Check processing status
curl https://apim-genai-copilot.azure-api.net/v1/ingest/status/{jobId} \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {"jobId": "ing-123", "status": "completed", "chunks": 24, "duration": "12.3s"}

# 3. Verify in search index
curl -X POST https://search-genai-copilot.search.windows.net/indexes/documents/docs/search \
  -H "api-key: $SEARCH_KEY" \
  -d '{"search": "remote work policy", "top": 5, "queryType": "semantic"}'
```

### 3.3 Chunking Visualization

Show side-by-side comparison:

| Document Type | Chunk Size | Overlap | Strategy |
|---------------|-----------|---------|----------|
| HR Policies & SOPs | 700–1200 tokens | 100 tokens | Section-aware, heading preservation |
| Legal Contracts | 400–800 tokens | 50 tokens | Clause-level splitting |
| Technical Manuals | 800–1500 tokens | 150 tokens | Heading-hierarchy aware |
| Scanned PDFs | 500–900 tokens | 75 tokens | OCR + layout-aware splitting |
| Spreadsheets | 300–600 tokens | 0 tokens | Row-group or sheet-based |

---

## 4. Search & Retrieval Demo

### 4.1 Query Types

| Query Type | Example | Expected Behavior |
|------------|---------|-------------------|
| Factual Q&A | "What is the PTO accrual rate?" | Direct answer with citation |
| Procedural | "How do I submit an expense report?" | Step-by-step instructions |
| Comparative | "Compare Plan A vs Plan B" | Side-by-side comparison table |
| Summarization | "Summarize the Q3 earnings report" | Condensed summary with key points |
| Clarification | "What does 'vesting' mean?" | Definition with contextual examples |

### 4.2 Hybrid Search Demonstration

```
Step 1: Vector Search Only
  → Semantic understanding, handles synonyms
  → May miss exact keyword matches

Step 2: BM25 Keyword Search Only
  → Exact term matching, handles specific codes/numbers
  → May miss semantic similarity

Step 3: Hybrid (Vector + BM25 + Semantic Ranking)
  → Best of both: semantic understanding + keyword precision
  → Semantic ranker reorders for relevance
  → Result: 40% better recall than vector-only
```

### 4.3 Filter Demonstration

```json
{
  "search": "expense policy",
  "filter": "department eq 'Finance' and effectiveDate ge 2024-01-01",
  "queryType": "semantic",
  "semanticConfiguration": "default",
  "top": 10
}
```

**Show filter combinations:**
- Department filter: restrict to HR, Finance, Engineering
- Date filter: only documents effective after a certain date
- ACL filter: enforce group-based access (auto-applied from user token)
- Document type filter: policies only, SOPs only, contracts only

### 4.4 Reranking Visualization

Show ranked results before and after reranking:

| Rank | Before Rerank (Vector Score) | After Rerank (Semantic Score) |
|------|------------------------------|-------------------------------|
| 1 | Generic expense overview (0.89) | Specific expense policy v3 (0.94) |
| 2 | Old expense form (0.87) | Expense submission SOP (0.91) |
| 3 | Specific expense policy v3 (0.85) | Expense limits table (0.88) |

---

## 5. Security Demo

### 5.1 RBAC Enforcement

```
Demo: Two users with different roles query the same topic

User A (HR Team member):
  Query: "What are the salary bands?"
  → Full response with salary data and citations

User B (Engineering Team member):
  Query: "What are the salary bands?"
  → "I don't have access to salary information for your role.
     Please contact HR for this information."
```

**Show in logs:**
- User A: `aclGroups: ['All Employees', 'HR Team']` → filter matches salary documents
- User B: `aclGroups: ['All Employees', 'Engineering']` → filter excludes salary documents

### 5.2 Tenant Isolation

```
Demo: Two tenants querying the same platform

Tenant: Contoso
  Query: "What is our refund policy?"
  → Returns Contoso-specific refund policy

Tenant: Fabrikam
  Query: "What is our refund policy?"
  → Returns Fabrikam-specific refund policy
  → Zero data leakage between tenants
```

**Show in Cosmos DB:**
- Partition key: `/tenantId`
- Cross-partition queries blocked
- Separate search index per tenant (or filtered)

### 5.3 PII Masking

```
Demo: Query that triggers PII detection

Input:  "Show me John Smith's record, SSN 123-45-6789"
Logged: "Show me [PERSON]'s record, SSN [SSN_MASKED]"

Output contains PII detected in source documents:
  "The employee (SSN: ***-**-6789) has been with the company..."
  → Last 4 digits only, per masking rules
```

**PII Detection Stack:**
- Presidio Analyzer: entity recognition (SSN, credit card, email, phone, name)
- Regex patterns: structured PII (SSN: `\d{3}-\d{2}-\d{4}`)
- Azure Content Safety: harmful content filtering
- spaCy NER: context-aware entity extraction

### 5.4 Audit Trail

```json
{
  "timestamp": "2024-11-15T10:23:45Z",
  "userId": "user@contoso.com",
  "tenantId": "contoso",
  "queryHash": "a1b2c3d4",
  "intent": "factual_qa",
  "documentsAccessed": ["doc-001", "doc-002"],
  "piiDetected": true,
  "piiEntities": ["PERSON", "SSN"],
  "responseConfidence": 0.87,
  "latencyMs": 2450,
  "cacheHit": false,
  "contentFilterTriggered": false
}
```

---

## 6. Monitoring & Observability Demo

### 6.1 App Insights Dashboards

**Dashboard 1: Real-Time Operations**
- Request rate (queries/min)
- Average and P95 latency
- Error rate by type (4xx, 5xx)
- Active users and sessions

**Dashboard 2: RAG Pipeline Health**
- Search latency (P50/P95)
- LLM latency (P50/P95)
- Cache hit ratio
- Token consumption rate

**Dashboard 3: Quality Metrics**
- Groundedness score trend (target ≥0.80)
- Hallucination rate trend (target ≤0.10)
- Citation accuracy (target ≥0.90)
- User satisfaction (target ≥4.2/5)

### 6.2 Distributed Tracing

```
Demo: Trace a single query through all services

Operation ID: abc-123-def
├── APIM Gateway (12ms)
│   ├── JWT validation (3ms)
│   └── Rate limit check (2ms)
├── Pre-Retrieval Function (85ms)
│   ├── Intent detection (25ms)
│   ├── Query expansion (30ms)
│   └── Cache lookup (15ms) → MISS
├── RAG Processor Function (2200ms)
│   ├── Embedding generation (50ms)
│   ├── Hybrid search (200ms)
│   ├── Semantic ranking (150ms)
│   ├── LLM generation (1600ms)
│   └── Post-processing (200ms)
│       ├── PII scan (80ms)
│       ├── Content safety (70ms)
│       └── Citation validation (50ms)
└── Response (total: 2450ms)
```

### 6.3 Alert Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High Latency | P95 > 5s for 5 min | Sev 2 | Page on-call, scale out |
| Error Spike | Error rate > 5% for 5 min | Sev 1 | Page on-call, investigate |
| Groundedness Drop | Score < 0.75 for 1 hour | Sev 2 | Notify ML team |
| Token Spike | > 150% daily average | Sev 3 | Notify FinOps team |
| PII Leak | Unmasked PII in output | Sev 0 | Block response, page security |
| Cache Degradation | Hit ratio < 30% for 30 min | Sev 3 | Check Redis health |

---

## 7. Evaluation Demo

### 7.1 Groundedness Scoring

```
Demo: Show LLM-as-judge evaluation

Query: "What is the maximum PTO carryover?"
Answer: "Employees can carry over up to 5 days of unused PTO."
Context: "Section 4.2: PTO carryover is limited to 5 business days..."

Groundedness Score: 0.92 (PASS ≥ 0.80)
Justification: Answer directly supported by context section 4.2
```

### 7.2 Hallucination Detection

```
Demo: Detect hallucinated content

Query: "What is the company's stock vesting schedule?"
Answer: "Stock vests over 4 years with a 1-year cliff, and the company
         also offers quarterly bonuses up to 15%."
Context: Only mentions 4-year vesting with 1-year cliff.

Hallucination Score: 0.35 (FAIL: hallucination detected)
Flagged: "quarterly bonuses up to 15%" — not grounded in context
```

### 7.3 A/B Test Results

```
Demo: Compare two configurations

Variant A (current): temperature=0.1, top-K=8, chunk_size=1000
Variant B (candidate): temperature=0.05, top-K=10, chunk_size=800

Results after 500 queries per variant:
┌────────────────┬───────────┬───────────┬─────────┐
│ Metric         │ Variant A │ Variant B │ Winner  │
├────────────────┼───────────┼───────────┼─────────┤
│ Groundedness   │ 0.82      │ 0.86      │ B (+5%) │
│ Relevance      │ 0.78      │ 0.81      │ B (+4%) │
│ Latency P95    │ 2.8s      │ 3.1s      │ A (-10%)│
│ Cost/query     │ $0.042    │ $0.048    │ A (-12%)│
│ User rating    │ 4.1/5     │ 4.3/5     │ B (+5%) │
└────────────────┴───────────┴───────────┴─────────┘
Recommendation: Deploy Variant B (quality improvement outweighs cost/latency)
```

### 7.4 Golden Dataset Evaluation

```
Demo: Run automated evaluation against 200 golden query-answer pairs

Categories:
- Factual Q&A: 80 queries → 92% pass rate
- Procedural: 40 queries → 88% pass rate
- Comparative: 30 queries → 85% pass rate
- Summarization: 30 queries → 90% pass rate
- Edge cases: 20 queries → 78% pass rate

Overall: 88.6% pass rate (target ≥85%) ✅
Release gate: PASSED
```

---

## 8. Configuration Walkthrough

### 8.1 Model Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Temperature | 0.1 | Low creativity for factual accuracy |
| Top-p | 0.5 | Focused token sampling |
| Max tokens | 2000 | Sufficient for detailed answers |
| Frequency penalty | 0.0 | No repetition penalty needed |
| Presence penalty | 0.0 | No topic diversity forcing |
| Model (RAG) | GPT-4o | Best quality for retrieval-augmented generation |
| Model (rewrite) | GPT-4o-mini | Cost-efficient for query rewriting |

### 8.2 Search Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Query type | Semantic | Best for natural language |
| Search mode | Hybrid (vector + BM25) | 40% better recall than vector-only |
| Top-K results | 8 | Optimal balance of context and noise |
| Semantic config | default | Pre-configured for document schema |
| Scoring profile | recency-boosted | Prefer recent documents |
| Vector dimensions | 3072 | text-embedding-3-large |
| HNSW (m) | 4 | Memory-efficient graph |
| HNSW (efConstruction) | 400 | High-quality index build |
| HNSW (efSearch) | 500 | High-quality search |

### 8.3 Cache Settings

| Cache Tier | TTL | Use Case |
|------------|-----|----------|
| Query cache (Redis) | 15–30 min | Exact query match |
| Retrieval cache (Redis) | 30–60 min | Search results for similar queries |
| Embedding cache (Redis) | 30 days | Pre-computed embeddings |
| Session cache (Cosmos DB) | 24 hours | Conversation context |

### 8.4 Content Filters

| Category | Input Threshold | Output Threshold |
|----------|----------------|-----------------|
| Hate | Medium | Medium |
| Sexual | Medium | Medium |
| Violence | Medium | Medium |
| Self-harm | Medium | Medium |
| Prompt injection | Enabled | N/A |
| Jailbreak detection | Enabled | N/A |
| PII masking | Enabled | Enabled |

---

## 9. Visualization & Reporting

### 9.1 Cost Dashboard

```
Monthly Cost Breakdown (Production):
┌─────────────────────┬──────────┬─────────┐
│ Category            │ Cost     │ % Total │
├─────────────────────┼──────────┼─────────┤
│ AI Services         │ $4,729   │ 34%     │
│ Networking          │ $4,173   │ 30%     │
│ Compute (AKS/Func)  │ $3,060   │ 22%     │
│ Storage (Data+Cosmos)│ $1,113   │ 8%      │
│ Monitoring          │ $834     │ 6%      │
├─────────────────────┼──────────┼─────────┤
│ Total               │ $13,909  │ 100%    │
└─────────────────────┴──────────┴─────────┘
```

### 9.2 Evaluation Metrics Dashboard

```
Weekly Quality Trend:
Groundedness:  ██████████████████░░ 0.84 (target: 0.80) ✅
Relevance:     ████████████████░░░░ 0.79 (target: 0.70) ✅
Hallucination: ███░░░░░░░░░░░░░░░░░ 0.07 (target: ≤0.10) ✅
Citation Acc:  ██████████████████░░ 0.91 (target: 0.90) ✅
User Rating:   █████████████████░░░ 4.3/5 (target: 4.2) ✅
```

### 9.3 Usage Analytics

- Queries per day (trend line, peak hours)
- Top query categories (factual, procedural, comparative)
- Department usage breakdown
- Unique users per week
- Average session length (queries per conversation)

### 9.4 Token Consumption

```
Daily Token Budget Tracking:
Platform budget:    5,000,000 tokens/day
Current usage:      3,200,000 tokens/day (64%)
Per-tenant avg:     400,000 tokens/day
Per-user avg:       12,000 tokens/day
Per-session avg:    3,500 tokens/day

Top consumers:
1. Finance Dept:    890,000 tokens (28%)
2. HR Dept:         720,000 tokens (23%)
3. Engineering:     640,000 tokens (20%)
```

---

## 10. Transaction History & Audit Trail

### 10.1 Query History

```
Demo: Show query history for compliance audit

Filters: Date range, user, department, intent type, confidence range
Export: CSV, JSON, or Power BI dataset

Sample record:
{
  "queryId": "q-2024-1115-001234",
  "timestamp": "2024-11-15T10:23:45Z",
  "userId": "jdoe@contoso.com",
  "department": "Finance",
  "query": "What are the Q3 revenue projections?",
  "intent": "factual_qa",
  "confidence": 0.91,
  "documentsAccessed": ["fin-q3-report-v2", "fin-budget-2024"],
  "latencyMs": 2100,
  "tokensUsed": 1850,
  "cacheHit": false,
  "piiDetected": false,
  "feedbackScore": 5
}
```

### 10.2 Document Access Logs

```
Document: "HR-Policy-Salary-Bands-v3.pdf"
Access log (last 30 days):
- 142 queries referenced this document
- 23 unique users accessed
- Departments: HR (85%), Management (12%), Legal (3%)
- Average confidence when cited: 0.88
- Last updated: 2024-10-01
```

### 10.3 Change Tracking

```
Index Change Log:
┌─────────────┬────────────┬──────────┬──────────────────────────────┐
│ Timestamp   │ Action     │ User     │ Details                      │
├─────────────┼────────────┼──────────┼──────────────────────────────┤
│ Nov 15 09:00│ INGEST     │ system   │ 12 docs added (HR policies)  │
│ Nov 14 22:00│ REINDEX    │ cron     │ Full index rebuild (2.1M docs)│
│ Nov 14 15:30│ DELETE     │ admin    │ Deprecated policy removed    │
│ Nov 14 10:00│ UPDATE     │ system   │ 3 docs re-chunked (v2)       │
│ Nov 13 09:00│ INGEST     │ system   │ 8 docs added (Finance)       │
└─────────────┴────────────┴──────────┴──────────────────────────────┘
```

---

## 11. Scoring & Feedback

### 11.1 Confidence Display

```
Response to user includes:
┌──────────────────────────────────────────────────────┐
│ Answer: Employees can carry over up to 5 days...     │
│                                                      │
│ Confidence: ████████░░ 87%                           │
│ Sources: HR-Policy-PTO-v3.pdf (Section 4.2)          │
│                                                      │
│ Was this helpful?  👍  👎                              │
└──────────────────────────────────────────────────────┘
```

**Confidence Thresholds:**
- ≥0.80: High confidence — display answer normally
- 0.60–0.79: Medium — display with disclaimer: "This answer may be incomplete"
- <0.60: Low — escalate to human: "I'm not confident. Routing to a specialist."

### 11.2 Feedback Collection

| Signal | Collection Method | Storage |
|--------|-------------------|---------|
| Thumbs up/down | In-line button | Cosmos DB `feedback` container |
| Star rating (1–5) | Post-session survey | Cosmos DB `feedback` container |
| Free-text comment | Optional field | Cosmos DB `feedback` container |
| Implicit (re-query) | Query log analysis | Log Analytics |
| Implicit (session length) | Session tracking | App Insights |

### 11.3 User Satisfaction Tracking

```
Weekly CSAT Report:
- Total feedback received: 1,234
- Positive (thumbs up): 1,048 (85%)
- Negative (thumbs down): 186 (15%)
- Average star rating: 4.3/5
- NPS score: +42

Top negative feedback themes:
1. "Answer was too vague" (32%)
2. "Wrong document cited" (24%)
3. "Didn't understand my question" (18%)
4. "Too slow" (14%)
5. "Other" (12%)
```

---

## 12. Demo Environment Setup

### 12.1 Prerequisites

| Requirement | Details |
|-------------|---------|
| Azure subscription | Demo subscription with contributor access |
| Azure CLI | v2.50+ installed and authenticated |
| Python | 3.11+ with `requirements.txt` installed |
| Postman / curl | For API calls |
| Browser | Edge/Chrome for Azure Portal dashboards |
| Sample data | Pre-loaded in `demo/sample-data/` directory |
| VPN | Connected to corporate network (private endpoints) |

### 12.2 Environment Variables

```bash
# Fetch from Key Vault
export AZURE_OPENAI_ENDPOINT=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name openai-endpoint --query value -o tsv)
export AZURE_OPENAI_KEY=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name openai-key --query value -o tsv)
export AZURE_SEARCH_ENDPOINT=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name search-endpoint --query value -o tsv)
export AZURE_SEARCH_KEY=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name search-key --query value -o tsv)
export COSMOS_CONNECTION=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name cosmos-connection --query value -o tsv)
export REDIS_CONNECTION=$(az keyvault secret show --vault-name kv-genai-copilot-dev --name redis-connection --query value -o tsv)
```

### 12.3 Sample Data

| Dataset | Count | Purpose |
|---------|-------|---------|
| HR policies | 25 docs | PTO, benefits, remote work |
| Finance policies | 15 docs | Expense, travel, procurement |
| IT SOPs | 20 docs | Password reset, VPN, access requests |
| Legal contracts | 10 docs | NDA, vendor agreements (anonymized) |
| Golden Q&A pairs | 200 pairs | Evaluation and demo queries |

### 12.4 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Expired token | Re-authenticate: `az login` |
| 403 Forbidden | Missing RBAC role | Check Entra ID group membership |
| 429 Too Many Requests | Rate limit exceeded | Wait 60s or reduce query rate |
| 504 Gateway Timeout | LLM latency spike | Retry; check Azure OpenAI status |
| Empty results | Index not populated | Run ingestion pipeline first |
| Low confidence scores | Stale index | Trigger index refresh job |

---

## 13. Demo Checklist per Scenario

### 13.1 Executive Demo Checklist

- [ ] Cost dashboard loaded in browser tab
- [ ] Adoption metrics dashboard ready
- [ ] 3 pre-tested queries prepared (factual, comparative, follow-up)
- [ ] Compliance report exported
- [ ] ROI slide deck open (backup if live demo fails)
- [ ] Internet/VPN connectivity verified
- [ ] Fallback: recorded demo video available

### 13.2 Technical Demo Checklist

- [ ] App Insights open with recent traces
- [ ] Terraform repo accessible (show IaC)
- [ ] Postman collection loaded with API calls
- [ ] Search index explorer open
- [ ] Cosmos DB Data Explorer open
- [ ] Redis CLI connected (show cache)
- [ ] Evaluation pipeline results loaded
- [ ] Architecture diagram printed/displayed

### 13.3 End-User Demo Checklist

- [ ] Copilot Studio / chat UI loaded
- [ ] Sample queries printed (5 per category)
- [ ] Multi-turn conversation pre-planned
- [ ] Feedback mechanism visible
- [ ] Out-of-scope query prepared (show graceful decline)
- [ ] Network connectivity stable

### 13.4 Partner Demo Checklist

- [ ] APIM developer portal accessible
- [ ] API keys provisioned for demo tenant
- [ ] Postman/curl examples ready
- [ ] SDK samples in Python, C#, JS
- [ ] Rate limiting demo configured
- [ ] Webhook endpoint configured

---

## 14. Role-Based Demo Tracks

### 14.1 Manager Track

**Focus:** ROI, timeline, adoption, risk management

| Demo Element | What to Show | Key Message |
|-------------|-------------|-------------|
| Cost dashboard | Monthly spend vs budget | Under budget, cost per query declining |
| Adoption metrics | User growth, department coverage | 60%+ adoption target achievable |
| RACI matrix | Roles and responsibilities | Clear ownership model |
| Risk register | Top risks with mitigations | Proactive risk management |
| Timeline | 10-phase delivery plan | On track, phase gates enforced |

### 14.2 Architect Track

**Focus:** Design quality, scalability, extensibility

| Demo Element | What to Show | Key Message |
|-------------|-------------|-------------|
| Architecture diagram | 6-layer security, 3 Functions | Defense-in-depth, modular design |
| ADR log | Key decisions with trade-offs | Every choice is justified |
| Scalability test | Load test results (500 concurrent) | Handles 2K queries/min peak |
| Integration patterns | APIM, webhooks, SDK | Extensible API-first design |
| DR strategy | RPO/RTO targets and test results | Business continuity assured |

### 14.3 DevOps Track

**Focus:** CI/CD, automation, operational excellence

| Demo Element | What to Show | Key Message |
|-------------|-------------|-------------|
| Pipeline dashboard | CI/CD stages with gates | Automated quality enforcement |
| Terraform plan | IaC for all 29 services | Reproducible infrastructure |
| Monitoring alerts | Alert rules and escalation | Proactive incident detection |
| Blue-green deployment | Zero-downtime deployment | No user impact during releases |
| Runbooks | Incident response procedures | Operational maturity |

### 14.4 Developer Track

**Focus:** Code quality, APIs, testing

| Demo Element | What to Show | Key Message |
|-------------|-------------|-------------|
| API documentation | OpenAPI spec via APIM | Developer-friendly APIs |
| Code walkthrough | RAG pipeline, chunking, embedding | Clean, modular code |
| Unit test suite | pytest with Azure SDK mocks | 80%+ coverage |
| Local dev setup | Docker Compose environment | Fast developer onboarding |
| SDK examples | Python, C#, JS integration | Easy to integrate |

### 14.5 Tester Track

**Focus:** Quality assurance, test coverage, evaluation

| Demo Element | What to Show | Key Message |
|-------------|-------------|-------------|
| Test pyramid | Unit → Integration → E2E → Eval | Comprehensive test strategy |
| Golden dataset | 200 Q&A pairs with categories | Systematic quality measurement |
| Evaluation pipeline | Automated groundedness/hallucination | Continuous quality monitoring |
| Security tests | Pen test results, prompt injection | Security hardened |
| Performance tests | Load test results with SLAs | Meets all latency targets |

---

## Cross-References

- [TECH-STACK-SERVICES.md](./TECH-STACK-SERVICES.md) — Full Azure services inventory
- [INTERVIEW-KNOWLEDGE-GUIDE.md](./INTERVIEW-KNOWLEDGE-GUIDE.md) — Q&A for defending architecture
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Detailed testing approach
- [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) — Cost details
- [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) — Security architecture
- [LLD-ARCHITECTURE.md](../../azurecloud/docs/LLD-ARCHITECTURE.md) — Low-level design
- [MODEL-BENCHMARKING.md](../governance/MODEL-BENCHMARKING.md) — Evaluation framework
- [RESPONSIBLE-AI.md](../governance/RESPONSIBLE-AI.md) — AI governance
