# Enterprise RAG Knowledge Copilot

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-00A4EF?style=flat&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade Retrieval-Augmented Generation (RAG) system that enables employees to query company policies, SOPs, HR documents, and technical documentation using natural language. The platform combines Azure OpenAI GPT-4o for response generation with Azure AI Search for hybrid (vector + keyword) semantic retrieval, delivering grounded answers with source citations. Chat session history is persisted in Cosmos DB and frequently queried results are cached in Redis for low-latency responses.

## Architecture

```
User (Web / Teams / Mobile)
        |
   Azure Front Door (WAF + SSL)
        |
   APIM Gateway (OAuth2, Rate Limiting)
        |
   Azure Functions (RAG Orchestrator)
        |
   +----+----+----+----+
   |         |         |
Azure     Azure AI   Azure
OpenAI    Search     Cosmos DB
(GPT-4o)  (Hybrid    (Sessions/
           Vector)    History)
   |                   |
Redis Cache        Key Vault
(Response Cache)   (Secrets)
        |
   Document Ingestion Pipeline
   (Event Grid -> Durable Functions -> Document Intelligence -> Embeddings -> AI Search)
```

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o, text-embedding-ada-002 | Response generation, vector embeddings |
| Azure AI Search | S1 (3 replicas) | Hybrid vector + keyword search with semantic ranking |
| Azure Cosmos DB | Serverless | Chat sessions, conversation history |
| Azure Document Intelligence | prebuilt-layout | OCR and document extraction for ingestion |
| Azure Cache for Redis | P1 Premium | Query response caching, rate limiting |
| Azure Blob Storage | Hot tier | Document storage (source files) |
| Azure Key Vault | Standard | Secrets, API keys, certificates |
| Azure Functions | Premium EP1 (Python 3.11) | RAG orchestration, ingestion triggers |
| Azure Event Grid | Standard | Blob upload event triggers |
| Application Insights | Pay-as-you-go | APM, telemetry, distributed tracing |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50
- Terraform >= 1.5
- Python 3.11+
- Azure OpenAI resource with GPT-4o and text-embedding-ada-002 deployments
- Azure AI Search service (S1 tier recommended)

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-1-rag-copilot

# Copy environment template
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### 2. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Install dependencies and run locally

```bash
cd ../src
pip install -r requirements.txt

# Start Azure Functions locally
func start
```

### 4. Test the chat endpoint

```bash
curl -X POST http://localhost:7071/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the vacation policy?",
    "user_id": "user@company.com"
  }'
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run comprehensive integration tests
python -m pytest test_comprehensive.py -v

# Run all tests with coverage
python -m pytest --cov=src --cov-report=term-missing
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID (OAuth2/OIDC) for user authentication; JWT validation at APIM gateway
- **Authorization**: Fine-grained RBAC role assignments per Azure resource; function-level auth keys
- **Managed Identity**: System-assigned managed identity for all service-to-service communication -- zero stored credentials
- **Network Isolation**: All PaaS services deployed behind Private Link endpoints within a dedicated VNet (10.0.0.0/16) with NSG rules; no public endpoints in production
- **Content Safety**: Azure AI Content Safety filters on all GenAI outputs; prompt injection prevention via input sanitization and system prompt isolation

### Encryption

- **Data at Rest**: AES-256 server-side encryption (SSE) on Blob Storage, Cosmos DB, and AI Search; platform-managed keys by default with customer-managed key (CMK) support via Key Vault
- **Data in Transit**: TLS 1.2+ enforced on all endpoints and inter-service communication
- **Key Management**: Azure Key Vault with RBAC access, soft-delete enabled, and purge protection for secrets, API keys, and certificates

### Monitoring

- **Application Insights**: Full APM with dependency tracking, request tracing, and custom telemetry for RAG pipeline latency
- **Log Analytics**: Centralized audit logs with 90-day retention; KQL queries for query pattern analysis
- **Alerts**: Azure Monitor alerts on latency P99, error rates, token consumption, and function execution failures
- **Dashboards**: Azure Monitor workbooks for RAG pipeline health, token usage, and cache hit rates

### Visualization

- **Power BI**: Connected to Log Analytics for executive dashboards on query volume, user adoption, and document coverage
- **Azure Monitor Workbooks**: Operational dashboards for real-time pipeline health and cost tracking

### Tracking

- **Request Tracing**: End-to-end correlation IDs propagated from APIM through Functions to OpenAI and AI Search via Application Insights
- **Audit Logs**: All user queries, document access, and response generation events logged to Cosmos DB and Log Analytics
- **Prompt Flow Tracing**: Azure AI Studio prompt flow tracing for debugging RAG chain execution

### Accuracy

- **Retrieval Quality**: Hybrid search (BM25 + vector) with semantic reranking; top-5 document retrieval with configurable relevance thresholds
- **Response Grounding**: System prompt enforces citation-only responses -- model must reference source documents or decline to answer
- **Confidence Thresholds**: Reranker scores tracked; low-confidence retrievals flagged for review
- **Feedback Loop**: User feedback captured for continuous retrieval and response quality improvement

### Explainability

- **Source Citations**: Every response includes `[Source: document_name, Page: X]` citations linking to retrieved documents
- **Retrieval Transparency**: API response includes source documents, relevance scores, and reranker scores
- **Token Usage**: Prompt and completion token counts returned with every response for cost transparency

### Responsibility

- **Content Filtering**: Azure OpenAI content filters enabled for hate, violence, self-harm, and sexual content categories
- **Grounded Responses**: System prompt prohibits hallucination -- responses must be grounded in retrieved documents
- **Data Loss Prevention (DLP)**: Policies prevent sensitive data leakage in AI-generated responses
- **Bias Mitigation**: Regular review of response patterns across user demographics

### Interpretability

- **Retrieval Scoring**: Each source document includes both search score and reranker score for transparency
- **Decision Trace**: Full RAG pipeline trace (query rewriting, embedding, retrieval, augmentation, generation) available in Application Insights
- **Chat History**: Multi-turn context window (last 3 turns) visible for understanding response context

### Portability

- **Infrastructure as Code**: All resources defined in Terraform with modular configuration per environment (dev/staging/prod)
- **Containerization**: Azure Functions compatible with Docker containers for local development and alternative hosting
- **Multi-Region**: Blue-green deployment strategy with East US primary and West US 2 secondary for disaster recovery
- **SDK Abstraction**: OpenAI Python SDK used with Azure-specific configuration, enabling migration to alternative LLM providers

## Project Structure

```
project-1-rag-copilot/
|-- docs/
|   +-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   +-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions: chat, health, history endpoints
|   +-- ingestion/
|       +-- document_processor.py # Document chunking and embedding pipeline
|-- tests/
|   |-- test_function_app.py     # Unit tests for function endpoints
|   +-- test_comprehensive.py    # Integration and end-to-end tests
+-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Submit a natural language query; returns grounded answer with citations |
| `GET` | `/api/health` | Health check -- returns service status, version, and timestamp |
| `GET` | `/api/sessions/{session_id}/history` | Retrieve chat history for a session |
| Event Grid | `DocumentIngestionTrigger` | Triggered on blob upload; initiates document processing pipeline |

### POST /api/chat

**Request:**
```json
{
  "query": "What is the vacation policy?",
  "user_id": "user@company.com",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "answer": "According to the HR policy document...",
  "sources": [
    { "title": "HR Policy Guide", "source": "hr-policies.pdf", "page": 12, "relevance_score": 0.95 }
  ],
  "session_id": "abc123",
  "usage": { "prompt_tokens": 1200, "completion_tokens": 350, "total_tokens": 1550 }
}
```

## License

This project is licensed under the MIT License.
