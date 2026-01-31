# Project 20: Energy & Utilities Smart Grid

## Executive Summary

An enterprise-grade smart grid analytics platform that ingests real-time smart meter telemetry, performs load forecasting and outage prediction using Azure ML, and delivers GenAI-powered grid optimization recommendations via Azure OpenAI GPT-4o. The system processes millions of meter readings per minute through IoT Hub and Event Hub, applies stream analytics for anomaly detection, and stores time-series data for historical analysis. Grid operators receive natural language optimization recommendations, demand response strategies, and predictive maintenance alerts through a real-time operations dashboard powered by Power BI and a custom web portal.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      ENERGY & UTILITIES SMART GRID PLATFORM                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Smart Meters   │     │  Grid Sensors   │     │  Weather APIs   │
│  (AMI Devices)  │     │  (SCADA/PMU)    │     │  (External Feed)│
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure IoT Hub         │
                    │   (Device Management,   │
                    │    D2C Messaging)        │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Azure IoT Edge │   │  Event Hub      │   │  Azure Stream   │
│  (Edge AI &     │   │  (High-Thruput  │   │  Analytics      │
│   Local Alerts) │   │   Ingestion)    │   │  (Real-time CEP)│
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                      │
         │  ┌──────────────────┼──────────────────────┘
         │  │                  │
         │  │  ┌───────────────┼───────────────────────────────────┐
         │  │  │              PRIVATE VNET (10.0.0.0/16)           │
         │  │  │  ┌─────────────────────────────────────────┐      │
         │  │  │  │      Application Subnet (10.0.1.0/24)   │      │
         ▼  ▼  │  │                                         │      │
┌──────────────┐│  │  ┌─────────────────┐                   │      │
│ Azure        ││  │  │  Azure OpenAI   │                   │      │
│ Functions    ││  │  │  (GPT-4o)       │                   │      │
│              ││  │  │  Private Link   │                   │      │
│ - Grid Optim.│◄─┼──┤  - Optimization │                   │      │
│ - Alert Proc.│  │  │    Recommends   │                   │      │
│ - Demand Resp│  │  │  - NL Summaries │                   │      │
└──────┬───────┘  │  └─────────────────┘                   │      │
       │          │                                         │      │
       │          │  ┌─────────────────┐                    │      │
       │          │  │  Azure ML       │                    │      │
       │          │  │  (Workspace)    │                    │      │
       ├──────────┼─►│  - Load Forecast│                    │      │
       │          │  │  - Outage Pred. │                    │      │
       │          │  │  - Anomaly Det. │                    │      │
       │          │  └─────────────────┘                    │      │
       │          │                                         │      │
       │          │  └─────────────────────────────────────┘│      │
       │          │                                         │      │
       │          │  ┌─────────────────────────────────────┐│      │
       │          │  │      Data Subnet (10.0.2.0/24)      ││      │
       │          │  │                                     ││      │
       │          │  │  ┌──────────┐  ┌───────────────┐    ││      │
       │          │  │  │ Cosmos DB│  │ Time Series   │    ││      │
       ├──────────┼──┼─►│(Meter    │  │ Insights      │    ││      │
       │          │  │  │ Events)  │  │ (Telemetry)   │    ││      │
       │          │  │  └──────────┘  └───────────────┘    ││      │
       │          │  │                                     ││      │
       │          │  │  ┌──────────┐  ┌───────────────┐    ││      │
       │          │  │  │ ADLS     │  │ Synapse       │    ││      │
       │          │  │  │ Gen2     │  │ Analytics     │    ││      │
       │          │  │  │ (Raw/    │  │ (Historical   │    ││      │
       │          │  │  │  Curated)│  │  Aggregations)│    ││      │
       │          │  │  └──────────┘  └───────────────┘    ││      │
       │          │  └─────────────────────────────────────┘│      │
       │          │                                         │      │
       │          │  ┌─────────────────────────────────────┐│      │
       │          │  │  Integration Subnet (10.0.3.0/24)   ││      │
       │          │  │                                     ││      │
       │          │  │  ┌─────────────┐  ┌──────────────┐  ││      │
       │          │  │  │  Key Vault  │  │ APIM Gateway │  ││      │
       │          │  │  │  (Secrets/  │  │ (Rate Limit, │  ││      │
       │          │  │  │   Certs)    │  │  Auth, Cache) │  ││      │
       │          │  │  └─────────────┘  └──────────────┘  ││      │
       │          │  └─────────────────────────────────────┘│      │
       │          └─────────────────────────────────────────┘      │
       │                                                           │
       │  ┌────────────────────────────────────────────────────┐   │
       │  │              OPERATIONS DASHBOARD                   │   │
       │  │                                                     │   │
       │  │  ┌──────────┐   ┌──────────────┐  ┌─────────────┐  │   │
       └──┼─►│ Power BI │   │ Grid Ops     │  │ Mobile      │  │   │
          │  │ (Real-   │   │ Web Portal   │  │ Alerts      │  │   │
          │  │  time)   │   │ (React/Next) │  │ (Push)      │  │   │
          │  └──────────┘   └──────────────┘  └─────────────┘  │   │
          └────────────────────────────────────────────────────┘   │
                                                                    │
┌───────────────────────────────────────────────────────────────────┘
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │                    OBSERVABILITY LAYER                       │
│   │                                                              │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│   │  │ App Insights│  │Log Analytics│  │ Azure Monitor       │  │
│   │  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)    │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│   │                                                              │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│   │  │ IoT Hub     │  │ Cost Mgmt  │  │ Defender for Cloud  │  │
│   │  │ Diagnostics │  │ Dashboard   │  │ (Security)          │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│   └─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  METER DATA INGESTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

Smart Meter Reading                              Real-Time Alert
      │                                                ▲
      ▼                                                │
┌───────────────┐                              ┌───────────────┐
│ 1. IoT Hub    │                              │ 8. Azure      │
│ (D2C Message) │                              │ Functions     │
└───────┬───────┘                              │ (Alert Proc.) │
        │                                      └───────┬───────┘
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 2. IoT Edge   │                              │ 7. Anomaly    │
│ (Edge Filter/ │                              │ Detection     │
│  Pre-process) │                              │ (Stream Ana.) │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 3. Event Hub  │──────────────────────────────│ 6. Stream     │
│ (Partitioned  │                              │ Analytics     │
│  Ingestion)   │                              │ (Windowed Agg)│
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐     ┌───────────────┐       ┌───────────────┐
│ 4. Time Series│     │ 5. ADLS Gen2  │       │ Cosmos DB     │
│ Insights      │────►│ (Raw Zone)    │──────►│ (Processed    │
│ (Hot Store)   │     │               │       │  Events)      │
└───────────────┘     └───────────────┘       └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                  LOAD FORECASTING & OPTIMIZATION FLOW                    │
└─────────────────────────────────────────────────────────────────────────┘

Historical Data                                Optimization Report
      │                                                ▲
      ▼                                                │
┌───────────────┐                              ┌───────────────┐
│ 1. Synapse    │                              │ 7. Power BI / │
│ Analytics     │                              │ Grid Portal   │
│ (SQL Pool)    │                              │ (Dashboard)   │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐                              ┌───────────────┐
│ 2. Feature    │                              │ 6. GPT-4o     │
│ Engineering   │                              │ (NL Grid      │
│ (Weather +    │                              │  Optimization │
│  Calendar)    │                              │  Recommends)  │
└───────┬───────┘                              └───────┬───────┘
        │                                              │
        ▼                                              │
┌───────────────┐     ┌───────────────┐       ┌───────────────┐
│ 3. Azure ML   │────►│ 4. Forecast   │──────►│ 5. Azure      │
│ (Training     │     │ Results       │       │ Functions     │
│  Pipeline)    │     │ (ADLS Gen2)   │       │ (Orchestrator)│
└───────────────┘     └───────────────┘       └───────────────┘
```

---

## Component Details

### 1. IoT & Edge Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Smart Meter Ingestion | Azure IoT Hub (S3) | Device management, D2C telemetry for millions of meters |
| Edge Processing | Azure IoT Edge | Local anomaly detection, data filtering, protocol translation |
| High-Throughput Streaming | Azure Event Hub (Premium) | Partitioned ingestion of 1M+ events/sec |
| Real-Time Analytics | Azure Stream Analytics | Windowed aggregations, anomaly detection, complex event processing |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| APIM Gateway | OAuth2/JWT, Rate limits | API management for grid ops portal and partner integrations |
| Private Link | All PaaS services | Zero-trust network isolation for critical infrastructure |
| Entra ID | RBAC + Conditional Access | Operator/engineer authentication with MFA |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Grid Optimization Service | Azure Functions (Python 3.11) | Orchestrates GPT-4o recommendations with ML forecasts |
| Alert Processing Engine | Azure Functions (Python 3.11) | Processes anomaly alerts, triggers demand response actions |
| Demand Response Manager | Azure Functions (Python 3.11) | Coordinates load shedding and DER dispatch signals |
| Forecast Scheduler | Azure Functions (Timer Trigger) | Triggers hourly/daily ML forecast pipeline runs |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Natural language grid optimization recommendations |
| Load Forecasting | Azure ML (LightGBM/Prophet) | Short-term (1h-24h) and medium-term (7d-30d) demand forecasting |
| Outage Prediction | Azure ML (XGBoost/LSTM) | Equipment failure and outage probability scoring |
| Anomaly Detection | Stream Analytics ML | Real-time meter tamper and voltage anomaly detection |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Cosmos DB | Multi-region, serverless | Processed meter events, device state, alert history |
| Time Series Insights | Gen2, warm/cold store | Hot path telemetry storage and time-series queries |
| ADLS Gen2 | Hierarchical namespace, zones | Raw/curated/serving data lake (raw meter data, forecasts) |
| Synapse Analytics | Dedicated SQL pool | Historical aggregations, reporting, feature engineering |

### 6. Presentation Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| Grid Operations Portal | React + TypeScript | Real-time grid monitoring, operator workbench |
| Power BI Dashboard | Embedded, DirectQuery | Executive KPIs, load curves, outage maps |
| Mobile Alerts | Push Notifications | Critical outage and threshold breach alerts |

### 7. Security & Governance Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, HSM-backed | SCADA credentials, API keys, certificates |
| Private Link | All PaaS services | Network isolation for NERC CIP compliance |
| Managed Identity | System-assigned | Zero-credential service-to-service authentication |
| Entra ID | OAuth2/OIDC + RBAC | Operator authentication, role-based grid access |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│              SECURITY LAYERS - CRITICAL INFRASTRUCTURE (NERC CIP)        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY (NERC CIP-005 - Electronic Security)        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-Fencing     │ │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (US-Only for    │ │
│ │             │  │             │  │ Standard    │  │  Grid Control)  │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS (NERC CIP-004 - Personnel & Training)        │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │ │
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time Grid       │ │
│ │             │  │ (Location + │  │ (All Ops)   │  │  Admin Access)  │ │
│ │             │  │  Device)    │  │             │  │                 │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY (NERC CIP-005 - Network Segmentation)         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ IoT Hub         │ │
│ │ Isolation   │  │ (Deny-All   │  │ Endpoints   │  │ IP Filtering    │ │
│ │ (OT/IT Sep.)│  │  Default)   │  │ (All PaaS)  │  │ (Device Allow)  │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY (NERC CIP-011 - Information Protection)          │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ Encryption  │  │ Key Vault   │  │ Data        │  │ Customer PII    │ │
│ │ at Rest/    │  │ (HSM-backed │  │ Masking     │  │ Anonymization   │ │
│ │ Transit     │  │  CMK)       │  │ (Meter IDs) │  │ (GDPR/CCPA)     │ │
│ │ (TLS 1.3)  │  │             │  │             │  │                 │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY (NERC CIP-007 - System Security Mgmt)     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ Managed     │  │ RBAC        │  │ API         │  │ IoT Device      │ │
│ │ Identity    │  │ (Operator/  │  │ Throttling  │  │ Attestation     │ │
│ │ (Zero Cred.)│  │  Engineer/  │  │ (Per-Device │  │ (X.509 Certs)   │ │
│ │             │  │  Admin)     │  │  Rate Limit)│  │                 │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE (NERC CIP-008 - Incident Response)     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ NERC CIP        │ │
│ │ for IoT     │  │ (SIEM +     │  │ (90-Day     │  │ Compliance      │ │
│ │ (OT Threat) │  │  SOAR)      │  │  Retention) │  │ Dashboard       │ │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy - Smart Grid Platform

environments:
  development:
    subscription: dev-energy-subscription
    resource_group: rg-smart-grid-dev
    location: eastus
    sku_tier: basic
    iot_hub_sku: S1
    meter_simulation: true
    device_count: 1000

  staging:
    subscription: staging-energy-subscription
    resource_group: rg-smart-grid-stg
    location: eastus
    sku_tier: standard
    iot_hub_sku: S2
    meter_simulation: false
    device_count: 50000

  production:
    subscription: prod-energy-subscription
    resource_group: rg-smart-grid-prod
    location: eastus
    secondary_location: westus2
    sku_tier: premium
    iot_hub_sku: S3
    device_count: 5000000

    high_availability:
      iot_hub_units: 4
      event_hub_throughput_units: 20
      stream_analytics_streaming_units: 48
      cosmos_db_multi_region: true
      adls_geo_redundant: true

    disaster_recovery:
      rpo_minutes: 5
      rto_minutes: 30
      failover_region: westus2
      iot_hub_failover: manual
      cosmos_db_failover: automatic

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 5
  health_check_path: /health
  iot_edge_update: staged-rollout
  edge_rollout_percentage: 10

compliance:
  nerc_cip: true
  soc2: true
  fedramp: moderate
  data_residency: us-only
  audit_log_retention_days: 90
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure IoT Hub | S3 (4 units, 5M msgs/unit/day) | ~$10,000 |
| Azure IoT Edge | Runtime on field gateways | ~$0 (included) |
| Azure Event Hub | Premium (20 TUs) | ~$2,200 |
| Azure Stream Analytics | 48 Streaming Units | ~$4,400 |
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$1,500-3,000 |
| Azure ML Workspace | Standard + compute | ~$2,000 |
| Azure Functions | Premium EP2 (3 instances) | ~$600 |
| Cosmos DB | Multi-region, provisioned 10K RU/s | ~$1,200 |
| Time Series Insights | Gen2 (warm + cold store) | ~$800 |
| ADLS Gen2 | Hot (5TB) + Cool (50TB) | ~$1,100 |
| Synapse Analytics | DW200c Dedicated Pool | ~$1,800 |
| Key Vault | Premium (HSM) | ~$30 |
| APIM | Standard | ~$700 |
| Power BI Embedded | A2 capacity | ~$900 |
| Application Insights | Pay-as-you-go (50GB/month) | ~$150 |
| Log Analytics | Pay-as-you-go (100GB/month) | ~$300 |
| Azure Monitor | Metrics + Alerts | ~$100 |
| Private Link | 12 endpoints | ~$90 |
| **Total Estimated** | | **~$27,870-29,370** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why IoT Hub + Event Hub dual ingestion?**
   - IoT Hub provides device identity management, twin state, D2C/C2D communication, and edge deployment orchestration for millions of smart meters
   - Event Hub acts as a high-throughput buffer (1M+ events/sec) between IoT Hub and Stream Analytics, decoupling ingestion from processing
   - IoT Edge enables local anomaly detection at substations, reducing cloud bandwidth and providing sub-second alerting for critical grid events

2. **Why Stream Analytics for real-time processing?**
   - Native integration with IoT Hub and Event Hub eliminates custom connector code
   - Tumbling and hopping window aggregations are ideal for meter reading intervals (15-min, 1-hr)
   - Built-in anomaly detection ML functions for voltage irregularities and meter tampering
   - Exactly-once processing guarantees critical for billing-grade meter data

3. **Why GPT-4o for grid optimization instead of rule-based systems?**
   - Natural language recommendations allow operators of varying skill levels to understand complex grid conditions
   - GPT-4o synthesizes ML forecast outputs, weather data, and historical patterns into actionable optimization strategies
   - Prompt engineering enables domain-specific recommendations (demand response, DER dispatch, load balancing)
   - Faster iteration than building and maintaining complex rule engines across thousands of grid scenarios

4. **Why Time Series Insights + ADLS Gen2 + Synapse (Lambda architecture)?**
   - Time Series Insights provides sub-second hot-path queries for real-time dashboards
   - ADLS Gen2 stores raw meter data in Parquet format for ML training and regulatory audit
   - Synapse Analytics handles complex historical aggregations, seasonal analysis, and feature engineering for ML models
   - Lambda pattern ensures both real-time responsiveness and batch accuracy for billing and compliance

5. **NERC CIP Compliance considerations**
   - CIP-005: Network segmentation isolates OT (SCADA/meter) traffic from IT (portal/analytics) using VNet subnets and NSGs
   - CIP-007: IoT device attestation via X.509 certificates ensures only authorized meters connect
   - CIP-011: Meter ID anonymization and HSM-backed encryption protect customer PII
   - CIP-008: Sentinel SIEM with automated playbooks enables rapid incident response for cyber-physical threats

6. **Why Azure ML over custom model serving?**
   - MLflow integration provides experiment tracking and model versioning critical for regulated forecasting models
   - Managed endpoints with auto-scaling handle variable inference load (peak demand periods)
   - Responsible AI dashboard provides model explainability required by utility regulators
   - Pipeline orchestration automates daily retraining as new meter data accumulates

### Scalability Considerations

- IoT Hub S3 with 4 units handles 20 million messages per day; horizontal scaling to additional units for grid expansion
- Event Hub Premium with 20 throughput units provides 20 MB/sec ingestion; auto-inflate up to 40 TUs during peak periods
- Stream Analytics with 48 SUs processes complex event patterns across millions of simultaneous meter streams
- Cosmos DB multi-region write ensures sub-10ms reads for real-time grid state queries; auto-scale RU/s during demand spikes
- ADLS Gen2 hierarchical namespace enables efficient partition pruning for time-range queries across petabytes of historical meter data
- Azure Functions Premium with VNET integration eliminates cold starts for latency-sensitive grid optimization requests
- IoT Edge staged rollout strategy ensures firmware and model updates reach 5M+ devices safely over configurable waves

### Operational Excellence

- Azure Monitor alerts on IoT Hub throttling, Stream Analytics watermark delays, and ML endpoint latency degradation
- Log Analytics workspace aggregates diagnostics across all services for unified troubleshooting with Kusto queries
- Power BI real-time streaming datasets provide grid operators with live load curves, outage maps, and forecast accuracy metrics
- Automated ML pipeline retraining with champion/challenger model comparison prevents forecast model drift
- Disaster recovery with IoT Hub manual failover and Cosmos DB automatic failover achieves RPO < 5 min and RTO < 30 min

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2B / B2C (Utility Operations + Consumer Portal)
- **Visibility:** Utility Ops + Consumer Portal — grid operators and energy consumers
- **Project Score:** 9.0 / 10 (Critical)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | SCADA Isolation | Air-gapped SCADA network, DMZ for IT/OT integration |
| Network | Private Link | IoT Hub, Time Series, ML Workspace via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for cloud services |
| Identity | NERC CIP Access | Personnel risk assessment and access authorization |
| Data | SCADA Encryption | End-to-end encryption for all grid telemetry |
| Data | Consumer PII | Energy usage data encrypted and access-controlled |
| Data | Encryption | AES-256 at rest, TLS 1.3 in transit |
| Data | Key Vault | Grid encryption keys, SCADA certificates |
| Application | Grid Isolation | Logical isolation between grid control and analytics |
| Application | Firmware Security | Signed firmware for smart meters and grid devices |
| Monitoring | NERC CIP Logging | Continuous compliance monitoring for CIP standards |
| Monitoring | Sentinel | IT/OT security event correlation for grid infrastructure |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| NERC CIP-002–014 | Enforced | Critical infrastructure protection standards compliance |
| FERC Compliance | Aligned | Federal Energy Regulatory Commission requirements |
| Grid Reliability | Monitored | Real-time grid reliability metrics and SLA tracking |
| Demand Response | Governed | Consumer program enrollment and consent management |
| Safety Standards | IEEE | IEEE standards for grid protection and safety |
| Environmental | EPA | Environmental impact monitoring and reporting |

### Regulatory Applicability
- **NERC CIP-002 through CIP-014:** Critical infrastructure protection standards
- **FERC Orders:** Federal Energy Regulatory Commission compliance
- **IEEE Standards:** Grid protection and power systems safety
- **EPA Regulations:** Environmental monitoring and emissions reporting
- **State PUC:** State public utility commission requirements
- **GDPR/CCPA:** Consumer energy usage data privacy
