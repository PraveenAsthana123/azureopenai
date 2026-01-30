# Model Benchmarking & Output Evaluation

> **Evaluation Framework, Sensitivity Analysis, and Release Gate Criteria**
>
> For Azure OpenAI Enterprise Platform

---

## Table of Contents

1. [Evaluation Metrics](#evaluation-metrics)
2. [Sensitivity Analysis](#sensitivity-analysis)
3. [Benchmarking Framework](#benchmarking-framework)
4. [Model Comparison Matrix](#model-comparison-matrix)
5. [A/B Testing Framework](#ab-testing-framework)
6. [Release Gate Criteria](#release-gate-criteria)

---

## Evaluation Metrics

### Core RAG Metrics

| Metric | Definition | Method | Target | Critical Threshold |
|--------|-----------|--------|--------|-------------------|
| **Groundedness** | Answer is supported by retrieved context | LLM-as-judge (GPT-4o evaluates if answer follows context) | ≥ 0.80 | < 0.70 blocks deployment |
| **Relevance** | Answer addresses the user's query | LLM-as-judge (GPT-4o scores query-answer alignment) | ≥ 0.70 | < 0.60 blocks deployment |
| **Coherence** | Answer is logically structured and clear | LLM-as-judge (GPT-4o evaluates logical flow) | ≥ 0.80 | < 0.70 triggers review |
| **Fluency** | Answer is grammatically correct and natural | LLM-as-judge (GPT-4o scores language quality) | ≥ 0.85 | < 0.75 triggers review |
| **Citation Accuracy** | Citations correctly map to source content | Rule-based (verify cited doc/page contains claim) | ≥ 0.90 | < 0.80 blocks deployment |
| **Hallucination Rate** | Fraction of claims not in context | LLM-as-judge + rule-based hybrid | ≤ 0.10 | > 0.15 blocks deployment |

### Retrieval Metrics

| Metric | Definition | Method | Target |
|--------|-----------|--------|--------|
| **Precision@K** | Fraction of top-K results that are relevant | Human-labeled relevance judgments | ≥ 0.70 |
| **Recall@K** | Fraction of relevant docs in top-K | Human-labeled relevance judgments | ≥ 0.60 |
| **NDCG@10** | Normalized discounted cumulative gain | Graded relevance (0–3 scale) | ≥ 0.65 |
| **MRR** | Mean reciprocal rank of first relevant | Human-labeled | ≥ 0.75 |
| **Hit Rate** | Queries with at least 1 relevant result | Binary relevance | ≥ 0.90 |

### Operational Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **Latency P50** | Median end-to-end response time | < 2s |
| **Latency P95** | 95th percentile response time | < 5s |
| **Token Efficiency** | Avg tokens per query (input + output) | < 3000 |
| **Cost per Query** | Total Azure cost per query | < $0.025 |
| **Refusal Rate** | Queries where model declines to answer | < 15% |
| **User Satisfaction** | Thumbs up / (thumbs up + thumbs down) | ≥ 80% |

### LLM-as-Judge Prompt Templates

**Groundedness Evaluation:**

```
You are an evaluation judge. Given the CONTEXT and ANSWER, score groundedness from 1-5.

5 = Every claim in the answer is directly supported by the context
4 = Most claims are supported, minor extrapolations
3 = Some claims are supported, some are not in context
2 = Most claims are not supported by context
1 = Answer contradicts or is unrelated to context

CONTEXT: {context}
ANSWER: {answer}

Score (1-5):
Reasoning:
```

**Relevance Evaluation:**

```
You are an evaluation judge. Given the QUERY and ANSWER, score relevance from 1-5.

5 = Answer directly and completely addresses the query
4 = Answer mostly addresses the query with minor gaps
3 = Answer partially addresses the query
2 = Answer is tangentially related
1 = Answer does not address the query

QUERY: {query}
ANSWER: {answer}

Score (1-5):
Reasoning:
```

---

## Sensitivity Analysis

### Temperature Sweep

| Temperature | Groundedness | Relevance | Coherence | Fluency | Diversity | Recommendation |
|-------------|-------------|-----------|-----------|---------|-----------|----------------|
| 0.0 | 0.91 | 0.86 | 0.88 | 0.87 | Very low | Deterministic, repetitive |
| 0.1 | **0.89** | **0.85** | **0.87** | **0.88** | Low | **Best for RAG (selected)** |
| 0.3 | 0.84 | 0.82 | 0.85 | 0.89 | Medium | Good for creative tasks |
| 0.5 | 0.78 | 0.79 | 0.83 | 0.90 | Medium-high | Too much variation for factual |
| 0.7 | 0.72 | 0.74 | 0.80 | 0.90 | High | Not suitable for RAG |
| 1.0 | 0.61 | 0.65 | 0.74 | 0.88 | Very high | Creative only |

### Top-p Sweep

| Top-p | Groundedness | Relevance | Output Consistency | Recommendation |
|-------|-------------|-----------|-------------------|----------------|
| 0.1 | 0.90 | 0.84 | Very high | Too constrained |
| 0.3 | 0.89 | 0.85 | High | Good for strict factual |
| **0.5** | **0.88** | **0.84** | **High** | **Selected for RAG** |
| 0.7 | 0.85 | 0.83 | Medium | Acceptable |
| 0.9 | 0.80 | 0.80 | Lower | More varied output |
| 1.0 | 0.78 | 0.79 | Low | Maximum diversity |

### Chunk Size Impact

| Chunk Size (tokens) | Retrieval Precision | Groundedness | Context Tokens Used | Cost per Query | Recommendation |
|---------------------|-------------------|-------------|--------------------|--------------|-|
| 256 | 0.78 | 0.82 | 1800 | $0.015 | Too granular, loses context |
| **512** | **0.82** | **0.86** | **2800** | **$0.020** | **Default (best balance)** |
| 768 | 0.80 | 0.87 | 3800 | $0.026 | Good for complex docs |
| 1024 | 0.75 | 0.85 | 5200 | $0.032 | Token-expensive |
| 2048 | 0.68 | 0.83 | 8500 | $0.048 | Too coarse, low precision |

### Top-K Results Impact

| Top-K | Precision@K | Recall@K | Groundedness | Tokens Used | Recommendation |
|-------|-----------|---------|-------------|-------------|----------------|
| 3 | 0.85 | 0.45 | 0.84 | 1500 | Misses relevant info |
| 5 | 0.82 | 0.58 | 0.86 | 2500 | Good for simple queries |
| **8** | **0.78** | **0.72** | **0.87** | **3500** | **Default (best balance)** |
| 12 | 0.72 | 0.80 | 0.86 | 5000 | Diminishing returns |
| 20 | 0.65 | 0.85 | 0.84 | 7000 | Too many irrelevant results |

### Max Output Tokens Impact

| Max Tokens | Completeness | Hallucination Risk | Cost | Recommendation |
|------------|-------------|-------------------|------|----------------|
| 500 | 0.65 | 0.05 | Low | Too short for complex |
| 1000 | 0.80 | 0.07 | Medium | Good for simple queries |
| **2000** | **0.90** | **0.09** | **Medium** | **Default** |
| 4000 | 0.92 | 0.12 | High | Complex reasoning only |

---

## Benchmarking Framework

### Automated Evaluation Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                 Automated Eval Pipeline                        │
│                 (Runs daily at 6:00 AM)                       │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Golden Dataset                                            │
│     ├── 200 query-answer pairs                               │
│     ├── Labeled by domain experts                            │
│     ├── Covers: factual, procedural, comparative, analytical │
│     ├── Includes edge cases (ambiguous, multi-doc, outdated) │
│     └── Updated quarterly                                     │
│                                                                │
│  2. Run RAG Pipeline                                          │
│     ├── Process all 200 queries                              │
│     ├── Capture: answer, citations, latency, tokens          │
│     └── Store: Cosmos DB (evaluations container)             │
│                                                                │
│  3. LLM-as-Judge Evaluation                                   │
│     ├── Score: groundedness, relevance, coherence, fluency   │
│     ├── Judge model: GPT-4o (different from generation)      │
│     └── Average across dataset                               │
│                                                                │
│  4. Rule-Based Checks                                         │
│     ├── Citation accuracy (verify citations exist)           │
│     ├── Hallucination detection (claims vs context)          │
│     ├── Format compliance (JSON schema)                      │
│     └── PII leakage check                                    │
│                                                                │
│  5. Metrics Dashboard                                         │
│     ├── Daily trend charts                                   │
│     ├── Per-category breakdown                               │
│     ├── Regression detection                                 │
│     └── Pass/fail gate status                                │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

### Golden Dataset Structure

```json
{
  "id": "eval-001",
  "category": "procedural",
  "difficulty": "medium",
  "query": "What are the steps for AML customer onboarding?",
  "expectedAnswer": "The AML customer onboarding process involves: 1) Identity verification...",
  "expectedCitations": [
    {"docId": "doc-aml-policy-v4", "page": 12}
  ],
  "expectedTopics": ["AML", "onboarding", "customer due diligence"],
  "department": "Compliance",
  "createdBy": "domain-expert@company.com",
  "lastReviewed": "2025-01-15"
}
```

### Human Evaluation Rubrics

| Dimension | Score 5 | Score 3 | Score 1 |
|-----------|---------|---------|---------|
| **Accuracy** | All facts correct, well-sourced | Mostly correct, minor gaps | Major errors or unsupported claims |
| **Completeness** | Addresses all aspects of query | Covers main points, misses details | Incomplete, misses key points |
| **Clarity** | Well-organized, easy to follow | Understandable but could be clearer | Confusing, poorly structured |
| **Usefulness** | Directly actionable for the user | Somewhat helpful, needs follow-up | Not useful, doesn't help |
| **Safety** | No harmful or inappropriate content | Minor concerns | Safety issues present |

### Evaluation Schedule

| Evaluation Type | Frequency | Dataset Size | Evaluator | Trigger |
|----------------|-----------|-------------|-----------|---------|
| **Automated (LLM-judge)** | Daily | 200 queries | GPT-4o | Scheduled |
| **Human spot-check** | Weekly | 20 queries | Domain experts | Scheduled |
| **Full human eval** | Monthly | 100 queries | Domain experts + AI team | Scheduled |
| **Regression eval** | Per deployment | 200 queries | GPT-4o | CI/CD gate |
| **Red team eval** | Quarterly | 50 adversarial queries | Security team | Scheduled |

---

## Model Comparison Matrix

### Generation Model Comparison

| Metric | GPT-4o | GPT-4o-mini | GPT-4 Turbo | GPT-3.5 Turbo |
|--------|--------|-------------|-------------|----------------|
| **Groundedness** | 0.87 | 0.79 | 0.85 | 0.72 |
| **Relevance** | 0.84 | 0.78 | 0.83 | 0.70 |
| **Coherence** | 0.86 | 0.80 | 0.84 | 0.74 |
| **Fluency** | 0.88 | 0.85 | 0.87 | 0.82 |
| **Hallucination Rate** | 0.08 | 0.14 | 0.09 | 0.20 |
| **Latency P50** | 1.2s | 0.6s | 1.8s | 0.4s |
| **Latency P95** | 1.8s | 0.9s | 2.5s | 0.7s |
| **Input Cost (per 1K)** | $0.005 | $0.00015 | $0.01 | $0.0005 |
| **Output Cost (per 1K)** | $0.015 | $0.0006 | $0.03 | $0.0015 |
| **Cost per Query** | $0.012 | $0.001 | $0.024 | $0.002 |
| **Context Window** | 128K | 128K | 128K | 16K |
| **Recommendation** | **Primary (complex)** | **Secondary (simple)** | Legacy fallback | Not recommended |

### Embedding Model Comparison

| Metric | text-embedding-3-large | text-embedding-3-small | text-embedding-ada-002 |
|--------|----------------------|----------------------|----------------------|
| **Dimensions** | 3072 | 1536 | 1536 |
| **MTEB Score** | 64.6 | 62.3 | 61.0 |
| **Retrieval Precision@10** | 0.82 | 0.78 | 0.75 |
| **Retrieval Recall@10** | 0.74 | 0.70 | 0.66 |
| **Cost (per 1K tokens)** | $0.00013 | $0.00002 | $0.0001 |
| **Latency** | 45ms | 30ms | 40ms |
| **Index Size (100K docs)** | 2.3 GB | 1.2 GB | 1.2 GB |
| **Recommendation** | **Selected** | Budget alternative | Legacy |

### Reranker Comparison

| Metric | Azure Semantic Reranker | Cohere Rerank v3 | No Reranker |
|--------|------------------------|-------------------|-------------|
| **NDCG@10 improvement** | +15% | +18% | Baseline |
| **Latency added** | 60–100ms | 80–120ms | 0ms |
| **Cost per query** | $0.003 | $0.002 | $0 |
| **Integration** | Native (Azure AI Search) | External API | N/A |
| **Recommendation** | **Selected** (native) | Alternative | Not recommended |

---

## A/B Testing Framework

### Test Configuration

```yaml
A/B Test Setup:
  Controller: Feature flag service (Azure App Configuration)
  Traffic Split: Percentage-based (configurable)
  User Assignment: Consistent hashing on userId (sticky sessions)
  Minimum Duration: 7 days
  Minimum Sample: 500 queries per group
  Statistical Test: Two-sample t-test (p < 0.05)

  Experiment Types:
    - Model change (GPT-4o version upgrade)
    - Prompt template change
    - Chunking strategy change
    - Search configuration change
    - Post-retrieval processing change
```

### Test Execution Flow

```
┌───────────────────────────────────────────────────────┐
│                 A/B Test Lifecycle                      │
├───────────────────────────────────────────────────────┤
│                                                         │
│  1. Design                                              │
│     ├── Define hypothesis                              │
│     ├── Select metrics (primary + guardrail)           │
│     ├── Calculate sample size                          │
│     └── Set duration                                   │
│                                                         │
│  2. Configure                                           │
│     ├── Create feature flag variants                   │
│     ├── Set traffic split (e.g., 80/20)               │
│     └── Enable metrics collection                     │
│                                                         │
│  3. Run                                                 │
│     ├── Monitor daily metrics                          │
│     ├── Check guardrail metrics (latency, errors)     │
│     └── Auto-stop if guardrail breached               │
│                                                         │
│  4. Analyze                                             │
│     ├── Statistical significance test                  │
│     ├── Effect size calculation                        │
│     ├── Segment analysis (by department, query type)  │
│     └── Cost impact analysis                          │
│                                                         │
│  5. Decide                                              │
│     ├── Roll out to 100% (winner)                     │
│     ├── Iterate (inconclusive)                        │
│     └── Revert (loser or guardrail breach)            │
│                                                         │
└───────────────────────────────────────────────────────┘
```

### Guardrail Metrics (Auto-Stop)

| Guardrail | Threshold | Action |
|-----------|-----------|--------|
| Groundedness | Drops > 5% from control | Auto-stop, alert |
| Hallucination rate | Increases > 50% from control | Auto-stop, alert |
| P95 latency | Increases > 30% from control | Auto-stop, alert |
| Error rate | Increases > 2x from control | Auto-stop, alert |
| Content filter triggers | Increases > 2x from control | Auto-stop, alert |
| User satisfaction | Drops > 10% from control | Alert (manual decision) |

### Example A/B Test

```yaml
Test: Prompt Template v2.2 vs v2.1
  Hypothesis: "New prompt with explicit reasoning steps improves groundedness by 3%"
  Primary Metric: Groundedness
  Guardrail Metrics: Latency, Error Rate, Hallucination Rate
  Traffic: 80% control (v2.1), 20% treatment (v2.2)
  Duration: 14 days
  Sample Size: 1000 per group (min)

  Results:
    Control (v2.1):
      Groundedness: 0.86 (±0.02)
      Latency P50: 1.8s
      Cost/query: $0.012

    Treatment (v2.2):
      Groundedness: 0.89 (±0.02)
      Latency P50: 2.0s (+11%)
      Cost/query: $0.014 (+17%)

    Statistical Significance: p = 0.003 (significant)
    Decision: Roll out v2.2 (groundedness improvement > latency cost)
```

---

## Release Gate Criteria

### Deployment Gate Checks

```
┌─────────────────────────────────────────────────────────┐
│              Release Gate Evaluation                      │
│                                                           │
│  ┌─────────────────┐                                     │
│  │ Quality Gates   │  ALL must pass                      │
│  ├─────────────────┤                                     │
│  │ Groundedness    │  ≥ 0.80 (block < 0.70)             │
│  │ Relevance       │  ≥ 0.70 (block < 0.60)             │
│  │ Hallucination   │  ≤ 0.10 (block > 0.15)             │
│  │ Citation Acc.   │  ≥ 0.90 (block < 0.80)             │
│  └─────────────────┘                                     │
│                                                           │
│  ┌─────────────────┐                                     │
│  │ Performance Gates│  ALL must pass                     │
│  ├─────────────────┤                                     │
│  │ Latency P95     │  < 5s (block > 8s)                 │
│  │ Error Rate      │  < 2% (block > 5%)                 │
│  │ Throughput       │  ≥ 50 QPS (block < 30 QPS)        │
│  └─────────────────┘                                     │
│                                                           │
│  ┌─────────────────┐                                     │
│  │ Safety Gates    │  ALL must pass                      │
│  ├─────────────────┤                                     │
│  │ PII Leakage     │  0% in test suite                  │
│  │ Injection Test  │  0% bypass in red team tests       │
│  │ Content Filter  │  < 2% false negatives              │
│  └─────────────────┘                                     │
│                                                           │
│  ┌─────────────────┐                                     │
│  │ Regression Gates│  No degradation allowed             │
│  ├─────────────────┤                                     │
│  │ vs. Previous    │  All metrics ≥ previous - 2%       │
│  │ vs. Baseline    │  All metrics ≥ baseline             │
│  └─────────────────┘                                     │
│                                                           │
│  Result: PASS / FAIL / WARN                              │
│  PASS → Auto-deploy to staging                           │
│  WARN → Manual review required                           │
│  FAIL → Block deployment, alert team                     │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Gate Implementation

```python
def evaluate_release_gate(eval_results: EvalResults) -> GateResult:
    blockers = []
    warnings = []

    # Quality gates
    if eval_results.groundedness < 0.70:
        blockers.append(f"Groundedness {eval_results.groundedness:.2f} < 0.70")
    elif eval_results.groundedness < 0.80:
        warnings.append(f"Groundedness {eval_results.groundedness:.2f} < 0.80")

    if eval_results.hallucination_rate > 0.15:
        blockers.append(f"Hallucination {eval_results.hallucination_rate:.2f} > 0.15")
    elif eval_results.hallucination_rate > 0.10:
        warnings.append(f"Hallucination {eval_results.hallucination_rate:.2f} > 0.10")

    if eval_results.citation_accuracy < 0.80:
        blockers.append(f"Citation accuracy {eval_results.citation_accuracy:.2f} < 0.80")

    # Performance gates
    if eval_results.latency_p95 > 8.0:
        blockers.append(f"P95 latency {eval_results.latency_p95:.1f}s > 8s")

    if eval_results.error_rate > 0.05:
        blockers.append(f"Error rate {eval_results.error_rate:.2%} > 5%")

    # Safety gates
    if eval_results.pii_leakage > 0:
        blockers.append(f"PII leakage detected: {eval_results.pii_leakage} instances")

    if blockers:
        return GateResult(status="FAIL", blockers=blockers, warnings=warnings)
    elif warnings:
        return GateResult(status="WARN", blockers=[], warnings=warnings)
    else:
        return GateResult(status="PASS", blockers=[], warnings=[])
```

### Release Approval Matrix

| Change Type | Auto-Deploy | Manual Approval | Full Review |
|-------------|-------------|-----------------|-------------|
| Config change (temperature, top-K) | If gates pass | — | — |
| Prompt template change | — | Team lead | — |
| Model version upgrade | — | — | AI Ethics Committee |
| New model deployment | — | — | AI Governance Board |
| Search config change | If gates pass | — | — |
| Chunking strategy change | — | Team lead | — |
| Security policy change | — | — | Security Team + CISO |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | AI Platform Team |
| Review | Quarterly |
| Related | [Responsible AI](RESPONSIBLE-AI.md), [AI Governance](AI-GOVERNANCE.md) |
