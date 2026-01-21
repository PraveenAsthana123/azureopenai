# Developer Onboarding Guide — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Teams**
>
> Designed to make new developers productive fast without increasing risk.

---

## Master Control Table

| # | Onboarding Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|-----------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Welcome & Context** | Set expectations | Intro session + docs | Code of conduct acknowledged | Welcome pack |
| 2 | **Org & Product Overview** | Understand the "why" | Explain business, users, value | Product vision clarity | Product overview doc |
| 3 | **Architecture Overview** | Avoid blind coding | Walk through reference architecture | C4 diagrams mandatory | Architecture deck |
| 4 | **SDLC & SOP Orientation** | Enforce how work is done | Review SDLC, DoR/DoD | SOP acceptance required | SOP acknowledgment |
| 5 | **Access Request Process** | Prevent over-privilege | Role-based access request | Least privilege | Access request tickets |
| 6 | **IAM & RBAC Training** | Avoid security incidents | Explain roles, scopes, MFA | No shared accounts | IAM training record |
| 7 | **Development Environment Setup** | Fast local productivity | Setup local dev env | No prod access | Setup guide |
| 8 | **Tooling & IDE Standards** | Reduce friction | Install approved tools | Standard versions | Tool checklist |
| 9 | **Source Control Practices** | Maintain traceability | Branching & commit rules | No direct main commits | Git policy |
| 10 | **Coding Standards** | Consistent codebase | Review language standards | Lint/format enforced | Coding standards doc |
| 11 | **Unit & Integration Testing** | Quality by default | Explain test expectations | Tests required | Test standards |
| 12 | **CI/CD Pipeline Walkthrough** | Know the gates | Explain pipeline stages | Pipeline is authority | Pipeline docs |
| 13 | **Secrets & Key Handling** | Prevent leaks | Vault/KMS usage | No secrets in code | Secrets SOP |
| 14 | **Security Awareness** | Reduce human risk | Secure coding & threats | Annual training | Security training log |
| 15 | **AI / GenAI Guardrails** | Prevent AI misuse | Prompt, model, RAG rules | AI policy sign-off | AI usage policy |
| 16 | **Data Handling Rules** | Prevent data breaches | Data classification & masking | No prod data in dev | Data policy |
| 17 | **Observability Basics** | Operate responsibly | Logs, metrics, traces | Correlation IDs mandatory | Observability guide |
| 18 | **Runbooks & Playbooks** | Operate under pressure | Review key runbooks | Read-only execution initially | Runbook catalog |
| 19 | **Incident Response Overview** | Preparedness | Explain IR process & roles | IC authority respected | IR SOP |
| 20 | **Change Mgmt & CAB** | Controlled releases | Explain change process | No prod change bypass | CAB SOP |
| 21 | **Release & Deployment Process** | Safe delivery | Explain release flow | Rollback awareness | Release docs |
| 22 | **Code Review Expectations** | Quality culture | Peer review checklist | No self-approval | PR guidelines |
| 23 | **First Task (Starter Story)** | Hands-on learning | Assigned low-risk task | Mentor required | Starter ticket |
| 24 | **Mentorship & Shadowing** | Accelerate learning | Pair with senior dev | Time-boxed | Mentorship plan |
| 25 | **Knowledge Base Access** | Self-service learning | Wiki/docs access | Docs kept current | KB links |
| 26 | **Compliance & Audit Awareness** | Avoid surprises | Explain evidence mindset | "If not logged, not done" | Compliance brief |
| 27 | **Feedback & Q&A Loop** | Improve onboarding | Regular check-ins | Issues tracked | Feedback notes |
| 28 | **Readiness Assessment** | Confirm independence | Review checklist | Tech lead sign-off | Readiness checklist |
| 29 | **Ongoing Training Plan** | Continuous growth | Skill roadmap | Required courses | Training plan |
| 30 | **Onboarding Completion** | Formal closure | Final review | Access verified | Completion record |

---

## 30–60–90 Day Milestones

| Timeline | Expected Outcome |
|----------|------------------|
| **0–30 days** | Local env running, first PR merged |
| **31–60 days** | Owns a small component, on-call shadow |
| **61–90 days** | Delivers independently, reviews PRs |

---

## AI / GenAI-Specific Onboarding Add-Ons

| Topic | Training Content |
|-------|------------------|
| Prompt Safety | Injection awareness, safe prompt patterns |
| Model Governance | Version control, approval process |
| RAG Data Access | Authorized sources, tenant isolation |
| Cost Awareness | Token usage, budget limits |
| Human-in-the-Loop | When and how to escalate |

---

## Onboarding Checklist Template

### Week 1: Foundation
- [ ] Welcome session completed
- [ ] Code of conduct acknowledged
- [ ] Access requests submitted
- [ ] Dev environment setup
- [ ] Architecture overview attended

### Week 2: Technical Deep-Dive
- [ ] SDLC/SOP training completed
- [ ] CI/CD pipeline understood
- [ ] Coding standards reviewed
- [ ] First PR submitted

### Week 3: Operations & Security
- [ ] Security awareness training
- [ ] Secrets handling SOP reviewed
- [ ] Observability basics understood
- [ ] Runbooks reviewed

### Week 4: Independence
- [ ] Starter story completed
- [ ] Code review given
- [ ] Readiness assessment passed
- [ ] Tech lead sign-off

---

## Executive Summary

> **Developer onboarding transforms new hires into productive, compliant, and security-aware contributors—fast.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All new developers |
| Framework Alignment | CMMI L3, ISO 42001 |
