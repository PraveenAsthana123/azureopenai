# Project 8: Supply Chain Optimizer

## Executive Summary

An enterprise-grade supply chain optimization platform that combines demand forecasting, inventory optimization, and supplier risk scoring powered by Azure AI services. The system leverages Azure OpenAI GPT-4o for GenAI-powered insights and natural language explanations, Azure Machine Learning AutoML for time-series demand forecasting, and a real-time streaming pipeline built on Event Hub and Stream Analytics for live supply chain signal processing. The platform ingests data from ERP systems, supplier portals, logistics feeds, and market signals to deliver actionable recommendations that reduce stockouts, minimize carrying costs, and proactively identify supplier risk.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          SUPPLY CHAIN OPTIMIZER PLATFORM                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Web Dashboard  │     │  Power BI       │     │  Mobile App     │
│  (React/Next)   │     │  (Embedded)     │     │  (React Native) │
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
│   APIM Gateway  │   │  Static Web App │   │  Power BI       │
│  (Rate Limit,   │   │  (Frontend)     │   │  Service        │
│   Auth, Cache)  │   │                 │   │  (Reports)      │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌─────────────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)                  │
         │  │  ┌─────────────────────────────────────────────────┐    │
         │  │  │         Application Subnet (10.0.1.0/24)        │    │
         ▼  │  │                                                 │    │
┌───────────┴──┴───┐                                             │    │
│ Azure Functions  │◄──────────────────────────────────────────┐ │    │
│ (API Layer)      │                                            │ │    │
│                  │    ┌─────────────────┐                      │ │    │
│ - Demand Forecast│    │  Azure OpenAI   │                      │ │    │
│ - Inventory Opt  │◄───┤  (GPT-4o)       │                      │ │    │
│ - Supplier Risk  │    │  Private Link   │                      │ │    │
│ - GenAI Insights │    └─────────────────┘                      │ │    │
└────────┬─────────┘                                             │ │    │
         │              ┌─────────────────┐                      │ │    │
         ├─────────────►│  Azure ML       │◄─────────────────────┘ │    │
         │              │  (AutoML)       │                        │    │
         │              │  - Time-Series  │                        │    │
         │              │  - Forecasting  │                        │    │
         │              └────────┬────────┘                        │    │
         │                       │                                 │    │
         │  ┌────────────────────┼──────────────────────────────┐  │    │
         │  │         Data Subnet (10.0.2.0/24)                 │  │    │
         │  │                    │                               │  │    │
         │  │    ┌───────────────┼───────────────────────┐      │  │    │
         │  │    │               │               │       │      │  │    │
         │  │    ▼               ▼               ▼       ▼      │  │    │
         │  │ ┌──────┐    ┌──────────┐    ┌───────┐ ┌────────┐  │  │    │
         │  │ │ADLS  │    │Cosmos DB │    │ Redis │ │Synapse │  │  │    │
         │  │ │Gen2  │    │(Orders,  │    │ Cache │ │Analyti │  │  │    │
         │  │ │(Lake)│    │Suppliers)│    │       │ │cs      │  │  │    │
         │  │ └──────┘    └──────────┘    └───────┘ └────────┘  │  │    │
         │  └───────────────────────────────────────────────────┘  │    │
         │                                                         │    │
         │  ┌─────────────────────────────────────────────────┐    │    │
         │  │     Integration Subnet (10.0.3.0/24)            │    │    │
         │  │                                                 │    │    │
         │  │  ┌─────────────┐  ┌──────────┐  ┌───────────┐  │    │    │
         │  │  │  Key Vault  │  │Event Hub │  │  Stream   │  │    │    │
         │  │  │  (Secrets)  │  │(Ingest)  │  │ Analytics │  │    │    │
         │  │  └─────────────┘  └──────────┘  └───────────┘  │    │    │
         │  │                                                 │    │    │
         │  │  ┌─────────────┐  ┌──────────────────────────┐  │    │    │
         │  │  │Data Factory │  │ Blob Storage             │  │    │    │
         │  │  │(ETL Pipes)  │  │ (Raw Files / Exports)    │  │    │    │
         │  │  └─────────────┘  └──────────────────────────┘  │    │    │
         │  └─────────────────────────────────────────────────┘    │    │
         └─────────────────────────────────────────────────────────┘    │
                                                                        │
┌───────────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────────┐
│   │              DATA INGESTION PIPELINE                             │
│   │                                                                 │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐   ┌───────────┐  │
│   │  │ ERP      │    │ Supplier │    │ Logistics│   │ Market    │  │
│   │  │ Systems  │    │ Portals  │    │ Feeds    │   │ Signals   │  │
│   │  └─────┬────┘    └────┬─────┘    └────┬─────┘   └─────┬─────┘  │
│   │        │              │               │               │        │
│   │        └──────────────┼───────────────┼───────────────┘        │
│   │                       ▼               ▼                        │
│   │              ┌─────────────────┐  ┌─────────────────┐          │
│   │              │  Data Factory   │  │  Event Hub      │          │
│   │              │  (Batch ETL)    │  │  (Real-time)    │          │
│   │              └────────┬────────┘  └────────┬────────┘          │
│   │                       │                    │                   │
│   │                       ▼                    ▼                   │
│   │              ┌─────────────────┐  ┌─────────────────┐          │
│   │              │  ADLS Gen2     │  │ Stream Analytics │          │
│   │              │  (Bronze/Silver)│  │ (Windowed Agg)  │          │
│   │              └────────┬────────┘  └────────┬────────┘          │
│   │                       │                    │                   │
│   │                       └────────┬───────────┘                   │
│   │                                ▼                               │
│   │                       ┌─────────────────┐                      │
│   │                       │ Synapse Analytics│                     │
│   │                       │ (Gold Layer)     │                     │
│   │                       └─────────────────┘                      │
│   └─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                               │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor               │  │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │ ML Model    │  │ Cost Mgmt  │  │ Defender for Cloud           │  │
│  │ Monitoring  │  │ Dashboard   │  │ (Security)                  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DEMAND FORECAST FLOW                                 │
└─────────────────────────────────────────────────────────────────────────┘

    ERP / POS Data                                    Forecast Output
        │                                                   ▲
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 1. Data       │                                  │ 8. GenAI      │
│ Factory ETL   │                                  │ Insight Gen   │
│ (Batch)       │                                  │ (GPT-4o)      │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 2. ADLS Gen2  │                                  │ 7. Forecast   │
│ Bronze Layer  │                                  │ API Response  │
│ (Raw Ingest)  │                                  │ + Explanation │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐                                  ┌───────────────┐
│ 3. Synapse    │──────────────────────────────────│ 6. Azure ML   │
│ Transform     │                                  │ AutoML Predict│
│ (Silver/Gold) │                                  │ (Time-Series) │
└───────┬───────┘                                  └───────┬───────┘
        │                                                   │
        ▼                                                   │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. Feature    │─────►│ 5. ML Model   │─────────►│ Scored        │
│ Engineering   │      │ Training      │          │ Forecast      │
│ (Lag, Season) │      │ (AutoML)      │          │               │
└───────────────┘      └───────────────┘          └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    SUPPLIER RISK SCORING FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

Supplier Signals (Real-time)
      │
      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Event Hub  │────►│ 2. Stream     │────►│ 3. Risk       │
│ (Ingest)      │     │ Analytics     │     │ Aggregation   │
│               │     │ (Windowed)    │     │ (Cosmos DB)   │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                            ┌────────────────────────┼────────────────────┐
                            │                        │                    │
                            ▼                        ▼                    ▼
                      ┌───────────┐          ┌───────────┐        ┌───────────┐
                      │ 4a. Lead  │          │ 4b. Qual  │        │ 4c. Fin   │
                      │ Time Score│          │ Score     │        │ Health    │
                      └─────┬─────┘          └─────┬─────┘        └─────┬─────┘
                            │                      │                    │
                            └──────────────────────┼────────────────────┘
                                                   │
                                                   ▼
                                            ┌───────────┐
                                            │ 5. GPT-4o │
                                            │ Risk      │
                                            │ Narrative │
                                            └─────┬─────┘
                                                  │
                                                  ▼
                                            ┌───────────┐
                                            │ 6. Push to│
                                            │ Dashboard │
                                            │ + Alerts  │
                                            └───────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Dashboard | React + TypeScript + Next.js | Supply chain command center UI |
| Power BI Embedded | Power BI Service | Interactive forecast and KPI reports |
| Mobile App | React Native | On-the-go alerts and approvals |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL, CDN | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits, Caching | API management, authentication, throttling |
| Power BI Service | Row-level security | Embedded analytics delivery |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Forecast API | Azure Functions (Python 3.11) | Demand forecast inference endpoint |
| Inventory Optimizer | Azure Functions (Python 3.11) | Safety stock and reorder point calculation |
| Supplier Risk API | Azure Functions (Python 3.11) | Risk score retrieval and supplier ranking |
| GenAI Insights API | Azure Functions (Python 3.11) | Natural language supply chain explanations |
| ETL Orchestrator | Data Factory Pipelines | Batch data ingestion and transformation |
| Stream Processor | Stream Analytics Jobs | Real-time supplier signal processing |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | GenAI narrative generation, insight summarization |
| Azure ML AutoML | TCNForecaster / Prophet | Time-series demand forecasting |
| Azure ML Pipeline | Managed endpoints | Model training, retraining, and serving |
| Stream Analytics | Windowed aggregations | Real-time anomaly detection on supplier signals |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| ADLS Gen2 | Hierarchical namespace, Bronze/Silver/Gold | Data lake for raw and curated datasets |
| Cosmos DB | Serverless, SQL API | Supplier profiles, risk scores, order history |
| Synapse Analytics | Dedicated SQL Pool (DW200c) | Aggregated analytics, feature store |
| Redis Cache | P1 Premium | Forecast cache, session state, hot supplier data |
| Blob Storage | Hot tier, versioning | Raw file exports, model artifacts |
| Event Hub | Standard, 8 partitions | Real-time supplier and logistics event ingestion |
| Data Factory | Managed VNET IR | Batch ETL from ERP, supplier portals |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protection | Secrets, connection strings, API keys |
| Private Link | All PaaS services | Network isolation, no public endpoints |
| Managed Identity | System-assigned | Zero-credential service-to-service auth |
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication and authorization |

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
│ │ Encryption  │  │ Key Vault   │  │ Data        │  │ Purview         │  │
│ │ at Rest/    │  │ (CMK)       │  │ Masking     │  │ (Classification)│  │
│ │ Transit     │  │             │  │ (PII/PCI)   │  │                 │  │
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
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (Activity)  │  │ Manager         │  │
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
    resource_group: rg-supply-chain-dev
    location: eastus
    sku_tier: basic
    ml_compute: Standard_DS3_v2 (single node)
    synapse_pool: DW100c

  staging:
    subscription: staging-subscription
    resource_group: rg-supply-chain-stg
    location: eastus
    sku_tier: standard
    ml_compute: Standard_DS4_v2 (2 nodes)
    synapse_pool: DW200c

  production:
    subscription: prod-subscription
    resource_group: rg-supply-chain-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    ml_compute: Standard_DS5_v2 (4 nodes)
    synapse_pool: DW500c

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  ml_model_deployment: managed_online_endpoint
  model_retraining_schedule: weekly
  data_pipeline_schedule: daily (batch), continuous (streaming)
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$1,500-3,000 |
| Azure ML (AutoML + Endpoints) | Managed compute (DS5_v2) | ~$1,200 |
| Azure Functions | Premium EP2 | ~$300 |
| Cosmos DB | Serverless (400K RU) | ~$150 |
| ADLS Gen2 | Hot + Cool (5TB) | ~$120 |
| Synapse Analytics | DW500c | ~$1,800 |
| Event Hub | Standard (8 TU) | ~$200 |
| Stream Analytics | 6 SU | ~$450 |
| Data Factory | Managed VNET IR | ~$350 |
| Redis Cache | P1 Premium | ~$250 |
| Blob Storage | Hot (1TB) | ~$20 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Power BI Embedded | A2 | ~$750 |
| Application Insights | Pay-as-you-go | ~$100 |
| Log Analytics | Pay-as-you-go (50GB/day) | ~$120 |
| Azure Monitor | Alerts + Metrics | ~$50 |
| Private Link | 15 endpoints | ~$100 |
| **Total Estimated** | | **~$7,600-9,100** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why AutoML for Demand Forecasting over Custom Models?**
   - AutoML evaluates multiple algorithms (TCN, Prophet, ARIMA, ExponentialSmoothing) automatically
   - Built-in feature engineering for time-series (lags, rolling windows, holidays)
   - Reduces model development time from weeks to hours while maintaining accuracy
   - Managed retraining pipelines ensure models stay current with minimal operational burden

2. **Why Event Hub + Stream Analytics for Supplier Risk?**
   - Supplier disruptions require near-real-time detection (geopolitical events, shipping delays, quality alerts)
   - Stream Analytics provides windowed aggregations (tumbling, hopping) for rolling risk scores
   - Event Hub handles bursty ingestion from multiple supplier feeds at scale
   - Decouples ingestion from processing, enabling independent scaling

3. **Why GPT-4o for GenAI Insights Instead of Traditional BI?**
   - Generates natural language explanations of forecast drivers ("demand spike driven by seasonal pattern + promotional uplift")
   - Enables supply chain planners to ask ad-hoc questions in natural language
   - Summarizes supplier risk profiles with actionable recommendations
   - Bridges the gap between ML model output and business decision-making

4. **Why a Medallion Architecture (Bronze/Silver/Gold) on ADLS Gen2?**
   - Bronze layer preserves raw data for auditability and replay
   - Silver layer applies schema enforcement, deduplication, and business logic
   - Gold layer provides curated, query-ready datasets for ML training and analytics
   - Synapse Analytics serves as the query engine over Gold layer for Power BI dashboards

5. **Why Cosmos DB for Supplier and Order Data?**
   - Low-latency reads for real-time supplier risk score lookups
   - Flexible schema accommodates diverse supplier profile structures
   - Global distribution capability for multi-region supply chain operations
   - Serverless mode keeps cost proportional to actual query volume

6. **Security Considerations**
   - All services behind Private Link with no public endpoints exposed
   - Managed Identity eliminates credential management across all service-to-service calls
   - Data Factory uses managed VNET integration runtime for secure data movement
   - Content filtering on Azure OpenAI prevents misuse of the GenAI insights layer
   - Key Vault with RBAC and purge protection secures all connection strings and API keys

### Scalability Considerations

- Event Hub partitions scale horizontally for high-throughput supplier signal ingestion
- Azure ML managed endpoints auto-scale based on inference request volume
- Stream Analytics scales from 1 to 120 streaming units to handle variable load
- Synapse dedicated pool scales from DW100c to DW30000c for analytical workloads
- Redis Cache reduces redundant API calls and serves hot forecast data in sub-millisecond latency
- Data Factory handles parallelized batch ingestion with up to 256 concurrent activities
- Cosmos DB auto-scales RU/s based on demand, with serverless mode for cost efficiency

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2B (Partner Portal + Internal Operations)
- **Visibility:** Partner Portal + Internal — supply chain partners and internal logistics teams
- **Project Score:** 8.5 / 10 (High)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet per supply chain tier, NSG rules |
| Network | Private Link | IoT Hub, Digital Twins, Cosmos DB via private endpoints |
| Identity | OAuth 2.0 | Federated identity for partner portal access |
| Identity | Managed Identity | Zero-secret architecture for internal services |
| Data | Supply Chain Isolation | Tenant-level data isolation between partners |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | Partner-specific encryption keys, rotation policies |
| Application | API Gateway | Rate limiting, request validation for partner APIs |
| Application | Data Classification | Proprietary demand/pricing data marked confidential |
| Monitoring | Sentinel | Supply chain threat detection and anomaly alerts |
| Monitoring | Audit Trail | Partner access and data exchange audit logging |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Vendor Compliance | Required | Third-party vendor security assessment and certification |
| Trade Controls | Enforced | Export control screening (EAR/ITAR) for restricted goods |
| Data Sovereignty | Enforced | Regional data residency per partner jurisdiction |
| Contract Governance | SLA-based | Partner SLAs with penalty clauses for data breaches |
| IP Protection | Enforced | Proprietary algorithm and demand forecast protection |
| Quality Standards | ISO 9001 | Quality management system for supply chain processes |

### Regulatory Applicability
- **Export Administration Regulations (EAR):** Trade compliance for controlled goods
- **ITAR:** International traffic in arms regulations (if defense supply chain)
- **Customs-Trade Partnership (C-TPAT):** Supply chain security standards
- **ISO 28000:** Supply chain security management systems
- **GDPR/CCPA:** Personal data of supply chain contacts and partners
