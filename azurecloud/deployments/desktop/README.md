# Desktop RAG Platform

Local/hybrid RAG deployment supporting offline operation with Ollama + ChromaDB, or connection to Azure services.

## Features

- **Full Local Mode**: Run completely offline with Ollama (LLM) + ChromaDB (vectors) + SQLite (database)
- **Hybrid Mode**: Use Azure OpenAI for better quality while keeping data local
- **Azure Mode**: Connect to full Azure stack from your desktop
- **Docker Support**: One-command deployment with Docker Compose
- **FastAPI**: Modern async Python API with auto-generated docs

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Ollama (for local LLM, install from https://ollama.ai)

### Option 1: Docker Compose (Recommended)

```bash
# Clone and navigate
cd deployments/desktop

# Copy environment file
cp .env.example .env

# Start with local mode (Ollama + ChromaDB)
docker compose --profile local up -d

# Or start with CPU-only Ollama (no GPU)
docker compose --profile cpu up -d

# Pull required models
docker compose --profile init up
```

### Option 2: Native Python

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start Ollama (in separate terminal)
ollama serve

# Pull required models
ollama pull llama3.2
ollama pull nomic-embed-text

# Start the API
python -m uvicorn src.api.main:app --reload
```

### Option 3: Startup Script

```bash
# Start all services automatically
python -m scripts.start_local

# With GPU support
python -m scripts.start_local --gpu

# In hybrid mode (Azure OpenAI + local storage)
python -m scripts.start_local --mode hybrid
```

## Configuration Modes

### 1. Local Mode (Default)

Full offline operation - no internet required after model download.

```bash
RAG_DEPLOYMENT_MODE=local
```

| Component | Service |
|-----------|---------|
| LLM | Ollama (llama3.2) |
| Embeddings | Ollama (nomic-embed-text) |
| Vector DB | ChromaDB |
| Database | SQLite |
| Storage | Local filesystem |

### 2. Hybrid Mode

Best of both worlds - Azure AI quality with local data storage.

```bash
RAG_DEPLOYMENT_MODE=hybrid
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
```

| Component | Service |
|-----------|---------|
| LLM | Azure OpenAI (gpt-4o-mini) |
| Embeddings | Azure OpenAI (text-embedding-3-large) |
| Vector DB | ChromaDB (local) |
| Database | SQLite (local) |
| Storage | Local filesystem |

### 3. Azure Mode

Connect to full Azure services from desktop.

```bash
RAG_DEPLOYMENT_MODE=azure
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-key
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-key
AZURE_STORAGE_ACCOUNT_URL=https://yourstorage.blob.core.windows.net
```

## API Endpoints

Once running, access the API at `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check with service status |
| `/chat` | POST | Chat with RAG |
| `/documents` | POST | Add document to vector store |
| `/search` | POST | Search vector store |
| `/config` | GET | Current configuration |
| `/models` | GET | List Ollama models |
| `/docs` | GET | Swagger UI |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "user_id": "user123"
  }'
```

### Example: Add Document

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Machine learning is a subset of AI...",
    "metadata": {"source": "textbook", "chapter": 1}
  }'
```

## Project Structure

```
desktop/
├── config/
│   └── settings.py          # Pydantic settings with mode switching
├── docker/
│   ├── docker-compose.yml   # Docker services
│   └── Dockerfile           # API container
├── scripts/
│   └── start_local.py       # Startup automation
├── src/
│   ├── api/
│   │   └── main.py          # FastAPI application
│   └── services/
│       ├── llm_service.py   # LLM providers (Ollama, Azure, OpenAI)
│       ├── vector_service.py # Vector DBs (ChromaDB, Azure Search)
│       ├── database_service.py # DBs (SQLite, Cosmos)
│       └── storage_service.py  # Storage (Local, Blob)
├── data/                    # Local data storage
│   ├── chromadb/            # Vector embeddings
│   ├── documents/           # Uploaded files
│   └── rag.db               # SQLite database
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

See `.env.example` for all configuration options. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_DEPLOYMENT_MODE` | local, hybrid, or azure | local |
| `RAG_LLM_PROVIDER` | ollama, azure_openai, openai | ollama |
| `RAG_VECTOR_DB_PROVIDER` | chromadb, azure_search, qdrant | chromadb |
| `RAG_OLLAMA__MODEL` | Ollama model for chat | llama3.2 |
| `RAG_OLLAMA__EMBEDDING_MODEL` | Ollama model for embeddings | nomic-embed-text |
| `RAG_API_PORT` | API server port | 8000 |

## Docker Profiles

The Docker Compose file supports different profiles:

```bash
# Local with GPU
docker compose --profile local up -d

# Local CPU-only
docker compose --profile cpu up -d

# With Qdrant instead of ChromaDB
docker compose --profile qdrant up -d

# With Redis cache
docker compose --profile cache up -d

# Initialize models
docker compose --profile init up
```

## Connecting to Azure Services

Desktop can connect to Azure services using:

1. **API Keys**: Set `AZURE_*_API_KEY` environment variables
2. **Azure CLI**: Run `az login` and use DefaultAzureCredential
3. **Managed Identity**: When running on Azure VM/Container Apps

```python
# The services automatically detect authentication method
# Priority: API Key > Environment Credentials > Managed Identity
```

## Development

```bash
# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Troubleshooting

### Ollama not starting

```bash
# Check if Ollama is installed
which ollama

# Start Ollama manually
ollama serve

# Check available models
ollama list
```

### ChromaDB errors

```bash
# Reset ChromaDB data
rm -rf data/chromadb

# Restart services
docker compose down && docker compose up -d
```

### Azure connection issues

```bash
# Test Azure credentials
az account show

# Test OpenAI endpoint
curl -H "api-key: $AZURE_OPENAI_API_KEY" \
  "$AZURE_OPENAI_ENDPOINT/openai/models?api-version=2024-02-15-preview"
```

## Performance Tips

1. **Use GPU for Ollama**: Enable GPU profile for faster inference
2. **Pre-pull models**: Models are large, pull them ahead of time
3. **Tune chunk size**: Adjust `RAG_CHUNK_SIZE` based on your documents
4. **Use hybrid mode**: Azure OpenAI is faster than local Ollama for most tasks
