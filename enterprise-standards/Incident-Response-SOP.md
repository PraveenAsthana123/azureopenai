# Incident Response SOP — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 + ISO 42001 + NIST SP 800-61 Aligned**
>
> Operational under pressure, audit-ready, and AI/GenAI aware.

---

## Master Control Table

| # | IR Phase | Purpose (Why) | Standard Process (How) | Mandatory Controls / Rules | Evidence / Artifacts |
|---|----------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Policy & Scope** | Avoid ad-hoc response | Define incident types & severity | P0–P4 classification | IR policy |
| 2 | **Preparation** | Reduce response time | Tools, access, training ready | On-call + runbooks ready | Readiness checklist |
| 3 | **Detection & Alerting** | Identify incidents early | SLO/alert-driven detection | Alerts tied to impact | Alert records |
| 4 | **Incident Identification** | Confirm real incident | Validate signal vs noise | False-positive triage | Incident ticket |
| 5 | **Severity Classification** | Right response level | Classify impact & urgency | Severity matrix enforced | Severity log |
| 6 | **Incident Declaration** | Trigger formal process | Declare incident | IC assigned | Declaration record |
| 7 | **Command & Control** | Centralize decisions | Assign Incident Commander | Single decision owner | IC assignment |
| 8 | **Containment (Short-Term)** | Limit blast radius | Isolate affected components | No unapproved actions | Containment actions |
| 9 | **Containment (Long-Term)** | Prevent recurrence | Apply compensating controls | Approved mitigations | Mitigation records |
| 10 | **Eradication** | Remove root cause | Patch, config fix, revoke access | Root cause addressed | Fix evidence |
| 11 | **Recovery** | Restore normal service | Gradual restore + monitoring | Rollback ready | Recovery logs |
| 12 | **Verification** | Ensure stability | Validate health & SLOs | SLOs met | Verification checklist |
| 13 | **Communication (Internal)** | Align teams | Regular status updates | Update cadence enforced | Status updates |
| 14 | **Communication (External)** | Maintain trust | Customer/regulator comms | Legal/comms approval | External notices |
| 15 | **Security Escalation** | Handle breaches | Trigger IR/security playbook | CISO notified | Security escalation log |
| 16 | **AI / GenAI Incident Handling** | Address AI-specific failures | Model, prompt, RAG isolation | AI kill-switch | AI incident log |
| 17 | **Evidence Preservation** | Support forensics | Preserve logs & artifacts | Chain of custody | Evidence archive |
| 18 | **Root Cause Analysis (RCA)** | Learn what failed | Timeline + 5-Whys | Blameless RCA | RCA report |
| 19 | **Post-Incident Review (PIR)** | Improve system | Review actions & gaps | Mandatory PIR | PIR notes |
| 20 | **Corrective Actions** | Prevent recurrence | Track remediation tasks | Owners & deadlines | Action tracker |
| 21 | **Regulatory & Compliance Review** | Meet obligations | Assess notification duties | Timelines met | Compliance report |
| 22 | **Metrics & KPIs** | Measure effectiveness | Track MTTD, MTTR | Reviewed quarterly | IR metrics |
| 23 | **Training & Drills** | Maintain readiness | Tabletop / game days | Annual minimum | Drill reports |
| 24 | **Documentation Update** | Keep SOP current | Update runbooks & SOP | Versioned updates | Doc history |
| 25 | **Governance & Review** | Enforce discipline | Periodic SOP review | Leadership sign-off | Review minutes |

---

## Severity Classification

| Severity | Description | Example | Response Target |
|----------|-------------|---------|-----------------|
| **P0** | Critical, widespread outage / breach | Data leak, total outage | Immediate, 24x7 |
| **P1** | Major user impact | Core service degraded | ≤ 1 hour |
| **P2** | Limited impact | Partial feature outage | ≤ 4 hours |
| **P3** | Minor issue | Non-critical bug | Business hours |
| **P4** | Informational | Alert without impact | As scheduled |

---

## AI / GenAI-Specific Incident Types

| Incident Type | Playbook Required |
|---------------|-------------------|
| Cross-tenant data leakage (RAG) | Yes |
| Prompt injection / jailbreak exploitation | Yes |
| Hallucinations causing business harm | Yes |
| Token abuse / cost-based DoS | Yes |
| Model drift causing unsafe outputs | Yes |

---

## Mandatory IR Roles

| Role | Responsibility |
|------|----------------|
| **Incident Commander (IC)** | Owns decisions |
| **Ops Lead** | Technical mitigation |
| **Security Lead** | Breach handling |
| **Comms Lead** | Stakeholder messaging |
| **Scribe** | Timeline & evidence |

---

## Incident Response Flow

```
Detection
    ↓
Identification & Classification
    ↓
Declaration (IC Assigned)
    ↓
Containment (Short-term → Long-term)
    ↓
Eradication
    ↓
Recovery
    ↓
Verification
    ↓
Post-Incident Review
    ↓
Corrective Actions
```

---

## Key Metrics (KPIs)

| Metric | Description | Target |
|--------|-------------|--------|
| MTTD | Mean Time to Detect | < 5 min (P0/P1) |
| MTTR | Mean Time to Recover | < 1 hour (P0) |
| Incident recurrence rate | Same root cause | < 10% |
| PIR completion rate | Reviews completed | 100% (P0/P1) |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| No clear incident commander | Chaos, conflicting actions |
| Ad-hoc fixes without containment | Blast radius expands |
| No evidence preservation | Forensics impossible |
| AI incidents treated as "model issues" | Repeated failures |
| No PIR → same incident repeats | Technical debt |

---

## Post-Incident Review Template

```markdown
## Post-Incident Review

**Incident ID:** [ID]
**Date:** [Date]
**Severity:** [P0-P4]
**Duration:** [Start - End]

### Summary
[Brief description of what happened]

### Timeline
| Time | Event |
|------|-------|
| HH:MM | Detection |
| HH:MM | IC assigned |
| HH:MM | Containment |
| HH:MM | Resolution |

### Root Cause
[5-Whys analysis]

### What Went Well
- [Item 1]
- [Item 2]

### What Could Be Improved
- [Item 1]
- [Item 2]

### Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| [Action] | [Name] | [Date] |
```

---

## Executive Summary

> **Incident Response is a disciplined, time-bound process to detect, contain, recover from, and learn from disruptions—without panic or blame.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / SOP |
| Applicable To | All production incidents |
| Framework Alignment | CMMI L3, ISO 42001, NIST SP 800-61, OWASP, MITRE |
