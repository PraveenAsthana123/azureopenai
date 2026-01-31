# Project 25: Digital Marketing & Product Intelligence Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat&logo=openai&logoColor=white)
![DALL-E 3](https://img.shields.io/badge/DALL--E%203-Visual%20Assets-purple?style=flat&logo=openai&logoColor=white)
![Azure ML](https://img.shields.io/badge/Azure%20ML-Attribution+Pricing-orange?style=flat)
![Azure AI Language](https://img.shields.io/badge/Azure%20AI%20Language-Sentiment-teal?style=flat)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

---

## Overview

An AI-powered digital marketing platform that automates product promotion workflows across channels. The system leverages Azure OpenAI GPT-4o for generating product descriptions and SEO content, DALL-E 3 for visual asset creation, Azure ML for marketing attribution modeling and dynamic pricing recommendations, and Azure AI Language for customer review sentiment analysis. The platform delivers end-to-end marketing automation from product launch to ROI analytics, including social media scheduling, landing page A/B optimization, and competitive intelligence gathering.

The platform supports multi-channel content generation (website, email, social media, marketplace), multi-touch attribution modeling (first-touch, last-touch, linear, time-decay, position-based), real-time review sentiment tracking, and AI-powered dynamic pricing with elasticity estimation.

---

## Architecture

```
+---------------------+    +---------------------+    +---------------------+
|  Marketing          |    |  Product Mgmt       |    |  Analytics          |
|  Dashboard (React)  |    |  Portal (React)     |    |  Console (Power BI) |
+---------+-----------+    +---------+-----------+    +---------+-----------+
          |                          |                          |
          +------------- Azure Front Door (WAF + CDN) ---------+
                                     |
                    +----------------+----------------+
                    |                |                |
              APIM Gateway     Azure CDN         Redis Cache
                    |          (Static Assets)   (Session + API Cache)
                    |
          +---------+--------------------------------------------------+
          |         PRIVATE VNET (10.0.0.0/16)                         |
          |                                                             |
          |   Application Subnet:                                       |
          |   - Azure Functions (Content Generator, SEO Optimizer,     |
          |     Campaign Scheduler, Pricing Engine, A/B Test Manager,  |
          |     Influencer Matcher, Attribution Processor)              |
          |   - Azure OpenAI (GPT-4o + DALL-E 3) via Private Link      |
          |   - Azure ML (Attribution, Pricing, Recommendations)        |
          |   - Azure AI Search (Product Index, Competitor Data)        |
          |   - Azure AI Language (Sentiment Analysis)                  |
          |                                                             |
          |   Data Subnet:                                              |
          |   - Cosmos DB (Products, Campaigns, Reviews)                |
          |   - ADLS Gen2 (Raw Marketing Data, Clickstream)             |
          |   - Blob Storage (Media Assets, Generated Visuals)          |
          |   - Synapse Analytics (BI Data)                             |
          |   - Event Hub (Marketing Events)                            |
          |                                                             |
          |   Integration Subnet:                                       |
          |   - Key Vault, Data Factory (ETL + Competitor Scrape)       |
          +-------------------------------------------------------------+
```

---

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Product descriptions, SEO content, social copy, landing pages |
| Azure OpenAI | DALL-E 3 | Marketing visual assets, product imagery generation |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for product and competitive search |
| Azure ML | Custom XGBoost + Shapley | Multi-touch attribution modeling |
| Azure ML | Prophet + LightGBM | Dynamic pricing recommendations |
| Azure AI Language | Sentiment Analysis v3.1 | Customer review sentiment extraction |
| Azure AI Search | S1 (2 replicas) | Product search, competitive intelligence retrieval |
| Azure Functions | Premium EP2 (6 function apps) | Application orchestration and API hosting |
| Azure Cosmos DB | Autoscale (10K RU max) | Products, campaigns, reviews, recommendations |
| Azure ADLS Gen2 | Hot + Cool (5TB) | Raw marketing data, clickstream, competitor data |
| Azure Blob Storage | Hot (2TB), CDN-integrated | Marketing media assets, generated visuals |
| Azure Synapse Analytics | Serverless SQL pool | Marketing analytics, attribution aggregation |
| Azure Event Hub | Standard (8 partitions) | Clickstream, review streams, campaign events |
| Azure Data Factory | Managed VNET, 50 pipelines | ETL, competitor data ingestion, catalog sync |
| Azure Redis Cache | Premium P1 (clustered) | Query cache, content cache, session management |
| Azure CDN | Standard Verizon | Static assets and marketing media delivery |
| Power BI | Pro (10 users) | ROI dashboards, attribution reports, sentiment trends |
| Azure Front Door | WAF + CDN + SSL | Global load balancing, DDoS protection |
| Azure API Management | Standard | API gateway, rate limiting, partner API exposure |
| Azure Key Vault | Standard, RBAC, CMK rotation | Secrets, certificates, encryption keys |
| Application Insights | Pay-as-you-go | APM, distributed tracing |
| Log Analytics | Pay-as-you-go | Centralized logging |

---

## Prerequisites

- **Azure Subscription** with Contributor access
- **Azure CLI** >= 2.50.0
- **Terraform** >= 1.5.0
- **Python** >= 3.11
- **Node.js** >= 20 (for Campaign Scheduler function)
- **Azure Functions Core Tools** >= 4.x
- Azure OpenAI resource with GPT-4o, DALL-E 3, and text-embedding-ada-002 deployed
- Azure ML workspace with attribution and pricing models registered
- Azure AI Language resource provisioned

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-25-digital-marketing

# Copy environment template and fill in values
cp .env.example .env
```

### 2. Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export AZURE_SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
export ML_ENDPOINT="https://<your-ml-endpoint>.azureml.ms/score"
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

- **Authentication**: Entra ID SSO with OAuth2/OIDC for marketing team and partner API access; Conditional Access with MFA enforcement
- **Authorization**: Fine-grained RBAC with Marketing, Product, and Analytics role separation
- **Managed Identity**: System-assigned managed identity for all Azure Functions service-to-service calls; zero credential storage
- **Network Isolation**: Private VNET (10.0.0.0/16) with 3-subnet topology (Application/Data/Integration); all PaaS services behind Private Link; NSG least-privilege rules
- **Perimeter Protection**: Azure Front Door with WAF (OWASP 3.2) and bot protection; DDoS Protection Standard; geo-filtering
- **PIM**: Privileged Identity Management for just-in-time elevated access to production resources

### Encryption

- **Data at Rest**: AES-256 encryption via SSE across Cosmos DB, ADLS Gen2, Blob Storage, and Redis; Customer-Managed Keys (CMK) for sensitive customer review and pricing data via Key Vault
- **Data in Transit**: TLS 1.3 enforced on all service endpoints, CDN delivery, and API gateway traffic
- **Key Management**: Azure Key Vault with RBAC, soft delete, purge protection, and automated CMK rotation

### Monitoring

- **Application Insights**: Full APM with distributed tracing across Azure Functions, OpenAI (GPT-4o + DALL-E 3), Azure ML inference, AI Language, and AI Search
- **Log Analytics**: Centralized log aggregation for all services with KQL queries for debugging and operational analysis
- **Alerts**: Azure Monitor alert rules for content generation latency, DALL-E 3 quota usage, ML model inference failures, and Event Hub throughput
- **Dashboards**: Azure Monitor dashboards for content generation throughput, API health, and cost tracking across OpenAI and DALL-E usage

### Visualization

- **Power BI**: Embedded analytics console with ROI dashboards, multi-touch attribution reports, sentiment trend analysis, and competitive pricing intelligence
- **Marketing Dashboard**: React-based dashboard for campaign scheduling, content calendar management, and A/B test results
- **Cost Management**: Azure Cost Management for per-service spend tracking with budget alerts for OpenAI and DALL-E consumption

### Tracking

- **Request Tracing**: End-to-end correlation IDs propagated from APIM through Azure Functions, Event Hub, and all downstream AI services via Application Insights
- **Audit Logs**: Content generation events (product descriptions, pricing decisions, visual assets) persisted to Cosmos DB with full audit trail including user, timestamp, and model used
- **Event-Driven Tracking**: Event Hub captures all marketing events (product views, cart abandons, purchases, review submissions, campaign interactions) for real-time and historical attribution analysis
- **Pricing Decision Trail**: Every dynamic pricing recommendation stored in Cosmos DB pricing-decisions container for regulatory and business audit

### Accuracy

- **Attribution Model Validation**: Multiple attribution models (first-touch, last-touch, linear, time-decay, position-based) computed simultaneously; AI recommends the best-fit model per dataset with supporting rationale
- **Pricing Confidence Scoring**: Each pricing recommendation includes a 0-1 confidence score, price elasticity estimate, and projected revenue/volume/margin impact
- **SEO Scoring**: SEO optimization returns a 0-100 score with keyword density analysis, readability grade, and specific improvement recommendations
- **Sentiment Validation**: Review sentiment analysis provides both an overall score (-1.0 to 1.0) and per-theme breakdown with example quotes for human validation
- **ML Shadow Scoring**: New ML models run in shadow mode (scoring alongside production models) before promotion to ensure accuracy parity

### Explainability

- **Attribution Transparency**: Each attribution result shows channel weights across all five models, with a narrative journey summary explaining the conversion path in natural language
- **Pricing Rationale**: Dynamic pricing outputs include a written strategy rationale, competitor position analysis, and explicit trigger conditions for re-evaluation
- **SEO Recommendations**: SEO optimizer provides actionable, prioritized improvement suggestions with estimated impact, not just a score
- **Sentiment Theme Decomposition**: Review sentiment analysis extracts distinct themes (quality, price, shipping, support) each with their own sentiment score and example quotes
- **Content Generation Tokens**: All generated content includes token usage metadata for cost transparency and model performance tracking

### Responsibility

- **Content Filtering**: Azure OpenAI responsible AI filters enabled for all text generation and DALL-E 3 image generation to prevent harmful or off-brand content
- **Digital Watermarking**: AI-generated visual assets via DALL-E 3 include digital watermarking to identify AI-created imagery
- **PII Masking**: Customer review PII redacted before sentiment analysis storage; data masking applied in analytics and logs
- **SEO Ethics**: Platform enforces white-hat SEO practices only; no keyword stuffing, cloaking, or deceptive techniques
- **Brand Compliance**: Brand voice guidelines enforced via system prompts in all content generation; content review workflows for brand consistency
- **GDPR/CCPA Compliance**: Customer review data privacy and consent management; Purview data classification and retention policies

### Interpretability

- **Feature Importance in Attribution**: Shapley value calculations provide per-channel contribution scores, enabling marketers to see the exact contribution of each touchpoint to the conversion
- **Pricing Strategy Labels**: Each pricing recommendation is labeled with the strategy name (penetration, skimming, competitive, value-based) and a time horizon for how long the price should remain active
- **Content Generation Parameters**: All API calls expose the tone, channel, and product attributes used to generate content, enabling reproduction and A/B comparison of outputs
- **Sentiment Distribution**: Review analysis breaks down into positive/neutral/negative counts with trending topics, enabling comparison against baseline patterns

### Portability

- **Infrastructure as Code**: All Azure resources provisioned via Terraform (infra/main.tf) with environment-specific variable files for dev/staging/production
- **Containerization**: Azure Functions on Python 3.11 and Node.js 20 with standard dependency management; compatible with Docker container deployment on AKS
- **Multi-Cloud Considerations**: Core logic uses standard OpenAI Python SDK; Cosmos DB, ADLS, and AI Search layers abstracted behind service clients for potential migration
- **ML Model Portability**: Attribution and pricing models use standard frameworks (XGBoost, Prophet, LightGBM) with MLflow tracking for cross-platform model registry compatibility
- **Blue-Green Deployment**: Blue-green deployment strategy with canary (10%) and ML shadow scoring for zero-downtime releases

---

## Project Structure

```
project-25-digital-marketing/
|-- docs/
|   +-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   +-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   +-- function_app.py          # Azure Functions application (8 core functions)
+-- README.md                    # This file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/product-description` | Generate AI-powered product descriptions per channel and tone |
| POST | `/api/seo-optimize` | Optimize content for search engines with keyword targeting |
| POST | `/api/social-calendar` | Generate a social media content calendar for products |
| POST | `/api/review-sentiment` | Analyze customer review sentiment with theme extraction |
| POST | `/api/dynamic-pricing` | Get AI-powered dynamic pricing recommendations |
| POST | `/api/landing-page` | Generate landing page content for a product campaign |
| POST | `/api/attribution` | Calculate multi-touch marketing attribution |
| POST | `/api/product-visuals` | Generate product imagery using DALL-E 3 |
| GET  | `/api/health` | Health check endpoint (includes model versions) |
| Event | `MarketingEventProcessor` | Event Hub trigger for real-time marketing event processing |

### Example: Generate Product Description

```bash
curl -X POST https://<function-app>/api/product-description \
  -H "Content-Type: application/json" \
  -d '{
    "product_data": {
      "name": "ProMax Wireless Headphones",
      "category": "Electronics",
      "features": ["Active Noise Cancellation", "40hr Battery", "Bluetooth 5.3"],
      "target_audience": "Professionals and audiophiles",
      "price_point": "$299"
    },
    "tone": "professional",
    "channel": "website"
  }'
```

### Example: Generate Product Visuals

```bash
curl -X POST https://<function-app>/api/product-visuals \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "Premium wireless over-ear headphones in matte black with rose gold accents",
    "style": "photorealistic"
  }'
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.
