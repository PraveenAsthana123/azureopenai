# Observability Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Ready**
>
> Makes systems measurable, debuggable, auditable, and cost-aware.

---

## Master Control Table

| # | Observability Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|-------------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Observability Scope** | Focus on what matters | Identify critical journeys & services | Business-critical paths covered | Observability scope doc |
| 2 | **Signals Definition** | Avoid partial visibility | Define Logs, Metrics, Traces (LMT) | All three required | Signal inventory |
| 3 | **Logging Standard** | Enable fast diagnosis | Structured logs (JSON) | No plain text logs | Logging config |
| 4 | **Log Content Rules** | Ensure usefulness & safety | Define mandatory fields | timestamp, level, service, trace_id | Log schema |
| 5 | **PII/PHI Handling** | Prevent data leakage | Mask/redact sensitive fields | No raw PII in logs | Redaction rules |
| 6 | **Metrics Standard** | Measure health & capacity | Define golden signals | latency, traffic, errors, saturation | Metrics catalog |
| 7 | **Tracing Standard** | Enable end-to-end visibility | Propagate trace context | Correlation IDs everywhere | Tracing config |
| 8 | **Service-Level Objectives (SLOs)** | Make reliability measurable | Define SLOs & error budgets | Approved thresholds | SLO definitions |
| 9 | **Alerting Strategy** | Reduce alert fatigue | Alert on symptoms, not noise | SLO-based alerts | Alert policy |
| 10 | **Dashboard Standard** | Enable fast insight | Standard dashboards per service | Health + business views | Dashboard templates |
| 11 | **Deployment Observability** | Detect release issues early | Enable deploy markers | Version tagged in telemetry | Release markers |
| 12 | **CI/CD Integration** | Shift observability left | Validate logging/metrics in pipeline | Missing telemetry fails build | CI checks |
| 13 | **Environment Separation** | Prevent signal mixing | Separate telemetry per env | No cross-env mixing | Env configs |
| 14 | **Retention & Cost Control** | Manage storage cost | Define retention tiers | Hot/warm/cold policies | Retention policy |
| 15 | **Access Control** | Protect observability data | Role-based access | Least privilege | IAM policy |
| 16 | **Incident Support** | Speed MTTR | Link alerts → runbooks | On-call workflows | Runbooks |
| 17 | **Post-Incident Analysis** | Learn from failures | Use telemetry for RCA | Blameless postmortems | PIR reports |
| 18 | **Performance Correlation** | Find bottlenecks | Correlate traces + metrics | Single pane of glass | Correlation evidence |
| 19 | **AI/GenAI Observability** | Prevent silent AI failures | Track AI-specific metrics | latency, drift, cost | AI observability report |
| 20 | **RAG Observability** | Improve retrieval quality | Track retrieval metrics | recall proxy, cache hit | RAG dashboards |
| 21 | **Security Monitoring** | Detect abuse & attacks | Monitor auth & anomaly signals | OWASP patterns | Security alerts |
| 22 | **Data Pipeline Observability** | Ensure data freshness | Monitor data SLAs | Freshness, completeness | Data SLIs |
| 23 | **Ownership & SLAs** | Prevent orphaned signals | Assign owners per signal | SLA defined | RACI |
| 24 | **Audit & Compliance** | Prove control & traceability | Retain logs & metrics | Retention enforced | Audit logs |
| 25 | **Continuous Improvement** | Keep signals relevant | Review & prune signals | Quarterly review | Improvement backlog |

---

## Mandatory Observability Fields

Every log/trace must include:

| Field | Purpose |
|-------|---------|
| `timestamp` | When it happened |
| `service_name` | Which service |
| `environment` | Which environment |
| `version` | Which version |
| `trace_id` / `correlation_id` | Request correlation |
| `request_id` | Unique request identifier |
| `severity` | Log level |
| `tenant_id` | Multi-tenant isolation |

---

## Golden Signals (Minimum Set)

| Signal | What to Measure |
|--------|-----------------|
| **Latency** | P50, P95, P99 response times |
| **Traffic** | Requests per second (RPS) |
| **Errors** | Error rate, error types |
| **Saturation** | CPU, memory, queue depth |

---

## AI / GenAI / RAG Observability Add-Ons

| Metric | Purpose |
|--------|---------|
| Inference latency (end-to-end) | User experience |
| Token usage per request | Cost tracking |
| Cost per request | FinOps |
| Model/prompt version | Traceability |
| Hallucination proxy signals | Quality monitoring |
| Retrieval metrics (top-k latency, cache hit) | RAG performance |

---

## Alerting Rules (Good vs Bad)

| Good | Bad |
|------|-----|
| Alert when SLO is breached | Alert on every error/log line |
| Page humans only on user-impacting issues | Page for non-prod noise |
| Actionable alerts with runbook links | Generic "something is wrong" |
| Aggregate before alerting | Alert per instance |

---

## SLO Examples

| Service | SLI | SLO Target |
|---------|-----|------------|
| API Gateway | Availability | 99.9% |
| API Gateway | Latency (P95) | < 500ms |
| RAG Service | Query success rate | 99.5% |
| OpenAI Integration | Latency (P95) | < 5s |

---

## Log Schema Example

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "service": "rag-api",
  "environment": "prod",
  "version": "1.2.3",
  "trace_id": "abc123",
  "request_id": "req-456",
  "tenant_id": "tenant-789",
  "message": "Query completed",
  "duration_ms": 234,
  "tokens_used": 150
}
```

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Logs without structure | Unparseable, unsearchable |
| No correlation IDs | Cannot trace requests |
| Alerts on everything | Alert fatigue, ignored |
| AI systems with zero telemetry | Silent failures |
| Metrics collected but never reviewed | Waste of resources |

---

## Executive Summary

> **Observability is the ability to explain system behavior from the outside using signals that are consistent, correlated, and actionable.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All services |
| Framework Alignment | CMMI L3, ISO 42001 |
