# Project 17: Knowledge Graph Builder

## Executive Summary

An enterprise-grade Knowledge Graph Builder platform that automates entity and relationship extraction from unstructured documents, constructs a traversable graph database, and powers graph-enhanced Retrieval-Augmented Generation (RAG) for superior contextual answers. The system leverages Azure OpenAI GPT-4o for entity extraction and natural language generation, Azure Cosmos DB Gremlin API for graph storage and traversal, Azure AI Search for hybrid vector retrieval, and Document Intelligence for document parsing. An ontology management layer allows domain experts to define and evolve entity schemas, relationship types, and validation rules without code changes.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE GRAPH BUILDER PLATFORM                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Graph Explorer│     │   Query Portal  │     │  Admin Console  │
│  (React/D3.js)  │     │  (React/Next)   │     │  (Ontology Mgmt)│
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
│  (Rate Limit,   │   │  (Frontend)     │   │  (Real-time     │
│   Auth, Cache)  │   │                 │   │   Graph Events) │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)              │
         │  │  ┌──────────────────────────────────────────────┐   │
         │  │  │         Application Subnet (10.0.1.0/24)     │   │
         ▼  │  │                                              │   │
┌───────────┴──┴──────┐                                       │   │
│  Azure Functions    │◄────────────────────────────────────┐ │   │
│  (Graph Orchestrator)│                                    │ │   │
│                     │    ┌─────────────────┐              │ │   │
│  - Entity Extractor │    │  Azure OpenAI   │              │ │   │
│  - Relation Builder │◄───┤  (GPT-4o)       │              │ │   │
│  - Graph Query Svc  │    │  Private Link   │              │ │   │
│  - RAG Orchestrator │    └─────────────────┘              │ │   │
│  - Ontology Manager │                                     │ │   │
└────────┬────────────┘                                     │ │   │
         │                                                  │ │   │
         │              ┌─────────────────┐                 │ │   │
         ├─────────────►│  Azure AI Search │◄───────────────┘ │   │
         │              │  (Vector Index)  │                  │   │
         │              │  - Hybrid Search │                  │   │
         │              │  - Semantic Rank │                  │   │
         │              └────────┬────────┘                  │   │
         │                       │                            │   │
         │  ┌────────────────────┼────────────────────────┐  │   │
         │  │         Data Subnet (10.0.2.0/24)           │  │   │
         │  │                    │                         │  │   │
         │  │    ┌───────────────┼───────────────────┐    │  │   │
         │  │    │               │                   │    │  │   │
         │  │    ▼               ▼                   ▼    │  │   │
         │  │ ┌──────────┐ ┌──────────┐       ┌────────┐ │  │   │
         │  │ │ Cosmos DB│ │   Blob   │       │ Redis  │ │  │   │
         │  │ │ Gremlin  │ │  Storage │       │ Cache  │ │  │   │
         │  │ │ (Graph)  │ │ (Docs)   │       │        │ │  │   │
         │  │ └──────────┘ └──────────┘       └────────┘ │  │   │
         │  └─────────────────────────────────────────────┘  │   │
         │                                                   │   │
         │  ┌─────────────────────────────────────────────┐  │   │
         │  │     Integration Subnet (10.0.3.0/24)        │  │   │
         │  │                                             │  │   │
         │  │  ┌─────────────┐   ┌─────────────────┐      │  │   │
         │  │  │  Key Vault  │   │ Document Intel. │      │  │   │
         │  │  │  (Secrets)  │   │ (OCR/Extract)   │      │  │   │
         │  │  └─────────────┘   └─────────────────┘      │  │   │
         │  │                                             │  │   │
         │  │  ┌─────────────┐   ┌─────────────────┐      │  │   │
         │  │  │ Data Factory│   │ Managed Identity│      │  │   │
         │  │  │ (ETL Pipes) │   │ (Auth Fabric)   │      │  │   │
         │  │  └─────────────┘   └─────────────────┘      │  │   │
         │  └─────────────────────────────────────────────┘  │   │
         └───────────────────────────────────────────────────┘   │
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │           DOCUMENT INGESTION & GRAPH BUILD PIPELINE          │
│   │                                                              │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐       │
│   │  │ SharePoint│    │  Email   │    │ Azure Blob       │       │
│   │  │ Connector │    │ Ingress  │    │ (Drop Zone)      │       │
│   │  └─────┬─────┘    └────┬─────┘    └────────┬─────────┘       │
│   │        │               │                    │                │
│   │        └───────────────┼────────────────────┘                │
│   │                        ▼                                     │
│   │              ┌─────────────────┐                             │
│   │              │  Event Grid     │                             │
│   │              │  (Blob Events)  │                             │
│   │              └────────┬────────┘                             │
│   │                       ▼                                      │
│   │              ┌─────────────────┐                             │
│   │              │ Durable Function │                            │
│   │              │ (Orchestrator)   │                            │
│   │              └────────┬────────┘                             │
│   │                       │                                      │
│   │        ┌──────────────┼──────────────────┐                   │
│   │        ▼              ▼                  ▼                   │
│   │  ┌──────────┐  ┌──────────────┐  ┌───────────────┐          │
│   │  │ Doc Intel│  │ GPT-4o NER  │  │ Ontology      │          │
│   │  │ (Parse)  │  │ (Entity +   │  │ Validator     │          │
│   │  │          │  │  Relations)  │  │ (Schema Check)│          │
│   │  └────┬─────┘  └──────┬───────┘  └───────┬───────┘          │
│   │       │               │                   │                  │
│   │       └───────────────┼───────────────────┘                  │
│   │                       ▼                                      │
│   │         ┌──────────────────────────┐                         │
│   │         │ Graph Writer (Gremlin)   │                         │
│   │         │ - Upsert Vertices        │                         │
│   │         │ - Upsert Edges           │                         │
│   │         │ - Update Embeddings      │                         │
│   │         └──────────────────────────┘                         │
│   └──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY LAYER                            │
│                                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor            │   │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)         │   │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘   │
│                                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │ Graph Stats │  │ Cost Mgmt  │  │ Defender for Cloud       │   │
│  │ Dashboard   │  │ Dashboard   │  │ (Security)               │   │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   ENTITY EXTRACTION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

Document Upload
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Blob       │────►│ 2. Event Grid │────►│ 3. Durable    │
│ Storage       │     │ Trigger       │     │ Function      │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                         ┌───────────────────────────┼──────────────────┐
                         │                           │                  │
                         ▼                           ▼                  ▼
                   ┌───────────┐           ┌──────────────┐    ┌──────────────┐
                   │ 4a. Doc   │           │ 4b. GPT-4o   │    │ 4c. Ontology │
                   │ Intelligence│          │ Entity/Rel   │    │ Schema Load  │
                   │ (Parse)    │           │ Extraction   │    │ (Validate)   │
                   └─────┬─────┘           └──────┬───────┘    └──────┬───────┘
                         │                        │                   │
                         └────────────────────────┼───────────────────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    │             │             │
                                    ▼             ▼             ▼
                              ┌──────────┐ ┌──────────┐ ┌──────────────┐
                              │ 5a. NER  │ │ 5b. Rel  │ │ 5c. Entity   │
                              │ Entities │ │ Triples  │ │ Coreference  │
                              │ (Person, │ │ (Subj,   │ │ Resolution   │
                              │  Org...) │ │  Pred,   │ │ (Dedup)      │
                              │          │ │  Obj)    │ │              │
                              └────┬─────┘ └────┬─────┘ └──────┬───────┘
                                   │            │              │
                                   └────────────┼──────────────┘
                                                │
                                                ▼
                                        ┌───────────────┐
                                        │ 6. Graph Write│
                                        │ Cosmos Gremlin│
                                        │ (Vertices +   │
                                        │  Edges)       │
                                        └───────┬───────┘
                                                │
                                  ┌─────────────┼─────────────┐
                                  ▼             ▼             ▼
                           ┌──────────┐  ┌──────────┐  ┌──────────┐
                           │ 7a. Index│  │ 7b. Cache│  │ 7c. Log  │
                           │ AI Search│  │ Invalidate│ │ Lineage  │
                           │ Vectors  │  │ Redis    │  │ Metadata │
                           └──────────┘  └──────────┘  └──────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                GRAPH-ENHANCED RAG QUERY FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

    User Query                                           Response
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 1. APIM Auth  │                                  │ 9. Format     │
│ (JWT/OAuth2)  │                                  │ Response +    │
│               │                                  │ Graph Viz     │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. Rate Limit │                                  │ 8. Generate   │
│ & Throttle    │                                  │ (GPT-4o)      │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Intent     │                                  │ 7. Augment    │
│ Detection +   │                                  │ Prompt with   │
│ Query Parse   │                                  │ Graph Context │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ├───────────────────────┐                           │
        ▼                       ▼                           │
┌───────────────┐      ┌───────────────┐           ┌───────────────┐
│ 4a. Embed     │      │ 4b. Entity    │           │ 6. Merge      │
│ Query         │      │ Recognition   │           │ Vector +      │
│ (ada-002)     │      │ in Query      │           │ Graph Results │
└───────┬───────┘      └───────┬───────┘           └───────┬───────┘
        │                       │                           │
        ▼                       ▼                    ┌──────┴──────┐
┌───────────────┐      ┌───────────────┐            │             │
│ 5a. Vector    │      │ 5b. Graph     │     ┌──────┴──┐  ┌───────┴──┐
│ Search        │      │ Traversal     │     │ Vector  │  │ Graph    │
│ (AI Search)   │      │ (Gremlin)     │     │ Chunks  │  │ Subgraph │
└───────────────┘      └───────────────┘     └─────────┘  └──────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Graph Explorer | React + D3.js/Cytoscape | Interactive graph visualization and exploration |
| Query Portal | React + TypeScript | Natural language query interface with graph context |
| Admin Console | React + TypeScript | Ontology management, schema editing, ingestion monitoring |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits | API management, authentication, usage analytics |
| SignalR | Serverless mode | Real-time graph update notifications |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Graph Orchestrator | Azure Functions (Python 3.11) | Entity extraction, graph query, RAG orchestration |
| Ingestion Pipeline | Durable Functions | Document processing and graph build orchestration |
| Entity Extractor | Azure Functions | NER using GPT-4o with ontology-guided prompts |
| Relation Builder | Azure Functions | Relationship triple extraction and validation |
| Ontology Manager | Azure Functions | CRUD operations on entity/relationship schemas |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Entity extraction, relationship inference, response generation |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for entities and document chunks |
| Document Intelligence | prebuilt-layout | OCR, table extraction, document structure parsing |
| AI Search | Semantic ranker | Hybrid vector + keyword search with reranking |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB (Gremlin API) | Dedicated 10K RU/s, auto-scale | Graph storage (vertices = entities, edges = relationships) |
| Azure Blob Storage | Hot tier, versioning enabled | Source document storage, extraction artifacts |
| Azure AI Search | S1 tier, 3 replicas | Vector index for entity embeddings and document chunks |
| Redis Cache | P1 Premium, 6GB | Graph traversal cache, query result cache, session state |

### 6. Integration Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Data Factory | Scheduled + event triggers | Batch ingestion pipelines, graph refresh jobs |
| Event Grid | System topic on Blob | Real-time document arrival triggers |
| Key Vault | RBAC, soft delete, purge protection | Secrets, connection strings, API keys |
| Managed Identity | System-assigned | Zero-credential service-to-service authentication |

### 7. Observability Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Application Insights | Workspace-based, sampling 50% | APM, dependency tracking, custom graph metrics |
| Log Analytics | 90-day retention | Centralized logging, KQL queries |
| Azure Monitor | Action groups, smart alerts | Infrastructure metrics, alert rules |
| Graph Dashboard | Custom workbook | Entity count, edge density, traversal latency |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                    │
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
│ │ Encryption  │  │ Key Vault   │  │ Graph ACL   │  │ Purview         │  │
│ │ at Rest/    │  │ (CMK)       │  │ (Vertex +   │  │ (Classification)│  │
│ │ Transit     │  │             │  │  Edge RBAC) │  │                 │  │
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
    resource_group: rg-knowledge-graph-dev
    location: eastus
    sku_tier: basic
    cosmos_db:
      throughput: 400 RU/s
      graph_name: kg-dev

  staging:
    subscription: staging-subscription
    resource_group: rg-knowledge-graph-stg
    location: eastus
    sku_tier: standard
    cosmos_db:
      throughput: 2000 RU/s
      graph_name: kg-stg

  production:
    subscription: prod-subscription
    resource_group: rg-knowledge-graph-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    cosmos_db:
      throughput: 10000 RU/s (auto-scale to 40000)
      graph_name: kg-prod
      multi_region_write: true

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  graph_migration:
    strategy: online-schema-evolution
    backward_compatible: true

ci_cd:
  pipeline: Azure DevOps / GitHub Actions
  stages:
    - lint_and_unit_test
    - integration_test (graph traversal assertions)
    - ontology_schema_validation
    - deploy_infrastructure (Terraform)
    - deploy_application (Functions)
    - smoke_test (entity extraction e2e)
    - graph_integrity_check
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go (extraction + generation) | ~$3,000-7,000 |
| Azure Cosmos DB (Gremlin) | Dedicated 10K RU/s, auto-scale | ~$800-1,500 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions | Premium EP2 (VNET integrated) | ~$300 |
| Document Intelligence | S0 (pay-per-page) | ~$200-500 |
| Blob Storage | Hot (2TB, versioning) | ~$40 |
| Redis Cache | P1 Premium (6GB) | ~$250 |
| Data Factory | Pay-as-you-go pipelines | ~$100 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Application Insights | Pay-as-you-go | ~$100 |
| Log Analytics | Pay-as-you-go (90-day) | ~$75 |
| Private Link | 6 endpoints | ~$45 |
| Azure Monitor | Alerts + Metrics | ~$30 |
| **Total Estimated** | | **~$6,000-11,000** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why a Knowledge Graph over flat vector-only RAG?**
   - Captures explicit relationships between entities (e.g., "Person X reports to Person Y at Company Z")
   - Enables multi-hop reasoning that vector similarity alone cannot achieve
   - Provides explainable paths: users see why two concepts are connected
   - Graph traversal surfaces indirect connections missed by embedding similarity

2. **Why Cosmos DB Gremlin API for graph storage?**
   - Fully managed, globally distributed graph database on Azure
   - Gremlin traversal language is expressive for complex path queries
   - Auto-scale RU/s handles variable ingestion and query workloads
   - Integrated Private Link for enterprise network isolation
   - Multi-region writes for disaster recovery scenarios

3. **Why combine Graph Traversal with Vector Search (Graph-Enhanced RAG)?**
   - Vector search retrieves semantically similar chunks (broad recall)
   - Graph traversal retrieves structurally related entities (precise context)
   - Merging both result sets gives GPT-4o richer context for generation
   - Reduces hallucination by grounding answers in verified graph relationships

4. **Why Ontology Management as a first-class feature?**
   - Domain experts define entity types, relationship schemas, and constraints
   - Extraction prompts are dynamically generated from the active ontology
   - Schema evolution is versioned -- old documents retain their extraction context
   - Validation layer ensures extracted entities conform to defined types

5. **Why Durable Functions for the ingestion pipeline?**
   - Long-running extraction (parse -> NER -> relation build -> graph write)
   - Built-in retry, checkpointing, and fan-out/fan-in patterns
   - Handles large document batches without timeout or memory issues
   - Orchestration state is persisted, enabling resume after failures

6. **Security Considerations**
   - All services behind Private Link (no public endpoints)
   - Managed Identity eliminates credential management across all services
   - Graph ACLs enforce vertex-level and edge-level access control
   - Content filtering in Azure OpenAI prevents prompt injection during extraction
   - Key Vault with CMK for encryption of graph data at rest

### Scalability Considerations

- Cosmos DB auto-scale from 10K to 40K RU/s handles ingestion bursts
- AI Search replicas scale read throughput for concurrent graph-enhanced queries
- Azure Functions Premium EP2 provides VNET integration with no cold starts
- Redis Cache reduces redundant graph traversals and embedding API calls
- Data Factory parallelizes batch ingestion across document partitions
- Entity coreference resolution prevents vertex explosion from duplicate entities

### Graph-Specific Design Patterns

- **Entity Coreference Resolution**: GPT-4o identifies when different mentions refer to the same entity, preventing duplicate vertices
- **Incremental Graph Updates**: New documents merge into the existing graph via upsert semantics, preserving historical edges
- **Graph Partitioning**: Vertices are partitioned by entity type in Cosmos DB for optimized traversal queries
- **Subgraph Extraction**: Query-time traversal returns only the relevant subgraph (2-3 hops), avoiding full graph scans
- **Ontology Versioning**: Schema changes are additive; breaking changes require a migration plan with backward compatibility

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Internal Knowledge Infrastructure)
- **Visibility:** Internal (Data & Research) — data scientists, researchers, and knowledge engineers
- **Project Score:** 7.5 / 10 (Elevated)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | Cosmos DB (Gremlin), OpenAI, Cognitive Search via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | Graph namespace-level access control |
| Data | Entity Access Control | Fine-grained permissions per entity type and relationship |
| Data | Traversal Limits | Query depth and breadth limits to prevent data exfiltration |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | Graph database credentials, encryption keys |
| Application | Query Governance | SPARQL/Gremlin query complexity limits |
| Application | Entity Validation | Schema validation for all entity CRUD operations |
| Monitoring | Traversal Audit | Graph traversal patterns logged and analyzed |
| Monitoring | Sentinel | Anomalous query pattern detection |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Ontology Governance | Committee-led | Ontology changes reviewed by data governance committee |
| Entity Lifecycle | Managed | Creation, update, deprecation, and deletion workflows |
| Relationship Integrity | Enforced | Referential integrity checks for all graph mutations |
| Schema Evolution | Versioned | Backward-compatible schema changes with migration plans |
| Data Quality | Monitored | Entity completeness and relationship accuracy scoring |
| Knowledge Curation | Workflow-based | SME review and approval for knowledge assertions |

### Regulatory Applicability
- **GDPR Article 17:** Right to erasure for personal entity data
- **CCPA:** Consumer data graph traversal and deletion capabilities
- **ISO 27001:** Information security for knowledge assets
- **Data Ethics:** Responsible entity linking and relationship inference
- **Internal Policy:** Intellectual property protection in knowledge graph
