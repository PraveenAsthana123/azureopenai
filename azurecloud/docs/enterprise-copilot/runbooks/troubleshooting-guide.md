# Enterprise Copilot - Troubleshooting Guide

## Quick Reference

| Symptom | Likely Cause | Quick Fix | Section |
|---------|--------------|-----------|---------|
| High latency (>5s) | OpenAI rate limiting | Check quota, enable caching | [Latency Issues](#latency-issues) |
| "No information found" | Index issues, RBAC | Verify index, check ACLs | [Retrieval Issues](#retrieval-issues) |
| 401/403 errors | Authentication | Check managed identities | [Auth Issues](#authentication-issues) |
| Empty responses | Context too large | Reduce chunk size | [Generation Issues](#generation-issues) |
| Ingestion failures | Parsing errors | Check document format | [Ingestion Issues](#ingestion-issues) |

---

## Latency Issues

### Symptom: P95 Latency > 5 seconds

**Diagnosis Steps:**

1. **Identify the bottleneck component:**
   ```kql
   customMetrics
   | where timestamp > ago(1h)
   | where name in ('embedding_latency', 'search_latency', 'llm_latency')
   | summarize avg_ms = avg(value), p95_ms = percentile(value, 95) by name
   | order by p95_ms desc
   ```

2. **Expected latency breakdown:**
   | Component | Normal P95 | Warning | Critical |
   |-----------|------------|---------|----------|
   | Embedding | < 200ms | 200-500ms | > 500ms |
   | Search | < 300ms | 300-800ms | > 800ms |
   | Reranking | < 500ms | 500-1000ms | > 1000ms |
   | LLM | < 3000ms | 3000-5000ms | > 5000ms |

**Resolution by Component:**

#### High Embedding Latency
```bash
# Check OpenAI embedding deployment status
az cognitiveservices account deployment show \
  --name openai-copilot-prod \
  --resource-group rg-copilot-prod \
  --deployment-name text-embedding-3-large

# Check rate limiting
az monitor metrics list \
  --resource openai-copilot-prod \
  --resource-group rg-copilot-prod \
  --metric "RateLimitedCalls" \
  --interval PT1H
```

**Fixes:**
- Enable embedding cache in Cosmos DB
- Increase TPM quota for embedding model
- Batch multiple queries for embedding

#### High Search Latency
```bash
# Check search service health
az search service show \
  --name search-copilot-prod \
  --resource-group rg-copilot-prod

# Check replica count
az search service show --name search-copilot-prod \
  --query "{replicas: replicaCount, partitions: partitionCount}"
```

**Fixes:**
- Add search replicas (for read throughput)
- Check index health and optimize
- Review vector search configuration (reduce k value)

#### High LLM Latency
```bash
# Check model deployment
az cognitiveservices account deployment show \
  --name openai-copilot-prod \
  --deployment-name gpt-4o

# Check PTU vs paygo
az cognitiveservices account deployment show \
  --name openai-copilot-prod \
  --deployment-name gpt-4o \
  --query "sku"
```

**Fixes:**
- Reduce context window size (fewer chunks)
- Use streaming responses
- Consider PTU deployment for consistent latency
- Enable response caching

---

## Retrieval Issues

### Symptom: "I don't have information about that"

**Diagnosis Steps:**

1. **Verify documents exist in index:**
   ```bash
   # Search directly in index
   az search document search \
     --service-name search-copilot-prod \
     --index-name enterprise-knowledge-index \
     --search "vacation policy" \
     --select "title,chunk_text" \
     --top 5
   ```

2. **Check document count:**
   ```kql
   AzureMetrics
   | where ResourceProvider == "MICROSOFT.SEARCH"
   | where MetricName == "DocumentCount"
   | summarize doc_count = max(Maximum) by bin(TimeGenerated, 1d)
   | order by TimeGenerated desc
   | take 7
   ```

3. **Test embedding generation:**
   ```python
   # Quick test script
   from openai import AzureOpenAI

   client = AzureOpenAI(...)
   response = client.embeddings.create(
       model="text-embedding-3-large",
       input="vacation policy"
   )
   print(f"Embedding dimensions: {len(response.data[0].embedding)}")
   # Should be 3072
   ```

**Common Causes & Fixes:**

#### 1. Documents Not Indexed
```bash
# Check indexer status
az search indexer status \
  --service-name search-copilot-prod \
  --indexer-name document-indexer

# If stuck, reset and re-run
az search indexer reset --service-name search-copilot-prod \
  --indexer-name document-indexer
az search indexer run --service-name search-copilot-prod \
  --indexer-name document-indexer
```

#### 2. Empty Embeddings
```kql
# Find documents with empty embeddings
AzureDiagnostics
| where ResourceType == "SEARCHSERVICES"
| where operation_Name == "Indexing"
| where Message contains "empty" or Message contains "null"
```

**Fix:** Re-run embedding generation for affected documents.

#### 3. RBAC Filters Too Restrictive
```kql
# Check RBAC filter patterns
traces
| where operation_Name == "search_query"
| extend filter = tostring(customDimensions.acl_filter)
| summarize count() by filter
| order by count_ desc
```

**Fix:** Verify user group memberships match document ACLs.

#### 4. Semantic Configuration Issues
```json
// Verify semantic config in index
{
  "semanticConfiguration": {
    "name": "semantic-config",
    "prioritizedFields": {
      "titleField": { "fieldName": "title" },
      "contentFields": [
        { "fieldName": "chunk_text" }
      ]
    }
  }
}
```

---

## Authentication Issues

### Symptom: 401 Unauthorized or 403 Forbidden

**Diagnosis Steps:**

1. **Check managed identity status:**
   ```bash
   # Function App managed identity
   az functionapp identity show \
     --name func-copilot-prod \
     --resource-group rg-copilot-prod

   # Verify identity is enabled
   # Output should show "type": "SystemAssigned"
   ```

2. **Verify role assignments:**
   ```bash
   # List role assignments for the managed identity
   az role assignment list \
     --assignee <principal-id> \
     --output table
   ```

3. **Check Application Insights for auth errors:**
   ```kql
   dependencies
   | where timestamp > ago(1h)
   | where resultCode in ("401", "403")
   | summarize count() by target, resultCode
   ```

**Required Role Assignments:**

| Resource | Role | Purpose |
|----------|------|---------|
| Azure OpenAI | Cognitive Services OpenAI User | API access |
| AI Search | Search Index Data Reader | Query access |
| AI Search | Search Index Data Contributor | Indexing |
| Cosmos DB | Cosmos DB Data Contributor | Cache operations |
| Key Vault | Key Vault Secrets User | Secret access |
| Storage | Storage Blob Data Contributor | Document access |

**Assign Missing Roles:**
```bash
# Example: Assign OpenAI role
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<openai-account>
```

### Symptom: Token Expired or Invalid

```bash
# Force token refresh
az account clear
az login
az account set --subscription <subscription-id>
```

For managed identity issues in Functions:
```bash
# Restart the function app to refresh tokens
az functionapp restart --name func-copilot-prod --resource-group rg-copilot-prod
```

---

## Generation Issues

### Symptom: Empty or Truncated Responses

**Diagnosis Steps:**

1. **Check context size:**
   ```kql
   customMetrics
   | where name == "context_tokens"
   | summarize avg_tokens = avg(value), max_tokens = max(value)
   ```

2. **Review token limits:**
   | Model | Max Context | Recommended Context | Max Output |
   |-------|-------------|---------------------|------------|
   | gpt-4o | 128K | 8-16K | 4K |
   | gpt-4 | 8K/32K | 4-6K | 4K |
   | gpt-35-turbo | 16K | 4-8K | 4K |

**Fixes:**

#### Context Too Large
```python
# Reduce chunks in config
CHUNKING_CONFIG = {
    "max_context_chunks": 5,  # Reduce from 10
    "max_tokens_per_chunk": 500,  # Reduce from 1000
}
```

#### Response Truncation
```python
# Increase max_tokens in generation
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    max_tokens=2000,  # Increase if needed
)
```

### Symptom: Hallucinations in Responses

**Diagnosis:**
```kql
customMetrics
| where name == "hallucination_score"
| where value > 0.3  # High hallucination
| summarize count() by bin(timestamp, 1h)
```

**Fixes:**
1. Strengthen system prompt grounding instructions
2. Enable groundedness checking
3. Reduce temperature to 0.1-0.3
4. Add citation requirements

---

## Ingestion Issues

### Symptom: Documents Not Appearing After Upload

**Diagnosis Steps:**

1. **Check Data Factory pipeline:**
   ```bash
   az datafactory pipeline-run query-by-factory \
     --factory-name adf-copilot-prod \
     --resource-group rg-copilot-prod \
     --last-updated-after "2024-01-01T00:00:00Z"
   ```

2. **Check Function logs:**
   ```kql
   traces
   | where operation_Name contains "ingestion"
   | where severityLevel >= 3
   | order by timestamp desc
   | take 50
   ```

3. **Check dead letter queue:**
   ```bash
   az storage message peek \
     --account-name stcopilotprod \
     --queue-name ingestion-dlq \
     --num-messages 10
   ```

**Common Causes & Fixes:**

#### 1. Unsupported Document Format
```python
# Supported formats
SUPPORTED_FORMATS = ['.pdf', '.docx', '.doc', '.pptx', '.html', '.md', '.txt']

# Check file extension before processing
```

**Fix:** Convert unsupported formats or add custom parser.

#### 2. Document Too Large
```bash
# Check document size limits
# Default: 100MB max
# For Azure Document Intelligence: 500MB max
```

**Fix:** Split large documents or use Document Intelligence for large PDFs.

#### 3. Parsing Errors
```kql
traces
| where operation_Name == "document_parsing"
| where severityLevel >= 3
| extend error = tostring(customDimensions.error_message)
| summarize count() by error
```

**Fix:** Check document for corruption, password protection, or complex layouts.

#### 4. Chunking Failures
```kql
traces
| where operation_Name == "document_chunking"
| where severityLevel >= 3
| project timestamp, message, customDimensions
```

**Fix:** Adjust chunking parameters for problematic document types.

---

## Cache Issues

### Symptom: Low Cache Hit Rate (<30%)

**Diagnosis:**
```kql
customMetrics
| where name == "cache_hit_rate"
| summarize avg_rate = avg(value) by bin(timestamp, 1h)
| order by timestamp desc
```

**Fixes:**

1. **Increase cache TTL:**
   ```python
   CACHE_CONFIG = {
       "ttl_seconds": 3600 * 24,  # 24 hours
       "max_items": 10000,
   }
   ```

2. **Review cache key strategy:**
   ```python
   # Ensure similar queries hit same cache entry
   def normalize_query(query: str) -> str:
       return query.lower().strip()
   ```

3. **Check Cosmos DB RU consumption:**
   ```bash
   az monitor metrics list \
     --resource cosmos-copilot-prod \
     --resource-group rg-copilot-prod \
     --metric "NormalizedRUConsumption"
   ```

### Symptom: Cache Errors

```kql
dependencies
| where target contains "cosmos"
| where success == false
| summarize count() by resultCode
```

**Fixes:**
- Increase Cosmos DB RUs
- Check partition key strategy
- Verify managed identity permissions

---

## Rate Limiting Issues

### Symptom: 429 Too Many Requests

**Diagnosis:**
```kql
dependencies
| where resultCode == "429"
| summarize count() by target, bin(timestamp, 5m)
```

**Fixes by Service:**

#### Azure OpenAI
```bash
# Check current quota
az cognitiveservices account deployment show \
  --name openai-copilot-prod \
  --deployment-name gpt-4o \
  --query "properties.rateLimits"

# Request quota increase via Azure Portal
```

**Mitigation strategies:**
- Enable request queuing
- Implement exponential backoff
- Use caching aggressively
- Consider PTU deployment

#### AI Search
```bash
# Check search service tier
az search service show \
  --name search-copilot-prod \
  --query "sku"
```

**Mitigation:**
- Upgrade search tier
- Add replicas
- Implement client-side rate limiting

---

## Network Issues

### Symptom: Timeout Errors or Connection Refused

**Diagnosis:**

1. **Check private endpoint status:**
   ```bash
   az network private-endpoint show \
     --name pe-openai-copilot-prod \
     --resource-group rg-copilot-prod
   ```

2. **Verify DNS resolution:**
   ```bash
   # From within the VNet (e.g., from a VM or Cloud Shell)
   nslookup openai-copilot-prod.openai.azure.com
   # Should resolve to private IP
   ```

3. **Check NSG rules:**
   ```bash
   az network nsg rule list \
     --nsg-name nsg-copilot-prod \
     --resource-group rg-copilot-prod \
     --output table
   ```

**Fixes:**
- Verify private DNS zone is linked to VNet
- Check NSG allows outbound HTTPS (443)
- Verify subnet service endpoints

---

## Health Check Failures

### Quick Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "=== Enterprise Copilot Health Check ==="

# 1. API Health
echo -n "API Health: "
curl -s https://api.company.com/health | jq -r '.status'

# 2. OpenAI
echo -n "OpenAI: "
az cognitiveservices account show --name openai-copilot-prod \
  --resource-group rg-copilot-prod \
  --query "properties.provisioningState" -o tsv

# 3. Search
echo -n "AI Search: "
az search service show --name search-copilot-prod \
  --resource-group rg-copilot-prod \
  --query "status" -o tsv

# 4. Cosmos DB
echo -n "Cosmos DB: "
az cosmosdb show --name cosmos-copilot-prod \
  --resource-group rg-copilot-prod \
  --query "properties.documentEndpoint" -o tsv && echo "OK"

# 5. Function App
echo -n "Functions: "
az functionapp show --name func-copilot-prod \
  --resource-group rg-copilot-prod \
  --query "state" -o tsv
```

---

## Escalation Paths

| Issue Type | First Contact | Escalation | External |
|------------|--------------|------------|----------|
| Performance | Platform Team | Tech Lead | Microsoft Support |
| Security | Security Team | CISO | Microsoft Security |
| Data Issues | Data Team | Data Lead | - |
| Infrastructure | DevOps | Cloud Architect | Microsoft Support |

**Microsoft Support:**
- Premier Support: 1-800-XXX-XXXX
- Azure Portal: Support + Troubleshooting
- Priority: Specify impact (Critical/High/Medium)

---

*Last Updated: 2025-01-15*
*Version: 1.0*
