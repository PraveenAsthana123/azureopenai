# Project 17: Knowledge Graph Builder

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-Gremlin%20API-green?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-yellow?style=flat)
![AI Search](https://img.shields.io/badge/AI%20Search-Hybrid%20Vector-purple?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade Knowledge Graph Builder platform that automates entity and relationship extraction from unstructured documents, constructs a traversable graph database, and powers graph-enhanced Retrieval-Augmented Generation (RAG) for superior contextual answers. The system leverages Azure OpenAI GPT-4o for entity extraction and natural language generation, Azure Cosmos DB Gremlin API for graph storage and traversal, and Azure AI Search for hybrid vector retrieval. An ontology management layer allows domain experts to define and evolve entity schemas, relationship types, and validation rules without code changes.

## Architecture

```
Documents --> Event Grid --> Durable Functions (Orchestrator)
                                |
                    +-----------+-----------+
                    |           |           |
               Doc Intel   GPT-4o NER   Ontology
               (Parse)    (Entities +   Validator
                          Relations)
                    |           |           |
                    +-----------+-----------+
                                |
                    Graph Writer (Cosmos DB Gremlin)
                         |         |          |
                    AI Search   Redis      Lineage
                    (Vectors)   (Cache)    (Metadata)

User Query --> APIM --> Azure Functions --> Vector Search + Graph Traversal
                                        --> Merge Results --> GPT-4o (Generate) --> Response
```

**Key Components:**
- **Graph Explorer** (React + D3.js/Cytoscape) -- Interactive graph visualization
- **Query Portal** (React + TypeScript) -- Natural language query interface
- **Admin Console** -- Ontology management, schema editing, ingestion monitoring
- **Azure Functions** (Python 3.11) -- Entity extraction, graph query, RAG orchestration
- **Durable Functions** -- Document processing and graph build pipeline

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Entity extraction, relationship inference, response generation |
| Azure OpenAI (text-embedding-ada-002) | Vector embeddings for entities and document chunks |
| Azure Cosmos DB (Gremlin API) | Graph storage (vertices = entities, edges = relationships) |
| Azure AI Search | Hybrid vector + keyword search with semantic reranking |
| Azure Document Intelligence | OCR, table extraction, document structure parsing |
| Azure Blob Storage | Source document storage, extraction artifacts |
| Azure Redis Cache | Graph traversal cache, query result cache |
| Azure Data Factory | Batch ingestion pipelines, graph refresh jobs |
| Azure Key Vault | Secrets, connection strings, encryption keys |
| Azure Front Door | WAF, CDN, SSL termination |
| Azure API Management | Rate limiting, authentication, usage analytics |
| Azure SignalR | Real-time graph update notifications |
| Application Insights | APM, dependency tracking, custom graph metrics |
| Log Analytics | Centralized logging, KQL queries |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- Node.js >= 18 (for frontend)
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- Cosmos DB Gremlin endpoint provisioned

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-17-knowledge-graph

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### Environment Variables

```bash
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
COSMOS_GREMLIN_ENDPOINT=wss://<your-cosmos>.gremlin.cosmos.azure.com:443/
COSMOS_GREMLIN_KEY=<your-gremlin-key>
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
COSMOS_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/
```

### Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Deploy Application

```bash
cd src
func azure functionapp publish <your-function-app-name>
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run integration tests
python -m pytest test_integration.py -v

# Test health endpoint
curl https://<function-app>.azurewebsites.net/api/health
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID (OAuth2/OIDC) with Conditional Access and MFA enforcement
- **Authorization**: Fine-grained RBAC with graph namespace-level access control; vertex-level and edge-level ACLs
- **Managed Identity**: System-assigned managed identity for zero-credential service-to-service authentication across all services
- **Network Isolation**: Dedicated VNet (10.0.0.0/16) with 3 subnets (Application, Data, Integration); all services behind Private Link with no public endpoints; NSG rules enforce least-privilege traffic flow
- **Perimeter**: Azure Front Door with WAF (OWASP 3.2), DDoS Protection, geo-filtering

### Encryption

- **Data at Rest**: AES-256 encryption (SSE) for Cosmos DB, Blob Storage, and AI Search; Customer-Managed Keys (CMK) via Key Vault for graph data
- **Data in Transit**: TLS 1.3 enforced for all service-to-service and client-to-service communication
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection; CMK rotation policies for graph database credentials and encryption keys

### Monitoring

- **Application Insights**: Workspace-based APM with 50% sampling; dependency tracking, custom graph metrics (entity count, edge density, traversal latency)
- **Log Analytics**: 90-day retention; centralized KQL queries across all services
- **Alerts**: Azure Monitor with action groups and smart detection alerts for graph ingestion failures, query latency spikes, and extraction errors
- **Dashboards**: Custom Azure Monitor workbooks for entity count trends, edge density, traversal performance, and ingestion pipeline health

### Visualization

- **Graph Explorer**: Interactive D3.js/Cytoscape.js visualization for exploring entity relationships
- **Graph Stats Dashboard**: Custom Azure Monitor workbook showing entity counts, edge density, traversal latency, and ingestion metrics
- **Cost Management Dashboard**: Azure Cost Management integration for service-level cost tracking

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across Azure Functions, Cosmos DB Gremlin, AI Search, and OpenAI calls
- **Correlation IDs**: End-to-end correlation through APIM, Functions, and data stores for every extraction and query request
- **Audit Logs**: Graph traversal patterns logged and analyzed; all entity CRUD operations tracked with timestamps and user context
- **Data Lineage**: Source document to entity mapping tracked in Cosmos DB; Purview integration for data classification

### Accuracy

- **Model Evaluation**: Entity extraction precision, recall, and F1 measured against labeled ground truth datasets; relationship inference accuracy benchmarked
- **Confidence Thresholds**: Extraction results include confidence scores; low-confidence entities routed for human review
- **Validation**: Ontology schema validation ensures extracted entities conform to defined types and constraints; referential integrity checks for all graph mutations

### Explainability

- Extracted entities and relationships include source document references and extraction confidence scores
- Graph-enhanced RAG responses cite sources using [Source: title] format, showing which documents and graph relationships contributed to the answer
- Graph traversal paths are returned with query results, making relationship chains transparent to end users

### Responsibility

- **Content Filtering**: Azure OpenAI content safety filters prevent prompt injection during entity extraction and response generation
- **Bias Detection**: Entity linking monitored for systematic bias in relationship inference; coreference resolution evaluated for demographic fairness
- **Responsible AI**: Extraction prompts reviewed for potential bias amplification; human-in-the-loop workflows for knowledge curation and assertion approval

### Interpretability

- **Feature Importance**: Graph traversal results show path weights and relationship types that contributed to answers
- **Decision Transparency**: RAG pipeline separates vector search results from graph context, allowing users to understand which retrieval method sourced each fact
- **Ontology Visibility**: Entity type definitions, relationship schemas, and constraints are visible through the Admin Console

### Portability

- **Containerization**: Azure Functions deployable as Docker containers for local development and alternative hosting
- **Infrastructure as Code**: Full Terraform configuration in `infra/` directory for reproducible deployments across environments (dev, staging, production)
- **Multi-Cloud Considerations**: Gremlin traversal language is an open standard (Apache TinkerPop); vector search patterns transferable to other graph + vector databases
- **Data Export**: Graph data exportable via Gremlin queries; ontology definitions stored as JSON documents

## Project Structure

```
project-17-knowledge-graph/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (extract, query, graph-query, ontology, health)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/extract` | Extract entities and relationships from text, optionally persist to graph |
| POST | `/api/query` | Graph-enhanced RAG query combining vector search with graph traversal |
| POST | `/api/graph-query` | Direct Gremlin query endpoint for graph exploration (read-only) |
| POST | `/api/ontology` | Ontology management CRUD (create, read, update, delete, list) |
| GET | `/api/health` | Health check with component status |
| EventGrid | `DocumentGraphIngestionTrigger` | Blob upload trigger for automated entity extraction and graph ingestion |

## License

This project is licensed under the MIT License.
