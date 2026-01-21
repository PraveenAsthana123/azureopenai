# AI Governance Framework Comparison

> **CMMI Level 3 + ISO/IEC 42001 + NIST AI RMF**
>
> Enterprise AI Operating Model — Auditor-Ready Reference

---

## Framework Overview

| Framework | Primary Purpose | Core Question |
|-----------|-----------------|---------------|
| **CMMI Level 3** | Process maturity & consistency | How do we build and deliver consistently? |
| **ISO/IEC 42001** | AI governance, trust & compliance | How do we govern AI responsibly? |
| **NIST AI RMF** | Risk quantification & measurement | Can we prove the risk is under control? |

---

## CMMI Level 3 vs ISO/IEC 42001 — Side-by-Side

| Dimension | CMMI Level 3 (Defined) | ISO/IEC 42001 (AIMS) |
|-----------|------------------------|----------------------|
| Primary Purpose | Process maturity & consistency | AI governance, trust & compliance |
| Scope | Projects & organizational processes | Enterprise AI systems & lifecycle |
| Focus Area | Execution discipline | Risk, ethics, accountability |
| Applies To | All engineering & delivery work | AI / GenAI / ML systems only |
| Level / Nature | Maturity level (1–5) | Management system standard |
| Outcome | Repeatable, defined processes | Trustworthy, auditable AI |
| Drivers | Quality, predictability | Regulation, ethics, risk |

### Process Coverage

| Area | CMMI Level 3 | ISO 42001 |
|------|--------------|-----------|
| Requirements | Structured & traceable | Risk-aware AI use-case approval |
| Estimation | Mandatory effort/cost models | Not primary focus |
| Project Planning | Detailed execution plans | Governance alignment |
| Process Assets | Organizational SOPs | AI policies & controls |
| Infrastructure | Tools & environments | Secure AI operations |
| Technical Design | Engineering correctness | Responsible AI design |
| Integration | Controlled system integration | Safe deployment controls |
| Configuration | Version & change control | Model & data change governance |
| Risk Management | Project & technical risk | AI harm, bias, legal risk |
| Peer Reviews | Quality inspections | Ethical & compliance reviews |
| Verification & Validation | Meets specs & needs | Safe, fair, explainable AI |
| Monitoring & Control | Schedule, cost, quality | Continuous AI monitoring |
| Governance | Project governance | Enterprise AI governance |

---

## How NIST AI RMF Complements ISO 42001

| Aspect | ISO/IEC 42001 | NIST AI RMF |
|--------|---------------|-------------|
| Primary role | Governance system | Risk quantification |
| Focus | Policies & controls | Measurement & mitigation |
| Risk handling | High-level | Metric-driven |
| AI harm | Managed | Measured |
| Outcome | Compliance | Risk reduction |

**Key Distinction:**
- **ISO 42001** = "Do you govern AI?"
- **NIST AI RMF** = "Can you prove the risk is under control?"

---

## AI / GenAI Perspective

| Aspect | CMMI Level 3 | ISO 42001 | NIST AI RMF |
|--------|--------------|-----------|-------------|
| GenAI usage | Process-controlled | Policy-controlled | Risk-measured |
| Prompt management | Change managed | Safety & misuse controlled | Attack-tested |
| RAG pipelines | Engineering standards | Data provenance & leakage control | Leakage metrics |
| Hallucinations | Quality defect | AI risk & harm | Performance metrics |
| Bias | Quality issue | Ethical & compliance risk | Fairness scorecards |
| Human oversight | Optional | Mandatory | Oversight effectiveness |
| Third-party AI | Supplier management | Vendor AI risk governance | Vendor risk scores |

---

## GenAI / RAG / LLM Risk Mapping

| GenAI Risk | CMMI L3 Control | ISO 42001 Control | NIST AI RMF Control |
|------------|-----------------|-------------------|---------------------|
| Hallucinations | Quality testing | Risk assessment | Measure → Performance & Harm |
| Prompt injection | Code review | Security controls | Measure → Security & Robustness |
| RAG data leakage | Config management | Data governance | Map → Data Context |
| Bias drift | Verification | Ethics review | Measure → Fairness |
| Model misuse | Access control | HITL oversight | Manage → Monitoring |
| Vendor LLM risk | Supplier mgmt | Vendor governance | Third-party risk |

---

## Audit & Evidence Comparison

| Area | CMMI L3 Auditors | ISO 42001 Auditors | NIST AI RMF Auditors |
|------|------------------|--------------------|--------------------|
| Documentation | SOPs, templates | AI policies, registers | Risk metrics, test reports |
| Consistency | Same process everywhere | Same governance everywhere | Same measurement everywhere |
| Training | Role-based process training | Responsible AI training | Risk awareness training |
| Risk | Logged & mitigated | Assessed & monitored | Quantified & scored |
| Decisions | Documented DAR | Explainable AI decisions | Evidence-based treatment |
| Enforcement | Process compliance | Ethical & legal compliance | Risk threshold enforcement |

---

## Strengths & Gaps

| Aspect | CMMI Level 3 | ISO 42001 | NIST AI RMF |
|--------|--------------|-----------|-------------|
| **Strength** | Execution rigor | Trust & compliance | Risk quantification |
| **Gap** | AI ethics & harm | Delivery discipline | Governance structure |
| **Best For** | Large delivery orgs | Regulated AI orgs | Risk-focused orgs |
| **Limitation** | Not AI-specific | Not delivery-specific | Not governance-specific |

---

## How They Fit Together (Enterprise Reality)

| Layer | Primary Framework | Supporting Framework |
|-------|-------------------|---------------------|
| Strategy & Governance | ISO/IEC 42001 | NIST AI RMF |
| AI Risk & Ethics | ISO/IEC 42001 | NIST AI RMF |
| Risk Quantification | NIST AI RMF | ISO/IEC 42001 |
| Execution & Delivery | CMMI Level 3 | ISO/IEC 42001 |
| Quality & Consistency | CMMI Level 3 | NIST AI RMF |

```
┌─────────────────────────────────────────────────────────┐
│                    ENTERPRISE AI                         │
├─────────────────────────────────────────────────────────┤
│  ISO 42001: "What is allowed and safe"                  │
│  ├── AI Policy & Governance                             │
│  ├── Risk Assessment & Ethics                           │
│  └── Compliance & Accountability                        │
├─────────────────────────────────────────────────────────┤
│  NIST AI RMF: "Prove risk is under control"             │
│  ├── Risk Quantification                                │
│  ├── Measurement & Testing                              │
│  └── Evidence & Metrics                                 │
├─────────────────────────────────────────────────────────┤
│  CMMI Level 3: "How it is built and delivered"          │
│  ├── Process Standardization                            │
│  ├── Execution Discipline                               │
│  └── Quality & Predictability                           │
└─────────────────────────────────────────────────────────┘
```

---

## Combined Control Matrix

| Control Area | CMMI L3 Artifact | ISO 42001 Artifact | NIST AI RMF Artifact |
|--------------|------------------|--------------------|--------------------|
| Governance | Process Library | AI Policy | Governance Charter |
| Risk | Risk Register | AI Risk Register | Risk Metrics |
| Data | Data Specs | Data Governance Register | Data Flow Diagrams |
| Model | Architecture Doc | Model Cards | Bias Reports |
| Testing | Test Plan & Results | Bias Test Reports | Fairness Scorecards |
| Deployment | CM Plan | Deployment Controls | Security Test Reports |
| Monitoring | KPI Dashboard | Monitoring Logs | Drift Logs |
| Incidents | CAPA | Incident Reports | CAPA with Metrics |
| Vendors | Supplier Assessments | Vendor Risk Register | Vendor Risk Scores |
| Training | Training Records | AI Training Records | Risk Training Records |

---

## Unified Audit Checklist

### Governance Layer (ISO 42001 Primary)
- [ ] AI Policy approved and published
- [ ] AI Use-Case Inventory complete
- [ ] AI Governance Charter with roles
- [ ] RACI for AI accountability
- [ ] AI risk classification criteria

### Risk Quantification Layer (NIST AI RMF Primary)
- [ ] Risk metrics defined
- [ ] Bias testing completed with scores
- [ ] Performance benchmarks documented
- [ ] Security/adversarial testing done
- [ ] Drift monitoring active

### Execution Layer (CMMI L3 Primary)
- [ ] Standard AI lifecycle defined
- [ ] Process assets published
- [ ] Project plans baselined
- [ ] Peer reviews conducted
- [ ] Configuration managed

### Cross-Cutting
- [ ] Human-in-the-loop documented
- [ ] Incident response tested
- [ ] Vendor AI risk assessed
- [ ] Training records current
- [ ] Continuous improvement logged

---

## Executive Summary

| Framework | One-Line Summary |
|-----------|------------------|
| **CMMI Level 3** | Makes AI delivery predictable |
| **ISO/IEC 42001** | Makes AI deployment trustworthy |
| **NIST AI RMF** | Turns AI risk into auditable evidence |

> **Together, they form an enterprise-grade AI operating model.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Audit-Ready |
| Applicable To | AI, GenAI, ML, RAG, Robotics, LLM |
| Framework References | CMMI V2.0, ISO/IEC 42001:2023, NIST AI RMF 1.0 |
