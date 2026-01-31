# Migration & Upgrade Guide — Azure OpenAI Enterprise RAG Platform

> Comprehensive migration playbook for model versions, SDK upgrades, infrastructure evolution, and zero-downtime schema changes — aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF**.

---

## Table of Contents

1. [Pre-Upgrade Checklist (Universal)](#1-pre-upgrade-checklist-universal)
2. [Model Version Migration](#2-model-version-migration)
3. [Embedding Model Migration](#3-embedding-model-migration)
4. [Azure SDK Version Upgrades](#4-azure-sdk-version-upgrades)
5. [Terraform Provider Version Upgrades](#5-terraform-provider-version-upgrades)
6. [AKS Version Upgrades](#6-aks-version-upgrades)
7. [Python Runtime Upgrades](#7-python-runtime-upgrades)
8. [Database Schema Evolution](#8-database-schema-evolution)
9. [Search Index Schema Migration](#9-search-index-schema-migration)
10. [Breaking Change Handling](#10-breaking-change-handling)
11. [Deprecated API Handling](#11-deprecated-api-handling)
12. [Rollback Procedures](#12-rollback-procedures)
13. [Post-Upgrade Validation Checklist](#13-post-upgrade-validation-checklist)
14. [Version Compatibility Matrix](#14-version-compatibility-matrix)
15. [Upgrade Scheduling & Governance](#15-upgrade-scheduling--governance)

---

## 1. Pre-Upgrade Checklist (Universal)

Every upgrade — regardless of type — **must** pass through this gate before execution.

| # | Check | Owner | Evidence Required | Blocking |
|---|-------|-------|-------------------|----------|
| 1 | **Change request** filed in ITSM tool | Platform Lead | CR number | Yes |
| 2 | **CAB approval** obtained (Sev 2+ changes) | Change Manager | CAB minutes | Yes |
| 3 | **Backup verified** — all stateful services | SRE | Backup job logs | Yes |
| 4 | **Rollback plan** documented and peer-reviewed | Upgrade Owner | Rollback runbook | Yes |
| 5 | **Staging validation** passed (full test suite) | QA Lead | Test report URL | Yes |
| 6 | **Dependency scan** — no known CVEs introduced | Security | Trivy / Snyk report | Yes |
| 7 | **Communication sent** to stakeholders | Product Owner | Email / Slack thread | Yes |
| 8 | **Monitoring dashboards** reviewed — baseline captured | SRE | Dashboard snapshot | Yes |
| 9 | **On-call roster** confirmed for upgrade window | SRE Manager | On-call schedule | Yes |
| 10 | **Feature flags** configured for gradual rollout | Dev Lead | Feature flag config | No |
| 11 | **Cost impact** estimated | FinOps | Cost projection | No |
| 12 | **Runbook** updated for new version specifics | Upgrade Owner | Runbook diff | Yes |

```
                    ┌──────────────────────┐
                    │   Upgrade Requested   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Is it a breaking      │
                    │ change?               │
                    └──┬───────────────┬───┘
                   Yes │               │ No
                       │               │
            ┌──────────▼──────┐  ┌─────▼──────────────┐
            │ Full migration  │  │ Zero downtime       │
            │ plan required   │  │ possible?           │
            │ (Section 10)    │  └──┬─────────────┬───┘
            └──────────┬──────┘  Yes│             │No
                       │            │             │
                       │  ┌─────────▼────┐ ┌─────▼──────────┐
                       │  │ Rolling      │ │ Maintenance    │
                       │  │ upgrade      │ │ window         │
                       │  └──────────────┘ └────────────────┘
                       │
            ┌──────────▼──────────────┐
            │ Schedule CAB review     │
            │ Minimum 5 business days │
            └─────────────────────────┘
```

---

## 2. Model Version Migration

### 2.1 Pre-Migration: Deploy Target Model in Parallel

```bash
# Deploy new model version alongside existing one
az cognitiveservices account deployment create \
  --name "oai-genai-copilot-prod-eus" \
  --resource-group "rg-genai-copilot-prod-eastus" \
  --deployment-name "gpt-4o-2024-08-06" \
  --model-name "gpt-4o" \
  --model-version "2024-08-06" \
  --model-format "OpenAI" \
  --sku-capacity 40 \
  --sku-name "Standard"
```

### 2.2 Evaluation Suite

```python
async def run_model_evaluation(old_deployment: str, new_deployment: str):
    """Compare old vs new model on golden dataset."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    client = AsyncAzureOpenAI(
        azure_endpoint="https://oai-genai-copilot-prod-eus.openai.azure.com/",
        azure_ad_token=token.token, api_version="2024-06-01")
    golden_dataset = load_golden_dataset("tests/data/golden_queries.json")
    results = {"old": [], "new": []}
    for entry in golden_dataset:
        msgs = [{"role": "system", "content": entry["system_prompt"]},
                {"role": "user", "content": entry["query"]}]
        old_r = await client.chat.completions.create(model=old_deployment, messages=msgs, temperature=0.0)
        new_r = await client.chat.completions.create(model=new_deployment, messages=msgs, temperature=0.0)
        results["old"].append({"answer": old_r.choices[0].message.content, "tokens": old_r.usage.total_tokens})
        results["new"].append({"answer": new_r.choices[0].message.content, "tokens": new_r.usage.total_tokens})
    return compute_comparison_metrics(results)
```

### 2.3 Acceptance Criteria & Traffic Shifting

| Metric | Threshold | Action if Failed |
|--------|-----------|------------------|
| **Groundedness** | >= 85% (no regression > 2%) | Block migration |
| **Relevance** | >= 80% (no regression > 3%) | Block migration |
| **Coherence** | >= 90% | Block migration |
| **Latency P95** | <= 120% of baseline | Investigate, may proceed |
| **Token usage** | <= 110% of baseline | Investigate, may proceed |
| **Content safety** | 100% pass rate | Block migration |
| **Cost per query** | <= 115% of baseline | FinOps review |

```
Traffic Shift Schedule:
  Day 1-2:   ████████████████████████████████████████ 95% old │ ███ 5% new
  Day 3-5:   █████████████████████████ 75% old │ █████████████ 25% new
  Day 6-8:   █████████████ 25% old │ █████████████████████████████████████ 75% new
  Day 9-10:  ██ 0% old (standby)   │ ████████████████████████████████████████ 100% new
  Day 14+:   Old model deployment deleted after 14-day hold
```

### 2.4 Rollback (Model)

```bash
az appconfig kv set --name "appconfig-genai-copilot-prod" \
  --key "OpenAI:DeploymentName" --value "gpt-4o-2024-05-13" \
  --label "production" --yes
kubectl rollout restart deployment/rag-api -n genai-copilot
```

---

## 3. Embedding Model Migration

Embedding model migration is the **highest-risk upgrade** in a RAG platform. Embeddings from different models are **not compatible** — a query embedded with model B cannot search an index built with model A.

### 3.1 Zero-Downtime Dual-Index Migration

```
┌─────────────────────────────────────────────────────────────────────┐
│                 EMBEDDING MIGRATION (Zero-Downtime)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: Build Shadow Index                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Source Docs   │───▶│ New Embed    │───▶│ Index-v2 (shadow)    │  │
│  │ (Blob Store)  │    │ Model B      │    │ AI Search            │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                     │
│  Phase 2: Dual-Read (Canary)                                        │
│  ┌────────┐    ┌────────────────┐    ┌──────────────────────┐      │
│  │ Query  │───▶│ Embed Model A  │───▶│ Index-v1 (primary)   │──┐   │
│  │        │    └────────────────┘    └──────────────────────┘  │   │
│  │        │    ┌────────────────┐    ┌──────────────────────┐  ├──▶│
│  │        │───▶│ Embed Model B  │───▶│ Index-v2 (shadow)    │──┘   │
│  └────────┘    └────────────────┘    └──────────────────────┘      │
│                                        Results merged & ranked      │
│                                                                     │
│  Phase 3: Cutover                                                   │
│  ┌────────┐    ┌────────────────┐    ┌──────────────────────┐      │
│  │ Query  │───▶│ Embed Model B  │───▶│ Index-v2 (primary)   │      │
│  └────────┘    └────────────────┘    └──────────────────────┘      │
│                                                                     │
│  Phase 4: Cleanup — Index-v1 deleted, Model A removed               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Re-Embedding Pipeline

```python
async def re_embed_index(source_index: str, target_index: str, new_deployment: str):
    """Re-embed all documents from source into target index."""
    credential = DefaultAzureCredential()
    search = SearchClient(endpoint="https://srch-genai-copilot-prod.search.windows.net",
        index_name=source_index, credential=credential)
    target = SearchClient(endpoint="https://srch-genai-copilot-prod.search.windows.net",
        index_name=target_index, credential=credential)
    oai = AsyncAzureOpenAI(
        azure_endpoint="https://oai-genai-copilot-prod-eus.openai.azure.com/",
        azure_ad_token=credential.get_token("https://cognitiveservices.azure.com/.default").token,
        api_version="2024-06-01")
    semaphore, batch, total, success, failed = asyncio.Semaphore(10), [], 0, 0, 0
    async for doc in search.search(search_text="*", select=["*"], top=100):
        total += 1
        async with semaphore:
            try:
                resp = await oai.embeddings.create(model=new_deployment, input=doc["content"])
                doc["contentVector"] = resp.data[0].embedding
                batch.append(doc); success += 1
            except Exception:
                failed += 1
        if len(batch) >= 100:
            target.upload_documents(documents=batch); batch = []
    if batch:
        target.upload_documents(documents=batch)
    return {"total": total, "success": success, "failed": failed}
```

### 3.3 Migration Timeline

| Day | Phase | Action | Validation |
|-----|-------|--------|------------|
| 1-2 | Prepare | Create target index schema, deploy new model | Schema matches source |
| 3-7 | Re-embed | Run pipeline (est. 500K docs/day) | Doc count parity |
| 8 | Validate | Retrieval evaluation on shadow index | Relevance >= baseline |
| 9-10 | Dual-read | 10% traffic to dual-read mode | Compare result quality |
| 11-12 | Cutover | Switch primary to Index-v2 | Full test suite green |
| 13-14 | Soak | Monitor in production | No regressions |
| 15+ | Cleanup | Delete Index-v1, remove Model A | Cost reduction confirmed |

---

## 4. Azure SDK Version Upgrades

### 4.1 SDK Compatibility Matrix

| Package | Current | Target | Py 3.11 | Py 3.12 | Breaking Changes |
|---------|---------|--------|---------|---------|-----------------|
| **azure-search-documents** | 11.4.0 | 11.6.0 | Yes | Yes | New vector search API |
| **azure-cosmos** | 4.5.1 | 4.7.0 | Yes | Yes | None |
| **azure-identity** | 1.15.0 | 1.17.0 | Yes | Yes | Token cache changes |
| **azure-keyvault-secrets** | 4.7.0 | 4.8.0 | Yes | Yes | None |
| **azure-storage-blob** | 12.19.0 | 12.21.0 | Yes | Yes | None |
| **azure-monitor-opentelemetry** | 1.2.0 | 1.4.0 | Yes | Yes | Exporter config change |
| **openai** | 1.30.0 | 1.40.0 | Yes | Yes | Structured output API |

### 4.2 Upgrade Procedure

```bash
git checkout -b upgrade/azure-sdk-2024-q4

cat > requirements-upgrade.txt << 'EOF'
azure-search-documents==11.6.0
azure-cosmos==4.7.0
azure-identity==1.17.0
azure-keyvault-secrets==4.8.0
azure-storage-blob==12.21.0
azure-monitor-opentelemetry==1.4.0
openai==1.40.0
EOF

pip install -r requirements-upgrade.txt
pytest tests/ -v --tb=short --junitxml=sdk-upgrade-results.xml
python -W all -m pytest tests/ 2>&1 | grep -i "deprecat"
```

### 4.3 Key API Changes

```python
# azure-search-documents 11.6.x — new vector query parameters
vector_query = VectorizedQuery(
    vector=query_embedding, k_nearest_neighbors=5, fields="contentVector",
    exhaustive=False,   # New: HNSW vs exhaustive KNN
    oversampling=2.0,   # New: oversampling factor
)

# openai >= 1.37.0 — Structured Outputs
from pydantic import BaseModel
class AnswerResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[str]

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06", messages=messages,
    response_format=AnswerResponse)
answer = completion.choices[0].message.parsed  # Typed object
```

---

## 5. Terraform Provider Version Upgrades

### 5.1 Provider Version Matrix

| Provider | Current | Target | Terraform | Key Changes |
|----------|---------|--------|-----------|-------------|
| **azurerm** | 3.85.0 | 4.0.0 | >= 1.7.0 | Major: resource renames |
| **azuread** | 2.47.0 | 2.53.0 | >= 1.6.0 | Minor: new data sources |
| **azapi** | 1.11.0 | 1.15.0 | >= 1.6.0 | Minor: new API versions |

### 5.2 State Migration Commands

```bash
# Step 1: Backup current state
terraform state pull > terraform-state-backup-$(date +%Y%m%d).json

# Step 2: Upgrade provider and plan
terraform init -upgrade
terraform plan -out=provider-upgrade.tfplan 2>&1 | tee plan-output.txt

# Step 3: Review for destroy/recreate
grep -E "(must be replaced|will be destroyed)" plan-output.txt

# Step 4: State moves if resources renamed in new provider
terraform state mv \
  'azurerm_kubernetes_cluster.main' \
  'azurerm_kubernetes_cluster.aks'

# Step 5: Import resources that need re-import
terraform import 'azurerm_cognitive_account.openai' \
  '/subscriptions/SUB_ID/resourceGroups/rg-genai-copilot-prod-eastus/providers/Microsoft.CognitiveServices/accounts/oai-genai-copilot-prod-eus'

# Step 6: Apply and verify
terraform apply provider-upgrade.tfplan
terraform plan  # Should show "No changes"
```

### 5.3 Safety Checklist

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | State backup created | `terraform state pull > backup.json` | File size > 0 |
| 2 | Plan shows no destroys | `terraform plan` | No "destroy" actions |
| 3 | Lock file updated | `terraform init -upgrade` | `.terraform.lock.hcl` updated |
| 4 | No drift detected | `terraform plan` | "No changes" |
| 5 | Remote state accessible | `terraform state list` | All resources listed |

---

## 6. AKS Version Upgrades

### 6.1 Upgrade Path

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ AKS 1.28    │────▶│ AKS 1.29    │────▶│ AKS 1.30    │
│ EOL 2024-11 │     │ EOL 2025-03 │     │ EOL 2025-07 │
└─────────────┘     └─────────────┘     └─────────────┘
  API removals:       API removals:       API removals:
  flowcontrol.v1beta2 flowcontrol.v1beta3 none announced
```

### 6.2 Pre-Upgrade Checks

```bash
# Check available versions
az aks get-upgrades --resource-group "rg-genai-copilot-prod-eastus" \
  --name "aks-genai-copilot-prod" --output table

# Scan for deprecated APIs
kubectl krew install deprecations
kubectl deprecations --k8s-version=v1.29.0

# Check PodDisruptionBudgets
kubectl get pdb -A -o json | jq '.items[] | {
  namespace: .metadata.namespace, name: .metadata.name,
  minAvailable: .spec.minAvailable, maxUnavailable: .spec.maxUnavailable}'
```

### 6.3 Node Pool Surge Upgrade

```bash
# Configure 33% surge capacity
az aks nodepool update --resource-group "rg-genai-copilot-prod-eastus" \
  --cluster-name "aks-genai-copilot-prod" --name "system" --max-surge "33%"
az aks nodepool update --resource-group "rg-genai-copilot-prod-eastus" \
  --cluster-name "aks-genai-copilot-prod" --name "userpool" --max-surge "33%"

# Upgrade control plane first
az aks upgrade --resource-group "rg-genai-copilot-prod-eastus" \
  --name "aks-genai-copilot-prod" --kubernetes-version "1.29.4" \
  --control-plane-only --yes

# Upgrade node pools sequentially
az aks nodepool upgrade --resource-group "rg-genai-copilot-prod-eastus" \
  --cluster-name "aks-genai-copilot-prod" --name "system" \
  --kubernetes-version "1.29.4" --yes
az aks nodepool upgrade --resource-group "rg-genai-copilot-prod-eastus" \
  --cluster-name "aks-genai-copilot-prod" --name "userpool" \
  --kubernetes-version "1.29.4" --yes
```

### 6.4 Cordon/Drain (Manual Fallback)

```bash
kubectl cordon aks-userpool-12345678-vmss000002
kubectl drain aks-userpool-12345678-vmss000002 \
  --ignore-daemonsets --delete-emptydir-data --grace-period=120 --timeout=300s
# After upgrade:
kubectl uncordon aks-userpool-12345678-vmss000002
```

### 6.5 Validation

| Check | Command | Expected |
|-------|---------|----------|
| Control plane | `az aks show --query kubernetesVersion` | "1.29.4" |
| Nodes ready | `kubectl get nodes` | All STATUS = Ready |
| Pods running | `kubectl get pods -A --field-selector status.phase!=Running` | No results |
| Ingress | `curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health` | 200 |

---

## 7. Python Runtime Upgrades

### 7.1 Python 3.11 to 3.12 Impact

| Area | Impact | Action |
|------|--------|--------|
| **Performance** | 5-15% speed improvement | Benchmark before/after |
| **typing** | New `type` statement, `TypeVar` defaults | Update type hints (optional) |
| **asyncio** | `TaskGroup` improvements | Review async code |
| **distutils** | Removed entirely | Replace with `setuptools` |
| **imp** module | Removed | Replace with `importlib` |

### 7.2 Testing & Docker Update

```bash
# Dependency compatibility testing
python3.12 -m venv .venv-py312 && source .venv-py312/bin/activate
pip install -r requirements.txt 2>&1 | tee py312-install.log
grep -i "error\|failed\|incompatible" py312-install.log
pytest tests/ -v --tb=short --junitxml=py312-test-results.xml
python -W error::DeprecationWarning -m pytest tests/ 2>&1 | head -50
```

```dockerfile
# Updated Dockerfile — Python 3.12
FROM python:3.12-slim-bookworm AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Test Type | Python 3.11 | Python 3.12 | Status |
|-----------|-------------|-------------|--------|
| Unit tests (500+) | Pass | Pass | Ready |
| Integration tests (150+) | Pass | Pass | Ready |
| Async tests | Pass | Verify `TaskGroup` | Review |
| C extension modules | Pass | Verify ABI | Test |
| Performance benchmark | Baseline | +5-15% expected | Measure |

---

## 8. Database Schema Evolution

Cosmos DB is **schemaless**, but the application enforces a logical schema via `schemaVersion` fields.

```json
{
  "id": "doc-001", "partitionKey": "finance", "schemaVersion": 3,
  "content": "...",
  "metadata": { "title": "Q3 Report", "department": "finance", "effectiveDate": "2024-07-01" }
}
```

### 8.1 Migration Script

```python
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

SCHEMA_TRANSFORMS = {
    (2, 3): lambda doc: {
        **doc, "schemaVersion": 3,
        "metadata": {
            **doc["metadata"],
            "tags": doc["metadata"].get("tags", "").split(",")
                    if isinstance(doc["metadata"].get("tags"), str)
                    else doc["metadata"].get("tags", []),
            "lastMigrated": "2024-12-01T00:00:00Z",
        },
    },
}

def migrate_container(container_name: str, from_v: int, to_v: int):
    credential = DefaultAzureCredential()
    client = CosmosClient(
        "https://cosmos-genai-copilot-prod.documents.azure.com:443/", credential)
    container = client.get_database_client("genai-copilot-db").get_container_client(container_name)
    transform = SCHEMA_TRANSFORMS[(from_v, to_v)]
    query = f"SELECT * FROM c WHERE c.schemaVersion = {from_v}"
    migrated, failed = 0, 0
    for item in container.query_items(query=query, enable_cross_partition_query=True):
        try:
            container.upsert_item(transform(item))
            migrated += 1
        except Exception as e:
            failed += 1
    return {"migrated": migrated, "failed": failed}
```

### 8.2 Container Migration Plan

| Container | Current | Target | Doc Count | Est. Time |
|-----------|---------|--------|-----------|-----------|
| **documents** | v2 | v3 | ~2M | 4-6 hours |
| **conversations** | v2 | v3 | ~500K | 1-2 hours |
| **feedback** | v1 | v2 | ~100K | 30 min |
| **audit-events** | v2 | v2 | ~10M | None |
| **config** | v2 | v3 | ~100 | < 1 min |
| **user-profiles** | v1 | v2 | ~10K | < 5 min |

---

## 9. Search Index Schema Migration

### 9.1 Change Type Matrix

| Change Type | Downtime | Reindex | Strategy |
|-------------|----------|---------|----------|
| **Add field** | No | No (new docs) | Online add |
| **Remove field** | No | Optional | Stop writing, ignore |
| **Change analyzer** | Yes | Yes | Rebuild index |
| **Change vector dims** | Yes | Yes | New index + cutover |
| **Add semantic config** | No | No | Online add |
| **Change field type** | Yes | Yes | New index + cutover |

### 9.2 Online Field Addition

```bash
az search index update --service-name "srch-genai-copilot-prod" \
  --resource-group "rg-genai-copilot-prod-eastus" --name "documents-v2" \
  --fields '[{"name":"classificationLevel","type":"Edm.String","filterable":true,"facetable":true}]'
```

### 9.3 Full Reindex Strategy

```python
def create_v3_index(index_client: SearchIndexClient):
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String,
                        analyzer_name="en.microsoft"),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="department", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SimpleField(name="classificationLevel", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SearchField(name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True, vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile"),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[VectorSearchProfile(name="vector-profile",
            algorithm_configuration_name="hnsw-config")])
    index = SearchIndex(name="documents-v3", fields=fields,
        vector_search=vector_search,
        semantic_search=SemanticSearch(configurations=[SemanticConfiguration(
            name="default", prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                title_field=SemanticField(field_name="title")))]))
    index_client.create_or_update_index(index)
```

**Cutover sequence:** Create index-v3 --> reindex --> validate doc counts --> run relevance eval --> update config `INDEX_NAME=documents-v3` --> rolling restart --> monitor 24h --> delete v2 after 7-day hold.

---

## 10. Breaking Change Handling

### 10.1 Detection & Triage

```
┌──────────────────────────────────────────────────────────┐
│              BREAKING CHANGE DETECTION FLOW               │
├──────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │ Dependabot / │    │ Azure Update │    │ Manual     │ │
│  │ Renovate PR  │    │ Notification │    │ Discovery  │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬─────┘ │
│         └───────────────────┼───────────────────┘       │
│                   ┌─────────▼─────────┐                 │
│                   │ Impact Assessment │                 │
│                   └─────────┬─────────┘                 │
│              ┌──────────────┼──────────────┐            │
│        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐      │
│        │ Low       │ │ Medium    │ │ High      │      │
│        │ Standard  │ │ CAB       │ │ CAB + VP  │      │
│        │ change    │ │ review    │ │ approval  │      │
│        └───────────┘ └───────────┘ └───────────┘      │
└──────────────────────────────────────────────────────────┘
```

### 10.2 Impact Assessment

| Dimension | Low (1) | Medium (2) | High (3) |
|-----------|---------|------------|----------|
| **Users affected** | < 10% | 10-50% | > 50% |
| **Downtime** | None | < 1 hour | > 1 hour |
| **Data migration** | None | Automated | Manual steps |
| **Rollback** | Instant | < 15 min | > 15 min or impossible |
| **API contract** | No change | Additive only | Breaking |
| **Dependencies** | None | 1-2 services | 3+ services |

**Risk Score** = Sum of dimensions. **Low**: 6-9 | **Medium**: 10-13 | **High**: 14-18

### 10.3 Communication Template

```
Subject: [BREAKING CHANGE] {Component} — {Short Description}
Severity: {Low | Medium | High}
Affected Components: {list}
Target Date: {YYYY-MM-DD}

## What is changing?       → {1-2 sentence description}
## Why?                    → {Business/technical justification}
## Impact                  → Services: {list}, Downtime: {duration}
## Migration steps         → 1. ... 2. ... 3. ...
## Rollback plan           → {1-2 sentences}
## Timeline                → Staging: {date}, Prod: {date}, Sunset: {date}
## Contact                 → #platform-upgrades / platform-team@company.com
```

---

## 11. Deprecated API Handling

### 11.1 Sunset Timeline

| API / Feature | Deprecation | Sunset | Replacement | Action |
|---------------|------------|--------|-------------|--------|
| **GPT-4 (0613)** | 2024-06 | 2024-10 | GPT-4o | Migrate deployment |
| **text-embedding-ada-002** | 2024-03 | 2025-03 | text-embedding-3-large | Re-embed index |
| **AI Search API 2023-07-01** | 2024-01 | 2024-07 | 2024-05-01-preview | Update SDK |
| **Cosmos DB SDK v3** | 2023-06 | 2024-06 | SDK v4 | Update package |
| **AKS 1.27** | 2024-07 | 2024-10 | AKS 1.28+ | Upgrade cluster |
| **Python 3.10** | 2024-10 | 2025-04 | Python 3.12 | Update runtime |

### 11.2 Monitoring Commands

```bash
# Model deprecation status
az cognitiveservices account deployment list \
  --name "oai-genai-copilot-prod-eus" \
  --resource-group "rg-genai-copilot-prod-eastus" --output table \
  --query "[].{Name:name, Model:properties.model.name, Version:properties.model.version}"

# AKS version support
az aks get-versions --location "eastus" --output table

# K8s deprecated API usage
kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis
```

### 11.3 Client Notification Process

| Phase | Timeline | Action | Audience |
|-------|----------|--------|----------|
| **Announce** | Sunset - 6 months | Blog post, email, header | All consumers |
| **Warn** | Sunset - 3 months | Deprecation warnings in responses | Active consumers |
| **Final Notice** | Sunset - 1 month | Direct email | Active consumers |
| **Grace Period** | Sunset - 1 week | Rate-limited access | Remaining consumers |
| **Sunset** | Sunset date | API returns 410 Gone | N/A |

```python
DEPRECATED_ENDPOINTS = {
    "/api/v1/search": {"sunset": "2025-03-01", "replacement": "/api/v2/search"},
}

@app.middleware("http")
async def add_deprecation_headers(request, call_next):
    response = await call_next(request)
    if request.url.path in DEPRECATED_ENDPOINTS:
        info = DEPRECATED_ENDPOINTS[request.url.path]
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = info["sunset"]
        response.headers["Link"] = f'<{info["replacement"]}>; rel="successor-version"'
    return response
```

---

## 12. Rollback Procedures

### 12.1 Rollback Matrix by Upgrade Type

| Upgrade Type | Rollback Method | RTO | Data Loss Risk | Complexity |
|--------------|----------------|-----|----------------|------------|
| **Model version** | Config switch to old deployment | < 5 min | None | Low |
| **Embedding model** | Switch index alias to v(N-1) | < 5 min | None (old index retained) | Low |
| **Azure SDK** | Revert `requirements.txt`, redeploy | < 15 min | None | Low |
| **Terraform provider** | State restore + re-apply | 30-60 min | Possible state drift | Medium |
| **AKS version** | **Not supported** (forward-only) | N/A | N/A | Cannot rollback |
| **Python runtime** | Redeploy old Docker image | < 15 min | None | Low |
| **Cosmos DB schema** | Reverse migration script | 1-4 hours | Possible for new fields | Medium |
| **Search index** | Switch to old index (retained) | < 5 min | None | Low |
| **API version** | Revert code, redeploy | < 15 min | None | Low |

### 12.2 Emergency Rollback Playbook

```bash
# 1. Model rollback
az appconfig kv set --name "appconfig-genai-copilot-prod" \
  --key "OpenAI:DeploymentName" --value "gpt-4o-2024-05-13" \
  --label "production" --yes

# 2. Application rollback (previous image)
kubectl set image deployment/rag-api \
  rag-api=acr-genai-copilot.azurecr.io/rag-api:v2.3.1-rollback -n genai-copilot
kubectl rollout status deployment/rag-api -n genai-copilot --timeout=300s

# 3. Terraform state rollback
cp terraform-state-backup-YYYYMMDD.json terraform.tfstate
terraform state push terraform.tfstate

# 4. Verify
kubectl get pods -n genai-copilot
curl -s https://api.example.com/health | jq .
```

### 12.3 AKS Forward-Only Mitigation

```
┌────────────────────────────────────────────────────┐
│         AKS FORWARD-ONLY MITIGATION                │
├────────────────────────────────────────────────────┤
│  1. Always test in staging cluster first           │
│  2. Upgrade control plane before node pools        │
│  3. Upgrade one node pool at a time                │
│  4. If critical failure:                           │
│     ┌──────────┐   ┌──────────────┐   ┌──────────┐│
│     │ Failure   │──▶│ New cluster  │──▶│ Velero   ││
│     │ detected  │   │ provisioned  │   │ restore  ││
│     └──────────┘   └──────────────┘   └────┬─────┘│
│                                      ┌─────▼─────┐│
│                                      │DNS cutover ││
│                                      └───────────┘│
│  Estimated RTO: 2-4 hours                          │
└────────────────────────────────────────────────────┘
```

---

## 13. Post-Upgrade Validation Checklist

### 13.1 Immediate Validation (T+0 to T+30 min)

| # | Check | Method | Pass Criteria |
|---|-------|--------|---------------|
| 1 | **Health endpoints** | `curl /health` | HTTP 200 |
| 2 | **Pod readiness** | `kubectl get pods` | All Running, 0 restarts |
| 3 | **Log errors** | Log Analytics query | No new ERROR patterns |
| 4 | **Latency P95** | App Insights | <= 120% of baseline |
| 5 | **Error rate** | App Insights | <= 1% |
| 6 | **Auth flow** | Test login + API call | Token obtained, 200 |
| 7 | **Search** | Test query | Results count > 0 |
| 8 | **LLM response** | Test question | Non-empty, grounded |

### 13.2 Extended Validation (T+30 min to T+24 hr)

| # | Check | Method | Pass Criteria |
|---|-------|--------|---------------|
| 1 | **Throughput** | Load test (50% prod) | RPS >= 80% baseline |
| 2 | **Memory** stable | Grafana | No upward trend |
| 3 | **Cache hit rate** | Redis metrics | >= 60% after warm-up |
| 4 | **Evaluation scores** | Golden dataset eval | Groundedness >= 85% |
| 5 | **Cosmos DB RU** | Azure Monitor | <= 110% of baseline |
| 6 | **Audit logging** | Query audit container | New entries appearing |

### 13.3 Validation Script

```bash
#!/bin/bash
set -euo pipefail
API="https://api.genai-copilot.example.com"; NS="genai-copilot"
echo "=== Post-Upgrade Validation ==="
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API/health")
[ "$HTTP" -eq 200 ] && echo "PASS: Health=$HTTP" || { echo "FAIL"; exit 1; }
NR=$(kubectl get pods -n "$NS" --no-headers | grep -cv "Running" || true)
[ "$NR" -eq 0 ] && echo "PASS: All pods running" || { echo "FAIL: $NR not ready"; exit 1; }
R=$(curl -s -X POST "$API/api/v1/search" -H "Content-Type: application/json" \
  -d '{"query":"validation","top":3}')
[ "$(echo $R | jq '.results|length')" -gt 0 ] && echo "PASS: Search OK" || { echo "FAIL"; exit 1; }
L=$(curl -s -X POST "$API/api/v1/query" -H "Content-Type: application/json" \
  -d '{"question":"What is the leave policy?"}')
[ "$(echo $L | jq '.answer|length')" -gt 10 ] && echo "PASS: LLM OK" || { echo "FAIL"; exit 1; }
echo "=== Validation Complete ==="
```

---

## 14. Version Compatibility Matrix

### 14.1 Platform Component Versions

| Component | Current | Target | Dependencies | Risk | Priority |
|-----------|---------|--------|--------------|------|----------|
| **GPT-4o** | 2024-05-13 | 2024-08-06 | openai >= 1.35 | Low | Medium |
| **GPT-4o-mini** | 2024-07-18 | 2024-07-18 | openai >= 1.35 | N/A | N/A |
| **text-embedding-3-large** | v1 | v1 | azure-search >= 11.4 | N/A | N/A |
| **azure-search-documents** | 11.4.0 | 11.6.0 | Python >= 3.8 | Low | Medium |
| **azure-cosmos** | 4.5.1 | 4.7.0 | Python >= 3.8 | Low | Low |
| **azure-identity** | 1.15.0 | 1.17.0 | msal >= 1.28 | Low | Medium |
| **openai** | 1.30.0 | 1.40.0 | httpx >= 0.25 | Medium | High |
| **AKS** | 1.28.9 | 1.29.4 | Helm charts | Medium | High |
| **Python** | 3.11.7 | 3.12.3 | All packages | Medium | Medium |
| **Terraform azurerm** | 3.85.0 | 4.0.0 | Terraform >= 1.7 | High | Low |
| **Docker image** | python:3.11-slim | python:3.12-slim | C extensions | Low | Medium |
| **Helm** | 3.13.0 | 3.14.0 | kubectl | Low | Low |
| **cert-manager** | 1.13.0 | 1.14.0 | K8s >= 1.25 | Low | Low |
| **ingress-nginx** | 4.8.0 | 4.10.0 | K8s >= 1.25 | Low | Medium |

### 14.2 Recommended Upgrade Order

| Order | Component | Reason |
|-------|-----------|--------|
| 1 | **Python 3.12** | Foundation — all SDK packages depend on runtime |
| 2 | **Azure SDK packages** | Required for new API features |
| 3 | **openai SDK** | Required for new model features |
| 4 | **Docker base image** | Must match Python version |
| 5 | **AKS** | Infrastructure must support new images |
| 6 | **Helm charts** | Must be compatible with new AKS version |
| 7 | **Terraform provider** | IaC alignment (non-blocking) |
| 8 | **Model version** | Requires SDK compatibility first |
| 9 | **Embedding model** | Highest risk — do last |

---

## 15. Upgrade Scheduling & Governance

### 15.1 Maintenance Windows

| Window Type | Schedule | Duration | Scope | Approval |
|-------------|----------|----------|-------|----------|
| **Standard** | Tuesday 02:00-06:00 UTC | 4 hours | Non-breaking changes | Team Lead |
| **Extended** | Saturday 00:00-08:00 UTC | 8 hours | Breaking changes, reindex | CAB |
| **Emergency** | Any time | As needed | Critical security patches | VP Eng + CAB |

### 15.2 CAB Approval Flow

```
Change Request (T-10) ──▶ Technical Review (T-7) ──▶ CAB Meeting (T-5)
                                                         │
                                                    ┌────┴────┐
                                               ┌────▼──┐  ┌──▼────┐
                                               │  OK   │  │Reject │──▶ Rework
                                               └───┬───┘  └───────┘
                                    Schedule (T-2) ──▶ Execute ──▶ Post-Report (T+1)
```

### 15.3 Quarterly Planning

| Quarter | Focus Area | Key Upgrades | Risk |
|---------|-----------|-------------|------|
| **Q1** | Security patches, SDK updates | azure-identity, cert-manager | Low |
| **Q2** | Runtime & infrastructure | Python 3.12, AKS version bump | Medium |
| **Q3** | Model updates, index optimization | GPT-4o version, reindex | Medium |
| **Q4** | Major versions, Terraform | azurerm 4.0, annual review | High |

### 15.4 Freeze Periods

| Period | Dates | Reason |
|--------|-------|--------|
| **Year-end** | Dec 15 - Jan 5 | Holiday season, reduced staffing |
| **Fiscal close** | Last 5 business days/quarter | Financial reporting |
| **Major audit** | As scheduled | External audit prep |
| **Peak usage** | Customer-specific | High-traffic periods |

---

## Cross-References

- [INFRA-DEVOPS-DEPLOYMENT.md](./INFRA-DEVOPS-DEPLOYMENT.md) — Infrastructure and deployment pipelines
- [OPERATIONS-GUIDE.md](./OPERATIONS-GUIDE.md) — Day-to-day operational procedures
- [FINOPS-COST-MANAGEMENT.md](./FINOPS-COST-MANAGEMENT.md) — Cost impact of upgrades
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Test suites for validation
- [SECURITY-COMPLIANCE.md](../security/SECURITY-COMPLIANCE.md) — Security review requirements
- [TECH-STACK-SERVICES.md](../reference/TECH-STACK-SERVICES.md) — Service inventory
- [ARCHITECTURE-GUIDE.md](../architecture/ARCHITECTURE-GUIDE.md) — System architecture context

---

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | Migration & Upgrade Guide |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Approved By** | Chief Architect, SRE Lead |
| **Framework Alignment** | CMMI Level 3, ISO/IEC 42001, NIST AI RMF |
