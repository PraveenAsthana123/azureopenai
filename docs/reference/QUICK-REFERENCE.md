# Quick Reference Card

> **Cheat Sheets & Checklists for Azure OpenAI Enterprise Platform**

---

## Emergency Contacts

| Role | Contact | When |
|------|---------|------|
| On-Call | [PagerDuty] | Any incident |
| Security | [Email] | Security events |
| Management | [Email] | P0 incidents |
| Microsoft | [Support] | Azure issues |

---

## Incident Severity Guide

| Severity | Definition | Response | Example |
|----------|------------|----------|---------|
| **P0** | Total outage / breach | Immediate 24x7 | Platform down |
| **P1** | Major degradation | < 1 hour | AI service down |
| **P2** | Partial impact | < 4 hours | Single feature |
| **P3** | Minor issue | Business hours | Performance |

---

## Key Azure CLI Commands

### AKS

```bash
# Get credentials
az aks get-credentials -g rg-aoai-prod -n aks-aoai-prod

# Check nodes
kubectl get nodes

# Check all pods
kubectl get pods -A

# Restart deployment
kubectl rollout restart deployment/<name> -n <namespace>

# View logs
kubectl logs -f deployment/<name> -n <namespace>

# Scale
kubectl scale deployment/<name> --replicas=N -n <namespace>
```

### Azure Functions

```bash
# View logs
az functionapp log tail -n func-aoai-prod -g rg-aoai-prod

# Restart
az functionapp restart -n func-aoai-prod -g rg-aoai-prod

# Status
az functionapp show -n func-aoai-prod -g rg-aoai-prod --query state
```

### Storage

```bash
# List containers
az storage container list --account-name staoaiprod --auth-mode login -o table

# Download file
az storage blob download --account-name staoaiprod -c documents -n file.pdf -f local.pdf --auth-mode login
```

### Key Vault

```bash
# List secrets
az keyvault secret list --vault-name kv-aoaiprod -o table

# Get secret (careful!)
az keyvault secret show --vault-name kv-aoaiprod -n secret-name --query value -o tsv
```

---

## Terraform Commands

```bash
# Initialize
terraform init

# Plan (dev)
terraform plan -var-file="environments/dev/terraform.tfvars"

# Apply (dev)
terraform apply -var-file="environments/dev/terraform.tfvars"

# Destroy (careful!)
terraform destroy -var-file="environments/dev/terraform.tfvars"

# State list
terraform state list

# Import existing
terraform import <resource> <id>
```

---

## Monitoring Quick Links

| Dashboard | Purpose |
|-----------|---------|
| Azure Portal | All resources |
| Log Analytics | Queries & alerts |
| App Insights | Application metrics |
| Cost Management | Spending |
| Security Center | Security posture |

### Key Log Analytics Queries

```kusto
// Error rate last hour
requests
| where timestamp > ago(1h)
| summarize errors = countif(success == false), total = count()
| extend error_rate = errors * 100.0 / total

// OpenAI latency P95
dependencies
| where type == "Azure OpenAI"
| summarize p95 = percentile(duration, 95) by bin(timestamp, 5m)
| render timechart

// Top errors
exceptions
| where timestamp > ago(24h)
| summarize count() by type, outerMessage
| top 10 by count_

// Token usage
customMetrics
| where name == "TokensUsed"
| summarize total = sum(value) by bin(timestamp, 1h)
| render timechart
```

---

## Change Management Quick Guide

### Standard Change (Pre-Approved)
1. Follow runbook
2. Update ticket
3. Done

### Normal Change
1. Submit CR (3 days before)
2. Impact analysis
3. CAB approval
4. Implement in window
5. Validate
6. Close CR

### Emergency Change
1. Get verbal approval
2. Implement fix
3. Submit CR within 24h
4. Retrospective

---

## Security Checklist

### Daily
- [ ] Review security alerts
- [ ] Check failed logins
- [ ] Verify backups

### Weekly
- [ ] Review access logs
- [ ] Check vulnerability scans
- [ ] Update threat intel

### Monthly
- [ ] Access review
- [ ] Patch status
- [ ] Security metrics

### Quarterly
- [ ] Full access recertification
- [ ] Penetration test
- [ ] Policy review

---

## AI Governance Quick Guide

### New AI Use Case
1. Fill intake form
2. Risk classification
3. Ethics review (if Medium+)
4. Approval
5. Implement with controls
6. Monitor

### Risk Levels
| Level | Approval | Examples |
|-------|----------|----------|
| Low | Team Lead | Internal tools |
| Medium | Ethics Committee | Customer-facing |
| High | Governance Board | Critical decisions |

### GenAI Controls Required
- [ ] System prompt approved
- [ ] Content filters enabled
- [ ] Output logging enabled
- [ ] HITL where required
- [ ] Monitoring configured

---

## Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] Security scan clean
- [ ] Change request approved
- [ ] Rollback plan ready
- [ ] Team notified

### Post-Deployment
- [ ] Health checks passing
- [ ] Monitoring verified
- [ ] Smoke tests completed
- [ ] Documentation updated
- [ ] Change request closed

---

## Network Quick Reference

### Subnets

| Subnet | CIDR | Purpose |
|--------|------|---------|
| snet-aks | 10.0.0.0/22 | AKS nodes |
| snet-functions | 10.0.4.0/24 | Functions |
| snet-pe | 10.0.5.0/24 | Private endpoints |
| snet-bastion | 10.0.6.0/26 | Bastion |
| snet-appgw | 10.0.7.0/24 | App Gateway |

### Private DNS Zones

| Service | Zone |
|---------|------|
| Key Vault | privatelink.vaultcore.azure.net |
| Storage | privatelink.blob.core.windows.net |
| OpenAI | privatelink.openai.azure.com |
| Search | privatelink.search.windows.net |

---

## Cost Quick Reference

### Top Cost Drivers
1. AKS compute
2. OpenAI tokens
3. AI Search
4. Storage
5. Log retention

### Cost Optimization Tips
- Right-size AKS nodes
- Use autoscaling
- Monitor token usage
- Archive old data
- Review log retention

---

## Naming Conventions

```
{resource-type}-{project}-{environment}

Examples:
rg-aoai-prod          Resource Group
vnet-aoai-prod        Virtual Network
aks-aoai-prod         AKS Cluster
kv-aoaiprod           Key Vault (no hyphens)
st-aoaiprod           Storage (no hyphens)
oai-aoai-prod         Azure OpenAI
srch-aoai-prod        AI Search
func-aoai-prod        Functions
```

---

## Support Escalation

```
L1: On-Call (15 min)
    ↓
L2: Platform Team Lead (30 min no progress)
    ↓
L3: Architecture (complex issues)
    ↓
Management: P0 incidents
    ↓
Microsoft: Azure platform issues
```

---

## Related Documents

| Document | Location |
|----------|----------|
| Full Docs Index | [docs/INDEX.md](../INDEX.md) |
| Architecture | [docs/architecture/](../architecture/) |
| Security | [docs/security/](../security/) |
| Operations | [docs/operations/](../operations/) |
| Governance | [docs/governance/](../governance/) |
| Terraform | [terraform/README.md](../../terraform/README.md) |

---

## Framework Summary

| Framework | What It Covers | Key Question |
|-----------|----------------|--------------|
| **CMMI L3** | Process maturity | How do we build consistently? |
| **ISO 42001** | AI governance | How do we govern AI responsibly? |
| **NIST AI RMF** | Risk management | Can we prove risk is controlled? |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Platform Team |
