# Enterprise Copilot — Azure Services Checklist

## Required Azure Services by Category

### 1. Core Infrastructure & Security

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| Azure Entra ID | Authentication, RBAC, group-level access | P1/P2 | All | Low |
| Azure Virtual Network | Secure network segregation | Standard | All | Low |
| Private Link / Private Endpoints | Private access to OpenAI, Search, Storage | Standard | Prod | Medium |
| Azure Key Vault | CMK encryption, secrets, certificates | Standard | All | Low |
| Azure Monitor | Metrics, alert rules | Standard | All | Medium |
| Log Analytics Workspace | Query & analyze logs | Pay-per-GB | All | Medium |
| Customer-Managed Keys (CMK) | Data encryption for storage + AI models | Standard | Prod | Low |

### 2. Azure AI & Model Services

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| **Azure OpenAI Service** | GPT-4o, GPT-4o Mini, Embeddings | S0 | All | **High** |
| **Azure AI Foundry** | Agent orchestration, tool integration, tracing | Standard | All | Medium |
| Azure AI Model Catalog | Access models (GPT, Phi, Mistral) | Standard | Dev/Test | Low |
| Azure AI Content Safety | PII detection, toxicity filtering | S0 | All | Low |
| Azure AI Document Intelligence | Parsing PDFs, DOCX, scanned docs | S0 | All | Medium |
| **Azure AI Search** | Vector index, hybrid search, semantic ranker | **Standard S1+** | All | **High** |

### 3. Data Engineering & Storage

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| **Azure Blob Storage** | Raw + processed document storage | Standard GRS | All | Medium |
| Azure Data Factory | Ingestion pipelines | Standard | All | Medium |
| **Azure Functions** | Custom ETL logic, chunking, metadata | Premium EP1 | All | Medium |
| Azure Logic Apps | Workflow automation | Consumption | All | Low |
| Azure Databricks (optional) | Heavy data transformation | Standard | Dev/Test | High |
| Azure Service Bus | Async ingestion & pipeline triggers | Standard | All | Low |

### 4. Search & Retrieval

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| **Azure AI Search** | Vector + BM25 hybrid index | Standard S1+ | All | **High** |
| Semantic Ranker | Deep ranker for accurate top-k | Add-on | All | Medium |
| Azure Cosmos DB (optional) | Store sessions, cache, feedback | Serverless | All | Medium |

### 5. Copilot / Application Layer

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| **Microsoft Copilot Studio** | Frontend chatbot UI | Per-user | All | Medium |
| Power Platform Connectors | CRM/ERP integrations | Standard | All | Low |
| Azure Web App (optional) | Custom portal UI | B1/P1 | Prod | Low |
| **Microsoft Teams** | Primary end-user interface | E3/E5 | All | Included |

### 6. DevOps & Deployment

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| Azure DevOps Pipelines | CI/CD automation | Basic | All | Low |
| Azure Repos / GitHub | Source code management | Free/Team | All | Low |
| Azure Artifacts | Package hosting | Basic | All | Low |
| Azure Container Registry | Host containers | Basic/Standard | Prod | Low |
| Azure Kubernetes Service (optional) | Microservices hosting | Standard | Prod | Medium |

### 7. Monitoring & Observability

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| **Application Insights** | LLM tracing, latency, prompt monitoring | Standard | All | Medium |
| Azure Monitor Alerts | Health alerts, failure notifications | Standard | All | Low |
| Azure AI Foundry Evaluation | Groundedness, Precision@K evaluations | Standard | All | Low |
| Azure Cost Management | Budgeting + cost alerts | Free | All | Free |

### 8. Security & Compliance (Optional but Recommended)

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| Microsoft Defender for Cloud | Threat protection | Standard | Prod | Medium |
| Microsoft Purview | Data classification, governance | Standard | Prod | Medium |
| Microsoft Sentinel | SIEM for enterprise monitoring | Pay-per-GB | Prod | High |

### 9. Optional Enterprise Scaling

| Service | Purpose | SKU/Tier | Environment | Cost Impact |
|---------|---------|----------|-------------|-------------|
| Azure Front Door | CDN + WAF + global routing | Standard | Prod | Medium |
| Azure API Management | Manage APIs/tools securely | Developer/Standard | Prod | Medium |
| Azure Redis Cache | Speed up repeated queries | Basic/Standard | Prod | Medium |
| Azure Event Grid | Event-driven processing | Standard | All | Low |

---

## Service-by-Environment Matrix

| Service | Dev | Test/QA | Staging | Prod |
|---------|-----|---------|---------|------|
| **Entra ID** | ✅ | ✅ | ✅ | ✅ |
| **VNet + Private DNS** | ✅ | ✅ | ✅ | ✅ |
| **Private Endpoints** | ❌ | ❌ | ✅ | ✅ |
| **Key Vault** | ✅ | ✅ | ✅ | ✅ |
| **Azure OpenAI** | ✅ (shared) | ✅ (shared) | ✅ | ✅ (dedicated) |
| **AI Search** | ✅ (Basic) | ✅ (Standard) | ✅ (Standard) | ✅ (Standard S2+) |
| **Document Intelligence** | ✅ | ✅ | ✅ | ✅ |
| **Blob Storage** | ✅ (LRS) | ✅ (LRS) | ✅ (GRS) | ✅ (GRS) |
| **Functions** | ✅ (Consumption) | ✅ (Consumption) | ✅ (Premium) | ✅ (Premium) |
| **Data Factory** | ✅ | ✅ | ✅ | ✅ |
| **Copilot Studio** | ✅ | ✅ | ✅ | ✅ |
| **App Insights** | ✅ | ✅ | ✅ | ✅ |
| **Cosmos DB** | ✅ (serverless) | ✅ (serverless) | ✅ | ✅ |
| **DevOps Pipelines** | ✅ | ✅ | ✅ | ✅ |
| **Defender for Cloud** | ❌ | ❌ | ✅ | ✅ |
| **Sentinel** | ❌ | ❌ | ❌ | ✅ (optional) |

---

## Cost Impact Summary

### Monthly Estimated Costs by Environment

| Environment | Estimated Monthly Cost | Notes |
|-------------|----------------------|-------|
| **Dev** | $500 - $1,500 | Shared resources, basic SKUs |
| **Test/QA** | $1,000 - $2,500 | Standard SKUs, limited scale |
| **Staging** | $2,000 - $4,000 | Production-like, private endpoints |
| **Production** | $5,000 - $15,000+ | Full redundancy, premium SKUs |

### Cost Breakdown by Service Category

| Category | % of Total | Key Cost Drivers |
|----------|------------|------------------|
| **Azure OpenAI** | 35-45% | Token usage (GPT-4o + embeddings) |
| **AI Search** | 20-25% | Index size, replicas, semantic ranker |
| **Compute (Functions/AKS)** | 10-15% | Function executions, container hours |
| **Storage** | 5-10% | Document storage, embeddings cache |
| **Monitoring** | 5-10% | Log Analytics, App Insights ingestion |
| **Networking** | 5-10% | Private endpoints, data transfer |
| **Other** | 5-10% | Misc services |

### Cost Optimization Strategies

| Strategy | Savings | Trade-off |
|----------|---------|-----------|
| Use GPT-4o-mini for classification | 90% on classification | Slight accuracy drop |
| Cache answers (1hr TTL) | 50-80% on LLM | Stale responses possible |
| Use text-embedding-3-small | 85% on embeddings | Lower retrieval quality |
| Reserved capacity (OpenAI PTU) | 20-30% | Commit to usage |
| Serverless Cosmos DB | Variable | Cold start latency |
| Basic AI Search for Dev | 70% | Limited scale |

---

## Deployment Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ORDER (LAYERS)                                │
└─────────────────────────────────────────────────────────────────────────────────┘

LAYER 1: FOUNDATION (Deploy First)
├── Azure Subscription
├── Resource Groups (dev/test/staging/prod)
├── Entra ID Configuration
└── Azure Policy Assignments

                    │
                    ▼

LAYER 2: NETWORKING
├── Virtual Network
├── Subnets (app, ai, data, security)
├── Network Security Groups
├── Private DNS Zones
└── Route Tables

                    │
                    ▼

LAYER 3: SECURITY
├── Key Vault
├── Managed Identities
├── Role Assignments (RBAC)
└── Customer-Managed Keys

                    │
                    ▼

LAYER 4: DATA LAYER
├── Storage Account (Blob)
├── Cosmos DB
├── Azure SQL (optional)
└── Private Endpoints (Data)

                    │
                    ▼

LAYER 5: AI SERVICES
├── Azure OpenAI
│   ├── GPT-4o deployment
│   └── text-embedding-3-large deployment
├── Azure AI Search
│   └── Index schema
├── Document Intelligence
└── Private Endpoints (AI)

                    │
                    ▼

LAYER 6: COMPUTE
├── Azure Functions (Premium)
├── Data Factory
├── Logic Apps
└── AKS Cluster (optional)

                    │
                    ▼

LAYER 7: APPLICATION
├── RAG Orchestrator (deployed to Functions/AKS)
├── Ingestion Pipeline
├── API Management (optional)
└── Copilot Studio Agent

                    │
                    ▼

LAYER 8: MONITORING
├── Log Analytics Workspace
├── Application Insights
├── Monitor Alerts
└── Dashboards

                    │
                    ▼

LAYER 9: DEVOPS
├── Azure DevOps Project
├── CI/CD Pipelines
├── Container Registry
└── Artifact Feeds
```

---

## Terraform/Bicep Module Checklist

### Foundation Modules
- [ ] `resource-groups` - Dev/Test/Staging/Prod RGs
- [ ] `naming-convention` - Consistent naming
- [ ] `tagging` - Cost center, environment tags

### Networking Modules
- [ ] `vnet` - Virtual network with subnets
- [ ] `nsg` - Network security groups
- [ ] `private-dns` - Private DNS zones
- [ ] `route-tables` - UDR for firewall

### Security Modules
- [ ] `key-vault` - Key Vault with private endpoint
- [ ] `managed-identity` - System/user-assigned identities
- [ ] `rbac` - Role assignments

### Data Modules
- [ ] `storage-account` - Blob storage with private endpoint
- [ ] `cosmos-db` - Cosmos DB serverless
- [ ] `sql-database` - Azure SQL (if needed)

### AI Modules
- [ ] `openai` - Azure OpenAI with deployments
- [ ] `ai-search` - AI Search with index
- [ ] `document-intelligence` - Doc Intelligence

### Compute Modules
- [ ] `function-app` - Premium function app
- [ ] `data-factory` - Data Factory instance
- [ ] `aks` - AKS cluster (optional)

### Monitoring Modules
- [ ] `log-analytics` - Log Analytics workspace
- [ ] `app-insights` - Application Insights
- [ ] `alerts` - Monitor alert rules
- [ ] `dashboards` - Azure dashboards

---

## Service Enablement Checklist

### Pre-Deployment
- [ ] Verify Azure subscription quotas
- [ ] Request Azure OpenAI access (if not enabled)
- [ ] Request AI Search semantic ranker access
- [ ] Enable required resource providers
- [ ] Configure Entra ID groups for RBAC

### Deployment Order
1. [ ] Resource Groups
2. [ ] Networking (VNet, DNS)
3. [ ] Key Vault + Identities
4. [ ] Storage Account
5. [ ] Cosmos DB
6. [ ] Azure OpenAI
7. [ ] AI Search
8. [ ] Document Intelligence
9. [ ] Function App
10. [ ] Data Factory
11. [ ] Private Endpoints
12. [ ] Log Analytics + App Insights
13. [ ] Copilot Studio
14. [ ] CI/CD Pipelines

### Post-Deployment
- [ ] Verify private endpoint connectivity
- [ ] Test managed identity access
- [ ] Configure diagnostic settings
- [ ] Set up alert rules
- [ ] Create initial AI Search index
- [ ] Deploy model deployments in OpenAI

---

*Document Version: 1.0*
*Last Updated: 2025-01-15*
