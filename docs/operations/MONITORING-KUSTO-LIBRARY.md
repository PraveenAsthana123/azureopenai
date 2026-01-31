# Monitoring & Observability — KQL Query Library

> **Production-Grade Kusto Query Language Reference for Azure OpenAI RAG Platform Observability**
> Aligned with CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF

---

## Table of Contents

1. [Overview](#overview)
2. [Latency Analysis](#1-latency-analysis)
3. [Error Analysis](#2-error-analysis)
4. [Token Consumption](#3-token-consumption)
5. [Cache Performance](#4-cache-performance)
6. [RAG Quality Metrics](#5-rag-quality-metrics)
7. [User Analytics](#6-user-analytics)
8. [Security Monitoring](#7-security-monitoring)
9. [Cost Tracking](#8-cost-tracking)
10. [Search Performance](#9-search-performance)
11. [Infrastructure Health](#10-infrastructure-health)
12. [Azure Monitor Alert Rules](#azure-monitor-alert-rules)
13. [Power BI Integration](#power-bi-integration)
14. [Dashboard Layout Recommendations](#dashboard-layout-recommendations)
15. [Document Control](#document-control)

---

## Overview

This document provides a **comprehensive library of Kusto Query Language (KQL) queries** purpose-built for monitoring the Azure OpenAI RAG Enterprise Platform. Each query is production-tested, parameterized where applicable, and designed to integrate with **Azure Monitor**, **Application Insights**, **Log Analytics**, and **Power BI** dashboards.

### Query Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| **Category** | Uppercase prefix | `LAT` (Latency), `ERR` (Error), `TOK` (Token) |
| **Sequence** | Three-digit number | `001`, `002`, `003` |
| **Full Name** | `{Category}-{Sequence}` | `LAT-001`, `ERR-003`, `TOK-002` |

### Custom Dimensions Schema

| Custom Dimension | Description | Example Values |
|------------------|-------------|----------------|
| `TenantId` | Multi-tenant identifier | `tenant-contoso`, `tenant-fabrikam` |
| `ModelDeployment` | Azure OpenAI deployment name | `gpt-4o-prod`, `gpt-4o-mini-prod` |
| `EndpointName` | API route identifier | `/api/v1/chat`, `/api/v1/search` |
| `TokensPrompt` | Input token count | `1500` |
| `TokensCompletion` | Output token count | `800` |
| `CacheHit` | Whether semantic cache hit | `true`, `false` |
| `GroundednessScore` | AI quality metric (0-1) | `0.87` |
| `CitationCount` | Number of citations returned | `3` |
| `SessionId` | User session tracking | `sess-abc123` |
| `QueryPattern` | Classified query type | `factual`, `analytical`, `creative` |

### Data Source Tables

| Table | Source | Purpose |
|-------|--------|---------|
| `requests` | Application Insights | HTTP request telemetry |
| `traces` | Application Insights | Custom log events |
| `customMetrics` | Application Insights | Numeric metric values |
| `customEvents` | Application Insights | Business events |
| `dependencies` | Application Insights | Outbound dependency calls |
| `exceptions` | Application Insights | Exception telemetry |
| `AzureDiagnostics` | Log Analytics | Azure service diagnostics |
| `InsightsMetrics` | Log Analytics | Container/VM metrics |

---

## 1. Latency Analysis

### LAT-001: P50 / P95 / P99 Latency by Hour

**Purpose:** Hourly latency percentile distribution for SLO compliance. Identifies time-of-day patterns and gradual degradation.

```kusto
requests
| where timestamp > ago(24h)
| where success == true
| where name has "/api/v1/"
| summarize
    P50 = percentile(duration, 50),
    P95 = percentile(duration, 95),
    P99 = percentile(duration, 99),
    RequestCount = count()
    by bin(timestamp, 1h)
| order by timestamp asc
| render timechart
```

### LAT-002: P95 Latency by Endpoint

**Purpose:** Compare latency across API endpoints to identify which routes contribute most to slowness.

```kusto
requests
| where timestamp > ago(7d)
| where success == true
| extend Endpoint = tostring(customDimensions["EndpointName"])
| summarize
    P50_ms = round(percentile(duration, 50), 1),
    P95_ms = round(percentile(duration, 95), 1),
    P99_ms = round(percentile(duration, 99), 1),
    AvgDuration_ms = round(avg(duration), 1),
    TotalRequests = count()
    by Endpoint
| order by P95_ms desc
```

### LAT-003: P95 Latency by Tenant

**Purpose:** Detect tenant-specific latency regressions in the multi-tenant platform.

```kusto
requests
| where timestamp > ago(24h)
| where success == true
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize
    P50_ms = round(percentile(duration, 50), 1),
    P95_ms = round(percentile(duration, 95), 1),
    P99_ms = round(percentile(duration, 99), 1),
    RequestCount = count()
    by TenantId
| order by P95_ms desc
| take 20
```

### LAT-004: Latency Distribution Histogram

**Purpose:** Visualize full latency distribution to identify bimodal patterns (cache hit vs. miss).

```kusto
requests
| where timestamp > ago(24h)
| where name has "/api/v1/chat"
| extend LatencyBucket = case(
    duration < 200, "0-200ms",
    duration < 500, "200-500ms",
    duration < 1000, "500ms-1s",
    duration < 2000, "1-2s",
    duration < 5000, "2-5s",
    duration < 10000, "5-10s",
    "10s+")
| summarize Count = count() by LatencyBucket
| order by case(
    LatencyBucket == "0-200ms", 1, LatencyBucket == "200-500ms", 2,
    LatencyBucket == "500ms-1s", 3, LatencyBucket == "1-2s", 4,
    LatencyBucket == "2-5s", 5, LatencyBucket == "5-10s", 6, 7) asc
```

### LAT-005: Slow Query Detection (> SLO Threshold)

**Purpose:** Surface requests breaching the 2-second P95 SLO with contextual metadata for root-cause investigation.

```kusto
requests
| where timestamp > ago(1h)
| where duration > 2000
| extend TenantId = tostring(customDimensions["TenantId"])
| extend Endpoint = tostring(customDimensions["EndpointName"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend TokensPrompt = toint(customDimensions["TokensPrompt"])
| project timestamp, Duration_ms = round(duration, 0), Endpoint, TenantId,
    ModelDeployment, TokensPrompt, resultCode, operation_Id
| order by Duration_ms desc
| take 50
```

### LAT-006: Latency Breakdown by Dependency (Waterfall)

**Purpose:** Decompose end-to-end latency into dependency calls (Azure OpenAI, AI Search, Cosmos DB, Redis).

```kusto
let targetOps = requests
| where timestamp > ago(1h)
| where duration > 3000
| project operation_Id;
dependencies
| where timestamp > ago(1h)
| where operation_Id in (targetOps)
| extend DependencyType = case(
    target has "openai", "Azure OpenAI",
    target has "search", "Azure AI Search",
    target has "cosmos" or target has "documents.azure.com", "Cosmos DB",
    target has "redis", "Redis Cache", type)
| summarize
    AvgDuration_ms = round(avg(duration), 1),
    P95Duration_ms = round(percentile(duration, 95), 1),
    CallCount = count(),
    FailureCount = countif(success == false)
    by DependencyType
| order by AvgDuration_ms desc
```

---

## 2. Error Analysis

### ERR-001: Error Rate Trending (Hourly)

**Purpose:** Monitor rolling error rate as a percentage of total requests against the 1% SLO threshold.

```kusto
requests
| where timestamp > ago(24h)
| where name has "/api/v1/"
| summarize
    TotalRequests = count(),
    FailedRequests = countif(success == false),
    ErrorRate = round(100.0 * countif(success == false) / count(), 2)
    by bin(timestamp, 1h)
| order by timestamp asc
| render timechart
```

### ERR-002: Error Breakdown by HTTP Status Code

**Purpose:** Classify errors by status code to distinguish client (4xx) from server (5xx) failures.

```kusto
requests
| where timestamp > ago(24h)
| where toint(resultCode) >= 400
| extend StatusCategory = case(
    toint(resultCode) >= 500, "5xx Server Error",
    toint(resultCode) == 429, "429 Rate Limited",
    toint(resultCode) == 401 or toint(resultCode) == 403, "401/403 Auth Failure",
    toint(resultCode) == 404, "404 Not Found",
    toint(resultCode) == 400, "400 Bad Request",
    strcat(resultCode, " Other"))
| summarize Count = count() by StatusCategory, resultCode
| order by Count desc
```

### ERR-003: Top 10 Errors by Exception Type

**Purpose:** Rank exceptions by frequency to prioritize bug fixes and identify systemic patterns.

```kusto
exceptions
| where timestamp > ago(24h)
| summarize
    Count = count(), LastSeen = max(timestamp),
    SampleMessage = take_any(outerMessage)
    by type, problemId
| order by Count desc
| take 10
| project ExceptionType = type, ProblemId = problemId,
    Occurrences = Count, LastSeen, SampleMessage
```

### ERR-004: 5xx Spike Detection

**Purpose:** Detect 5xx bursts exceeding 3 standard deviations above the rolling mean within 5-minute windows.

```kusto
let errorTimeline = requests
| where timestamp > ago(6h)
| where toint(resultCode) >= 500
| summarize ErrorCount = count() by bin(timestamp, 5m);
let stats = errorTimeline
| summarize AvgErrors = avg(ErrorCount), StdDev = stdev(ErrorCount);
errorTimeline
| extend Threshold = toscalar(stats | project AvgErrors + 3 * StdDev)
| extend AvgBaseline = toscalar(stats | project AvgErrors)
| where ErrorCount > Threshold
| project timestamp, ErrorCount, Baseline = round(AvgBaseline, 1),
    Threshold = round(Threshold, 1),
    Severity = case(ErrorCount > Threshold * 2, "Critical",
        ErrorCount > Threshold * 1.5, "High", "Medium")
| order by timestamp desc
```

### ERR-005: Dependency Failure Correlation

**Purpose:** Correlate failed requests with downstream dependency failures (OpenAI throttling, search outages, DB timeouts).

```kusto
let failedOps = requests
| where timestamp > ago(2h) | where success == false
| project operation_Id, RequestTime = timestamp, ResultCode = resultCode;
dependencies
| where timestamp > ago(2h) | where success == false
| join kind=inner (failedOps) on operation_Id
| extend DependencyTarget = case(
    target has "openai", "Azure OpenAI", target has "search", "Azure AI Search",
    target has "cosmos", "Cosmos DB", target has "redis", "Redis Cache",
    target has "blob", "Blob Storage", target)
| summarize
    CorrelatedFailures = count(), DistinctRequests = dcount(operation_Id),
    AvgDepDuration_ms = round(avg(duration), 0),
    SampleResultCodes = make_set(resultCode, 5)
    by DependencyTarget
| order by CorrelatedFailures desc
```

### ERR-006: Error Rate by Tenant

**Purpose:** Detect tenant-specific error patterns and misconfigurations.

```kusto
requests
| where timestamp > ago(24h)
| where name has "/api/v1/"
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize
    TotalRequests = count(),
    FailedRequests = countif(success == false),
    ErrorRate_pct = round(100.0 * countif(success == false) / count(), 2)
    by TenantId
| where TotalRequests > 10
| order by ErrorRate_pct desc
| take 20
```

---

## 3. Token Consumption

### TOK-001: Token Usage by Tenant (Daily)

**Purpose:** Per-tenant token consumption for chargeback allocation and quota enforcement.

```kusto
customMetrics
| where timestamp > ago(30d)
| where name == "TokensTotal"
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize
    PromptTokens = sumif(value, customDimensions["TokenType"] == "prompt"),
    CompletionTokens = sumif(value, customDimensions["TokenType"] == "completion"),
    TotalTokens = sum(value)
    by TenantId, bin(timestamp, 1d)
| extend Day = format_datetime(timestamp, "yyyy-MM-dd")
| project Day, TenantId, PromptTokens, CompletionTokens, TotalTokens
| order by Day desc, TotalTokens desc
```

### TOK-002: Token Usage by Model Deployment

**Purpose:** Compare token consumption across GPT-4o, GPT-4o-mini, and embedding models.

```kusto
requests
| where timestamp > ago(7d)
| where name has "/api/v1/chat" or name has "/api/v1/embeddings"
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| summarize
    TotalPromptTokens = sum(TokensPrompt),
    TotalCompletionTokens = sum(TokensCompletion),
    AvgPromptTokens = round(avg(TokensPrompt), 0),
    RequestCount = count()
    by ModelDeployment, bin(timestamp, 1d)
| order by timestamp desc, TotalPromptTokens desc
```

### TOK-003: Token Cost Calculation (Estimated)

**Purpose:** Translate token consumption into dollar-cost estimates using Azure OpenAI pricing tiers.

```kusto
requests
| where timestamp > ago(30d)
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend PromptCostPer1K = case(
    ModelDeployment has "gpt-4o-mini", 0.00015,
    ModelDeployment has "gpt-4o", 0.005,
    ModelDeployment has "embedding", 0.00013, 0.005)
| extend CompletionCostPer1K = case(
    ModelDeployment has "gpt-4o-mini", 0.0006,
    ModelDeployment has "gpt-4o", 0.015,
    ModelDeployment has "embedding", 0.0, 0.015)
| extend EstimatedCost_USD =
    (TokensPrompt / 1000.0) * PromptCostPer1K +
    (TokensCompletion / 1000.0) * CompletionCostPer1K
| summarize
    TotalCost_USD = round(sum(EstimatedCost_USD), 2),
    TotalPromptTokens = sum(TokensPrompt),
    TotalCompletionTokens = sum(TokensCompletion),
    RequestCount = count()
    by ModelDeployment, bin(timestamp, 1d)
| order by timestamp desc, TotalCost_USD desc
```

### TOK-004: Budget Burn Rate and Projected Overage

**Purpose:** Calculate daily spend velocity and project monthly totals, flagging budget overruns.

```kusto
let MonthlyBudget = 15000.0;
let DaysInMonth = 30;
requests
| where timestamp > ago(30d)
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend CostPerRequest = case(
    ModelDeployment has "gpt-4o-mini",
        (TokensPrompt / 1000.0) * 0.00015 + (TokensCompletion / 1000.0) * 0.0006,
    ModelDeployment has "gpt-4o",
        (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015,
    (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015)
| summarize DailyCost = sum(CostPerRequest) by bin(timestamp, 1d)
| summarize AvgDailyCost = round(avg(DailyCost), 2),
    MaxDailyCost = round(max(DailyCost), 2),
    TotalSpentToDate = round(sum(DailyCost), 2)
| extend ProjectedMonthly = round(AvgDailyCost * DaysInMonth, 2)
| extend BudgetUtilization_pct = round(100.0 * TotalSpentToDate / MonthlyBudget, 1)
| extend BurnStatus = case(
    ProjectedMonthly > MonthlyBudget * 1.2, "CRITICAL - Over budget",
    ProjectedMonthly > MonthlyBudget, "WARNING - Approaching limit",
    "Healthy - Under budget")
```

---

## 4. Cache Performance

### CAC-001: Semantic Cache Hit Ratio (Hourly)

**Purpose:** Measure Redis semantic cache effectiveness. Target: 25-40% hit ratio for repeated enterprise queries.

```kusto
customEvents
| where timestamp > ago(24h)
| where name == "CacheLookup"
| extend CacheHit = tobool(customDimensions["CacheHit"])
| summarize
    TotalLookups = count(),
    CacheHits = countif(CacheHit == true),
    CacheMisses = countif(CacheHit == false),
    HitRatio_pct = round(100.0 * countif(CacheHit == true) / count(), 2)
    by bin(timestamp, 1h)
| order by timestamp asc
| render timechart
```

### CAC-002: Cache Miss Rate by Query Pattern

**Purpose:** Identify query categories with lowest cache hit rates for cache key strategy tuning.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "CacheLookup"
| extend CacheHit = tobool(customDimensions["CacheHit"])
| extend QueryPattern = tostring(customDimensions["QueryPattern"])
| summarize
    TotalLookups = count(),
    Misses = countif(CacheHit == false),
    MissRate_pct = round(100.0 * countif(CacheHit == false) / count(), 2),
    AvgSimilarityScore = round(avg(todouble(customDimensions["SimilarityScore"])), 3)
    by QueryPattern
| order by MissRate_pct desc
```

### CAC-003: Cache Eviction Rate and Memory Pressure

**Purpose:** Monitor Redis eviction events and memory utilization for capacity planning.

```kusto
customMetrics
| where timestamp > ago(24h)
| where name in ("CacheEvictions", "CacheMemoryUsedMB", "CacheMemoryMaxMB")
| summarize AvgValue = avg(value), MaxValue = max(value) by name, bin(timestamp, 15m)
| evaluate pivot(name, take_any(AvgValue))
| extend MemoryUtilization_pct = round(100.0 * CacheMemoryUsedMB / CacheMemoryMaxMB, 1)
| project timestamp, EvictionsAvg = round(CacheEvictions, 0),
    MemoryUsed_MB = round(CacheMemoryUsedMB, 1),
    MemoryMax_MB = round(CacheMemoryMaxMB, 1), MemoryUtilization_pct
| order by timestamp asc
```

---

## 5. RAG Quality Metrics

### RAG-001: Groundedness Score Trending

**Purpose:** Track AI-evaluated groundedness over time. Measures whether LLM responses are substantiated by retrieved documents.

```kusto
customMetrics
| where timestamp > ago(30d)
| where name == "GroundednessScore"
| summarize
    AvgGroundedness = round(avg(value), 3),
    P25 = round(percentile(value, 25), 3),
    Median = round(percentile(value, 50), 3),
    P75 = round(percentile(value, 75), 3),
    SampleSize = count()
    by bin(timestamp, 1d)
| order by timestamp asc
| render timechart
```

### RAG-002: Hallucination Rate Detection

**Purpose:** Identify responses with groundedness below 0.5, classified as potential hallucinations.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "RAGResponse"
| extend GroundednessScore = todouble(customDimensions["GroundednessScore"])
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize
    TotalResponses = count(),
    HallucinationCount = countif(GroundednessScore < 0.5),
    HallucinationRate_pct = round(100.0 * countif(GroundednessScore < 0.5) / count(), 2),
    AvgGroundedness = round(avg(GroundednessScore), 3)
    by TenantId, bin(timestamp, 1d)
| order by HallucinationRate_pct desc
```

### RAG-003: Citation Accuracy and Coverage

**Purpose:** Measure citation inclusion rate and average citations per response.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "RAGResponse"
| extend CitationCount = toint(customDimensions["CitationCount"])
| extend DocumentsRetrieved = toint(customDimensions["DocumentsRetrieved"])
| summarize
    TotalResponses = count(),
    WithCitations = countif(CitationCount > 0),
    CitationCoverage_pct = round(100.0 * countif(CitationCount > 0) / count(), 2),
    AvgCitations = round(avg(CitationCount), 1),
    AvgDocsRetrieved = round(avg(DocumentsRetrieved), 1)
    by bin(timestamp, 1d)
| order by timestamp asc
```

### RAG-004: Zero-Result Rate (No Documents Retrieved)

**Purpose:** Track queries returning zero documents, indicating index coverage gaps.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "SearchQuery"
| extend DocumentsRetrieved = toint(customDimensions["DocumentsRetrieved"])
| extend QueryPattern = tostring(customDimensions["QueryPattern"])
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize
    TotalQueries = count(),
    ZeroResultQueries = countif(DocumentsRetrieved == 0),
    ZeroResultRate_pct = round(100.0 * countif(DocumentsRetrieved == 0) / count(), 2)
    by TenantId, QueryPattern, bin(timestamp, 1d)
| where ZeroResultRate_pct > 5.0
| order by ZeroResultRate_pct desc
```

---

## 6. User Analytics

### USR-001: Daily Active Users (DAU) and Monthly Active Users (MAU)

**Purpose:** Track platform adoption with DAU/MAU stickiness ratio. Enterprise benchmark: above 20%.

```kusto
let DAU = customEvents
| where timestamp > ago(1d) | where name == "UserQuery"
| extend UserId = tostring(customDimensions["UserId"])
| summarize DAU = dcount(UserId);
let MAU = customEvents
| where timestamp > ago(30d) | where name == "UserQuery"
| extend UserId = tostring(customDimensions["UserId"])
| summarize MAU = dcount(UserId);
let dauVal = toscalar(DAU);
let mauVal = toscalar(MAU);
print DAU = dauVal, MAU = mauVal,
    Stickiness_pct = round(100.0 * todouble(dauVal) / todouble(mauVal), 1)
```

### USR-002: Queries per User Distribution

**Purpose:** Segment users into light (1-5), moderate (6-20), and power (20+) for capacity planning.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "UserQuery"
| extend UserId = tostring(customDimensions["UserId"])
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize QueryCount = count() by UserId, TenantId, bin(timestamp, 1d)
| extend UserSegment = case(
    QueryCount <= 5, "Light (1-5)", QueryCount <= 20, "Moderate (6-20)",
    QueryCount <= 50, "Heavy (21-50)", "Power (50+)")
| summarize UserCount = dcount(UserId), AvgQueries = round(avg(QueryCount), 1),
    MaxQueries = max(QueryCount) by UserSegment
| order by case(UserSegment == "Light (1-5)", 1,
    UserSegment == "Moderate (6-20)", 2,
    UserSegment == "Heavy (21-50)", 3, 4) asc
```

### USR-003: Average Session Length

**Purpose:** Measure user engagement depth via session duration and event density.

```kusto
customEvents
| where timestamp > ago(7d)
| where name in ("UserQuery", "UserFeedback", "DocumentView")
| extend SessionId = tostring(customDimensions["SessionId"])
| extend UserId = tostring(customDimensions["UserId"])
| summarize SessionStart = min(timestamp), SessionEnd = max(timestamp),
    EventCount = count() by SessionId, UserId
| extend SessionDuration_min = round(datetime_diff("second", SessionEnd, SessionStart) / 60.0, 1)
| where SessionDuration_min > 0
| summarize
    AvgSessionLength_min = round(avg(SessionDuration_min), 1),
    MedianSessionLength_min = round(percentile(SessionDuration_min, 50), 1),
    AvgEventsPerSession = round(avg(EventCount), 1),
    TotalSessions = count()
    by bin(SessionStart, 1d)
| order by SessionStart asc
```

### USR-004: Top Query Patterns and Topics

**Purpose:** Identify most frequently asked categories to guide knowledge base expansion.

```kusto
customEvents
| where timestamp > ago(30d)
| where name == "UserQuery"
| extend QueryPattern = tostring(customDimensions["QueryPattern"])
| extend TopicCategory = tostring(customDimensions["TopicCategory"])
| summarize QueryCount = count(),
    UniqueUsers = dcount(tostring(customDimensions["UserId"])),
    AvgGroundedness = round(avg(todouble(customDimensions["GroundednessScore"])), 3)
    by QueryPattern, TopicCategory
| order by QueryCount desc
| take 25
```

---

## 7. Security Monitoring

### SEC-001: Failed Authentication Attempts

**Purpose:** Detect brute-force attacks and credential stuffing by tracking failed auth events with IP enrichment.

```kusto
requests
| where timestamp > ago(24h)
| where resultCode == "401" or resultCode == "403"
| extend ClientIP = client_IP
| extend TenantId = tostring(customDimensions["TenantId"])
| extend UserAgent = tostring(customDimensions["UserAgent"])
| summarize FailedAttempts = count(), DistinctEndpoints = dcount(name),
    FirstAttempt = min(timestamp), LastAttempt = max(timestamp),
    UserAgents = make_set(UserAgent, 5) by ClientIP, TenantId
| where FailedAttempts > 10
| extend RiskLevel = case(FailedAttempts > 100, "Critical",
    FailedAttempts > 50, "High", FailedAttempts > 20, "Medium", "Low")
| order by FailedAttempts desc
```

### SEC-002: PII Detection Trigger Events

**Purpose:** Monitor PII detection triggers for GDPR/CCPA compliance, ensuring no sensitive data leakage.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "PIIDetection"
| extend PIICategory = tostring(customDimensions["PIICategory"])
| extend Direction = tostring(customDimensions["Direction"])
| extend TenantId = tostring(customDimensions["TenantId"])
| extend ActionTaken = tostring(customDimensions["ActionTaken"])
| summarize DetectionCount = count(),
    DistinctUsers = dcount(tostring(customDimensions["UserId"]))
    by PIICategory, Direction, ActionTaken, bin(timestamp, 1d)
| order by DetectionCount desc
```

### SEC-003: Content Filter Block Events

**Purpose:** Track content filter activations to detect prompt injection or jailbreak attempts.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "ContentFilterTriggered"
| extend FilterCategory = tostring(customDimensions["FilterCategory"])
| extend Severity = tostring(customDimensions["Severity"])
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize BlockCount = count(),
    DistinctUsers = dcount(tostring(customDimensions["UserId"])),
    DistinctTenants = dcount(TenantId)
    by FilterCategory, Severity, tostring(customDimensions["Direction"]), bin(timestamp, 1d)
| order by BlockCount desc
```

### SEC-004: Suspicious IP Analysis

**Purpose:** Identify IPs with anomalous patterns: high volume, multi-tenant access, or excessive errors.

```kusto
let IpActivity = requests
| where timestamp > ago(24h) | where name has "/api/v1/"
| extend ClientIP = client_IP
| extend TenantId = tostring(customDimensions["TenantId"])
| summarize RequestCount = count(), DistinctTenants = dcount(TenantId),
    ErrorCount = countif(success == false),
    ErrorRate_pct = round(100.0 * countif(success == false) / count(), 2),
    TenantList = make_set(TenantId, 10) by ClientIP;
IpActivity
| where DistinctTenants > 1 or RequestCount > 5000 or ErrorRate_pct > 50
| extend SuspicionReason = case(
    DistinctTenants > 3, "Multi-tenant access (credential compromise)",
    RequestCount > 10000, "Extreme volume (DoS)",
    RequestCount > 5000, "High volume (scraping)",
    ErrorRate_pct > 80, "Mostly errors (enumeration)", "Anomalous pattern")
| order by RequestCount desc
```

---

## 8. Cost Tracking

### CST-001: Cost per Tenant (Monthly)

**Purpose:** Per-tenant total cost for chargeback reporting combining token consumption across models.

```kusto
requests
| where timestamp > ago(30d)
| extend TenantId = tostring(customDimensions["TenantId"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend TokenCost = case(
    ModelDeployment has "gpt-4o-mini",
        (TokensPrompt / 1000.0) * 0.00015 + (TokensCompletion / 1000.0) * 0.0006,
    ModelDeployment has "gpt-4o",
        (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015,
    ModelDeployment has "embedding", (TokensPrompt / 1000.0) * 0.00013, 0.0)
| summarize TotalTokenCost_USD = round(sum(TokenCost), 2),
    TotalRequests = count(), AvgCostPerRequest_USD = round(avg(TokenCost), 4)
    by TenantId
| order by TotalTokenCost_USD desc
```

### CST-002: Daily Cost Trending with Moving Average

**Purpose:** Overlay daily cost with 7-day moving average to detect sustained upward trends.

```kusto
let DailyCosts = requests
| where timestamp > ago(60d)
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend Cost = case(
    ModelDeployment has "gpt-4o-mini",
        (TokensPrompt / 1000.0) * 0.00015 + (TokensCompletion / 1000.0) * 0.0006,
    ModelDeployment has "gpt-4o",
        (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015, 0.0)
| summarize DailyCost = sum(Cost) by Day = bin(timestamp, 1d);
DailyCosts
| order by Day asc
| extend MovingAvg7d = round(avg_if(DailyCost, Day between (Day - 7d .. Day)), 2)
| project Day, DailyCost = round(DailyCost, 2), MovingAvg7d
| render timechart
```

### CST-003: Cost Anomaly Detection

**Purpose:** Flag days where spend deviates more than 2 standard deviations from the rolling mean.

```kusto
let DailyCosts = requests
| where timestamp > ago(30d)
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend Cost = case(
    ModelDeployment has "gpt-4o-mini",
        (TokensPrompt / 1000.0) * 0.00015 + (TokensCompletion / 1000.0) * 0.0006,
    ModelDeployment has "gpt-4o",
        (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015, 0.0)
| summarize DailyCost = round(sum(Cost), 2) by Day = bin(timestamp, 1d);
let CostStats = DailyCosts
| summarize AvgCost = avg(DailyCost), StdDevCost = stdev(DailyCost);
DailyCosts
| extend AvgCost = toscalar(CostStats | project AvgCost)
| extend StdDevCost = toscalar(CostStats | project StdDevCost)
| extend ZScore = round((DailyCost - AvgCost) / StdDevCost, 2)
| where abs(ZScore) > 2
| extend AnomalyType = iff(ZScore > 0, "Cost Spike", "Cost Drop")
| project Day, DailyCost, AvgCost = round(AvgCost, 2), ZScore, AnomalyType
| order by Day desc
```

---

## 9. Search Performance

### SRC-001: Azure AI Search Latency Analysis

**Purpose:** Monitor search query performance to detect degradation from index growth or resource contention.

```kusto
dependencies
| where timestamp > ago(24h)
| where type == "Azure.Search" or target has "search.windows.net"
| extend SearchIndex = tostring(customDimensions["SearchIndex"])
| extend QueryType = tostring(customDimensions["QueryType"])
| summarize
    P50_ms = round(percentile(duration, 50), 1),
    P95_ms = round(percentile(duration, 95), 1),
    P99_ms = round(percentile(duration, 99), 1),
    QueryCount = count(), ErrorCount = countif(success == false)
    by SearchIndex, QueryType, bin(timestamp, 1h)
| order by timestamp desc
```

### SRC-002: Zero-Result Search Queries

**Purpose:** Capture zero-result queries for knowledge base gap analysis and synonym enrichment.

```kusto
customEvents
| where timestamp > ago(7d)
| where name == "SearchQuery"
| extend DocumentsRetrieved = toint(customDimensions["DocumentsRetrieved"])
| extend SearchQuery = tostring(customDimensions["SearchQuerySanitized"])
| extend SearchIndex = tostring(customDimensions["SearchIndex"])
| where DocumentsRetrieved == 0
| summarize Occurrences = count(),
    DistinctUsers = dcount(tostring(customDimensions["UserId"])),
    LastOccurrence = max(timestamp)
    by SearchQuery, SearchIndex, tostring(customDimensions["TenantId"])
| order by Occurrences desc
| take 50
```

### SRC-003: Index Size and Document Count Monitoring

**Purpose:** Track search index growth for scaling and ingestion pipeline validation.

```kusto
customMetrics
| where timestamp > ago(30d)
| where name in ("SearchIndexDocumentCount", "SearchIndexSizeBytes")
| extend SearchIndex = tostring(customDimensions["SearchIndex"])
| summarize LatestValue = arg_max(timestamp, value) by name, SearchIndex, bin(timestamp, 1d)
| evaluate pivot(name, take_any(value))
| extend IndexSize_MB = round(SearchIndexSizeBytes / (1024.0 * 1024.0), 2)
| project timestamp, SearchIndex,
    DocumentCount = SearchIndexDocumentCount, IndexSize_MB
| order by timestamp desc
```

---

## 10. Infrastructure Health

### INF-001: AKS Node CPU and Memory Utilization

**Purpose:** Monitor Kubernetes cluster resources for HPA tuning and pre-emptive scaling.

```kusto
InsightsMetrics
| where TimeGenerated > ago(24h)
| where Namespace == "container.azm.ms/insights"
| where Name in ("cpuUsageNanoCores", "memoryWorkingSetBytes")
| extend NodeName = tostring(parse_json(Tags)["hostName"])
| summarize AvgValue = avg(Val), MaxValue = max(Val),
    P95Value = percentile(Val, 95)
    by Name, NodeName, bin(TimeGenerated, 15m)
| extend MetricValue = case(
    Name == "cpuUsageNanoCores", round(AvgValue / 1000000.0, 2),
    Name == "memoryWorkingSetBytes", round(AvgValue / (1024.0 * 1024.0 * 1024.0), 2),
    AvgValue)
| extend Unit = case(Name == "cpuUsageNanoCores", "millicores",
    Name == "memoryWorkingSetBytes", "GB", "raw")
| project TimeGenerated, NodeName, Metric = Name, MetricValue, Unit
| order by TimeGenerated desc
```

### INF-002: Azure Functions Execution Count and Duration

**Purpose:** Track function invocations for document ingestion, embedding generation, and maintenance.

```kusto
requests
| where timestamp > ago(24h)
| where cloud_RoleName has "func-"
| extend FunctionName = name
| extend TriggerType = tostring(customDimensions["TriggerType"])
| summarize ExecutionCount = count(),
    SuccessRate_pct = round(100.0 * countif(success == true) / count(), 2),
    AvgDuration_ms = round(avg(duration), 0),
    P95Duration_ms = round(percentile(duration, 95), 0),
    MaxDuration_ms = round(max(duration), 0)
    by FunctionName, TriggerType, bin(timestamp, 1h)
| order by timestamp desc, ExecutionCount desc
```

### INF-003: Cosmos DB RU Consumption and Throttling

**Purpose:** Monitor RU consumption against provisioned throughput, detect HTTP 429 throttling.

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.DOCUMENTDB"
| where TimeGenerated > ago(24h)
| extend RequestCharge = todouble(requestCharge_s)
| extend StatusCode = toint(statusCode_s)
| summarize TotalRUs = round(sum(RequestCharge), 0),
    AvgRUPerRequest = round(avg(RequestCharge), 2),
    P95RUPerRequest = round(percentile(RequestCharge, 95), 2),
    RequestCount = count(),
    ThrottledCount = countif(StatusCode == 429),
    ThrottleRate_pct = round(100.0 * countif(StatusCode == 429) / count(), 2)
    by databaseName_s, bin(TimeGenerated, 15m)
| order by TimeGenerated desc
```

### INF-004: API Management Request Volume and Latency

**Purpose:** Monitor the APIM gateway for request volume, backend latency, and policy overhead.

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT"
| where TimeGenerated > ago(24h)
| extend BackendLatency_ms = todouble(backendTime_d)
| extend TotalLatency_ms = todouble(totalTime_d)
| extend PolicyLatency_ms = TotalLatency_ms - BackendLatency_ms
| extend StatusCode = toint(httpStatusCode_d)
| summarize RequestCount = count(),
    AvgBackendLatency_ms = round(avg(BackendLatency_ms), 0),
    P95BackendLatency_ms = round(percentile(BackendLatency_ms, 95), 0),
    AvgPolicyOverhead_ms = round(avg(PolicyLatency_ms), 0),
    ErrorRate_pct = round(100.0 * countif(StatusCode >= 400) / count(), 2)
    by apiId_s, bin(TimeGenerated, 1h)
| order by TimeGenerated desc, RequestCount desc
```

---

## Azure Monitor Alert Rules

The following **ARM template fragments** define critical alert rules. Deploy via the IaC pipeline alongside Terraform infrastructure.

### Alert Rule 1: High Error Rate (> 5% over 15 minutes)

```json
{
  "type": "Microsoft.Insights/scheduledQueryRules",
  "apiVersion": "2023-03-15-preview",
  "name": "alert-high-error-rate",
  "location": "[resourceGroup().location]",
  "properties": {
    "displayName": "High Error Rate - API Layer",
    "description": "Error rate exceeds 5% over 15-minute window",
    "severity": 1,
    "enabled": true,
    "evaluationFrequency": "PT5M",
    "windowSize": "PT15M",
    "scopes": ["[resourceId('Microsoft.Insights/components', parameters('appInsightsName'))]"],
    "criteria": {
      "allOf": [{
        "query": "requests | where timestamp > ago(15m) | where name has '/api/v1/' | summarize ErrorRate = 100.0 * countif(success == false) / count() | where ErrorRate > 5",
        "timeAggregation": "Count",
        "operator": "GreaterThan",
        "threshold": 0,
        "failingPeriods": { "numberOfEvaluationPeriods": 3, "minFailingPeriodsToAlert": 2 }
      }]
    },
    "actions": { "actionGroups": ["[resourceId('Microsoft.Insights/actionGroups', 'ag-platform-oncall')]"] }
  }
}
```

### Alert Rule 2: P95 Latency SLO Breach (> 2 seconds)

```json
{
  "type": "Microsoft.Insights/scheduledQueryRules",
  "apiVersion": "2023-03-15-preview",
  "name": "alert-p95-latency-breach",
  "location": "[resourceGroup().location]",
  "properties": {
    "displayName": "P95 Latency SLO Breach",
    "description": "P95 latency exceeds 2000ms over 10-minute window",
    "severity": 2,
    "enabled": true,
    "evaluationFrequency": "PT5M",
    "windowSize": "PT10M",
    "scopes": ["[resourceId('Microsoft.Insights/components', parameters('appInsightsName'))]"],
    "criteria": {
      "allOf": [{
        "query": "requests | where timestamp > ago(10m) | where name has '/api/v1/' | where success == true | summarize P95 = percentile(duration, 95) | where P95 > 2000",
        "timeAggregation": "Count",
        "operator": "GreaterThan",
        "threshold": 0,
        "failingPeriods": { "numberOfEvaluationPeriods": 3, "minFailingPeriodsToAlert": 2 }
      }]
    },
    "actions": { "actionGroups": ["[resourceId('Microsoft.Insights/actionGroups', 'ag-platform-oncall')]"] }
  }
}
```

### Alert Rule 3: Cosmos DB Throttling Detected

```json
{
  "type": "Microsoft.Insights/scheduledQueryRules",
  "apiVersion": "2023-03-15-preview",
  "name": "alert-cosmos-throttling",
  "location": "[resourceGroup().location]",
  "properties": {
    "displayName": "Cosmos DB Throttling Detected",
    "description": "HTTP 429 responses exceed 10 in 5-minute window",
    "severity": 2,
    "enabled": true,
    "evaluationFrequency": "PT5M",
    "windowSize": "PT5M",
    "scopes": ["[resourceId('Microsoft.OperationalInsights/workspaces', parameters('logAnalyticsName'))]"],
    "criteria": {
      "allOf": [{
        "query": "AzureDiagnostics | where ResourceProvider == 'MICROSOFT.DOCUMENTDB' | where toint(statusCode_s) == 429 | summarize ThrottleCount = count() | where ThrottleCount > 10",
        "timeAggregation": "Count",
        "operator": "GreaterThan",
        "threshold": 0,
        "failingPeriods": { "numberOfEvaluationPeriods": 1, "minFailingPeriodsToAlert": 1 }
      }]
    },
    "actions": { "actionGroups": ["[resourceId('Microsoft.Insights/actionGroups', 'ag-platform-oncall')]", "[resourceId('Microsoft.Insights/actionGroups', 'ag-data-team')]"] }
  }
}
```

### Alert Rule 4: Excessive Failed Authentication

```json
{
  "type": "Microsoft.Insights/scheduledQueryRules",
  "apiVersion": "2023-03-15-preview",
  "name": "alert-excessive-auth-failures",
  "location": "[resourceGroup().location]",
  "properties": {
    "displayName": "Excessive Failed Authentication Attempts",
    "description": "More than 50 failed auth attempts from single IP in 10 minutes",
    "severity": 1,
    "enabled": true,
    "evaluationFrequency": "PT5M",
    "windowSize": "PT10M",
    "scopes": ["[resourceId('Microsoft.Insights/components', parameters('appInsightsName'))]"],
    "criteria": {
      "allOf": [{
        "query": "requests | where timestamp > ago(10m) | where resultCode in ('401', '403') | summarize FailCount = count() by client_IP | where FailCount > 50",
        "timeAggregation": "Count",
        "operator": "GreaterThan",
        "threshold": 0,
        "failingPeriods": { "numberOfEvaluationPeriods": 1, "minFailingPeriodsToAlert": 1 }
      }]
    },
    "actions": { "actionGroups": ["[resourceId('Microsoft.Insights/actionGroups', 'ag-security-team')]", "[resourceId('Microsoft.Insights/actionGroups', 'ag-platform-oncall')]"] }
  }
}
```

---

## Power BI Integration

### Power BI KQL Query Template — Executive Cost Dashboard

Designed for **Power BI DirectQuery** mode against the Log Analytics workspace. Produces a flattened table for matrix and chart visuals.

```kusto
let StartDate = datetime({StartDate});
let EndDate = datetime({EndDate});
requests
| where timestamp between (StartDate .. EndDate)
| where name has "/api/v1/"
| extend TenantId = tostring(customDimensions["TenantId"])
| extend ModelDeployment = tostring(customDimensions["ModelDeployment"])
| extend TokensPrompt = todouble(customDimensions["TokensPrompt"])
| extend TokensCompletion = todouble(customDimensions["TokensCompletion"])
| extend ModelFamily = case(
    ModelDeployment has "gpt-4o-mini", "GPT-4o-mini",
    ModelDeployment has "gpt-4o", "GPT-4o",
    ModelDeployment has "embedding", "Embeddings", "Other")
| extend EstCost_USD = case(
    ModelFamily == "GPT-4o-mini",
        (TokensPrompt / 1000.0) * 0.00015 + (TokensCompletion / 1000.0) * 0.0006,
    ModelFamily == "GPT-4o",
        (TokensPrompt / 1000.0) * 0.005 + (TokensCompletion / 1000.0) * 0.015,
    ModelFamily == "Embeddings", (TokensPrompt / 1000.0) * 0.00013, 0.0)
| summarize TotalRequests = count(),
    EstimatedCost_USD = round(sum(EstCost_USD), 2),
    P95Latency_ms = round(percentile(duration, 95), 0),
    ErrorRate_pct = round(100.0 * countif(success == false) / count(), 2),
    UniqueUsers = dcount(tostring(customDimensions["UserId"]))
    by TenantId, ModelFamily, Date = bin(timestamp, 1d)
| order by Date desc, TenantId asc
```

**Power BI Configuration:**

| Setting | Value |
|---------|-------|
| **Data Source** | Azure Log Analytics |
| **Connection Mode** | DirectQuery (real-time) or Import (performance) |
| **Refresh Frequency** | 15 min (DirectQuery) / 1 hour (Import) |
| **Parameters** | `StartDate`, `EndDate` mapped to date slicers |
| **Row Limit** | 500,000 rows (Log Analytics limit) |

---

## Dashboard Layout Recommendations

### Executive Dashboard (Audience: Leadership, FinOps)

| Position | Widget | KQL Source | Refresh |
|----------|--------|------------|---------|
| **Top-Left** | Total Cost (MTD) — Single Value | CST-001 | 1h |
| **Top-Center** | DAU / MAU — Single Value | USR-001 | 1h |
| **Top-Right** | Platform SLO Status — Scorecard | LAT-001 + ERR-001 | 5m |
| **Mid-Left** | Cost by Tenant — Stacked Bar | CST-001 | 1h |
| **Mid-Right** | Daily Cost Trend — Line Chart | CST-002 | 1h |
| **Bottom-Left** | Token Usage by Model — Pie Chart | TOK-002 | 1h |
| **Bottom-Right** | Budget Burn Rate — Gauge | TOK-004 | 6h |

### Operations Dashboard (Audience: Platform Team, SRE)

| Position | Widget | KQL Source | Refresh |
|----------|--------|------------|---------|
| **Top-Left** | P50/P95/P99 Latency — Line Chart | LAT-001 | 5m |
| **Top-Center** | Error Rate — Line Chart | ERR-001 | 5m |
| **Top-Right** | Active Alerts — Count + List | Azure Monitor | Real-time |
| **Mid-Left** | Latency by Endpoint — Bar Chart | LAT-002 | 5m |
| **Mid-Center** | Dependency Health — Heatmap | LAT-006 | 5m |
| **Mid-Right** | 5xx Spike Timeline — Scatter | ERR-004 | 5m |
| **Bottom-Left** | AKS CPU/Memory — Area Chart | INF-001 | 5m |
| **Bottom-Center** | Cosmos DB RU — Area Chart | INF-003 | 5m |
| **Bottom-Right** | Function Executions — Bar Chart | INF-002 | 15m |

### AI Quality Dashboard (Audience: AI/ML Team, Product)

| Position | Widget | KQL Source | Refresh |
|----------|--------|------------|---------|
| **Top-Left** | Groundedness Score Trend — Line Chart | RAG-001 | 1h |
| **Top-Center** | Hallucination Rate — Single Value | RAG-002 | 1h |
| **Top-Right** | Citation Coverage — Single Value | RAG-003 | 1h |
| **Mid-Left** | Zero-Result Rate — Line Chart | RAG-004 | 1h |
| **Mid-Right** | Cache Hit Ratio — Gauge | CAC-001 | 15m |
| **Bottom-Left** | Top Query Patterns — Table | USR-004 | 1h |
| **Bottom-Right** | Content Filter Blocks — Bar Chart | SEC-003 | 1h |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document** | Monitoring & Observability — KQL Query Library |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Approved By** | Platform Architect, SRE Lead |
| **Distribution** | Platform Engineering, SRE, AI/ML, SecOps, FinOps |
