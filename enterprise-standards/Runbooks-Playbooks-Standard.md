# Runbooks & Playbooks — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 + ISO 42001 + NIST Aligned**
>
> Ensures operations are executable, repeatable, and auditable under pressure.

---

## Master Control Table

| # | Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Scope & Classification** | Avoid ad-hoc ops | Classify scenarios | Incident, Ops, Security, AI, DR | Runbook catalog |
| 2 | **Trigger Conditions** | Know when to act | Define clear triggers | Alert/SLO breach mapped | Trigger definitions |
| 3 | **Audience & Ownership** | Prevent confusion | Assign primary/backup owners | 24x7 ownership | RACI |
| 4 | **Preconditions** | Avoid unsafe execution | Validate prerequisites | Access, env, approvals | Preconditions checklist |
| 5 | **Step-by-Step Actions** | Enable execution under stress | Ordered, atomic steps | No ambiguity | Runbook steps |
| 6 | **Decision Points** | Guide human judgment | IF/THEN branches | Escalation paths defined | Decision tree |
| 7 | **Commands & Scripts** | Reduce human error | Provide copy-safe commands | Read-only vs write marked | Command snippets |
| 8 | **Automation Hooks** | Speed response | Link to scripts/tools | Idempotent automation | Automation refs |
| 9 | **Safety Checks** | Prevent damage | Validate before/after actions | Guardrails mandatory | Safety checklist |
| 10 | **Rollback / Recovery** | Enable fast reversal | Define rollback steps | Tested rollback | Rollback section |
| 11 | **Verification Steps** | Confirm success | Define "done" checks | Health/SLO verified | Verification checklist |
| 12 | **Observability Links** | Speed diagnosis | Link dashboards & logs | One-click access | Dashboard links |
| 13 | **Access & Permissions** | Secure execution | Least-privilege access | JIT elevation | Access policy |
| 14 | **Communication Plan** | Coordinate teams | Who/when/how to notify | Templates provided | Comms templates |
| 15 | **Escalation & Handover** | Avoid stalls | Escalation thresholds | On-call rotation | Escalation matrix |
| 16 | **Time Objectives** | Control impact | RTO/RPO or MTTR targets | Targets defined | SLO/IR mapping |
| 17 | **Compliance & Evidence** | Audit readiness | Log actions & decisions | Immutable logs | Audit trail |
| 18 | **Post-Action Review** | Improve quality | Capture outcomes | Mandatory review | PIR notes |
| 19 | **Versioning & Change Control** | Prevent drift | Version runbooks | Approval required | Version history |
| 20 | **Testing & Drills** | Ensure readiness | Tabletop / game days | Scheduled drills | Drill reports |
| 21 | **AI / GenAI Playbooks** | Handle AI failures | Model, RAG, cost incidents | AI-specific steps | AI playbooks |
| 22 | **Security Incident Playbooks** | Contain breaches | Predefined IR flows | No improvisation | IR playbooks |
| 23 | **DR / BCP Playbooks** | Ensure continuity | Failover & restore steps | Annual DR test | DR reports |
| 24 | **Decommissioning Playbooks** | Avoid zombie systems | Safe shutdown steps | Data retention honored | Decom checklist |
| 25 | **Governance & Review Cadence** | Keep runbooks current | Quarterly review | Owner accountability | Review minutes |

---

## Runbook vs Playbook

| Aspect | Runbook | Playbook |
|--------|---------|----------|
| **Purpose** | Exact execution steps | Strategy + decision framework |
| **Usage** | Known, repeatable tasks | Complex or evolving incidents |
| **Automation** | High | Medium |
| **Audience** | Operators / SRE | Incident commanders |
| **Example** | Restart service | Major outage response |

---

## Critical Runbooks (Baseline)

| Runbook | Trigger | Owner |
|---------|---------|-------|
| Service restart / rollback | Failed health check | SRE |
| Failed deployment recovery | Deploy failure alert | DevOps |
| Database failover | DB health alert | DBA |
| Secrets/key rotation | Expiry alert, breach | Security |
| Certificate expiry response | Cert monitor alert | Platform |
| High error-rate mitigation | Error rate SLO breach | SRE |
| Access revoke (user/service) | Offboarding, breach | Security |

---

## Critical Playbooks (Baseline)

| Playbook | Trigger | IC |
|----------|---------|-----|
| P1/P2 outage response | Major incident declared | On-call lead |
| Security breach response | Security alert confirmed | Security lead |
| Data leakage response | Data exposure detected | Security + Legal |
| AI hallucination / abuse response | AI incident detected | AI lead |
| Cost spike (FinOps) response | Budget alert | FinOps lead |
| DR / regional outage response | Region failure | Platform lead |

---

## AI / GenAI-Specific Playbooks

| Playbook | Scenario |
|----------|----------|
| Model rollback procedure | Model regression detected |
| Prompt disable / hotfix | Prompt injection exploited |
| RAG index isolation | Cross-tenant leakage |
| Token abuse / cost DoS response | Abnormal token consumption |
| Human-in-the-loop activation | High-risk AI decision |

---

## Runbook Template

```markdown
# Runbook: [Name]

**Version:** 1.0
**Owner:** [Team/Person]
**Last Tested:** [Date]

## Trigger
- Alert: [Alert name]
- SLO: [Threshold]

## Preconditions
- [ ] Access to [system]
- [ ] Approval from [role] (if required)

## Steps

### 1. Assess
```bash
# Check current state
kubectl get pods -n [namespace]
```

### 2. Mitigate
```bash
# Restart service
kubectl rollout restart deployment/[name]
```

### 3. Verify
```bash
# Confirm health
curl -s https://[endpoint]/health
```

## Rollback
[Steps to revert if mitigation fails]

## Escalation
- After 15 min: Escalate to [team]
- After 30 min: Page [manager]

## Post-Action
- [ ] Update incident ticket
- [ ] Log actions taken
- [ ] Schedule PIR if P0/P1
```

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Too high-level ("restart service") | Unusable under stress |
| Not tested until real incident | Fails when needed |
| No ownership | Never updated |
| Outdated after architecture change | Dangerous misinformation |
| AI systems with zero operational playbooks | Chaos during AI incidents |

---

## Executive Summary

> **Runbooks and playbooks convert incidents from chaos into controlled, auditable, and repeatable responses.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Operational Standard |
| Applicable To | All operational scenarios |
| Framework Alignment | CMMI L3, ISO 42001, NIST, OWASP, MITRE |
