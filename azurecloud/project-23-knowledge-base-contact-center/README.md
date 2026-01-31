# Project 23: Contact Center Knowledge Base

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat&logo=openai&logoColor=white)
![Azure AI Search](https://img.shields.io/badge/Azure%20AI%20Search-Semantic+Vector-purple?style=flat)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-Serverless-green?style=flat&logo=microsoftazure)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

---

## Overview

An AI-powered knowledge management system designed to support contact center agents and customers with intelligent, real-time access to organizational knowledge. The platform leverages Azure OpenAI GPT-4o for GenAI-powered article authoring, FAQ generation from call transcripts, and conversational self-service. Azure AI Search provides hybrid semantic and vector search for instant article retrieval during live calls and chats, while Cosmos DB stores articles with full version history and approval workflows.

The system includes knowledge gap detection from call transcript analysis, article versioning with approval workflows, multilingual support, content freshness scoring, and feedback-driven article ranking to continuously improve knowledge quality.

---

## Architecture

```
+---------------------+    +---------------------+    +---------------------+
|   Agent Desktop     |    |  Self-Service Bot   |    |   Author Portal     |
|   (React/Next.js)   |    |  (Azure Bot Svc)    |    |   (React/Next.js)   |
+---------+-----------+    +---------+-----------+    +---------+-----------+
          |                          |                          |
          +------------- Azure Front Door (WAF + CDN) ---------+
                                     |
                    +----------------+----------------+
                    |                |                |
              APIM Gateway    Azure Bot Svc    Azure SignalR
                    |          (Self-Service)   (Real-time)
                    |                |                |
          +---------+--------+-------+--------+------+---------+
          |         PRIVATE VNET (10.0.0.0/16)                 |
          |                                                     |
          |   Azure Functions (Python 3.11)                     |
          |   - Knowledge Authoring Service                     |
          |   - Agent Assist Suggestion Engine                  |
          |   - Knowledge Gap Detector (Durable Functions)      |
          |   - FAQ Generation Service                          |
          |   - Content Freshness Scoring Engine                |
          |                                                     |
          |   AI/ML Layer:                                      |
          |   - Azure OpenAI (GPT-4o + text-embedding-ada-002)  |
          |   - Azure AI Search (Semantic + Vector Hybrid)      |
          |   - Azure Speech Services (Whisper STT)             |
          |                                                     |
          |   Data Layer:                                       |
          |   - Cosmos DB (Articles, Versions, Feedback)        |
          |   - Blob Storage (Transcripts, Media)               |
          |   - Redis Cache (Search Cache, Sessions)            |
          |   - Event Grid (Article Lifecycle Events)           |
          +-----------------------------------------------------+
```

---

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Article generation, FAQ synthesis, intent extraction |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for semantic search |
| Azure AI Search | S1 (3 replicas) | Hybrid search with semantic reranking |
| Azure Functions | Premium EP1 | Application orchestration and API hosting |
| Azure Speech Services | Whisper STT | Call recording transcription |
| Azure Cosmos DB | Serverless, multi-partition | Articles, versions, feedback, approval state |
| Azure Blob Storage | Hot tier, versioning | Call recordings, transcripts, media |
| Azure Redis Cache | P1 Premium | Search result caching, session state |
| Azure Event Grid | System topics | Article lifecycle and transcript arrival triggers |
| Azure Bot Service | S1 Standard | Conversational self-service channel |
| Azure SignalR Service | Serverless mode | Real-time article suggestions for agents |
| Azure Front Door | WAF + CDN + SSL | Global load balancing, DDoS protection |
| Azure API Management | Standard | Rate limiting, auth, API gateway |
| Azure Key Vault | Standard, RBAC | Secrets and certificate management |
| Application Insights | Pay-as-you-go | APM, distributed tracing |
| Log Analytics | Pay-as-you-go | Centralized logging and KQL queries |

---

## Prerequisites

- **Azure Subscription** with Contributor access
- **Azure CLI** >= 2.50.0
- **Terraform** >= 1.5.0
- **Python** >= 3.11
- **Azure Functions Core Tools** >= 4.x
- **Node.js** >= 18 (for frontend builds)
- Azure OpenAI resource with GPT-4o and text-embedding-ada-002 deployed
- Azure AI Search resource with semantic ranker enabled

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-23-knowledge-base-contact-center

# Copy environment template and fill in values
cp .env.example .env
```

### 2. Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export AZURE_SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
```

### 3. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 4. Deploy Application

```bash
cd ../src
pip install -r requirements.txt
func azure functionapp publish <function-app-name>
```

### 5. Verify Deployment

```bash
curl https://<function-app-name>.azurewebsites.net/api/health
```

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run unit tests
cd tests
pytest test_function_app.py -v

# Run comprehensive tests
pytest test_comprehensive.py -v

# Run with coverage
pytest --cov=src --cov-report=html -v
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Entra ID (Azure AD) with OAuth2/OIDC for all users; Azure Bot Service uses Secure DirectLine token
- **Authorization**: RBAC with tiered roles -- Author (edit), Agent (read), Customer (filtered self-service)
- **Managed Identity**: System-assigned managed identity for all service-to-service authentication; zero credential storage
- **Network Isolation**: Private VNET (10.0.0.0/16) with 3-subnet topology (Application/Data/Integration); all PaaS services behind Private Link endpoints; NSG rules enforce least-privilege traffic flow
- **Perimeter Protection**: Azure Front Door with WAF (OWASP 3.2), DDoS Protection Standard, geo-filtering

### Encryption

- **Data at Rest**: AES-256 encryption via Azure Storage Service Encryption (SSE); Customer-Managed Keys (CMK) via Key Vault for sensitive data
- **Data in Transit**: TLS 1.2+ enforced on all service endpoints; HTTPS-only for all API and frontend traffic
- **Key Management**: Azure Key Vault with RBAC access policies, soft delete, and purge protection; automatic key rotation

### Monitoring

- **Application Insights**: Full APM with distributed tracing across Azure Functions, OpenAI calls, and Search queries
- **Log Analytics**: Centralized log aggregation with 90-day retention; KQL queries for operational troubleshooting
- **Alerts**: Azure Monitor alert rules for search latency (P95 < 500ms), function failures, OpenAI quota usage, and article authoring endpoint health
- **Dashboards**: Azure Monitor dashboards for article freshness trends, search hit rates, knowledge gap detection metrics, and cost management

### Visualization

- **Prompt Flow Tracing**: Azure AI Studio Prompt Flow for tracing and debugging GenAI pipeline interactions
- **Cost Management Dashboard**: Azure Cost Management for per-service spend tracking and budget alerts
- **Author Dashboard**: Custom React portal showing article freshness scores, gap reports, and approval workflow status

### Tracking

- **Request Tracing**: End-to-end correlation IDs propagated through APIM, Azure Functions, OpenAI, and AI Search via Application Insights
- **Audit Logs**: Article lifecycle events tracked (create, edit, publish, archive) in Cosmos DB and Azure Activity Log
- **Event-Driven Tracking**: Event Grid captures transcript upload events and article state transitions for full pipeline observability

### Accuracy

- **Semantic Reranking**: Cross-encoder reranking via Azure AI Search semantic ranker for precision in article retrieval
- **Freshness Scoring**: Algorithmic scoring (0-100) weighing article age, edit frequency, usage rate, negative feedback ratio, and manual accuracy flags
- **Gap Detection Thresholds**: Reranker score < 1.5 flags weak coverage; < 0.5 flags missing coverage entirely
- **Confidence Controls**: GPT-4o temperature set to 0.3 for factual tasks (search, gap detection) and 0.4 for authoring to balance creativity with accuracy

### Explainability

- **Search Score Transparency**: Each article result includes both the BM25 search score and the semantic reranker score, allowing agents and authors to understand why an article was surfaced
- **Coaching Tips**: The agent-assist engine provides natural language coaching tips explaining how the suggested articles relate to the live call context
- **Gap Detection Reports**: Each identified knowledge gap includes the best match score and a "missing" vs. "weak" coverage label to explain why a new article is needed

### Responsibility

- **Content Filtering**: Azure OpenAI responsible AI filters enabled for all generative calls to prevent generation of harmful, biased, or off-brand content
- **PII Masking**: Automated PII redaction applied to call transcripts before storage and before use in knowledge gap analysis
- **Approval Workflows**: Multi-step article review via Durable Functions ensures all GenAI-generated content is reviewed by a subject matter expert before publication
- **Bias Monitoring**: Article feedback data is analyzed for patterns that may indicate biased or inaccurate content across customer segments

### Interpretability

- **Feature Importance in Freshness Scoring**: The freshness score breaks down into weighted components (age decay, negative feedback ratio, view count, inaccuracy flag) so authors understand exactly which factor drives a low score
- **Hybrid Search Decomposition**: Results from vector search and keyword search are visible separately before fusion, enabling debugging of retrieval quality
- **Decision Transparency**: FAQ generation returns the source transcript count and the confidence of each generated FAQ entry

### Portability

- **Infrastructure as Code**: All Azure resources provisioned via Terraform (infra/main.tf) for repeatable, version-controlled deployments
- **Containerization**: Azure Functions run on Python 3.11 with requirements.txt dependency management; compatible with Docker container deployment
- **Multi-Cloud Considerations**: Core logic uses standard OpenAI Python SDK; search and database layers are abstracted behind service clients for potential portability
- **Environment Parity**: Development, staging, and production environments defined in Terraform variables with SKU-tier differentiation (basic/standard/premium)

---

## Project Structure

```
project-23-knowledge-base-contact-center/
|-- docs/
|   +-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   +-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py          # Azure Functions application (6 core functions)
|-- tests/
|   |-- test_function_app.py     # Unit tests
|   +-- test_comprehensive.py    # Comprehensive integration tests
+-- README.md                    # This file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Hybrid vector + keyword search for knowledge articles |
| POST | `/api/agent-suggest` | Real-time article suggestions during live calls |
| POST | `/api/detect-gaps` | Knowledge gap detection from batch call transcripts |
| POST | `/api/generate-faq` | Auto-generate FAQ articles from call transcript patterns |
| POST | `/api/author-article` | GenAI-assisted knowledge article authoring |
| GET  | `/api/health` | Health check endpoint |
| Event | `TranscriptUploadTrigger` | Event Grid trigger for new transcript blob uploads |

### Example: Search Knowledge Base

```bash
curl -X POST https://<function-app>/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I reset a customer password?",
    "top_k": 5
  }'
```

### Example: Generate Agent Suggestions

```bash
curl -X POST https://<function-app>/api/agent-suggest \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_segment": "Customer is asking about refund policy...",
    "customer_context": {
      "tier": "gold",
      "product": "Premium Plan",
      "previous_contacts": 3
    }
  }'
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.
