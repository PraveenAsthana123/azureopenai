# RAG Platform Deployment Options

This directory contains two deployment configurations for the Enterprise RAG Platform:

## Deployment Comparison

| Feature | Cloud | Desktop |
|---------|-------|---------|
| **Target** | Production/Enterprise | Development/Small Teams |
| **LLM** | Azure OpenAI | Ollama (local) + Azure OpenAI (optional) |
| **Vector DB** | Azure AI Search | ChromaDB (local) + Azure Search (optional) |
| **Database** | Cosmos DB | SQLite + Azure Cosmos (optional) |
| **API** | Azure Functions | FastAPI (local) |
| **Storage** | Azure Blob | Local filesystem |
| **Auth** | Entra ID + RBAC | API Key / Local |
| **Cost** | Pay-per-use | Mostly free (local) |
| **Scalability** | Auto-scale | Single machine |
| **Offline** | No | Yes (with Ollama) |

## Quick Start

### Cloud Deployment
```bash
cd cloud
# Deploy infrastructure
az deployment group create -f infrastructure/main.bicep -g rg-rag-prod

# Deploy functions
func azure functionapp publish rag-fn-prod
```

### Desktop Deployment
```bash
cd desktop

# Install dependencies
pip install -r requirements.txt

# Start with local services (Ollama + ChromaDB)
python -m scripts.start_local

# Or start with Azure hybrid mode
export USE_AZURE_OPENAI=true
export USE_AZURE_SEARCH=true
python -m uvicorn src.api.main:app --reload
```

## Configuration Modes

### Desktop - Full Local (Offline)
```yaml
llm: ollama
vector_db: chromadb
database: sqlite
storage: local
```

### Desktop - Hybrid (Local + Azure)
```yaml
llm: azure_openai          # Cloud
vector_db: chromadb        # Local
database: sqlite           # Local
storage: azure_blob        # Cloud
```

### Desktop - Azure Connected
```yaml
llm: azure_openai          # Cloud
vector_db: azure_search    # Cloud
database: cosmos_db        # Cloud
storage: azure_blob        # Cloud
```

### Cloud - Full Azure
```yaml
llm: azure_openai
vector_db: azure_search
database: cosmos_db
storage: azure_blob
auth: entra_id
compute: azure_functions
```

## Directory Structure

```
deployments/
├── cloud/                    # Full Azure deployment
│   ├── src/
│   │   ├── functions/        # Azure Functions
│   │   └── services/         # Shared services
│   ├── config/
│   │   └── settings.yaml     # Cloud configuration
│   ├── infrastructure/       # Bicep/Terraform
│   └── docker/               # Container definitions
│
├── desktop/                  # Local + hybrid deployment
│   ├── src/
│   │   ├── api/              # FastAPI application
│   │   ├── services/         # Service implementations
│   │   └── models/           # Data models
│   ├── config/
│   │   ├── local.yaml        # Full local config
│   │   └── hybrid.yaml       # Azure hybrid config
│   ├── docker/               # Docker compose
│   └── scripts/              # Startup scripts
│
└── shared/                   # Shared code between deployments
    ├── core/                 # Core RAG logic
    ├── evaluation/           # Evaluation framework
    └── utils/                # Common utilities
```
