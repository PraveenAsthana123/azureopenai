# NIST AI Risk Management Framework (AI RMF) — Single Master Table

> **Auditor-Ready | AI / GenAI / ML / RAG / Robotics**
>
> This table fills the risk-quantification gap left by CMMI L3 + ISO 42001.

---

## Master Control Table

| # | AI RMF Function | Purpose (Why) | Standard Process (How) | Key Activities | Mandatory Artifacts / Evidence |
|---|-----------------|---------------|------------------------|----------------|-------------------------------|
| 1 | **Govern (GV)** | Establish risk accountability & culture | Define AI risk policy → Assign ownership → Integrate with enterprise risk | AI risk policy, roles, oversight committees | AI Risk Policy, Governance Charter, RACI |
| 2 | **Map (MP)** | Understand AI context & impact | Identify AI use cases → Stakeholders → Impact & harm scenarios | Context analysis, stakeholder mapping, use-case scoping | AI Inventory, Context & Impact Assessment |
| 3 | **Map – Data & System Context** | Understand data & system boundaries | Identify data sources → Dependencies → System interactions | Data lineage, system dependency analysis | Data Flow Diagrams, System Context Docs |
| 4 | **Measure (ME)** | Quantify AI risks | Define metrics → Test → Score risks | Bias testing, robustness testing, accuracy metrics | Risk Metrics, Test Reports |
| 5 | **Measure – Harm & Bias** | Detect unfair or harmful outcomes | Bias evaluation → Fairness metrics → Threshold checks | Demographic parity, error analysis | Bias Reports, Fairness Scorecards |
| 6 | **Measure – Performance & Reliability** | Ensure AI works consistently | Accuracy, drift, latency monitoring | Performance benchmarking, stress testing | Performance Reports, Drift Logs |
| 7 | **Measure – Security & Robustness** | Protect against AI attacks | Adversarial testing → Abuse case testing | Prompt injection tests, poisoning tests | Security Test Reports |
| 8 | **Manage (MG)** | Reduce AI risks | Prioritize → Mitigate → Accept or Reject | Risk treatment decisions | Risk Treatment Plans |
| 9 | **Manage – Controls & Safeguards** | Apply risk controls | Technical, process, human controls | Guardrails, HITL, access control | Control Implementation Records |
| 10 | **Manage – Monitoring** | Detect risk changes over time | Continuous monitoring → Alerts | Drift detection, misuse detection | Monitoring Dashboards, Alerts |
| 11 | **Incident Response** | Respond to AI failures | Detect → Triage → Contain → Recover | Incident classification, root cause | Incident Reports, CAPA |
| 12 | **Transparency & Communication** | Build trust with stakeholders | Document → Communicate → Explain | Model explanations, disclosures | Model Cards, Transparency Reports |
| 13 | **Third-Party & Supply Chain Risk** | Control external AI risk | Assess vendors → Monitor → Reassess | Vendor risk scoring | Vendor Risk Assessments |
| 14 | **Continuous Improvement** | Improve risk posture | Review outcomes → Update controls | Lessons learned, updates | Improvement Logs, Updated Controls |

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

## GenAI / RAG / LLM Risk Mapping

| GenAI Risk | NIST AI RMF Control |
|------------|---------------------|
| Hallucinations | Measure → Performance & Harm |
| Prompt injection | Measure → Security & Robustness |
| RAG data leakage | Map → Data Context |
| Bias drift | Measure → Fairness |
| Model misuse | Manage → Monitoring |
| Vendor LLM risk | Third-party risk |

---

## Auditor Expectations

Auditors will require:

| Requirement | Evidence Type |
|-------------|---------------|
| Quantified risk metrics | Risk scorecards, dashboards |
| Evidence of bias testing | Bias reports, fairness metrics |
| Drift & misuse monitoring | Monitoring logs, alerts |
| Incident handling proof | Incident reports, CAPA records |
| Risk treatment decisions | Treatment plans, approval records |

**Without NIST AI RMF:**
- Risk remains subjective
- "Trustworthy AI" is unprovable

---

## Executive Summary

> **NIST AI RMF turns AI risk from opinions into measurable, auditable evidence.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Audit-Ready |
| Applicable To | AI, GenAI, ML, RAG, Robotics, LLM |
| Framework Reference | NIST AI RMF 1.0 |
