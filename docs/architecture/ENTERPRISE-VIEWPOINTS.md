# Enterprise Viewpoints

> **Multi-Stakeholder Perspectives for Azure OpenAI Enterprise Platform**
>
> Architecture | Management | Deployment | Scalability | NFR | B2B | B2C | B2E

---

## Table of Contents

1. [Architect Viewpoint](#architect-viewpoint)
2. [Manager Viewpoint](#manager-viewpoint)
3. [Deployment Viewpoint](#deployment-viewpoint)
4. [Scalability Viewpoint](#scalability-viewpoint)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [B2B Viewpoint](#b2b-viewpoint)
7. [B2C Viewpoint](#b2c-viewpoint)
8. [B2E Viewpoint](#b2e-viewpoint)

---

## Architect Viewpoint

### System Design Principles

| Principle | Approach | Trade-off |
|-----------|----------|-----------|
| **Loose Coupling** | Microservices via AKS, event-driven Functions | Distributed complexity |
| **High Cohesion** | Domain-bounded services (ingestion, retrieval, generation) | Service boundaries must be maintained |
| **Data Sovereignty** | Tenant-scoped partitions, region-aware | Cross-region latency |
| **Fail-Safe Defaults** | Content filters on, PII masking on, public access off | May over-restrict initially |
| **Defense in Depth** | 6 security layers (network → AI) | Operational overhead |

### Integration Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **API Gateway** | External and internal API access | Azure APIM with JWT validation |
| **Event-Driven** | Document ingestion, cache invalidation | Blob triggers → Functions → AI Search |
| **Request-Reply** | Synchronous chat queries | APIM → AKS → OpenAI → Response |
| **CQRS** | Separate read/write for conversations | Cosmos DB (write) + Cache (read) |
| **Circuit Breaker** | OpenAI rate limit protection | Polly/resilience4j with fallback |
| **Saga** | Multi-step document processing | Durable Functions orchestration |
| **Sidecar** | Logging, auth token refresh, PII scanning | AKS sidecar containers |

### Key Trade-offs

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| Consistency vs Latency | Strong consistency | Eventual consistency | Eventual | Sub-second query response |
| Cost vs Quality | GPT-4o-mini for all | Model routing | Routing | Quality for complex, cost for simple |
| Simplicity vs Control | Container Apps | AKS | AKS | Enterprise networking requirements |
| Freshness vs Performance | Real-time indexing | Batch indexing | Batch (15 min) | Acceptable freshness for enterprise docs |

### Component Interaction Map

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   APIM      │────►│  AKS        │────►│ Azure OpenAI│
│  (Gateway)  │     │ (Services)  │     │  (LLM)      │
└──────┬──────┘     └──────┬──────┘     └─────────────┘
       │                   │
       │            ┌──────┼──────────────┐
       │            ▼      ▼              ▼
       │     ┌──────────┐ ┌──────────┐ ┌──────────┐
       │     │AI Search │ │Cosmos DB │ │  Redis   │
       │     │(Vectors) │ │(Sessions)│ │ (Cache)  │
       │     └──────────┘ └──────────┘ └──────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Functions  │────►│  Doc Intel  │────►│ Data Lake   │
│ (Ingestion) │     │  (OCR)      │     │ (Storage)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Manager Viewpoint

### RACI Matrix

| Activity | AI Governance Board | Platform Team | Security Team | DevOps | Data Engineering |
|----------|:---:|:---:|:---:|:---:|:---:|
| AI Policy Approval | **A** | C | C | I | I |
| Model Selection | A | **R** | C | I | I |
| Infrastructure Deploy | I | C | C | **R** | I |
| Data Pipeline | I | C | I | I | **R** |
| Security Audit | I | C | **R** | C | C |
| Incident Response | I | **R** | A | R | C |
| Cost Management | **A** | R | I | R | I |
| Capacity Planning | I | **R** | I | R | C |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

### Budget Breakdown

| Category | Monthly Estimate (Prod) | % of Total |
|----------|------------------------|------------|
| Compute (AKS + Functions) | $3,500–$5,000 | 30% |
| AI Services (OpenAI + Search) | $4,000–$6,000 | 35% |
| Storage (Data Lake + Cosmos DB) | $800–$1,200 | 8% |
| Networking (VNet, APIM, Bastion) | $1,500–$2,000 | 13% |
| Monitoring (Log Analytics, App Insights) | $500–$800 | 5% |
| Security (Key Vault, Defender) | $300–$500 | 3% |
| Cache (Redis) | $400–$600 | 4% |
| **Total** | **$11,000–$16,100** | **100%** |

### Timeline — Phased Delivery

| Phase | Duration | Deliverables | Exit Criteria |
|-------|----------|-------------|---------------|
| **Phase 1: Foundation** | Weeks 1–4 | Infrastructure, networking, security baseline | Terraform deployed, private endpoints verified |
| **Phase 2: Core AI** | Weeks 5–8 | RAG pipeline, ingestion, basic chat | End-to-end query working, groundedness ≥ 0.80 |
| **Phase 3: Enterprise** | Weeks 9–12 | Multi-tenant, RBAC, audit, monitoring | Tenant isolation verified, alerts configured |
| **Phase 4: Production** | Weeks 13–16 | Performance tuning, DR, go-live | SLA met, DR tested, security audit passed |

### Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|----|------|-----------|--------|------------|-------|
| R1 | Azure OpenAI rate limits exceeded | Medium | High | Token budgets, caching, model routing | Platform Team |
| R2 | Model deprecation by Azure | Low | High | Abstraction layer, migration runbook | Architecture |
| R3 | Data leakage across tenants | Low | Critical | Defense-in-depth, pen testing | Security Team |
| R4 | Cost overrun | Medium | Medium | Budget alerts, FinOps reviews | Platform Team |
| R5 | Skill gap (Kubernetes, AI) | Medium | Medium | Training plan, vendor support | Manager |
| R6 | Regulatory change (AI Act) | Low | High | Governance framework, legal review | AI Governance |

---

## Deployment Viewpoint

### Deployment Strategy

| Strategy | Environment | Use Case |
|----------|-------------|----------|
| **Blue-Green** | Production | Zero-downtime releases for infrastructure |
| **Canary** | Production | Gradual rollout for AI model changes |
| **Rolling** | Staging | Standard AKS deployment |
| **Recreate** | Development | Fast iteration, downtime acceptable |

### Blue-Green Deployment

```
                    ┌─────────────────────────┐
                    │     Traffic Manager /     │
                    │     App Gateway           │
                    └────────┬────────────────┘
                             │
                   ┌─────────┼─────────┐
                   ▼                   ▼
            ┌──────────┐        ┌──────────┐
            │  Blue    │        │  Green   │
            │ (Active) │        │ (Standby)│
            │  v2.1    │        │  v2.2    │
            └──────────┘        └──────────┘
                                     │
                              Deploy + Test
                                     │
                              Swap traffic
                                     │
                              Blue becomes standby
```

### Canary Deployment for Model Changes

```yaml
Canary Configuration:
  Initial: 5% traffic to new model
  Step 1: 5% → Monitor for 1 hour
  Step 2: 25% → Monitor for 4 hours
  Step 3: 50% → Monitor for 24 hours
  Step 4: 100% → Full rollout

  Rollback Triggers:
    - Groundedness drops below 0.75
    - Error rate exceeds 5%
    - Latency P95 exceeds 8s
    - Content filter triggers increase 2x

  Metrics Monitored:
    - Groundedness score (AI eval)
    - Relevance score (AI eval)
    - Latency P50, P95, P99
    - Error rate
    - Token consumption
    - User satisfaction (thumbs up/down)
```

### Environment Promotion

```
Dev  ──►  Staging  ──►  Production
 │           │              │
 │    Automated tests   Manual approval
 │    Integration tests    + CAB review
 │    Security scan     + DR verification
 │
 └── PR merge triggers CI/CD
```

### Rollback Procedures

| Scenario | Rollback Method | RTO |
|----------|----------------|-----|
| Bad application deploy | AKS rollback to previous ReplicaSet | < 5 min |
| Bad infrastructure change | Terraform state rollback | < 30 min |
| Bad model config | Revert deployment config in Key Vault | < 10 min |
| Bad index update | Restore from AI Search backup index | < 2 hours |
| Data corruption | Cosmos DB point-in-time restore | < 1 hour |

---

## Scalability Viewpoint

### Horizontal Scaling

| Component | Scaling Trigger | Min | Max | Scale Metric |
|-----------|----------------|-----|-----|-------------|
| AKS System Pool | CPU > 70% | 2 | 6 | CPU utilization |
| AKS Workload Pool | RPS > 100/pod | 1 | 10 | Request rate |
| Azure Functions | Queue depth > 100 | 0 | 200 | Queue length |
| APIM | Built-in | N/A | N/A | Azure-managed |
| Redis | Memory > 80% | 1 | 1 | Manual scale-up |

### Vertical Scaling

| Component | Dev SKU | Staging SKU | Prod SKU | Scale-Up Trigger |
|-----------|---------|-------------|----------|------------------|
| AKS Nodes | D2s_v3 | D4s_v3 | D4s_v3 → D8s_v3 | Sustained CPU > 80% |
| AI Search | Basic (1 unit) | Standard (1 unit) | Standard (3 units) | Query latency > 500ms |
| Cosmos DB | 400 RU/s | 1000 RU/s | Autoscale 4000 RU/s | Throttling (429s) |
| OpenAI | 50 TPM | 50 TPM | 100 TPM | Rate limit hits |

### Auto-Scale Rules (AKS)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

### Multi-Region Architecture

```
                    ┌──────────────────┐
                    │  Traffic Manager  │
                    │  (Priority)       │
                    └────────┬─────────┘
                             │
                   ┌─────────┼──────────┐
                   ▼                    ▼
          ┌────────────────┐   ┌────────────────┐
          │  East US       │   │  West US       │
          │  (Primary)     │   │  (Failover)    │
          │                │   │                │
          │  AKS           │   │  AKS           │
          │  OpenAI        │   │  OpenAI        │
          │  AI Search     │   │  AI Search     │
          │  Cosmos DB     │   │  Cosmos DB     │
          │  (Multi-write) │   │  (Multi-write) │
          └────────────────┘   └────────────────┘
                   │                    │
                   └────────┬───────────┘
                            │
                   ┌────────────────┐
                   │  GRS Storage   │
                   │  (Replicated)  │
                   └────────────────┘
```

| Component | Multi-Region Strategy | RPO | RTO |
|-----------|----------------------|-----|-----|
| AKS | Active-Passive (re-deploy) | 0 | 1 hour |
| Cosmos DB | Multi-region write | 0 | 0 (auto-failover) |
| Storage | GRS replication | < 15 min | 1 hour |
| AI Search | Index rebuild from Data Lake | 1 hour | 2 hours |
| OpenAI | Regional endpoint failover | N/A | < 5 min |

---

## Non-Functional Requirements

### Performance Requirements

| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|-----------------|
| Query Latency (P50) | < 2s | Application Insights | > 3s |
| Query Latency (P95) | < 5s | Application Insights | > 7s |
| Query Latency (P99) | < 10s | Application Insights | > 12s |
| Document Ingestion | < 30s per document | Custom metric | > 60s |
| Search Latency | < 500ms | AI Search metrics | > 800ms |
| Cache Hit Latency | < 5ms | Redis metrics | > 20ms |
| Embedding Generation | < 100ms per chunk | Custom metric | > 200ms |

### Availability Requirements

| Component | Target SLA | Measurement | DR Strategy |
|-----------|-----------|-------------|-------------|
| Overall Platform | 99.9% | Synthetic monitoring | Multi-zone + failover |
| API Gateway (APIM) | 99.95% | Azure SLA | Built-in HA |
| AKS Cluster | 99.95% | Azure SLA + health probes | Multi-zone |
| Azure OpenAI | 99.9% | Azure SLA | Regional failover |
| AI Search | 99.9% | Azure SLA | Index rebuild |
| Cosmos DB | 99.99% | Azure SLA | Multi-region |

### Reliability Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Idempotency** | All API operations are idempotent |
| **Retry Logic** | Exponential backoff with jitter (3 retries) |
| **Circuit Breaker** | Open after 5 consecutive failures, half-open after 30s |
| **Graceful Degradation** | Fallback to cached answer if OpenAI unavailable |
| **Health Checks** | Liveness + readiness probes on all services |
| **Dead Letter Queue** | Failed ingestion items queued for retry |

### Capacity Planning

| Resource | Current | 6-Month Projection | 12-Month Projection |
|----------|---------|--------------------|--------------------|
| Queries/day | 1,000 | 5,000 | 15,000 |
| Documents indexed | 10,000 | 50,000 | 200,000 |
| Storage (TB) | 0.5 | 2 | 5 |
| OpenAI tokens/month | 5M | 25M | 75M |
| Concurrent users | 50 | 200 | 500 |

---

## B2B Viewpoint

### Partner API Integration

```
Partner Application
        │
        ▼
┌────────────────────┐
│  APIM (B2B Tier)   │
│  • OAuth 2.0       │
│  • Rate: 500/min   │
│  • SLA: 99.9%      │
│  • API versioning   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Tenant Middleware  │
│  • Tenant context   │
│  • Quota check     │
│  • Billing meter   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  RAG Pipeline      │
│  (Tenant-scoped)   │
└────────────────────┘
```

### B2B SLA Tiers

| Tier | Rate Limit | Latency SLA | Availability | Support | Monthly Price |
|------|-----------|-------------|-------------|---------|---------------|
| **Bronze** | 100 req/min | P95 < 8s | 99.5% | Email (NBD) | $2,000 |
| **Silver** | 500 req/min | P95 < 5s | 99.9% | Email (4h) | $5,000 |
| **Gold** | 2000 req/min | P95 < 3s | 99.95% | Phone (1h) | $15,000 |

### Multi-Tenant Isolation (B2B)

| Isolation Layer | Implementation |
|-----------------|----------------|
| **Network** | Dedicated APIM subscription per partner |
| **Compute** | Shared AKS with namespace isolation |
| **Data** | Cosmos DB partition + AI Search filter by tenantId |
| **Storage** | Separate Data Lake container per tenant |
| **Encryption** | Customer-managed keys (CMK) optional per tenant |
| **Logging** | Tenant-scoped audit logs, accessible via API |

### API Versioning

```
/api/v1/chat      → Current stable
/api/v2/chat      → Next version (preview)
/api/v1/ingest    → Document ingestion
/api/v1/status    → Health and usage
```

---

## B2C Viewpoint

### Customer-Facing Chat Architecture

```
Customer (Browser / Mobile)
        │
        ▼
┌────────────────────┐
│  CDN + WAF         │
│  • DDoS protection │
│  • Bot detection   │
│  • Geo-filtering   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  APIM (B2C Tier)   │
│  • Anonymous or    │
│    Entra B2C auth  │
│  • Rate: 20/min    │
│    per session     │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Content Safety    │
│  • Input filter    │
│  • Output filter   │
│  • PII masking     │
│  • Language detect  │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  RAG Pipeline      │
│  (Public docs only)│
└────────────────────┘
```

### B2C-Specific Requirements

| Requirement | Implementation | Priority |
|-------------|----------------|----------|
| **Low Latency** | Edge caching, optimized prompts, GPT-4o-mini for simple queries | P0 |
| **Content Safety** | Azure Content Safety filters (block medium+) | P0 |
| **GDPR Compliance** | Consent management, data deletion API, no PII logging | P0 |
| **Multilingual** | Language detection + locale-specific responses | P1 |
| **Accessibility** | WCAG 2.1 AA for chat UI, screen reader support | P1 |
| **Session Management** | Stateless or short-lived sessions (24h max) | P1 |
| **Abuse Prevention** | Rate limiting, CAPTCHA, bot detection | P0 |

### GDPR Data Flow

```
User Consent → Collect Only Necessary Data → Process with PII Masking
                                                      │
                    ┌─────────────────────────────────┤
                    ▼                                  ▼
             Log (anonymized)                   Respond (PII-free)
                    │
                    ▼
             Auto-delete after 30 days
```

### B2C Content Safety Controls

| Control | Configuration | Rationale |
|---------|---------------|-----------|
| Hate speech filter | Block Low+ | Public-facing, zero tolerance |
| Sexual content filter | Block Low+ | Public-facing |
| Violence filter | Block Medium+ | Context-dependent |
| Self-harm filter | Block Low+ | Safety-critical |
| PII in output | Always mask | Regulatory requirement |
| Custom blocklist | Industry-specific terms | Brand safety |
| Response length | Max 500 tokens | Cost + readability |
| Topic guardrails | On-topic only (product/service) | Prevent misuse |

---

## B2E Viewpoint

### Internal Knowledge Copilot

```
Employee (Teams / Web Portal)
        │
        ▼
┌────────────────────┐
│  Copilot Studio    │
│  or Teams Bot      │
│  • SSO (Entra ID)  │
│  • Auto user context│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  APIM (B2E Tier)   │
│  • Entra ID auth   │
│  • Rate: 50/min    │
│    per user        │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Department Filter │
│  • User groups     │
│  • ACL trimming    │
│  • Department scope│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  RAG Pipeline      │
│  (ACL-scoped)      │
└────────────────────┘
```

### SSO Integration

```yaml
Entra ID Integration:
  Protocol: OpenID Connect
  Grant: Authorization Code + PKCE
  Scopes: openid, profile, email, Groups.Read
  Token: JWT with user groups claim

  User Context Extraction:
    - userId: from JWT sub claim
    - email: from JWT email claim
    - department: from directory extension attribute
    - groups: from JWT groups claim
    - manager: from Graph API (optional)
```

### Department-Level Access Control

| Department | Accessible Documents | Additional Access |
|------------|---------------------|-------------------|
| **HR** | HR policies, onboarding, benefits | Employee records (restricted) |
| **Legal** | Contracts, compliance, regulations | Privileged legal opinions |
| **Finance** | Financial policies, reporting guidelines | Audit reports |
| **Engineering** | Technical docs, architecture, runbooks | Source code docs |
| **Compliance** | Regulatory docs, AML/KYC policies | Examination reports |
| **All Employees** | Company handbook, IT policies, general FAQ | — |

### B2E Feature Matrix

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| **Contextual Answers** | RAG with ACL-trimmed retrieval | Only see authorized content |
| **Follow-up Questions** | Conversation memory (Cosmos DB) | Natural dialog flow |
| **Source Citations** | Document ID + page number | Verifiable answers |
| **Feedback Loop** | Thumbs up/down + comments | Continuous improvement |
| **Suggested Questions** | LLM-generated follow-ups | Discoverability |
| **Export to Email** | One-click share | Workflow integration |
| **Audit Trail** | All queries logged | Compliance |

---

## Cross-Cutting Concerns

### Shared Across All Viewpoints

| Concern | B2E | B2B | B2C |
|---------|-----|-----|-----|
| Authentication | Entra ID SSO | OAuth 2.0 client credentials | Entra B2C / anonymous |
| Rate Limiting | 50/min/user | Per SLA tier | 20/min/session |
| Content Safety | Standard | Configurable per tenant | Strictest |
| PII Handling | Mask in logs | Mask + tenant isolation | No PII stored |
| SLA | 99.9% | Per contract | 99.5% |
| Data Retention | 90 days | Per contract | 30 days |
| Support | L1 internal | Per SLA tier | Self-service + chatbot |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Architecture Team |
| Review | Quarterly |
