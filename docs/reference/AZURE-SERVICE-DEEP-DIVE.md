# Azure Service Deep Dive — Enterprise RAG Platform

> Per-service operational guide for all 29 Azure services: architecture role, SKU selection, planning phases, challenges, FinOps, DR, testing, and monitoring.

---

## Table of Contents

1. [AI Services](#1-ai-services)
2. [Compute Services](#2-compute-services)
3. [Data Services](#3-data-services)
4. [Networking Services](#4-networking-services)
5. [Security Services](#5-security-services)
6. [Monitoring Services](#6-monitoring-services)
7. [Governance Services](#7-governance-services)

---

## 1. AI Services

### 1.1 Azure OpenAI Service

**Purpose & Architecture Role:**
Central LLM provider for the RAG pipeline. Powers query generation (GPT-4o), query rewriting (GPT-4o-mini), and text embeddings (text-embedding-3-large). All LLM interactions are routed through this service.

**SKU Selection:**
| SKU | Use Case | Cost Model |
|-----|----------|------------|
| Standard (S0) | Dev/Staging | Pay-per-token ($0.005/1K input, $0.015/1K output for GPT-4o) |
| Provisioned Throughput | Production (future) | Reserved PTU for guaranteed latency |

**Dos & Don'ts:**
- DO: Use model routing (GPT-4o for RAG, GPT-4o-mini for simple tasks)
- DO: Set token budgets per user/session/tenant
- DO: Use managed identity for authentication
- DON'T: Use high temperature for factual retrieval (use 0.1)
- DON'T: Send PII to the model without masking
- DON'T: Exceed quota without monitoring — request increases proactively

**Planning Phases (Crawl → Walk → Run):**
- **Crawl:** Single model (GPT-4o), basic prompts, manual evaluation
- **Walk:** Model routing, optimized prompts, automated evaluation pipeline
- **Run:** Provisioned throughput, fine-tuning exploration, multi-model orchestration

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Rate limiting (429) | Implement retry with exponential backoff, request quota increase |
| High latency spikes | Cache frequent queries, use streaming for long responses |
| Hallucination | Low temperature, grounding prompts, post-generation evaluation |
| Token budget exhaustion | Per-user/session limits, model routing for cost optimization |
| Model deprecation | Abstract model selection, test new models before migration |

**Limitations & Workarounds:**
- Max token limit (128K context for GPT-4o): Context compression, top-K retrieval limits
- No fine-tuning in all regions: Use prompt engineering as primary optimization
- Regional availability: Deploy to supported region, use failover for DR

**FinOps:**
- Monthly cost estimate: $2,500–$4,000 (production)
- Optimization: Model routing saves 45%, caching saves 26–30%
- Monitor: Token consumption per tenant via App Insights custom metrics
- Budget alert at 80% of monthly allocation

**Backup & DR:**
- No data stored in OpenAI service (stateless)
- DR: Deploy to secondary region with same model configuration
- RPO: N/A (stateless), RTO: 1 hour (redeploy configuration)

**Testing Scenarios:**
- Unit: Mock API responses, test prompt construction
- Integration: End-to-end query with real model
- Performance: Measure P95 latency under load
- Security: Prompt injection payloads, PII leak detection

**Quality & Monitoring:**
- Groundedness score ≥0.80 (LLM-as-judge)
- Hallucination rate ≤0.10
- P95 latency ≤2000ms for generation
- Token efficiency: tokens per query trending downward

---

### 1.2 Azure AI Search

**Purpose & Architecture Role:**
Hybrid search engine combining vector search (semantic understanding), BM25 (keyword matching), and semantic ranking (reordering). Stores document chunks with embeddings, metadata, and ACL tags.

**SKU Selection:**
| SKU | Replicas | Partitions | Use Case |
|-----|----------|------------|----------|
| Basic | 1 | 1 | Dev |
| Standard S1 | 2 | 1 | Staging |
| Standard S2 | 3 | 2 | Production |

**Dos & Don'ts:**
- DO: Use hybrid search (vector + BM25 + semantic)
- DO: Include ACL fields in every document for security filtering
- DO: Use composite indexes for filtered queries
- DO: Configure scoring profiles for recency boosting
- DON'T: Skip semantic ranker configuration
- DON'T: Use single vector search without BM25 fallback
- DON'T: Index PII fields — mask before indexing

**Planning Phases:**
- **Crawl:** BM25 keyword search, manual relevance testing
- **Walk:** Hybrid search, semantic ranker, automated relevance evaluation
- **Run:** Custom scoring profiles, HNSW tuning, blue-green indexing, multi-index architecture

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Slow indexing for large batches | Parallel batch indexing, incremental updates |
| Relevance degradation over time | Regular golden dataset evaluation, scoring profile tuning |
| ACL filter complexity | Pre-build filter strings from JWT, cache group lookups |
| Index size growth | Document lifecycle management, archive old content |
| Synonym handling | Synonym maps for domain-specific terms |

**Limitations & Workarounds:**
- Max 1000 fields per index: Use metadata field with JSON for overflow
- Max 32 dimensions for filterable fields: Flatten critical dimensions only
- Semantic ranker adds 150ms: Accept for quality, bypass for speed-critical queries
- No native backup: Export index to blob storage via custom script

**FinOps:**
- Monthly cost: S2 with 3 replicas ≈ $2,200/month
- Optimization: Right-size replicas per query volume, use Basic for dev
- Monitor: Search units utilization, query throttling rate
- Scale triggers: >80% utilization, >100ms average latency

**Backup & DR:**
- No native backup — implement custom export/import via REST API
- Blue-green indexing for zero-downtime updates
- DR: Rebuild index from Data Lake source documents (2–4 hours for full reindex)
- RPO: 1 hour (incremental), RTO: 4 hours (full rebuild)

**Vector DB Scenarios (AI Search Specific):**

**HNSW Tuning:**
| Parameter | Value | Impact |
|-----------|-------|--------|
| m (connections) | 4 | Lower memory, good for <5M vectors |
| efConstruction | 400 | High quality index build (one-time cost) |
| efSearch | 500 | High quality search (runtime cost) |
| metric | cosine | Standard for text embeddings |

**Index Design:**
```json
{
  "name": "documents",
  "fields": [
    {"name": "docId", "type": "Edm.String", "key": true},
    {"name": "chunkId", "type": "Edm.String"},
    {"name": "content", "type": "Edm.String", "searchable": true},
    {"name": "chunkVector", "type": "Collection(Edm.Single)", "dimensions": 3072,
     "vectorSearchProfile": "hnsw-profile"},
    {"name": "titleVector", "type": "Collection(Edm.Single)", "dimensions": 3072},
    {"name": "department", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "effectiveDate", "type": "Edm.DateTimeOffset", "filterable": true, "sortable": true},
    {"name": "aclGroups", "type": "Collection(Edm.String)", "filterable": true},
    {"name": "piiClass", "type": "Edm.String", "filterable": true},
    {"name": "source", "type": "Edm.String"},
    {"name": "version", "type": "Edm.String"},
    {"name": "region", "type": "Edm.String", "filterable": true},
    {"name": "metadata", "type": "Edm.String"},
    {"name": "chunkIndex", "type": "Edm.Int32"}
  ]
}
```

**Index Backup Strategy:**
1. Scheduled export to Data Lake (nightly)
2. Export format: JSON documents with embeddings
3. Restore: Batch import from Data Lake
4. Verification: Document count + sample search validation

**Index Migration:**
1. Create new index with updated schema
2. Batch copy documents from old to new index
3. Validate document count and search quality
4. Swap index alias
5. Delete old index after verification period (7 days)

**Quality Monitoring:**
- Precision@10 tracked weekly against golden dataset
- Search latency P95 alert at >500ms
- Zero-result query rate (target <5%)
- Synonym coverage for domain terms

**Costing:**
- Per search unit: $0.34/hour
- Query cost: negligible per query (included in SU)
- Storage cost: included in SU (up to partition limit)
- Optimization: Right-size replicas, use Basic for non-production

---

### 1.3 Azure Document Intelligence

**Purpose & Architecture Role:**
Document parsing service for OCR, layout extraction, and structured data extraction. Processes uploaded documents before chunking and embedding.

**SKU Selection:**
| SKU | Pricing | Use Case |
|-----|---------|----------|
| Free (F0) | 500 pages/month | Development |
| Standard (S0) | $0.01/page (read), $0.01/page (layout) | Staging/Production |

**Dos & Don'ts:**
- DO: Use prebuilt-read for general OCR, layout for structured documents
- DO: Set confidence thresholds (reject <0.70)
- DO: Handle multi-page documents with pagination
- DON'T: Process encrypted PDFs (detect and reject)
- DON'T: Skip error handling for OCR failures
- DON'T: Process files >100MB without chunking

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Scanned PDF quality varies | Confidence threshold, manual review queue |
| Multi-column layouts | Layout model with reading-order detection |
| Large files (>100 pages) | Fan-out processing: 20-page batches in parallel |
| Handwritten text | Read model with handwriting support, lower confidence threshold |
| Non-English documents | Multi-language support, specify language hint |

**FinOps:**
- Cost: $0.01/page, estimate 50K pages/month = $500
- Optimization: Skip OCR for native digital PDFs (text extraction only)
- Monitor: Pages processed per day, error rate, cost per document

---

### 1.4 Azure Content Safety

**Purpose & Architecture Role:**
Content moderation for both user input and LLM output. Detects hate, sexual, violence, and self-harm content. Also provides prompt injection detection.

**SKU Selection:**
| SKU | Pricing | Use Case |
|-----|---------|----------|
| Standard (S0) | $1/1K text records | All environments |

**Dos & Don'ts:**
- DO: Apply to both input and output
- DO: Configure severity thresholds per category
- DO: Maintain custom blocklists for domain terms
- DON'T: Rely solely on Content Safety (layer with Presidio for PII)
- DON'T: Set thresholds too low (excessive false positives)

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| False positives on medical terms | Custom allow-list for domain vocabulary |
| Prompt injection evolving | Regular blocklist updates, pattern monitoring |
| Latency overhead | Async processing where possible |

---

## 2. Compute Services

### 2.1 Azure Kubernetes Service (AKS)

**Purpose & Architecture Role:**
Container orchestration for application workloads. Hosts backend API services, monitoring agents, and supporting infrastructure.

**SKU Selection:**
| Node Pool | VM SKU | Count | Purpose |
|-----------|--------|-------|---------|
| System | Standard_D4s_v3 | 3 | System pods, monitoring |
| User | Standard_D8s_v3 | 3–10 | Application workloads |
| Spot (optional) | Standard_D4s_v3 | 0–5 | Non-critical batch jobs |

**Dos & Don'ts:**
- DO: Use Workload Identity for pod-to-service auth
- DO: Enable cluster autoscaler (min 3, max 10)
- DO: Use network policies for pod isolation
- DO: Regular node image upgrades
- DON'T: Use public API server endpoint
- DON'T: Store secrets in pod environment variables
- DON'T: Skip resource requests/limits on pods

**Planning Phases:**
- **Crawl:** Single node pool, manual scaling, basic monitoring
- **Walk:** Multi-pool (system + user), HPA, KEDA for event-driven scaling
- **Run:** Spot nodes, pod disruption budgets, advanced network policies, GitOps

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Pod scheduling delays | Pre-scale before peak, resource requests/limits |
| Node image vulnerabilities | Automated node image upgrade, Defender for Containers |
| IP address exhaustion | Plan CIDR blocks carefully, use Azure CNI overlay |
| Ingress complexity | Application Gateway Ingress Controller (AGIC) |
| Secret management | Workload Identity + Key Vault CSI driver |

**FinOps:**
- Monthly cost: ~$2,000 (3 nodes Standard_D4s_v3) to $6,000 (10 nodes)
- Optimization: Spot nodes for batch (60–70% savings), reserved instances for base nodes (37%)
- Monitor: Node utilization, pod resource usage, autoscaler events

**Backup & DR:**
- AKS configuration: Terraform state in Azure Storage
- Application state: Stateless pods, state in Cosmos DB/Redis
- DR: Terraform apply to secondary region, DNS failover
- RPO: N/A (stateless), RTO: 1 hour

---

### 2.2 Azure Functions

**Purpose & Architecture Role:**
Serverless compute for the three pipeline functions: Pre-Retrieval (intent detection, query expansion), RAG Processor (search, LLM generation), and Ingestion (document parsing, chunking, embedding).

**SKU Selection:**
| Plan | Use Case | Scaling |
|------|----------|---------|
| Consumption | Dev | Auto-scale, cold start risk |
| Premium (EP1) | Staging | Always-ready instances (1) |
| Premium (EP2) | Production | Always-ready instances (2), burst to 20 |

**Dos & Don'ts:**
- DO: Use Premium plan for production (no cold starts)
- DO: Use Durable Functions for long-running ingestion
- DO: Initialize SDK clients once per instance (singleton pattern)
- DO: Use VNet integration with private endpoints
- DON'T: Put heavy logic in function triggers
- DON'T: Exceed execution timeout (default 5 min, max 60 min)
- DON'T: Use Consumption plan for latency-sensitive workloads

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Cold starts | Premium plan with always-ready instances |
| Timeout on large document ingestion | Durable Functions with checkpointing |
| Connection pooling | Singleton HTTP/SDK clients, connection reuse |
| VNet latency | Co-locate Functions in same region as dependencies |

**FinOps:**
- Monthly cost: EP1 ≈ $150, EP2 ≈ $300 (base), plus execution costs
- Optimization: Right-size plan per environment, Consumption for dev
- Monitor: Execution count, duration, failure rate, always-ready utilization

---

### 2.3 Azure Container Registry (ACR)

**Purpose & Architecture Role:**
Private container image registry for all application containers. Stores Docker images for AKS deployments.

**SKU Selection:**
| SKU | Use Case | Features |
|-----|----------|----------|
| Basic | Dev | 10 GB storage |
| Standard | Staging | 100 GB, webhooks |
| Premium | Production | Geo-replication, private endpoint, content trust |

**Dos & Don'ts:**
- DO: Enable vulnerability scanning
- DO: Use content trust (image signing)
- DO: Set retention policies (keep last 10 tags per repo)
- DO: Use private endpoint in production
- DON'T: Use public endpoint for production workloads
- DON'T: Store credentials in CI/CD (use managed identity)

---

## 3. Data Services

### 3.1 Azure Cosmos DB

**Purpose & Architecture Role:**
NoSQL database for operational data: conversations, sessions, evaluations, feedback, audit events, tenant configuration, and model metrics. Provides single-digit millisecond reads with partition-key-based tenant isolation.

**SKU Selection:**
| Tier | Use Case | RU/s |
|------|----------|------|
| Serverless | Dev | Pay-per-request |
| Autoscale | Staging/Production | 400–4000 RU/s (conversations), 400–1000 (evaluations) |

**Container Design:**

| Container | Partition Key | TTL | Max RU/s | Purpose |
|-----------|--------------|-----|----------|---------|
| conversations | /tenantId | 90 days | 4000 | Chat history |
| sessions | /tenantId | 24 hours | 2000 | Active sessions |
| evaluations | /tenantId | 365 days | 1000 | Quality metrics |
| feedback | /tenantId | 730 days | 1000 | User ratings |
| audit-events | /tenantId | 2555 days | 2000 | Compliance trail |
| tenant-config | /tenantId | None | 400 | Per-tenant settings |
| model-metrics | /modelId | 365 days | 1000 | Performance data |

**Dos & Don'ts:**
- DO: Use autoscale RU/s to handle burst without over-provisioning
- DO: Set TTL for data lifecycle management
- DO: Use composite indexes for common query patterns
- DO: Enable analytical store for reporting queries
- DON'T: Use cross-partition queries for transactional data
- DON'T: Store large binary data (use Storage Account instead)
- DON'T: Skip capacity planning — underscaled RU/s causes 429 errors

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Hot partition (busy tenant) | Monitor RU consumption per partition, right-size |
| Cross-partition query cost | Design queries around partition key, use analytical store |
| Data consistency | Use Session consistency for conversations, Eventual for analytics |
| Cost at scale | TTL-based expiration, tiered RU/s, serverless for dev |

**FinOps:**
- Monthly cost: ~$800 (autoscale, production workload)
- Optimization: TTL reduces storage cost, analytical store offloads reporting
- Monitor: RU consumption, throttled requests (429), storage size per container

**Backup & DR:**
- Continuous backup (PITR) with 30-day retention
- Periodic backup: 4-hour intervals, 2 copies
- DR: Restore to secondary region from continuous backup
- RPO: <1 hour (continuous), RTO: 2–4 hours

---

### 3.2 Azure Cache for Redis

**Purpose & Architecture Role:**
Three-tier caching layer: query cache (exact match), retrieval cache (search results), embedding cache (pre-computed vectors). Reduces latency and token consumption.

**SKU Selection:**
| SKU | Use Case | Memory |
|-----|----------|--------|
| Basic C0 | Dev | 250 MB |
| Standard C1 | Staging | 1 GB |
| Premium P1 | Production | 6 GB, clustering, VNet |

**Dos & Don'ts:**
- DO: Use cache-aside pattern with write-through for frequent updates
- DO: Set appropriate TTL per cache tier
- DO: Implement cache warming on deployment
- DO: Monitor hit ratio (target 40–60%)
- DON'T: Store session state without TTL
- DON'T: Use Redis as primary data store
- DON'T: Skip connection pooling

**Challenges & Solutions:**
| Challenge | Solution |
|-----------|----------|
| Cache stampede | Mutex/lock pattern for concurrent cache rebuilds |
| Memory pressure | LRU eviction policy, monitor memory usage |
| Connection limits | Connection pooling, reduce idle connections |
| Stale data | Event-driven invalidation + TTL safety net |

**FinOps:**
- Monthly cost: Premium P1 ≈ $400
- ROI: $1,200/month savings from reduced OpenAI calls
- Break-even: Month 1
- Monitor: Hit ratio, memory usage, connection count, evictions

---

### 3.3 Azure Storage (Data Lake Gen2)

**Purpose & Architecture Role:**
Hierarchical storage for document lifecycle: raw uploads, processed outputs, chunks, embeddings, evaluation datasets, and archived content.

**SKU Selection:**
| Tier | Use Case | Cost/GB |
|------|----------|---------|
| Hot | Active documents (90 days) | $0.018/GB |
| Cool | Archived (275 days) | $0.010/GB |
| Archive | Long-term compliance (2190 days) | $0.002/GB |

**Container Structure:**
```
raw/            → Uploaded documents (original)
processed/      → OCR/parsed output
chunks/         → Chunked text files
embeddings/     → Vector files
evaluation/     → Golden datasets, test results
backups/        → Index exports, configuration snapshots
```

**Dos & Don'ts:**
- DO: Enable hierarchical namespace (Data Lake Gen2)
- DO: Configure lifecycle management policies
- DO: Use RBAC per container
- DO: Enable soft delete and versioning
- DON'T: Use flat blob storage for structured data
- DON'T: Store PII in hot tier without encryption + access controls
- DON'T: Skip lifecycle policies (manual cleanup doesn't scale)

**FinOps:**
- Monthly cost: ~$200 (10 TB mixed tiers)
- Optimization: Auto-tier transition via lifecycle policies, compression
- Monitor: Storage capacity by tier, transaction costs, egress

---

## 4. Networking Services

### 4.1 Azure Virtual Network (VNet)

**Purpose & Architecture Role:**
Network isolation backbone. All services communicate over private network via VNet integration and private endpoints.

**Architecture:**
```
VNet: 10.0.0.0/16
├── AKS Subnet:      10.0.0.0/20   (4096 IPs for pods)
├── Functions Subnet: 10.0.16.0/24  (256 IPs)
├── PE Subnet:        10.0.17.0/24  (256 IPs for private endpoints)
├── Bastion Subnet:   10.0.18.0/26  (64 IPs)
└── AppGW Subnet:     10.0.19.0/24  (256 IPs)
```

**Dos & Don'ts:**
- DO: Plan CIDR blocks with growth in mind
- DO: Use NSGs on every subnet
- DO: Use private endpoints for all PaaS services
- DON'T: Use overlapping address spaces with on-premises
- DON'T: Expose services to public internet unnecessarily
- DON'T: Use /28 or smaller subnets (insufficient IPs)

### 4.2 Network Security Groups (NSGs)

**Purpose:** Firewall rules at subnet and NIC level.

**Key Rules:**
| Priority | Direction | Source | Destination | Port | Action |
|----------|-----------|--------|-------------|------|--------|
| 100 | Inbound | AppGW Subnet | AKS Subnet | 443 | Allow |
| 200 | Inbound | AKS Subnet | PE Subnet | 443 | Allow |
| 300 | Inbound | Functions Subnet | PE Subnet | 443 | Allow |
| 4096 | Inbound | Any | Any | Any | Deny |

### 4.3 Private Endpoints (8 total)

| Service | PE Subnet | Private DNS Zone |
|---------|-----------|-----------------|
| Azure OpenAI | 10.0.17.x | privatelink.openai.azure.com |
| Azure AI Search | 10.0.17.x | privatelink.search.windows.net |
| Cosmos DB | 10.0.17.x | privatelink.documents.azure.com |
| Storage Account | 10.0.17.x | privatelink.blob.core.windows.net |
| Key Vault | 10.0.17.x | privatelink.vaultcore.azure.net |
| Redis Cache | 10.0.17.x | privatelink.redis.cache.windows.net |
| ACR | 10.0.17.x | privatelink.azurecr.io |
| Document Intelligence | 10.0.17.x | privatelink.cognitiveservices.azure.com |

### 4.4 Application Gateway (WAF v2)

**Purpose:** Public entry point with WAF protection, SSL termination, and backend routing.

**SKU:** WAF v2 (autoscale 2–10 instances)

**Dos & Don'ts:**
- DO: Enable OWASP 3.2 core rule set
- DO: Use WAF Prevention mode in production
- DO: Configure custom rules for API-specific threats
- DON'T: Skip SSL policy configuration (enforce TLS 1.2+)
- DON'T: Use Detection mode in production

**FinOps:** ~$500/month (2 instances base) + $0.008/GB data processed

### 4.5 Azure Bastion

**Purpose:** Secure RDP/SSH access to VMs without public IPs.
**SKU:** Standard (supports file upload, session recording)
**Cost:** ~$140/month

### 4.6 Azure DDoS Protection

**Purpose:** Adaptive DDoS mitigation for public endpoints.
**SKU:** Standard ($2,944/month — covers up to 100 public IPs)
**Justification:** Cost of downtime far exceeds protection cost for enterprise platform.

### 4.7 Azure API Management (APIM)

**Purpose & Architecture Role:**
API gateway for all external traffic. Handles authentication, rate limiting, request transformation, analytics, and developer portal.

**SKU Selection:**
| SKU | Use Case | Cost |
|-----|----------|------|
| Developer | Dev | ~$50/month |
| Standard | Staging | ~$700/month |
| Premium | Production | ~$2,800/month (multi-region capable) |

**Dos & Don'ts:**
- DO: Validate JWT tokens at APIM level
- DO: Implement rate limiting per subscription
- DO: Use named values for configuration (not hardcoded)
- DO: Enable request/response logging
- DON'T: Pass API keys to clients (use subscription keys or OAuth)
- DON'T: Skip CORS configuration for web clients

---

## 5. Security Services

### 5.1 Azure Key Vault

**Purpose:** Centralized secrets, keys, and certificate management.

**SKU Selection:**
| SKU | Use Case | Key Type |
|-----|----------|----------|
| Standard | Dev/Staging | Software-protected keys |
| Premium | Production | HSM-backed keys |

**Stored Items:**
- Secrets: API keys, connection strings (12+ secrets)
- Keys: CMK for storage, Cosmos DB encryption
- Certificates: TLS certificates, client auth certs

**Rotation Policy:** 90-day rotation via Event Grid + Azure Function

**FinOps:** ~$10–$30/month (based on operations count)

### 5.2 Azure Entra ID (formerly Azure AD)

**Purpose:** Identity provider for user authentication and service authorization.

**SKU:** P2 (PIM, conditional access, identity protection)

**Key Configuration:**
- App registrations for each application
- Group-based RBAC (6 groups)
- Conditional Access: MFA required, compliant devices, location restrictions
- PIM for privileged access elevation
- Workload Identity for AKS pods

### 5.3 Azure Defender for Cloud

**Purpose:** Cloud security posture management and threat protection.

**Enabled Plans:**
| Plan | Coverage | Monthly Cost |
|------|----------|-------------|
| Defender for Containers | AKS | ~$7/vCore |
| Defender for Storage | Data Lake | ~$10/storage account |
| Defender for Key Vault | Key Vault | ~$0.02/10K operations |
| Defender for Cosmos DB | Cosmos DB | ~$1/100 RU/s |

**Security Score Target:** ≥90%

### 5.4 Azure Sentinel

**Purpose:** SIEM/SOAR for security analytics and automated incident response.

**Key Detections:**
- Brute force attempts (>5 failures in 10 min)
- Unusual query volume (>3x normal)
- PII exfiltration patterns
- Prompt injection attempts
- After-hours admin access
- Cross-tenant data access attempts

**Playbooks (Logic Apps):**
- Block user on confirmed threat
- Notify SOC on high-severity alert
- Create ServiceNow ticket on security incident
- Auto-remediate common issues (certificate renewal, key rotation)

**FinOps:** ~$500–$1,000/month (based on ingestion volume)

---

## 6. Monitoring Services

### 6.1 Azure Application Insights

**Purpose:** Application performance monitoring, distributed tracing, custom metrics.

**Key Features Used:**
- Auto-instrumentation for HTTP, database calls
- Custom metrics: groundedness, hallucination rate, cache hit ratio
- Distributed tracing with OpenTelemetry
- Availability tests (synthetic monitoring)
- Smart detection for anomalies

**Custom Metrics:**

| Metric | Type | Alert Threshold |
|--------|------|----------------|
| groundedness_score | Gauge | <0.75 |
| hallucination_rate | Gauge | >0.12 |
| cache_hit_ratio | Gauge | <0.30 |
| tokens_consumed | Counter | >150% daily avg |
| pii_detected | Counter | >0 in output |
| query_latency_p95 | Histogram | >5000ms |
| user_satisfaction | Gauge | <4.0 |

**Sampling:** 100% for errors, 20% for success (reduce cost)

**FinOps:** ~$200–$400/month

### 6.2 Azure Log Analytics

**Purpose:** Centralized log storage and Kusto query engine.

**Workspace Design:**
- Single workspace for all environments (dev/staging/prod)
- Data segregation via resource tags
- Saved queries shared across team

**Key Kusto Queries:**
```kusto
// Latency trend by hour
requests | where timestamp > ago(24h)
| summarize p95=percentile(duration, 95) by bin(timestamp, 1h)
| render timechart

// Error breakdown
requests | where success == false and timestamp > ago(24h)
| summarize count() by resultCode
| sort by count_ desc

// Token consumption by tenant
customMetrics | where name == "tokens_consumed" and timestamp > ago(24h)
| extend tenant = tostring(customDimensions.tenantId)
| summarize total=sum(value) by tenant
| sort by total desc
```

**Data Retention:** 90 days interactive, 730 days archive
**FinOps:** ~$250–$400/month

### 6.3 Azure Monitor

**Purpose:** Platform-level monitoring, alerting, and action groups.

**Alert Rules (12 total):**

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High P95 Latency | P95 > 5s for 5 min | Sev 2 | Page on-call |
| Error Rate Spike | >5% for 5 min | Sev 1 | Page on-call |
| Groundedness Drop | <0.75 for 1 hr | Sev 2 | Notify ML team |
| Token Budget Exceeded | >100% daily budget | Sev 2 | Notify FinOps |
| PII in Output | Any detection | Sev 0 | Block + page security |
| Cache Hit Ratio Low | <30% for 30 min | Sev 3 | Notify ops |
| AKS Node Pressure | CPU >90% for 10 min | Sev 2 | Scale alert |
| Cosmos DB Throttle | >10 429s in 5 min | Sev 2 | Scale RU/s |
| Certificate Expiry | <30 days | Sev 3 | Notify ops |
| Budget Threshold | >80% monthly | Sev 3 | Notify FinOps |
| Security Event | Sentinel trigger | Sev 1 | Page security |
| Function Failure | >5% failure rate | Sev 2 | Page on-call |

---

## 7. Governance Services

### 7.1 Azure Policy

**Purpose:** Enforce organizational compliance at resource level.

**Key Policies:**
| Policy | Effect | Scope |
|--------|--------|-------|
| Require HTTPS | Deny | All resources |
| Require encryption at rest | Deny | Storage, Cosmos DB |
| Deny public endpoints | Deny | All PaaS services |
| Enforce tagging | Deny | All resources |
| Restrict allowed SKUs | Deny | Compute resources |
| Require diagnostic settings | DeployIfNotExists | All resources |
| Deny unmanaged disks | Deny | Compute |

### 7.2 Azure Event Grid

**Purpose:** Event-driven architecture for decoupled service communication.

**Event Subscriptions:**
| Source | Event | Handler | Action |
|--------|-------|---------|--------|
| Storage Account | BlobCreated | Ingestion Function | Process new document |
| Key Vault | SecretNearExpiry | Rotation Function | Rotate secret |
| AI Search | IndexChanged | Cache Invalidation | Clear related cache |
| Cosmos DB | DocumentChanged | Notification Function | Audit trail |

### 7.3 Azure Data Factory

**Purpose:** Batch data ingestion from enterprise sources.

**Pipelines:**
| Pipeline | Source | Schedule | Purpose |
|----------|--------|----------|---------|
| SharePoint Sync | SharePoint Online | Daily 2 AM | HR, IT documents |
| File Share Sync | On-premises shares | Daily 3 AM | Engineering docs |
| Database Export | SQL Server | Weekly Sunday | Financial reports |

### 7.4 Microsoft Purview

**Purpose:** Data governance, catalog, and compliance.

**Features Used:**
- Data catalog for document lineage
- Sensitivity labels for PII classification
- Compliance reporting for GDPR/SOX audits
- Data map for understanding data landscape

---

## Cross-References

- [TECH-STACK-SERVICES.md](./TECH-STACK-SERVICES.md) — Service inventory with SKUs and costs
- [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) — Detailed cost analysis
- [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) — Security architecture
- [INTERVIEW-KNOWLEDGE-GUIDE.md](./INTERVIEW-KNOWLEDGE-GUIDE.md) — Service Q&A for interviews
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Service-level testing
- [EDGE-CASES-DATA-TYPES.md](./EDGE-CASES-DATA-TYPES.md) — Edge cases per service
