# Project 24: AI Campaign Management Platform

## Executive Summary

An enterprise-grade AI-powered campaign management platform that enables marketing teams to create, orchestrate, and optimize multi-channel campaigns (email, SMS, push notifications, in-app messages) using GenAI-driven content generation, intelligent audience segmentation, A/B testing optimization, predictive ROI modeling, and real-time performance analytics. The system leverages Azure OpenAI GPT-4o for campaign content generation, Azure ML for audience propensity scoring and segmentation, Azure Communication Services for email/SMS delivery, and Azure Notification Hubs for push notifications across mobile platforms.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       AI CAMPAIGN MANAGEMENT PLATFORM                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Campaign Portal│     │  Analytics      │     │  Mobile App     │
│  (React/Next.js)│     │  Dashboard      │     │  (React Native) │
│                 │     │  (Power BI)     │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (Campaign UI)  │   │  (Real-time     │
│   Auth, Cache)  │   │                 │   │   Monitoring)   │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌──────────────────────────────────────────────────────────────┐
         │  │                  PRIVATE VNET (10.0.0.0/16)                  │
         │  │                                                              │
         │  │  ┌────────────────────────────────────────────────────────┐  │
         │  │  │            Application Subnet (10.0.1.0/24)           │  │
         ▼  │  │                                                        │  │
┌───────────┴──┴──────┐                                                 │  │
│  Azure Functions    │◄──────────────────────────────────────────┐     │  │
│  (Campaign Engine)  │                                           │     │  │
│                     │    ┌──────────────────┐                   │     │  │
│ - Campaign Creator  │    │  Azure OpenAI    │                   │     │  │
│ - Content Generator │◄───┤  (GPT-4o)        │                   │     │  │
│ - A/B Test Engine   │    │  Private Link    │                   │     │  │
│ - Journey Mapper    │    └──────────────────┘                   │     │  │
│ - Budget Optimizer  │                                           │     │  │
└──────────┬──────────┘    ┌──────────────────┐                   │     │  │
           │               │  Azure ML        │                   │     │  │
           ├──────────────►│  (Segmentation,  │                   │     │  │
           │               │   Propensity,    │                   │     │  │
           │               │   ROI Predict)   │                   │     │  │
           │               └──────────────────┘                   │     │  │
           │               └────────────────────────────────────────┘   │  │
           │                                                            │  │
           │  ┌──────────────────────────────────────────────────────┐  │  │
           │  │         Channel Orchestration Subnet (10.0.2.0/24)  │  │  │
           │  │                                                      │  │  │
           │  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │  │
           │  │  │ Azure Comm.  │  │ Notification │  │ In-App     │ │  │  │
           ├──┤  │ Services     │  │ Hubs         │  │ Messaging  │ │  │  │
           │  │  │ (Email/SMS)  │  │ (Push)       │  │ (SignalR)  │ │  │  │
           │  │  └──────────────┘  └──────────────┘  └────────────┘ │  │  │
           │  └──────────────────────────────────────────────────────┘  │  │
           │                                                            │  │
           │  ┌──────────────────────────────────────────────────────┐  │  │
           │  │            Data Subnet (10.0.3.0/24)                │  │  │
           │  │                                                      │  │  │
           │  │  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │  │  │
           │  │  │Cosmos DB │  │ Redis Cache  │  │ Blob Storage  │  │  │  │
           ├──┤  │(Campaign │  │ (Audience    │  │ (Templates,   │  │  │  │
           │  │  │ State,   │  │  Cache,      │  │  Assets,      │  │  │  │
           │  │  │ Journey) │  │  Sessions)   │  │  Media)       │  │  │  │
           │  │  └──────────┘  └──────────────┘  └───────────────┘  │  │  │
           │  └──────────────────────────────────────────────────────┘  │  │
           │                                                            │  │
           │  ┌──────────────────────────────────────────────────────┐  │  │
           │  │        Analytics Subnet (10.0.4.0/24)               │  │  │
           │  │                                                      │  │  │
           │  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │  │
           │  │  │ Event Hub    │  │ ADLS Gen2    │  │ Synapse    │ │  │  │
           ├──┤  │ (Campaign   │  │ (Raw Events, │  │ Analytics  │ │  │  │
           │  │  │  Events)    │  │  Aggregates) │  │ (BI/ML)    │ │  │  │
           │  │  └──────────────┘  └──────────────┘  └────────────┘ │  │  │
           │  └──────────────────────────────────────────────────────┘  │  │
           │                                                            │  │
           │  ┌──────────────────────────────────────────────────────┐  │  │
           │  │       Integration Subnet (10.0.5.0/24)              │  │  │
           │  │                                                      │  │  │
           │  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │  │
           │  │  │ Key Vault    │  │ Data Factory │  │ Entra ID   │ │  │  │
           └──┤  │ (Secrets)    │  │ (ETL/        │  │ (Auth)     │ │  │  │
              │  │              │  │  Pipelines)  │  │            │ │  │  │
              │  └──────────────┘  └──────────────┘  └────────────┘ │  │  │
              └──────────────────────────────────────────────────────┘  │  │
              └────────────────────────────────────────────────────────┘  │
              └──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                               │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ App Insights│  │Log Analytics │  │ Azure Monitor│  │ Power BI     │  │
│  │ (APM)       │  │ (Logs)       │  │ (Metrics/    │  │ (Campaign    │  │
│  │             │  │              │  │  Alerts)     │  │  Dashboards) │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAMPAIGN CREATION FLOW                                 │
└─────────────────────────────────────────────────────────────────────────┘

    Marketing User                                      Campaign Ready
        │                                                    ▲
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 1. Campaign   │                                   │ 8. Schedule   │
│ Brief Input   │                                   │ & Activate    │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 2. GenAI      │                                   │ 7. A/B Test   │
│ Content Gen   │                                   │ Variant Gen   │
│ (GPT-4o)      │                                   │ (GPT-4o)      │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐                                   ┌───────────────┐
│ 3. Audience   │──────────────────────────────────►│ 6. Budget     │
│ Segmentation  │                                   │ Allocation    │
│ (Azure ML)    │                                   │ Optimizer     │
└───────┬───────┘                                   └───────┬───────┘
        │                                                    │
        ▼                                                    │
┌───────────────┐      ┌───────────────┐           ┌───────────────┐
│ 4. Propensity │─────►│ 5. Channel    │──────────►│ Predicted     │
│ Scoring       │      │ Selection     │           │ ROI Model     │
│ (Azure ML)    │      │ (ML Routing)  │           │ (Azure ML)    │
└───────────────┘      └───────────────┘           └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                 MULTI-CHANNEL EXECUTION FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

Campaign Trigger
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Campaign   │────►│ 2. Audience   │────►│ 3. Channel    │
│ Scheduler     │     │ Resolver      │     │ Router        │
│ (Functions)   │     │ (Cosmos DB)   │     │ (Orchestrator)│
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                         ┌───────────────────────────┼──────────────────────────┐
                         │                           │                          │
                         ▼                           ▼                          ▼
                   ┌───────────┐            ┌───────────────┐          ┌───────────────┐
                   │ 4a. Email │            │ 4b. SMS       │          │ 4c. Push      │
                   │ (Azure    │            │ (Azure Comm.  │          │ (Notification │
                   │  Comm Svc)│            │  Services)    │          │  Hubs)        │
                   └─────┬─────┘            └───────┬───────┘          └───────┬───────┘
                         │                          │                          │
                         │                          ▼                          │
                         │                   ┌───────────────┐                 │
                         │                   │ 4d. In-App    │                 │
                         │                   │ (SignalR)     │                 │
                         │                   └───────┬───────┘                 │
                         │                           │                         │
                         └───────────────────────────┼─────────────────────────┘
                                                     │
                                                     ▼
                                              ┌───────────┐
                                              │ 5. Event  │
                                              │ Hub       │
                                              │ (Delivery │
                                              │  Events)  │
                                              └─────┬─────┘
                                                    │
                                                    ▼
                                              ┌───────────┐
                                              │ 6. ADLS   │
                                              │ Gen2 (Raw │
                                              │ Events)   │
                                              └───────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                   PERFORMANCE ANALYTICS FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

Channel Delivery Events
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Event Hub  │────►│ 2. Stream     │────►│ 3. ADLS Gen2  │
│ (Ingest)      │     │ Analytics     │     │ (Data Lake)   │
└───────────────┘     │ (Real-time)   │     └───────┬───────┘
                      └───────────────┘             │
                                                    ▼
                                             ┌───────────────┐
                      ┌──────────────────────│ 4. Data       │
                      │                      │ Factory       │
                      │                      │ (ETL)         │
                      │                      └───────┬───────┘
                      │                              │
                      ▼                              ▼
               ┌───────────────┐            ┌───────────────┐
               │ 5a. Synapse   │            │ 5b. Azure ML  │
               │ Analytics     │            │ (Retrain      │
               │ (Aggregation) │            │  Models)      │
               └───────┬───────┘            └───────────────┘
                       │
                       ▼
               ┌───────────────┐
               │ 6. Power BI   │
               │ (Campaign     │
               │  Dashboards)  │
               └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Campaign Portal | React + Next.js + TypeScript | Campaign creation, management, and monitoring UI |
| Analytics Dashboard | Power BI Embedded | Campaign performance visualization and ROI reporting |
| Mobile App | React Native | On-the-go campaign monitoring and approval workflows |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL, CDN | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits, Caching | API management, authentication, developer portal |
| SignalR | Serverless mode | Real-time campaign monitoring and live metric updates |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Campaign Engine | Azure Functions (Python 3.11) | Campaign lifecycle management, scheduling, orchestration |
| Content Generator | Azure Functions (Python 3.11) | GenAI-powered content creation for all channels |
| A/B Test Engine | Azure Functions (Python 3.11) | Variant generation, traffic splitting, statistical analysis |
| Journey Mapper | Azure Functions (Python 3.11) | Customer journey orchestration and state management |
| Budget Optimizer | Azure Functions (Python 3.11) | Budget allocation across channels and campaigns |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Campaign content generation, subject lines, CTAs |
| Azure ML | Custom segmentation model | Audience clustering and micro-segmentation |
| Azure ML | Propensity scoring model | Predict user engagement likelihood per channel |
| Azure ML | ROI prediction model | Forecast campaign return on investment |
| Azure ML | Send-time optimization model | Optimal delivery time per recipient |

### 5. Channel Delivery Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Communication Services | Email + SMS | Email campaign delivery, SMS notifications |
| Azure Notification Hubs | FCM + APNS | Push notifications to iOS and Android devices |
| Azure SignalR Service | Serverless mode | In-app messaging and real-time notifications |

### 6. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Multi-region, serverless | Campaign state, customer journeys, audience segments |
| Redis Cache | P1 Premium, 6GB | Audience cache, session state, rate limiting |
| Blob Storage | Hot tier, versioning | Campaign templates, creative assets, media files |
| ADLS Gen2 | Hierarchical namespace | Raw event storage, campaign analytics data lake |
| Event Hub | Standard, 8 partitions | Real-time campaign event ingestion (delivery, opens, clicks) |

### 7. Analytics Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Synapse Analytics | Serverless SQL pool | Campaign performance aggregation and ad-hoc analysis |
| Data Factory | Managed VNET | ETL pipelines for event processing and model retraining |
| Power BI | Premium Per User | Campaign dashboards, ROI reports, executive summaries |

### 8. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protection | Secrets, API keys, encryption keys |
| Private Link | All PaaS services | Network isolation for all Azure resources |
| Managed Identity | System-assigned | Service-to-service authentication without credentials |
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication and RBAC authorization |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (Allowed Regions│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time access)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ PII         │  │ Data Masking    │  │
│ │ at Rest/    │  │ (CMK)       │  │ Detection   │  │ (Email, Phone,  │  │
│ │ Transit     │  │             │  │ & Redaction │  │  PII Fields)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain)│  │ Throttling  │  │ Filtering       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ GDPR/CAN-SPAM   │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (Activity)  │  │ Compliance      │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-campaign-mgmt-dev
    location: eastus
    sku_tier: basic
    channels_enabled: [email]
    audience_limit: 10000

  staging:
    subscription: staging-subscription
    resource_group: rg-campaign-mgmt-stg
    location: eastus
    sku_tier: standard
    channels_enabled: [email, sms, push]
    audience_limit: 100000

  production:
    subscription: prod-subscription
    resource_group: rg-campaign-mgmt-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    channels_enabled: [email, sms, push, in-app]
    audience_limit: 10000000

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  campaign_drain_timeout: 300s  # Allow in-flight campaigns to complete

scaling:
  azure_functions:
    min_instances: 3
    max_instances: 50
    target_cpu: 70
  event_hub:
    partitions: 8
    throughput_units: 4
    auto_inflate: true
  cosmos_db:
    max_ru: 10000
    auto_scale: true
  redis_cache:
    shards: 2
    max_memory_policy: allkeys-lru
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$3,000-8,000 |
| Azure ML | Managed compute (Standard_DS3_v2) | ~$800 |
| Azure Communication Services | Email + SMS (pay-per-message) | ~$2,000-5,000 |
| Azure Notification Hubs | Standard (10M pushes) | ~$200 |
| Azure Functions | Premium EP2 (3 instances) | ~$600 |
| Cosmos DB | Autoscale (10K RU/s) | ~$600 |
| Event Hub | Standard (8 partitions, 4 TUs) | ~$300 |
| ADLS Gen2 | Hot (5TB) | ~$100 |
| Synapse Analytics | Serverless SQL pool | ~$400 |
| Data Factory | Managed VNET, 100 pipeline runs/day | ~$300 |
| Redis Cache | P1 Premium (6GB) | ~$250 |
| Blob Storage | Hot (500GB) | ~$10 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Power BI | Premium Per User (10 users) | ~$200 |
| Application Insights | Pay-as-you-go | ~$150 |
| Log Analytics | Pay-as-you-go (50GB/day) | ~$250 |
| Azure Monitor | Alerts + Metrics | ~$50 |
| **Total Estimated** | | **~$9,500-17,000** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why GenAI for Campaign Content?**
   - GPT-4o generates subject lines, email bodies, SMS text, and push copy in seconds
   - Produces multiple A/B test variants automatically from a single campaign brief
   - Tone and brand voice consistency enforced through system prompts and guardrails
   - Reduces content creation time from days to minutes for marketing teams

2. **Why Azure ML for Audience Segmentation?**
   - Custom clustering models identify micro-segments beyond basic demographics
   - Propensity scoring predicts per-user engagement likelihood for each channel
   - Send-time optimization determines best delivery window per recipient
   - Models retrain on campaign outcome data via automated Data Factory pipelines

3. **Why Multi-Channel Orchestration with Azure Functions?**
   - Event-driven architecture scales independently per channel
   - Durable Functions manage campaign state machines and customer journey flows
   - Channel-specific retry policies handle transient delivery failures
   - Fan-out pattern enables parallel delivery across email, SMS, push, and in-app

4. **Why Event Hub + ADLS Gen2 for Analytics?**
   - Event Hub ingests millions of delivery, open, click, and conversion events in real-time
   - ADLS Gen2 provides cost-effective long-term storage for campaign event data
   - Synapse Serverless SQL enables ad-hoc analysis without provisioned compute
   - Data Factory orchestrates ETL from raw events to aggregated performance metrics

5. **Why Cosmos DB for Campaign State?**
   - Multi-region replication ensures campaign state availability during failovers
   - Low-latency reads for real-time campaign status and journey progression
   - Flexible schema accommodates different campaign types and channel configurations
   - Change feed triggers downstream processing for real-time monitoring updates

6. **Security and Compliance Considerations**
   - All services behind Private Link with no public endpoints
   - Managed Identity eliminates credential management across all services
   - PII detection and redaction for audience data in transit and at rest
   - GDPR consent management and CAN-SPAM compliance built into delivery layer
   - Content filtering in Azure OpenAI prevents generation of inappropriate campaign content

### Scalability Considerations

- Azure Functions Premium plan scales to 50 instances for high-volume campaign launches
- Event Hub auto-inflate handles burst traffic during simultaneous campaign sends
- Cosmos DB autoscale adjusts RU/s based on campaign activity patterns
- Redis Cache reduces database load for frequently accessed audience segments
- Notification Hubs handles millions of push notifications with platform-native batching
- Synapse Serverless pool eliminates idle compute costs for periodic analytics queries

### Key Metrics and SLAs

- Campaign content generation: < 5 seconds for full multi-channel content set
- Email delivery throughput: 1M+ emails per hour via Azure Communication Services
- Push notification delivery: 10M+ notifications per campaign via Notification Hubs
- Real-time dashboard refresh: < 10 seconds for campaign performance metrics
- A/B test statistical significance: automated detection with Bayesian inference
- Audience segmentation refresh: < 30 minutes for full customer base re-scoring
- End-to-end campaign launch: < 2 minutes from activation to first delivery

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2C / B2B (Marketing Team + Analytics)
- **Visibility:** Marketing Team + Analytics — campaign managers, marketing analysts, and target audiences
- **Project Score:** 8.5 / 10 (High)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Private Link | All PaaS services via private endpoints |
| Network | VNET Isolation | 5-subnet topology (App/Channel/Data/Analytics/Integration) |
| Identity | Entra ID SSO | OAuth2/OIDC with conditional access and MFA |
| Identity | RBAC | Campaign Manager, Analyst, Admin role separation |
| Data | CAN-SPAM Compliance | Automated unsubscribe link injection in all marketing emails |
| Data | GDPR Consent | Opt-in consent verification before campaign delivery |
| Data | List Hygiene | Automated bounce removal, suppression list management |
| Data | PII Protection | Email and phone number masking in analytics and logs |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Application | Content Filtering | Azure OpenAI responsible AI for campaign content generation |
| Application | Rate Limiting | Per-channel delivery throttling to prevent spam classification |
| Monitoring | Audit Logs | Campaign lifecycle events and delivery audit trail |
| Monitoring | Sentinel SIEM | Anomaly detection for unusual campaign patterns |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| CAN-SPAM | Enforced | Unsubscribe mechanism, physical address, honest subject lines |
| CASL | Enforced | Canadian Anti-Spam Legislation consent requirements |
| GDPR | Enforced | Consent management, right to erasure, data portability |
| Opt-out Governance | Automated | Real-time suppression list updates across all channels |
| Brand Compliance | Reviewed | Content review workflows for brand voice consistency |
| Audience Privacy | Enforced | PII redaction in analytics, anonymized reporting |
| Data Retention | Policy | Campaign data 2-year retention, PII purge on opt-out |

### Regulatory Applicability
- **CAN-SPAM Act:** Commercial email compliance (unsubscribe, identification, opt-out)
- **CASL:** Canadian Anti-Spam Legislation express/implied consent
- **GDPR:** Consent-based marketing, right to erasure, data portability
- **CCPA:** California consumer opt-out rights for marketing communications
- **TCPA:** SMS marketing consent and opt-out compliance
- **FTC Guidelines:** Truth-in-advertising, endorsement disclosures
- **ePrivacy Directive:** Cookie consent and electronic communications privacy
