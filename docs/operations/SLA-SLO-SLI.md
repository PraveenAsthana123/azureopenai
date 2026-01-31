# SLA, SLO & SLI Framework — Azure OpenAI Enterprise RAG Platform

> Service Level Agreements, Objectives, and Indicators for enterprise AI reliability management.
> Aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF** governance standards.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Service Level Indicators (SLIs)](#2-service-level-indicators-slis)
3. [Service Level Objectives (SLOs)](#3-service-level-objectives-slos)
4. [Service Level Agreements (SLAs)](#4-service-level-agreements-slas)
5. [Compensation & Penalty Structure](#5-compensation--penalty-structure)
6. [Error Budget Framework](#6-error-budget-framework)
7. [Error Budget Burn Rate Alerts](#7-error-budget-burn-rate-alerts)
8. [Dependency SLAs](#8-dependency-slas)
9. [Composite SLA Calculation](#9-composite-sla-calculation)
10. [SLI Measurement — KQL Queries](#10-sli-measurement--kql-queries)
11. [Monthly SLA Reporting Template](#11-monthly-sla-reporting-template)
12. [SLA Exclusions](#12-sla-exclusions)
13. [SLA Review Cadence](#13-sla-review-cadence)
14. [Escalation on SLO Breach](#14-escalation-on-slo-breach)
15. [Document Control](#15-document-control)

---

## 1. Overview

This document defines the **Service Level Indicators (SLIs)**, **Service Level Objectives (SLOs)**, and **Service Level Agreements (SLAs)** for the Azure OpenAI Enterprise RAG Platform. The framework ensures measurable, enforceable reliability commitments across all platform tiers.

### 1.1 SLI / SLO / SLA Relationship

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SLA (Service Level Agreement)                    │
│   Contractual commitment between provider and consumer with penalties   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                  SLO (Service Level Objective)                   │   │
│   │   Internal reliability target — tighter than SLA                │   │
│   │                                                                 │   │
│   │   ┌─────────────────────────────────────────────────────────┐   │   │
│   │   │              SLI (Service Level Indicator)               │   │   │
│   │   │   Quantitative measure of a service dimension            │   │   │
│   │   │                                                         │   │   │
│   │   │   Examples:                                             │   │   │
│   │   │   • Availability  = successful requests / total         │   │   │
│   │   │   • Latency       = P95 response time in ms             │   │   │
│   │   │   • Error Rate    = 5xx responses / total responses     │   │   │
│   │   │   • Groundedness  = grounded tokens / total tokens      │   │   │
│   │   └─────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Guiding Principles

| Principle | Description |
|-----------|-------------|
| **Measurability** | Every SLI must be captured by Azure Monitor, Application Insights, or custom telemetry |
| **Transparency** | SLO dashboards are available to all engineering and product teams |
| **Accountability** | Each SLO has a named owner and escalation path |
| **Error Budgets** | Teams may ship features as long as error budget remains positive |
| **Continuous Improvement** | Quarterly reviews adjust targets based on historical data |

---

## 2. Service Level Indicators (SLIs)

### 2.1 SLI Definitions

SLIs are the **quantitative metrics** that describe a specific dimension of the platform's behavior. Each SLI maps to an observable signal collected from Azure Monitor, Application Insights, or custom instrumentation.

### 2.2 Availability SLI

| Attribute | Value |
|-----------|-------|
| **Metric Name** | `platform.availability` |
| **Formula** | `(Total Successful Requests / Total Valid Requests) x 100` |
| **Data Source** | Application Insights — `requests` table |
| **Successful Request** | HTTP status 2xx or 3xx |
| **Excluded** | Health-check probes, synthetic monitors |
| **Granularity** | 1-minute rolling window |
| **Aggregation** | Monthly percentage |

### 2.3 Latency SLIs

| Percentile | Metric Name | Description | Data Source |
|------------|-------------|-------------|-------------|
| **P50** | `platform.latency.p50` | Median response time | Application Insights `requests.duration` |
| **P95** | `platform.latency.p95` | 95th percentile response time | Application Insights `requests.duration` |
| **P99** | `platform.latency.p99` | 99th percentile response time | Application Insights `requests.duration` |
| **P50 (RAG)** | `rag.latency.p50` | Median end-to-end RAG query time | Custom telemetry |
| **P95 (RAG)** | `rag.latency.p95` | 95th percentile RAG query time | Custom telemetry |
| **P99 (RAG)** | `rag.latency.p99` | 99th percentile RAG query time | Custom telemetry |

### 2.4 Error Rate SLIs

| Error Class | Metric Name | Formula | Threshold |
|-------------|-------------|---------|-----------|
| **Client Errors (4xx)** | `platform.error_rate.4xx` | `count(4xx) / count(total)` | Informational — not counted against SLO |
| **Server Errors (5xx)** | `platform.error_rate.5xx` | `count(5xx) / count(total)` | Counted against SLO |
| **Timeout Errors** | `platform.error_rate.timeout` | `count(timeout) / count(total)` | Counted against SLO |
| **Dependency Errors** | `platform.error_rate.dependency` | `count(dep_failure) / count(total)` | Counted against SLO |

### 2.5 Throughput SLIs

| Metric Name | Formula | Unit | Data Source |
|-------------|---------|------|-------------|
| **`platform.throughput.qpm`** | Queries processed per minute | queries/min | Application Insights `requests` |
| **`platform.throughput.tpm`** | Tokens processed per minute | tokens/min | Azure OpenAI metrics |
| **`platform.throughput.docs_indexed`** | Documents indexed per hour | docs/hr | AI Search metrics |

### 2.6 AI Quality SLIs

| Metric Name | Formula | Range | Data Source |
|-------------|---------|-------|-------------|
| **`rag.quality.groundedness`** | Proportion of response grounded in retrieved context | 0.0 — 1.0 | Azure AI Content Safety / custom evaluator |
| **`rag.quality.hallucination_rate`** | Proportion of responses containing fabricated information | 0.0 — 1.0 | Custom LLM-as-judge evaluator |
| **`rag.quality.citation_accuracy`** | Proportion of citations that map to actual source passages | 0.0 — 1.0 | Custom citation validator |
| **`rag.quality.relevance`** | Semantic similarity between query intent and response | 0.0 — 1.0 | Embedding cosine similarity evaluator |
| **`rag.quality.coherence`** | Logical consistency and readability of response | 1 — 5 | LLM-as-judge (GPT-4o) |

---

## 3. Service Level Objectives (SLOs)

### 3.1 Platform SLO Targets

| SLI Category | Metric | Business Hours Target | Off-Hours Target | Measurement Window |
|-------------|--------|----------------------|------------------|--------------------|
| **Availability** | Uptime % | **99.9%** | **99.5%** | Monthly |
| **Latency** | P50 | ≤ 1.5s | ≤ 2.0s | Monthly |
| **Latency** | P95 | **≤ 3.0s** | ≤ 4.0s | Monthly |
| **Latency** | P99 | **≤ 5.0s** | ≤ 7.0s | Monthly |
| **Error Rate** | 5xx rate | **< 1.0%** | < 1.5% | Monthly |
| **Error Rate** | Timeout rate | < 0.5% | < 1.0% | Monthly |
| **Throughput** | Sustained QPM | ≥ 500 queries/min | ≥ 200 queries/min | Continuous |
| **Quality** | Groundedness | **≥ 0.80** | ≥ 0.80 | Weekly evaluation batch |
| **Quality** | Hallucination rate | ≤ 0.05 | ≤ 0.05 | Weekly evaluation batch |
| **Quality** | Citation accuracy | ≥ 0.85 | ≥ 0.85 | Weekly evaluation batch |

> **Business Hours** are defined as Monday–Friday, 06:00–22:00 UTC.
> **Off-Hours** are Saturday–Sunday and weekdays 22:00–06:00 UTC.

### 3.2 Per-Endpoint SLO Targets

| Endpoint | P95 Latency | Availability | Error Rate |
|----------|-------------|-------------|------------|
| **`/api/v1/chat`** (RAG query) | ≤ 3.0s | 99.9% | < 1.0% |
| **`/api/v1/search`** (hybrid search) | ≤ 1.5s | 99.9% | < 0.5% |
| **`/api/v1/embed`** (embedding) | ≤ 0.5s | 99.9% | < 0.5% |
| **`/api/v1/ingest`** (document ingestion) | ≤ 30.0s | 99.5% | < 2.0% |
| **`/api/v1/health`** (health check) | ≤ 0.2s | 99.99% | < 0.1% |

### 3.3 SLO Ownership

| SLO Domain | Owner | Backup | Escalation |
|------------|-------|--------|------------|
| **Availability** | Platform Engineering Lead | SRE Team | VP Engineering |
| **Latency** | Backend Engineering Lead | Platform Engineering | VP Engineering |
| **Error Rate** | SRE Team Lead | Platform Engineering | VP Engineering |
| **Throughput** | Infrastructure Lead | SRE Team | VP Engineering |
| **AI Quality** | ML Engineering Lead | AI Governance Board | CTO |

---

## 4. Service Level Agreements (SLAs)

### 4.1 SLA Tier Definitions

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SLA Tier Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌───────────────────┐                                             │
│   │     TIER 1        │  99.9% Availability                         │
│   │  Mission-Critical │  P95 ≤ 3s  │  Error Rate < 0.5%            │
│   │  24x7 Support     │  15-min response  │  4-hr resolution        │
│   └───────┬───────────┘                                             │
│           │                                                         │
│   ┌───────▼───────────┐                                             │
│   │     TIER 2        │  99.5% Availability                         │
│   │  Business         │  P95 ≤ 5s  │  Error Rate < 1.0%            │
│   │  12x5 Support     │  1-hr response  │  8-hr resolution          │
│   └───────┬───────────┘                                             │
│           │                                                         │
│   ┌───────▼───────────┐                                             │
│   │     TIER 3        │  99.0% Availability                         │
│   │  Internal / Dev   │  P95 ≤ 10s  │  Error Rate < 2.0%           │
│   │  Best Effort      │  4-hr response  │  Next business day        │
│   └───────────────────┘                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 SLA Tier Comparison

| Attribute | Tier 1 — Mission-Critical | Tier 2 — Business | Tier 3 — Internal |
|-----------|--------------------------|-------------------|-------------------|
| **Availability** | 99.9% | 99.5% | 99.0% |
| **P95 Latency** | ≤ 3.0s | ≤ 5.0s | ≤ 10.0s |
| **P99 Latency** | ≤ 5.0s | ≤ 8.0s | ≤ 15.0s |
| **Error Rate** | < 0.5% | < 1.0% | < 2.0% |
| **Support Window** | 24x7x365 | 12x5 (Business Hours) | Best Effort |
| **Initial Response** | 15 minutes | 1 hour | 4 hours |
| **Resolution Target** | 4 hours | 8 hours | Next business day |
| **Incident Manager** | Dedicated | Shared pool | On-call rotation |
| **Monitoring** | Real-time + proactive | Real-time | Periodic |
| **Maintenance Window** | Pre-approved, rolling | Scheduled, notified 48 hrs | Standard window |
| **Typical Consumers** | Customer-facing RAG apps, Copilot integrations | Internal business tools, analytics dashboards | Dev/test, sandbox, experimentation |

### 4.3 SLA Coverage by Environment

| Environment | SLA Tier | Availability Target | Support Level |
|-------------|----------|--------------------:|---------------|
| **Production** | Tier 1 | 99.9% | 24x7 |
| **Staging** | Tier 3 | 99.0% | Best Effort |
| **Development** | None | No SLA | Best Effort |
| **Sandbox** | None | No SLA | Self-service |

---

## 5. Compensation & Penalty Structure

### 5.1 Service Credit Schedule — Tier 1 (Mission-Critical)

| Monthly Uptime % | Service Credit (% of monthly invoice) |
|------------------:|--------------------------------------:|
| 99.9% — 100% | 0% (SLA met) |
| 99.0% — 99.89% | **10%** |
| 95.0% — 98.99% | **25%** |
| 90.0% — 94.99% | **50%** |
| < 90.0% | **100%** |

### 5.2 Service Credit Schedule — Tier 2 (Business)

| Monthly Uptime % | Service Credit (% of monthly invoice) |
|------------------:|--------------------------------------:|
| 99.5% — 100% | 0% (SLA met) |
| 99.0% — 99.49% | **10%** |
| 95.0% — 98.99% | **20%** |
| 90.0% — 94.99% | **35%** |
| < 90.0% | **50%** |

### 5.3 Service Credit Schedule — Tier 3 (Internal)

| Monthly Uptime % | Service Credit (% of monthly invoice) |
|------------------:|--------------------------------------:|
| 99.0% — 100% | 0% (SLA met) |
| 95.0% — 98.99% | **10%** |
| 90.0% — 94.99% | **20%** |
| < 90.0% | **30%** |

### 5.4 Credit Claim Process

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Consumer     │     │  SRE Team    │     │  Finance     │     │  Consumer    │
│  Files Claim  │────▶│  Validates   │────▶│  Approves    │────▶│  Credit      │
│  (within 30d) │     │  SLI Data    │     │  Credit      │     │  Applied     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     Day 0               Day 1-3             Day 4-7             Day 8-14
```

> **Note:** Service credits must be claimed within **30 calendar days** of the incident month.
> Credits are capped at **100% of the monthly invoice** for the affected service.

---

## 6. Error Budget Framework

### 6.1 Error Budget Concept

The **error budget** is the maximum amount of unreliability the platform can tolerate within a measurement window while still meeting its SLO. It quantifies the acceptable failure margin and governs the balance between feature velocity and reliability investment.

```
Error Budget = 1 - SLO Target

Example (99.9% availability):
  Error Budget = 1 - 0.999 = 0.001 = 0.1%
  In a 30-day month (43,200 minutes):
    Allowed downtime = 43,200 x 0.001 = 43.2 minutes
```

### 6.2 Error Budget by SLA Tier

| SLA Tier | Availability Target | Error Budget (%) | Allowed Downtime / Month | Allowed Downtime / Quarter |
|----------|--------------------:|------------------:|-------------------------:|---------------------------:|
| **Tier 1** | 99.9% | 0.1% | **43.2 min** | 129.6 min |
| **Tier 2** | 99.5% | 0.5% | **216.0 min** (3.6 hrs) | 648.0 min (10.8 hrs) |
| **Tier 3** | 99.0% | 1.0% | **432.0 min** (7.2 hrs) | 1,296.0 min (21.6 hrs) |

### 6.3 Error Budget Calculation Examples

**Example 1 — Tier 1, Month of January (31 days = 44,640 minutes)**

```
Total minutes in January:  44,640
SLO Target:                99.9%
Error Budget:              44,640 x 0.001 = 44.64 minutes

Incidents this month:
  - Jan 5:  API gateway restart       =  3.0 min
  - Jan 12: CosmosDB throttling       =  8.5 min
  - Jan 22: OpenAI regional failover  = 12.0 min
                              Total   = 23.5 min

Budget consumed:  23.5 / 44.64 = 52.6%
Budget remaining: 21.14 minutes (47.4%)
Status:           WITHIN BUDGET
```

**Example 2 — Tier 1, Month of February (28 days = 40,320 minutes)**

```
Total minutes in February:  40,320
SLO Target:                 99.9%
Error Budget:               40,320 x 0.001 = 40.32 minutes

Incidents this month:
  - Feb 3:  Certificate expiry outage  = 25.0 min
  - Feb 14: AKS node pool failure      = 18.0 min
                               Total   = 43.0 min

Budget consumed:  43.0 / 40.32 = 106.6%
Budget remaining: -2.68 minutes (EXCEEDED)
Status:           BUDGET EXHAUSTED — freeze feature deployments
```

### 6.4 Error Budget Policy

| Budget Remaining | Status | Action |
|-----------------:|--------|--------|
| > 50% | **Healthy** | Normal feature velocity; standard deployment cadence |
| 25% — 50% | **Caution** | Increased review for risky changes; additional canary coverage |
| 10% — 25% | **Warning** | Feature freeze for non-critical changes; reliability sprint |
| 0% — 10% | **Critical** | Full feature freeze; all engineering on reliability |
| Exhausted (< 0%) | **Exhausted** | Emergency reliability mode; post-mortem required; SLA review triggered |

---

## 7. Error Budget Burn Rate Alerts

### 7.1 Burn Rate Concept

**Burn rate** measures how quickly the error budget is being consumed relative to the measurement window. A burn rate of **1.0** means the budget will be exactly exhausted by end of month. A burn rate of **14.4** means the entire monthly budget will be consumed in **1 hour**.

```
Burn Rate = (Error Rate Observed / Error Budget Rate)

Where:
  Error Budget Rate = (1 - SLO) / measurement_window_hours

For 99.9% SLO over 30 days (720 hours):
  Error Budget Rate = 0.001 / 720 = 0.00000139 per hour

If observed error rate = 2% of budget in 1 hour:
  Burn Rate = 0.02 / (1/720) = 14.4x
```

### 7.2 Burn Rate Alert Thresholds

| Alert Severity | Burn Rate | Budget Consumed | Time to Exhaustion | Lookback Window |
|----------------|----------:|----------------:|-------------------:|----------------:|
| **Critical (P1)** | ≥ 14.4x | **2% in 1 hour** | ~50 minutes | 5 min + 1 hr |
| **High (P2)** | ≥ 6.0x | **5% in 6 hours** | ~5 hours | 30 min + 6 hr |
| **Medium (P3)** | ≥ 3.0x | **10% in 3 days** | ~10 days | 2 hr + 3 days |
| **Low (P4)** | ≥ 1.0x | **100% projected over month** | ≤ 30 days | 6 hr + 30 days |

### 7.3 Multi-Window Burn Rate Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Multi-Window Burn Rate Alerts                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Short Window (fast detection)    Long Window (sustained signal)        │
│  ┌─────────┐                      ┌──────────────┐                     │
│  │  5 min  │ ──── AND ──────────▶ │   1 hour     │ ──▶ P1 Alert       │
│  └─────────┘                      └──────────────┘                     │
│                                                                         │
│  ┌─────────┐                      ┌──────────────┐                     │
│  │  30 min │ ──── AND ──────────▶ │   6 hours    │ ──▶ P2 Alert       │
│  └─────────┘                      └──────────────┘                     │
│                                                                         │
│  ┌─────────┐                      ┌──────────────┐                     │
│  │  2 hrs  │ ──── AND ──────────▶ │   3 days     │ ──▶ P3 Alert       │
│  └─────────┘                      └──────────────┘                     │
│                                                                         │
│  Both windows must fire to trigger alert (reduces false positives)      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Alert Routing

| Severity | Notification Channel | Responder | Auto-Escalation |
|----------|---------------------|-----------|-----------------|
| **P1 — Critical** | PagerDuty + Teams (War Room) + SMS | On-call SRE + Incident Commander | VP Engineering at 30 min |
| **P2 — High** | PagerDuty + Teams | On-call SRE | Engineering Manager at 2 hrs |
| **P3 — Medium** | Teams + Email | SRE queue | Team Lead at 24 hrs |
| **P4 — Low** | Email + Dashboard | Weekly review queue | None |

---

## 8. Dependency SLAs

### 8.1 Azure Service SLAs

| Azure Service | Published SLA | Our Tier | Region Config | Effective SLA |
|---------------|:------------:|:--------:|---------------|:-------------:|
| **Azure OpenAI Service** | 99.9% | S0 | East US + West US (failover) | 99.9% |
| **Azure Cosmos DB** | 99.999% | Multi-region write | East US + West US | 99.999% |
| **Azure AI Search** | 99.9% | Standard S1, 2+ replicas | East US | 99.9% |
| **Azure Kubernetes Service (AKS)** | 99.95% | Standard tier, Uptime SLA | East US | 99.95% |
| **Azure API Management** | 99.95% | Standard | East US | 99.95% |
| **Azure Key Vault** | 99.99% | Standard | East US | 99.99% |
| **Azure Blob Storage (RA-GRS)** | 99.99% | RA-GRS | East US + paired | 99.99% |
| **Azure Cache for Redis** | 99.9% | Premium P1 | East US | 99.9% |
| **Azure Monitor / App Insights** | 99.9% | — | East US | 99.9% |
| **Azure Active Directory (Entra ID)** | 99.99% | — | Global | 99.99% |

### 8.2 Dependency Criticality Matrix

| Dependency | Criticality | Failure Impact | Fallback Strategy |
|------------|:-----------:|----------------|-------------------|
| **Azure OpenAI** | **Critical** | RAG queries fail completely | Failover to secondary region; cache recent responses |
| **Cosmos DB** | **Critical** | Conversation history and metadata unavailable | Multi-region write; local cache for reads |
| **AI Search** | **Critical** | Document retrieval fails | Degrade to keyword search; serve cached results |
| **AKS** | **Critical** | All API endpoints unavailable | Multi-zone node pools; pod disruption budgets |
| **API Management** | **High** | External API access blocked | Direct AKS ingress fallback |
| **Key Vault** | **High** | Secret/cert rotation fails | Local secret cache (short TTL) |
| **Blob Storage** | **Medium** | Document ingestion paused | Queue ingestion for retry |
| **Redis Cache** | **Medium** | Increased latency, DB load | Bypass cache; serve from Cosmos DB directly |

---

## 9. Composite SLA Calculation

### 9.1 Serial Dependency Model

When services are in **series** (each must be available for the platform to function), the composite SLA is the product of individual SLAs.

```
Composite SLA = SLA_1 x SLA_2 x SLA_3 x ... x SLA_n
```

### 9.2 Platform Critical Path

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   API    │    │   AKS    │    │    AI    │    │  Azure   │    │  Cosmos  │
│ Mgmt     │───▶│ Cluster  │───▶│  Search  │───▶│  OpenAI  │───▶│    DB    │
│ 99.95%   │    │ 99.95%   │    │ 99.9%    │    │ 99.9%    │    │ 99.999%  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘

Composite SLA (serial) = 0.9995 x 0.9995 x 0.999 x 0.999 x 0.99999
                       = 0.99699 ≈ 99.70%
```

### 9.3 Improving Composite SLA with Redundancy

Adding **redundancy** (parallel paths) improves the composite SLA for individual components:

```
Redundant SLA = 1 - (1 - SLA_primary) x (1 - SLA_secondary)

Example — Azure OpenAI with regional failover:
  Primary region:   99.9%
  Secondary region: 99.9%
  Effective SLA = 1 - (1 - 0.999) x (1 - 0.999)
                = 1 - 0.001 x 0.001
                = 1 - 0.000001
                = 99.9999%
```

### 9.4 Adjusted Composite SLA (with Redundancy)

| Component | Base SLA | Redundancy | Effective SLA |
|-----------|:--------:|------------|:-------------:|
| **API Management** | 99.95% | None (single instance) | 99.95% |
| **AKS** | 99.95% | Multi-zone node pools | 99.9975% |
| **AI Search** | 99.9% | 2 replicas | 99.99% |
| **Azure OpenAI** | 99.9% | Dual-region failover | 99.9999% |
| **Cosmos DB** | 99.999% | Multi-region write | 99.9999999% |

```
Adjusted Composite = 0.9995 x 0.999975 x 0.9999 x 0.999999 x 0.999999999
                   ≈ 0.99940 ≈ 99.94%
```

> **Result:** With redundancy applied, the platform achieves an effective composite SLA of **~99.94%**, well within the Tier 1 target of 99.9%.

---

## 10. SLI Measurement — KQL Queries

### 10.1 Availability SLI

```kusto
// Availability — Percentage of successful requests (excluding health checks)
let startTime = ago(30d);
let endTime = now();
requests
| where timestamp between (startTime .. endTime)
| where name !contains "health" and name !contains "ping"
| summarize
    TotalRequests = count(),
    SuccessfulRequests = countif(resultCode startswith "2" or resultCode startswith "3"),
    FailedRequests = countif(resultCode startswith "5")
| extend Availability = round(100.0 * SuccessfulRequests / TotalRequests, 4)
| project TotalRequests, SuccessfulRequests, FailedRequests, Availability
```

### 10.2 Latency Percentiles SLI

```kusto
// Latency percentiles — P50, P95, P99 by endpoint
let startTime = ago(30d);
requests
| where timestamp > startTime
| where name !contains "health"
| summarize
    P50 = percentile(duration, 50),
    P95 = percentile(duration, 95),
    P99 = percentile(duration, 99),
    Count = count()
    by bin(timestamp, 1h), name
| order by timestamp desc
```

### 10.3 Error Rate SLI

```kusto
// Error rate breakdown by class (4xx vs 5xx) — rolling 1-hour windows
requests
| where timestamp > ago(24h)
| summarize
    Total = count(),
    Client4xx = countif(toint(resultCode) >= 400 and toint(resultCode) < 500),
    Server5xx = countif(toint(resultCode) >= 500),
    Timeouts = countif(resultCode == "408" or duration > 30000)
    by bin(timestamp, 1h)
| extend
    ErrorRate4xx = round(100.0 * Client4xx / Total, 2),
    ErrorRate5xx = round(100.0 * Server5xx / Total, 2),
    TimeoutRate = round(100.0 * Timeouts / Total, 2)
| order by timestamp desc
```

### 10.4 Throughput SLI

```kusto
// Throughput — queries per minute over the last 24 hours
requests
| where timestamp > ago(24h)
| where name !contains "health"
| summarize QPM = count() by bin(timestamp, 1m)
| summarize
    AvgQPM = round(avg(QPM), 1),
    MaxQPM = max(QPM),
    MinQPM = min(QPM),
    P95QPM = round(percentile(QPM, 95), 1)
```

### 10.5 Error Budget Burn Rate

```kusto
// Error budget burn rate — multi-window (Tier 1: 99.9% SLO)
let sloTarget = 0.999;
let monthlyMinutes = 43200.0;
let errorBudgetMinutes = monthlyMinutes * (1.0 - sloTarget); // 43.2 min
// Short window: last 1 hour
let shortWindow =
    requests
    | where timestamp > ago(1h)
    | summarize
        Total = count(),
        Errors = countif(toint(resultCode) >= 500)
    | extend ShortErrorRate = 1.0 * Errors / Total;
// Long window: last 24 hours
let longWindow =
    requests
    | where timestamp > ago(24h)
    | summarize
        Total = count(),
        Errors = countif(toint(resultCode) >= 500)
    | extend LongErrorRate = 1.0 * Errors / Total;
shortWindow
| extend ShortBurnRate = round(ShortErrorRate / (1.0 - sloTarget), 2)
| join kind=inner (
    longWindow
    | extend LongBurnRate = round(LongErrorRate / (1.0 - sloTarget), 2)
) on $left.Total == $right.Total
| project
    ShortWindowErrorRate = round(ShortErrorRate * 100, 3),
    ShortBurnRate,
    LongWindowErrorRate = round(LongErrorRate * 100, 3),
    LongBurnRate,
    AlertSeverity = case(
        ShortBurnRate >= 14.4 and LongBurnRate >= 14.4, "P1-Critical",
        ShortBurnRate >= 6.0 and LongBurnRate >= 6.0, "P2-High",
        ShortBurnRate >= 3.0 and LongBurnRate >= 3.0, "P3-Medium",
        LongBurnRate >= 1.0, "P4-Low",
        "OK"
    )
```

### 10.6 SLO Compliance Dashboard Query

```kusto
// Monthly SLO compliance summary
let startOfMonth = startofmonth(now());
let endOfMonth = endofmonth(now());
requests
| where timestamp between (startOfMonth .. endOfMonth)
| where name !contains "health"
| summarize
    TotalRequests = count(),
    SuccessfulRequests = countif(resultCode startswith "2" or resultCode startswith "3"),
    P50Latency = round(percentile(duration, 50), 0),
    P95Latency = round(percentile(duration, 95), 0),
    P99Latency = round(percentile(duration, 99), 0),
    Server5xx = countif(toint(resultCode) >= 500)
| extend
    Availability = round(100.0 * SuccessfulRequests / TotalRequests, 4),
    ErrorRate = round(100.0 * Server5xx / TotalRequests, 4)
| extend
    AvailabilitySLO = iff(Availability >= 99.9, "PASS", "FAIL"),
    P95LatencySLO = iff(P95Latency <= 3000, "PASS", "FAIL"),
    P99LatencySLO = iff(P99Latency <= 5000, "PASS", "FAIL"),
    ErrorRateSLO = iff(ErrorRate < 1.0, "PASS", "FAIL")
| project
    Availability, AvailabilitySLO,
    P50Latency, P95Latency, P95LatencySLO,
    P99Latency, P99LatencySLO,
    ErrorRate, ErrorRateSLO
```

### 10.7 AI Quality SLI — Groundedness

```kusto
// Groundedness score — weekly evaluation results
customEvents
| where timestamp > ago(7d)
| where name == "rag_evaluation_result"
| extend
    groundedness = todouble(customDimensions["groundedness_score"]),
    hallucination = todouble(customDimensions["hallucination_detected"]),
    citationAccuracy = todouble(customDimensions["citation_accuracy"])
| summarize
    AvgGroundedness = round(avg(groundedness), 3),
    AvgCitationAccuracy = round(avg(citationAccuracy), 3),
    HallucinationRate = round(avg(hallucination), 4),
    EvaluationCount = count()
| extend
    GroundednessSLO = iff(AvgGroundedness >= 0.80, "PASS", "FAIL"),
    HallucinationSLO = iff(HallucinationRate <= 0.05, "PASS", "FAIL"),
    CitationSLO = iff(AvgCitationAccuracy >= 0.85, "PASS", "FAIL")
```

---

## 11. Monthly SLA Reporting Template

### 11.1 Report Header

| Field | Value |
|-------|-------|
| **Report Period** | YYYY-MM |
| **Generated On** | YYYY-MM-DD HH:MM UTC |
| **Generated By** | Automated / SRE Team |
| **Distribution** | Platform Team, Engineering Management, SLA Stakeholders |
| **Classification** | Internal |

### 11.2 Executive Summary Table

| KPI | Target | Actual | Status | Trend |
|-----|-------:|-------:|--------|-------|
| **Availability** | 99.90% | ___.___% | PASS / FAIL | Up / Down / Stable |
| **P50 Latency** | ≤ 1,500 ms | _____ ms | PASS / FAIL | Up / Down / Stable |
| **P95 Latency** | ≤ 3,000 ms | _____ ms | PASS / FAIL | Up / Down / Stable |
| **P99 Latency** | ≤ 5,000 ms | _____ ms | PASS / FAIL | Up / Down / Stable |
| **Error Rate (5xx)** | < 1.00% | ___.___% | PASS / FAIL | Up / Down / Stable |
| **Throughput (Avg QPM)** | ≥ 500 | _____ | PASS / FAIL | Up / Down / Stable |
| **Groundedness** | ≥ 0.80 | _.__ | PASS / FAIL | Up / Down / Stable |
| **Hallucination Rate** | ≤ 0.05 | _.__ | PASS / FAIL | Up / Down / Stable |
| **Citation Accuracy** | ≥ 0.85 | _.__ | PASS / FAIL | Up / Down / Stable |

### 11.3 Error Budget Consumption

| Tier | Monthly Budget | Consumed | Remaining | Status |
|------|---------------:|---------:|----------:|--------|
| **Tier 1** | 43.2 min | ___ min | ___ min | Healthy / Caution / Warning / Critical |
| **Tier 2** | 216.0 min | ___ min | ___ min | Healthy / Caution / Warning / Critical |
| **Tier 3** | 432.0 min | ___ min | ___ min | Healthy / Caution / Warning / Critical |

### 11.4 Incident Log

| Incident ID | Date | Duration | Root Cause | Services Affected | Error Budget Impact |
|-------------|------|----------|------------|-------------------|--------------------:|
| INC-YYYY-001 | YYYY-MM-DD | __ min | ___ | ___ | __ min |
| INC-YYYY-002 | YYYY-MM-DD | __ min | ___ | ___ | __ min |
| **Total** | | **__ min** | | | **__ min** |

### 11.5 Dependency Health

| Dependency | Published SLA | Observed Availability | Incidents | Status |
|------------|:------------:|----------------------:|:---------:|--------|
| **Azure OpenAI** | 99.9% | ___.___% | _ | OK / Degraded |
| **Cosmos DB** | 99.999% | ___.___% | _ | OK / Degraded |
| **AI Search** | 99.9% | ___.___% | _ | OK / Degraded |
| **AKS** | 99.95% | ___.___% | _ | OK / Degraded |
| **API Management** | 99.95% | ___.___% | _ | OK / Degraded |
| **Key Vault** | 99.99% | ___.___% | _ | OK / Degraded |

### 11.6 Action Items from Report

| # | Action | Owner | Due Date | Priority | Status |
|---|--------|-------|----------|----------|--------|
| 1 | ___ | ___ | YYYY-MM-DD | High / Medium / Low | Open / In Progress / Closed |
| 2 | ___ | ___ | YYYY-MM-DD | High / Medium / Low | Open / In Progress / Closed |
| 3 | ___ | ___ | YYYY-MM-DD | High / Medium / Low | Open / In Progress / Closed |

---

## 12. SLA Exclusions

### 12.1 Excluded Events

The following events are **excluded** from SLA availability calculations:

| Exclusion Category | Description | Documentation Requirement |
|--------------------|-------------|---------------------------|
| **Scheduled Maintenance** | Pre-announced maintenance windows with ≥ 48-hour notice (Tier 1) or ≥ 24-hour notice (Tier 2/3) | Change request ticket; notification evidence |
| **Force Majeure** | Natural disasters, war, government actions, pandemics, widespread internet outages | Incident report citing external cause |
| **Customer-Caused Issues** | Misuse of API, exceeding documented rate limits, invalid request patterns | Request logs demonstrating customer fault |
| **Third-Party Outages** | Azure region-wide outages confirmed by Microsoft Azure Status page | Azure incident ID; RCA from Microsoft |
| **Pre-Production Environments** | All activity in dev, staging, sandbox environments | Environment tag in telemetry |
| **Alpha/Beta Features** | Functionality explicitly marked as preview or experimental | Feature flag documentation |

### 12.2 Maintenance Window Schedule

| Window | Day | Time (UTC) | Duration | Tier 1 Impact | Notification |
|--------|-----|-----------|----------|:-------------:|:------------:|
| **Standard** | Sunday | 02:00 — 06:00 | 4 hours | Zero-downtime rolling | 48 hrs |
| **Emergency** | Any | As needed | ≤ 2 hours | Possible brief outage | Best effort |
| **Major Upgrade** | Quarterly | Saturday 22:00 — Sunday 06:00 | 8 hours | Planned failover | 2 weeks |

### 12.3 Exclusion Request Process

```yaml
# Exclusion Request Template
exclusion_request:
  incident_id: "INC-2024-042"
  requested_by: "sre-team@contoso.com"
  exclusion_type: "scheduled_maintenance"  # or: force_majeure, customer_caused, third_party
  start_time: "2024-01-14T02:00:00Z"
  end_time: "2024-01-14T04:30:00Z"
  duration_minutes: 150
  justification: |
    Scheduled AKS node pool upgrade from 1.28 to 1.29.
    Change request CR-2024-015 approved by CAB on 2024-01-10.
    48-hour notification sent via Teams and email.
  evidence:
    - change_request: "CR-2024-015"
    - notification_timestamp: "2024-01-12T02:00:00Z"
    - notification_channel: "teams, email"
  approved_by: ""
  approval_date: ""
```

---

## 13. SLA Review Cadence

### 13.1 Review Schedule

| Review Type | Frequency | Participants | Output |
|-------------|-----------|-------------|--------|
| **Daily SLI Check** | Daily (automated) | SRE on-call | Dashboard update; alert if anomaly |
| **Weekly SLO Review** | Weekly (Monday) | SRE Team + Engineering Leads | Weekly status report; burn rate analysis |
| **Monthly SLA Report** | Monthly (1st business day) | SRE + Engineering Management + Product | Monthly SLA report (Section 11 template) |
| **Quarterly SLA Review** | Quarterly | SRE + Architecture + VP Engineering + Stakeholders | SLO target adjustments; SLA renegotiation |
| **Annual SLA Audit** | Annually | All above + Legal + Finance + CISO | Full SLA framework review; contractual updates |

### 13.2 Quarterly Review Agenda

| # | Topic | Duration | Owner |
|---|-------|----------|-------|
| 1 | Previous quarter SLA performance summary | 15 min | SRE Lead |
| 2 | Error budget consumption trend analysis | 15 min | SRE Lead |
| 3 | Dependency SLA variance report | 10 min | Infrastructure Lead |
| 4 | AI quality metrics trend (groundedness, hallucination) | 10 min | ML Engineering Lead |
| 5 | Proposed SLO target adjustments | 15 min | Architecture Lead |
| 6 | Upcoming changes impacting SLA (new features, migrations) | 10 min | Product Manager |
| 7 | Action items and next steps | 15 min | All |
| | **Total** | **90 min** | |

### 13.3 SLO Adjustment Criteria

| Trigger | Action | Approval Required |
|---------|--------|-------------------|
| SLO exceeded for 3 consecutive months (> 99.95% when target is 99.9%) | Consider tightening SLO | Engineering Manager |
| SLO missed for 2 consecutive months | Root cause analysis; adjust if target is unrealistic | VP Engineering |
| New dependency added to critical path | Recalculate composite SLA; adjust if needed | Architecture Board |
| Significant traffic growth (> 50% QoQ) | Review throughput SLOs and capacity | Infrastructure Lead |
| AI model upgrade (e.g., GPT-4o to next gen) | Re-baseline quality SLIs | ML Engineering Lead + AI Governance Board |

---

## 14. Escalation on SLO Breach

### 14.1 Escalation Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        SLO Breach Escalation Flow                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  SLO Breach  │    │  On-Call SRE  │    │  Incident    │                  │
│  │  Detected    │───▶│  Paged       │───▶│  Declared    │                  │
│  │  (automated) │    │  (< 5 min)   │    │  (< 15 min)  │                  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                      ┌───────────────────────────┼────────────────┐         │
│                      │                           │                │         │
│               ┌──────▼──────┐             ┌──────▼──────┐  ┌─────▼──────┐  │
│               │  Severity 1 │             │  Severity 2 │  │ Severity 3 │  │
│               │  (Tier 1    │             │  (Tier 2    │  │ (Tier 3    │  │
│               │   breach)   │             │   breach)   │  │  breach)   │  │
│               └──────┬──────┘             └──────┬──────┘  └─────┬──────┘  │
│                      │                           │               │          │
│  ┌───────────────────▼──┐          ┌─────────────▼──┐  ┌────────▼───────┐  │
│  │ War Room activated   │          │ Eng Manager    │  │ Team Lead      │  │
│  │ VP Eng notified      │          │ notified       │  │ notified       │  │
│  │ Exec bridge if > 1hr │          │ at 2 hrs       │  │ next bus. day  │  │
│  └──────────┬───────────┘          └────────┬───────┘  └────────┬───────┘  │
│             │                               │                   │           │
│             ▼                               ▼                   ▼           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      Post-Incident Review                            │   │
│  │  • Blameless post-mortem within 48 hours                             │   │
│  │  • Action items tracked in engineering backlog                       │   │
│  │  • Error budget impact documented                                    │   │
│  │  • SLO adjustment considered if systemic                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 14.2 Escalation Matrix

| Condition | Time Elapsed | Escalation To | Action |
|-----------|:------------:|---------------|--------|
| **SLO breach detected** | 0 min | On-call SRE | Acknowledge; begin investigation |
| **Incident not acknowledged** | 15 min | Secondary on-call | Page secondary; notify manager |
| **Tier 1 — no mitigation** | 30 min | VP Engineering | Executive awareness; resource allocation |
| **Tier 1 — ongoing > 1 hr** | 60 min | CTO + Exec Team | Executive bridge call; customer comms drafted |
| **Tier 1 — ongoing > 4 hrs** | 240 min | CEO (briefing) | External customer communication; legal review |
| **Tier 2 — no mitigation** | 2 hrs | Engineering Manager | Additional resources assigned |
| **Tier 2 — ongoing > 8 hrs** | 8 hrs | VP Engineering | Escalate to Tier 1 treatment |
| **Tier 3 — no mitigation** | Next business day | Team Lead | Prioritize in sprint |

### 14.3 Post-Incident Requirements

| Severity | Post-Mortem Required | Deadline | Distribution |
|----------|:-------------------:|----------|-------------|
| **Sev 1** | Yes (mandatory) | 48 hours | Engineering-wide + stakeholders |
| **Sev 2** | Yes (mandatory) | 5 business days | Team + management |
| **Sev 3** | Optional | 10 business days | Team only |

### 14.4 Post-Mortem Template (JSON Schema)

```json
{
  "incident_id": "INC-2024-042",
  "title": "RAG API latency degradation due to AI Search index corruption",
  "severity": 1,
  "duration_minutes": 37,
  "error_budget_impact_minutes": 37,
  "timeline": [
    {"time": "2024-01-15T14:22:00Z", "event": "P1 burn rate alert fired"},
    {"time": "2024-01-15T14:25:00Z", "event": "On-call SRE acknowledged"},
    {"time": "2024-01-15T14:30:00Z", "event": "Root cause identified: corrupted search index"},
    {"time": "2024-01-15T14:45:00Z", "event": "Failover to replica index initiated"},
    {"time": "2024-01-15T14:59:00Z", "event": "Service restored; monitoring confirmed"}
  ],
  "root_cause": "AI Search index corruption during scheduled re-indexing due to concurrent write conflict",
  "impact": {
    "availability_loss_percent": 0.026,
    "affected_requests": 2847,
    "affected_users": 412
  },
  "action_items": [
    {
      "id": "AI-001",
      "action": "Implement index versioning with blue-green swap",
      "owner": "search-team",
      "priority": "P1",
      "due_date": "2024-02-01"
    },
    {
      "id": "AI-002",
      "action": "Add pre-swap index validation check",
      "owner": "sre-team",
      "priority": "P1",
      "due_date": "2024-01-25"
    }
  ],
  "lessons_learned": [
    "Index re-indexing must be performed with write locks to prevent concurrent corruption",
    "Replica index should be validated before promotion to primary"
  ]
}
```

---

## 15. Document Control

| Field | Value |
|-------|-------|
| **Document Title** | SLA, SLO & SLI Framework |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Next Review** | 2024-04 |
| **Approved By** | VP Engineering, Architecture Board |

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01 | Platform Team | Initial release |

---

> **End of Document** — SLA, SLO & SLI Framework for Azure OpenAI Enterprise RAG Platform
