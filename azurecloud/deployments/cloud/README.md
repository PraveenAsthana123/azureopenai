# Cloud RAG Platform

Production-ready Azure deployment with Azure Functions, Azure OpenAI, Azure AI Search, Cosmos DB, and full enterprise security.

## Features

- **Serverless Architecture**: Azure Functions with auto-scaling
- **Enterprise LLM**: Azure OpenAI with GPT-4o-mini and text-embedding-3-large
- **Hybrid Search**: Azure AI Search with vector + semantic search
- **Global Database**: Cosmos DB for conversation history
- **Managed Identity**: No API keys in code, full RBAC
- **Private Networking**: VNet integration with private endpoints
- **Monitoring**: Application Insights with custom RAG metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Azure Cloud                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Entra ID   │    │   API Mgmt   │    │     CDN      │       │
│  │    (Auth)    │    │  (Optional)  │    │  (Optional)  │       │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘       │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Azure Functions                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │  /chat   │  │ /ingest  │  │ /search  │  │ /health  │   │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │ │
│  └───────┼─────────────┼─────────────┼───────────────────────┘ │
│          │             │             │                          │
│          ▼             ▼             ▼                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ Azure OpenAI  │  │  AI Search    │  │   Cosmos DB   │       │
│  │  - GPT-4o     │  │  - Vectors    │  │  - Sessions   │       │
│  │  - Embeddings │  │  - Semantic   │  │  - Documents  │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Blob Storage │  │  Key Vault    │  │ App Insights  │       │
│  │  - Documents  │  │  - Secrets    │  │  - Metrics    │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Azure CLI (`az`)
- Azure Functions Core Tools (`func`)
- Contributor access to Azure subscription
- jq (for script parsing)

### Deploy

```bash
# Login to Azure
az login

# Deploy everything (infrastructure + functions)
chmod +x scripts/deploy.sh
./scripts/deploy.sh prod rg-rag-prod eastus2
```

This deploys:
- Azure OpenAI with GPT-4o-mini and embedding models
- Azure AI Search with vector index
- Cosmos DB serverless
- Azure Functions (Python 3.11)
- Application Insights
- Key Vault
- VNet with private endpoints

### Manual Deployment

```bash
# 1. Create resource group
az group create -n rg-rag-prod -l eastus2

# 2. Deploy infrastructure
az deployment group create \
  -g rg-rag-prod \
  -f infrastructure/main.bicep \
  -p environment=prod

# 3. Deploy functions
cd src/functions
func azure functionapp publish func-rag-prod-xxx
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/chat` | POST | Entra ID | RAG chat with retrieval |
| `/api/ingest` | POST | Entra ID | Document ingestion |
| `/api/health` | GET | Anonymous | Health check |

### Chat Request

```bash
# Get access token
TOKEN=$(az account get-access-token --resource api://your-client-id --query accessToken -o tsv)

# Chat request
curl -X POST "https://func-rag-prod-xxx.azurewebsites.net/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the key benefits of Azure?",
    "user_id": "user@company.com",
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### Document Ingestion

```bash
curl -X POST "https://func-rag-prod-xxx.azurewebsites.net/api/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "category=technical" \
  -F 'metadata={"author": "John", "department": "Engineering"}'
```

## Configuration

### Environment Variables

Set in Azure Functions configuration:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint URL |
| `AZURE_SEARCH_ENDPOINT` | AI Search endpoint |
| `AZURE_SEARCH_INDEX` | Search index name |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `COSMOS_DATABASE` | Database name |
| `AZURE_STORAGE_ACCOUNT_URL` | Blob storage URL |
| `CHAT_DEPLOYMENT` | OpenAI chat model deployment |
| `EMBEDDING_DEPLOYMENT` | OpenAI embedding deployment |

### Bicep Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `environment` | dev, staging, prod | prod |
| `location` | Azure region | resourceGroup().location |
| `baseName` | Resource name prefix | rag |
| `enablePrivateEndpoints` | Enable private networking | true |

## Project Structure

```
cloud/
├── config/
│   └── settings.yaml        # Configuration reference
├── infrastructure/
│   ├── main.bicep           # Main infrastructure template
│   ├── search-index.json    # AI Search index definition
│   └── modules/
│       ├── network.bicep    # VNet, subnets, NSGs
│       └── private-endpoints.bicep  # Private endpoints
├── scripts/
│   └── deploy.sh            # Deployment automation
└── src/
    └── functions/
        ├── chat/            # Chat function
        ├── ingest/          # Ingestion function
        ├── health/          # Health check function
        ├── host.json        # Functions host config
        └── requirements.txt # Python dependencies
```

## Security

### Authentication

- **Entra ID**: All API endpoints protected by Entra ID authentication
- **Managed Identity**: Function App uses system-assigned identity
- **RBAC**: Role-based access to all Azure services

### Network Security

- **Private Endpoints**: All services accessed via private endpoints
- **VNet Integration**: Functions run inside VNet
- **NSGs**: Network security groups restrict traffic
- **No Public Access**: Services have public access disabled

### Data Protection

- **Encryption at Rest**: All services use Azure-managed encryption
- **TLS 1.2+**: All traffic encrypted in transit
- **Key Vault**: Secrets stored in Key Vault
- **Soft Delete**: Key Vault and Cosmos DB have soft delete enabled

## Monitoring

### Application Insights

Custom metrics tracked:
- `rag_query_latency_ms` - End-to-end query time
- `rag_tokens_used` - Token consumption
- `rag_relevance_score` - Search relevance scores
- `rag_sources_found` - Documents retrieved

### Alerts

Configure in Azure Monitor:
- Response time > 5 seconds
- Error rate > 5%
- Availability < 99%

### Log Analytics Queries

```kql
// Chat latency percentiles
customMetrics
| where name == "rag_query_latency_ms"
| summarize p50=percentile(value, 50), p95=percentile(value, 95), p99=percentile(value, 99)
| by bin(timestamp, 1h)

// Token usage by user
customEvents
| where name == "ChatCompleted"
| extend tokens = toint(customDimensions.tokens_used)
| summarize total_tokens=sum(tokens) by user_id=tostring(customDimensions.user_id)
| order by total_tokens desc
```

## Scaling

### Azure Functions

- **Consumption Plan**: Auto-scales from 0, pay per execution
- **Premium Plan**: Pre-warmed instances, VNet integration
- **Dedicated Plan**: Fixed instances for predictable workloads

### Azure AI Search

- **Replicas**: Add replicas for query throughput
- **Partitions**: Add partitions for index size

### Cosmos DB

- **Serverless**: Auto-scales, no capacity planning
- **Provisioned**: Configure RU/s for predictable costs

## Cost Optimization

| Service | Optimization |
|---------|--------------|
| Functions | Use Consumption plan for variable loads |
| OpenAI | Use GPT-4o-mini instead of GPT-4o |
| Search | Standard tier for most workloads |
| Cosmos | Serverless for <1M RU/month |
| Storage | Cool tier for infrequently accessed documents |

## Disaster Recovery

- **Multi-region**: Deploy to secondary region
- **Cosmos DB**: Enable multi-region writes
- **Blob Storage**: Use GRS replication
- **Backup**: Enable point-in-time restore

## Troubleshooting

### Functions not starting

```bash
# Check function status
az functionapp show -n func-rag-prod -g rg-rag-prod --query state

# View logs
az functionapp log tail -n func-rag-prod -g rg-rag-prod
```

### Search index issues

```bash
# Check index status
az search service show -n search-rag-prod -g rg-rag-prod

# Verify index exists
az rest --method GET \
  --url "https://search-rag-prod.search.windows.net/indexes?api-version=2023-11-01"
```

### Permission errors

```bash
# Verify managed identity roles
az role assignment list --assignee <function-principal-id> --all

# Check Cosmos RBAC
az cosmosdb sql role assignment list --account-name cosmos-rag-prod -g rg-rag-prod
```
