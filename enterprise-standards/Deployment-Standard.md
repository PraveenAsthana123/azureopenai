# Deployment Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Ready**
>
> Makes deployments repeatable, low-risk, observable, and reversible.

---

## Master Control Table

| # | Deployment Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|-----------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Deployment Strategy Selection** | Minimize blast radius | Choose strategy per service | Canary / Blue-Green / Rolling | Deployment strategy ADR |
| 2 | **Artifact Immutability** | Prevent drift | Build once, deploy same artifact | No rebuilds per env | Artifact digest / tag |
| 3 | **Environment Parity** | Reduce surprises | Same topology & config patterns | IaC enforced | IaC templates |
| 4 | **Pre-Deployment Checks** | Catch obvious failures | Health, config, secrets validation | Gate before deploy | Pre-deploy checklist |
| 5 | **Configuration Management** | Avoid misconfig | Externalized config | No secrets in code | Config validation logs |
| 6 | **Secrets & Keys Handling** | Prevent leaks | Vault/KMS integration | Rotation enabled | Secrets policy |
| 7 | **Database & Schema Changes** | Prevent data loss | Backward-compatible migrations | Expand-and-contract | Migration scripts |
| 8 | **AI/Model Deployment** | Safe AI updates | Versioned models/prompts | Rollback supported | Model registry records |
| 9 | **RAG Corpus Deployment** | Prevent bad retrieval | Versioned indices & data | Reindex plan approved | RAG deployment plan |
| 10 | **Traffic Management** | Control exposure | Gradual traffic shift | %-based routing | Traffic rules |
| 11 | **Automated Deployment** | Reduce human error | Pipeline-driven deploy | No manual prod deploys | CI/CD logs |
| 12 | **Health Checks** | Detect failures early | Liveness/readiness probes | Mandatory probes | Health check results |
| 13 | **Observability Enablement** | Diagnose issues | Logs, metrics, traces live | Correlation IDs | Dashboards |
| 14 | **Deployment Validation** | Confirm success | Smoke tests post-deploy | Must pass | Validation report |
| 15 | **Rollback Strategy** | Fast recovery | Define triggers & steps | Tested rollback | Rollback runbook |
| 16 | **Failure Handling** | Limit impact | Auto-abort on failures | Circuit breakers | Abort logs |
| 17 | **Change Management (CAB)** | Governance & audit | Approval where required | Change record | CAB approval |
| 18 | **Security Posture Check** | Prevent exposure | Runtime security checks | No critical findings | Security report |
| 19 | **Performance Guardrails** | Protect UX & cost | P95/P99 checks | Thresholds enforced | Perf metrics |
| 20 | **Multi-Tenant Isolation** | Prevent cross-tenant leaks | Tenant-aware routing & data | Isolation verified | Tenant test results |
| 21 | **Release Communication** | Align stakeholders | Notify ops/support | Advance notice | Release notes |
| 22 | **Hypercare Window** | Catch early issues | Enhanced monitoring | Defined duration | Hypercare plan |
| 23 | **Decommissioning Old Version** | Avoid zombie services | Safe shutdown | Data retention honored | Decommission checklist |
| 24 | **Audit & Traceability** | Prove compliance | Log who/what/when | Immutable logs | Audit trail |
| 25 | **Post-Deployment Review** | Improve process | Review outcomes | Actions tracked | PIR report |

---

## Deployment Strategies

| Strategy | Use When | Risk | Rollback |
|----------|----------|------|----------|
| **Canary** | User-facing services, AI models | Lowest | Traffic shift back |
| **Blue-Green** | Zero-downtime required | Low | Switch to blue |
| **Rolling** | Stateless services | Medium | Roll forward/back |
| **Big-Bang** | Small internal tools only | High (avoid) | Full redeploy |

---

## AI / GenAI Deployment Add-Ons

| Requirement | Implementation |
|-------------|----------------|
| Model, prompt, embedding version pinned | Version manifest |
| Evaluation results attached to deployment | Eval reports |
| Token cost guardrails active | Cost monitoring |
| Human-in-the-loop preserved if required | HITL verification |
| Rollback tested with previous model/index | Rollback test results |

---

## Release-Blocking Conditions

Deployment is aborted if:

| Condition | Threshold |
|-----------|-----------|
| Health checks fail | Any failure |
| Smoke tests fail | Any failure |
| Error rate exceeds threshold | > 5% |
| P95 latency breaches NFR | > defined limit |
| AI eval metrics regress | Beyond tolerance |

---

## Pre-Deployment Checklist

```markdown
Before Deployment:
- [ ] Artifact built and tested
- [ ] Change request approved
- [ ] Rollback plan documented
- [ ] Team notified
- [ ] Monitoring alerts configured

During Deployment:
- [ ] Health checks monitored
- [ ] Error rates tracked
- [ ] Latency monitored
- [ ] Ready to rollback

After Deployment:
- [ ] Smoke tests passed
- [ ] Metrics normal
- [ ] No alerts firing
- [ ] Documentation updated
```

---

## Rollback Triggers

| Trigger | Action |
|---------|--------|
| Error rate > 10% | Immediate rollback |
| P95 latency > 5x baseline | Immediate rollback |
| Health check failures | Immediate rollback |
| Security alert | Stop and assess |
| Customer complaints spike | Assess and decide |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Manual prod deploys | Human error, inconsistency |
| No rollback rehearsed | Slow recovery |
| DB changes not backward-compatible | Data issues |
| AI models updated silently | Unexpected behavior |
| Monitoring added after incident | Blind to problems |

---

## Executive Summary

> **A Deployment Standard ensures every release is automated, observable, reversible, and governed—without slowing delivery.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All deployments |
| Framework Alignment | CMMI L3, ISO 42001 |
