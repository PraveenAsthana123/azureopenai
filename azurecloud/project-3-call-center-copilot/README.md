# Automated Call Center Copilot (Voice + Chat)

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-00A4EF?style=flat&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

A multilingual conversational AI platform for call centers that handles voice calls and chat, providing real-time transcription, automatic language detection, intent classification, RAG-based knowledge search, sentiment analysis, and post-call summarization. The system supports 100+ languages with seamless agent handoff and scores call quality across five dimensions (professionalism, resolution effectiveness, response time, empathy, knowledge). Designed for production call center operations with PCI DSS compliance and DTMF masking.

## Architecture

```
Customer Channels (Phone / Web Chat / Teams / WhatsApp)
        |
   Azure Communication Services (Voice + IVR)
        |
   Real-Time Processing Layer
   |                          |
Voice Pipeline             Text Pipeline
(Speech-to-Text)          (Language Detection)
   |                          |
   +---- Translation (if non-English) ----+
                     |
              SignalR Hub (Real-time Stream)
                     |
              Conversation AI Engine
   +----+----+----+----+
   |         |         |         |
Intent    RAG        Sentiment  Response
Classify  Search     Analysis   Translation
(GPT-4o)  (AI Search (GPT-4o)  (Translator)
           + GPT-4o)
        |
   +----+----+----+
   |         |         |
Text       Voice      Agent
Response   Response   Dashboard
(Chat)     (TTS)      (Real-time)
        |
   Post-Call Analytics
   (Summarize + Quality Score + Action Items)
        |
   Cosmos DB + Power BI Dashboards
```

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o, text-embedding-ada-002 | Conversations, intent classification, summarization, quality scoring |
| Azure Communication Services | Standard | Voice calls, PSTN, IVR, call recording |
| Azure Speech Services | S0 | Real-time speech-to-text, neural text-to-speech |
| Azure Translator | S1 | 100+ language translation |
| Azure Language Service | S0 | Language detection |
| Azure AI Search | S1 | Knowledge base RAG retrieval |
| Azure Cosmos DB | Serverless | Transcripts, conversations, call summaries |
| Azure Cache for Redis | Premium | Response caching, session management |
| Azure SignalR | Serverless | Real-time streaming to agent dashboard |
| Azure Key Vault | Standard | Secrets, speech keys, connection strings |
| Azure Functions | Premium EP1 (Python 3.11) | API endpoints and processing |
| Application Insights | Pay-as-you-go | Call analytics and telemetry |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50
- Terraform >= 1.5
- Python 3.11+
- Azure OpenAI resource with GPT-4o deployment
- Azure Speech Services resource
- Azure Communication Services resource (for voice)

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-3-call-center-copilot

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

func start
```

### 4. Send a chat message

```bash
curl -X POST http://localhost:7071/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help with my order status",
    "call_id": "call-001",
    "language": "en"
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

- **Authentication**: Azure Entra ID (SSO) for agent authentication; customer identity verified through Communication Services
- **Authorization**: Role-based access for agents, supervisors, and QA reviewers; function-level auth keys for API endpoints
- **Managed Identity**: System-assigned managed identity for all service-to-service communication -- zero stored credentials
- **Network Isolation**: Public-facing endpoints behind WAF with DDoS protection; backend services (Cosmos DB, AI Search, OpenAI) via Private Link
- **PCI DSS**: Payment handling zones isolated; DTMF masking prevents card digits from appearing in recordings or transcripts
- **Content Safety**: Real-time content filtering on all AI-generated responses

### Encryption

- **Data at Rest**: AES-256 encryption for all call recordings, transcripts, and conversation data in Blob Storage and Cosmos DB
- **Data in Transit**: TLS 1.2+ end-to-end encryption for voice streams, chat messages, and all inter-service communication
- **Key Management**: Azure Key Vault for speech keys, connection strings, and certificates with RBAC and soft-delete

### Monitoring

- **Application Insights**: Full telemetry for call processing latency, STT/TTS performance, and GPT-4o response times
- **Log Analytics**: Centralized call processing logs; KQL queries for call pattern analysis and agent performance
- **Alerts**: Alerts on transcription failures, high-latency responses, sentiment score drops, and service degradation
- **Dashboards**: Azure Monitor workbooks for real-time call volume, average handle time, and resolution rates

### Visualization

- **Power BI**: Executive dashboards for call analytics -- volume trends, sentiment distribution, quality scores, resolution rates
- **Agent Dashboard**: Real-time web dashboard (via SignalR) showing live transcript, AI-suggested responses, and customer sentiment

### Tracking

- **Request Tracing**: Correlation IDs assigned per call/session, propagated through transcription, translation, and generation stages
- **Conversation Logs**: Every conversation turn stored in Cosmos DB with call ID, intent, sentiment, language, and timestamp
- **Call Recording Audit**: Recording metadata tracked from upload through transcription and summarization

### Accuracy

- **Transcription Quality**: Azure Speech Services with speaker diarization and word-level timestamps; interim and final result streaming
- **Intent Classification**: GPT-4o classification with confidence scores; five intent categories (FAQ, transactional, complaint, escalation, general)
- **Quality Scoring**: Five-dimension scoring (0-100): professionalism, resolution effectiveness, response time, empathy, knowledge
- **Sentiment Thresholds**: Configurable thresholds -- positive (>0.6), negative (<-0.3) -- for real-time escalation triggers

### Explainability

- **Intent Transparency**: Intent classification returns the intent label, confidence score, and suggested action for every message
- **Quality Breakdown**: Call quality scores are broken down by dimension with specific improvement recommendations
- **Summarization Structure**: Post-call summaries include distinct sections for summary, action items, topics discussed, sentiment, and resolution status
- **Source Citations**: RAG-based responses cite knowledge base articles used to generate the answer

### Responsibility

- **Content Filtering**: Azure AI Content Safety filters applied to all AI-generated responses sent to customers
- **Call Recording Consent**: Two-party consent compliance; both parties notified when recording is active
- **Bias Monitoring**: Sentiment and quality scoring monitored across customer demographics for fairness
- **Accessibility**: Real-time translation supports 100+ languages for non-English speakers; ADA compliance for hearing-impaired customers

### Interpretability

- **Sentiment Scoring**: Sentiment analysis returns label (positive/negative/neutral/mixed), numeric score (-1.0 to 1.0), and key phrases driving the assessment
- **RAG Source Scores**: Knowledge base search results include document title, category, and relevance score
- **Decision Trace**: Full conversation processing trace available in Application Insights -- from language detection through intent classification to response generation

### Portability

- **Infrastructure as Code**: All resources defined in Terraform with environment parameterization
- **Containerization**: Azure Functions compatible with Docker for local development and hybrid deployment
- **Multi-Channel**: Bot Framework integration supports Teams, Slack, Web Chat, and WhatsApp from a single codebase
- **Latency Budget**: Documented latency targets per stage (STT ~200ms, Translation ~100ms, GPT-4o ~1000ms, TTS ~200ms) for SLA management

## Project Structure

```
project-3-call-center-copilot/
|-- data/
|   +-- Call Center Data.csv         # Sample call center dataset
|-- docs/
|   +-- ARCHITECTURE.md             # Detailed architecture documentation
|-- infra/
|   +-- main.tf                     # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py             # Azure Functions: transcribe, detect-language,
|                                   #   translate, chat, summarize-call, quality-score
|-- tests/
|   |-- test_function_app.py        # Unit tests for all endpoints
|   +-- test_comprehensive.py       # Integration and pipeline tests
+-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transcribe` | Submit audio for batch transcription (returns transcription ID) |
| `POST` | `/api/detect-language` | Detect language of input text |
| `POST` | `/api/translate` | Translate text between 100+ languages |
| `POST` | `/api/chat` | Send a customer message -- returns intent, sentiment, RAG response |
| `POST` | `/api/summarize-call` | Generate post-call summary with action items and topics |
| `POST` | `/api/quality-score` | Score call quality across 5 dimensions (0-100) |
| `GET` | `/api/calls/{call_id}` | Retrieve a call summary record |
| `GET` | `/api/health` | Health check -- returns service status and version |
| Event Grid | `CallRecordingTrigger` | Auto-triggered on recording upload; initiates transcription pipeline |

### POST /api/chat

**Request:**
```json
{
  "message": "Necesito ayuda con mi pedido",
  "call_id": "call-001",
  "language": "es"
}
```

**Response:**
```json
{
  "call_id": "call-001",
  "response": "I'd be happy to help with your order. Could you provide your order number?",
  "intent": {"intent": "transactional", "confidence": 0.91, "suggested_action": "lookup_order"},
  "sentiment": {"sentiment": "neutral", "score": 0.1, "key_phrases": ["need help", "order"]},
  "sources": [{"title": "Order FAQ", "category": "orders", "score": 0.88}],
  "usage": {"prompt_tokens": 800, "completion_tokens": 45, "total_tokens": 845}
}
```

## License

This project is licensed under the MIT License.
