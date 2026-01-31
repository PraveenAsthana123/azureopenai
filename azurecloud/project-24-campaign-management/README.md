# Project 24: AI Campaign Management Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat&logo=openai&logoColor=white)
![Azure ML](https://img.shields.io/badge/Azure%20ML-Segmentation+Propensity-orange?style=flat)
![Communication Services](https://img.shields.io/badge/Azure%20Comm%20Services-Email+SMS-teal?style=flat)
![Notification Hubs](https://img.shields.io/badge/Notification%20Hubs-Push-green?style=flat)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

---

## Overview

An enterprise-grade AI-powered campaign management platform that enables marketing teams to create, orchestrate, and optimize multi-channel campaigns (email, SMS, push notifications, in-app messages) using GenAI-driven content generation, intelligent audience segmentation, A/B testing optimization, predictive ROI modeling, and real-time performance analytics. The system leverages Azure OpenAI GPT-4o for campaign content generation across all channels, Azure ML for audience propensity scoring and micro-segmentation, Azure Communication Services for email and SMS delivery, and Azure Notification Hubs for push notifications across mobile platforms.

The platform supports the full campaign lifecycle from brief to post-campaign analytics, including budget optimization across campaigns, customer journey mapping, and automated suppression list management for regulatory compliance.

---

## Architecture

```
+---------------------+    +---------------------+    +---------------------+
|  Campaign Portal    |    |  Analytics Dashboard|    |  Mobile App         |
|  (React/Next.js)    |    |  (Power BI)         |    |  (React Native)     |
+---------+-----------+    +---------+-----------+    +---------+-----------+
          |                          |                          |
          +------------- Azure Front Door (WAF + CDN) ---------+
                                     |
                    +----------------+----------------+
                    |                |                |
              APIM Gateway    Static Web App    Azure SignalR
                    |                                (Real-time)
                    |
          +---------+--------------------------------------------------+
          |         PRIVATE VNET (10.0.0.0/16)                         |
          |                                                             |
          |   Application Subnet:                                       |
          |   - Azure Functions (Campaign Engine, Content Generator,    |
          |     A/B Test Engine, Journey Mapper, Budget Optimizer)      |
          |   - Azure OpenAI (GPT-4o) via Private Link                  |
          |   - Azure ML (Segmentation, Propensity, ROI Prediction)     |
          |                                                             |
          |   Channel Orchestration Subnet:                             |
          |   - Azure Communication Services (Email/SMS)                |
          |   - Azure Notification Hubs (Push - FCM/APNS)               |
          |   - Azure SignalR (In-App Messaging)                        |
          |                                                             |
          |   Data Subnet:                                              |
          |   - Cosmos DB (Campaign State, Journey Data)                |
          |   - Redis Cache (Audience Cache, Sessions)                  |
          |   - Blob Storage (Templates, Creative Assets)               |
          |                                                             |
          |   Analytics Subnet:                                         |
          |   - Event Hub (Campaign Events)                             |
          |   - ADLS Gen2 (Raw Events, Aggregates)                      |
          |   - Synapse Analytics (BI/ML)                                |
          |                                                             |
          |   Integration Subnet:                                       |
          |   - Key Vault, Data Factory, Entra ID                       |
          +-------------------------------------------------------------+
```

---

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Campaign content generation, subject lines, CTAs, A/B variants |
| Azure ML | Managed compute (Standard_DS3_v2) | Audience segmentation, propensity scoring, ROI prediction, send-time optimization |
| Azure Communication Services | Email + SMS (pay-per-message) | Email campaign delivery, SMS notifications |
| Azure Notification Hubs | Standard (10M pushes) | Push notifications to iOS and Android |
| Azure Functions | Premium EP2 (3 instances) | Campaign lifecycle, content generation, orchestration |
| Azure Cosmos DB | Autoscale (10K RU/s) | Campaign state, customer journeys, audience segments |
| Azure Event Hub | Standard (8 partitions, 4 TUs) | Real-time campaign event ingestion |
| Azure ADLS Gen2 | Hot (5TB) | Raw event storage, campaign analytics data lake |
| Azure Synapse Analytics | Serverless SQL pool | Campaign performance aggregation, ad-hoc analysis |
| Azure Data Factory | Managed VNET | ETL pipelines for event processing, model retraining |
| Azure Redis Cache | P1 Premium (6GB) | Audience cache, session state, rate limiting |
| Power BI | Premium Per User | Campaign dashboards, ROI reports |
| Azure Front Door | WAF + CDN + SSL | Global load balancing, DDoS protection |
| Azure API Management | Standard | API gateway, rate limiting, developer portal |
| Azure Key Vault | Standard, RBAC | Secrets, API keys, encryption keys |
| Application Insights | Pay-as-you-go | APM, distributed tracing |
| Log Analytics | Pay-as-you-go (50GB/day) | Centralized logging |

---

## Prerequisites

- **Azure Subscription** with Contributor access
- **Azure CLI** >= 2.50.0
- **Terraform** >= 1.5.0
- **Python** >= 3.11
- **Azure Functions Core Tools** >= 4.x
- **Node.js** >= 18 (for frontend builds)
- Azure OpenAI resource with GPT-4o deployed
- Azure ML workspace with compute provisioned
- Azure Communication Services resource with email and SMS configured

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-24-campaign-management

# Copy environment template and fill in values
cp .env.example .env
```

### 2. Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
export ML_ENDPOINT="https://<your-ml-endpoint>.azureml.ms/score"
export COMMUNICATION_ENDPOINT="https://<your-acs>.communication.azure.com"
export EVENT_HUB_CONNECTION="<event-hub-connection-string>"
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
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html -v
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Entra ID SSO with OAuth2/OIDC and Conditional Access; MFA enforced for all admin actions
- **Authorization**: Fine-grained RBAC with Campaign Manager, Analyst, and Admin role separation
- **Managed Identity**: System-assigned managed identity for all Azure Functions to service connections; zero credential storage
- **Network Isolation**: Private VNET (10.0.0.0/16) with 5-subnet topology (App/Channel/Data/Analytics/Integration); all PaaS services behind Private Link; NSG least-privilege rules
- **Perimeter Protection**: Azure Front Door with WAF (OWASP 3.2), DDoS Protection Standard, geo-filtering
- **PIM**: Privileged Identity Management for just-in-time elevated access

### Encryption

- **Data at Rest**: AES-256 encryption via SSE across Cosmos DB, ADLS Gen2, Blob Storage, and Redis; Customer-Managed Keys (CMK) via Key Vault for sensitive campaign data
- **Data in Transit**: TLS 1.3 enforced on all service endpoints and channel delivery (email, SMS, push)
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection; automatic rotation for API keys and encryption keys

### Monitoring

- **Application Insights**: Full APM with distributed tracing across Azure Functions, OpenAI calls, Azure ML inference, and channel delivery
- **Log Analytics**: Centralized log aggregation at 50GB/day with KQL queries for campaign event analysis and debugging
- **Alerts**: Azure Monitor alert rules for campaign delivery failures, OpenAI quota usage, Event Hub throughput, and function latency (content generation < 5s)
- **Dashboards**: Azure Monitor dashboards for real-time campaign status, channel delivery rates, and cost tracking

### Visualization

- **Power BI**: Campaign performance dashboards embedded in the portal -- ROI reports, channel comparison, audience segment performance, and executive summaries
- **SignalR Real-time**: Live campaign monitoring with real-time metric updates pushed to the Campaign Portal during active sends
- **Cost Management**: Azure Cost Management dashboard for per-campaign and per-channel spend tracking

### Tracking

- **Request Tracing**: End-to-end correlation IDs propagated from APIM through Azure Functions, Event Hub, and channel delivery services
- **Audit Logs**: Campaign lifecycle events (create, schedule, activate, pause, complete) logged with full user attribution in Cosmos DB and Azure Activity Log
- **Event-Driven Tracking**: Event Hub captures all delivery events (send, open, click, conversion, unsubscribe) for real-time and historical analytics
- **Suppression Tracking**: Automated unsubscribe management with real-time suppression list updates in Cosmos DB

### Accuracy

- **A/B Test Statistical Rigor**: Bayesian inference for automated statistical significance detection; confidence threshold set to 0.95 before declaring a winner
- **Propensity Model Validation**: Azure ML models retrained on campaign outcome data via automated Data Factory pipelines; shadow scoring validates new models before promotion
- **ROI Prediction Confidence**: Scenario analysis (optimistic/baseline/pessimistic) with confidence intervals for every ROI forecast
- **Audience Segmentation Refresh**: Full customer base re-scoring in < 30 minutes to ensure segment accuracy

### Explainability

- **A/B Test Analysis**: Every test result includes metric-level p-values, effect sizes, lift percentages, and an actionable recommendation explaining why a variant won or lost
- **Campaign Performance Insights**: GPT-4o generates natural language summaries of campaign performance highlighting strengths, weaknesses, and specific improvement recommendations
- **Budget Allocation Rationale**: Budget optimizer provides a written optimization rationale explaining why each campaign received its allocation, including diminishing returns thresholds
- **Journey Stage Analysis**: Customer journey mapper explains the current stage (awareness/consideration/decision/retention), engagement score, and churn risk with supporting evidence

### Responsibility

- **Content Filtering**: Azure OpenAI responsible AI filters prevent generation of inappropriate, misleading, or off-brand campaign content
- **Consent Management**: GDPR consent verification before any campaign delivery; real-time opt-in/opt-out status tracking
- **CAN-SPAM Compliance**: Automated unsubscribe link injection in all marketing emails; honest subject line enforcement
- **PII Protection**: Email and phone number masking in analytics and logs; PII detection and redaction for audience data in transit and at rest
- **Bias Monitoring**: Audience segmentation models monitored for demographic bias in propensity scoring and channel routing

### Interpretability

- **Channel Routing Transparency**: Propensity scoring outputs per-user engagement likelihood for each channel, enabling marketers to understand why a particular channel was recommended for a segment
- **ROI Driver Decomposition**: ROI predictions identify key drivers and risk factors separately, so marketers can see which inputs most impact projected returns
- **Content Variant Comparison**: Each generated content variant includes personalization tokens and compliance notes, making the generation logic transparent
- **Rebalancing Triggers**: Budget allocator specifies explicit conditions (metric thresholds) that should trigger reallocation, providing clear decision rules

### Portability

- **Infrastructure as Code**: All Azure resources provisioned via Terraform (infra/main.tf) for repeatable, auditable deployments across environments
- **Containerization**: Azure Functions on Python 3.11 with standard dependency management; compatible with container deployment on AKS or ACA
- **Multi-Cloud Considerations**: Core logic uses standard OpenAI Python SDK and Cosmos DB SDK; channel delivery layer can be abstracted behind a provider interface for alternative SMS/email vendors
- **Environment Parity**: Dev/staging/production environments defined with tiered SKUs and feature flags (channels_enabled, audience_limit) in Terraform variables
- **Blue-Green Deployment**: Blue-green deployment strategy with canary (10%) and campaign drain timeout (300s) for zero-downtime releases

---

## Project Structure

```
project-24-campaign-management/
|-- docs/
|   +-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   +-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py          # Azure Functions application (7 core functions)
+-- README.md                    # This file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/create-campaign` | Create a new AI-assisted marketing campaign from a brief |
| POST | `/api/segment-audience` | AI-driven audience segmentation with propensity scoring |
| POST | `/api/generate-content` | Generate channel-specific campaign content (email, SMS, push, in-app) |
| POST | `/api/optimize-ab` | Analyze A/B test results and select a statistically significant winner |
| POST | `/api/predict-roi` | Predictive ROI modeling with scenario analysis |
| POST | `/api/allocate-budget` | Optimize budget allocation across multiple campaigns |
| POST | `/api/performance` | Campaign performance analytics with AI-generated insights |
| GET  | `/api/health` | Health check endpoint |
| Event | `CampaignEventProcessor` | Event Hub trigger for real-time campaign event processing |

### Example: Create Campaign

```bash
curl -X POST https://<function-app>/api/create-campaign \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Launch summer promotion for premium subscription plan targeting existing free-tier users",
    "objectives": ["conversion", "upsell", "retention"]
  }'
```

### Example: Generate Content

```bash
curl -X POST https://<function-app>/api/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_data": {
      "brief": "Summer promotion",
      "audience": "free-tier users",
      "tone": "friendly and urgent"
    },
    "channel": "email"
  }'
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.
