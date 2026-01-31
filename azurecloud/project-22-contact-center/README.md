# Project 22: AI Contact Center Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat)
![Communication Services](https://img.shields.io/badge/Communication%20Services-Voice%20%7C%20Chat-green?style=flat)
![Speech Services](https://img.shields.io/badge/Speech%20Services-Real--time%20STT-orange?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-yellow?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise AI-powered contact center platform that delivers omnichannel customer engagement across voice, chat, email, and social media. The system leverages Azure Communication Services for real-time voice and messaging, Azure Speech Services for live transcription in 100+ languages, Azure OpenAI GPT-4o for intelligent agent assist and automated responses, and Azure AI Search for knowledge base retrieval. Key capabilities include intelligent skill-based call routing, real-time customer sentiment analysis, automated post-call summarization, GenAI-powered email/chat auto-responses, AI-driven quality management scoring, and supervisor real-time dashboards with live metrics.

## Architecture

```
Customer Channels: Voice/PSTN | Web Chat | Email | Social Media
                              |
                    Azure Front Door (WAF + Geo-routing)
                              |
            +-----------------+-----------------+
            |                 |                 |
       APIM Gateway     Azure Bot Service   SignalR Service
       (Auth, Rate)     (IVR/Chat)          (Real-time Push)
            |                 |
            +---------+-------+
                      |
             Azure Functions (Contact Center Orchestrator)
                      |
    +---------+-------+-------+---------+
    |         |       |       |         |
Call Router  Agent   Auto-  Post-Call  QA Scoring
             Assist  Resp   Summary
    |         |       |       |         |
    |    +----+----+  |       |         |
    |    | GPT-4o  |  |    GPT-4o     GPT-4o
    |    |AI Search|  |       |         |
    |    +---------+  |       |         |
    |                 |       |         |
Azure Communication Services     Azure Speech Services
(Voice/Chat/SMS)                 (Real-time STT/TTS)
            |                         |
    Azure Translator          Event Hub (Transcript Stream)
    (100+ Languages)                  |
                              Stream Analytics
                              (Real-time Aggregation)
                                      |
    Cosmos DB | Blob Storage | Redis Cache | Power BI
    (History)   (Recordings)   (Agent State)  (Dashboards)
```

**Key Components:**
- **Agent Desktop** (React + TypeScript SPA) -- Unified agent workspace with real-time assist
- **Supervisor Dashboard** (React + Power BI Embedded) -- Live queue monitoring, KPI dashboards
- **Azure Functions** (Python 3.11 / Node.js 20) -- Call routing, agent assist, auto-response, summarization, QA scoring
- **Azure Communication Services** -- PSTN voice, web chat, email, SMS channels

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Agent assist, auto-responses, summarization, QA scoring, routing |
| Azure OpenAI (text-embedding-ada-002) | Vector embeddings for knowledge base search |
| Azure Communication Services | Inbound/outbound voice, PSTN, web chat, email, SMS |
| Azure Speech Services (Real-time STT/TTS) | Live call transcription and IVR text-to-speech |
| Azure Translator (Neural MT) | Real-time multilingual transcription and translation (100+ languages) |
| Azure AI Search | Knowledge base hybrid search for agent assist |
| Azure Cognitive Services | Real-time customer sentiment and intent detection |
| Azure Bot Service | IVR system with AI deflection and chat widget |
| Azure Cosmos DB | Call history, agent sessions, routing rules, analytics |
| Azure Blob Storage | Call recordings, transcripts, compliance archives |
| Azure Redis Cache | Agent state, active call metadata, session cache |
| Azure Event Hub | Real-time telemetry stream for transcripts and events |
| Azure Stream Analytics | Real-time aggregation of call metrics and sentiment scores |
| Azure SignalR Service | Sub-second push to agent desktops and supervisor dashboards |
| Power BI Embedded | Supervisor dashboards, historical reporting |
| Application Insights | APM, distributed tracing across call flows |
| Log Analytics | Centralized logging for all contact center services |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- Node.js >= 20 (for orchestrator and frontend)
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- Azure Communication Services resource with PSTN numbers
- Azure Speech Services resource

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-22-contact-center

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Copy environment template and configure
cp .env.example .env
```

### Environment Variables

```bash
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
SPEECH_ENDPOINT=https://<your-speech>.cognitiveservices.azure.com/
TRANSLATOR_ENDPOINT=https://<your-translator>.cognitiveservices.azure.com/
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
COSMOS_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/
COMMUNICATION_SERVICES_ENDPOINT=https://<your-acs>.communication.azure.com
EVENT_HUB_CONNECTION=<event-hub-connection-string>
SIGNALR_CONNECTION=<signalr-connection-string>
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

- **Authentication**: Azure Entra ID (SSO) with Conditional Access (device + location) and MFA enforcement for all agent logins
- **Authorization**: RBAC with role separation for Agent, Supervisor, Admin, and QA Analyst; PIM for just-in-time supervisor and admin access elevation
- **Managed Identity**: System-assigned managed identity for zero-credential service-to-service authentication across all services
- **Network Isolation**: Dedicated VNet with 5-subnet topology (Application, Communication, Data, Streaming, Integration); all PaaS services behind Private Link; subnet-level NSG ACLs
- **PCI DSS Compliance**: Payment card data tokenized before reaching contact center; DTMF masking for card entry during voice calls; call recordings with payment segments auto-redacted
- **Bot Protection**: Azure Front Door WAF with bot protection rules for chat and web channels

### Encryption

- **Data at Rest**: AES-256 encryption for Cosmos DB, Blob Storage (call recordings), and Redis Cache; Customer-Managed Keys (CMK) via Key Vault
- **Data in Transit**: TLS 1.3 for all service communication; SRTP for end-to-end voice call encryption
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection for encryption keys and PSTN certificates
- **Call Recordings**: Immutable WORM-compliant Blob Storage with time-based retention policies; 90-day hot storage, 7-year archive for compliance

### Monitoring

- **Application Insights**: APM with 50% sampling, custom events, and distributed tracing across all call flows (voice, chat, email)
- **Log Analytics**: 90-day retention centralized logging for all contact center services
- **Alerts**: Azure Monitor custom metrics and alert rules for SLA breach (99.95% target), average handle time (>300s), sentiment threshold (<0.3), and abandon rate (>5%)
- **Security Monitoring**: Azure Sentinel SIEM for contact center security event correlation; Defender for Cloud for continuous threat detection

### Visualization

- **Supervisor Dashboard**: Power BI Embedded with real-time queue monitoring, agent utilization, KPI dashboards, and historical reporting
- **Agent Desktop**: React SPA with live sentiment indicators, suggestion panels, and call metrics
- **Cost Management Dashboard**: Azure Cost Management for per-channel cost tracking

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across call routing, transcription, sentiment analysis, and agent assist workflows
- **Correlation IDs**: End-to-end correlation from customer call initiation through IVR, routing, agent handling, and post-call analytics
- **Audit Logs**: PCI audit trail for all call recordings access; complete interaction history in Cosmos DB with timestamps and agent metadata
- **Recording Compliance**: Dual-party consent announcements auto-played via IVR; consent status tracked per interaction

### Accuracy

- **Speech Recognition**: Azure Speech Services custom models fine-tuned for domain-specific vocabulary to improve transcription accuracy
- **Sentiment Analysis**: Real-time sentiment scoring with escalation threshold (score < 0.3 triggers supervisor notification)
- **Quality Scoring**: AI quality scores calibrated against human QA auditor benchmarks; minimum quality threshold of 70/100
- **Routing Accuracy**: Skill-based routing decisions evaluated against resolution rates and customer satisfaction scores

### Explainability

- Agent assist suggestions include the source knowledge base articles, relevance scores, and resolution steps that informed the recommendation
- Quality scorecards break down scores into 7 categories (greeting, empathy, resolution, product knowledge, communication, compliance, hold/transfer) with specific strengths and improvement notes
- Post-call summaries include structured fields: customer issue, resolution, action items, key topics, and disposition code

### Responsibility

- **Content Filtering**: Azure OpenAI responsible AI filters enabled for all agent assist and auto-response generation
- **Customer Consent**: Dual-party and one-party consent state compliance for call recording; GDPR right-to-erasure API deletes all associated recordings and transcripts
- **Fair Treatment**: Routing algorithm monitored for equitable wait time distribution across customer segments
- **Accessibility**: ADA-compliant IVR, TTY/TDD support, and chat accessibility for customers with disabilities

### Interpretability

- **Routing Decisions**: Routing responses include target queue, required skills, priority level, estimated handle time, VIP flag, and a natural language explanation of the routing rationale
- **Sentiment Scoring**: Sentiment results include specific emotions detected, numeric score (-1.0 to 1.0), and escalation recommendation with reasoning
- **Quality Categories**: QA scores decompose into independently scored categories with coaching notes and compliance flags

### Portability

- **Containerization**: Azure Functions deployable as Docker containers for local development and testing
- **Infrastructure as Code**: Full Terraform configuration in `infra/` for reproducible multi-environment deployments (dev: 10 agents, staging: 50, production: 500)
- **Multi-Cloud Considerations**: Contact center patterns transferable; Speech-to-Text APIs compatible with alternatives (Google STT, AWS Transcribe); knowledge base search portable to Elasticsearch
- **Channel Flexibility**: Architecture supports adding new channels (WhatsApp, Facebook Messenger, Teams) via Azure Bot Service connectors
- **Standards**: TCPA, PCI DSS, GDPR, HIPAA compliance frameworks are cloud-agnostic

## Project Structure

```
project-22-contact-center/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (agent-assist, auto-response, summarize, QA, route, sentiment)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent-assist` | Real-time agent assist suggestions from transcript and knowledge base |
| POST | `/api/auto-response` | Generate AI auto-response for chat, email, or SMS channels |
| POST | `/api/summarize` | Post-call/chat interaction summarization with action items |
| POST | `/api/quality-score` | AI quality management scoring of agent interactions |
| POST | `/api/route` | Intelligent skill-based routing for incoming interactions |
| POST | `/api/sentiment` | Real-time customer sentiment analysis with escalation detection |
| POST | `/api/negotiate` | SignalR negotiate endpoint for agent desktop real-time connections |
| POST | `/api/broadcast-update` | Broadcast real-time update to agent desktop via SignalR |
| GET | `/api/health` | Health check endpoint |
| Event Hub | `CallEventProcessor` | Process real-time call events (started, transcript, ended) with agent desktop push |

## License

This project is licensed under the MIT License.
