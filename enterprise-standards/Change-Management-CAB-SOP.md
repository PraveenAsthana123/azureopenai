# Change Management / CAB SOP — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 + ITIL v4 + ISO 42001 Aligned**
>
> Ensures controlled change without slowing delivery.

---

## Master Control Table

| # | Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Scope & Change Types** | Avoid ambiguity | Define what is a change | App, infra, data, AI, config | Change policy |
| 2 | **Change Classification** | Apply right rigor | Classify change | Standard / Normal / Emergency | Classification guide |
| 3 | **Change Intake** | Centralize control | Submit change request (CR) | Single intake channel | Change request form |
| 4 | **Change Description** | Enable informed decisions | Document what/why/how | Clear & complete CR | CR details |
| 5 | **Impact Analysis** | Prevent unintended damage | Assess tech, business, security | Mandatory analysis | Impact assessment |
| 6 | **Risk Assessment** | Right-size governance | Rate risk level | Low/Medium/High | Risk score |
| 7 | **Dependency Identification** | Avoid hidden breakage | Identify upstream/downstream deps | All deps listed | Dependency matrix |
| 8 | **Testing Evidence** | Ensure readiness | Attach test results | DoD satisfied | Test reports |
| 9 | **Security & Compliance Review** | Prevent violations | Security sign-off if needed | Mandatory for high-risk | Security review |
| 10 | **AI / GenAI Change Review** | Control AI-specific risk | Model/prompt/RAG review | Eval results required | AI change checklist |
| 11 | **Rollback Plan** | Enable safe reversal | Define rollback steps | Rollback mandatory | Rollback plan |
| 12 | **Implementation Window** | Minimize business impact | Schedule approved window | Change freeze honored | Change calendar |
| 13 | **CAB Review** | Enforce governance | CAB reviews CR | Quorum required | CAB minutes |
| 14 | **Approval / Rejection** | Clear accountability | Approve, reject, or defer | Role-based approval | Approval record |
| 15 | **Pre-Implementation Checks** | Catch last-minute issues | Verify readiness | Go/No-Go checklist | Pre-check logs |
| 16 | **Change Implementation** | Controlled execution | Execute per plan | No deviation | Implementation logs |
| 17 | **Post-Implementation Validation** | Confirm success | Verify health & KPIs | Acceptance criteria met | Validation report |
| 18 | **Emergency Changes** | Restore service fast | Expedited approval | Retrospective mandatory | Emergency CR |
| 19 | **Change Communication** | Align stakeholders | Notify impacted parties | Timely comms | Notifications |
| 20 | **Incident Linkage** | Learn from failures | Link changes → incidents | Root cause tracked | Incident links |
| 21 | **Documentation Update** | Preserve knowledge | Update docs/ADRs | Mandatory | Updated docs |
| 22 | **Change Closure** | Complete lifecycle | Close CR with evidence | Closure review | Closure record |
| 23 | **Metrics & KPIs** | Measure effectiveness | Track change success | KPIs reviewed | Metrics dashboard |
| 24 | **Audit & Compliance** | Prove control | Retain change records | Retention enforced | Audit trail |
| 25 | **Governance & Review Cadence** | Improve process | Periodic SOP review | Leadership sign-off | Review minutes |

---

## Change Types

| Change Type | Description | CAB Required |
|-------------|-------------|--------------|
| **Standard** | Pre-approved, low-risk, repeatable | No |
| **Normal** | Planned, assessed change | Yes |
| **Emergency** | Urgent fix to restore service | Post-approval |

---

## Non-Negotiable Rules

| Rule | Rationale |
|------|-----------|
| No production change without a CR | Traceability |
| No change without rollback plan | Recovery capability |
| No undocumented emergency changes | Audit compliance |
| CI/CD evidence required for Normal changes | Quality assurance |
| Emergency changes must be reviewed post-fact | Learning & compliance |

---

## AI / GenAI-Specific CAB Add-Ons

| Requirement | Evidence |
|-------------|----------|
| Model version, prompt version, embedding version identified | Version manifest |
| Evaluation results attached (bias, safety, performance) | Eval reports |
| Cost impact (token usage) assessed | Cost estimate |
| Rollback to previous model/index tested | Rollback test results |
| Human-in-the-loop preserved if required | HITL verification |

---

## Key Change Management KPIs

| Metric | Target |
|--------|--------|
| Change success rate | > 95% |
| Change failure rate | < 5% |
| Emergency change percentage | < 10% |
| Mean time to implement change | Trending down |
| Incidents caused by change | < 5% of incidents |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| CAB becomes bureaucratic gate | Velocity drops, shadow changes |
| Emergency changes bypass process forever | No learning, repeated failures |
| No rollback tested | Prolonged outages |
| AI changes treated as "experiments" | Production incidents |
| Metrics not reviewed | No improvement |

---

## Change Request Template

```markdown
## Change Request

**CR ID:** [Auto-generated]
**Requestor:** [Name]
**Date:** [Date]

### Change Details
- **Type:** Standard / Normal / Emergency
- **Summary:** [Brief description]
- **Business Justification:** [Why is this needed?]

### Impact Analysis
- **Systems Affected:** [List]
- **Dependencies:** [Upstream/downstream]
- **Risk Level:** Low / Medium / High

### Implementation
- **Planned Window:** [Date/Time]
- **Duration:** [Estimated]
- **Rollback Plan:** [Steps]

### Testing Evidence
- [ ] Unit tests passed
- [ ] Integration tests passed
- [ ] Security scan passed

### Approvals
- [ ] Technical Lead
- [ ] Security (if required)
- [ ] CAB (if Normal/Emergency)
```

---

## Executive Summary

> **Change Management ensures every production change is assessed, approved, implemented, validated, and learned from—without blocking innovation.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / SOP |
| Applicable To | All production changes |
| Framework Alignment | CMMI L3, ITIL v4, ISO 42001, NIST |
