# Vendor & Azure Support Management — Azure OpenAI Enterprise RAG Platform

> Vendor engagement, Azure support plans, escalation workflows, quota management, service health monitoring, contract governance, and third-party risk assessment aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF**.

---

## Table of Contents

1. [Azure Support Plan Comparison](#1-azure-support-plan-comparison)
2. [Escalation Matrix for Azure Service Issues](#2-escalation-matrix-for-azure-service-issues)
3. [Requesting OpenAI TPM Quota Increases](#3-requesting-openai-tpm-quota-increases)
4. [Filing Azure AI Search Support Tickets](#4-filing-azure-ai-search-support-tickets)
5. [Microsoft TAM Engagement](#5-microsoft-tam-engagement)
6. [Azure Service Health Monitoring](#6-azure-service-health-monitoring)
7. [Planned Maintenance Notification Handling](#7-planned-maintenance-notification-handling)
8. [Service Deprecation Monitoring](#8-service-deprecation-monitoring)
9. [Feature Request Process](#9-feature-request-process)
10. [Azure Advisory Services](#10-azure-advisory-services)
11. [Contract & Licensing Management](#11-contract--licensing-management)
12. [Azure Cost Anomaly Escalation](#12-azure-cost-anomaly-escalation)
13. [Third-Party Vendor Management](#13-third-party-vendor-management)
14. [Vendor Risk Assessment Template](#14-vendor-risk-assessment-template)
15. [Support Ticket Tracking](#15-support-ticket-tracking)
16. [Azure Support CLI Commands](#16-azure-support-cli-commands)

---

## 1. Azure Support Plan Comparison

### 1.1 Plan Tier Overview

| Feature | **Developer** | **Standard** | **Professional Direct** | **Unified** |
|---------|--------------|-------------|------------------------|-------------|
| **Monthly Cost** | $29/mo | $100/mo | $1,000/mo | Custom ($50K+/yr) |
| **Scope** | Trial / non-prod | Production | Business-critical | Enterprise-wide |
| **Sev A Response** | N/A | < 1 hour | < 1 hour (24/7) | < 15 min (24/7) |
| **Sev B Response** | < 8 biz hrs | < 4 hours | < 2 hours | < 1 hour |
| **Sev C Response** | < 8 biz hrs | < 8 biz hrs | < 4 biz hrs | < 4 biz hrs |
| **TAM** | No | No | ProDirect delivery pool | Designated TAM |
| **Escalation Mgmt** | Self-service | Support engineer | Escalation manager | Designated manager |
| **Advisory Services** | No | No | Limited | Full WAF Reviews |
| **API Access** | No | No | No | Yes |

### 1.2 Recommended Plan for This Platform

| Environment | Recommended Plan | Justification |
|------------|-----------------|---------------|
| **Dev / Sandbox** | Developer ($29) | Non-production workloads |
| **Staging** | Standard ($100) | Pre-prod validation |
| **Production** | Unified (Custom) | Business-critical AI/RAG |

**Why Unified for Production**: GPT-4o downtime = revenue loss; AI Search degradation = stale RAG results; 15-min Sev A response critical for AI workloads; designated TAM provides proactive prevention; API access enables automated ticket creation in CI/CD.

---

## 2. Escalation Matrix for Azure Service Issues

### 2.1 Severity Classification

| Severity | Definition | Example (RAG Platform) | Response Target | Escalation Path |
|----------|-----------|----------------------|-----------------|-----------------|
| **Sev A — Critical** | Business-critical; service completely down | Azure OpenAI endpoint returning 503 for all requests; AI Search index unavailable | < 15 min (Unified) | L1 On-Call -> Platform Lead -> TAM -> Azure Escalation Manager |
| **Sev B — High** | Significant impact; service degraded | GPT-4o latency > 10s; AI Search returning partial results; Cosmos DB throttling | < 1 hr (Unified) | L1 On-Call -> Platform Lead -> TAM |
| **Sev C — Moderate** | Moderate impact; workaround available | Document Intelligence processing failures on specific file types; Redis cache misses elevated | < 4 hrs | L1 On-Call -> Platform Engineer -> Azure Support |
| **Sev D — Low** | Minimal impact; informational | Portal UI rendering issue; minor billing discrepancy; documentation error | < 8 business hrs | Platform Engineer -> Azure Support (self-service) |

### 2.2 Escalation Flow Diagram

```
Alert ──> L1 On-Call (< 5 min) ──> Platform Lead (< 15 min) ──> TAM (< 30 min)
               │                          │                          │
          Sev C/D:                   Sev B:                     Sev A:
          Self-service               Azure Support              Azure Rapid Response
          ticket                     Ticket                     ──> Escalation Manager

ALL SEVERITIES: Log in ServiceNow | Update Slack #azure-support
```

### 2.3 Escalation Contact Matrix

| Role | Name / Alias | Contact Method | Availability |
|------|-------------|---------------|--------------|
| **L1 On-Call Engineer** | Rotating (PagerDuty) | PagerDuty + Slack #oncall | 24/7 |
| **Platform Lead** | platform-lead@company.com | Teams / Phone | Business hours + on-call |
| **Microsoft TAM** | Assigned TAM name | Teams / Email / Phone | Business hours (SLA-backed) |
| **Azure Escalation Manager** | Via TAM or Sev A ticket | Azure Support Portal | 24/7 for Sev A |
| **VP Engineering** | vp-eng@company.com | Phone (Sev A only) | 24/7 for Sev A |

---

## 3. Requesting OpenAI TPM Quota Increases

### 3.1 Current Quota Defaults

| Model | Default TPM (Tokens Per Minute) | Default RPM (Requests Per Minute) | Platform Target TPM |
|-------|---------------------------------|-----------------------------------|---------------------|
| **GPT-4o** | 30,000 | 30 | 150,000 |
| **GPT-4o-mini** | 60,000 | 60 | 300,000 |
| **text-embedding-3-large** | 120,000 | 120 | 500,000 |

### 3.2 Step-by-Step: Azure Portal Method

**Step 1 — Check current usage and quota**

Navigate to: **Azure Portal > Azure OpenAI > your-resource > Management > Quotas**

The Quotas blade displays current allocation, usage percentage, and region-level capacity for each model deployment.

**Step 2 — Submit quota increase request**

From the Quotas blade, select the model deployment, click **Request Quota Increase**, and fill in:

| Field | Value | Notes |
|-------|-------|-------|
| **Subscription** | Your production subscription ID | Must match the resource |
| **Region** | e.g., East US 2 | Quota is region-specific |
| **Model** | e.g., gpt-4o | Select from dropdown |
| **Current Quota** | Auto-populated | Shows current TPM |
| **Requested Quota** | e.g., 150000 | Must justify business need |
| **Business Justification** | "Enterprise RAG platform serving 2,000+ users; current 30K TPM causes throttling during peak hours (9-11 AM EST). P95 latency exceeds 8s." | Detailed justification improves approval speed |

**Step 3** — Monitor approval via **Support + Troubleshooting > Support requests** (typical turnaround: 1-3 business days).

### 3.3 Step-by-Step: Azure CLI Method

```bash
# Check current deployments and TPM limits
az cognitiveservices account deployment list \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name oai-genai-copilot-prod --output table

# Check current quota usage
az cognitiveservices usage list --location eastus2 --output table

# Update deployment with new TPM capacity (if region has capacity)
az cognitiveservices account deployment create \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name oai-genai-copilot-prod \
  --deployment-name gpt-4o-prod \
  --model-name gpt-4o --model-version "2024-08-06" \
  --model-format OpenAI --sku-name Standard --sku-capacity 150

# If region capacity insufficient, file a support ticket
az support tickets create \
  --ticket-name "quota-increase-gpt4o-$(date +%Y%m%d)" \
  --title "GPT-4o TPM Quota Increase - Enterprise RAG Platform" \
  --description "Requesting TPM increase from 30K to 150K in East US 2. \
Enterprise RAG platform, 2000+ users, 85% peak utilization, throttling observed." \
  --problem-classification "/providers/Microsoft.Support/services/AZURE_OPENAI/problemClassifications/QUOTA" \
  --severity moderate \
  --contact-first-name "Platform" --contact-last-name "Team" \
  --contact-method email --contact-email platform-team@company.com \
  --contact-timezone "Eastern Standard Time" \
  --contact-language "en-us" --contact-country "US"
```

### 3.4 Quota Increase Approval Timeline

| Request Type | Typical Turnaround |
|-------------|-------------------|
| **Within existing regional capacity** | Instant (self-service via deployment update) |
| **Small increase (< 2x current)** | 1-2 business days |
| **Large increase (> 2x current)** | 3-5 business days (capacity planning) |
| **New region enablement** | 5-10 business days |
| **PTU (Provisioned Throughput)** | 5-15 business days (reservation required) |

---

## 4. Filing Azure AI Search Support Tickets

### 4.1 Required Diagnostic Information

| Diagnostic | How to Collect |
|-----------|---------------|
| **Search Service Name** | Azure Portal > AI Search > Overview |
| **Index Name(s)** | Portal or `az search index list` |
| **Correlation ID** | HTTP response header `request-id` |
| **Time Range (UTC)** | Timestamps of issue window |
| **Query Latency Logs** | App Insights: `requests \| where name contains "search"` |
| **Indexer Status** | Portal > Indexers > Run History |
| **Service Metrics** | Portal > Monitoring > Metrics (QPS, Latency, Throttled %) |
| **Resource Health** | Portal > Resource Health |

### 4.2 Filing the Ticket

```bash
# Collect diagnostics
az search service show \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name srch-genai-copilot-prod --output json > /tmp/search-diag.json

# File the support ticket
az support tickets create \
  --ticket-name "ai-search-degradation-$(date +%Y%m%d)" \
  --title "AI Search - Elevated Query Latency in Production" \
  --description "P95 latency >2s (baseline 200ms) since 2024-01-15T14:00Z. \
S2 tier, 3 replicas. No config changes in 7 days. QPS normal (50-80)." \
  --problem-classification "/providers/Microsoft.Support/services/AZURE_AI_SEARCH/problemClassifications/PERFORMANCE" \
  --severity moderate \
  --contact-first-name "Platform" --contact-last-name "Team" \
  --contact-method email --contact-email platform-team@company.com \
  --contact-timezone "Eastern Standard Time" \
  --contact-language "en-us" --contact-country "US"
```

### 4.3 Expected Response Times

| Issue Type | Severity | First Response | Resolution |
|-----------|----------|---------------|-----------|
| **Index corruption** | Sev A | < 1 hour | 4-12 hours |
| **Query latency degradation** | Sev B | < 2 hours | 1-3 days |
| **Indexer failures** | Sev B/C | < 4 hours | 1-5 days |
| **Semantic ranker issues** | Sev C | < 8 hours | 3-7 days |

---

## 5. Microsoft TAM Engagement

### 5.1 TAM Services Overview

| Service | Description | Frequency |
|---------|------------|-----------|
| **Service Delivery Management** | Proactive oversight of Azure health and support tickets | Ongoing |
| **Incident Management** | Coordinates across Azure engineering teams during Sev A/B | As needed |
| **Service Reviews** | Quarterly business and technical health reviews | Quarterly |
| **Risk Assessment** | Identifies platform risks and recommends mitigations | Bi-annual |
| **Escalation Management** | Single point of contact for stalled support tickets | As needed |
| **Workshop Facilitation** | Azure Well-Architected, security, AI/ML workshops | Quarterly |
| **Roadmap Briefings** | Private previews and upcoming feature briefings | Quarterly (NDA) |

### 5.2 When to Engage the TAM

| Trigger Condition | Action |
|------------------|--------|
| **Sev A production outage** | Engage TAM IMMEDIATELY + file Sev A ticket |
| **Support ticket stalled > 48 hrs** | Engage TAM for escalation |
| **Major architecture change planned** | Schedule TAM workshop / review |
| **Quarterly review approaching** | Prepare service review deck |
| **None of the above** | Handle via standard Azure Support portal |

### 5.3 TAM Quarterly Review Agenda

| Agenda Item | Duration | Owner |
|------------|----------|-------|
| Service Health Summary | 15 min | TAM |
| Open Ticket Review + Incident Post-Mortems | 20 min | TAM + Platform Lead |
| Architecture / Roadmap Updates | 15 min | TAM |
| Upcoming Maintenance / Deprecations | 10 min | TAM |
| Quota & Capacity Planning + Action Items | 15 min | Both |

---

## 6. Azure Service Health Monitoring

### 6.1 Service Health Components

```
┌─────────────────────────────────────────────────────────────┐
│                   AZURE SERVICE HEALTH                        │
├─────────────────┬──────────────────┬────────────────────────┤
│  Service Issues │ Planned          │ Health Advisories      │
│  • Active       │ Maintenance      │ • Service retirements  │
│    incidents    │ • Scheduled      │ • Feature deprecations │
│  • RCA reports  │   updates        │ • Action required      │
├─────────────────┴──────────────────┴────────────────────────┤
│  ACTION GROUPS: Email | SMS | Webhook (PagerDuty) |         │
│                 Azure Function | Logic App (Slack)           │
├─────────────────────────────────────────────────────────────┤
│  RESOURCE HEALTH: Per-resource availability status           │
│  Available / Degraded / Unavailable / Unknown                │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Setting Up Service Health Alerts

```bash
# Create Action Group for Service Health notifications
az monitor action-group create \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name ag-service-health-prod \
  --short-name SvcHealth \
  --action email platform-alerts platform-team@company.com \
  --action webhook pagerduty-webhook "https://events.pagerduty.com/integration/YOUR_KEY/enqueue"

# Create Service Health Alert for Azure OpenAI
az monitor activity-log alert create \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name "alert-service-health-openai" \
  --description "Azure OpenAI service health events" \
  --condition category=ServiceHealth \
  --action-group ag-service-health-prod \
  --scope "/subscriptions/YOUR_SUBSCRIPTION_ID"

# Create Resource Health Alert for all critical resources
az monitor activity-log alert create \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name "alert-resource-health-prod" \
  --description "Resource health changes for production resources" \
  --condition category=ResourceHealth \
  --action-group ag-service-health-prod \
  --scope "/subscriptions/YOUR_SUBSCRIPTION_ID"
```

### 6.3 Critical Services to Monitor

| Azure Service | Impact if Down |
|--------------|---------------|
| **Azure OpenAI** | RAG queries fail completely |
| **Azure AI Search** | Document retrieval fails |
| **Azure Cosmos DB** | Conversation history / audit lost |
| **Azure Key Vault** | All services lose secret access |
| **Azure Entra ID** | Authentication fails platform-wide |
| **Azure Cache for Redis** | Latency spike; cache misses |
| **Azure Kubernetes Service** | API layer unavailable |
| **Application Gateway** | All traffic blocked |

All services above require both **Service Health** and **Resource Health** alerts enabled.

---

## 7. Planned Maintenance Notification Handling

### 7.1 Notification Subscription

| Channel | Lead Time |
|---------|----------|
| **Azure Portal Alerts** (Service Health > Planned Maintenance) | 2-4 weeks |
| **Email Notifications** (via Action Group) | Same as alert |
| **Azure Mobile App** (push notifications) | Real-time |
| **RSS Feed** (azurestatuscdn.azureedge.net/en-us/status/feed/) | Varies |
| **TAM Notification** (proactive for Unified plan) | 2-6 weeks |

### 7.2 Maintenance Response Procedures

| Phase | Action | Timeline |
|-------|--------|----------|
| **Notification Received** | Log in tracking sheet; assess impact to RAG platform | Within 4 hours |
| **Impact Assessment** | Map affected service to platform component; determine user impact | Within 1 business day |
| **Stakeholder Communication** | Notify affected teams via email + Slack #platform-updates | Within 1 business day |
| **Pre-Maintenance Prep** | Verify failover readiness; test health probes; snapshot configs | 3 days before |
| **Maintenance Window** | Monitor dashboards; validate recovery; test critical paths | During window |
| **Post-Maintenance Validation** | Run smoke tests; verify GPT-4o, AI Search, Cosmos DB | Within 2 hours after |

### 7.3 Maintenance Impact Classification

| Impact Level | User Impact | Action Required | Example |
|-------------|------------|-----------------|---------|
| **None** | Transparent | Monitor only | Backend infra patch |
| **Low** | Brief blip | Notify team | Redis failover |
| **Medium** | Degraded | Notify users | AKS node upgrade |
| **High** | Partial down | Prep failover | AI Search reindex |
| **Critical** | Full outage | Schedule downtime | Region migration |

---

## 8. Service Deprecation Monitoring

### 8.1 Monitoring Channels

| Source | Check Frequency | Owner |
|--------|----------------|-------|
| **Azure Updates** (azure.microsoft.com/updates) | Weekly | Platform Engineer |
| **Azure Updates RSS** (azurecomcdn.azureedge.net/en-us/updates/feed/) | Automated | RSS reader + Platform Engineer |
| **Azure Advisor** (Portal > Advisor > Operational Excellence) | Weekly | Platform Engineer |
| **Service Health Advisories** (Portal > Service Health) | Alert-driven | Automated |
| **TAM Briefings** | Quarterly | TAM |

### 8.2 Deprecation Timeline Handling

| Phase | Timeline | Action |
|-------|----------|--------|
| **Announcement** | Day 0 | Log in tracker; assess impact (Platform Engineer) |
| **Impact Analysis** | Day 0 - 14 | Map to platform usage; identify migration path (Platform Lead) |
| **Migration Planning** | Day 14 - 60 | Create backlog items; estimate effort (Platform Lead) |
| **Migration Execution** | Day 60 - Retirement -30d | Implement in Dev > Staging > Prod (Platform Team) |
| **Retirement Date** | End of support | Verify clean cutover; close tracking item |

### 8.3 Current Deprecation Watch List

| Service / Feature | Status | Migration Target | Platform Impact |
|------------------|--------|-----------------|-----------------|
| **Cognitive Search (name)** | Renamed (completed) | Azure AI Search | Branding only |
| **GPT-4 (0314)** | Deprecated (2024-06-13) | GPT-4o | Model swap required |
| **text-embedding-ada-002** | Monitoring (TBD) | text-embedding-3-large | Reindex required |
| **Azure AD** | Renamed (completed) | Microsoft Entra ID | Config/docs update |
| **Form Recognizer** | Renamed (completed) | Document Intelligence | SDK update |

---

## 9. Feature Request Process

### 9.1 Channels for Feature Requests

| Channel | Best For | Response |
|---------|----------|---------|
| **Azure Feedback Portal** (feedback.azure.com) | Public feature requests; vote on existing | Community-driven; no SLA |
| **Azure OpenAI Feedback** (aka.ms/oai/feedback) | OpenAI-specific model and feature requests | Product team reviewed |
| **TAM Direct Channel** | High-priority enterprise requests | TAM escalates to product group |
| **GitHub Issues** (Azure SDK repos) | SDK bugs and improvements | Community + MSFT engineers |

### 9.2 Internal Feature Request Tracking

| Field | Description | Example |
|-------|------------|---------|
| **Tracking ID** | Internal ID (FR-YYYY-NNNN) | FR-2024-0042 |
| **Azure Service** | Which Azure service | Azure OpenAI |
| **Request Title** | Brief description | JSON mode in Batch API |
| **Business Justification** | Why this matters | 50% cost reduction for document processing |
| **Channel Submitted** | Feedback Portal / TAM / GitHub | TAM + Feedback Portal |
| **External ID** | Azure Feedback ID or GitHub issue | feedback-12345 |
| **Priority** | Critical / High / Medium / Low | High |
| **Status** | Submitted / Under Review / Planned / Shipped / Declined | Under Review |

---

## 10. Azure Advisory Services

### 10.1 Available Advisory Engagements

| Service | Description | Eligibility |
|---------|------------|-------------|
| **Azure Well-Architected Review** | Assessment against WAF pillars (Reliability, Security, Cost, Ops, Performance) | Unified / ProDirect |
| **Well-Architected for AI** | AI-specific: responsible AI, model ops, data pipeline | Unified |
| **Azure Migrate Assessment** | Migration planning and cost estimation | All plans |
| **Security Best Practices Review** | Posture assessment with Defender for Cloud | Unified |
| **Cost Optimization Review** | Azure Advisor + manual spending review | Unified / ProDirect |
| **Architectural Design Session** | Deep-dive design for specific workloads | Unified |

### 10.2 Well-Architected Review: RAG Platform Focus Areas

| WAF Pillar | Key Assessment Areas |
|-----------|---------------------|
| **Reliability** | Multi-region failover for Azure OpenAI; AI Search replica config; Cosmos DB multi-region write; circuit breaker patterns |
| **Security** | Private endpoints for all PaaS; managed identity (no stored credentials); Content Safety; CMK encryption + TLS 1.2 |
| **Cost Optimization** | PTU vs. pay-as-you-go for OpenAI; AI Search tier right-sizing; Cosmos DB autoscale vs provisioned RU; AKS reserved instances |
| **Operational Excellence** | Terraform IaC (100% target); CI/CD staged rollout; automated testing (unit, integration, E2E); runbook coverage |
| **Performance Efficiency** | Semantic caching with Redis; embedding batch optimization; AI Search index tuning; token budget management |

---

## 11. Contract & Licensing Management

### 11.1 Licensing Model Comparison

| Aspect | **EA (Enterprise Agreement)** | **PAYG (Pay-As-You-Go)** | **CSP** |
|--------|------------------------------|--------------------------|---------|
| **Commitment** | 3-year term, annual true-up | None | Via CSP partner |
| **Discount** | 5-15% off list pricing | None | Partner-negotiated |
| **Billing** | Monthly against commitment | Monthly usage-based | Partner invoice |
| **Azure OpenAI Access** | Direct | Direct | Via partner |
| **PTU Commitment** | Required for PTU | Not available | Via partner |
| **Best For** | Enterprise (>$100K/yr) | Startups, dev/test | SMB, managed |

### 11.2 EA Renewal Timeline

| Milestone | Timeline | Action |
|-----------|----------|--------|
| **T-12 months** | EA Anniversary -12 | Consumption forecasting (Finance + Platform Lead) |
| **T-9 months** | EA Anniversary -9 | Engage Microsoft AE; request proposal (Procurement) |
| **T-6 months** | EA Anniversary -6 | Negotiate pricing; evaluate PTU needs (Procurement + Platform) |
| **T-3 months** | EA Anniversary -3 | Finalize terms; legal review; sign (Procurement + Legal) |
| **T-0** | EA Anniversary | New term begins; validate pricing (Finance) |

### 11.3 OpenAI-Specific Licensing Notes

| Item | Detail |
|------|--------|
| **Azure OpenAI Access** | Requires application approval (one-time); EA or PAYG eligible |
| **PTU** | Minimum 1-month commitment; billed hourly; requires EA or direct billing |
| **Data Processing Agreement** | Microsoft DPA covers Azure OpenAI; no training on customer data |
| **SLA** | 99.9% availability (GA models) |
| **Content Filtering** | Included; cannot be fully disabled |

---

## 12. Azure Cost Anomaly Escalation

### 12.1 When to Contact Azure Billing Support

| Scenario | Action |
|----------|--------|
| **Unexpected cost spike (> 20% above daily avg)** | Investigate via Cost Analysis; if unexplained, file billing ticket |
| **Metering discrepancy** | File billing support ticket with App Insights evidence |
| **RI misapplication** | Check RI scope; file ticket if config is correct |
| **PTU billing after deletion** | File Sev B billing ticket immediately |
| **Budget alert triggered (80%/100%)** | Review Cost Analysis; escalate if not organic growth |

### 12.2 Cost Anomaly Detection Setup

```bash
# Create budget with alerts for the production resource group
az consumption budget create \
  --budget-name "budget-genai-prod-monthly" \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --amount 15000 \
  --time-grain Monthly \
  --start-date "2024-01-01" \
  --end-date "2025-12-31" \
  --category Cost

# Configure alert thresholds in Azure Portal:
# Cost Management > Budgets > Alert conditions
# Thresholds: 50% (Forecasted), 80% (Actual), 100% (Actual), 120% (Actual)
```

---

## 13. Third-Party Vendor Management

### 13.1 Vendor Inventory

| Vendor | Service | Criticality | Contract |
|--------|---------|-------------|----------|
| **Microsoft (Azure OpenAI)** | GPT-4o, GPT-4o-mini, Embeddings | **Critical** | EA / Consumption |
| **Microsoft (Azure Platform)** | AI Search, Cosmos DB, AKS, KV, etc. | **Critical** | EA / Consumption |
| **Datadog / Azure Monitor** | Monitoring, alerting, dashboards | **High** | SaaS |
| **PagerDuty** | Incident management, on-call routing | **High** | SaaS |
| **Snyk / Trivy** | Container and dependency scanning | **Medium** | SaaS / OSS |
| **HashiCorp (Terraform)** | Infrastructure as Code | **High** | OSS + Cloud |
| **GitHub / Azure DevOps** | Source control, CI/CD | **Critical** | SaaS |

### 13.2 Vendor Review Cadence

| Review Type | Frequency | Deliverable |
|------------|-----------|-------------|
| **Security Assessment** | Annual | SOC 2 / ISO 27001 report review |
| **Performance Review** | Quarterly | SLA compliance report |
| **Contract Review** | Annual (at renewal) | Renewal / renegotiation terms |
| **Business Continuity** | Annual | DR test results; RTO/RPO validation |

---

## 14. Vendor Risk Assessment Template

### 14.1 Risk Assessment Matrix

| Risk Category | Assessment Criteria | Weight | Score (1-5) | Weighted Score |
|--------------|-------------------|--------|-------------|---------------|
| **Data Security** | Encryption, access controls, incident response | 25% | ___ | ___ |
| **Compliance** | SOC 2, ISO 27001, GDPR, industry certifications | 20% | ___ | ___ |
| **Availability** | SLA, uptime history, redundancy, DR capability | 20% | ___ | ___ |
| **Financial Stability** | Revenue, market position, funding | 10% | ___ | ___ |
| **Vendor Lock-in** | Data portability, API standards, exit strategy | 10% | ___ | ___ |
| **Support Quality** | Response times, escalation, documentation | 10% | ___ | ___ |
| **Strategic Alignment** | Roadmap alignment, innovation, partnership level | 5% | ___ | ___ |
| **Total** | | **100%** | | **___/5.0** |

**Risk Scoring**: 5 = Excellent (exceeds requirements) | 4 = Good | 3 = Acceptable | 2 = Concerning (mitigation needed) | 1 = Unacceptable (remediation required)

### 14.2 Azure OpenAI Vendor Risk Summary (Example)

| Risk Category | Score | Rationale |
|--------------|-------|-----------|
| **Data Security** | 5 | Microsoft DPA; no training on customer data; CMK; private endpoints |
| **Compliance** | 5 | SOC 1/2/3, ISO 27001/27017/27018, FedRAMP High, HIPAA BAA |
| **Availability** | 4 | 99.9% SLA; regional capacity constraints; no auto multi-region failover |
| **Vendor Lock-in** | 3 | OpenAI API compat eases migration; Azure-specific features create dependency |
| **Support Quality** | 4 | Unified support excellent; quota process can be slow |
| **Total** | **4.3/5.0** | **Low Risk** |

---

## 15. Support Ticket Tracking

### 15.1 Recommended Ticket Fields

| Field | Type | Example |
|-------|------|---------|
| **Ticket ID** | Auto-generated | SUP-2024-0123 |
| **Azure Ticket ID** | String | 2401150010000123 |
| **Title** | String | "GPT-4o 503 errors in East US 2" |
| **Severity** | Enum (A/B/C/D) | Sev B |
| **Azure Service** | Enum | Azure OpenAI |
| **Status** | Enum | Open / In Progress / Waiting on Microsoft / Resolved / Closed |
| **Created Date** | DateTime | 2024-01-15T14:30Z |
| **SLA Target** | DateTime | 2024-01-15T15:30Z |
| **First Response** | DateTime | 2024-01-15T15:15Z |
| **SLA Met** | Boolean | Yes |
| **Resolution Date** | DateTime | 2024-01-16T09:00Z |
| **Root Cause** | String | Regional capacity constraint |
| **Owner** | String | platform-engineer@company.com |
| **Escalated to TAM** | Boolean | No |

### 15.2 SLA Tracking Dashboard Metrics

| Metric | Calculation | Target | Alert Threshold |
|--------|------------|--------|----------------|
| **SLA Compliance Rate** | (Tickets meeting SLA / Total) x 100 | > 95% | < 90% |
| **Mean Time to First Response** | Avg(First Response - Created) | < Plan SLA | > 1.5x SLA |
| **Mean Time to Resolution** | Avg(Resolution - Created) | Sev A: < 4h; B: < 24h | 2x target |
| **Open Ticket Count** | Status != Closed | < 10 | > 20 |
| **TAM Escalation Rate** | Escalated / Total x 100 | < 10% | > 20% |
| **Recurring Issue Rate** | Same root cause in 90 days | < 5% | > 10% |

### 15.3 Monthly Support Report Fields

| Report Section | Key Data Points |
|---------------|----------------|
| **Ticket Summary** | Total filed, breakdown by severity, avg resolution per severity |
| **SLA Compliance** | % meeting SLA target, breaches with root cause |
| **TAM Escalations** | Count, reason, outcome |
| **Top Services** | Ticket count by Azure service (top 5) |
| **Recurring Issues** | Issues appearing >1 time in 90-day window |
| **Action Items** | Remediation tasks with owner and due date |

---

## 16. Azure Support CLI Commands

### 16.1 Support Ticket Management

```bash
# List all open support tickets
az support tickets list --output table

# Create a new support ticket
az support tickets create \
  --ticket-name "platform-issue-$(date +%Y%m%d%H%M)" \
  --title "Azure OpenAI - Intermittent 429 Throttling Despite Available Quota" \
  --description "429 responses (Retry-After: 10s) despite 60% TPM utilization. \
Region: East US 2. Model: gpt-4o. Started: 2024-01-15T10:00Z." \
  --problem-classification "/providers/Microsoft.Support/services/AZURE_OPENAI/problemClassifications/CONNECTIVITY_PERFORMANCE" \
  --severity moderate \
  --contact-first-name "Platform" --contact-last-name "Team" \
  --contact-method email --contact-email platform-team@company.com \
  --contact-timezone "Eastern Standard Time" \
  --contact-language "en-us" --contact-country "US"

# Show ticket details / Add communication / List communications
az support tickets show --ticket-name "platform-issue-20240115" --output json
az support tickets communications create \
  --ticket-name "platform-issue-20240115" \
  --communication-name "update-01" \
  --communication-subject "Additional diagnostics" \
  --communication-body "App Insights KQL results showing 429 pattern attached."
az support tickets communications list --ticket-name "platform-issue-20240115" --output table
```

### 16.2 Service Health Queries

```bash
# List current service health events (service issues)
az rest --method GET \
  --url "https://management.azure.com/subscriptions/YOUR_SUB_ID/providers/Microsoft.ResourceHealth/events?api-version=2022-10-01" \
  --query "value[?properties.eventType=='ServiceIssue'].[name,properties.title,properties.status]" \
  --output table

# Check resource health for Azure OpenAI
az rest --method GET \
  --url "https://management.azure.com/subscriptions/YOUR_SUB_ID/resourceGroups/rg-genai-copilot-prod-eastus2/providers/Microsoft.CognitiveServices/accounts/oai-genai-copilot-prod/providers/Microsoft.ResourceHealth/availabilityStatuses/current?api-version=2023-07-01-preview" \
  --output json

# List planned maintenance events
az rest --method GET \
  --url "https://management.azure.com/subscriptions/YOUR_SUB_ID/providers/Microsoft.ResourceHealth/events?api-version=2022-10-01&\$filter=eventType eq 'PlannedMaintenance'" \
  --output table
```

### 16.3 Diagnostic Commands for Support Tickets

```bash
# Collect Azure OpenAI diagnostics
az cognitiveservices account show \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name oai-genai-copilot-prod --output json

az cognitiveservices account deployment list \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name oai-genai-copilot-prod --output table

# Collect AI Search diagnostics
az search service show \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --name srch-genai-copilot-prod --output json

# Recent failures in Activity Log (last 24h)
az monitor activity-log list \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --start-time "$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --status Failed --output table
```

### 16.4 Quick Reference: Common Support Scenarios

| Scenario | CLI Command | Notes |
|----------|------------|-------|
| **List open tickets** | `az support tickets list --output table` | Shows all tickets for subscription |
| **Check ticket status** | `az support tickets show --ticket-name NAME` | Returns full ticket details |
| **Add update to ticket** | `az support tickets communications create ...` | Append diagnostics or updates |
| **List service health issues** | `az rest --method GET --url ".../events?..."` | Filter by eventType |
| **Check resource health** | `az rest --method GET --url ".../availabilityStatuses/current"` | Per-resource status |
| **Query cost anomalies** | `az rest --method GET --url ".../query?..."` | Cost Management API |
| **Create budget alert** | `az consumption budget create ...` | Monthly cost threshold |
| **List OpenAI deployments** | `az cognitiveservices account deployment list ...` | Shows model, version, TPM |
| **Check quota usage** | `az cognitiveservices usage list --location REGION` | Regional quota consumption |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | Vendor & Azure Support Management |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cadence** | Quarterly |
| **Approved By** | Platform Lead, VP Engineering |
| **Framework Alignment** | CMMI Level 3, ISO/IEC 42001, NIST AI RMF |
