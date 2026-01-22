# Environment Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Ready**
>
> Ensures environment parity, security, repeatability, and auditability.

---

## Master Control Table

| # | Environment Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|-----------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Environment Types** | Avoid ambiguity | Define standard envs | Dev / Test / QA / Staging / Prod | Environment catalog |
| 2 | **Environment Parity** | Prevent "works in dev" issues | Same architecture pattern across envs | No functional drift | Parity checklist |
| 3 | **Provisioning Method** | Ensure repeatability | Provision via IaC only | No manual creation | IaC templates |
| 4 | **Configuration Management** | Prevent misconfiguration | Externalized config per env | No hard-coded values | Config files |
| 5 | **Secrets Management** | Protect credentials | Vault/KMS usage | No secrets in code | Secrets policy |
| 6 | **Access Control (IAM)** | Enforce least privilege | Role-based access per env | Prod access restricted | IAM policy |
| 7 | **Network Segmentation** | Reduce attack surface | Define network boundaries | Private endpoints where required | Network diagrams |
| 8 | **Data Handling Rules** | Prevent data leaks | Define allowed data per env | No prod PII in non-prod | Data usage policy |
| 9 | **Test Data Strategy** | Enable safe testing | Synthetic/masked data | Masking required | Test data plan |
| 10 | **AI/Model Environment Handling** | Prevent AI drift | Separate model versions per env | No prod model in dev | Model registry records |
| 11 | **RAG Corpus Separation** | Prevent cross-env leakage | Separate indices per env | No shared vector DB | RAG env config |
| 12 | **Resource Sizing** | Control cost & performance | Right-size per env | Budget limits enforced | Resource plans |
| 13 | **Cost Controls (FinOps)** | Prevent runaway spend | Budgets & quotas per env | Alerts enabled | Cost dashboards |
| 14 | **Logging & Monitoring** | Enable observability | Centralized logs/metrics | Mandatory in all envs | Monitoring config |
| 15 | **Environment Naming & Tagging** | Improve traceability | Standard naming/tagging | Env, owner, cost center | Tag policy |
| 16 | **CI/CD Integration** | Automate env usage | Pipeline-driven deploys | No manual prod deploy | Pipeline configs |
| 17 | **Promotion Rules** | Control flow between envs | Artifact promotion only | Build once, deploy many | Promotion records |
| 18 | **Environment Reset & Cleanup** | Avoid drift & cost | Scheduled teardown/reset | Ephemeral envs preferred | Cleanup logs |
| 19 | **Availability & Resilience** | Protect critical envs | HA required for prod | DR tested | DR plan |
| 20 | **Security Baseline** | Standardize protection | Hardened baseline configs | CIS benchmarks | Security baseline |
| 21 | **Compliance Controls** | Stay audit-ready | Apply required controls | Logging & retention | Compliance mapping |
| 22 | **Change Management** | Control env changes | Approved changes only | CAB for prod | Change records |
| 23 | **Environment Validation** | Ensure readiness | Health & smoke tests | Pass before use | Validation reports |
| 24 | **Documentation & Diagrams** | Reduce tribal knowledge | Maintain env docs | Updated diagrams | Env documentation |
| 25 | **Ownership & Governance** | Prevent orphan envs | Assign env owners | SLA defined | RACI |

---

## Environment Types

| Environment | Purpose | Access | Data |
|-------------|---------|--------|------|
| **Dev** | Development & debugging | Developers | Synthetic |
| **Test** | Automated testing | CI/CD | Synthetic |
| **QA** | Manual testing | QA team | Synthetic/Masked |
| **Staging** | Pre-prod validation | DevOps | Masked subset |
| **Prod** | Production workloads | Restricted | Real |

---

## Non-Negotiable Rules

| Rule | Rationale |
|------|-----------|
| No manual provisioning (IaC only) | Repeatability |
| No production data in non-prod environments | Data protection |
| No shared environments between unrelated teams | Isolation |
| No direct prod access without approval | Security |
| Same artifact across all environments | Consistency |

---

## AI / GenAI Environment Add-Ons

| Requirement | Implementation |
|-------------|----------------|
| Model versions pinned per environment | Model registry |
| Prompt versions tracked per environment | Version control |
| Separate evaluation datasets | Data management |
| Token usage limits per environment | Cost controls |
| No cross-environment vector search | Index isolation |

---

## Environment Parity Matrix

| Aspect | Dev | Staging | Prod |
|--------|-----|---------|------|
| Architecture | Same | Same | Same |
| Config pattern | Same | Same | Same |
| Network topology | Simplified | Same | Full |
| Data | Synthetic | Masked | Real |
| Scale | Minimal | Medium | Full |
| Security | Standard | Enhanced | Full |

---

## Resource Sizing Guidelines

| Environment | Compute | Storage | AI Capacity |
|-------------|---------|---------|-------------|
| Dev | Minimal | Minimal | Low quota |
| Test | Minimal | Minimal | Low quota |
| Staging | Medium | Medium | Medium quota |
| Prod | Full scale | Full scale | Full quota |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Snowflake environments | "Works in dev" failures |
| Prod data copied to test | Data breach risk |
| Manual hotfixes in prod | Drift, instability |
| Shared vector DB across envs | Data leakage |
| No cost controls in non-prod | Budget overruns |

---

## Environment Validation Checklist

```markdown
Before Use:
- [ ] IaC deployment successful
- [ ] Configuration validated
- [ ] Secrets accessible
- [ ] Network connectivity verified
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Access controls verified
```

---

## Executive Summary

> **An Environment Standard ensures every environment is consistent, secure, cost-controlled, and governed—so failures are predictable and recoverable.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All environments |
| Framework Alignment | CMMI L3, ISO 42001 |
