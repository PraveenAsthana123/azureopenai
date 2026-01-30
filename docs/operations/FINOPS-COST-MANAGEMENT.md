# FinOps & Cost Management

> **Cost Optimization, Budget Management, and Financial Operations for Azure OpenAI Enterprise Platform**

---

## Table of Contents

1. [Cost Calculation per Azure Service](#cost-calculation-per-azure-service)
2. [Monthly Cost Estimates by Environment](#monthly-cost-estimates-by-environment)
3. [Cost Optimization Recommendations](#cost-optimization-recommendations)
4. [Dos and Don'ts](#dos-and-donts)
5. [Budget Alerts and Thresholds](#budget-alerts-and-thresholds)
6. [Cost Allocation Tags and Chargeback](#cost-allocation-tags-and-chargeback)
7. [Token Usage Optimization](#token-usage-optimization)
8. [Scaling Cost Impact Analysis](#scaling-cost-impact-analysis)

---

## Cost Calculation per Azure Service

### AI Services

| Service | SKU | Billing Unit | Unit Cost | Dev Estimate | Staging Estimate | Prod Estimate |
|---------|-----|-------------|-----------|-------------|-----------------|---------------|
| **Azure OpenAI — GPT-4o** | S0 | Per 1K tokens (input) | $0.005 | $50/mo | $150/mo | $1,500/mo |
| **Azure OpenAI — GPT-4o** | S0 | Per 1K tokens (output) | $0.015 | $75/mo | $225/mo | $2,250/mo |
| **Azure OpenAI — GPT-4o-mini** | S0 | Per 1K tokens (input) | $0.00015 | $2/mo | $5/mo | $30/mo |
| **Azure OpenAI — GPT-4o-mini** | S0 | Per 1K tokens (output) | $0.0006 | $3/mo | $8/mo | $60/mo |
| **Azure OpenAI — Embeddings** | S0 | Per 1K tokens | $0.00013 | $5/mo | $15/mo | $50/mo |
| **Azure AI Search** | Basic / Standard S1 | Per search unit/hour | $0.34/hr (Basic) / $0.34/hr (S1) | $75/mo | $250/mo | $750/mo |
| **Document Intelligence** | S0 | Per page processed | $0.01/page | $10/mo | $30/mo | $100/mo |
| **Content Safety** | S0 | Per 1K characters | $0.00075 | $5/mo | $10/mo | $30/mo |

### Compute

| Service | SKU | Billing Unit | Unit Cost | Dev Estimate | Staging Estimate | Prod Estimate |
|---------|-----|-------------|-----------|-------------|-----------------|---------------|
| **AKS — System Pool** | D2s_v3 (dev) / D4s_v3 (prod) | Per node/hour | $0.096/hr (D2) / $0.192/hr (D4) | $140/mo | $420/mo | $1,260/mo |
| **AKS — Workload Pool** | D4s_v3 | Per node/hour | $0.192/hr | $140/mo | $420/mo | $1,400/mo |
| **Azure Functions** | Consumption / EP1 | Per execution + GB-s | $0.20/M exec | $10/mo | $30/mo | $300/mo |
| **Container Registry** | Basic / Premium | Per day + storage | $0.167/day (Basic) / $1.667/day (Prem) | $5/mo | $15/mo | $50/mo |

### Data & Storage

| Service | SKU | Billing Unit | Unit Cost | Dev Estimate | Staging Estimate | Prod Estimate |
|---------|-----|-------------|-----------|-------------|-----------------|---------------|
| **Data Lake Gen2 — Hot** | StorageV2 | Per GB/month + operations | $0.018/GB | $5/mo | $20/mo | $100/mo |
| **Data Lake Gen2 — Cool** | StorageV2 | Per GB/month + operations | $0.01/GB | $2/mo | $5/mo | $50/mo |
| **Cosmos DB** | Serverless / Autoscale | Per RU/s + storage | $0.25/M RU (serverless) | $25/mo | $100/mo | $500/mo |
| **Azure Cache for Redis** | C1 (dev) / P1 (prod) | Per instance/hour | $0.055/hr (C1) / $0.554/hr (P1) | $40/mo | $150/mo | $400/mo |

### Networking

| Service | SKU | Billing Unit | Unit Cost | Dev Estimate | Staging Estimate | Prod Estimate |
|---------|-----|-------------|-----------|-------------|-----------------|---------------|
| **Application Gateway + WAF** | WAF_v2 | Per hour + capacity | $0.36/hr + CU | $0/mo (none) | $0/mo | $300/mo |
| **Azure Bastion** | Standard | Per hour | $0.19/hr | $0/mo | $0/mo | $140/mo |
| **API Management** | Developer / Standard | Per unit/hour | $0.07/hr (Dev) / $0.98/hr (Std) | $50/mo | $200/mo | $700/mo |
| **Private Endpoints** | Standard | Per endpoint/hour | $0.01/hr | $25/mo | $50/mo | $75/mo |
| **DDoS Protection** | Standard | Per month | $2,944/mo | $0/mo | $0/mo | $2,944/mo |
| **VNet** | Standard | Free | Free | $0/mo | $0/mo | $0/mo |

### Monitoring & Security

| Service | SKU | Billing Unit | Unit Cost | Dev Estimate | Staging Estimate | Prod Estimate |
|---------|-----|-------------|-----------|-------------|-----------------|---------------|
| **Log Analytics** | Per-GB | Per GB ingested | $2.76/GB | $30/mo | $80/mo | $300/mo |
| **Application Insights** | Standard | Per GB ingested | $2.76/GB | $20/mo | $50/mo | $200/mo |
| **Key Vault** | Standard / Premium | Per operation | $0.03/10K ops | $5/mo | $10/mo | $30/mo |
| **Microsoft Sentinel** | Pay-per-GB | Per GB analyzed | $2.46/GB | $0/mo | $0/mo | $200/mo |
| **Defender for Cloud** | Standard | Per resource/month | Varies | $20/mo | $30/mo | $100/mo |
| **Entra ID P2** | Per user | Per user/month | $9/user | $45/mo | $45/mo | $90/mo |

---

## Monthly Cost Estimates by Environment

### Summary

| Category | Development | Staging | Production | Total |
|----------|------------|---------|------------|-------|
| **AI Services** | $220 | $693 | $4,770 | $5,683 |
| **Compute** | $295 | $885 | $3,010 | $4,190 |
| **Data & Storage** | $72 | $275 | $1,050 | $1,397 |
| **Networking** | $75 | $250 | $4,159 | $4,484 |
| **Monitoring & Security** | $120 | $215 | $920 | $1,255 |
| **Total Monthly** | **$782** | **$2,318** | **$13,909** | **$17,009** |
| **Total Annual** | **$9,384** | **$27,816** | **$166,908** | **$204,108** |

### Cost Distribution (Production)

```
AI Services (OpenAI + Search)  ████████████████████  34%
Networking (DDoS + APIM + WAF) ████████████████████  30%
Compute (AKS + Functions)      ██████████████        22%
Data & Storage                 ████                   8%
Monitoring & Security          ████                   6%
```

### Scale-Adjusted Estimates

| Scale | Queries/Day | Monthly Prod Cost | Cost per Query |
|-------|------------|-------------------|---------------|
| **Current** | 1,000 | $13,909 | $0.46 |
| **6 months** | 5,000 | $18,500 | $0.12 |
| **12 months** | 15,000 | $28,000 | $0.06 |
| **24 months** | 50,000 | $52,000 | $0.03 |

*Note: Cost per query decreases with scale due to fixed infrastructure costs being amortized.*

---

## Cost Optimization Recommendations

### Reserved Instances

| Service | Pay-as-you-go | 1-Year Reserved | 3-Year Reserved | Savings |
|---------|--------------|-----------------|-----------------|---------|
| AKS Nodes (D4s_v3) | $0.192/hr | $0.121/hr | $0.077/hr | 37–60% |
| Redis (P1) | $0.554/hr | $0.348/hr | $0.221/hr | 37–60% |
| Cosmos DB (Autoscale) | Standard | Reserved capacity | — | 20–65% |

### Spot Nodes (AKS)

```yaml
Spot Node Pool:
  Name: spot-workload
  VM Size: Standard_D4s_v3
  Priority: Spot
  Eviction Policy: Delete
  Max Price: -1 (Azure-defined, ~70% discount)
  Use For: Batch evaluation, non-critical ingestion
  NOT For: Real-time API serving
  Savings: ~60-70% vs on-demand
```

### Right-Sizing Recommendations

| Service | Current | Recommended (Dev) | Recommended (Prod) | Savings |
|---------|---------|-------------------|--------------------|---------|
| AKS System Pool | D4s_v3 (3 nodes) | D2s_v3 (2 nodes) | D4s_v3 (3 nodes) | 50% dev |
| AI Search | Standard S1 | Basic (1 unit) | Standard S1 (2 units) | 70% dev |
| Redis | Premium P1 | Basic C1 | Premium P1 | 93% dev |
| Functions | EP1 | Consumption | EP1 | 90% dev |
| Cosmos DB | Autoscale 4000 RU | Serverless | Autoscale 4000 RU | 80% dev |
| APIM | Standard | Developer | Standard | 93% dev |

### Caching Cost Reduction

| Without Cache | With Cache (30% L1 hit) | Savings |
|--------------|------------------------|---------|
| 30,000 queries × $0.012 = $360/day | 21,000 × $0.012 + $13/day (Redis) = $265/day | 26% |
| OpenAI tokens: 90M/month | OpenAI tokens: 63M/month | 30% |

---

## Dos and Don'ts

### Dos

| # | Practice | Impact | Implementation |
|---|---------|--------|----------------|
| 1 | **Use model routing** — Send simple queries to GPT-4o-mini | 60–70% token cost reduction | Intent classifier routes by complexity |
| 2 | **Enable caching** — Cache frequent queries and retrieval results | 30% cost reduction | Redis with TTLs |
| 3 | **Right-size per environment** — Dev uses minimum SKUs | 50–80% dev cost savings | Terraform variables per environment |
| 4 | **Set token budgets** — Limit max tokens per query and per day | Prevents cost spikes | APIM policies + application config |
| 5 | **Use reserved instances** — Commit to 1-year for stable workloads | 37–60% savings | Azure reservation portal |
| 6 | **Tag all resources** — Apply cost allocation tags | Accurate chargeback | Azure Policy enforcement |
| 7 | **Review costs weekly** — FinOps review of anomalies | Early detection | Cost Management dashboards |
| 8 | **Auto-shutdown dev** — Scale to zero outside business hours | 65% dev compute savings | KEDA + Function consumption plan |
| 9 | **Compress prompts** — Remove unnecessary context, use concise system prompts | 15–20% token savings | Prompt engineering |
| 10 | **Archive old data** — Move to cool/archive storage tiers | 50–80% storage savings | Lifecycle policies |

### Don'ts

| # | Anti-Pattern | Risk | Alternative |
|---|-------------|------|-------------|
| 1 | **Don't use GPT-4o for everything** | 10x higher cost for simple queries | Model routing by intent |
| 2 | **Don't skip caching** | Paying for identical queries repeatedly | Redis cache with TTLs |
| 3 | **Don't use prod SKUs in dev** | Wasting 80% of dev budget | Environment-specific Terraform vars |
| 4 | **Don't ignore token limits** | Single user could exhaust daily budget | Max tokens + rate limits |
| 5 | **Don't run DDoS Standard on all envs** | $2,944/mo per environment | Only production |
| 6 | **Don't keep Bastion running 24/7** | $140/mo when rarely used | Start/stop on demand |
| 7 | **Don't over-provision Cosmos DB** | Paying for unused RU/s | Autoscale or serverless |
| 8 | **Don't send full documents as context** | Massive token waste | Chunk and retrieve only relevant pieces |
| 9 | **Don't ignore log retention** | Logs can cost more than compute | Set retention policies (30/90/365 days) |
| 10 | **Don't deploy without cost alerts** | No visibility into spend | Budget alerts at 50%, 80%, 100% |

---

## Budget Alerts and Thresholds

### Alert Configuration

```yaml
Azure Cost Management Budgets:
  Development:
    Monthly Budget: $1,000
    Alerts:
      - Threshold: 50% ($500) → Email: devops-team
      - Threshold: 80% ($800) → Email: devops-team + manager
      - Threshold: 100% ($1,000) → Email: all + action group (auto-scale-down)

  Staging:
    Monthly Budget: $3,000
    Alerts:
      - Threshold: 50% ($1,500) → Email: devops-team
      - Threshold: 80% ($2,400) → Email: devops-team + manager
      - Threshold: 100% ($3,000) → Email: all + action group

  Production:
    Monthly Budget: $18,000
    Alerts:
      - Threshold: 50% ($9,000) → Email: devops-team
      - Threshold: 80% ($14,400) → Email: devops-team + manager + finance
      - Threshold: 100% ($18,000) → Email: all + action group (cost review)
      - Threshold: 120% ($21,600) → Email: all + emergency action group
```

### Token Budget Enforcement

| Scope | Daily Limit | Per-Query Limit | Alert At | Action |
|-------|-----------|----------------|---------|--------|
| Platform (total) | 5M tokens | — | 80% | Email alert |
| Per tenant (B2B) | Per SLA tier | Per SLA tier | 90% | Throttle |
| Per user (B2E) | 50K tokens | 4,000 tokens | 90% | Warn user |
| Per session (B2C) | 10K tokens | 2,000 tokens | 80% | End session gracefully |

### Anomaly Detection

| Metric | Baseline | Anomaly Trigger | Action |
|--------|----------|----------------|--------|
| Daily token usage | 30-day rolling average | > 2x baseline | Alert + investigate |
| Daily cost | 30-day rolling average | > 1.5x baseline | Alert + investigate |
| Per-user cost | Historical average | > 5x user average | Alert + rate limit |
| Per-tenant cost | SLA baseline | > 1.2x contracted | Alert + review |

---

## Cost Allocation Tags and Chargeback

### Required Tags

| Tag Name | Values | Purpose | Enforced |
|----------|--------|---------|----------|
| `Environment` | dev, staging, prod | Environment separation | Azure Policy (deny) |
| `Project` | aoai-platform | Project attribution | Azure Policy (deny) |
| `CostCenter` | CC-1234, CC-5678 | Finance chargeback | Azure Policy (audit) |
| `Team` | platform, security, data | Team ownership | Azure Policy (audit) |
| `Tenant` | tenant-001, shared | Multi-tenant attribution | Azure Policy (audit) |
| `ManagedBy` | terraform | IaC tracking | Azure Policy (audit) |

### Chargeback Model

| Cost Category | Allocation Method | Charged To |
|---------------|------------------|-----------|
| **Shared infrastructure** (VNet, monitoring, security) | Even split across tenants | Platform overhead |
| **AI Services** (OpenAI tokens) | Metered per tenant | Tenant cost center |
| **Compute** (AKS, Functions) | Proportional to usage | Weighted by query volume |
| **Storage** (Data Lake, Cosmos) | Per-tenant storage used | Tenant cost center |
| **Cache** (Redis) | Even split | Platform overhead |

### Chargeback Report

```
Monthly Chargeback Report — January 2025
──────────────────────────────────────────────

Tenant: Internal HR (tenant-001)
  Queries: 8,500
  Tokens consumed: 12.5M
  OpenAI cost: $175.00
  Search cost: $85.00
  Compute (allocated): $420.00
  Storage: $15.00
  Platform overhead: $200.00
  ────────────────────
  Total: $895.00

Tenant: Compliance (tenant-002)
  Queries: 15,200
  Tokens consumed: 25.8M
  ...
```

---

## Token Usage Optimization

### Prompt Compression

| Technique | Token Reduction | Quality Impact | Implementation |
|-----------|----------------|---------------|----------------|
| **Remove boilerplate** from system prompt | 10–15% | None | Trim redundant instructions |
| **Shorten context** — Top-K = 5 instead of 8 | 30–40% | -3% groundedness | Adjust top-K dynamically |
| **Summarize low-rank chunks** | 20–30% | -1% groundedness | GPT-4o-mini summarization |
| **Use abbreviations** in system prompt | 5% | None | Tested carefully |
| **Dynamic prompt selection** | 10–20% | None | Intent-based prompt template |

### Response Length Limits

| Use Case | Max Output Tokens | Avg Tokens | Rationale |
|----------|------------------|-----------|-----------|
| Simple factual | 500 | 150 | Short answers |
| Procedural | 1,000 | 400 | Step-by-step |
| Comparative | 1,500 | 600 | Multiple perspectives |
| Complex analytical | 2,000 | 800 | Detailed analysis |
| Summarization | 500 | 250 | Concise by design |

### Model Routing by Cost

```
Query Intent
    │
    ├── Simple/Factual → GPT-4o-mini ($0.001/query)
    │   (60% of queries)
    │
    ├── Standard → GPT-4o ($0.012/query)
    │   (30% of queries)
    │
    └── Complex → GPT-4o with high tokens ($0.024/query)
        (10% of queries)

Blended cost: 0.6 × $0.001 + 0.3 × $0.012 + 0.1 × $0.024
            = $0.0006 + $0.0036 + $0.0024
            = $0.0066/query (vs $0.012 without routing = 45% savings)
```

---

## Scaling Cost Impact Analysis

### Cost Growth Scenarios

| Queries/Day | OpenAI Cost | AI Search | Compute | Storage | Total Monthly |
|-------------|-----------|-----------|---------|---------|---------------|
| 1,000 | $3,750 | $750 | $3,010 | $1,050 | $13,909 |
| 5,000 | $6,000 | $1,500 | $4,200 | $1,500 | $18,500 |
| 15,000 | $12,000 | $2,250 | $6,500 | $2,000 | $28,000 |
| 50,000 | $30,000 | $4,500 | $10,000 | $3,500 | $52,000 |

### Scale-Up Trigger Points

| Trigger | Current Capacity | Scale Action | Cost Delta |
|---------|-----------------|-------------|-----------|
| Queries > 5,000/day | 1 AKS workload node | Add 2 nodes | +$280/mo |
| AI Search latency > 500ms | 1 search unit | Add 1 replica | +$250/mo |
| Cosmos DB 429 errors | 4,000 RU/s | Increase to 8,000 RU/s | +$250/mo |
| OpenAI 429 rate > 5% | 50 TPM | Increase to 100 TPM | $0 (PTU) or per-token |
| Redis memory > 80% | P1 (6GB) | P2 (13GB) | +$400/mo |

### Break-Even Analysis

| Optimization | Monthly Investment | Monthly Savings | Break-Even |
|-------------|-------------------|-----------------|-----------|
| Redis cache layer | $400 (P1 instance) | $1,200 (30% token reduction) | Month 1 |
| Model routing | $50 (classifier cost) | $2,500 (60% token reduction) | Month 1 |
| Reserved instances (1yr) | Upfront commitment | $800/mo on compute | Month 1 |
| Spot nodes for batch | $0 | $200/mo on eval/batch | Month 1 |
| Prompt compression | $0 (engineering effort) | $500/mo token savings | Immediate |

### FinOps Maturity Model

| Level | Practices | Tools | Review Cycle |
|-------|----------|-------|-------------|
| **Crawl** | Tag resources, set budgets, basic alerts | Azure Cost Management | Monthly |
| **Walk** | Chargeback model, right-sizing, reserved instances | Cost Management + Advisor | Bi-weekly |
| **Run** | Automated optimization, anomaly detection, forecasting | Cost Management + custom dashboards + automation | Weekly |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Platform Team + Finance |
| Review | Monthly |
| Related | [Tech Stack](../reference/TECH-STACK-SERVICES.md), [Enterprise Viewpoints](../architecture/ENTERPRISE-VIEWPOINTS.md) |
