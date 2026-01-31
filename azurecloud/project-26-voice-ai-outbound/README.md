# Project 26: Voice AI Outbound Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat&logo=openai&logoColor=white)
![Communication Services](https://img.shields.io/badge/Azure%20Comm%20Services-Voice%20Calling-teal?style=flat)
![Speech Services](https://img.shields.io/badge/Azure%20Speech-Neural%20TTS+STT-green?style=flat)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-Serverless-green?style=flat&logo=microsoftazure)
![Redis](https://img.shields.io/badge/Redis-DNC%20Cache-red?style=flat&logo=redis&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

---

## Overview

An AI-powered outbound voice platform for proactive customer engagement that leverages Azure OpenAI GPT-4o for GenAI-scripted outbound calls with real-time conversation steering, Azure Communication Services for voice calling with call recording and voicemail detection, and Azure Speech Services for neural text-to-speech (en-US-JennyNeural) and real-time speech-to-text (Whisper). The platform enables campaign-driven outbound dialing with conversational AI, intelligent call scheduling based on customer availability patterns, TCPA/DNC compliance management, voicemail detection and message drop, sentiment-based escalation to human agents, and multilingual voice support.

Key configuration parameters: `MAX_RETRY_ATTEMPTS=3`, `MAX_CALL_DURATION_SECONDS=600`, `VOICEMAIL_DETECTION_TIMEOUT_MS=5000`, `SENTIMENT_ANALYSIS_INTERVAL_SECONDS=10`, `CALL_THROTTLE_PER_MINUTE=30`.

---

## Architecture

```
+---------------------+    +---------------------+    +---------------------+
|  Campaign Mgmt      |    |  Agent Desktop      |    |  Analytics          |
|  Portal (React)     |    |  (React/SignalR)    |    |  Dashboard (PBI)    |
+---------+-----------+    +---------+-----------+    +---------+-----------+
          |                          |                          |
          +------------- Azure Front Door (WAF + CDN) ---------+
                                     |
                    +----------------+----------------+
                    |                |                |
              APIM Gateway    Static Web App    Power BI Embedded
                    |
          +---------+--------------------------------------------------+
          |         PRIVATE VNET (10.0.0.0/16)                         |
          |                                                             |
          |   Application Subnet (10.0.1.0/24):                        |
          |   - Azure Functions (Call Orchestrator, Campaign Engine,   |
          |     Schedule Optimizer, Compliance Engine)                  |
          |   - Azure OpenAI (GPT-4o) - Script Gen + Conversation     |
          |   - Azure Bot Service (Dialog Management)                   |
          |                                                             |
          |   Voice Services Subnet (10.0.2.0/24):                     |
          |   - Azure Communication Services (Voice, Recording, DTMF) |
          |   - Azure Speech Services (Neural TTS + Whisper STT)       |
          |   - Azure AI Language (Sentiment + Intent Detection)        |
          |   - Service Bus (Call Queue Mgmt, Priority Routing)         |
          |                                                             |
          |   Data Subnet (10.0.3.0/24):                               |
          |   - Cosmos DB (Campaigns, Call Logs, Scripts)               |
          |   - Blob Storage (Recordings, Voicemail, Exports)           |
          |   - Redis Cache (DNC List, Call State, Rate Limits)         |
          |                                                             |
          |   Integration Subnet (10.0.4.0/24):                        |
          |   - Key Vault, Event Hub, Stream Analytics                  |
          +-------------------------------------------------------------+
```

---

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Script generation, real-time conversation steering, outcome classification |
| Azure Communication Services | Voice Calling SDK | Outbound dialing, call recording (dual-channel), DTMF, voicemail detection |
| Azure Speech Services | Neural TTS (en-US-JennyNeural) | Natural voice synthesis, multilingual TTS |
| Azure Speech Services | Whisper STT | Real-time speech-to-text transcription |
| Azure AI Language | Sentiment Analysis v3 | Real-time sentiment scoring for escalation triggers |
| Azure Bot Service | Bot Framework Composer | Dialog management, conversation flow control |
| Azure Functions | Premium EP2 | Call orchestration, compliance gating, scheduling |
| Durable Functions | Campaign Engine | Campaign scheduling, call list processing, retry logic |
| Azure Cosmos DB | Multi-region, serverless | Campaign data, call logs, scripts, CDR |
| Azure Blob Storage | Hot + Cool, immutable | Call recordings, voicemail audio, compliance exports |
| Azure Redis Cache | P1 Premium (6GB) | DNC list cache, active call state, rate limiting |
| Azure Service Bus | Premium, partitioned queues | Call queue management, priority routing, dead letter handling |
| Azure Event Hub | Standard (4 partitions) | Real-time call event ingestion for analytics |
| Azure Stream Analytics | 6 SU | Real-time aggregation of call metrics, windowed analytics |
| Power BI Embedded | A2 | Real-time call KPIs, campaign performance, sentiment trends |
| Azure Front Door | WAF + SSL | Global load balancing, DDoS protection, geo-filtering (US-only) |
| Azure API Management | Standard | API gateway, rate limiting, request routing |
| Azure Key Vault | Standard, RBAC | API keys, connection strings, CMK for recordings |
| Application Insights | Workspace-based | APM, distributed tracing, call performance metrics |
| Log Analytics | 90-day retention | Centralized logging, KQL queries, compliance audit |

---

## Prerequisites

- **Azure Subscription** with Contributor access
- **Azure CLI** >= 2.50.0
- **Terraform** >= 1.5.0
- **Python** >= 3.11
- **Azure Functions Core Tools** >= 4.x
- Azure OpenAI resource with GPT-4o deployed
- Azure Communication Services resource with phone numbers provisioned (toll-free + local DIDs)
- Azure Speech Services resource with neural TTS and Whisper STT enabled
- Redis Cache instance accessible from the VNET

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-26-voice-ai-outbound

# Copy environment template and fill in values
cp .env.example .env
```

### 2. Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export COMMUNICATION_SERVICES_ENDPOINT="https://<your-acs>.communication.azure.com"
export SPEECH_ENDPOINT="https://<your-speech>.cognitiveservices.azure.com/"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
export REDIS_HOST="<your-redis>.redis.cache.windows.net"
export SERVICE_BUS_CONNECTION="<service-bus-connection-string>"
export EVENT_HUB_CONNECTION="<event-hub-connection-string>"
export DEFAULT_CALLER_ID="+1XXXXXXXXXX"
export AGENT_QUEUE_NUMBER="+1XXXXXXXXXX"
export WEBSOCKET_ENDPOINT="wss://<your-websocket-endpoint>"
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

### 6. Pre-Deployment Validation

The deployment strategy includes pre-deploy health checks that must pass:
- DNC cache is populated in Redis
- Speech Services endpoints are healthy
- ACS phone numbers are active and verified

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

- **Authentication**: Entra ID SSO with OAuth2/OIDC for campaign operators; MFA enforced for all admin actions; Conditional Access policies scoped by device and location
- **Authorization**: RBAC role separation for Campaign Operators, Compliance Officers, and Agent Supervisors
- **Managed Identity**: System-assigned managed identity for passwordless authentication across all Azure resources (OpenAI, Cosmos DB, ACS, Redis, Key Vault)
- **Network Isolation**: Private VNET (10.0.0.0/16) with 4-subnet topology (App/Voice/Data/Integration); all PaaS services behind Private Link; NSG rules enforce least-privilege traffic between voice and data subnets
- **Perimeter Protection**: Azure Front Door with WAF (OWASP 3.2), DDoS Protection Standard, geo-filtering restricted to US for TCPA-scoped operations
- **PIM**: Privileged Identity Management for just-in-time elevated access for compliance admin roles
- **TCPA Compliance Gate**: Three-layer pre-dial compliance check (DNC list, time zone window, consent status) executed before any outbound call is placed

### Encryption

- **Data at Rest**: AES-256 encryption via SSE across Cosmos DB, Blob Storage, and Redis; Customer-Managed Keys (CMK) via Key Vault specifically for call recordings and compliance exports
- **Data in Transit**: TLS 1.3 enforced on all service endpoints, voice media streams, and WebSocket connections
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection; CMK rotation for recording encryption keys
- **Immutable Storage**: Call recordings stored in WORM-compliant immutable Blob Storage for regulatory retention

### Monitoring

- **Application Insights**: Workspace-based APM with distributed tracing across call orchestration, OpenAI script generation, ACS voice calls, Speech Services, and sentiment analysis
- **Log Analytics**: Centralized logging with 90-day retention; KQL queries for compliance audit, call performance analysis, and debugging
- **Alerts**: Azure Monitor alert rules for call failure rates, sentiment escalation triggers, DNC cache freshness, Service Bus dead-letter queue depth, and ACS concurrent call limits
- **Stream Analytics**: Real-time windowed aggregation of call metrics (answer rates, average duration, sentiment distribution) streamed to Power BI

### Visualization

- **Power BI Embedded**: Real-time call KPI dashboards showing campaign performance, outcome distribution, conversion rates, sentiment trends, and escalation rates
- **Agent Desktop**: React-based agent workspace with SignalR push for live call monitoring, full conversation transcript, and escalation context
- **Campaign Analytics**: Interactive reporting for outcome classification distribution, callback rates, DNC request tracking, and average customer interest scores

### Tracking

- **Request Tracing**: End-to-end correlation IDs propagated from APIM through Azure Functions, Service Bus, ACS voice calls, and Event Hub via Application Insights
- **Call Detail Records**: Every call logged in Cosmos DB with full lifecycle events (initiated, connected, speech detected, sentiment shift, escalated, ended, classified)
- **Audit Logs**: Immutable WORM-compliant audit logs in Log Analytics for 7-year regulatory retention covering all call actions, DNC checks, and compliance decisions
- **DNC Compliance Trail**: Every DNC check result (federal, state, internal, time zone, frequency) persisted with timestamp for regulatory evidence

### Accuracy

- **Outcome Classification Confidence**: GPT-4o classifies call outcomes into 10 categories (sale_completed, callback_requested, not_interested, etc.) with a 0-1 confidence score and a 0-10 customer interest score
- **Voicemail Detection**: Multi-signal detection using tone analysis, greeting duration (>3s), silence duration, and speech pattern classification with 0.7-0.95 confidence range
- **Sentiment Thresholds**: Real-time sentiment analysis every 5 conversation turns; risk level (low/medium/high) with automatic escalation at "high" risk
- **Compliance Accuracy**: DNC list refreshed hourly in production (configurable: 24h dev, 6h staging, 1h prod); federal + state + internal lists checked with sub-millisecond Redis lookups

### Explainability

- **Script Generation Transparency**: Each generated call script includes structured sections (opening, value proposition, objection responses, closing, voicemail script) with metadata showing the campaign and customer profile inputs used
- **Conversation Steering Rationale**: Real-time steering guidance includes the recommended strategy (empathetic/direct/consultative), whether to deviate from script and why, and a confidence score for call success
- **Outcome Classification Detail**: Each classified outcome includes a natural language summary of what happened, follow-up action recommendations, and the single most important next-best-action
- **Sentiment Trend Reporting**: Sentiment analysis returns not just the current score but the trend (improving/stable/declining), key moments of sentiment shift, and detected customer emotions (frustrated, interested, confused)

### Responsibility

- **Content Filtering**: Azure OpenAI responsible AI filters enabled for all script generation to prevent manipulative, deceptive, or high-pressure sales language
- **TCPA Compliance**: Automated calling hours enforcement (8am-9pm local time per recipient); prior express consent verification; STIR/SHAKEN caller ID authentication to prevent spoofing
- **DNC Respect**: Federal, state (all 50 states), and internal Do-Not-Call lists enforced; customers who say "do not call" during a call are automatically added to the internal DNC list
- **Recording Consent**: Dual-party consent auto-announcement in required states; no voice biometric data collection without explicit consent
- **Call Frequency Limits**: MAX_RETRY_ATTEMPTS=3 per phone number within a 30-day window to prevent harassment
- **Opt-Out Mechanisms**: Multiple opt-out channels supported -- DTMF keypress, voice command, or post-call SMS

### Interpretability

- **Compliance Check Decomposition**: Each DNC compliance check returns individual results for federal DNC, state DNC, internal DNC, time zone compliance, and call frequency compliance, enabling operators to see exactly which check passed or failed
- **Call Outcome Categories**: The 10-category outcome classification system provides clear, mutually exclusive labels (sale_completed, callback_requested, not_interested, objection_unresolved, voicemail_left, no_answer, wrong_number, do_not_call, escalated, technical_failure) with no ambiguous catch-all
- **Campaign Analytics Breakdown**: Analytics endpoint returns per-campaign outcome distribution, conversion rate, callback rate, escalation rate, average interest score, and DNC request count -- all derived from transparent aggregation logic
- **Escalation Decision Chain**: When escalation occurs, the full decision chain is visible: sentiment score that triggered it, the recommendation from sentiment analysis, and the complete conversation context handed off to the agent

### Portability

- **Infrastructure as Code**: All Azure resources provisioned via Terraform (infra/main.tf) with environment-specific parameters (max_concurrent_calls, dnc_refresh_interval) for dev/staging/production
- **Containerization**: Azure Functions on Python 3.11 with standard pip dependencies; compatible with Docker container deployment for AKS or ACA
- **Multi-Cloud Considerations**: Core script generation and outcome classification use standard OpenAI Python SDK; voice calling layer is ACS-specific but abstracted behind the call orchestrator for potential SIP trunk or Twilio migration
- **Multi-Language Voice Support**: Platform supports 5 languages (en-US, es-US, fr-CA, de-DE, pt-BR) via configurable TTS voice and STT model parameters
- **Blue-Green Deployment**: Blue-green strategy with 5% canary and pre-deploy checks (DNC cache, Speech Services, ACS phone numbers) for zero-downtime voice platform releases

---

## Project Structure

```
project-26-voice-ai-outbound/
|-- docs/
|   +-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   +-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py          # Azure Functions application (6 core + 2 trigger functions)
|-- tests/
|   |-- test_function_app.py     # Unit tests
|   +-- test_comprehensive.py    # Comprehensive integration tests
+-- README.md                    # This file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate-script` | Generate a personalized outbound call script |
| POST | `/api/check-compliance` | Check DNC/TCPA compliance for a phone number |
| POST | `/api/initiate-call` | Initiate an outbound voice call (includes pre-flight compliance check) |
| POST | `/api/classify-outcome` | Classify the outcome of a completed call |
| POST | `/api/schedule-call` | Get AI-optimized call scheduling for a customer |
| POST | `/api/campaign-analytics` | Get analytics for an outbound calling campaign |
| GET  | `/api/health` | Health check endpoint |
| Queue | `OutboundCallQueueProcessor` | Service Bus trigger for outbound call queue processing |
| Event | `CallEventAnalytics` | Event Hub trigger for real-time call event analytics |

### Example: Generate Call Script

```bash
curl -X POST https://<function-app>/api/generate-script \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_data": {
      "campaign_id": "camp-001",
      "product": "Premium Support Plan",
      "objective": "upsell",
      "talking_points": ["24/7 support", "dedicated account manager", "SLA guarantee"]
    },
    "customer_profile": {
      "customer_id": "cust-123",
      "name": "John Smith",
      "current_plan": "Basic",
      "tenure_months": 18,
      "support_tickets_last_90d": 5
    }
  }'
```

### Example: Check DNC Compliance

```bash
curl -X POST https://<function-app>/api/check-compliance \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+12125551234"
  }'
```

### Example: Initiate Outbound Call

```bash
curl -X POST https://<function-app>/api/initiate-call \
  -H "Content-Type: application/json" \
  -d '{
    "customer_data": {
      "customer_id": "cust-123",
      "phone_number": "+12125551234",
      "caller_id": "+18005551000"
    },
    "script": {
      "opening": "Hi, this is Sarah from Acme Corp...",
      "value_proposition": "I am calling about your Premium Support upgrade..."
    }
  }'
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.
