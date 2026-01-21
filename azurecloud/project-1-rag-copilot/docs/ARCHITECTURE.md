# Project 1: Enterprise RAG Knowledge Copilot

## Executive Summary

An enterprise-grade Retrieval-Augmented Generation (RAG) system that enables employees to query company policies, SOPs, HR documents, and technical documentation using natural language. The system leverages Azure OpenAI GPT-4o for generation and Azure AI Search for semantic retrieval.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            ENTERPRISE RAG KNOWLEDGE COPILOT                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Portal    │     │   Teams Bot     │     │   Mobile App    │
│  (React/Next)   │     │  (Bot Service)  │     │   (React Native)│
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (Frontend)     │   │  (Real-time)    │
│   Auth, Cache)  │   │                 │   │                 │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)         │
         │  │  ┌─────────────────────────────────────────┐    │
         │  │  │         Application Subnet              │    │
         ▼  │  │         (10.0.1.0/24)                   │    │
┌───────────┴──┴───┐                                     │    │
│ Azure Functions  │◄──────────────────────────────────┐ │    │
│ (RAG Orchestrator)│                                  │ │    │
│                  │    ┌─────────────────┐            │ │    │
│ - Query Handler  │    │  Azure OpenAI   │            │ │    │
│ - Chat History   │◄───┤  (GPT-4o)       │            │ │    │
│ - Response Gen   │    │  Private Link   │            │ │    │
└────────┬─────────┘    └─────────────────┘            │ │    │
         │                                              │ │    │
         │              ┌─────────────────┐            │ │    │
         ├─────────────►│  Azure AI Search │◄──────────┘ │    │
         │              │  (Vector Index)  │             │    │
         │              │  - Hybrid Search │             │    │
         │              │  - Semantic Rank │             │    │
         │              └────────┬────────┘             │    │
         │                       │                       │    │
         │  ┌────────────────────┼────────────────────┐ │    │
         │  │         Data Subnet (10.0.2.0/24)       │ │    │
         │  │                    │                     │ │    │
         │  │    ┌───────────────┼───────────────┐    │ │    │
         │  │    │               │               │    │ │    │
         │  │    ▼               ▼               ▼    │ │    │
         │  │ ┌──────┐     ┌──────────┐    ┌───────┐ │ │    │
         │  │ │ Blob │     │ Cosmos DB│    │ Redis │ │ │    │
         │  │ │Store │     │(Sessions)│    │ Cache │ │ │    │
         │  │ └──────┘     └──────────┘    └───────┘ │ │    │
         │  └─────────────────────────────────────────┘ │    │
         │                                              │    │
         │  ┌─────────────────────────────────────────┐ │    │
         │  │     Integration Subnet (10.0.3.0/24)    │ │    │
         │  │                                         │ │    │
         │  │  ┌─────────────┐   ┌─────────────────┐  │ │    │
         │  │  │  Key Vault  │   │ Document Intel. │  │ │    │
         │  │  │  (Secrets)  │   │ (OCR/Extract)   │  │ │    │
         │  │  └─────────────┘   └─────────────────┘  │ │    │
         │  └─────────────────────────────────────────┘ │    │
         └──────────────────────────────────────────────┘    │
                                                              │
┌─────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────┐
│   │              DOCUMENT INGESTION PIPELINE                │
│   │                                                         │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│   │  │ SharePoint│    │ OneDrive │    │ Azure Blob       │  │
│   │  │ Connector │    │ Sync     │    │ (Drop Zone)      │  │
│   │  └─────┬─────┘    └────┬─────┘    └────────┬─────────┘  │
│   │        │               │                    │           │
│   │        └───────────────┼────────────────────┘           │
│   │                        ▼                                │
│   │              ┌─────────────────┐                        │
│   │              │  Event Grid     │                        │
│   │              │  (Blob Events)  │                        │
│   │              └────────┬────────┘                        │
│   │                       ▼                                 │
│   │              ┌─────────────────┐                        │
│   │              │ Durable Function │                       │
│   │              │ (Orchestrator)   │                       │
│   │              └────────┬────────┘                        │
│   │                       │                                 │
│   │        ┌──────────────┼──────────────┐                  │
│   │        ▼              ▼              ▼                  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐          │
│   │  │ Doc Intel│  │ Chunking │  │ Embedding    │          │
│   │  │ (OCR)    │  │ Service  │  │ (ada-002)    │          │
│   │  └──────────┘  └──────────┘  └──────────────┘          │
│   │                       │                                 │
│   │                       ▼                                 │
│   │              ┌─────────────────┐                        │
│   │              │ AI Search Index │                        │
│   │              │ (Vector Store)  │                        │
│   │              └─────────────────┘                        │
│   └─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                       │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor       │  │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Prompt Flow │  │ Cost Mgmt  │  │ Defender for Cloud  │  │
│  │ Tracing     │  │ Dashboard   │  │ (Security)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER QUERY FLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘

    User Query                                           Response
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 1. APIM Auth  │                                  │ 8. Format     │
│ (JWT/OAuth2)  │                                  │ Response      │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. Rate Limit │                                  │ 7. Generate   │
│ & Throttle    │                                  │ (GPT-4o)      │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Query      │──────────────────────────────────│ 6. Augment    │
│ Rewriting     │                                  │ Prompt        │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. Embed      │─────►│ 5. Vector     │─────────►│ Retrieved     │
│ Query         │      │ Search        │          │ Chunks        │
│ (ada-002)     │      │ (AI Search)   │          │               │
└───────────────┘      └───────────────┘          └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT INGESTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

Document Upload
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Blob       │────►│ 2. Event Grid │────►│ 3. Durable    │
│ Storage       │     │ Trigger       │     │ Function      │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                            ┌────────────────────────┼────────────────────┐
                            │                        │                    │
                            ▼                        ▼                    ▼
                      ┌───────────┐          ┌───────────┐        ┌───────────┐
                      │ 4a. OCR   │          │ 4b. Text  │        │ 4c. Meta  │
                      │ Extract   │          │ Extract   │        │ Extract   │
                      └─────┬─────┘          └─────┬─────┘        └─────┬─────┘
                            │                      │                    │
                            └──────────────────────┼────────────────────┘
                                                   │
                                                   ▼
                                            ┌───────────┐
                                            │ 5. Chunk  │
                                            │ Documents │
                                            └─────┬─────┘
                                                  │
                                                  ▼
                                            ┌───────────┐
                                            │ 6. Generate│
                                            │ Embeddings │
                                            └─────┬─────┘
                                                  │
                                                  ▼
                                            ┌───────────┐
                                            │ 7. Index  │
                                            │ in Search │
                                            └───────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Portal | React + TypeScript | Main user interface |
| Teams Integration | Bot Framework | Enterprise chat integration |
| Mobile App | React Native | On-the-go access |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits | API management, authentication |
| SignalR | Serverless mode | Real-time streaming responses |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| RAG Orchestrator | Azure Functions (Python 3.11) | Query processing, response generation |
| Ingestion Pipeline | Durable Functions | Document processing orchestration |
| Embedding Service | Azure Functions | Vector generation |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Response generation |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings |
| Document Intelligence | prebuilt-layout | OCR and document parsing |
| AI Search | Semantic ranker | Hybrid search + reranking |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Blob Storage | Hot tier, versioning | Document storage |
| Azure AI Search | S1 tier, 3 replicas | Vector index |
| Cosmos DB | Serverless | Chat history, sessions |
| Redis Cache | P1 Premium | Query cache, rate limiting |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete | Secrets management |
| Private Link | All PaaS services | Network isolation |
| Managed Identity | System-assigned | Service authentication |
| Entra ID | OAuth2/OIDC | User authentication |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (Allowed Regions│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time access)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ Data        │  │ Purview         │  │
│ │ at Rest/    │  │ (CMK)       │  │ Masking     │  │ (Classification)│  │
│ │ Transit     │  │             │  │             │  │                 │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain)│  │ Throttling  │  │ Filtering       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (Activity)  │  │ Manager         │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-rag-copilot-dev
    location: eastus
    sku_tier: basic

  staging:
    subscription: staging-subscription
    resource_group: rg-rag-copilot-stg
    location: eastus
    sku_tier: standard

  production:
    subscription: prod-subscription
    resource_group: rg-rag-copilot-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$2,000-5,000 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions | Premium EP1 | ~$200 |
| Cosmos DB | Serverless | ~$100 |
| Blob Storage | Hot (1TB) | ~$20 |
| Key Vault | Standard | ~$5 |
| APIM | Developer | ~$50 |
| Application Insights | Pay-as-you-go | ~$100 |
| **Total Estimated** | | **~$3,500-6,500** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why RAG over Fine-tuning?**
   - Lower cost, easier updates, no retraining needed
   - Better for frequently changing enterprise documents
   - Grounded responses with citations

2. **Why Hybrid Search?**
   - Combines BM25 keyword matching with vector similarity
   - Better recall for exact terms (product names, policy numbers)
   - Semantic understanding for natural language queries

3. **Why Durable Functions for Ingestion?**
   - Long-running document processing (OCR, chunking)
   - Built-in retry and checkpoint support
   - Fan-out/fan-in pattern for parallel processing

4. **Security Considerations**
   - All services behind Private Link (no public endpoints)
   - Managed Identity eliminates credential management
   - Content filtering in Azure OpenAI prevents misuse

### Scalability Considerations

- AI Search replicas for read scaling
- Function Premium plan for VNET integration + no cold starts
- Redis cache to reduce embedding API calls
- Cosmos DB auto-scaling for session management
