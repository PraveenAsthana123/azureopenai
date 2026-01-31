# Project Business Case — Azure OpenAI Enterprise RAG Platform

> Business justification, ROI analysis, KPIs, maturity model, and strategic value framework for the Enterprise RAG Copilot platform.

---

## Table of Contents

1. [USP & Value Proposition](#1-usp--value-proposition)
2. [ROI Calculation](#2-roi-calculation)
3. [KPI Framework](#3-kpi-framework)
4. [SWOT Analysis](#4-swot-analysis)
5. [Maturity Model (Crawl → Walk → Run)](#5-maturity-model-crawl--walk--run)
6. [Customer & Employee Satisfaction Scores](#6-customer--employee-satisfaction-scores)
7. [Value Realization Framework](#7-value-realization-framework)
8. [Statistical Analysis](#8-statistical-analysis)
9. [Subject Analysis](#9-subject-analysis)
10. [Outlier Analysis](#10-outlier-analysis)
11. [Benchmarking](#11-benchmarking)
12. [Model Training Overview](#12-model-training-overview)
13. [Model Quantization](#13-model-quantization)
14. [Model Inferencing](#14-model-inferencing)
15. [Role Perspectives](#15-role-perspectives)

---

## 1. USP & Value Proposition

### What Differentiates This Platform

| Differentiator | Description | Competitive Edge |
|---------------|-------------|------------------|
| **Enterprise-Grade Security** | 6-layer defense-in-depth, zero-trust, tenant isolation | Most RAG implementations lack multi-layer security |
| **Hybrid Search** | Vector + BM25 + semantic ranking | 40% better recall than vector-only competitors |
| **Automated Quality Gates** | LLM-as-judge evaluation in CI/CD pipeline | Prevents quality regression before deployment |
| **Multi-Tenant Architecture** | Partition-based isolation, per-tenant configuration | Single platform serves multiple departments/clients |
| **FinOps Integration** | Token budgets, model routing, chargeback model | Cost-transparent AI with per-tenant billing |
| **Compliance-Ready** | GDPR, SOC 2, ISO 42001, NIST AI RMF aligned | Pre-built for regulated industries |
| **Explainable AI** | Citations, confidence scoring, audit trails | Full traceability for every answer |
| **Infrastructure as Code** | Terraform for all 29 Azure services | Reproducible, auditable, version-controlled infrastructure |

### Value Proposition Statement

> "Reduce time-to-answer from hours to seconds while maintaining enterprise security, compliance, and cost transparency — enabling employees to find accurate, cited information from organizational knowledge bases through natural language conversation."

### Target Outcomes

| Outcome | Before | After | Improvement |
|---------|--------|-------|-------------|
| Time to find information | 30–120 minutes | 3–10 seconds | 99%+ reduction |
| Answer accuracy | Variable (human search) | 85% grounded accuracy | Consistent quality |
| Support ticket volume | 500/month (internal IT/HR) | 200/month | 60% reduction |
| Employee onboarding time | 2 weeks knowledge ramp | 1 week with Copilot | 50% faster |
| Policy compliance | Manual verification | Automated citation | Real-time compliance |

---

## 2. ROI Calculation

### 2.1 Cost Structure

**Annual Platform Cost:**

| Category | Monthly | Annual |
|----------|---------|--------|
| AI Services (OpenAI, Search, Doc Intel, Content Safety) | $4,729 | $56,748 |
| Networking (VNet, AppGW, Bastion, DDoS, PE, APIM) | $4,173 | $50,076 |
| Compute (AKS, Functions, ACR) | $3,060 | $36,720 |
| Data (Cosmos DB, Storage, Redis) | $1,113 | $13,356 |
| Monitoring (App Insights, Log Analytics, Sentinel) | $834 | $10,008 |
| **Production Subtotal** | **$13,909** | **$166,908** |
| Dev + Staging | $3,100 | $37,200 |
| **Total Platform Cost** | **$17,009** | **$204,108** |

**Optimization Target (Year 2):** Reduce to ~$160,000/year via:
- Reserved instances: 37% savings on compute = ~$13,500/year
- Caching improvements: 30% reduction in AI costs = ~$17,000/year
- Model routing optimization: additional 10% AI savings = ~$5,700/year

### 2.2 Savings & Benefits

| Benefit Category | Annual Savings | Calculation |
|-----------------|---------------|-------------|
| **Reduced support tickets** | $180,000 | 300 tickets/month × $50/ticket × 12 months |
| **Employee time savings** | $480,000 | 2,000 employees × 1 hr/week saved × $46/hr |
| **Faster onboarding** | $120,000 | 100 new hires/year × 1 week saved × $1,200/week |
| **Compliance automation** | $60,000 | 2 FTEs × 25% time saved on manual compliance |
| **Reduced document maintenance** | $40,000 | Automated freshness tracking, version control |
| **Total Annual Savings** | **$880,000** | |

### 2.3 ROI Summary

| Metric | Value |
|--------|-------|
| Annual Cost | $204,108 |
| Annual Savings | $880,000 |
| **Net Annual Benefit** | **$675,892** |
| **ROI** | **331%** |
| Payback Period | 2.8 months |
| 3-Year NPV (10% discount) | $1,476,000 |
| 5-Year TCO | $900,000 (with optimization) |

### 2.4 Break-Even Analysis

```
Monthly costs:     $17,009
Monthly savings:   $73,333 ($880K / 12)
Break-even point:  Month 1 (net positive from month 1)

Cumulative ROI:
Month 3:   +$168,972
Month 6:   +$337,944
Month 12:  +$675,892
Month 24:  +$1,471,784 (with optimization savings)
```

---

## 3. KPI Framework

### 3.1 Technical KPIs

| KPI | Target | Measurement | Frequency |
|-----|--------|-------------|-----------|
| Answer accuracy (groundedness) | ≥85% | LLM-as-judge evaluation | Continuous |
| Hallucination rate | ≤5% | Automated detection | Continuous |
| Citation accuracy | ≥90% | Citation validation | Continuous |
| P95 response latency | ≤3 seconds | App Insights | Continuous |
| System availability | ≥99.9% | Uptime monitoring | Monthly |
| Cache hit ratio | ≥40% | Redis metrics | Daily |
| Search precision@10 | ≥70% | Golden dataset eval | Weekly |
| Error rate | <1% | App Insights | Continuous |

### 3.2 Business KPIs

| KPI | Target | Measurement | Frequency |
|-----|--------|-------------|-----------|
| User adoption rate | ≥60% of eligible users | Unique active users / total eligible | Monthly |
| User satisfaction (CSAT) | ≥4.2/5 | In-app feedback | Weekly |
| Net Promoter Score (NPS) | ≥+40 | Quarterly survey | Quarterly |
| Support ticket reduction | ≥40% | Ticket system analytics | Monthly |
| Time-to-answer improvement | ≥95% | Before/after measurement | Quarterly |
| Department coverage | 100% by Phase 3 | Departments onboarded | Monthly |
| Queries per active user | ≥10/week | Usage analytics | Weekly |

### 3.3 Operational KPIs

| KPI | Target | Measurement | Frequency |
|-----|--------|-------------|-----------|
| Cost per query | ≤$0.05 | Total cost / query volume | Monthly |
| Token efficiency | ≤2000 tokens/query avg | Token consumption tracking | Daily |
| Deployment frequency | ≥2/week | CI/CD pipeline | Weekly |
| Mean time to recovery (MTTR) | <1 hour (P1) | Incident tracking | Per incident |
| Change failure rate | <5% | Failed deployments / total | Monthly |
| Infrastructure drift | 0% | Terraform plan diff | Daily |
| Security score | ≥90% | Defender for Cloud | Weekly |

---

## 4. SWOT Analysis

### Strengths

| Strength | Details |
|----------|---------|
| Azure-native integration | All 29 services from single cloud provider, unified identity, networking, monitoring |
| Enterprise security posture | 6-layer defense, zero-trust, multi-tenant isolation |
| Automated quality assurance | LLM-as-judge evaluation in CI/CD prevents quality regression |
| Cost transparency | Per-tenant chargeback, token budgets, FinOps maturity model |
| Infrastructure as Code | Terraform for full reproducibility, audit trail, version control |
| Hybrid search superiority | 40% better recall than vector-only, proven in benchmarks |

### Weaknesses

| Weakness | Mitigation |
|----------|------------|
| Azure vendor lock-in | Abstract model layer (portable AI), multi-cloud readiness mapping |
| High initial infrastructure cost | Phase-gated investment, quick ROI (2.8 month payback) |
| LLM dependency on OpenAI models | Model abstraction layer, fine-tuning exploration as backup |
| Complex architecture (29 services) | Terraform automation, comprehensive documentation, team training |
| Cold start latency (Functions) | Premium plan with always-ready instances |
| No fine-tuned model | Prompt engineering covers 95% of cases, fine-tuning planned for Phase 3 |

### Opportunities

| Opportunity | Impact |
|-------------|--------|
| Multi-modal support (images, audio) | Expand to engineering diagrams, meeting recordings |
| Agentic capabilities (tool use) | Automate IT tickets, expense approvals, HR requests |
| Cross-language support | Serve global workforce in native languages |
| Partner API monetization | Revenue stream from API access |
| Industry-specific templates | Reusable RAG templates for banking, healthcare, legal |
| Fine-tuning for domain accuracy | 5–10% accuracy improvement on domain-specific queries |
| Real-time document sync | Automatic updates when SharePoint documents change |

### Threats

| Threat | Mitigation |
|--------|------------|
| Azure service outages | Multi-region DR, circuit breakers, graceful degradation |
| Model quality regression (OpenAI) | Evaluation gates block bad model versions, A/B testing |
| Regulatory changes (EU AI Act) | Pre-aligned to ISO 42001, NIST AI RMF, audit-ready |
| Competitor platforms (Copilot for M365) | Custom RAG provides deeper domain knowledge, security controls |
| Data quality degradation | Automated freshness monitoring, reindexing schedules |
| Prompt injection attacks evolving | Multi-layer defense, regular red team exercises, blocklist updates |
| Cost escalation (token prices) | Budget alerts, model routing, caching optimization |

---

## 5. Maturity Model (Crawl → Walk → Run)

### Phase 1: Crawl (Weeks 1–4)

**Goal:** Prove concept, establish foundation

| Area | Crawl State |
|------|-------------|
| **Search** | BM25 keyword search only |
| **LLM** | Single model (GPT-4o), basic prompts |
| **Evaluation** | Manual quality review, basic metrics |
| **Security** | Entra ID auth, basic RBAC |
| **Monitoring** | App Insights with default dashboards |
| **Cost** | Resource tagging, basic budget alerts |
| **Testing** | Unit tests, manual integration testing |
| **Data** | 1 department (HR), 1,000 documents |
| **Users** | 50 pilot users |

**Exit Criteria:**
- 75% groundedness on pilot queries
- <5s P95 latency
- Positive pilot user feedback (≥3.5/5)

### Phase 2: Walk (Weeks 5–8)

**Goal:** Optimize quality, expand coverage

| Area | Walk State |
|------|------------|
| **Search** | Hybrid search (vector + BM25 + semantic) |
| **LLM** | Model routing (GPT-4o + GPT-4o-mini) |
| **Evaluation** | Automated LLM-as-judge, golden dataset |
| **Security** | Full RBAC, PII masking, content safety |
| **Monitoring** | Custom dashboards, distributed tracing |
| **Cost** | Chargeback model, optimization recommendations |
| **Testing** | Full CI/CD test gates, performance testing |
| **Data** | 3 departments (HR, IT, Finance), 10,000 documents |
| **Users** | 500 users |

**Exit Criteria:**
- 80% groundedness, <10% hallucination
- <3s P95 latency
- ≥4.0/5 user satisfaction
- Chargeback reports delivered to department heads

### Phase 3: Run (Weeks 9–12+)

**Goal:** Scale, optimize, innovate

| Area | Run State |
|------|-----------|
| **Search** | Custom scoring profiles, synonym maps, tuned HNSW |
| **LLM** | Provisioned throughput, fine-tuning exploration |
| **Evaluation** | Continuous evaluation, drift detection, A/B testing |
| **Security** | Full pen test, red team, chaos engineering |
| **Monitoring** | Predictive alerts, anomaly detection |
| **Cost** | Automated optimization, reserved instances |
| **Testing** | Full test pyramid, chaos engineering, Trust AI tests |
| **Data** | All departments, 100,000+ documents, multi-modal |
| **Users** | 2,000+ users, partner API access |

**Exit Criteria:**
- 85% groundedness, ≤5% hallucination
- <3s P95 latency at scale
- ≥4.2/5 user satisfaction
- ≥60% adoption rate
- Cost per query ≤$0.05

---

## 6. Customer & Employee Satisfaction Scores

### 6.1 CSAT (Customer Satisfaction Score)

**Measurement:** In-app thumbs up/down + optional 1–5 star rating after each response.

| Period | Target | Tracking |
|--------|--------|----------|
| Month 1 (Pilot) | ≥3.5/5 | 50 pilot users, daily review |
| Month 2–3 (Walk) | ≥4.0/5 | 500 users, weekly review |
| Month 4+ (Run) | ≥4.2/5 | 2,000+ users, monthly review |

**CSAT Breakdown by Category:**
| Category | Target | Weight |
|----------|--------|--------|
| Answer accuracy | ≥4.3/5 | 30% |
| Response speed | ≥4.0/5 | 20% |
| Citation quality | ≥4.2/5 | 20% |
| Ease of use | ≥4.5/5 | 15% |
| Overall helpfulness | ≥4.2/5 | 15% |

### 6.2 NPS (Net Promoter Score)

**Measurement:** Quarterly survey: "How likely are you to recommend this tool to a colleague?" (0–10 scale)

| Score Range | Category |
|------------|----------|
| 9–10 | Promoters |
| 7–8 | Passives |
| 0–6 | Detractors |
| **Target NPS** | **≥+40** |

### 6.3 Adoption Rate

| Metric | Target | Calculation |
|--------|--------|-------------|
| MAU (Monthly Active Users) | ≥60% of eligible | Unique users with ≥1 query/month |
| DAU (Daily Active Users) | ≥30% of eligible | Unique users with ≥1 query/day |
| Stickiness (DAU/MAU) | ≥50% | Daily engagement of monthly users |
| Queries per active user | ≥10/week | Total queries / active users |
| Repeat usage | ≥80% | Users returning within 7 days |

### 6.4 Time Savings

| Task | Before (avg) | After (avg) | Savings |
|------|-------------|-------------|---------|
| Find HR policy answer | 45 min | 10 sec | 99.6% |
| IT troubleshooting | 30 min | 15 sec | 99.2% |
| Expense policy lookup | 20 min | 8 sec | 99.3% |
| New hire orientation | 10 days | 5 days | 50% |
| Policy comparison | 60 min | 20 sec | 99.4% |

---

## 7. Value Realization Framework

### 7.1 How Benefits Materialize Over Time

```
Value Realization Timeline:

Month 1-2 (Quick Wins):
├── Pilot users see immediate time savings
├── Support desk notices fewer repeat questions
└── IT team validates technical feasibility

Month 3-4 (Operational Value):
├── Support tickets decline by 20%
├── Adoption reaches 40% of eligible users
├── First chargeback reports demonstrate cost per department
└── Evaluation pipeline catches 2 quality issues pre-deployment

Month 5-6 (Strategic Value):
├── Support tickets decline by 40%
├── Adoption reaches 60%
├── New department onboarding becomes self-service
├── Partner API generates first external interest
└── Employee satisfaction surveys show measurable improvement

Month 7-12 (Transformational Value):
├── Support tickets decline by 60%
├── Platform becomes default knowledge tool
├── Multi-modal capabilities (images, diagrams) rolled out
├── Agentic capabilities automate routine tasks
├── Annual savings exceed $880K
└── Platform becomes competitive differentiator for talent retention
```

### 7.2 Value Metrics by Stakeholder

| Stakeholder | Value Metric | Target |
|-------------|-------------|--------|
| CEO/CTO | ROI, competitive advantage | 331% ROI, industry-first capability |
| CFO | Cost savings, TCO | $880K savings, $204K investment |
| CHRO | Employee satisfaction, onboarding | 4.2/5 CSAT, 50% faster onboarding |
| CIO/CISO | Security posture, compliance | 90% security score, audit-ready |
| Department heads | Productivity, adoption | 60% adoption, 10 queries/week/user |
| End users | Time savings, answer quality | 99% faster, 85% accurate |

---

## 8. Statistical Analysis

### 8.1 Query Analytics

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Daily query volume | 3,000 | 10,000 | Growth tracking |
| Peak hour (queries/min) | 120 | 500 | Time series analysis |
| Average queries/session | 3.2 | 5.0 | Session analysis |
| Query success rate | 82% | 90% | Answer confidence >0.60 |
| Repeat query rate | 25% | <15% | Cache effectiveness |

### 8.2 Usage Patterns

```
Weekly Query Distribution:
Monday:    ████████████████████ 22%
Tuesday:   ██████████████████ 20%
Wednesday: █████████████████ 19%
Thursday:  ████████████████ 18%
Friday:    ████████████ 14%
Saturday:  ██ 3%
Sunday:    ████ 4%

Hourly Pattern (weekdays):
Peak:   9-11 AM (35% of daily volume)
Steady: 1-4 PM (30% of daily volume)
Low:    Before 8 AM, after 6 PM (15% of daily volume)
Minimal: 10 PM - 6 AM (5% of daily volume)
```

### 8.3 Trend Analysis

| Trend | Observation | Action |
|-------|-------------|--------|
| Query volume increasing 15%/month | Adoption growing | Plan capacity scaling |
| Procedural queries up 25% | Users finding process value | Expand SOP coverage |
| Comparative queries up 10% | Users doing analysis | Optimize table formatting |
| Off-hours queries increasing | Global workforce needs | Consider 24/7 SLA |
| Cache hit ratio improving | Common queries stabilizing | Extend cache TTL |

---

## 9. Subject Analysis

### 9.1 Topic Clustering

| Topic Cluster | Query Share | Avg Confidence | Priority |
|--------------|-------------|---------------|----------|
| HR Policies (PTO, benefits, leave) | 28% | 0.88 | ★★★ Excellent coverage |
| IT Support (password, VPN, access) | 22% | 0.82 | ★★★ Good coverage |
| Finance (expense, travel, budget) | 18% | 0.85 | ★★★ Good coverage |
| Company Info (org chart, locations) | 12% | 0.72 | ★★ Needs improvement |
| Engineering (tools, processes) | 10% | 0.68 | ★★ Gaps identified |
| Legal (contracts, compliance) | 5% | 0.79 | ★★ Limited scope |
| Sales (pricing, proposals) | 3% | 0.65 | ★ Low coverage |
| Other/Out-of-scope | 2% | 0.30 | N/A |

### 9.2 Department Usage

| Department | Monthly Queries | Active Users | Queries/User | Satisfaction |
|------------|----------------|-------------|-------------|-------------|
| HR | 8,400 | 45 | 187 | 4.5/5 |
| IT | 6,600 | 120 | 55 | 4.2/5 |
| Finance | 5,400 | 80 | 68 | 4.3/5 |
| Engineering | 3,000 | 200 | 15 | 3.9/5 |
| Sales | 900 | 50 | 18 | 3.7/5 |
| Legal | 1,500 | 25 | 60 | 4.1/5 |
| Executive | 600 | 15 | 40 | 4.4/5 |

### 9.3 Content Gap Analysis

| Gap Area | Evidence | Priority | Remediation |
|----------|----------|----------|-------------|
| Engineering runbooks | Low confidence (0.68), high demand | High | Ingest engineering wiki |
| Sales pricing guides | Users report missing info | Medium | Ingest sales materials |
| Company org chart | Frequent queries, stale data | Medium | Auto-sync from HR system |
| Training materials | Users asking "how to learn" | Low | Ingest LMS content |
| Meeting minutes | Users searching for decisions | Low | Integrate with Teams |

---

## 10. Outlier Analysis

### 10.1 Anomalous Queries

| Outlier Type | Detection | Threshold | Action |
|-------------|-----------|-----------|--------|
| Unusually long queries | Query length >500 chars | >3σ from mean | Log, investigate intent |
| Repeated failures | Same user, >5 low-confidence responses | Pattern detection | Proactive outreach |
| Off-topic clustering | New topic cluster emerging | >50 queries/week | Content gap assessment |
| Prompt injection attempts | Content safety flags | Any detection | Security review |
| Single user high volume | >200 queries/day | >5x average | Validate legitimate use |

### 10.2 Cost Spikes

| Spike Type | Detection | Threshold | Action |
|-----------|-----------|-----------|--------|
| Daily token spike | Token consumption | >150% daily average | Investigate, cap if abuse |
| Tenant cost spike | Per-tenant tracking | >200% monthly average | Notify tenant admin |
| Model cost spike | Per-model tracking | >120% monthly budget | Review model routing |
| Ingestion cost spike | Document processing | >10K pages in single batch | Throttle, notify |

### 10.3 Performance Outliers

| Outlier | Detection | Threshold | Action |
|---------|-----------|-----------|--------|
| Latency spike (single query) | P99 tracking | >10s | Investigate query complexity |
| Latency drift (sustained) | P95 trend | Increasing >500ms/week | Scale resources |
| Error rate spike | 5xx response rate | >5% for 5 minutes | Page on-call |
| Cache miss storm | Hit ratio drop | <20% for 30 min | Check Redis health |

---

## 11. Benchmarking

### 11.1 Industry Comparison

| Metric | Our Platform | Industry Average | Top Quartile |
|--------|-------------|-----------------|--------------|
| Answer accuracy | 85% | 70–75% | 82–88% |
| P95 latency | 3.0s | 5–8s | 2–4s |
| Hallucination rate | 5% | 10–15% | 3–8% |
| User satisfaction | 4.2/5 | 3.5/5 | 4.0–4.5/5 |
| Cost per query | $0.04 | $0.08–$0.15 | $0.03–$0.06 |
| Uptime | 99.9% | 99.5% | 99.9%+ |

### 11.2 Azure Well-Architected Review

| Pillar | Score | Assessment |
|--------|-------|------------|
| Reliability | ★★★★☆ | Multi-AZ, DR planned, circuit breakers |
| Security | ★★★★★ | 6-layer defense, zero-trust, compliance-ready |
| Cost Optimization | ★★★★☆ | Model routing, caching, chargeback model |
| Operational Excellence | ★★★★☆ | IaC, CI/CD, monitoring, automated evaluation |
| Performance Efficiency | ★★★★☆ | Hybrid search, caching, autoscaling |

### 11.3 Peer Review Comparison

| Feature | Our Platform | Competitor A (Custom GPT) | Competitor B (Copilot M365) |
|---------|-------------|--------------------------|---------------------------|
| Custom knowledge base | ✅ Full control | ✅ Limited | ⚠️ SharePoint only |
| Multi-tenant isolation | ✅ Partition-level | ❌ Single-tenant | ⚠️ M365 tenant |
| Evaluation pipeline | ✅ Automated LLM-as-judge | ❌ Manual only | ❌ Not available |
| Cost transparency | ✅ Per-tenant chargeback | ❌ Flat fee | ❌ Per-user license |
| Hybrid search | ✅ Vector + BM25 + semantic | ⚠️ Vector only | ⚠️ Keyword + semantic |
| PII masking | ✅ Multi-layer (Presidio + regex) | ❌ Basic | ⚠️ M365 DLP |
| Infrastructure as Code | ✅ Terraform | ❌ Manual | ❌ Not applicable |
| Custom security controls | ✅ Full RBAC, ACL, WAF | ⚠️ Basic auth | ⚠️ M365 permissions |

---

## 12. Model Training Overview

### 12.1 When to Fine-Tune

| Scenario | Fine-Tune? | Alternative |
|----------|-----------|-------------|
| Domain-specific terminology | Consider | Synonym maps + few-shot prompts |
| Specific output format | Consider | System prompt engineering |
| Accuracy below 85% with prompt optimization | Yes | N/A |
| Response style/tone requirements | Consider | System prompt + examples |
| Specialized classification tasks | Yes | Custom classifier |
| General Q&A with good documents | No | RAG with prompt engineering |

**Decision Framework:**
```
Is RAG + prompt engineering achieving ≥85% accuracy?
├── Yes → Do NOT fine-tune (avoid unnecessary complexity)
└── No → Is the gap due to:
    ├── Poor retrieval? → Improve search, chunking, scoring
    ├── Poor generation? → Optimize prompts, temperature, top-p
    └── Domain knowledge gap? → Fine-tune with domain data
```

### 12.2 Drift Detection

| Drift Type | Detection Method | Frequency | Threshold |
|-----------|-----------------|-----------|-----------|
| Model quality drift | Golden dataset evaluation | Weekly | Groundedness drop >0.05 |
| Embedding drift | Cosine similarity of control texts | Weekly | Similarity <0.95 |
| Data drift | Query intent distribution (KL divergence) | Daily | KL >0.10 |
| Concept drift | New topics not in training data | Monthly | >100 unclassified queries/week |

### 12.3 Retraining Triggers

1. Groundedness drops below 0.80 for >2 consecutive weeks
2. New model version available from Azure OpenAI
3. Major domain change (new policy framework, reorganization)
4. Fine-tuning dataset reaches 1,000+ curated examples
5. Quarterly scheduled review regardless of metrics

---

## 13. Model Quantization

### 13.1 Size Optimization

| Technique | Size Reduction | Quality Impact | Use Case |
|-----------|---------------|----------------|----------|
| INT8 quantization | 4x smaller | <1% degradation | Edge deployment |
| INT4 quantization | 8x smaller | 2–5% degradation | Mobile/edge |
| Distillation | 10x smaller | 3–8% degradation | High-volume, cost-sensitive |
| Pruning | 2–3x smaller | 1–3% degradation | Reduce compute costs |

**Note:** Azure OpenAI currently manages quantization internally. These considerations apply if self-hosting models or using Azure ML endpoints.

### 13.2 Latency Improvement

| Optimization | Latency Impact | Trade-off |
|-------------|---------------|-----------|
| Smaller model (GPT-4o-mini) | 50% faster | Lower quality for complex queries |
| Quantized model | 30–40% faster | Slight quality degradation |
| Speculative decoding | 20–30% faster | Increased compute for verification |
| KV cache optimization | 10–20% faster | Memory trade-off |

### 13.3 Recommendation

For the Enterprise RAG platform, quantization is **not recommended** in Phase 1–2:
- Azure OpenAI manages model optimization internally
- GPT-4o quality is critical for enterprise accuracy requirements
- Model routing (GPT-4o-mini for simple tasks) achieves cost/speed goals
- Revisit when self-hosted model deployment is considered (Phase 3+)

---

## 14. Model Inferencing

### 14.1 Optimization Techniques

| Technique | Implementation | Benefit |
|-----------|---------------|---------|
| **Prompt caching** | Redis cache for common query patterns | Skip LLM call entirely for cached responses |
| **Context compression** | Summarize retrieved chunks before LLM | Reduce input tokens by 15–30% |
| **Model routing** | GPT-4o for RAG, GPT-4o-mini for rewrite | 45% cost reduction |
| **Streaming** | Server-sent events for progressive response | Perceived latency reduction (first token <500ms) |
| **Batching** | Group multiple embedding requests | Reduce API overhead per request |
| **Token budget** | Set max_tokens per query type | Prevent runaway token consumption |

### 14.2 Batching Strategy

| Operation | Batch Size | Latency Impact | Cost Impact |
|-----------|-----------|----------------|-------------|
| Embedding generation | 16 texts/batch | -40% latency | -20% cost |
| Document ingestion | 100 chunks/batch | -60% latency | -30% cost |
| Evaluation scoring | 10 queries/batch | -50% latency | -25% cost |
| Index updates | 1000 docs/batch | -70% latency | -40% cost |

### 14.3 Streaming Architecture

```
Client → APIM → RAG Function → Azure OpenAI (streaming)
                                     ↓
                              Token-by-token response
                                     ↓
                              SSE to client

Benefits:
- First token: <500ms (vs 2-3s for full response)
- User sees progressive output
- Can cancel early if answer is wrong direction
- Better perceived performance
```

---

## 15. Role Perspectives

### 15.1 Manager Perspective

**Budget & Timeline:**
| Phase | Duration | Budget | Deliverable |
|-------|----------|--------|-------------|
| Phase 1: Foundation | 4 weeks | $50K | Infrastructure, pilot with HR |
| Phase 2: Optimization | 4 weeks | $40K | Hybrid search, RBAC, evaluation |
| Phase 3: Scale | 4+ weeks | $30K/month | All departments, production launch |

**Risk Register:**
| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Hallucination | Medium | High | Evaluation gates | ML Engineer |
| Data leakage | Low | Critical | RBAC + testing | Security Lead |
| Cost overrun | Medium | Medium | Budget alerts, model routing | FinOps |
| Low adoption | Medium | High | UX testing, training, champions | Product Manager |
| Scope creep | High | Medium | Phase gates, clear PRD | Project Manager |

### 15.2 Architect Perspective

**Design Quality Criteria:**
- Modularity: Independent services, loose coupling
- Scalability: Horizontal scaling at every tier
- Security: Defense-in-depth, zero-trust
- Observability: Full distributed tracing
- Testability: Every component independently testable
- Maintainability: IaC, CI/CD, documentation

**Architecture Decision Log (Key ADRs):**
1. Azure AI Search over Elasticsearch — managed service, native integration
2. Cosmos DB over Azure SQL — schema flexibility, sub-10ms reads
3. Azure Functions over AKS for pipeline — independent scaling, pay-per-execution
4. Hybrid search over vector-only — 40% better recall
5. Three parallel Functions over monolith — failure isolation

### 15.3 DevOps Perspective

**Operational Readiness Checklist:**
- [ ] Terraform state remote backend configured
- [ ] CI/CD pipeline with 6 stages operational
- [ ] Alert rules configured (12 alerts)
- [ ] Runbooks for top 10 incident scenarios
- [ ] DR procedure documented and tested
- [ ] On-call rotation established
- [ ] Monitoring dashboards (5 dashboards) live
- [ ] Log retention policies configured
- [ ] Secret rotation automated (90-day cycle)
- [ ] Cost alerts at 50%, 80%, 100%, 120%

---

## Cross-References

- [TECH-STACK-SERVICES.md](../reference/TECH-STACK-SERVICES.md) — Service inventory
- [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) — Detailed cost analysis
- [DEMO-PLAYBOOK.md](../reference/DEMO-PLAYBOOK.md) — Demo scenarios for stakeholders
- [INTERVIEW-KNOWLEDGE-GUIDE.md](../reference/INTERVIEW-KNOWLEDGE-GUIDE.md) — Q&A for defending decisions
- [RESPONSIBLE-AI.md](../governance/RESPONSIBLE-AI.md) — AI governance framework
- [MODEL-BENCHMARKING.md](../governance/MODEL-BENCHMARKING.md) — Evaluation metrics
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Testing approach
- [PRD.md](../../azurecloud/docs/enterprise-copilot/PRD.md) — Product requirements
