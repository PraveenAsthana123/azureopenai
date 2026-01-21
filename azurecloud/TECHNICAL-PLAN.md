# Enterprise GenAI Knowledge Copilot Platform - Technical Plan

## Executive Summary

This document outlines the complete technical implementation plan for deploying an enterprise-grade AI-powered knowledge copilot platform on Microsoft Azure. The platform enables intelligent document search, RAG (Retrieval-Augmented Generation), and AI-powered assistance using Azure OpenAI, Azure AI Search, and multiple LLM providers.

---

## 1. Project Overview

### 1.1 Vision
Build a scalable, secure, enterprise knowledge assistant that can:
- Ingest and process enterprise documents (PDF, Word, images)
- Provide AI-powered search with source citations
- Support multiple deployment modes (cloud and desktop/offline)
- Integrate with enterprise authentication (Azure AD/Entra ID)

### 1.2 Key Features
| Feature | Description |
|---------|-------------|
| Hybrid Search | Vector + keyword search for best results |
| RAG Pipeline | Grounded responses with source citations |
| Multi-LLM Support | Azure OpenAI, Ollama (local), Anthropic, OpenAI |
| Document Processing | OCR, chunking, embedding generation |
| Enterprise Security | Private endpoints, RBAC, Key Vault |
| Offline Mode | Desktop deployment with local LLM (Ollama) |

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │   Web Frontend   │  │  Desktop App     │  │   API Clients    │       │
│  │   (React + TS)   │  │  (Python/Local)  │  │   (REST/SDK)     │       │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘       │
└───────────┼─────────────────────┼─────────────────────┼─────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Azure Functions (Serverless)                     │   │
│  │  • API Gateway Function - Request routing, auth validation        │   │
│  │  • Rate limiting, request validation                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PROCESSING LAYER                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │  Orchestrator  │  │   RAG Engine   │  │   Ingestion    │             │
│  │   Function     │  │   Function     │  │   Function     │             │
│  │                │  │                │  │                │             │
│  │  • Workflow    │  │  • Query       │  │  • Document    │             │
│  │    coordination│  │    processing  │  │    upload      │             │
│  │  • Session     │  │  • Context     │  │  • Chunking    │             │
│  │    management  │  │    building    │  │  • Embedding   │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI SERVICES LAYER                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │  Azure OpenAI  │  │  Azure AI      │  │  Document      │             │
│  │                │  │  Search        │  │  Intelligence  │             │
│  │  • GPT-4o      │  │                │  │                │             │
│  │  • GPT-4o-mini │  │  • Vector      │  │  • OCR         │             │
│  │  • Embeddings  │  │    indexing    │  │  • Layout      │             │
│  │    (ada-3)     │  │  • Semantic    │  │    analysis    │             │
│  │                │  │    search      │  │                │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │   Cosmos DB    │  │  Blob Storage  │  │   Key Vault    │             │
│  │                │  │                │  │                │             │
│  │  • Conversations│ │  • Documents   │  │  • API Keys    │             │
│  │  • User sessions│ │  • Embeddings  │  │  • Connection  │             │
│  │  • Audit logs  │  │  • Cache       │  │    strings     │             │
│  │  • Metadata    │  │                │  │                │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AZURE VIRTUAL NETWORK                               │
│                       (10.0.0.0/16)                                      │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  VM Subnet       │  │  Functions       │  │  Private         │       │
│  │  10.0.1.0/24     │  │  Subnet          │  │  Endpoints       │       │
│  │                  │  │  10.0.2.0/24     │  │  10.0.3.0/24     │       │
│  │  • Backend VMs   │  │  • Function Apps │  │  • OpenAI PE     │       │
│  │  • Frontend VMs  │  │  • VNet          │  │  • Search PE     │       │
│  │                  │  │    Integration   │  │  • Cosmos PE     │       │
│  └──────────────────┘  └──────────────────┘  │  • Storage PE    │       │
│                                              │  • KeyVault PE   │       │
│  ┌──────────────────┐                        └──────────────────┘       │
│  │  Bastion Subnet  │                                                    │
│  │  10.0.255.0/26   │  ← Secure VM access (no public IPs)               │
│  └──────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### 3.1 Infrastructure (Terraform)
| Component | Technology | Purpose |
|-----------|------------|---------|
| IaC | Terraform 1.5+ | Infrastructure provisioning |
| State | Azure Storage | Remote state management |
| Modules | Custom | Reusable resource modules |

### 3.2 Backend Services
| Service | Technology | Purpose |
|---------|------------|---------|
| API Gateway | Azure Functions (Python) | Request routing, auth |
| Orchestrator | Azure Functions (Python) | Workflow coordination |
| RAG Processor | Azure Functions (Python) | Query + generation |
| Ingestion | Azure Functions (Python) | Document processing |

### 3.3 AI/ML Services
| Service | Model/SKU | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o, GPT-4o-mini | Chat completions |
| Azure OpenAI | text-embedding-3-large | Embeddings (3072 dims) |
| Azure AI Search | Standard S1 | Vector + semantic search |
| Document Intelligence | S0 | OCR, layout analysis |
| Computer Vision | S1 | Image analysis |
| Content Safety | S0 | Content moderation |

### 3.4 Data Services
| Service | SKU | Purpose |
|---------|-----|---------|
| Cosmos DB | Serverless | Conversations, metadata |
| Blob Storage | Standard LRS | Document storage |
| Key Vault | Standard | Secrets management |

### 3.5 Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18+ | UI framework |
| TypeScript | 5+ | Type safety |
| Vite | 5+ | Build tool |
| TailwindCSS | 3+ | Styling |

---

## 4. Implementation Phases

### Phase 1: Infrastructure Foundation (Week 1-2)

#### 4.1.1 Prerequisites
- [ ] Azure subscription with Owner access
- [ ] Request Azure OpenAI access: https://aka.ms/oai/access
- [ ] Request VM quota increase in West US 2 (if needed)
- [ ] Install tools: Azure CLI, Terraform, Python 3.11+, Node.js 20+

#### 4.1.2 Terraform Setup
```bash
# Initialize backend storage
az group create -n tfstate-rg -l westus2
az storage account create -n tfstategenai -g tfstate-rg -l westus2 --sku Standard_LRS
az storage container create -n tfstate --account-name tfstategenai

# Deploy infrastructure
cd infrastructure/terraform
terraform init -backend-config=backend.tfvars
terraform plan -out=tfplan
terraform apply tfplan
```

#### 4.1.3 Resources Created
| Module | Resources |
|--------|-----------|
| networking | VNet, Subnets, NSGs, Bastion, Private DNS Zones |
| storage | Storage Accounts, Containers |
| database | Cosmos DB Account, Database, Containers |
| ai-services | OpenAI, AI Search, Document Intelligence, etc. |
| compute | VMs, Function Apps, Service Plans |
| monitoring | Log Analytics, App Insights, Key Vault, Alerts |

### Phase 2: AI Services Configuration (Week 2-3)

#### 4.2.1 Azure OpenAI Setup
```bash
# Deploy models (after quota approval)
# In main.tf, set: deploy_openai = true

# Model deployments configured in terraform:
# - gpt-4o (100K TPM)
# - gpt-4o-mini (500K TPM)
# - text-embedding-3-large (350K TPM)
```

#### 4.2.2 Azure AI Search Index
```json
{
  "name": "rag-multimodal-index",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true},
    {"name": "content_text", "type": "Edm.String", "searchable": true},
    {"name": "content_vector", "type": "Collection(Edm.Single)",
     "dimensions": 3072, "vectorSearchProfile": "default"},
    {"name": "title", "type": "Edm.String", "searchable": true},
    {"name": "metadata", "type": "Edm.ComplexType"},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": true}
  ],
  "vectorSearch": {
    "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
    "profiles": [{"name": "default", "algorithm": "hnsw"}]
  },
  "semantic": {
    "configurations": [{
      "name": "default",
      "prioritizedFields": {
        "contentFields": [{"fieldName": "content_text"}],
        "titleField": {"fieldName": "title"}
      }
    }]
  }
}
```

### Phase 3: Backend Development (Week 3-5)

#### 4.3.1 Azure Functions Structure
```
backend/azure-functions/
├── api-gateway/
│   ├── __init__.py
│   ├── function.json
│   └── requirements.txt
├── orchestrator/
│   ├── __init__.py
│   ├── function.json
│   └── requirements.txt
├── rag-processor/
│   ├── chat/
│   │   ├── __init__.py      # RAG chat endpoint
│   │   └── function.json
│   ├── search/
│   │   ├── __init__.py      # Direct search endpoint
│   │   └── function.json
│   └── requirements.txt
├── ingestion/
│   ├── upload/
│   │   ├── __init__.py      # Document upload
│   │   └── function.json
│   ├── process/
│   │   ├── __init__.py      # Blob trigger for processing
│   │   └── function.json
│   └── requirements.txt
└── host.json
```

#### 4.3.2 Key API Endpoints
| Endpoint | Method | Function | Description |
|----------|--------|----------|-------------|
| /api/chat | POST | rag-processor | RAG chat with sources |
| /api/search | POST | rag-processor | Direct vector search |
| /api/documents | POST | ingestion | Upload document |
| /api/documents | GET | orchestrator | List documents |
| /api/sessions | GET/POST | orchestrator | Manage sessions |
| /api/health | GET | api-gateway | Health check |

### Phase 4: Document Ingestion Pipeline (Week 4-5)

#### 4.4.1 Pipeline Flow
```
Document Upload → Blob Storage → Trigger Function
                                        │
                                        ▼
                              Document Intelligence
                              (OCR + Layout Analysis)
                                        │
                                        ▼
                              Text Chunking
                              (1000 chars, 200 overlap)
                                        │
                                        ▼
                              Embedding Generation
                              (Azure OpenAI)
                                        │
                                        ▼
                              Azure AI Search Index
                                        │
                                        ▼
                              Cosmos DB Metadata
```

#### 4.4.2 Chunking Strategy
```python
def chunk_document(text: str, chunk_size: int = 1000, overlap: int = 200):
    """
    Chunk document with overlap for context preservation.

    - chunk_size: 1000 characters (optimal for embedding models)
    - overlap: 200 characters (20% overlap)
    - Boundary: Prefer sentence/paragraph boundaries
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Find sentence boundary
        if end < len(text):
            for boundary in ['. ', '\n\n', '\n', ' ']:
                idx = text.rfind(boundary, start, end)
                if idx > start:
                    end = idx + len(boundary)
                    break
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
```

### Phase 5: Frontend Development (Week 5-6)

#### 4.5.1 Component Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── SourceCard.tsx
│   │   ├── Search/
│   │   │   ├── SearchBar.tsx
│   │   │   └── SearchResults.tsx
│   │   ├── Documents/
│   │   │   ├── DocumentList.tsx
│   │   │   └── UploadModal.tsx
│   │   └── Layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useSearch.ts
│   │   └── useAuth.ts
│   ├── services/
│   │   ├── api.ts
│   │   └── auth.ts
│   ├── store/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

### Phase 6: Security Implementation (Week 6-7)

#### 4.6.1 Authentication Flow
```
User → Azure AD Login → ID Token
           │
           ▼
    Function App (EasyAuth)
           │
           ▼
    Validate Token + Extract Claims
           │
           ▼
    RBAC Check → Access Resource
```

#### 4.6.2 Security Checklist
- [ ] All services use private endpoints
- [ ] No public IP addresses on VMs
- [ ] Key Vault for all secrets
- [ ] Managed Identity for service-to-service auth
- [ ] Network Security Groups configured
- [ ] Azure AD authentication required
- [ ] CORS policies configured
- [ ] Rate limiting enabled

### Phase 7: CI/CD Setup (Week 7-8)

#### 4.7.1 Pipeline Structure
```yaml
# azure-devops/pipelines/main-pipeline.yml
trigger:
  branches:
    include:
      - main
      - develop

stages:
  - stage: Build
    jobs:
      - job: BuildFunctions
        steps:
          - task: UsePythonVersion@0
          - script: pip install -r requirements.txt
          - task: ArchiveFiles@2

      - job: BuildFrontend
        steps:
          - task: NodeTool@0
          - script: npm ci && npm run build
          - task: PublishBuildArtifacts@1

  - stage: DeployDev
    condition: eq(variables['Build.SourceBranch'], 'refs/heads/develop')
    jobs:
      - deployment: DeployToDev
        environment: development
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureFunctionApp@1
                - task: AzureCLI@2

  - stage: DeployProd
    condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')
    jobs:
      - deployment: DeployToProd
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureFunctionApp@1
```

---

## 5. Cost Estimation

### 5.1 Development Environment (~$400-500/month)

| Resource | SKU | Est. Cost |
|----------|-----|-----------|
| Azure AI Search | Standard S1 | $250 |
| Azure Bastion | Basic | $140 |
| Cosmos DB | Serverless | $25 |
| Storage | Standard LRS | $10 |
| Key Vault | Standard | $5 |
| Log Analytics | Pay-per-GB | $10 |
| App Insights | Free tier | $0 |
| **Subtotal (No OpenAI/Functions)** | | **~$440** |

### 5.2 Full Production (~$800-1200/month)

| Resource | SKU | Est. Cost |
|----------|-----|-----------|
| Azure OpenAI | Pay-per-use | $100-300 |
| Azure AI Search | Standard S1 | $250 |
| Azure Functions (Premium) | EP1 x 2 | $220 |
| Azure Functions (Consumption) | Y1 | $20 |
| VMs | D2s_v3 x 1 | $70 |
| Cosmos DB | Serverless | $50 |
| Azure Bastion | Basic | $140 |
| Storage | Standard LRS | $20 |
| Key Vault | Standard | $5 |
| Monitoring | Combined | $25 |
| **Total** | | **~$900-1100** |

---

## 6. Deployment Commands

### 6.1 Quick Start
```bash
# 1. Deploy infrastructure
cd infrastructure/terraform
./deploy.sh deploy

# 2. Deploy functions (after quota approval)
cd backend/azure-functions
func azure functionapp publish func-api-genai-copilot-<suffix>

# 3. Setup search index
az search admin-key show --service-name search-genai-copilot-dev-<suffix> -g rg-genai-copilot-dev-wus2
# Use key to configure index via REST API or SDK

# 4. Deploy frontend
cd frontend
npm run build
az storage blob upload-batch -d '$web' -s dist --account-name <storage>
```

### 6.2 Destroy Resources
```bash
cd infrastructure/terraform
./deploy.sh destroy
```

---

## 7. Desktop/Offline Mode

### 7.1 Architecture
```
Desktop App (Python)
       │
       ├── Ollama (Local LLM)
       │   └── llama3.2, nomic-embed-text
       │
       ├── SQLite (Local Database)
       │
       ├── Chroma/FAISS (Vector Store)
       │
       └── Optional: Connect to Azure
           └── Hybrid mode with cloud services
```

### 7.2 Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2
ollama pull nomic-embed-text

# Run desktop app
cd deployments/desktop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/start_local.py
```

---

## 8. Monitoring & Observability

### 8.1 Key Metrics
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Latency (P95) | < 2s | > 5s |
| Error Rate | < 1% | > 5% |
| Token Usage | Monitor | Budget limit |
| Search Latency | < 500ms | > 2s |
| Function Execution | < 30s | > 60s |

### 8.2 Dashboards
- Application Insights overview
- Custom RAG metrics (tokens, sources, latency)
- Cost analysis dashboard
- Security audit logs

---

## 9. Next Steps

### Immediate (Before Deployment)
1. [ ] Request Azure OpenAI access at https://aka.ms/oai/access
2. [ ] Request VM quota increase if needed
3. [ ] Create Azure DevOps project for CI/CD
4. [ ] Set up Azure AD App Registration

### Short Term (Week 1-2)
1. [ ] Deploy base infrastructure with `./deploy.sh deploy`
2. [ ] Configure private DNS zones
3. [ ] Set up monitoring alerts

### Medium Term (Week 3-4)
1. [ ] Enable OpenAI once quota approved (`deploy_openai = true`)
2. [ ] Enable Functions once VM quota approved (`deploy_functions = true`)
3. [ ] Deploy and test RAG pipeline

### Long Term (Week 5+)
1. [ ] Frontend development and deployment
2. [ ] CI/CD pipeline configuration
3. [ ] Security hardening
4. [ ] Performance optimization
5. [ ] User acceptance testing

---

## 10. Support & Resources

- **Azure OpenAI Docs**: https://learn.microsoft.com/azure/ai-services/openai/
- **Azure AI Search**: https://learn.microsoft.com/azure/search/
- **Terraform Azure Provider**: https://registry.terraform.io/providers/hashicorp/azurerm/
- **RAG Best Practices**: https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview

---

*Document Version: 1.0*
*Last Updated: 2024-11-25*
*Author: AI Platform Team*
