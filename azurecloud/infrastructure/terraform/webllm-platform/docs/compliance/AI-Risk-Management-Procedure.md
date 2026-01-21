# AI Risk Management Procedure
## Document ID: WLP-RISK-001

**Version:** 1.0
**Effective Date:** 2026-01-21
**Owner:** Program Manager
**Classification:** Internal

---

## 1. Purpose

This procedure establishes the framework for identifying, analyzing, evaluating, treating, and monitoring risks associated with AI systems within the WebLLM Platform.

## 2. Scope

This procedure applies to:
- All AI models deployed on the platform
- AI system components (WebLLM, MLC LLM, Azure OpenAI)
- Data processing pipelines
- Agent orchestration systems
- All personnel involved in AI development and operations

## 3. References

- ISO/IEC 42001:2023 Clause 6.1
- CMMI RSKM Process Area
- NIST AI Risk Management Framework

## 4. Definitions

| Term | Definition |
|------|------------|
| AI Risk | Potential for harm arising from AI system behavior |
| Risk Appetite | Amount of risk acceptable to achieve objectives |
| Risk Treatment | Process to modify risk |
| Residual Risk | Risk remaining after treatment |
| Risk Owner | Person accountable for managing a specific risk |

## 5. Risk Management Process

### 5.1 Risk Identification

#### 5.1.1 Methods

| Method | Description | Frequency | Participants |
|--------|-------------|-----------|--------------|
| Brainstorming | Team sessions to identify risks | Per project | Project team |
| Checklist Review | Standard AI risk checklist | Per release | Tech lead, Security |
| Expert Interview | Consult subject matter experts | As needed | Experts |
| Historical Analysis | Review past incidents | Quarterly | All teams |
| Threat Modeling | STRIDE analysis for AI systems | Per major change | Security team |

#### 5.1.2 AI-Specific Risk Categories

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI RISK CATEGORIES                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐│
│  │   DATA RISKS    │     │  MODEL RISKS    │     │ INFERENCE RISKS ││
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤│
│  │• Data quality   │     │• Bias/fairness  │     │• Hallucination  ││
│  │• Data poisoning │     │• Model drift    │     │• Prompt injection││
│  │• Privacy breach │     │• Overfitting    │     │• Jailbreaking   ││
│  │• Data leakage   │     │• Underfitting   │     │• Data extraction││
│  │• Label errors   │     │• Catastrophic   │     │• Adversarial    ││
│  │                 │     │  forgetting     │     │  inputs         ││
│  └─────────────────┘     └─────────────────┘     └─────────────────┘│
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐│
│  │OPERATIONAL RISKS│     │  ETHICAL RISKS  │     │COMPLIANCE RISKS ││
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤│
│  │• Availability   │     │• Discrimination │     │• Regulatory     ││
│  │• Performance    │     │• Misinformation │     │  violation      ││
│  │• Scalability    │     │• Harmful content│     │• Contractual    ││
│  │• Dependencies   │     │• Privacy        │     │  breach         ││
│  │• Configuration  │     │  intrusion      │     │• Data residency ││
│  │• Human error    │     │• Autonomy       │     │• Audit failure  ││
│  └─────────────────┘     │  concerns       │     └─────────────────┘│
│                          └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.1.3 Risk Identification Checklist

**Data Risks:**
- [ ] Is training data representative of production scenarios?
- [ ] Are there potential biases in the training data?
- [ ] Is PII properly handled and protected?
- [ ] Are data sources trustworthy?
- [ ] Is data provenance tracked?

**Model Risks:**
- [ ] Has the model been tested for bias?
- [ ] Are model outputs within expected ranges?
- [ ] Has adversarial testing been performed?
- [ ] Is model performance monitored for drift?
- [ ] Are model versions properly tracked?

**Inference Risks:**
- [ ] Are inputs validated and sanitized?
- [ ] Are outputs filtered for harmful content?
- [ ] Are confidence scores provided and used?
- [ ] Is there human oversight for critical decisions?
- [ ] Are rate limits in place?

**Operational Risks:**
- [ ] Are SLAs defined and monitored?
- [ ] Are failover mechanisms tested?
- [ ] Is capacity planning performed?
- [ ] Are dependencies identified and monitored?
- [ ] Are runbooks up to date?

### 5.2 Risk Analysis

#### 5.2.1 Likelihood Scale

| Level | Score | Description | Frequency |
|-------|-------|-------------|-----------|
| Rare | 1 | Unlikely to occur | <1% annually |
| Unlikely | 2 | May occur occasionally | 1-10% annually |
| Possible | 3 | Might occur | 10-50% annually |
| Likely | 4 | Will probably occur | 50-90% annually |
| Almost Certain | 5 | Expected to occur | >90% annually |

#### 5.2.2 Impact Scale

| Level | Score | Description | Impact |
|-------|-------|-------------|--------|
| Negligible | 1 | Minor inconvenience | <$1K, no reputation impact |
| Minor | 2 | Limited impact | $1K-$10K, minor reputation |
| Moderate | 3 | Significant impact | $10K-$100K, moderate reputation |
| Major | 4 | Serious impact | $100K-$1M, major reputation |
| Critical | 5 | Catastrophic impact | >$1M, severe reputation |

#### 5.2.3 AI-Specific Impact Dimensions

| Dimension | Description | Considerations |
|-----------|-------------|----------------|
| Safety | Physical or psychological harm | User safety, downstream effects |
| Rights | Violation of rights | Privacy, autonomy, dignity |
| Economic | Financial impact | Direct costs, lost revenue |
| Operational | Business operations | Downtime, productivity |
| Reputational | Public perception | Media coverage, trust |
| Legal | Regulatory consequences | Fines, lawsuits |

### 5.3 Risk Evaluation

#### 5.3.1 Risk Matrix

```
                              IMPACT
              ┌────────┬────────┬────────┬────────┬────────┐
              │ Neg(1) │ Min(2) │ Mod(3) │ Maj(4) │ Cri(5) │
┌─────────────┼────────┼────────┼────────┼────────┼────────┤
│ Almost      │   5    │   10   │   15   │   20   │   25   │
│ Certain (5) │  LOW   │  MED   │  HIGH  │ V.HIGH │CRITICAL│
├─────────────┼────────┼────────┼────────┼────────┼────────┤
│ Likely (4)  │   4    │   8    │   12   │   16   │   20   │
│             │  LOW   │  MED   │  HIGH  │ V.HIGH │ V.HIGH │
├─────────────┼────────┼────────┼────────┼────────┼────────┤
L│ Possible(3)│   3    │   6    │   9    │   12   │   15   │
I│            │  LOW   │  LOW   │  MED   │  HIGH  │  HIGH  │
K├─────────────┼────────┼────────┼────────┼────────┼────────┤
E│ Unlikely(2)│   2    │   4    │   6    │   8    │   10   │
L│            │  LOW   │  LOW   │  LOW   │  MED   │  MED   │
I├─────────────┼────────┼────────┼────────┼────────┼────────┤
H│ Rare (1)   │   1    │   2    │   3    │   4    │   5    │
O│            │  LOW   │  LOW   │  LOW   │  LOW   │  LOW   │
O└─────────────┴────────┴────────┴────────┴────────┴────────┘
D

Risk Score Legend:
CRITICAL (21-25): Immediate action required, executive escalation
VERY HIGH (16-20): Urgent action required, management escalation
HIGH (11-15): Action required within 30 days
MEDIUM (6-10): Action required within 90 days
LOW (1-5): Monitor and review
```

#### 5.3.2 Risk Appetite Thresholds

| Risk Level | Appetite | Required Actions |
|------------|----------|------------------|
| CRITICAL | Not acceptable | Stop, escalate, immediate treatment |
| VERY HIGH | Not acceptable | Escalate, urgent treatment required |
| HIGH | Limited tolerance | Treatment plan required |
| MEDIUM | Acceptable with controls | Monitor, implement controls |
| LOW | Acceptable | Monitor, review periodically |

### 5.4 Risk Treatment

#### 5.4.1 Treatment Options

| Option | Description | When to Use |
|--------|-------------|-------------|
| **Avoid** | Eliminate the activity causing risk | Risk exceeds appetite, no viable treatment |
| **Mitigate** | Implement controls to reduce likelihood/impact | Most common for manageable risks |
| **Transfer** | Share risk with third party | Insurance, contracts, outsourcing |
| **Accept** | Acknowledge and monitor | Risk within appetite, cost of treatment exceeds benefit |

#### 5.4.2 AI-Specific Mitigations

| Risk Category | Mitigation Strategies |
|---------------|----------------------|
| **Hallucination** | • RAG with verified sources<br>• Confidence thresholds<br>• Human review for critical outputs<br>• Fact-checking layer |
| **Bias** | • Diverse training data<br>• Bias testing and monitoring<br>• Fairness metrics<br>• Regular audits |
| **Privacy** | • PII detection and filtering<br>• Differential privacy<br>• Data minimization<br>• Encryption |
| **Adversarial** | • Input validation<br>• Prompt injection detection<br>• Rate limiting<br>• Output filtering |
| **Model Drift** | • Continuous monitoring<br>• A/B testing<br>• Retraining pipelines<br>• Performance alerts |
| **Availability** | • Redundancy<br>• Failover<br>• Load balancing<br>• Graceful degradation |

#### 5.4.3 Control Implementation

| Control Type | Description | Examples |
|--------------|-------------|----------|
| **Preventive** | Stop risk from occurring | Input validation, access control |
| **Detective** | Identify when risk occurs | Monitoring, anomaly detection |
| **Corrective** | Fix issues after occurrence | Incident response, rollback |
| **Compensating** | Alternative control | Manual review when automation fails |

### 5.5 Risk Monitoring

#### 5.5.1 Monitoring Activities

| Activity | Frequency | Responsible | Output |
|----------|-----------|-------------|--------|
| Risk register review | Weekly | Risk owners | Updated register |
| KRI monitoring | Continuous | Operations | Dashboards |
| Risk assessment refresh | Quarterly | Risk manager | Updated assessments |
| Emerging risk scan | Monthly | All teams | New risks identified |
| Control effectiveness | Quarterly | Control owners | Effectiveness report |

#### 5.5.2 Key Risk Indicators (KRIs)

| KRI | Description | Threshold | Response |
|-----|-------------|-----------|----------|
| Hallucination rate | % of factually incorrect outputs | >5% | Investigation |
| Bias score | Demographic parity difference | >0.1 | Review |
| PII detection rate | PII found in outputs | >0 | Alert |
| Model latency P95 | 95th percentile response time | >2000ms | Scale |
| Error rate | % of failed requests | >1% | Investigate |
| Adversarial attempts | Detected prompt injections | >10/hour | Block |

### 5.6 Risk Reporting

#### 5.6.1 Report Types

| Report | Audience | Frequency | Content |
|--------|----------|-----------|---------|
| Risk Dashboard | Operations | Real-time | KRIs, alerts |
| Risk Summary | Management | Weekly | Top risks, changes |
| Risk Report | Executives | Monthly | Trends, actions |
| Risk Assessment | Governance | Quarterly | Full assessment |
| Incident Report | Stakeholders | Per incident | Details, actions |

#### 5.6.2 Escalation Matrix

| Risk Level | Escalation To | Timeline |
|------------|---------------|----------|
| CRITICAL | Executive Sponsor, CISO | Immediate |
| VERY HIGH | Chief AI Officer | Within 4 hours |
| HIGH | Program Manager | Within 24 hours |
| MEDIUM | Risk Owner | Within 1 week |
| LOW | Documented only | Next review |

## 6. Roles and Responsibilities

| Role | Responsibilities |
|------|------------------|
| Executive Sponsor | Risk appetite definition, escalation decisions |
| Risk Manager | Process ownership, reporting, facilitation |
| Risk Owners | Individual risk management, treatment implementation |
| AI Ethics Board | Ethical risk review and approval |
| Security Team | Security risk assessment and treatment |
| Operations | Risk monitoring, incident response |
| All Staff | Risk identification and reporting |

## 7. Records

| Record | Retention | Location |
|--------|-----------|----------|
| Risk Register | Active + 7 years | SharePoint |
| Risk Assessments | 7 years | SharePoint |
| Treatment Plans | Plan lifecycle + 3 years | SharePoint |
| Monitoring Reports | 3 years | Dashboard archives |
| Incident Reports | 7 years | ServiceNow |

## 8. Process Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Risk identification coverage | 100% of AI systems | Audit |
| Risk assessment timeliness | Within 30 days of change | Tracking |
| Treatment plan completion | 90% on time | Tracking |
| Control effectiveness | >80% effective | Testing |
| Residual risk within appetite | 100% | Review |

---

## Appendix A: Risk Register Template

| Field | Description |
|-------|-------------|
| Risk ID | Unique identifier (AI-Rxxx) |
| Category | Risk category |
| Description | Clear description of the risk |
| Cause | Root cause or source |
| Consequence | Potential impact |
| Likelihood | 1-5 score |
| Impact | 1-5 score |
| Risk Score | Likelihood x Impact |
| Risk Level | CRITICAL/V.HIGH/HIGH/MEDIUM/LOW |
| Owner | Accountable person |
| Treatment | Avoid/Mitigate/Transfer/Accept |
| Controls | Existing controls |
| Planned Actions | Additional treatments |
| Due Date | Treatment deadline |
| Status | Open/In Progress/Closed |
| Residual Risk | Risk after treatment |
| Last Review | Date of last review |
| Notes | Additional information |

---

**Document Approval:**

| Role | Name | Date |
|------|------|------|
| Owner | Program Manager | 2026-01-21 |
| Reviewer | CISO | 2026-01-21 |
| Approver | Chief AI Officer | 2026-01-21 |
