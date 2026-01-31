# Project 12: Real-Time Analytics Dashboard

## Executive Summary

An enterprise real-time analytics platform that ingests high-velocity telemetry, application logs, and business events through Azure Event Hub and Stream Analytics, storing them in Azure Data Explorer (ADX/Kusto) for sub-second exploratory queries. The system features a Natural Language-to-KQL (NL-to-KQL) engine powered by Azure OpenAI GPT-4o, enabling non-technical executives to ask plain-English questions that are automatically translated into optimized Kusto queries. Anomaly detection runs continuously on streaming data, triggering intelligent alerts with GenAI-narrated executive summaries delivered through Power BI Embedded dashboards and SignalR-powered real-time notifications.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       REAL-TIME ANALYTICS DASHBOARD PLATFORM                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Power BI       │     │  Web Dashboard  │     │  Mobile Alerts  │
│  Embedded       │     │  (React/Next)   │     │  (Push/Email)   │
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
│  (Rate Limit,   │   │  (Dashboard UI) │   │  (Real-time     │
│   Auth, Cache)  │   │                 │   │   Push Updates) │
└────────┬────────┘   └─────────────────┘   └────────┬────────┘
         │                                            │
         │  ┌──────────────────────────────────────────────────────┐
         │  │              PRIVATE VNET (10.0.0.0/16)              │
         │  │  ┌────────────────────────────────────────────────┐  │
         │  │  │         Application Subnet (10.0.1.0/24)       │  │
         ▼  │  │                                                │  │
┌───────────┴──┴──────┐                                         │  │
│  Azure Functions    │◄──────────────────────────────────────┐ │  │
│  (Analytics Engine) │                                       │ │  │
│                     │    ┌──────────────────┐               │ │  │
│ - NL-to-KQL Handler│    │  Azure OpenAI    │               │ │  │
│ - Anomaly Processor│◄───┤  (GPT-4o)        │               │ │  │
│ - Summary Generator│    │  Private Link    │               │ │  │
│ - Alert Dispatcher │    └──────────────────┘               │ │  │
└────────┬────────────┘                                       │ │  │
         │                                                    │ │  │
         │              ┌──────────────────┐                  │ │  │
         ├─────────────►│  Azure Data      │◄─────────────────┘ │  │
         │              │  Explorer (ADX)  │                    │  │
         │              │  - Kusto Engine   │                    │  │
         │              │  - Time-Series DB │                    │  │
         │              │  - Streaming Ingest│                   │  │
         │              └────────┬─────────┘                    │  │
         │                       │                              │  │
         │  ┌────────────────────┼─────────────────────────┐   │  │
         │  │         Data Subnet (10.0.2.0/24)            │   │  │
         │  │                    │                          │   │  │
         │  │    ┌───────────────┼──────────────────┐      │   │  │
         │  │    │               │                  │      │   │  │
         │  │    ▼               ▼                  ▼      │   │  │
         │  │ ┌──────────┐ ┌──────────┐   ┌─────────────┐ │   │  │
         │  │ │ Cosmos DB│ │ Blob     │   │ Redis Cache │ │   │  │
         │  │ │(Metadata,│ │ Storage  │   │ (Query      │ │   │  │
         │  │ │ Alerts)  │ │ (Archive)│   │  Results)   │ │   │  │
         │  │ └──────────┘ └──────────┘   └─────────────┘ │   │  │
         │  └──────────────────────────────────────────────┘   │  │
         │                                                     │  │
         │  ┌──────────────────────────────────────────────┐   │  │
         │  │     Integration Subnet (10.0.3.0/24)         │   │  │
         │  │                                              │   │  │
         │  │  ┌─────────────┐   ┌──────────────────────┐  │   │  │
         │  │  │  Key Vault  │   │  Power BI Embedded   │  │   │  │
         │  │  │  (Secrets)  │   │  (Executive Reports) │  │   │  │
         │  │  └─────────────┘   └──────────────────────┘  │   │  │
         │  └──────────────────────────────────────────────┘   │  │
         └─────────────────────────────────────────────────────┘  │
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │              STREAMING INGESTION PIPELINE                    │
│   │                                                              │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│   │  │ IoT Hub  │    │ App Logs │    │ Business Events      │   │
│   │  │ Telemetry│    │ (Serilog)│    │ (ERP/CRM Webhooks)   │   │
│   │  └─────┬────┘    └────┬─────┘    └──────────┬───────────┘   │
│   │        │              │                      │              │
│   │        └──────────────┼──────────────────────┘              │
│   │                       ▼                                     │
│   │              ┌─────────────────┐                             │
│   │              │  Azure Event    │                             │
│   │              │  Hub (Kafka API)│                             │
│   │              └────────┬────────┘                             │
│   │                       ▼                                     │
│   │              ┌─────────────────┐                             │
│   │              │ Stream Analytics│                             │
│   │              │ (Windowed Agg.) │                             │
│   │              └────────┬────────┘                             │
│   │                       │                                     │
│   │        ┌──────────────┼──────────────┐                      │
│   │        ▼              ▼              ▼                       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐              │
│   │  │ ADX      │  │ Cosmos DB│  │ Anomaly      │              │
│   │  │ Streaming│  │ Change   │  │ Detection    │              │
│   │  │ Ingest   │  │ Feed     │  │ (Functions)  │              │
│   │  └──────────┘  └──────────┘  └──────────────┘              │
│   └─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                            │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor            │  │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)         │  │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘  │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ ADX Query   │  │ Cost Mgmt  │  │ Defender for Cloud       │  │
│  │ Diagnostics │  │ Dashboard   │  │ (Security Posture)       │  │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STREAMING DATA INGESTION FLOW                         │
└─────────────────────────────────────────────────────────────────────────┘

  IoT Sensors       App Servers         ERP/CRM Systems
      │                  │                     │
      ▼                  ▼                     ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────────┐
│ 1a. MQTT/AMQP │ │ 1b. HTTP POST │ │ 1c. Webhook/REST  │
│ IoT Hub       │ │ Serilog Sink  │ │ Event Publisher   │
└───────┬───────┘ └───────┬───────┘ └─────────┬─────────┘
        │                 │                    │
        └─────────────────┼────────────────────┘
                          ▼
                 ┌─────────────────┐
                 │ 2. Event Hub    │
                 │ (Partitioned    │
                 │  Kafka-compat.) │
                 └────────┬────────┘
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
        ┌───────────┐ ┌────────┐ ┌───────────┐
        │ 3a. Stream│ │3b. ADX │ │ 3c. Blob  │
        │ Analytics │ │Streaming│ │ Archive   │
        │ (Window   │ │Ingest  │ │ (Cold)    │
        │  30s/5m)  │ │(Hot)   │ │           │
        └─────┬─────┘ └────────┘ └───────────┘
              │
              ▼
        ┌───────────┐
        │ 4. Anomaly│───────► Azure Functions ───► SignalR Push
        │ Detect    │         (Alert + GenAI       (Real-time
        │ (Sliding  │          Summary)             Notification)
        │  Window)  │
        └───────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    NL-TO-KQL QUERY FLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘

    User Natural Language Query
        │ "Show me the top 5 regions with highest error rates
        │  in the last 24 hours"
        ▼
┌───────────────┐                                  ┌───────────────┐
│ 1. APIM Auth  │                                  │ 8. Render in  │
│ (JWT/OAuth2)  │                                  │ Power BI /    │
└───────┬───────┘                                  │ Dashboard     │
        │                                          └───────┬───────┘
        ▼                                                  │
┌───────────────┐                                  ┌───────────────┐
│ 2. Validate & │                                  │ 7. GenAI      │
│ Sanitize Input│                                  │ Narrative     │
└───────┬───────┘                                  │ (GPT-4o)      │
        │                                          └───────┬───────┘
        ▼                                                  │
┌───────────────┐                                  ┌───────────────┐
│ 3. Schema     │                                  │ 6. Execute    │
│ Context Load  │──────────────────────────────────│ KQL on ADX    │
│ (ADX tables,  │                                  │ & Return Rows │
│  columns, etc)│                                  └───────┬───────┘
└───────┬───────┘                                          │
        │                                                  │
        ▼                                                  │
┌───────────────┐      ┌───────────────┐          ┌───────────────┐
│ 4. GPT-4o     │─────►│ 5. KQL        │─────────►│ Validated     │
│ NL-to-KQL     │      │ Validation &  │          │ KQL Query     │
│ Translation   │      │ Safety Check  │          │               │
└───────────────┘      └───────────────┘          └───────────────┘

    Generated KQL:
    ┌─────────────────────────────────────────────────────┐
    │ AppErrors                                           │
    │ | where Timestamp > ago(24h)                        │
    │ | summarize ErrorCount=count() by Region            │
    │ | top 5 by ErrorCount desc                          │
    │ | project Region, ErrorCount                        │
    └─────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    ANOMALY ALERTING FLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

  Stream Analytics (Windowed Aggregation)
        │
        ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Threshold  │────►│ 2. ML-based   │────►│ 3. Anomaly    │
│ Breach Detect │     │ Anomaly Score │     │ Confirmed     │
│ (Static Rules)│     │ (ADX built-in)│     │ (Score > 0.8) │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                            ┌────────────────────────┼────────────┐
                            │                        │            │
                            ▼                        ▼            ▼
                      ┌───────────┐          ┌───────────┐  ┌──────────┐
                      │ 4. GPT-4o │          │ 5. Store  │  │ 6. Push  │
                      │ Executive │          │ Alert in  │  │ via      │
                      │ Summary   │          │ Cosmos DB │  │ SignalR  │
                      └───────────┘          └───────────┘  └──────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Dashboard | React + TypeScript + D3.js | Interactive analytics UI with live charts |
| Power BI Embedded | Power BI Premium Per User | Executive-facing reports and KPI visuals |
| NL Query Interface | React + Monaco Editor | Natural language input with KQL preview pane |
| Alert Console | React + SignalR Client | Real-time anomaly alerts with GenAI narratives |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL, CDN | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits (100 req/min) | API management, NL-to-KQL endpoint |
| SignalR Service | Serverless mode, 10K connections | Real-time push for alerts and dashboard updates |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| NL-to-KQL Engine | Azure Functions (Python 3.11) | Translates natural language to validated Kusto queries |
| Anomaly Processor | Azure Functions (Event Hub trigger) | Continuous anomaly detection on streaming windows |
| Summary Generator | Azure Functions (Timer + Event trigger) | GPT-4o narrated executive summaries on anomalies |
| Alert Dispatcher | Azure Functions (Cosmos DB trigger) | Routes alerts to SignalR, email, Teams webhooks |
| Query Executor | Azure Functions (HTTP trigger) | Executes validated KQL against ADX, returns results |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | NL-to-KQL translation and executive summaries |
| ADX ML Functions | series_decompose_anomalies() | Built-in time-series anomaly detection |
| Stream Analytics | Tumbling/Sliding Windows | Real-time windowed aggregation and pattern matching |
| Content Safety | Azure AI Content Safety | Input/output filtering for NL queries |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Data Explorer | D14_v2 (8 nodes), Hot cache 30d | Primary analytics store, sub-second KQL queries |
| Event Hub | Standard, 32 partitions, 7d retention | High-throughput event ingestion (Kafka-compatible) |
| Cosmos DB | Serverless, multi-region | Alert metadata, user queries, session history |
| Blob Storage | Hot + Cool tiers, lifecycle policy | Raw event archive, long-term retention |
| Redis Cache | P1 Premium, 6GB | Query result caching, NL-to-KQL translation cache |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protection | ADX connection strings, OpenAI keys |
| Private Link | ADX, Event Hub, Cosmos DB, OpenAI | All PaaS services on private network |
| Managed Identity | System-assigned on all Functions | Passwordless auth to ADX, Key Vault, Cosmos DB |
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication, RBAC for dashboard access |

### 7. Streaming Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Event Hub | Capture to Blob every 5 min | Event archival and replay capability |
| Stream Analytics | 6 SU, 3 jobs (agg, anomaly, route) | Real-time transformations and windowed queries |
| ADX Streaming Ingest | Enabled, 5s latency target | Near-real-time data availability for queries |
| SignalR | Fan-out to dashboard groups | Push anomaly alerts and metric updates to clients |

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
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time ADX Admin) │  │
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
│ │ Encryption  │  │ Key Vault   │  │ Row-Level   │  │ ADX Column-     │  │
│ │ at Rest/    │  │ (CMK for    │  │ Security    │  │ Level Security  │  │
│ │ Transit     │  │  ADX + EH)  │  │ (Cosmos DB) │  │ (Restricted     │  │
│ │ (TLS 1.3)  │  │             │  │             │  │  Viewer Roles)  │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ KQL         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain │  │ Injection   │  │ Filtering       │  │
│ │ (All Funcs) │  │  ADX Roles) │  │ Prevention  │  │ (OpenAI Safety) │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ ADX Audit   │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ Logs (Query │  │ Manager (SOC2,  │  │
│ │             │  │             │  │  Tracking)  │  │  ISO 27001)     │  │
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
    resource_group: rg-analytics-dash-dev
    location: eastus2
    adx_sku: Dev(No SLA)_Standard_E2a_v4
    adx_nodes: 1
    event_hub_sku: Basic
    event_hub_partitions: 4
    stream_analytics_su: 1

  staging:
    subscription: staging-subscription
    resource_group: rg-analytics-dash-stg
    location: eastus2
    adx_sku: Standard_D14_v2
    adx_nodes: 2
    event_hub_sku: Standard
    event_hub_partitions: 8
    stream_analytics_su: 3

  production:
    subscription: prod-subscription
    resource_group: rg-analytics-dash-prod
    location: eastus2
    secondary_location: westus2  # DR
    adx_sku: Standard_D14_v2
    adx_nodes: 8
    adx_hot_cache_days: 30
    event_hub_sku: Standard
    event_hub_partitions: 32
    event_hub_retention_days: 7
    stream_analytics_su: 6
    cosmos_db_mode: serverless
    signalr_units: 10

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /api/health
  adx_schema_migration: incremental
  event_hub_consumer_groups:
    - stream-analytics-agg
    - stream-analytics-anomaly
    - adx-streaming-ingest
    - blob-archive-capture

ci_cd:
  pipeline: Azure DevOps
  stages:
    - lint-and-test
    - deploy-infra (Terraform)
    - deploy-adx-schema (KQL scripts)
    - deploy-functions
    - deploy-stream-analytics
    - integration-tests
    - deploy-dashboard
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure Data Explorer (ADX) | D14_v2 (8 nodes) | ~$8,500 |
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$1,500-3,000 |
| Event Hub | Standard (32 partitions) | ~$800 |
| Stream Analytics | 6 Streaming Units (3 jobs) | ~$450 |
| Azure Functions | Premium EP2 (3 instances) | ~$500 |
| Cosmos DB | Serverless | ~$150 |
| Power BI Embedded | A2 (2 v-cores) | ~$730 |
| SignalR Service | Standard (10 units) | ~$490 |
| Redis Cache | P1 Premium | ~$220 |
| Blob Storage | Hot 2TB + Cool 10TB | ~$250 |
| Key Vault | Standard | ~$10 |
| APIM | Standard | ~$700 |
| Application Insights | Pay-as-you-go (50GB/mo) | ~$120 |
| Log Analytics | Pay-as-you-go (100GB/mo) | ~$250 |
| Azure Monitor | Alerts + Metrics | ~$50 |
| Private Link | 6 endpoints | ~$45 |
| **Total Estimated** | | **~$14,800-16,300** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why Azure Data Explorer (ADX) over Log Analytics or SQL?**
   - ADX is purpose-built for log and telemetry analytics at petabyte scale
   - Sub-second query response on billions of rows using Kusto query language
   - Native time-series functions (series_decompose_anomalies, make-series) for anomaly detection
   - Streaming ingestion provides sub-5-second data freshness, critical for real-time dashboards
   - Cost-effective hot/warm/cold tiering compared to always-hot SQL databases

2. **Why NL-to-KQL with GPT-4o instead of a custom query builder UI?**
   - Executives and business users cannot learn KQL syntax; natural language removes that barrier
   - GPT-4o with schema context (table names, column types, sample values) generates accurate KQL
   - The system includes a KQL validation layer that parses the generated query before execution, preventing injection attacks and syntax errors
   - Caching frequent NL-to-KQL translations in Redis reduces latency and OpenAI token costs
   - The KQL preview pane allows power users to inspect and modify generated queries

3. **Why Event Hub plus Stream Analytics instead of direct ADX ingestion?**
   - Event Hub provides a durable, partitioned buffer that decouples producers from consumers
   - Stream Analytics adds windowed aggregation (tumbling 30s, sliding 5m) before storage, reducing ADX query load for pre-computed metrics
   - Anomaly detection in Stream Analytics runs on aggregated windows, not raw events, reducing false positives
   - Event Hub Capture provides automatic archival to Blob Storage for compliance and replay
   - Kafka-compatible API lets existing producers send data without SDK changes

4. **How does the anomaly alerting pipeline work end-to-end?**
   - Stream Analytics computes windowed aggregates (error rates, latency percentiles, throughput)
   - When a static threshold is breached or the ADX series_decompose_anomalies() function scores above 0.8, an alert event is emitted
   - Azure Functions picks up the alert, enriches it with historical context from ADX, and calls GPT-4o to generate a plain-English executive summary
   - The summary, anomaly metadata, and recommended actions are stored in Cosmos DB
   - SignalR pushes the alert in real-time to connected dashboard clients
   - Optional escalation via email (SendGrid) or Teams webhook for critical severity

5. **Security Considerations for NL-to-KQL**
   - All generated KQL is parsed and validated before execution (no raw string execution)
   - Read-only ADX database permissions for the query service identity (no .set, .drop, .alter)
   - APIM rate limiting prevents abuse of the OpenAI-backed translation endpoint
   - Content Safety filters block prompt injection attempts in natural language input
   - All queries are audit-logged in Cosmos DB with user identity, input text, generated KQL, and execution time

### Scalability Considerations

- ADX auto-scale from 8 to 16 nodes based on CPU and ingestion lag metrics
- Event Hub partitions (32) enable parallel consumer processing for high-throughput ingestion
- Stream Analytics scales up to 24 SUs for burst traffic during peak business hours
- Azure Functions Premium plan with pre-warmed instances eliminates cold start for NL-to-KQL
- Redis caching of top-100 repeated queries reduces ADX load by an estimated 40%
- SignalR scales to 10K concurrent dashboard connections per unit
- Cosmos DB serverless auto-scales for bursty alert writes during incident storms

### Operational Considerations

- ADX cluster diagnostics exported to Log Analytics for query performance monitoring
- Stream Analytics job monitoring via Azure Monitor with alerts on input/output watermark lag
- Event Hub namespace metrics (incoming messages, throttled requests) on the operations dashboard
- Automated KQL schema migration scripts run as part of CI/CD before function deployment
- Blue-green deployment ensures zero-downtime updates to the NL-to-KQL engine
- Disaster recovery: ADX follower database in West US 2 provides read-only replica for failover

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Executive + Internal Analytics)
- **Visibility:** Executive + Internal — C-suite, business analysts, and operations teams
- **Project Score:** 8.5 / 10 (High)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | Synapse, Event Hub, Power BI, OpenAI via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | Department-level access control for dashboards |
| Data | Row-Level Security | RLS in Synapse and Power BI per business unit |
| Data | Column-Level Security | Sensitive KPIs restricted by role |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | Dashboard encryption keys, API credentials |
| Application | Rate Limiting | Query throttling to prevent resource exhaustion |
| Application | Query Governance | Query complexity limits and timeout policies |
| Monitoring | Query Audit | All dashboard queries and exports logged |
| Monitoring | Sentinel | Anomalous data access pattern detection |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Query Audit | Enforced | Complete audit trail for all data queries and exports |
| Dashboard Publishing | Approved | Publishing workflow with business owner sign-off |
| Data Classification | Tagged | All data sources classified by sensitivity level |
| Export Controls | Restricted | Data export limited by role and classification |
| Refresh Governance | Scheduled | Data refresh cadence governed by data freshness SLAs |
| Access Reviews | Quarterly | Dashboard access reviewed and recertified quarterly |

### Regulatory Applicability
- **SOX:** Financial dashboard data integrity and audit trail
- **SOC 2 Type II:** Analytics platform security controls
- **GDPR/CCPA:** Personal data in analytics and reporting
- **Industry-Specific:** Sector-specific reporting requirements
- **Internal Policy:** Executive data access and need-to-know policies
