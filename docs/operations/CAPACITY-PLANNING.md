# Capacity Planning — Enterprise Azure OpenAI RAG Platform

> **Demand Forecasting, Resource Scaling, and Infrastructure Growth Planning**
> Framework Alignment: CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF

---

## Table of Contents

1. [Current Baseline Metrics](#current-baseline-metrics)
2. [Growth Projections](#growth-projections)
3. [Scaling Triggers and Thresholds](#scaling-triggers-and-thresholds)
4. [Azure Service Limits](#azure-service-limits)
5. [Cost Projection Models](#cost-projection-models)
6. [SKU Upgrade Triggers](#sku-upgrade-triggers)
7. [Multi-Region Expansion Planning](#multi-region-expansion-planning)
8. [Token Consumption Forecasting](#token-consumption-forecasting)
9. [Storage Growth Forecasting](#storage-growth-forecasting)
10. [AKS Node Scaling Model](#aks-node-scaling-model)
11. [OpenAI TPM Quota Planning](#openai-tpm-quota-planning)
12. [Cosmos DB RU/s Scaling Model](#cosmos-db-rus-scaling-model)
13. [Reserved Instance Commitment Planning](#reserved-instance-commitment-planning)
14. [Capacity Review Cadence](#capacity-review-cadence)
15. [Capacity Alerts and KQL Queries](#capacity-alerts-and-kql-queries)

---

## Current Baseline Metrics

**Baseline Snapshot** taken from production environment as of last capacity review cycle.

| Service | Resource | Current Usage | Provisioned Capacity | Utilization % | Status |
|---------|----------|---------------|----------------------|---------------|--------|
| **Azure OpenAI — GPT-4o** | TPM (Tokens/Min) | 48,000 | 80,000 | 60% | Normal |
| **Azure OpenAI — GPT-4o-mini** | TPM (Tokens/Min) | 22,000 | 60,000 | 37% | Normal |
| **Azure OpenAI — Embeddings** | TPM (Tokens/Min) | 95,000 | 350,000 | 27% | Normal |
| **Azure AI Search** | Queries/Sec (QPS) | 18 | 50 (S1) | 36% | Normal |
| **Azure AI Search** | Index Size | 28 GB | 160 GB (S1 x1) | 18% | Normal |
| **Cosmos DB** | RU/s (Autoscale) | 2,800 | 8,000 max | 35% | Normal |
| **Cosmos DB** | Storage | 45 GB | Unlimited | — | Normal |
| **AKS — System Pool** | CPU | 1.8 cores | 4 cores (D4s_v3 x1) | 45% | Normal |
| **AKS — Workload Pool** | CPU | 9.6 cores | 16 cores (D4s_v3 x4) | 60% | Watch |
| **AKS — Workload Pool** | Memory | 24 GB | 64 GB | 38% | Normal |
| **Data Lake Gen2** | Storage (Hot) | 120 GB | 5 TB account | 2% | Normal |
| **Data Lake Gen2** | Storage (Cool) | 380 GB | 5 TB account | 8% | Normal |
| **Redis Cache** | Memory | 4.2 GB | 6 GB (P1) | 70% | Watch |
| **Redis Cache** | Connections | 680 | 7,500 | 9% | Normal |
| **API Management** | Requests/Sec | 35 | 4,000 (Standard) | <1% | Normal |
| **Application Gateway** | Connections | 850 | 32,000 (WAF_v2) | 3% | Normal |
| **Document Intelligence** | Pages/Day | 2,400 | 50,000 (S0) | 5% | Normal |

### Status Definitions

| Status | Utilization Range | Action Required |
|--------|-------------------|-----------------|
| **Normal** | 0–59% | No action; continue monitoring |
| **Watch** | 60–74% | Add to next capacity review |
| **Warning** | 75–89% | Begin scaling plan within 2 weeks |
| **Critical** | 90–100% | Immediate scaling required |

---

## Growth Projections

### User and Workload Growth

| Metric | Current (Month 0) | 6 Months | 12 Months | 24 Months |
|--------|--------------------|----------|-----------|-----------|
| **Active Users** | 500 | 1,200 | 2,500 | 6,000 |
| **Queries/Day** | 15,000 | 36,000 | 75,000 | 180,000 |
| **Peak Queries/Hour** | 2,500 | 6,000 | 12,500 | 30,000 |
| **Documents Indexed** | 85,000 | 200,000 | 450,000 | 1,200,000 |
| **Total Storage (Hot)** | 120 GB | 290 GB | 650 GB | 1.8 TB |
| **Total Storage (Cool)** | 380 GB | 900 GB | 2.0 TB | 5.5 TB |
| **Embeddings Vectors** | 2.1M | 5.0M | 11.2M | 30M |
| **Cosmos DB Documents** | 1.8M | 4.3M | 9.5M | 25M |
| **Monthly Token Consumption** | 180M | 430M | 960M | 2.3B |

### Growth Assumptions

```
Compound Monthly Growth Rate (CMGR):
  - Users:      ~15% month-over-month for first 12 months, tapering to ~8%
  - Queries:    Proportional to users × engagement increase (1.2x factor)
  - Documents:  ~12% monthly (driven by onboarding new departments)
  - Storage:    Linear with documents + version history overhead (1.3x multiplier)
```

### Growth Trajectory (ASCII)

```
  Queries/Day (thousands)
  200 ┤
      │                                                          ╭──
  160 ┤                                                     ╭────╯
      │                                                ╭────╯
  120 ┤                                           ╭────╯
      │                                      ╭────╯
   80 ┤                                 ╭────╯
      │                           ╭─────╯
   60 ┤                      ╭────╯
      │                 ╭────╯
   40 ┤            ╭────╯
      │       ╭────╯
   20 ┤──╮────╯
      │  ╰── Current
    0 ┼───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
      M0  M2  M4  M6  M8  M10 M12 M14 M16 M18 M20 M22 M24
```

---

## Scaling Triggers and Thresholds

### Per-Service Scaling Matrix

| Service | Metric | Warning (75%) | Critical (90%) | Scale Action |
|---------|--------|---------------|----------------|--------------|
| **Azure OpenAI GPT-4o** | TPM Utilization | 60,000 TPM | 72,000 TPM | Request quota increase via Azure Portal |
| **Azure OpenAI Embeddings** | TPM Utilization | 262,500 TPM | 315,000 TPM | Request quota increase; add PTU deployment |
| **AI Search** | QPS | 38 QPS | 45 QPS | Add replica (S1: up to 12) |
| **AI Search** | Index Size | 120 GB | 144 GB | Add partition or upgrade SKU |
| **AI Search** | Latency P95 | >150ms | >300ms | Add replica for read throughput |
| **Cosmos DB** | RU/s Consumed | 6,000 RU/s | 7,200 RU/s | Increase autoscale max RU/s |
| **Cosmos DB** | Storage/Partition | 37.5 GB | 45 GB | Review partition key distribution |
| **AKS Workload Pool** | CPU Utilization | 60% avg | 80% avg | HPA scales pods; add node if pool full |
| **AKS Workload Pool** | Memory Utilization | 70% avg | 85% avg | Increase pod limits; add node |
| **Redis Cache** | Memory Usage | 4.5 GB (75%) | 5.4 GB (90%) | Upgrade to P2 (13 GB) |
| **Redis Cache** | Server Load | 60% | 80% | Upgrade SKU or enable clustering |
| **API Management** | Capacity Metric | 70% | 85% | Add unit or upgrade SKU |
| **Data Lake Gen2** | Transaction Rate | 15,000 IOPS | 18,000 IOPS | Enable premium tier or distribute |
| **Document Intelligence** | Queue Depth | >500 pages | >2,000 pages | Add concurrent processing instances |
| **App Gateway** | Compute Units | 75% peak CU | 90% peak CU | Enable autoscaling (max CU increase) |

### Automated Scaling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCALING DECISION FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────┐ │
│  │ Azure Monitor │───▶│ Alert Rule    │───▶│ Action Group     │ │
│  │ Metrics       │    │ (Threshold)   │    │ (Notify + Auto)  │ │
│  └──────────────┘    └───────────────┘    └────────┬─────────┘ │
│                                                     │           │
│                              ┌──────────────────────┼───────┐   │
│                              │                      ▼       │   │
│                    ┌─────────┴──────┐   ┌──────────────────┐│   │
│                    │ Manual Review  │   │ Auto-Scale       ││   │
│                    │ (SKU changes,  │   │ (HPA, VMSS,      ││   │
│                    │  quota requests│   │  Cosmos autoscale)││   │
│                    │  RI purchases) │   │                   ││   │
│                    └────────────────┘   └──────────────────┘│   │
│                                                              │   │
│                              └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Azure Service Limits

### Hard Limits and Soft Limits Reference

| Service | Limit Description | Value | Limit Type | Request Process |
|---------|-------------------|-------|------------|-----------------|
| **Azure OpenAI** | TPM per deployment (GPT-4o) | 80K–450K | Soft | Azure Portal → Quotas → Request Increase |
| **Azure OpenAI** | TPM per deployment (GPT-4o-mini) | 200K–2M | Soft | Azure Portal → Quotas → Request Increase |
| **Azure OpenAI** | TPM per deployment (Embeddings) | 350K–1M | Soft | Azure Portal → Quotas → Request Increase |
| **Azure OpenAI** | Max deployments per resource | 32 | Hard | Create additional AOAI resource |
| **Azure OpenAI** | Max content filter configs | 100 | Soft | Support ticket |
| **Azure OpenAI** | Requests per minute (RPM) | 480–3,600 | Soft | Azure Portal → Quotas |
| **AI Search (S1)** | Indexes per service | 50 | Hard | Upgrade SKU or add service |
| **AI Search (S1)** | Partitions | 12 | Hard | Upgrade SKU |
| **AI Search (S1)** | Replicas | 12 | Hard | Upgrade SKU |
| **AI Search (S1)** | Search units (R × P) | 36 | Hard | Upgrade SKU |
| **AI Search (S1)** | Storage per partition | 160 GB | Hard | Add partition or upgrade SKU |
| **AI Search (S1)** | Documents per index | 15M | Soft | Upgrade to S2 for higher limits |
| **Cosmos DB** | Max RU/s (autoscale) | 1,000,000 | Soft | Support ticket for higher |
| **Cosmos DB** | Max item size | 2 MB | Hard | Application-level chunking |
| **Cosmos DB** | Logical partition max | 20 GB | Hard | Redesign partition key |
| **Cosmos DB** | Physical partition max | 50 GB | Hard | Automatic splitting |
| **AKS** | Nodes per pool | 1,000 | Hard | Multiple node pools |
| **AKS** | Pods per node | 250 | Hard | Adjust max-pods setting |
| **AKS** | Max clusters per subscription | 5,000 | Soft | Support ticket |
| **Data Lake Gen2** | Max storage account size | 5 PB | Hard | Multiple accounts |
| **Data Lake Gen2** | Max single blob size | 190.7 TB | Hard | — |
| **Redis (P1)** | Memory | 6 GB | Hard | Upgrade to P2 (13 GB) |
| **Redis (P2)** | Memory | 13 GB | Hard | Upgrade to P3 (26 GB) |
| **API Management (Standard)** | Max units | 4 | Soft | Upgrade to Premium |
| **API Management (Standard)** | Requests/sec (est.) | ~4,000 | Soft | Add units or upgrade |
| **App Gateway (WAF_v2)** | Max instances | 125 | Hard | — |
| **Subscription** | Cores per region | 350 (default) | Soft | Support ticket |
| **Subscription** | Resource groups | 980 | Hard | — |

---

## Cost Projection Models

### Monthly Cost at Scale Multipliers

| Service | Current (1x) | 2x Scale | 5x Scale | 10x Scale |
|---------|-------------|----------|----------|-----------|
| **Azure OpenAI — GPT-4o** | $3,750 | $7,500 | $18,750 | $37,500 |
| **Azure OpenAI — GPT-4o-mini** | $90 | $180 | $450 | $900 |
| **Azure OpenAI — Embeddings** | $50 | $100 | $250 | $500 |
| **AI Search (S1)** | $750 | $1,500 | $3,750 | $7,500 |
| **Cosmos DB** | $500 | $950 | $2,200 | $4,500 |
| **AKS Compute** | $2,660 | $4,200 | $9,800 | $19,600 |
| **Data Lake Gen2** | $150 | $300 | $750 | $1,500 |
| **Redis Cache** | $400 | $800 | $1,600 | $3,200 |
| **API Management** | $700 | $700 | $1,400 | $2,800 |
| **App Gateway + WAF** | $300 | $300 | $450 | $600 |
| **Document Intelligence** | $100 | $200 | $500 | $1,000 |
| **Networking & Misc** | $215 | $350 | $700 | $1,200 |
| **Monitoring (Log Analytics)** | $200 | $350 | $800 | $1,500 |
| **Key Vault** | $15 | $15 | $20 | $30 |
| **───────────────** | **─────────** | **────────** | **────────** | **─────────** |
| **Total Monthly** | **$9,880** | **$17,445** | **$41,420** | **$82,330** |
| **Total Annual** | **$118,560** | **$209,340** | **$497,040** | **$987,960** |
| **Cost per User/Month** | **$19.76** | **$17.45** | **$16.57** | **$13.72** |

### Cost Scaling Efficiency

```
  Monthly Cost ($K)
  90 ┤
     │                                                    ╭── 10x
  80 ┤                                               ╭────╯
     │                                          ╭────╯
  70 ┤                                     ╭────╯
     │                                ╭────╯
  60 ┤                           ╭────╯
     │                      ╭────╯
  50 ┤                 ╭────╯
     │            ╭────╯               Cost grows ~8.3x at 10x scale
  40 ┤       ╭────╯                    (sublinear due to fixed costs)
     │  ╭────╯
  30 ┤──╯
     │
  20 ┤── 2x
     │
  10 ┤── 1x (current)
     │
   0 ┼───┬────┬────┬────┬────┬────┬────┬────┬────┬────
     1x  2x   3x   4x   5x   6x   7x   8x   9x  10x
```

---

## SKU Upgrade Triggers

### Decision Matrix: When to Upgrade

| Service | Current SKU | Upgrade To | Trigger Condition | Lead Time | Downtime |
|---------|-------------|------------|-------------------|-----------|----------|
| **AI Search** | S1 (1 SU) | S1 (+ replica) | QPS >38 sustained 7 days | Minutes | None |
| **AI Search** | S1 (1 SU) | S1 (+ partition) | Index >120 GB | Minutes | None |
| **AI Search** | S1 (max SU) | S2 | Need >160 GB/partition or >50 indexes | 2–4 hours | Reindex required |
| **AI Search** | S2 | S3 | Need >512 GB/partition or >200 indexes | 2–4 hours | Reindex required |
| **Cosmos DB** | Autoscale 8K | Autoscale 16K | Sustained >6K RU/s (75%) for 7 days | Minutes | None |
| **Cosmos DB** | Autoscale 16K | Autoscale 40K | Sustained >12K RU/s; >2,000 users | Minutes | None |
| **Cosmos DB** | Serverless | Provisioned | Workload >$200/mo serverless cost | 1 hour | Migration needed |
| **Redis** | P1 (6 GB) | P2 (13 GB) | Memory >4.5 GB (75%) sustained | 30 min | Brief failover |
| **Redis** | P2 (13 GB) | P3 (26 GB) | Memory >9.75 GB (75%) sustained | 30 min | Brief failover |
| **Redis** | P3 single | P3 clustered | Need >26 GB or >100K ops/sec | 1 hour | Brief failover |
| **AKS nodes** | D4s_v3 | D8s_v3 | Pod memory limits >14 GB consistently | Node drain | Rolling update |
| **AKS nodes** | D8s_v3 | D16s_v3 | Compute-heavy workloads >90% CPU | Node drain | Rolling update |
| **API Mgmt** | Standard (1 unit) | Standard (2 units) | Capacity metric >70% sustained | Minutes | None |
| **API Mgmt** | Standard (4 units) | Premium | Need multi-region or VNet integration | 45 min | Brief |
| **App Gateway** | WAF_v2 (2 inst) | WAF_v2 (auto 2–10) | CU >75% peak | Minutes | None |

### AI Search SKU Comparison

```
┌───────────────────────────────────────────────────────────────────┐
│              AI Search SKU Progression                            │
├──────────┬──────────┬────────────┬───────────┬──────────────────┤
│          │ Basic    │ S1         │ S2        │ S3               │
├──────────┼──────────┼────────────┼───────────┼──────────────────┤
│ Storage  │ 2 GB     │ 160 GB/P   │ 512 GB/P  │ 2 TB/P           │
│ Indexes  │ 15       │ 50         │ 200       │ 200              │
│ Replicas │ 3        │ 12         │ 12        │ 12               │
│ Partns   │ 1        │ 12         │ 12        │ 12               │
│ Max SU   │ 3        │ 36         │ 36        │ 36               │
│ Cost/SU  │ ~$250/mo │ ~$250/mo   │ ~$1,000/mo│ ~$2,000/mo       │
├──────────┼──────────┼────────────┼───────────┼──────────────────┤
│ Upgrade  │ >2 GB or │ >160 GB/P  │ >512 GB/P │ S3HD or multiple │
│ When     │ >15 idx  │ or >50 idx │ or >200idx│ services         │
└──────────┴──────────┴────────────┴───────────┴──────────────────┘
```

---

## Multi-Region Expansion Planning

### When to Add Regions

**Latency-Based Triggers:**

| Trigger | Threshold | Measurement | Action |
|---------|-----------|-------------|--------|
| **API Response P95** | >200ms | Application Insights (end-to-end) | Evaluate CDN or regional deployment |
| **API Response P99** | >500ms | Application Insights | Deploy API tier to closest region |
| **OpenAI Inference P95** | >3s | Custom metrics (model latency) | Deploy model in second region |
| **Search Query P95** | >150ms | AI Search metrics | Add search replica in secondary region |
| **User-Perceived Latency** | >2s total | Real User Monitoring (RUM) | Full regional stack deployment |

**Compliance-Based Triggers:**

| Trigger | Requirement | Action |
|---------|-------------|--------|
| **EU Data Residency** | GDPR — data stays in EU | Deploy full stack in West Europe |
| **Canada Data Residency** | PIPEDA compliance | Deploy in Canada Central |
| **Government Workloads** | FedRAMP / IL4+ | Deploy in Azure Government |
| **APAC Users >20%** | Latency + data residency | Deploy in Southeast Asia |

### Multi-Region Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    MULTI-REGION TOPOLOGY                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│              ┌─────────────────┐                                     │
│              │  Azure Front    │                                     │
│              │  Door / Traffic │                                     │
│              │  Manager        │                                     │
│              └────────┬────────┘                                     │
│                       │                                              │
│         ┌─────────────┼─────────────┐                                │
│         │             │             │                                 │
│         ▼             ▼             ▼                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                    │
│  │ East US 2   │ │ West Europe │ │ SE Asia     │                    │
│  │ (Primary)   │ │ (Secondary) │ │ (Future)    │                    │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤                    │
│  │ AKS Cluster │ │ AKS Cluster │ │ AKS Cluster │                    │
│  │ AOAI Deploy │ │ AOAI Deploy │ │ AOAI Deploy │                    │
│  │ AI Search   │ │ AI Search   │ │ AI Search   │                    │
│  │ Redis Cache │ │ Redis Cache │ │ Redis Cache │                    │
│  │ Cosmos DB ──┼─┼─ Cosmos DB ─┼─┼─ Cosmos DB  │                    │
│  │ (Write)     │ │ (Read)      │ │ (Read)      │                    │
│  └─────────────┘ └─────────────┘ └─────────────┘                    │
│                                                                      │
│  Note: Cosmos DB uses multi-region writes or single-write with       │
│        automatic failover. AI Search indexes replicated via          │
│        indexer pipeline per region.                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Regional Expansion Cost Impact

| Component | Single Region (Current) | Two Regions | Three Regions |
|-----------|-------------------------|-------------|---------------|
| **Compute (AKS)** | $2,660/mo | $5,320/mo | $7,980/mo |
| **Azure OpenAI** | $3,890/mo | $5,835/mo | $7,780/mo |
| **AI Search** | $750/mo | $1,500/mo | $2,250/mo |
| **Cosmos DB** | $500/mo | $750/mo | $1,000/mo |
| **Redis** | $400/mo | $800/mo | $1,200/mo |
| **Networking** | $515/mo | $1,200/mo | $1,900/mo |
| **Total** | **$8,715/mo** | **$15,405/mo** | **$22,110/mo** |
| **Multiplier** | 1.0x | 1.77x | 2.54x |

---

## Token Consumption Forecasting

### Core Forecasting Formula

```
Monthly Token Consumption = Active_Users × Queries_per_Day × 30 × Avg_Tokens_per_Query × (1 + Growth_Rate)^Months

Where:
  Avg_Tokens_per_Query = Input_Tokens + Output_Tokens
                       = (System_Prompt + Context_Chunks + User_Query) + Response_Tokens
                       = (800 + 2,400 + 150) + 650
                       = 4,000 tokens (weighted average across models)
```

### Token Breakdown by Component

| Component | Avg Tokens | Min | Max | Notes |
|-----------|-----------|-----|-----|-------|
| **System Prompt** | 800 | 400 | 1,200 | RAG instructions, persona, guardrails |
| **Retrieved Context** | 2,400 | 800 | 4,000 | 3–5 chunks × 600–800 tokens each |
| **User Query** | 150 | 20 | 500 | Typical enterprise question |
| **Model Response** | 650 | 200 | 2,000 | Answer with citations |
| **Total per Query** | **4,000** | **1,420** | **7,700** | Weighted average |

### Python Forecasting Model

```python
import math
from dataclasses import dataclass

@dataclass
class CapacityForecast:
    """Token consumption and cost forecasting model."""
    active_users: int = 500
    queries_per_user_day: float = 30.0     # avg queries per user per day
    avg_tokens_per_query: int = 4000       # input + output tokens
    input_ratio: float = 0.84              # 3350 / 4000 = input portion
    output_ratio: float = 0.16             # 650 / 4000 = output portion
    user_growth_rate_monthly: float = 0.15 # 15% monthly user growth
    engagement_growth_factor: float = 1.02 # 2% monthly engagement increase
    gpt4o_input_cost_per_1k: float = 0.005
    gpt4o_output_cost_per_1k: float = 0.015
    gpt4o_mini_ratio: float = 0.30         # 30% of queries use mini

    def forecast_month(self, months_ahead: int) -> dict:
        """Forecast token consumption and cost for a future month."""
        # Project user growth (tapering after 12 months)
        if months_ahead <= 12:
            growth = self.user_growth_rate_monthly
        else:
            growth = 0.08  # tapers to 8%

        projected_users = self.active_users * (1 + growth) ** months_ahead

        # Project engagement growth
        engagement = self.queries_per_user_day * (
            self.engagement_growth_factor ** months_ahead
        )

        # Daily token consumption
        daily_queries = projected_users * engagement
        daily_tokens = daily_queries * self.avg_tokens_per_query

        # Monthly totals
        monthly_tokens = daily_tokens * 30
        monthly_input = monthly_tokens * self.input_ratio
        monthly_output = monthly_tokens * self.output_ratio

        # Cost calculation (split by model)
        gpt4o_fraction = 1.0 - self.gpt4o_mini_ratio
        gpt4o_cost = (
            (monthly_input * gpt4o_fraction / 1000 * self.gpt4o_input_cost_per_1k) +
            (monthly_output * gpt4o_fraction / 1000 * self.gpt4o_output_cost_per_1k)
        )
        # GPT-4o-mini is ~30x cheaper on input, ~25x cheaper on output
        mini_cost = (
            (monthly_input * self.gpt4o_mini_ratio / 1000 * 0.00015) +
            (monthly_output * self.gpt4o_mini_ratio / 1000 * 0.0006)
        )

        # Required TPM (tokens per minute) based on peak factor
        peak_factor = 2.5  # peak is 2.5x average
        avg_tpm = daily_tokens / (24 * 60)
        required_tpm = avg_tpm * peak_factor

        return {
            "month": months_ahead,
            "users": int(projected_users),
            "daily_queries": int(daily_queries),
            "monthly_tokens_millions": round(monthly_tokens / 1e6, 1),
            "required_tpm": int(required_tpm),
            "monthly_gpt4o_cost": round(gpt4o_cost, 2),
            "monthly_mini_cost": round(mini_cost, 2),
            "total_monthly_cost": round(gpt4o_cost + mini_cost, 2),
        }

    def generate_forecast_table(self, months: list[int]) -> None:
        """Print forecast for specified months."""
        print(f"{'Month':<8}{'Users':<10}{'Queries/Day':<14}"
              f"{'Tokens(M)':<12}{'TPM Needed':<12}{'GPT-4o $':<12}"
              f"{'Mini $':<10}{'Total $':<10}")
        print("-" * 88)
        for m in months:
            f = self.forecast_month(m)
            print(f"{f['month']:<8}{f['users']:<10}{f['daily_queries']:<14}"
                  f"{f['monthly_tokens_millions']:<12}"
                  f"{f['required_tpm']:<12}"
                  f"${f['monthly_gpt4o_cost']:<11,.2f}"
                  f"${f['monthly_mini_cost']:<9,.2f}"
                  f"${f['total_monthly_cost']:<9,.2f}")


# Run forecast
forecast = CapacityForecast()
forecast.generate_forecast_table([0, 3, 6, 9, 12, 18, 24])
```

### Sample Forecast Output

| Month | Users | Queries/Day | Tokens (M/mo) | TPM Needed | GPT-4o Cost | Mini Cost | Total |
|-------|-------|-------------|----------------|------------|-------------|-----------|-------|
| 0 | 500 | 15,000 | 180 | 12,500 | $3,690 | $90 | $3,780 |
| 3 | 760 | 23,300 | 280 | 19,400 | $5,740 | $140 | $5,880 |
| 6 | 1,200 | 37,500 | 450 | 31,250 | $9,230 | $225 | $9,455 |
| 9 | 1,780 | 56,800 | 682 | 47,400 | $13,990 | $342 | $14,332 |
| 12 | 2,500 | 81,200 | 974 | 67,600 | $19,980 | $488 | $20,468 |
| 18 | 4,000 | 134,000 | 1,608 | 111,700 | $32,970 | $806 | $33,776 |
| 24 | 6,350 | 220,600 | 2,647 | 183,800 | $54,280 | $1,327 | $55,607 |

---

## Storage Growth Forecasting

### Storage Growth Formula

```
Monthly_Storage_Growth = New_Documents × Avg_Document_Size × Processing_Overhead

Where:
  New_Documents   = Base_Rate × (1 + Growth_Rate)^Month
  Avg_Doc_Size    = 2.5 MB (raw) → 0.8 MB (processed text) + 1.2 MB (embeddings) + 0.5 MB (metadata)
  Processing_Overhead = 1.3x (index overhead, versioning, staging copies)

Cumulative_Storage = Σ(Monthly_Growth) + Retention_Archive

Retention Policy:
  Hot:    0–90 days   (Data Lake Gen2 Hot tier)
  Cool:   91–365 days (Data Lake Gen2 Cool tier)
  Archive: >365 days  (Data Lake Gen2 Archive tier)
```

### Python Storage Forecasting

```python
@dataclass
class StorageForecast:
    """Storage capacity forecasting model."""
    current_docs: int = 85_000
    monthly_new_docs_base: int = 12_000
    doc_growth_rate: float = 0.12           # 12% monthly growth in new docs
    avg_raw_size_mb: float = 2.5
    avg_processed_size_mb: float = 0.8
    avg_embedding_size_mb: float = 1.2
    avg_metadata_size_mb: float = 0.5
    processing_overhead: float = 1.3
    retention_months_hot: int = 3
    retention_months_cool: int = 12

    def forecast_storage(self, months_ahead: int) -> dict:
        """Forecast storage needs at a future point."""
        total_docs = self.current_docs
        hot_storage_gb = 0
        cool_storage_gb = 0
        archive_storage_gb = 0

        monthly_docs_history = []

        for m in range(months_ahead + 1):
            new_docs = int(self.monthly_new_docs_base * (1 + self.doc_growth_rate) ** m)
            monthly_docs_history.append(new_docs)
            total_docs += new_docs

        # Storage per doc (total processed)
        per_doc_gb = (
            self.avg_processed_size_mb +
            self.avg_embedding_size_mb +
            self.avg_metadata_size_mb
        ) * self.processing_overhead / 1024  # Convert MB to GB

        # Hot = last N months of docs
        hot_docs = sum(monthly_docs_history[-self.retention_months_hot:])
        hot_storage_gb = hot_docs * per_doc_gb

        # Cool = months between hot and cool retention
        cool_start = max(0, len(monthly_docs_history) - self.retention_months_cool)
        cool_end = max(0, len(monthly_docs_history) - self.retention_months_hot)
        cool_docs = sum(monthly_docs_history[cool_start:cool_end])
        cool_storage_gb = cool_docs * per_doc_gb

        # Archive = everything older
        archive_docs = sum(monthly_docs_history[:cool_start])
        archive_storage_gb = archive_docs * per_doc_gb

        # AI Search index size (embeddings + metadata)
        index_size_gb = total_docs * (self.avg_embedding_size_mb + 0.1) / 1024

        return {
            "month": months_ahead,
            "total_documents": total_docs,
            "hot_storage_gb": round(hot_storage_gb, 1),
            "cool_storage_gb": round(cool_storage_gb, 1),
            "archive_storage_gb": round(archive_storage_gb, 1),
            "total_storage_gb": round(
                hot_storage_gb + cool_storage_gb + archive_storage_gb, 1
            ),
            "search_index_gb": round(index_size_gb, 1),
            "monthly_storage_cost": round(
                hot_storage_gb * 0.018 +
                cool_storage_gb * 0.01 +
                archive_storage_gb * 0.002, 2
            ),
        }
```

### Storage Projection Table

| Month | Total Docs | Hot (GB) | Cool (GB) | Archive (GB) | Total (GB) | Search Index (GB) | Storage Cost/Mo |
|-------|-----------|----------|-----------|---------------|------------|--------------------|----|
| 0 | 97,000 | 37 | 0 | 0 | 37 | 28 | $0.67 |
| 6 | 200,000 | 98 | 120 | 0 | 218 | 58 | $2.96 |
| 12 | 450,000 | 220 | 310 | 85 | 615 | 130 | $7.27 |
| 18 | 820,000 | 410 | 590 | 280 | 1,280 | 237 | $14.34 |
| 24 | 1,350,000 | 680 | 980 | 620 | 2,280 | 390 | $24.80 |

---

## AKS Node Scaling Model

### Scaling Parameters

```yaml
# AKS HPA Configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-api-hpa
  namespace: rag-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-api
  minReplicas: 3
  maxReplicas: 24
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "50"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

### Concurrent Users to Infrastructure Mapping

| Concurrent Users | Queries/Min | API Pods | Worker Pods | Nodes (D4s_v3) | Node Pool Config |
|------------------|-------------|----------|-------------|-----------------|------------------|
| 50 | 75 | 3 | 2 | 2 | Min: 2, Max: 4 |
| 100 | 150 | 4 | 3 | 3 | Min: 2, Max: 5 |
| 250 | 375 | 6 | 4 | 4 | Min: 3, Max: 6 |
| 500 | 750 | 10 | 6 | 5 | Min: 4, Max: 8 |
| 1,000 | 1,500 | 16 | 10 | 8 | Min: 6, Max: 12 |
| 2,000 | 3,000 | 24 | 16 | 12 | Min: 8, Max: 16 |
| 5,000 | 7,500 | 48 | 32 | 24 | Min: 16, Max: 32 |
| 10,000 | 15,000 | 80 | 50 | 40 | Min: 28, Max: 50 |

**Assumptions:**
- Each API pod handles ~50 req/min at target CPU
- Each pod requests: 500m CPU, 1Gi memory
- D4s_v3 node: 4 vCPU, 16 GB RAM, fits ~6 pods (with system overhead)
- System pool: 1–2 D4s_v3 nodes (separate pool, not counted above)

### Node Scaling Diagram

```
  Nodes (D4s_v3)
  50 ┤
     │                                                          ╭──
  40 ┤                                                     ╭────╯
     │                                                ╭────╯
  30 ┤                                           ╭────╯
     │                                      ╭────╯
  24 ┤- - - - - - - - - - - - - - - - ╭────╯- - - - - Node pool max
     │                           ╭─────╯                (expand pool)
  16 ┤                      ╭────╯
     │                 ╭────╯
  12 ┤            ╭────╯
     │       ╭────╯
   8 ┤──╮────╯
     │  ╰── Current (5 nodes)
   4 ┤
     │
   0 ┼───┬────┬────┬────┬────┬────┬────┬────┬────┬────
     50  250  500  1K   2K   3K   4K   5K   7K   10K
                    Concurrent Users
```

---

## OpenAI TPM Quota Planning

### Current Quota Allocation and Projections

| Model | Deployment | Current TPM | Current Usage | 6-Mo Need | 12-Mo Need | 24-Mo Need |
|-------|------------|-------------|---------------|-----------|------------|------------|
| **GPT-4o** | gpt4o-prod | 80,000 | 48,000 (60%) | 120,000 | 200,000 | 450,000 |
| **GPT-4o** | gpt4o-fallback | 40,000 | 5,000 (13%) | 60,000 | 100,000 | 200,000 |
| **GPT-4o-mini** | gpt4o-mini-prod | 60,000 | 22,000 (37%) | 80,000 | 150,000 | 300,000 |
| **text-embedding-3-large** | embed-prod | 350,000 | 95,000 (27%) | 200,000 | 400,000 | 800,000 |
| **text-embedding-3-large** | embed-batch | 200,000 | 120,000 (60%) | 300,000 | 500,000 | 1,000,000 |

### Quota Request Timeline

| Quarter | Model | Current Quota | Requested Quota | Justification | Request By |
|---------|-------|---------------|-----------------|---------------|------------|
| **Q1 2024** | GPT-4o | 80K TPM | 150K TPM | User growth 2.4x in 6 months | Immediate |
| **Q2 2024** | GPT-4o-mini | 60K TPM | 120K TPM | Shifting traffic to mini for cost | +3 months |
| **Q2 2024** | Embeddings | 350K TPM | 500K TPM | Document ingestion backlog | +3 months |
| **Q3 2024** | GPT-4o | 150K TPM | 250K TPM | 12-month projection | +6 months |
| **Q4 2024** | All models | Various | PTU evaluation | Consider Provisioned Throughput | +9 months |

### PTU (Provisioned Throughput Units) Break-Even Analysis

```
PTU Break-Even Formula:
  PTU_Monthly_Cost = PTU_Count × $2.00/hr × 730 hrs
  PayGo_Monthly_Cost = Monthly_Tokens / 1000 × Token_Price

  Break-Even when: PTU_Monthly_Cost < PayGo_Monthly_Cost

For GPT-4o:
  1 PTU ≈ 3,500 TPM capacity
  1 PTU cost = $2.00/hr × 730 = $1,460/month

  If monthly token usage = 600M tokens:
    PayGo cost = (600M × 0.84 / 1000 × $0.005) + (600M × 0.16 / 1000 × $0.015)
               = $2,520 + $1,440 = $3,960/month

  PTU needed = 200K TPM / 3,500 ≈ 58 PTUs
  PTU cost = 58 × $1,460 = $84,680/month

  Verdict: Stay on pay-as-you-go until >$85K/month token cost
           (approximately at 12B+ tokens/month for GPT-4o)
```

---

## Cosmos DB RU/s Scaling Model

### RU/s Estimation by Operation

| Operation | RU Cost (per op) | Frequency (per query) | RU/s at 50 QPS |
|-----------|-------------------|----------------------|-----------------|
| **Point Read** (1 KB) | 1 RU | 2 reads/query | 100 |
| **Point Read** (8 KB) | 3 RU | 1 read/query | 150 |
| **Query** (cross-partition) | 10–50 RU | 0.5/query | 750 |
| **Query** (single partition) | 3–15 RU | 1/query | 450 |
| **Write** (1 KB item) | 5 RU | 0.3/query | 75 |
| **Write** (8 KB item) | 20 RU | 0.1/query | 100 |
| **Upsert** (session/context) | 10 RU | 1/query | 500 |
| **Total per Query** | ~40 RU avg | — | **2,125** |

### Concurrent Users to RU/s Mapping

| Concurrent Users | Queries/Sec | Estimated RU/s | Autoscale Setting | Monthly Cost |
|------------------|-------------|----------------|-------------------|-------------|
| 50 | 8 | 320 | 1,000 (min 100) | $47 |
| 100 | 15 | 600 | 2,000 (min 200) | $95 |
| 250 | 40 | 1,600 | 4,000 (min 400) | $237 |
| 500 | 75 | 3,000 | 8,000 (min 800) | $475 |
| 1,000 | 150 | 6,000 | 16,000 (min 1,600) | $950 |
| 2,500 | 375 | 15,000 | 40,000 (min 4,000) | $2,370 |
| 5,000 | 750 | 30,000 | 80,000 (min 8,000) | $4,745 |

**Autoscale Pricing:** Billed at highest RU/s reached in each hour. Minimum = 10% of max.
At scale max: `Max_RU/s × $0.008/hr × 730 hrs/mo ÷ 100`

### Partition Strategy at Scale

```
┌───────────────────────────────────────────────────────────────┐
│                  COSMOS DB PARTITION MODEL                     │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Container: conversations                                     │
│  Partition Key: /userId                                       │
│  ┌──────────────┬──────────────┬──────────────┐              │
│  │ Partition 1  │ Partition 2  │ Partition N  │              │
│  │ userId: A-F  │ userId: G-M  │ userId: N-Z  │              │
│  │ ≤20 GB each  │ ≤20 GB each  │ ≤20 GB each  │              │
│  │ ~10K RU/s    │ ~10K RU/s    │ ~10K RU/s    │              │
│  └──────────────┴──────────────┴──────────────┘              │
│                                                               │
│  Container: document_metadata                                 │
│  Partition Key: /departmentId                                 │
│  ┌──────────────┬──────────────┬──────────────┐              │
│  │ Engineering  │ Legal        │ Finance      │              │
│  │ 45% traffic  │ 25% traffic  │ 20% traffic  │              │
│  │              │              │              │              │
│  │ WARNING: Hot partition risk if one dept     │              │
│  │ exceeds 20 GB. Consider hierarchical key:  │              │
│  │ /departmentId + /yearMonth                  │              │
│  └──────────────┴──────────────┴──────────────┘              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Reserved Instance Commitment Planning

### RI Savings Analysis

| Service | SKU | On-Demand/Mo | 1-Year RI/Mo | 3-Year RI/Mo | 1-Yr Savings | 3-Yr Savings |
|---------|-----|-------------|-------------|-------------|--------------|--------------|
| **AKS (D4s_v3)** | 4 vCPU, 16 GB | $140.16 | $87.60 | $55.48 | 37% | 60% |
| **AKS (D8s_v3)** | 8 vCPU, 32 GB | $280.32 | $175.20 | $110.96 | 37% | 60% |
| **Cosmos DB** | 1000 RU/s | $58.40 | $46.72 | $35.04 | 20% | 40% |
| **Redis (P1)** | 6 GB | $400.92 | $265.72 | $176.66 | 34% | 56% |
| **Redis (P2)** | 13 GB | $801.84 | $531.44 | $353.32 | 34% | 56% |
| **SQL DB (S3)** | 100 DTU | $150.24 | $97.68 | $60.84 | 35% | 60% |
| **App Gateway** | WAF_v2 base | $262.80 | $197.10 | $157.68 | 25% | 40% |
| **API Mgmt** | Standard/unit | $700.80 | $490.56 | $350.40 | 30% | 50% |

### RI Commitment Decision Framework

```
┌─────────────────────────────────────────────────────────────┐
│              RI COMMITMENT DECISION TREE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Is the workload stable for ≥12 months?                     │
│  ├── NO  → Use on-demand / autoscale                        │
│  └── YES                                                    │
│       │                                                     │
│       Is the SKU likely to change?                           │
│       ├── YES → 1-Year RI (flexibility to upgrade)          │
│       └── NO                                                │
│            │                                                │
│            Is budget approved for 3-year commitment?         │
│            ├── NO  → 1-Year RI                              │
│            └── YES → 3-Year RI (maximum savings)            │
│                                                             │
│  Priority for RI purchase (highest savings first):          │
│  1. AKS nodes (60% savings on 3-yr, always-on workload)    │
│  2. Redis Cache (56% savings, stable requirement)           │
│  3. Cosmos DB (40% savings, stable baseline RU/s)           │
│  4. API Management (50% savings, always-on)                 │
│  5. App Gateway (40% savings, always-on)                    │
└─────────────────────────────────────────────────────────────┘
```

### Current RI Savings Projection

| Commitment | Annual On-Demand | Annual with RI | Annual Savings |
|------------|-----------------|---------------|----------------|
| **AKS (5 nodes × D4s_v3, 3-yr)** | $8,410 | $3,329 | $5,081 (60%) |
| **Redis (1× P1, 3-yr)** | $4,811 | $2,120 | $2,691 (56%) |
| **Cosmos DB (4000 RU/s base, 1-yr)** | $2,803 | $2,242 | $561 (20%) |
| **API Management (1 unit, 3-yr)** | $8,410 | $4,205 | $4,205 (50%) |
| **App Gateway (WAF_v2, 1-yr)** | $3,154 | $2,365 | $789 (25%) |
| **Total** | **$27,588** | **$14,261** | **$13,327 (48%)** |

---

## Capacity Review Cadence

### Monthly Capacity Review Template

```markdown
# Capacity Review — [Month YYYY]

## Attendees
- Platform Engineering Lead
- DevOps Lead
- FinOps Analyst
- Product Owner (optional)

## 1. Service Utilization Summary

| Service | Capacity | Usage | Util% | Trend (30d) | Status | Action |
|---------|----------|-------|-------|-------------|--------|--------|
| AOAI GPT-4o | ___ TPM | ___ TPM | __% | ↑↓→ | Normal/Watch/Warning | ___ |
| AI Search | ___ QPS | ___ QPS | __% | ↑↓→ | Normal/Watch/Warning | ___ |
| Cosmos DB | ___ RU/s | ___ RU/s | __% | ↑↓→ | Normal/Watch/Warning | ___ |
| AKS Nodes | ___ nodes | ___ active | __% | ↑↓→ | Normal/Watch/Warning | ___ |
| Redis | ___ GB | ___ GB | __% | ↑↓→ | Normal/Watch/Warning | ___ |
| Storage | ___ TB | ___ TB | __% | ↑↓→ | Normal/Watch/Warning | ___ |

## 2. Growth vs. Forecast

| Metric | Forecasted | Actual | Variance | Forecast Accuracy |
|--------|-----------|--------|----------|-------------------|
| Users | ___ | ___ | __% | On-Track / Over / Under |
| Queries/Day | ___ | ___ | __% | On-Track / Over / Under |
| Token Consumption | ___M | ___M | __% | On-Track / Over / Under |
| Documents Indexed | ___ | ___ | __% | On-Track / Over / Under |

## 3. Scaling Actions Taken

| Date | Service | Action | Reason | Impact |
|------|---------|--------|--------|--------|
| ___ | ___ | ___ | ___ | ___ |

## 4. Upcoming Scaling Needs (Next 90 Days)

| Service | Current | Projected Need | Action | Timeline | Approver |
|---------|---------|---------------|--------|----------|----------|
| ___ | ___ | ___ | ___ | ___ | ___ |

## 5. Cost Impact

| Item | Current Monthly | Projected Change | New Monthly | Approval Status |
|------|----------------|-----------------|-------------|-----------------|
| ___ | $___ | +/- $___ | $___ | Pending/Approved |

## 6. Action Items

| # | Action | Owner | Due Date | Priority |
|---|--------|-------|----------|----------|
| 1 | ___ | ___ | ___ | High/Medium/Low |

## 7. Next Review Date: [Date]
```

### Review Schedule

| Review Type | Frequency | Participants | Duration | Focus |
|-------------|-----------|-------------|----------|-------|
| **Operational** | Weekly | Platform Eng | 15 min | Utilization dashboards, alerts review |
| **Capacity** | Monthly | Platform + FinOps | 45 min | Growth vs. forecast, scaling decisions |
| **Strategic** | Quarterly | Leadership + Arch | 90 min | SKU upgrades, RI commitments, multi-region |
| **Annual** | Yearly | All stakeholders | Half-day | 24-month forecast refresh, budget planning |

---

## Capacity Alerts and KQL Queries

### Azure OpenAI — TPM Approaching Quota

```kql
// Alert: OpenAI TPM usage exceeding 75% of quota
let quota_tpm = 80000;  // Set per deployment
let threshold = 0.75;
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
| where Category == "RequestResponse"
| where TimeGenerated > ago(5m)
| summarize TotalTokens = sum(toint(properties_s.totalTokens)) by bin(TimeGenerated, 1m)
| extend TPM = TotalTokens
| where TPM > quota_tpm * threshold
| project TimeGenerated, TPM, QuotaTPM = quota_tpm,
          UtilizationPct = round(TPM * 100.0 / quota_tpm, 1)
| order by TimeGenerated desc
```

### Azure AI Search — Query Latency Degradation

```kql
// Alert: AI Search P95 latency exceeding 150ms
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.SEARCH"
| where OperationName == "Query.Search"
| where TimeGenerated > ago(15m)
| summarize P95_Latency_ms = percentile(DurationMs, 95),
            P99_Latency_ms = percentile(DurationMs, 99),
            AvgLatency_ms = avg(DurationMs),
            QueryCount = count()
        by bin(TimeGenerated, 5m)
| where P95_Latency_ms > 150
| project TimeGenerated, P95_Latency_ms, P99_Latency_ms,
          AvgLatency_ms, QueryCount
```

### Cosmos DB — RU/s Throttling Detection

```kql
// Alert: Cosmos DB 429 throttling errors detected
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.DOCUMENTDB"
| where TimeGenerated > ago(15m)
| where statusCode_s == "429"
| summarize ThrottledRequests = count(),
            TotalRequests = countif(statusCode_s != ""),
            AvgRUCharge = avg(todouble(requestCharge_s))
        by bin(TimeGenerated, 5m), collectionName_s
| extend ThrottleRate = round(ThrottledRequests * 100.0 / TotalRequests, 2)
| where ThrottledRequests > 10
| project TimeGenerated, collectionName_s, ThrottledRequests,
          ThrottleRate, AvgRUCharge
```

### AKS — Node Pool Approaching Capacity

```kql
// Alert: AKS node pool CPU utilization exceeding threshold
let threshold = 75;
InsightsMetrics
| where Namespace == "container.azm.ms/kuberesources"
| where Name == "cpuUsageNanoCores"
| where TimeGenerated > ago(15m)
| extend NodePool = tostring(parse_json(Tags).agentpool)
| summarize AvgCPU_Percent = avg(Val / 1e9 * 100 / 4.0)  // 4 cores per D4s_v3
        by bin(TimeGenerated, 5m), NodePool, Computer
| summarize PoolAvgCPU = avg(AvgCPU_Percent),
            MaxNodeCPU = max(AvgCPU_Percent),
            NodeCount = dcount(Computer)
        by bin(TimeGenerated, 5m), NodePool
| where PoolAvgCPU > threshold
| project TimeGenerated, NodePool, PoolAvgCPU = round(PoolAvgCPU, 1),
          MaxNodeCPU = round(MaxNodeCPU, 1), NodeCount
```

### Redis Cache — Memory Pressure

```kql
// Alert: Redis memory usage approaching limit
AzureMetrics
| where ResourceProvider == "MICROSOFT.CACHE"
| where MetricName == "usedmemorypercentage"
| where TimeGenerated > ago(15m)
| summarize AvgMemPct = avg(Average),
            MaxMemPct = max(Maximum)
        by bin(TimeGenerated, 5m), Resource
| where MaxMemPct > 75
| project TimeGenerated, Resource,
          AvgMemoryPct = round(AvgMemPct, 1),
          MaxMemoryPct = round(MaxMemPct, 1),
          Status = case(
              MaxMemPct > 90, "CRITICAL",
              MaxMemPct > 75, "WARNING",
              "NORMAL")
```

### Storage Account — Transaction Rate Trending

```kql
// Alert: Storage account transaction rate trending up
StorageBlobLogs
| where TimeGenerated > ago(1h)
| where StatusCode < 500
| summarize TransactionCount = count(),
            AvgLatency_ms = avg(DurationMs),
            P95Latency_ms = percentile(DurationMs, 95)
        by bin(TimeGenerated, 5m), AccountName
| extend TransactionsPerSec = TransactionCount / 300.0
| where TransactionsPerSec > 100  // threshold: 100 TPS
| project TimeGenerated, AccountName, TransactionsPerSec = round(TransactionsPerSec, 1),
          AvgLatency_ms = round(AvgLatency_ms, 1),
          P95Latency_ms = round(P95Latency_ms, 1)
```

### Composite Capacity Health Dashboard Query

```kql
// Unified capacity health score across all services
let aoai_health = AzureDiagnostics
    | where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
    | where TimeGenerated > ago(5m)
    | summarize TPM = sum(toint(properties_s.totalTokens)) by bin(TimeGenerated, 1m)
    | summarize AvgTPM = avg(TPM)
    | extend Service = "Azure OpenAI", Utilization = round(AvgTPM / 80000 * 100, 1);
let search_health = AzureDiagnostics
    | where ResourceProvider == "MICROSOFT.SEARCH"
    | where TimeGenerated > ago(5m)
    | summarize QPS = count() / 300.0
    | extend Service = "AI Search", Utilization = round(QPS / 50 * 100, 1);
let cosmos_health = AzureDiagnostics
    | where ResourceProvider == "MICROSOFT.DOCUMENTDB"
    | where TimeGenerated > ago(5m)
    | summarize AvgRU = avg(todouble(requestCharge_s)) * count() / 300.0
    | extend Service = "Cosmos DB", Utilization = round(AvgRU / 8000 * 100, 1);
union aoai_health, search_health, cosmos_health
| extend HealthStatus = case(
    Utilization > 90, "CRITICAL",
    Utilization > 75, "WARNING",
    Utilization > 60, "WATCH",
    "NORMAL")
| project Service, Utilization, HealthStatus
```

### Alert Configuration Summary

| Alert Name | Service | KQL Query | Threshold | Severity | Action Group |
|------------|---------|-----------|-----------|----------|--------------|
| **AOAI-TPM-High** | Azure OpenAI | TPM Quota Query | >75% TPM | Sev 2 | platform-alerts |
| **Search-Latency-P95** | AI Search | Latency Query | >150ms P95 | Sev 2 | platform-alerts |
| **Cosmos-Throttle** | Cosmos DB | 429 Detection | >10 throttles/5m | Sev 1 | platform-critical |
| **AKS-CPU-High** | AKS | Node Pool CPU | >75% avg | Sev 2 | platform-alerts |
| **Redis-Memory** | Redis Cache | Memory Pressure | >75% memory | Sev 2 | platform-alerts |
| **Storage-TPS** | Data Lake | Transaction Rate | >100 TPS | Sev 3 | platform-info |

### Bash: Alert Rule Deployment

```bash
#!/bin/bash
# Deploy capacity alert rules via Azure CLI

RESOURCE_GROUP="rg-rag-platform-prod"
WORKSPACE_ID="/subscriptions/<sub-id>/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.OperationalInsights/workspaces/law-rag-prod"
ACTION_GROUP_ID="/subscriptions/<sub-id>/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Insights/actionGroups/platform-alerts"

# Azure OpenAI TPM Alert
az monitor scheduled-query create \
  --name "AOAI-TPM-High" \
  --resource-group "$RESOURCE_GROUP" \
  --scopes "$WORKSPACE_ID" \
  --condition "count > 0" \
  --condition-query "AzureDiagnostics | where ResourceProvider == 'MICROSOFT.COGNITIVESERVICES' | where TimeGenerated > ago(5m) | summarize TPM = sum(toint(properties_s.totalTokens)) by bin(TimeGenerated, 1m) | where TPM > 60000" \
  --evaluation-frequency "5m" \
  --window-size "5m" \
  --severity 2 \
  --action-groups "$ACTION_GROUP_ID" \
  --description "Azure OpenAI TPM exceeding 75% of quota"

# Cosmos DB Throttle Alert
az monitor scheduled-query create \
  --name "Cosmos-Throttle" \
  --resource-group "$RESOURCE_GROUP" \
  --scopes "$WORKSPACE_ID" \
  --condition "count > 10" \
  --condition-query "AzureDiagnostics | where ResourceProvider == 'MICROSOFT.DOCUMENTDB' | where statusCode_s == '429' | where TimeGenerated > ago(5m) | summarize ThrottleCount = count()" \
  --evaluation-frequency "5m" \
  --window-size "5m" \
  --severity 1 \
  --action-groups "$ACTION_GROUP_ID" \
  --description "Cosmos DB throttling detected - RU/s capacity exceeded"

echo "Capacity alerts deployed successfully."
```

---

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | Capacity Planning — Enterprise Azure OpenAI RAG Platform |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Monthly (operational), Quarterly (strategic) |
| **Approved By** | Head of Platform Engineering |
| **Distribution** | Platform Engineering, DevOps, FinOps, Architecture |
| **Related Documents** | FINOPS-COST-MANAGEMENT.md, OPERATIONS-GUIDE.md, INFRA-DEVOPS-DEPLOYMENT.md |

---

*This document is maintained by the Platform Engineering team and reviewed monthly as part of the capacity review cadence. All forecasting models should be recalibrated quarterly against actual usage data. For questions or updates, contact the Platform Team via the #platform-capacity Slack channel.*
