# Interview Knowledge Guide — Azure OpenAI Enterprise RAG Platform

> Comprehensive Q&A organized by Azure service, technical domain, and role for interview preparation and knowledge validation.

> **Note:** This guide extends the existing [Interview Guide](../../azurecloud/INTERVIEW_GUIDE.md) with service-level depth, scenario-based questions, and role-specific preparation.

---

## Table of Contents

1. [Per Azure Service Q&A](#1-per-azure-service-qa)
2. [Quality Validation Questions](#2-quality-validation-questions)
3. [Monitoring & Observability Questions](#3-monitoring--observability-questions)
4. [Testing & Deployment Questions](#4-testing--deployment-questions)
5. [Logging, Tracing & Visualization](#5-logging-tracing--visualization)
6. [Reporting & Costing Questions](#6-reporting--costing-questions)
7. [Architecture Decision Defense](#7-architecture-decision-defense)
8. [Scenario-Based Questions](#8-scenario-based-questions)
9. [Role-Specific Questions](#9-role-specific-questions)
10. [Whiteboard Exercise Guide](#10-whiteboard-exercise-guide)

---

## 1. Per Azure Service Q&A

### 1.1 Azure OpenAI Service

**Q: Why GPT-4o over GPT-4 Turbo for RAG?**
A: GPT-4o provides better multimodal capabilities, lower latency (~30% faster), and reduced cost per token. For RAG workloads, it offers equivalent groundedness scores (0.82–0.86) while processing at higher throughput. GPT-4o-mini handles simpler tasks (query rewriting, summarization) at ~60% lower cost.

**Q: How do you handle token budget management?**
A: Multi-level budget enforcement — Platform: 5M tokens/day, Per-tenant: variable by SLA, Per-user: 50K/day, Per-session: 10K/day. Budget tracking via App Insights custom metrics with alerts at 80% and 100% thresholds.

**Q: How do you prevent hallucinations?**
A: Four-layer approach: (1) Low temperature (0.1) constrains creativity, (2) System prompt enforces context-only answers with mandatory citations, (3) Post-generation groundedness scoring via LLM-as-judge, (4) Release gate blocks deployment if hallucination rate exceeds 10%.

**Q: What is model routing and why?**
A: Route by task complexity — GPT-4o (temp 0.1) for RAG generation requiring accuracy, GPT-4o-mini (temp 0.3) for query rewriting and summarization. This saves ~45% on AI service costs without quality degradation on routed tasks.

### 1.2 Azure AI Search

**Q: Why hybrid search over pure vector search?**
A: Hybrid (vector + BM25 + semantic ranking) delivers 40% better recall than vector-only. Vector captures semantic meaning (synonyms, paraphrases), BM25 captures exact keyword matches (policy numbers, codes). Semantic ranker reorders for final relevance.

**Q: Explain HNSW tuning parameters.**
A: `m=4` (connections per node) — lower memory, suitable for our index size. `efConstruction=400` — high quality index build, worth the one-time cost. `efSearch=500` — high quality search at runtime, balanced against latency budget of 200ms for search.

**Q: How do you handle index updates without downtime?**
A: Blue-green indexing — build new index alongside current, swap alias when ready. Incremental updates via change tracking on Data Lake. Full reindex scheduled nightly via cron job.

**Q: How do you enforce document-level security in search?**
A: Every chunk includes `aclGroups` field populated during ingestion. At query time, user's Entra ID groups are extracted from JWT and injected as OData filter: `aclGroups/any(g: search.in(g, 'group1,group2'))`. Documents without matching ACL are excluded before ranking.

**Q: What is your index schema design?**
A: 14-field schema: `docId`, `chunkId`, `content`, `chunkVector` (3072d), `titleVector` (3072d), `source`, `department`, `region`, `version`, `effectiveDate`, `piiClass`, `aclGroups`, `metadata`, `chunkIndex`. Composite index on `department + effectiveDate` for filtered queries.

### 1.3 Azure Document Intelligence

**Q: How do you handle scanned PDFs?**
A: Prebuilt-read model with OCR for scanned documents. Layout model for structured documents (tables, forms). Confidence threshold of 0.70 — below this, document is flagged for manual review. Multi-column layouts handled via reading-order detection.

**Q: What about encrypted PDFs?**
A: Detection at upload via file header analysis. If encrypted, return error with instructions to upload unencrypted version. No server-side decryption to avoid key management complexity.

**Q: How do you handle large documents (>100 pages)?**
A: Chunked processing — split into 20-page batches, process in parallel via Azure Functions fan-out. Results merged maintaining page order. Timeout set at 30 minutes per document with retry logic.

### 1.4 Azure Kubernetes Service (AKS)

**Q: Why AKS over Azure Container Apps?**
A: AKS provides fine-grained control over networking (CNI, network policies), scaling (KEDA, HPA), and pod-level security (Workload Identity, pod security policies). For an enterprise platform with strict security requirements and multi-tenant isolation, AKS's control plane is essential.

**Q: How do you handle AKS scaling?**
A: HPA for pod-level scaling (CPU >70%, memory >80%). Cluster autoscaler for node-level scaling (min 3, max 10 nodes in production). KEDA for event-driven scaling on queue depth. Spot node pools for non-critical workloads (60–70% cost savings).

**Q: What is your AKS networking model?**
A: Azure CNI with VNet integration. Dedicated AKS subnet (10.0.0.0/20) with NSG rules. Internal load balancer, no public IP. Ingress via Application Gateway WAF. Private API server endpoint. Network policies for pod-to-pod traffic control.

### 1.5 Azure Functions

**Q: Why Functions for the RAG pipeline?**
A: Three parallel Functions (Pre-Retrieval, RAG Processor, Ingestion) provide independent scaling, isolated failure domains, and pay-per-execution cost for variable workloads. Durable Functions handle long-running ingestion with checkpointing.

**Q: How do you handle cold starts?**
A: Premium plan with always-ready instances (min 1 in production). Pre-warmed instances for burst traffic. Dependency injection optimized — Azure SDK clients initialized once per instance. Connection pooling for Cosmos DB and Redis.

**Q: What is the Functions networking model?**
A: VNet-integrated Functions with dedicated subnet. Private endpoints for all downstream services (OpenAI, Search, Cosmos DB, Redis). No public internet egress — all traffic via private network.

### 1.6 Azure Cosmos DB

**Q: Why Cosmos DB over Azure SQL?**
A: Cosmos DB provides single-digit millisecond latency for key-value lookups (conversations, sessions), flexible schema for evolving metadata, global distribution for future multi-region, and partition-key-based tenant isolation. SQL would add unnecessary relational overhead for our document-oriented data.

**Q: Explain your partition key strategy.**
A: `/tenantId` for multi-tenant containers (conversations, sessions). This ensures tenant isolation at the storage level, co-locates tenant data for efficient queries, and prevents cross-tenant reads. Autoscale RU/s: 400–4000 for conversations, 400–1000 for evaluations.

**Q: How do you manage Cosmos DB costs?**
A: Autoscale RU/s to handle burst without over-provisioning. TTL-based data expiration (conversations 90 days, evaluations 365 days, audit 2555 days). Composite indexes reduce cross-partition query RU consumption. Analytical store for reporting queries without impacting transactional workload.

**Q: What containers do you use?**
A: 7 containers — `conversations` (chat history), `sessions` (active sessions), `evaluations` (quality metrics), `feedback` (user ratings), `audit-events` (compliance trail), `tenant-config` (per-tenant settings), `model-metrics` (performance data). Each with specific TTL and RU/s allocation.

### 1.7 Azure Key Vault

**Q: How do you manage secrets rotation?**
A: 90-day rotation policy for all keys. Event Grid triggers Azure Function on near-expiry. Function generates new key, updates downstream services, validates connectivity, then marks old version for deletion. HSM-backed keys in production (Premium SKU), software-backed in dev/staging.

**Q: What secrets are stored?**
A: API keys (OpenAI, Search, Document Intelligence), connection strings (Cosmos DB, Redis, Storage), certificates (TLS, client auth), encryption keys (CMK for storage and Cosmos DB). All accessed via managed identity — no secrets in code or config.

### 1.8 Azure Redis Cache

**Q: What is your caching strategy?**
A: Three-tier cache — Query cache (exact match, TTL 15–30 min), Retrieval cache (search results, TTL 30–60 min), Embedding cache (pre-computed vectors, TTL 30 days). Cache-aside pattern with write-through for frequently updated data.

**Q: How do you handle cache invalidation?**
A: Event-driven invalidation when source documents change (via Event Grid). Scheduled invalidation via nightly job. TTL-based expiration as safety net. Cache warming on deployment for top-100 queries.

**Q: What is the ROI of Redis cache?**
A: $400/month investment → $1,200/month savings (break-even in Month 1). Cache hit ratio target: 40–60%. Reduces average latency from 2.5s to 200ms for cached queries. Reduces OpenAI token consumption by 26–30%.

### 1.9 Azure API Management (APIM)

**Q: What does APIM handle in the architecture?**
A: API gateway for all external traffic — JWT validation, rate limiting (B2E 50/min, B2C 20/min), request/response transformation, API versioning, developer portal, usage analytics. Also handles subscription key management for partner integrations.

**Q: How do you implement rate limiting?**
A: Per-subscription rate limits enforced at APIM level. Burst: 10 requests/10 seconds. Sustained: 50/min (B2E), 20/min (B2C). Per-tenant token budget enforced at application level. 429 responses include `Retry-After` header.

### 1.10 Azure Storage (Data Lake Gen2)

**Q: How is storage organized?**
A: Hierarchical namespace with Data Lake Gen2. Container structure: `raw/` (uploaded documents), `processed/` (OCR output), `chunks/` (chunked text), `embeddings/` (vector files), `evaluation/` (golden datasets, results). RBAC per container via Entra ID.

**Q: What are the retention policies?**
A: Hot tier: 90 days (active documents). Cool tier: 275 days (archived). Archive tier: 2190 days (compliance). Lifecycle management policies auto-transition between tiers. Legal hold for documents under litigation.

### 1.11 Azure Entra ID

**Q: How do you implement RBAC?**
A: Group-based access control synced from Entra ID. Groups: All Employees, HR Team, Finance Team, Engineering, Executives, Legal. Document-level ACL tags match Entra groups. Conditional Access policies enforce MFA, compliant devices, and location-based restrictions.

**Q: What is the auth flow?**
A: OAuth 2.0 authorization code flow via Entra ID. JWT tokens validated at APIM. Token claims include user ID, groups, tenant ID. Managed Identity for service-to-service auth (zero secrets). PIM for privileged access to production resources.

### 1.12 Azure Application Insights

**Q: What custom metrics do you track?**
A: RAG-specific: groundedness score, hallucination rate, citation accuracy, cache hit ratio, tokens consumed. Operational: query latency (P50/P95/P99), error rate by type, concurrent users. Business: queries per department, adoption rate, feedback scores.

**Q: How do you correlate traces across services?**
A: OpenTelemetry SDK with W3C trace context propagation. Operation ID flows from APIM → Functions → OpenAI → Search → Cosmos DB. Custom dimensions tag each span with `tenantId`, `userId`, `queryIntent`.

### 1.13 Azure Log Analytics

**Q: What queries do you run most frequently?**
A: Top Kusto queries: (1) P95 latency trend by hour, (2) Error rate by service, (3) Token consumption by tenant, (4) Cache hit ratio trend, (5) PII detection events, (6) Failed authentication attempts. Saved queries shared via workspace.

**Q: How do you manage log volume and cost?**
A: Log sampling at 20% for verbose traces (dependency calls). Full logging for errors and security events. Data retention: 90 days interactive, 730 days archive. Basic logs tier for high-volume, low-query data. Estimated cost: $250–$400/month production.

### 1.14 Azure Sentinel

**Q: What security detections are configured?**
A: Custom analytics rules: (1) Brute force login attempts (>5 failures in 10 min), (2) Unusual query patterns (>3x normal volume), (3) PII exfiltration attempts, (4) Prompt injection patterns, (5) After-hours admin access, (6) Cross-tenant data access attempts.

**Q: How does Sentinel integrate with the platform?**
A: Log Analytics workspace feeds Sentinel. Custom connectors ingest APIM logs, Function logs, AI audit events. Automated playbooks (Logic Apps) for incident response — block user, notify SOC, create ticket.

### 1.15 Azure WAF (Application Gateway)

**Q: What WAF rules are configured?**
A: OWASP 3.2 core rule set. Custom rules: block SQL injection in query params, rate limiting by IP, geo-blocking (if required). WAF mode: Prevention in production, Detection in staging. Bot protection enabled with managed rule set.

### 1.16 Azure Bastion

**Q: Why Bastion over jump boxes?**
A: Bastion provides secure RDP/SSH via browser without public IPs on VMs. No need to manage jump box OS patching, no inbound NSG rules for RDP/SSH. Session recording for audit compliance. Standard SKU for file upload/download capability.

### 1.17 Azure Container Registry (ACR)

**Q: How do you secure container images?**
A: Premium SKU with geo-replication. Content trust (Docker Notary) for signed images. Vulnerability scanning via Defender for Containers. Private endpoint access only. Retention policy: keep last 10 tags per repository. Automated build tasks on code push.

### 1.18 Azure DDoS Protection

**Q: What tier and why?**
A: Standard tier for adaptive tuning and telemetry. Protects public-facing Application Gateway endpoint. DDoS alerts integrated with Sentinel. Cost justification: potential downtime cost far exceeds $2,944/month Standard tier.

### 1.19 Azure Content Safety

**Q: How do content filters work in the pipeline?**
A: Dual-pass filtering — Input: scan user query for hate, sexual, violence, self-harm content (Medium threshold). Output: scan LLM response before delivery. Prompt injection detection as separate layer. Custom blocklist for domain-specific terms. Severity levels: Low (log), Medium (flag), High (block).

### 1.20–1.29 Additional Services

**Azure Private Link / Private Endpoints:**
- Q: How many private endpoints? A: 8 private endpoints covering OpenAI, AI Search, Cosmos DB, Storage, Key Vault, Redis, ACR, and Document Intelligence. All inter-service traffic stays on Azure backbone.

**Azure VNet / NSGs:**
- Q: VNet architecture? A: 10.0.0.0/16 with dedicated subnets — AKS (/20), Functions (/24), Private Endpoints (/24), Bastion (/26), Application Gateway (/24). NSG rules follow least-privilege with explicit deny default.

**Azure Monitor:**
- Q: What alerts exist? A: 12 alert rules covering latency, errors, groundedness, tokens, PII leaks, cache health, scaling events, certificate expiry, budget thresholds, security events.

**Azure Defender for Cloud:**
- Q: What Defender plans are enabled? A: Defender for Containers (AKS), Defender for Storage, Defender for Key Vault, Defender for Cosmos DB, Defender for App Service. Security score target: ≥90%.

**Azure Policy:**
- Q: What policies enforce compliance? A: Require HTTPS, require encryption at rest, deny public endpoints, enforce tagging, restrict allowed SKUs, require diagnostic settings.

**Azure Event Grid:**
- Q: How is Event Grid used? A: Document upload triggers ingestion pipeline, key rotation triggers secret update, index change triggers cache invalidation, alert triggers incident response.

**Azure Data Factory:**
- Q: Is ADF used? A: For batch document ingestion from SharePoint and file shares. Scheduled pipelines for ETL from source systems. Monitoring via ADF built-in dashboards.

**Azure Purview / Microsoft Purview:**
- Q: Data governance integration? A: Data catalog for document lineage, sensitivity labels for PII classification, compliance reporting for GDPR/SOX audits.

**Azure Service Bus:**
- Q: Why Service Bus? A: Decouples ingestion pipeline — upload events queued for processing. Dead letter queue for failed ingestion. Session-based ordering for batch operations. Complements Event Grid for reliable messaging.

---

## 2. Quality Validation Questions

**Q: How do you validate RAG output quality?**
A: Five-layer validation — (1) Automated eval pipeline using LLM-as-judge (groundedness, relevance, coherence, fluency), (2) Golden dataset of 200 Q&A pairs across 5 categories, (3) Human spot-checks (weekly sample of 50 queries), (4) User feedback analysis (thumbs up/down, star ratings), (5) A/B testing for configuration changes.

**Q: What evaluation metrics do you track?**
A: Core RAG: Groundedness (≥0.80), Relevance (≥0.70), Coherence (≥0.75), Fluency (≥0.80), Citation Accuracy (≥0.90), Hallucination Rate (≤0.10). Retrieval: Precision@K, Recall@K, NDCG@10, MRR, Hit Rate. Operational: Latency P50/P95, token efficiency, cost per query, user satisfaction (≥4.2/5).

**Q: What is a golden dataset and how is it maintained?**
A: 200 curated query-answer pairs with verified ground truth. Categories: factual (80), procedural (40), comparative (30), summarization (30), edge cases (20). Refreshed quarterly. Each entry includes: query, expected answer, source documents, difficulty level, query type.

**Q: How do you detect evaluation drift?**
A: Weekly automated evaluation against golden dataset. Score trends tracked in App Insights. Alert if groundedness drops below 0.75 for >1 hour. Monthly comparison against baseline. Drift triggers investigation: index freshness, model version, data quality.

**Q: Explain G-Eval technique.**
A: G-Eval uses GPT-4 to evaluate GPT-4 outputs. Prompt includes evaluation criteria, scoring rubric (1–5 scale), and chain-of-thought reasoning. More consistent than single-score prompts. Used for subjective metrics like coherence and fluency where rule-based evaluation fails.

---

## 3. Monitoring & Observability Questions

**Q: Describe your monitoring stack.**
A: Application Insights (APM, custom metrics, traces), Log Analytics (centralized logs, Kusto queries), Sentinel (security analytics, SIEM), Azure Monitor (alerts, action groups), Grafana (optional dashboards). All connected via Log Analytics workspace.

**Q: How do you implement distributed tracing?**
A: OpenTelemetry SDK with W3C trace context. Each request gets a unique `operation_Id` that propagates across APIM → Functions → OpenAI API → AI Search → Cosmos DB → Redis. Custom spans for business logic (chunking, PII scan, reranking). Traces stored in App Insights for 90 days.

**Q: What dashboards do you have?**
A: (1) Real-time operations: request rate, latency, errors, (2) RAG pipeline health: search latency, LLM latency, cache hit ratio, (3) Quality metrics: groundedness trend, hallucination rate, user satisfaction, (4) Cost dashboard: spend by service, cost per query, token consumption, (5) Security dashboard: auth failures, PII events, content filter triggers.

**Q: How do you handle alert fatigue?**
A: Severity-based routing — Sev 0 (PII leak): page immediately. Sev 1 (error spike): page on-call. Sev 2 (latency/quality): notify team channel. Sev 3 (cost/info): daily digest. Alert suppression for known maintenance windows. Alert correlation to group related issues.

**Q: What is your latency budget breakdown?**
A: Total budget: 2650ms. API gateway: 20ms, Embedding: 50ms, Search: 200ms, Reranking: 150ms, LLM generation: 2000ms, Post-processing: 200ms, Cache lookup: 15ms. Tracked per component via distributed tracing.

---

## 4. Testing & Deployment Questions

**Q: Describe your CI/CD pipeline.**
A: GitHub Actions with 5 stages — (1) Build: lint, type check, unit tests, (2) Security: dependency scan, SAST, secret detection, (3) Deploy to staging: Terraform apply, blue-green swap, (4) Quality gates: integration tests, smoke tests, evaluation pipeline, (5) Deploy to production: canary rollout (10% → 50% → 100%), automated rollback on failure.

**Q: How do you implement blue-green deployments?**
A: Two AKS deployment slots. New version deployed to inactive slot. Smoke tests validate health. Traffic switched via Application Gateway backend pool update. Old slot kept running for 30 minutes as rollback target. Zero-downtime deployment verified via synthetic transactions.

**Q: What are your release gates?**
A: Quality: groundedness ≥0.80, hallucination ≤0.10. Performance: P95 latency ≤5s, error rate <1%. Safety: no PII leaks, no prompt injection bypass. Regression: no degradation >5% from baseline. All gates automated; failure blocks deployment.

**Q: How do you handle database migrations?**
A: Cosmos DB is schema-flexible — no traditional migrations. Schema changes handled via application-level versioning. Breaking changes use dual-write pattern during transition. Index changes via blue-green indexing on AI Search.

**Q: How do you test in production safely?**
A: Canary deployments with 10% traffic. Feature flags for new capabilities. Synthetic monitoring for baseline comparison. Automated rollback if error rate exceeds threshold. A/B testing framework for configuration changes.

---

## 5. Logging, Tracing & Visualization

**Q: What log categories do you capture?**
A: Application logs (structured JSON), Audit logs (all user actions), Security logs (auth events, PII detections), Performance logs (latency, tokens), Error logs (exceptions, retries), Infrastructure logs (AKS, Functions platform).

**Q: Show a useful Kusto query.**
A:
```kusto
// P95 latency by hour for last 24 hours
requests
| where timestamp > ago(24h)
| summarize p95_latency = percentile(duration, 95) by bin(timestamp, 1h)
| render timechart

// Top 10 slowest queries
requests
| where timestamp > ago(24h)
| top 10 by duration desc
| project timestamp, name, duration, customDimensions.queryIntent

// Cache hit ratio trend
customMetrics
| where name == "cache_hit_ratio"
| summarize avg_ratio = avg(value) by bin(timestamp, 1h)
| render timechart
```

**Q: How do you use Power BI for reporting?**
A: Power BI connected to Log Analytics via direct query. Dashboards: (1) Executive summary (adoption, satisfaction, cost), (2) Quality trends (weekly eval scores), (3) Usage analytics (queries by department, peak hours), (4) Cost analysis (spend trend, forecast). Refreshed daily.

**Q: How do you implement OpenTelemetry?**
A: OpenTelemetry Python SDK with Azure Monitor exporter. Auto-instrumentation for HTTP, database calls. Custom spans for business logic. Baggage propagation for tenant context. Resource attributes: service name, version, environment. Sampling: 100% for errors, 20% for success.

---

## 6. Reporting & Costing Questions

**Q: What is your FinOps maturity model?**
A: Three phases — Crawl: resource tagging, cost visibility, basic budgets. Walk: chargeback model, optimization recommendations, reserved instances. Run: automated scaling policies, anomaly detection, predictive budgeting. Currently transitioning from Crawl to Walk.

**Q: How do you implement chargeback?**
A: Shared infrastructure (networking, monitoring) split equally across tenants. AI services metered per tenant via token consumption tracking. Compute weighted by usage (query volume). Monthly chargeback reports generated from tagged resource costs + custom metrics.

**Q: What is the cost per query at different scales?**

| Scale | Queries/Day | Cost/Query | Monthly Total |
|-------|------------|------------|---------------|
| Low | 1,000 | $0.46 | $13,909 |
| Medium | 10,000 | $0.09 | $27,000 |
| High | 50,000 | $0.03 | $45,000 |

**Q: How do you optimize token costs?**
A: (1) Model routing: GPT-4o-mini for simple tasks (45% savings), (2) Caching: avoid redundant LLM calls (26–30% reduction), (3) Context compression: reduce retrieved text before LLM (15% savings), (4) Prompt optimization: concise system prompts, (5) Token budget enforcement per user/session.

**Q: What reserved instance savings do you achieve?**
A: 1-year RI: 37% savings on AKS nodes, Cosmos DB RU/s. 3-year RI: 60% savings where commitment is justified. Spot nodes for non-critical workloads: 60–70% discount. Total infrastructure savings: ~40% vs pay-as-you-go.

---

## 7. Architecture Decision Defense

### How to Defend Key ADRs

**ADR: Chose Azure AI Search over Elasticsearch**
- Defense: Native Azure integration, semantic ranking built-in, vector search + BM25 hybrid, managed service reduces ops burden. Trade-off: less customizable than self-managed Elastic, but operational cost is ~60% lower.

**ADR: Chose Cosmos DB over Azure SQL**
- Defense: Sub-10ms reads for key-value patterns (conversations, sessions), schema flexibility for evolving metadata, partition-key tenant isolation, global distribution ready. Trade-off: higher per-operation cost, no relational joins (not needed for our data model).

**ADR: Chose Azure Functions over AKS for RAG pipeline**
- Defense: Independent scaling per pipeline stage, pay-per-execution for variable load, Durable Functions for long-running ingestion. Trade-off: cold start latency (mitigated by Premium plan), less control than AKS pods.

**ADR: Three parallel Functions vs monolithic API**
- Defense: Failure isolation (ingestion failure doesn't affect queries), independent scaling (queries scale differently from ingestion), independent deployment (update ingestion without touching query pipeline). Trade-off: increased operational complexity (3 deployments vs 1).

**ADR: HNSW over IVF for vector index**
- Defense: HNSW provides better recall at our index size (<5M vectors), tunable trade-off between speed and accuracy. IVF requires careful cluster selection and works better at >10M vectors. Trade-off: higher memory usage (acceptable for our scale).

**Handling Pushback:**
- "Why not use LangChain for everything?" — We use LangChain selectively for orchestration, not as a full framework. Direct Azure SDK calls for performance-critical paths reduce latency and dependency risk.
- "Why not a single LLM for all tasks?" — Model routing saves 45% on AI costs. Simple tasks don't need GPT-4o's capacity.
- "Why not PostgreSQL with pgvector?" — AI Search provides managed hybrid search with semantic ranking, no vector DB management overhead, native Azure security integration.

---

## 8. Scenario-Based Questions

### 8.1 Troubleshooting Scenarios

**Scenario: Users report slow responses (P95 > 5s)**
```
Investigation steps:
1. Check App Insights → Performance → Operations (identify slow operation)
2. Open distributed trace for a slow request
3. Identify bottleneck component (typically LLM or Search)
4. Check Azure OpenAI → Metrics → Latency and Throttling
5. Check AI Search → Metrics → Search latency and throttled queries
6. Check Redis → Cache hit ratio (drop indicates cache issue)
7. Mitigation: Scale up/out bottleneck, increase cache TTL, optimize query
```

**Scenario: Groundedness score drops below 0.75**
```
Investigation steps:
1. Check evaluation dashboard for when drop started
2. Correlate with recent deployments or index changes
3. Review recent document ingestion (stale or corrupted chunks?)
4. Run golden dataset evaluation to confirm
5. Check search relevance scores (retrieval quality vs generation quality)
6. Mitigation: Reindex affected documents, roll back config changes, adjust chunking
```

**Scenario: PII detected in LLM output**
```
Incident response:
1. IMMEDIATE: Block affected response (auto-blocked by content filter)
2. Check audit log for scope (how many responses affected?)
3. Investigate source: PII in source documents? PII in training data?
4. If source documents: re-process with enhanced PII masking
5. If model behavior: increase output PII scanning sensitivity
6. Post-incident: Update PII detection rules, add test cases
7. Report to security team and compliance officer
```

### 8.2 Scaling Scenarios

**Scenario: Traffic spikes 10x during open enrollment**
```
Preparation:
1. Pre-scale AKS nodes (autoscaler max from 10 → 25)
2. Pre-warm cache with top-100 enrollment queries
3. Pre-scale Cosmos DB RU/s (autoscale max from 4000 → 10000)
4. Increase OpenAI TPM quota (request temporary increase)
5. Enable aggressive caching (extend TTL)
6. Prepare circuit breaker for graceful degradation
7. Monitor: real-time dashboard, 15-minute check-ins
```

**Scenario: New department onboarding (500 users, 10K documents)**
```
Steps:
1. Create Entra ID group for department
2. Configure tenant settings in Cosmos DB
3. Ingest 10K documents with proper ACL tags
4. Validate search quality with department SME
5. Run evaluation against department-specific golden dataset
6. Gradual rollout: 10% → 50% → 100% of department users
7. Monitor adoption, quality, and cost metrics
```

### 8.3 Incident Response Scenarios

**Scenario: Suspected prompt injection attack**
```
Response:
1. Content Safety detects injection pattern → auto-block
2. Log query with full context (anonymized)
3. Analyze pattern: systematic attack or accidental?
4. If systematic: block source IP/user, escalate to security
5. Review prompt injection defense layers:
   - Input: instruction delimiter, input sanitization
   - System: robust system prompt with boundaries
   - Output: response validation, citation check
   - Monitor: pattern detection in Sentinel
6. Update custom blocklist if new pattern identified
```

---

## 9. Role-Specific Questions

### 9.1 Manager Questions

**Q: What is the project RACI?**
A: Responsible: Engineering team (development, testing). Accountable: Project manager (delivery, budget). Consulted: Security team, compliance team, department SMEs. Informed: Executive sponsors, end users, partners.

**Q: What is the budget breakdown?**
A: Monthly: Dev $782, Staging $2,318, Production $13,909 = $17,009/month. Annual: $204,108. Optimization target: reduce to $160K/year via reserved instances and caching improvements.

**Q: What are the key risks and mitigations?**
A: Top 5: (1) Hallucination → grounding + evaluation gates, (2) Data leakage → RBAC + testing, (3) Poor retrieval → hybrid search + tuning, (4) Latency → caching + scaling, (5) Cost overrun → budgets + model routing. Each risk has owner, probability, impact, and mitigation plan.

**Q: How do you measure success?**
A: KPIs: 85% accuracy, 60% adoption, 4.2/5 satisfaction, ≤$0.05 cost/query, ≤3s P95 latency, ≤5% hallucination. Tracked weekly, reported monthly, reviewed quarterly.

### 9.2 Architect Questions

**Q: Justify the 6-layer security model.**
A: Defense-in-depth — each layer addresses different attack vectors. Network (perimeter), Identity (authentication), Application (input validation), Data (classification/encryption), Encryption (keys/certificates), AI (content safety/prompt defense). Compromise of one layer doesn't expose the system.

**Q: How does this architecture scale to 10x current load?**
A: Horizontal scaling at each tier: AKS node autoscaler, Functions concurrent instances, Cosmos DB autoscale RU/s, AI Search replicas. Vertical: OpenAI TPM quota increase. Architectural: add read replicas, geographic distribution, CDN for static content.

**Q: What would you change with unlimited budget?**
A: (1) Azure OpenAI provisioned throughput for guaranteed latency, (2) Cosmos DB multi-region write for DR, (3) Dedicated AI Search cluster for index isolation, (4) Real-time evaluation pipeline (currently batch), (5) Fine-tuned model for domain-specific accuracy.

### 9.3 DevOps Questions

**Q: Describe your Terraform module structure.**
A: Root module calls child modules: `networking` (VNet, NSGs, PEs), `compute` (AKS, Functions), `data` (Cosmos DB, Storage, Redis), `ai` (OpenAI, Search, Doc Intel), `security` (Key Vault, Entra, WAF), `monitoring` (App Insights, Log Analytics, Sentinel). State stored in Azure Storage with locking.

**Q: How do you handle secrets in CI/CD?**
A: GitHub Actions secrets for service principal credentials. Terraform accesses Key Vault via managed identity. Application config injected via Key Vault references (no secrets in code, config, or environment variables). Secret scanning in pipeline blocks commits with secrets.

**Q: What is your incident response process?**
A: Detection (automated alerts + user reports) → Triage (severity classification) → Investigation (distributed tracing, log analysis) → Mitigation (scale, rollback, hotfix) → Resolution (root cause fix) → Review (blameless post-mortem, runbook update). SLAs: P0 immediate, P1 <1hr, P2 <4hrs, P3 next business day.

### 9.4 Cloud Engineer Questions

**Q: Walk through the VNet architecture.**
A: 10.0.0.0/16 with 5 subnets — AKS (10.0.0.0/20, 4096 IPs for pods), Functions (10.0.16.0/24), Private Endpoints (10.0.17.0/24), Bastion (10.0.18.0/26), Application Gateway (10.0.19.0/24). All inter-service traffic via private endpoints. No public IPs except Application Gateway frontend.

**Q: How do you handle DR?**
A: RPO: 1 hour (Cosmos DB continuous backup, Storage GRS). RTO: 4 hours (Terraform re-deploy to paired region). Regular DR drills quarterly. Runbook for failover procedure. AI Search index rebuild from Storage backup (2–4 hours for full reindex).

### 9.5 Developer Questions

**Q: Walk through the code structure.**
A: `backend/shared/` — common utilities (auth, PII, cache, config). `backend/azure-functions/` — three Function apps (pre-retrieval, rag-processor, ingestion). Each Function follows: input validation → business logic → output formatting. LangChain for orchestration, Azure SDK for service calls.

**Q: How do you test Azure SDK interactions?**
A: Mock Azure SDK clients using `unittest.mock`. Fixture-based test data for search results, LLM responses. Integration tests against real Azure services in staging (not mocked). Contract tests verify API request/response schemas.

### 9.6 Tester Questions

**Q: What is your test pyramid?**
A: Base: Unit tests (80%+ coverage, pytest, fast, mocked). Middle: Integration tests (API contract, service chain, staging). Top: E2E tests (user scenarios, golden dataset eval). Outer: Performance tests (load, stress, soak). Cross-cutting: Security tests (pen test, prompt injection).

**Q: How do you test RAG quality?**
A: Automated evaluation pipeline: LLM-as-judge scores groundedness, relevance, coherence, fluency for every release. Golden dataset regression testing. Human evaluation: weekly spot-checks (50 queries), monthly full eval (200 queries), quarterly red team.

---

## 10. Whiteboard Exercise Guide

### 10.1 Draw the Architecture

**What to draw:**
```
[Users] → [Copilot Studio / Chat UI]
          → [APIM Gateway]
              → [Pre-Retrieval Function]
                  → [Redis Cache]
              → [RAG Processor Function]
                  → [Azure OpenAI] (embedding + generation)
                  → [Azure AI Search] (hybrid search)
                  → [Cosmos DB] (session, conversation)
              → [Ingestion Function]
                  → [Document Intelligence] (OCR)
                  → [Azure Storage] (Data Lake)
                  → [Azure AI Search] (indexing)
          [Key Vault] — secrets for all services
          [App Insights + Log Analytics] — monitoring
          [Entra ID] — authentication
          [VNet + Private Endpoints] — networking
```

**Key points to articulate:**
- Three parallel Functions for isolation and independent scaling
- Private endpoints for all inter-service communication
- Cache-aside pattern at query and retrieval levels
- ACL-enforced search results based on Entra ID groups
- Dual-model strategy: GPT-4o for RAG, GPT-4o-mini for simple tasks

### 10.2 Explain the Data Flow

**Query flow (11 steps):**
1. User submits query via Copilot Studio
2. APIM validates JWT, applies rate limit
3. Pre-Retrieval Function: intent detection, query expansion, ACL filter
4. Cache check: exact query hash in Redis
5. If miss: generate embedding via text-embedding-3-large
6. Hybrid search: vector + BM25 + semantic ranking with ACL filter
7. Post-retrieval: deduplicate, rerank, compress context
8. LLM generation: GPT-4o with system prompt + retrieved context
9. Post-processing: PII scan, content safety, citation extraction
10. Cache write: store response in Redis
11. Return response with citations, confidence, follow-up suggestions

### 10.3 Design for Failure

**What to cover:**
- Circuit breaker on OpenAI calls (fail-open to cached response)
- Retry with exponential backoff on transient failures
- Dead letter queue for failed ingestion jobs
- Health probes on all Functions (liveness + readiness)
- Graceful degradation: if search fails, return "unable to answer"
- If cache fails, bypass cache (increased latency, not failure)
- If PII scan fails, block response (fail-safe, not fail-open)
- Multi-region DR with RPO 1hr, RTO 4hrs

---

## Cross-References

- [DEMO-PLAYBOOK.md](./DEMO-PLAYBOOK.md) — Live demo scripts and checklists
- [TECH-STACK-SERVICES.md](./TECH-STACK-SERVICES.md) — Full 29-service inventory
- [AZURE-SERVICE-DEEP-DIVE.md](./AZURE-SERVICE-DEEP-DIVE.md) — Per-service operational guide
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Detailed testing approach
- [PROJECT-BUSINESS-CASE.md](../architecture/PROJECT-BUSINESS-CASE.md) — Business case and KPIs
- [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) — Security architecture details
- [FINOPS-COST-MANAGEMENT.md](../operations/FINOPS-COST-MANAGEMENT.md) — Cost management
- [Interview Guide (Portfolio)](../../azurecloud/INTERVIEW_GUIDE.md) — Portfolio-level interview prep
