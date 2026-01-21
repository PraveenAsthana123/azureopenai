# Operations Guide

> **Day-to-Day Operations for Azure OpenAI Enterprise Platform**

---

## Table of Contents

1. [Operational Overview](#operational-overview)
2. [Monitoring & Alerting](#monitoring--alerting)
3. [Common Operations](#common-operations)
4. [Incident Management](#incident-management)
5. [Change Management](#change-management)
6. [Capacity Management](#capacity-management)
7. [Backup & Recovery](#backup--recovery)
8. [Maintenance Windows](#maintenance-windows)

---

## Operational Overview

### Service Level Objectives (SLOs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Availability** | 99.9% | Uptime monitoring |
| **Latency (P95)** | < 2s | Application Insights |
| **Error Rate** | < 1% | Error count / total |
| **AI Response Time** | < 10s | OpenAI latency |

### On-Call Rotation

| Shift | Coverage | Team |
|-------|----------|------|
| Primary | 24x7 | Platform Team |
| Secondary | Business hours | DevOps Team |
| Escalation | As needed | Architecture |

### Daily Operations Checklist

```markdown
Morning (Start of Day):
- [ ] Review overnight alerts
- [ ] Check dashboard for anomalies
- [ ] Verify all services healthy
- [ ] Review pending changes

End of Day:
- [ ] Handover notes for on-call
- [ ] Check scheduled maintenance
- [ ] Review open incidents
```

---

## Monitoring & Alerting

### Key Dashboards

| Dashboard | Purpose | URL |
|-----------|---------|-----|
| Platform Health | Overall status | Azure Portal |
| AI Services | OpenAI, Search metrics | Log Analytics |
| AKS Cluster | Kubernetes health | Container Insights |
| Cost | Resource consumption | Cost Management |

### Critical Alerts

| Alert | Condition | Response |
|-------|-----------|----------|
| Service Down | Health check fails | Page on-call |
| High Error Rate | > 5% errors | Page on-call |
| OpenAI Rate Limit | > 80% quota | Warning |
| Storage Full | > 90% capacity | Warning |
| Security Event | Anomaly detected | Page security |

### Alert Response Matrix

| Severity | Response Time | Notification | Escalation |
|----------|---------------|--------------|------------|
| Critical | Immediate | Page + call | 15 min |
| High | < 15 min | Page | 30 min |
| Medium | < 1 hour | Email | 4 hours |
| Low | < 4 hours | Email | Next day |

### Key Metrics to Monitor

```yaml
Infrastructure:
  - CPU utilization (< 80%)
  - Memory utilization (< 85%)
  - Disk utilization (< 90%)
  - Network throughput

Application:
  - Request rate
  - Error rate
  - Response time (P50, P95, P99)
  - Active connections

AI Services:
  - Token consumption
  - Request latency
  - Content filter triggers
  - Embedding throughput

Business:
  - Query success rate
  - User satisfaction
  - Cost per query
```

---

## Common Operations

### AKS Operations

```bash
# Get cluster credentials
az aks get-credentials --resource-group rg-aoai-prod --name aks-aoai-prod

# Check node status
kubectl get nodes

# Check pod status
kubectl get pods -A

# View logs
kubectl logs -f deployment/rag-api -n ai-services

# Scale deployment
kubectl scale deployment rag-api --replicas=5 -n ai-services

# Restart deployment
kubectl rollout restart deployment/rag-api -n ai-services
```

### Azure Functions Operations

```bash
# View function logs
az functionapp log tail --name func-aoai-prod --resource-group rg-aoai-prod

# Restart function app
az functionapp restart --name func-aoai-prod --resource-group rg-aoai-prod

# Check function status
az functionapp show --name func-aoai-prod --resource-group rg-aoai-prod --query state
```

### Storage Operations

```bash
# List containers
az storage container list --account-name staoaiprod --auth-mode login

# Check blob count
az storage blob list --account-name staoaiprod --container-name documents --auth-mode login --query "length(@)"

# Download blob
az storage blob download --account-name staoaiprod --container-name documents --name file.pdf --file local.pdf --auth-mode login
```

### OpenAI Operations

```bash
# Check deployment status
az cognitiveservices account deployment list --name oai-aoai-prod --resource-group rg-aoai-prod

# View usage metrics
az monitor metrics list --resource /subscriptions/{sub}/resourceGroups/rg-aoai-prod/providers/Microsoft.CognitiveServices/accounts/oai-aoai-prod --metric TokenTransaction
```

---

## Incident Management

### Incident Workflow

```
Detection → Triage → Declare → Contain → Resolve → Review
```

### Severity Classification

| Severity | Impact | Examples |
|----------|--------|----------|
| **P0** | Total outage / data breach | Platform down, security breach |
| **P1** | Major degradation | AI service unavailable |
| **P2** | Partial impact | Single function failing |
| **P3** | Minor issue | Performance degradation |

### Incident Commander Checklist

```markdown
Upon Declaration:
- [ ] Confirm severity
- [ ] Assign incident commander
- [ ] Open incident channel
- [ ] Notify stakeholders

During Incident:
- [ ] Regular status updates (every 15 min for P0/P1)
- [ ] Document timeline
- [ ] Coordinate response teams
- [ ] Approve changes

After Resolution:
- [ ] Confirm service restored
- [ ] Notify stakeholders
- [ ] Schedule PIR (within 48 hours for P0/P1)
- [ ] Create action items
```

### Communication Templates

**Internal Update:**
```
INCIDENT UPDATE - [ID]
Status: [Investigating/Identified/Monitoring/Resolved]
Severity: [P0-P3]
Impact: [Description]
Current Actions: [What's being done]
Next Update: [Time]
```

**Customer Communication:**
```
Service Status Update

We are currently experiencing [brief description].

Impact: [What customers may notice]
Status: Our team is actively working on resolution.
Next Update: [Time]

We apologize for any inconvenience.
```

---

## Change Management

### Change Types

| Type | CAB Required | Lead Time |
|------|--------------|-----------|
| Standard | No | Immediate |
| Normal | Yes | 3 days |
| Emergency | Post-approval | Immediate |

### Change Process

```
1. Submit CR → 2. Impact Analysis → 3. CAB Review →
4. Approval → 5. Implementation → 6. Validation → 7. Closure
```

### Pre-Change Checklist

```markdown
Before Implementation:
- [ ] Change approved
- [ ] Rollback plan documented
- [ ] Communication sent
- [ ] Monitoring in place
- [ ] Team available

During Implementation:
- [ ] Follow runbook steps
- [ ] Verify each step
- [ ] Monitor for issues
- [ ] Update status

After Implementation:
- [ ] Verify functionality
- [ ] Check monitoring
- [ ] Update documentation
- [ ] Close change request
```

### Rollback Triggers

| Condition | Action |
|-----------|--------|
| Error rate > 10% | Immediate rollback |
| Latency > 5x baseline | Immediate rollback |
| Security alert | Stop and assess |
| > 30 min troubleshooting | Consider rollback |

---

## Capacity Management

### Resource Limits

| Resource | Soft Limit | Hard Limit | Action at 80% |
|----------|------------|------------|---------------|
| AKS Nodes | 10 | 20 | Review scaling |
| OpenAI TPM | 100K | Per quota | Request increase |
| Storage | 5 TB | 50 TB | Archive old data |
| Log Analytics | 10 GB/day | Unlimited | Review retention |

### Scaling Procedures

**AKS Horizontal Scaling:**
```bash
# Scale node pool
az aks nodepool scale --resource-group rg-aoai-prod --cluster-name aks-aoai-prod --name workload --node-count 5
```

**OpenAI Capacity:**
```bash
# Update deployment capacity (requires Portal or ARM)
# Request quota increase via Azure Portal support
```

### Capacity Review Schedule

| Review | Frequency | Focus |
|--------|-----------|-------|
| Daily | Automated | Alerts on thresholds |
| Weekly | Manual | Growth trends |
| Monthly | Planning | Forecast vs actual |
| Quarterly | Strategic | Capacity planning |

---

## Backup & Recovery

### Backup Schedule

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| Storage | Continuous | 30 days | Soft delete + versioning |
| Key Vault | Continuous | 90 days | Soft delete |
| AKS Config | Daily | 30 days | GitOps |
| AI Search Index | Daily | 7 days | Index backup |

### Recovery Procedures

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Blob deletion | 1 hour | 0 | Restore from soft delete |
| Container deletion | 1 hour | 0 | Restore from soft delete |
| Key Vault secret | 15 min | 0 | Recover from soft delete |
| AKS cluster | 2 hours | 0 | Redeploy from Terraform |
| Search index | 4 hours | 24 hours | Rebuild from documents |

### DR Test Schedule

| Test | Frequency | Duration |
|------|-----------|----------|
| Backup verification | Weekly | Automated |
| Single service recovery | Monthly | 2 hours |
| Full DR simulation | Annually | 1 day |

---

## Maintenance Windows

### Scheduled Maintenance

| Window | Time (UTC) | Duration | Notice |
|--------|------------|----------|--------|
| Regular | Sunday 02:00 | 4 hours | 48 hours |
| Emergency | As needed | As needed | Best effort |

### Maintenance Checklist

```markdown
Before Maintenance:
- [ ] Notify stakeholders (48+ hours)
- [ ] Confirm change approved
- [ ] Prepare rollback plan
- [ ] Scale down non-critical

During Maintenance:
- [ ] Monitor health
- [ ] Execute changes
- [ ] Verify each step
- [ ] Test functionality

After Maintenance:
- [ ] Confirm all services up
- [ ] Run smoke tests
- [ ] Remove maintenance notice
- [ ] Document completion
```

### Patching Schedule

| Component | Frequency | Window |
|-----------|-----------|--------|
| AKS | Monthly | Maintenance window |
| OS patches | Monthly | Maintenance window |
| Application | As needed | CI/CD |
| Dependencies | Weekly | CI/CD |

---

## Contacts & Escalation

| Level | Contact | When |
|-------|---------|------|
| L1 | On-call | First response |
| L2 | Platform Team Lead | 30 min no progress |
| L3 | Architecture | Complex issues |
| Management | Engineering Manager | P0 incidents |
| External | Microsoft Support | Azure issues |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Operations Team |
| Review | Monthly |
