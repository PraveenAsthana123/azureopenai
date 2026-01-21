# Enterprise Copilot - Administrator Runbook

## Table of Contents

1. [System Overview](#system-overview)
2. [Daily Operations](#daily-operations)
3. [Common Tasks](#common-tasks)
4. [Troubleshooting](#troubleshooting)
5. [Incident Response](#incident-response)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Disaster Recovery](#disaster-recovery)

---

## System Overview

### Architecture Components

| Component | Service | Purpose | Health Check |
|-----------|---------|---------|--------------|
| RAG Orchestrator | Azure Functions / AKS | Query processing | `/health` endpoint |
| AI Search | Azure AI Search | Document retrieval | Portal metrics |
| LLM | Azure OpenAI | Response generation | API status |
| Cache | Cosmos DB | Session & answer cache | Container metrics |
| Ingestion | Durable Functions | Document processing | Function logs |
| Frontend | Copilot Studio | User interface | Teams health |

### Key Endpoints

```
Production:
- RAG API: https://api.company.com/rag
- Health: https://api.company.com/health
- Metrics: https://api.company.com/metrics

Staging:
- RAG API: https://staging-api.company.com/rag
```

### Access & Permissions

| Role | Access Level | Azure Groups |
|------|--------------|--------------|
| Platform Admin | Full access | `Copilot-Admins` |
| Operations | Read + restart | `Copilot-Ops` |
| Developer | Read-only prod | `Copilot-Devs` |
| Support | Logs only | `Copilot-Support` |

---

## Daily Operations

### Morning Checklist (9 AM)

1. **Check System Health**
   ```bash
   # Check health endpoints
   curl https://api.company.com/health

   # Expected response:
   # {"status": "healthy", "dependencies": {...}}
   ```

2. **Review Overnight Alerts**
   - Azure Portal → Monitor → Alerts
   - Check for any triggered alerts
   - Review and acknowledge

3. **Check Key Metrics**
   - Response latency P95 < 3s
   - Error rate < 1%
   - Cache hit rate > 50%

4. **Verify Ingestion Pipeline**
   - Check Data Factory runs
   - Verify index document count
   - Review failed ingestion logs

### Key Metrics Dashboard

Access: Azure Portal → Dashboards → Enterprise Copilot Operations

| Metric | Normal Range | Alert Threshold |
|--------|--------------|-----------------|
| Latency P50 | < 1.5s | > 2s |
| Latency P95 | < 3s | > 5s |
| Error Rate | < 0.5% | > 2% |
| Cache Hit Rate | > 60% | < 30% |
| Daily Queries | 500-2000 | < 100 (investigate) |
| Index Size | Growing | Sudden drop |

---

## Common Tasks

### 1. Add New Document Source

```bash
# 1. Add connector configuration
# Edit: infrastructure/terraform/enterprise/data-sources.tf

# 2. Deploy connector
terraform apply -target=module.sharepoint_connector

# 3. Configure in Data Factory
# Create new pipeline for the source

# 4. Run initial sync
az datafactory pipeline create-run \
  --resource-group rg-copilot-prod \
  --factory-name adf-copilot-prod \
  --name "sharepoint-new-site-pipeline"

# 5. Verify index population
az search index show --name enterprise-knowledge-index
```

### 2. Update ACL for Document

```bash
# 1. Get document ID
az search document search --index enterprise-knowledge-index \
  --search "document_title" \
  --select "id,title,acl_groups"

# 2. Update ACL groups
# Use the indexer or manual update
az search document merge --index enterprise-knowledge-index \
  --body '{
    "value": [{
      "@search.action": "merge",
      "id": "doc_123",
      "acl_groups": ["HR-Team", "Finance-Team"]
    }]
  }'
```

### 3. Reindex Documents

```bash
# Full reindex (use sparingly)
az search indexer reset --name document-indexer \
  --resource-group rg-copilot-prod \
  --service-name search-copilot-prod

az search indexer run --name document-indexer \
  --resource-group rg-copilot-prod \
  --service-name search-copilot-prod

# Monitor progress
az search indexer status --name document-indexer
```

### 4. Clear Cache

```python
# Clear answer cache (use Azure Portal or SDK)
from azure.cosmos import CosmosClient

client = CosmosClient(endpoint, credential)
database = client.get_database_client("genai_platform")
container = database.get_container_client("answer_cache")

# Delete all items (careful!)
for item in container.query_items("SELECT c.id, c.query_hash FROM c"):
    container.delete_item(item["id"], partition_key=item["query_hash"])
```

### 5. Update System Prompt

```bash
# 1. Edit prompt in code
# src/prompts/prompt_templates.py

# 2. Deploy via CI/CD
git commit -m "Update system prompt for better citations"
git push origin main

# 3. Verify deployment
curl https://api.company.com/health | jq .version
```

### 6. Add User to Access Group

```bash
# Via Azure CLI
az ad group member add \
  --group "Copilot-Users" \
  --member-id "user-object-id"

# Verify
az ad group member check \
  --group "Copilot-Users" \
  --member-id "user-object-id"
```

---

## Troubleshooting

### Issue: High Latency (> 5s)

**Symptoms:**
- Users report slow responses
- P95 latency alerts firing

**Diagnostic Steps:**
```bash
# 1. Check component latencies
# Azure Portal → Application Insights → Performance

# 2. Identify bottleneck (usually one of):
# - Embedding generation: ~500ms
# - Search retrieval: ~200ms
# - LLM generation: ~2000ms

# 3. Check for rate limiting
az monitor metrics list --resource openai-copilot-prod \
  --metric "TokenTransaction" --interval PT1H
```

**Resolution:**
| Bottleneck | Action |
|------------|--------|
| Embeddings | Check OpenAI quota, enable caching |
| Search | Add replicas, check index health |
| LLM | Check quota, reduce context size |
| Network | Check private endpoint DNS |

### Issue: Low Retrieval Quality

**Symptoms:**
- Users report irrelevant answers
- "I don't have information" responses for known topics

**Diagnostic Steps:**
```bash
# 1. Test retrieval directly
POST https://search-copilot-prod.search.windows.net/indexes/enterprise-knowledge-index/docs/search
{
  "search": "vacation policy",
  "top": 5,
  "select": "title,chunk_text,@search.score"
}

# 2. Check if documents exist
# 3. Verify embeddings are populated
# 4. Check ACL filters aren't too restrictive
```

**Resolution:**
- Re-run embedding generation for affected docs
- Check chunking configuration
- Adjust search scoring profile
- Verify user has correct group membership

### Issue: RBAC Bypass Suspected

**Symptoms:**
- User sees content they shouldn't
- Audit logs show unauthorized access

**Immediate Actions:**
```bash
# 1. Capture evidence
az monitor log-analytics query -w workspace-id \
  --analytics-query "requests | where user_id == 'suspect_user'"

# 2. Disable user access temporarily
az ad group member remove --group "Copilot-Users" --member-id "user-id"

# 3. Review document ACLs
# 4. Escalate to Security team
```

### Issue: Ingestion Pipeline Failure

**Symptoms:**
- New documents not appearing in search
- Data Factory pipeline failures

**Diagnostic Steps:**
```bash
# 1. Check pipeline status
az datafactory pipeline-run query-by-factory \
  --factory-name adf-copilot-prod \
  --resource-group rg-copilot-prod

# 2. Check function logs
az monitor app-insights query --app ai-copilot-prod \
  --analytics-query "traces | where operation_Name == 'ingestion_orchestrator'"

# 3. Check dead letter queue
az storage message peek --queue-name ingestion-dlq
```

**Resolution:**
- Retry failed documents
- Check source system connectivity
- Verify managed identity permissions

### Issue: High Error Rate

**Symptoms:**
- Error rate > 2%
- Users seeing error messages

**Diagnostic Steps:**
```bash
# 1. Identify error types
az monitor app-insights query --app ai-copilot-prod \
  --analytics-query "
    exceptions
    | where timestamp > ago(1h)
    | summarize count() by type, outerMessage
    | order by count_ desc
  "

# 2. Check specific errors
# Common: 429 (rate limit), 401 (auth), 500 (server error)
```

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time | Escalation |
|-------|------------|---------------|------------|
| P1 | Complete outage | 15 min | Immediate on-call |
| P2 | Major degradation | 1 hour | Team lead |
| P3 | Minor issues | 4 hours | Standard |
| P4 | Enhancement | Next sprint | Backlog |

### P1 Incident Playbook

```
1. ACKNOWLEDGE (5 min)
   - Join incident bridge: teams.company.com/copilot-incident
   - Acknowledge in PagerDuty
   - Post initial status

2. ASSESS (10 min)
   - Run health checks
   - Check dashboards
   - Identify affected users

3. MITIGATE (variable)
   - Apply known fix or
   - Rollback to last good version
   - Enable maintenance mode if needed

4. COMMUNICATE
   - Update status page
   - Notify stakeholders
   - Regular updates every 30 min

5. RESOLVE & DOCUMENT
   - Verify fix
   - Write incident report
   - Schedule post-mortem
```

### Rollback Procedure

```bash
# 1. Identify last good deployment
az functionapp deployment list --name func-copilot-prod

# 2. Rollback to specific version
az functionapp deployment slot swap \
  --name func-copilot-prod \
  --slot staging \
  --action swap

# 3. Verify health
curl https://api.company.com/health

# 4. Monitor for 15 minutes
```

---

## Maintenance Procedures

### Weekly Maintenance

1. **Review Performance Trends**
   - Check week-over-week metrics
   - Identify degradation patterns

2. **Index Optimization**
   ```bash
   # Check index statistics
   az search index show --name enterprise-knowledge-index

   # If fragmentation > 20%, consider reindex
   ```

3. **Log Cleanup**
   - Archive logs older than 30 days
   - Review storage costs

4. **Security Review**
   - Check for new CVEs
   - Review access logs

### Monthly Maintenance

1. **Capacity Review**
   - Check OpenAI quota utilization
   - Review AI Search unit usage
   - Plan scaling if > 70% utilization

2. **Cost Review**
   - Review monthly spend by component
   - Identify optimization opportunities

3. **Prompt Optimization**
   - Review evaluation metrics
   - Update prompts if needed

4. **Documentation Update**
   - Update runbooks with new procedures
   - Review and refresh training materials

---

## Disaster Recovery

### RPO/RTO Targets

| Component | RPO | RTO |
|-----------|-----|-----|
| Search Index | 24 hours | 4 hours |
| Cosmos DB | 1 hour | 2 hours |
| Configuration | 0 | 1 hour |
| Documents | 24 hours | 8 hours |

### Recovery Procedures

#### Search Index Recovery

```bash
# 1. Create new search service (if needed)
az search service create --name search-copilot-dr \
  --resource-group rg-copilot-dr \
  --sku Standard

# 2. Create index schema
az search index create --name enterprise-knowledge-index \
  --definition @search-schema/vector-index.json

# 3. Trigger reindex from source
az datafactory pipeline create-run --name full-reindex-pipeline
```

#### Cosmos DB Recovery

```bash
# 1. Point-in-time restore
az cosmosdb sql database restore \
  --account-name cosmos-copilot-prod \
  --name genai_platform \
  --restore-timestamp "2024-01-15T10:00:00Z"
```

#### Full DR Failover

```bash
# 1. Activate DR environment
cd infrastructure/terraform/dr
terraform apply

# 2. Update DNS
az network dns record-set a update \
  --zone-name company.com \
  --record-set-name api \
  --ipv4-address "DR_IP_ADDRESS"

# 3. Verify services
curl https://api.company.com/health
```

---

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | PagerDuty | Automatic |
| Platform Lead | platform-lead@company.com | P1/P2 incidents |
| Security Team | security@company.com | Security incidents |
| Microsoft Support | Premier support | Azure issues |

---

*Last Updated: 2025-01-15*
*Version: 1.0*
