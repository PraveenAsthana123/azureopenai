# Project 23: Contact Center Knowledge Base

## Executive Summary

An AI-powered knowledge management system designed to support contact center agents and customers with intelligent, real-time access to organizational knowledge. The platform leverages Azure OpenAI GPT-4o for GenAI-powered article authoring, FAQ generation from call transcripts, and conversational self-service. Azure AI Search provides semantic and vector search for instant article retrieval during live calls and chats. The system includes knowledge gap detection from call transcript analysis, article versioning with approval workflows, multilingual support, content freshness scoring, and feedback-driven article ranking to continuously improve knowledge quality.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     CONTACT CENTER KNOWLEDGE BASE PLATFORM                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Agent Desktop  │     │  Self-Service   │     │  Author Portal  │
│  (React/Next)   │     │  Portal (Bot)   │     │  (React/Next)   │
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
│   APIM Gateway  │   │  Azure Bot     │   │  Azure SignalR  │
│  (Rate Limit,   │   │  Service       │   │  (Real-time     │
│   Auth, Cache)  │   │  (Self-Service)│   │   Suggestions)  │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
   ┌───────────────────────────┼──────────────────────────────────┐
   │              PRIVATE VNET (10.0.0.0/16)                      │
   │  ┌────────────────────────┼───────────────────────────────┐  │
   │  │         Application Subnet (10.0.1.0/24)               │  │
   │  │                        │                               │  │
   │  │  ┌─────────────────────▼──────────────────────────┐    │  │
   │  │  │          Azure Functions (Orchestrators)        │    │  │
   │  │  │                                                 │    │  │
   │  │  │  ┌──────────────┐  ┌──────────────────────┐    │    │  │
   │  │  │  │ Knowledge    │  │ Agent Assist         │    │    │  │
   │  │  │  │ Authoring    │  │ Suggestion Engine    │    │    │  │
   │  │  │  │ Service      │  │ (Real-time Lookup)   │    │    │  │
   │  │  │  └──────────────┘  └──────────────────────┘    │    │  │
   │  │  │  ┌──────────────┐  ┌──────────────────────┐    │    │  │
   │  │  │  │ Knowledge    │  │ FAQ Generation       │    │    │  │
   │  │  │  │ Gap Detector │  │ Service              │    │    │  │
   │  │  │  └──────────────┘  └──────────────────────┘    │    │  │
   │  │  │  ┌──────────────┐  ┌──────────────────────┐    │    │  │
   │  │  │  │ Feedback &   │  │ Content Freshness    │    │    │  │
   │  │  │  │ Ranking Svc  │  │ Scoring Engine       │    │    │  │
   │  │  │  └──────────────┘  └──────────────────────┘    │    │  │
   │  │  └─────────────────────────────────────────────────┘    │  │
   │  │                        │                               │  │
   │  │         ┌──────────────┼──────────────┐                │  │
   │  │         ▼              ▼              ▼                │  │
   │  │  ┌─────────────┐ ┌──────────┐ ┌──────────────────┐    │  │
   │  │  │ Azure OpenAI│ │ Azure AI │ │ Azure Speech     │    │  │
   │  │  │ (GPT-4o +   │ │ Search   │ │ Services         │    │  │
   │  │  │  ada-002)   │ │ (Semantic│ │ (Transcript      │    │  │
   │  │  │ Private Link│ │ +Vector) │ │  Processing)     │    │  │
   │  │  └─────────────┘ └──────────┘ └──────────────────┘    │  │
   │  └────────────────────────────────────────────────────────┘  │
   │                                                              │
   │  ┌────────────────────────────────────────────────────────┐  │
   │  │         Data Subnet (10.0.2.0/24)                      │  │
   │  │                                                        │  │
   │  │  ┌──────────┐  ┌──────────┐  ┌───────┐  ┌──────────┐  │  │
   │  │  │ Cosmos DB│  │  Blob    │  │ Redis │  │ Event    │  │  │
   │  │  │(Articles,│  │  Storage │  │ Cache │  │ Grid     │  │  │
   │  │  │ Versions,│  │(Transcr.,│  │(Search│  │(Article  │  │  │
   │  │  │ Feedback)│  │ Media)   │  │ Cache)│  │ Events)  │  │  │
   │  │  └──────────┘  └──────────┘  └───────┘  └──────────┘  │  │
   │  └────────────────────────────────────────────────────────┘  │
   │                                                              │
   │  ┌────────────────────────────────────────────────────────┐  │
   │  │     Integration Subnet (10.0.3.0/24)                   │  │
   │  │                                                        │  │
   │  │  ┌─────────────┐   ┌─────────────────┐                │  │
   │  │  │  Key Vault  │   │ Managed Identity│                │  │
   │  │  │  (Secrets)  │   │ (Auth)          │                │  │
   │  │  └─────────────┘   └─────────────────┘                │  │
   │  └────────────────────────────────────────────────────────┘  │
   └──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│               TRANSCRIPT INGESTION PIPELINE                      │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │ Call Record- │   │ Chat Logs    │   │ Azure Blob           │  │
│  │ ings (Audio) │   │ (Text)       │   │ (Drop Zone)          │  │
│  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘  │
│         │                  │                      │              │
│         └──────────────────┼──────────────────────┘              │
│                            ▼                                     │
│                  ┌─────────────────┐                              │
│                  │  Event Grid     │                              │
│                  │  (Blob Events)  │                              │
│                  └────────┬────────┘                              │
│                           ▼                                      │
│                  ┌─────────────────┐                              │
│                  │ Durable Function│                              │
│                  │ (Orchestrator)  │                              │
│                  └────────┬────────┘                              │
│                           │                                      │
│            ┌──────────────┼──────────────┐                       │
│            ▼              ▼              ▼                        │
│      ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│      │ Speech   │  │ Topic    │  │ Embedding    │               │
│      │ to Text  │  │ Extract  │  │ (ada-002)    │               │
│      │ (Speech) │  │ (GPT-4o) │  │              │               │
│      └──────────┘  └──────────┘  └──────────────┘               │
│                           │                                      │
│                           ▼                                      │
│                  ┌─────────────────┐                              │
│                  │ AI Search Index │                              │
│                  │ + Cosmos DB     │                              │
│                  └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                            │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor           │  │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Prompt Flow │  │ Cost Mgmt  │  │ Defender for Cloud       │  │
│  │ Tracing     │  │ Dashboard   │  │ (Security)              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│              KNOWLEDGE ARTICLE AUTHORING FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

    Author Input (Topic/Outline)                  Published Article
        │                                              ▲
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 1. Entra ID   │                              │ 8. Publish &  │
│ Auth (RBAC)   │                              │ Index Article │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 2. APIM       │                              │ 7. Approval   │
│ Validation    │                              │ Workflow      │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 3. GenAI Draft│──────────────────────────────│ 6. Version    │
│ Generation    │                              │ Control       │
│ (GPT-4o)      │                              │ (Cosmos DB)   │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐     ┌───────────────┐        ┌───────────────┐
│ 4. Semantic   │────►│ 5. Duplicate  │───────►│ Author Review │
│ Embedding     │     │ & Gap Check   │        │ & Edit        │
│ (ada-002)     │     │ (AI Search)   │        │               │
└───────────────┘     └───────────────┘        └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│           AGENT-ASSIST KNOWLEDGE RETRIEVAL FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

    Live Call/Chat Context                      Suggested Articles
        │                                              ▲
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 1. SignalR    │                              │ 7. Rank &     │
│ Real-time     │                              │ Return Top-K  │
│ Stream        │                              │ (Feedback Wt) │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 2. Speech to  │                              │ 6. Freshness  │
│ Text (if call)│                              │ Score Filter  │
│ (Speech Svc)  │                              │               │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐      ┌───────────────┐       ┌───────────────┐
│ 3. Intent &   │─────►│ 4. Embed      │──────►│ 5. Hybrid     │
│ Entity Extract│      │ Query         │       │ Search        │
│ (GPT-4o)      │      │ (ada-002)     │       │ (AI Search)   │
└───────────────┘      └───────────────┘       └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│              KNOWLEDGE GAP DETECTION FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

    Call Transcripts (Batch)                    Gap Report + Draft Articles
        │                                              ▲
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 1. Blob       │                              │ 7. Notify     │
│ Storage       │                              │ Authors via   │
│ (Transcript)  │                              │ Event Grid    │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 2. Event Grid │                              │ 6. GenAI Draft│
│ Trigger       │                              │ Suggestion    │
└───────┬───────┘                              │ (GPT-4o)      │
        │                                      └───────┬───────┘
        ▼                                              │
┌───────────────┐      ┌───────────────┐       ┌───────────────┐
│ 3. Speech to  │─────►│ 4. Topic &    │──────►│ 5. Compare vs │
│ Text (Audio)  │      │ Question      │       │ Existing KB   │
│ (Speech Svc)  │      │ Extraction    │       │ (AI Search)   │
└───────────────┘      └───────────────┘       └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent Desktop | React + TypeScript | Live call/chat interface with article suggestions sidebar |
| Self-Service Portal | Azure Bot Service + React | Customer-facing conversational AI for knowledge lookup |
| Author Portal | React + TypeScript | Article authoring, versioning, and approval management |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits | API management, authentication, throttling |
| Azure SignalR | Serverless mode | Real-time article suggestions pushed to agent desktop |
| Azure Bot Service | DirectLine + WebChat | Conversational self-service channel |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Knowledge Authoring Service | Azure Functions (Python 3.11) | GenAI-assisted article drafting and editing |
| Agent Assist Suggestion Engine | Azure Functions (Python 3.11) | Real-time article retrieval during live interactions |
| Knowledge Gap Detector | Durable Functions | Batch transcript analysis to find missing knowledge |
| FAQ Generation Service | Azure Functions (Python 3.11) | Auto-generate FAQs from call transcript patterns |
| Feedback & Ranking Service | Azure Functions (Python 3.11) | Collect agent feedback, compute article rankings |
| Content Freshness Scoring Engine | Azure Functions (Python 3.11) | Score articles by age, usage, feedback, and accuracy |
| Approval Workflow Orchestrator | Durable Functions | Multi-step article review and publish pipeline |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Article generation, FAQ synthesis, intent extraction |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for semantic search |
| Azure AI Search | Semantic ranker + vector index | Hybrid search with semantic reranking |
| Azure Speech Services | speech-to-text (whisper) | Call recording transcription |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Serverless, multi-partition | Articles, versions, feedback, approval state |
| Azure Blob Storage | Hot tier, versioning | Call recordings, transcripts, media attachments |
| Azure AI Search | S1 tier, 3 replicas | Vector + keyword index for knowledge articles |
| Redis Cache | P1 Premium | Search result caching, session state, frequent queries |
| Event Grid | System topics | Article lifecycle events, transcript arrival triggers |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protection | Secrets and certificate management |
| Private Link | All PaaS services | Network isolation for data plane |
| Managed Identity | System-assigned | Zero-credential service-to-service auth |
| Entra ID | OAuth2/OIDC, RBAC roles | User authentication and role-based access |

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
│ │ Transit     │  │             │  │ (PII in     │  │                 │  │
│ │ (TLS 1.2+) │  │             │  │ Transcripts)│  │                 │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Author vs  │  │ Throttling  │  │ Filtering       │  │
│ │             │  │  Agent vs   │  │ (APIM)      │  │ (Azure OpenAI)  │  │
│ │             │  │  Customer)  │  │             │  │                 │  │
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
    resource_group: rg-kb-contact-center-dev
    location: eastus
    sku_tier: basic
    features:
      - single_region
      - basic_search (free tier)
      - shared_openai_quota

  staging:
    subscription: staging-subscription
    resource_group: rg-kb-contact-center-stg
    location: eastus
    sku_tier: standard
    features:
      - single_region
      - standard_search (S1)
      - dedicated_openai_quota

  production:
    subscription: prod-subscription
    resource_group: rg-kb-contact-center-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    features:
      - multi_region
      - ha_search (S1, 3 replicas)
      - premium_redis
      - private_link_all_services
      - cosmos_db_multi_region_writes

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  smoke_tests:
    - knowledge_search_latency_p95 < 500ms
    - article_authoring_endpoint_healthy
    - bot_service_channel_active
    - speech_transcription_functional
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$3,000-7,000 |
| Azure OpenAI (ada-002 embeddings) | Pay-as-you-go | ~$200-500 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions (Orchestrators) | Premium EP1 | ~$250 |
| Azure Bot Service | S1 Standard | ~$500 |
| Azure Speech Services | Pay-as-you-go | ~$300-800 |
| Cosmos DB | Serverless | ~$150 |
| Blob Storage | Hot (2TB) | ~$40 |
| Redis Cache | P1 Premium | ~$250 |
| Azure SignalR | Standard (1 unit) | ~$50 |
| Event Grid | Pay-per-event | ~$10 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Application Insights | Pay-as-you-go | ~$100 |
| Log Analytics | Pay-as-you-go | ~$75 |
| Azure Monitor | Alerts + Dashboards | ~$30 |
| Private Link | Per endpoint (8) | ~$60 |
| **Total Estimated** | | **~$6,000-10,500** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why Azure AI Search with Hybrid (Semantic + Vector) Search?**
   - Contact center queries range from exact product names to vague customer descriptions
   - Hybrid search combines BM25 keyword matching with vector similarity for best recall
   - Semantic ranker reranks results using cross-encoder for precision
   - Redis caching reduces latency for frequently asked questions during peak call volume

2. **Why Real-time Article Suggestions via SignalR?**
   - Agents need article suggestions pushed instantly as call context evolves
   - SignalR provides low-latency bidirectional communication without polling
   - Speech Services transcribes live calls; GPT-4o extracts intent in near real-time
   - Suggestions update as the conversation progresses, not just at query time

3. **Why GenAI-Powered Article Authoring?**
   - Subject matter experts spend less time drafting; GPT-4o generates initial drafts from outlines
   - Duplicate detection via embedding similarity prevents redundant articles
   - Multilingual support through GPT-4o translation reduces localization effort
   - Approval workflows in Durable Functions enforce governance before publishing

4. **Why Knowledge Gap Detection from Transcripts?**
   - Call transcripts reveal questions agents could not answer from existing KB
   - Batch processing via Durable Functions analyzes transcript topics at scale
   - Comparison against AI Search index identifies missing or outdated content
   - Auto-generated draft articles accelerate gap closure

5. **Why Content Freshness Scoring?**
   - Stale articles cause agents to provide incorrect information
   - Scoring algorithm weighs article age, edit frequency, usage rate, and negative feedback
   - Low-scoring articles surface in author dashboards for review
   - Ensures continuous knowledge quality improvement

6. **Why Cosmos DB for Article Storage?**
   - Native versioning support through partition key design (articleId + version)
   - Serverless mode handles bursty authoring workloads cost-effectively
   - Change feed powers real-time indexing into AI Search
   - Multi-region writes for DR in production deployment

7. **Security Considerations**
   - All services behind Private Link with no public endpoints
   - Managed Identity eliminates credential management across all services
   - PII masking in transcripts before storage using Azure AI content safety
   - RBAC separates author, agent, and customer access levels via Entra ID
   - Content filtering in Azure OpenAI prevents misuse of generative capabilities

### Scalability Considerations

- AI Search replicas scale read throughput for peak call center hours
- Azure Functions Premium plan provides VNET integration and zero cold starts
- Redis Cache reduces embedding API calls for repeated queries
- Cosmos DB auto-scales RU/s based on traffic patterns
- Event Grid decouples transcript ingestion from processing for burst handling
- SignalR scales to thousands of concurrent agent connections
- Bot Service handles concurrent self-service sessions independently

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Agent Desktop + Self-Service)
- **Visibility:** Agent Desktop + Self-Service — internal agents and customer-facing self-service portal
- **Project Score:** 8.0 / 10 (High)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Private Link | All PaaS services via private endpoints |
| Network | VNET Isolation | 3-subnet topology (App/Data/Integration) |
| Identity | Content Authorization | RBAC-based article access (Author, Agent, Customer roles) |
| Identity | RBAC | Entra ID role separation for authoring, review, and consumption |
| Data | Bot Authentication | Secure DirectLine token for self-service bot channel |
| Data | PII Masking | Automated PII redaction in call transcripts before storage |
| Data | Encryption | AES-256 at rest, TLS 1.2+ in transit, CMK via Key Vault |
| Application | Content Filtering | Azure OpenAI responsible AI filters for article generation |
| Application | Approval Workflow | Multi-step article review before publishing to knowledge base |
| Monitoring | Audit Logs | Article lifecycle events tracked (create, edit, publish, archive) |
| Monitoring | Defender for Cloud | Continuous security posture assessment |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Article Lifecycle | Governed | Draft → Review → Approve → Publish → Archive workflow |
| SME Review | Required | Subject matter expert sign-off before article publication |
| Version Control | Enforced | Full article version history with rollback capability |
| Content Accuracy | Monitored | Freshness scoring and periodic content review cycles |
| Data Privacy | Enforced | PII scrubbed from transcripts used for knowledge gap analysis |
| Access Control | RBAC | Tiered access: Author (edit), Agent (read), Customer (filtered) |

### Regulatory Applicability
- **Internal Governance:** Article lifecycle management and SME review workflows
- **Data Privacy:** PII protection in transcript-derived knowledge articles
- **Accessibility:** WCAG 2.1 AA compliance for self-service knowledge portal
- **Content Accuracy:** Regulatory content requires mandatory review cycles
- **Audit Trail:** Complete article change history for compliance review
