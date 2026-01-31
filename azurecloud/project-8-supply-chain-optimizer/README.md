# Project 8: Supply Chain Optimizer

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=flat&logo=openai&logoColor=white)
![Azure ML](https://img.shields.io/badge/Azure_ML-AutoML-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-Python_3.11-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Event Hub](https://img.shields.io/badge/Event_Hub-Streaming-0078D4?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade supply chain optimization platform that combines demand forecasting, inventory optimization, and supplier risk scoring powered by Azure AI services. The system leverages Azure OpenAI GPT-4o for natural language insights and risk narrative generation, Azure Machine Learning AutoML for time-series demand forecasting (TCNForecaster/Prophet), and a real-time streaming pipeline built on Event Hub and Stream Analytics for live supply chain signal processing. The platform ingests data from ERP systems, supplier portals, logistics feeds, and market signals to deliver actionable recommendations that reduce stockouts, minimize carrying costs, and proactively identify supplier risk.

---

## Architecture

```
Data Sources (ERP Systems, Supplier Portals, Logistics Feeds, Market Signals)
        |
   +----+----+
   |         |
Data Factory  Event Hub
(Batch ETL)   (Real-time)
   |         |
  ADLS Gen2  Stream Analytics
  (Bronze/   (Windowed Aggregations)
   Silver)        |
   |              |
   +----+---------+
        |
   Synapse Analytics (Gold Layer)
        |
   +----+----+----+
   |    |    |    |
Azure  Azure Azure  Redis
ML     OpenAI Cosmos Cache
AutoML GPT-4o DB
(Demand (GenAI  (Orders,
 Fcst)  Insight Suppliers)
        s)
        |
   Azure Functions API Layer
   (Forecast, Inventory, Risk, Insights)
        |
   +----+----+
   |         |
  Web      Power BI
  Dashboard (Embedded
  (React)   Reports)
        |
   Observability (App Insights + Log Analytics + Monitor)
```

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | GenAI narrative insights, supplier risk narratives, demand explanation |
| Azure ML (AutoML) | Time-series demand forecasting (TCNForecaster, Prophet, ARIMA) |
| Azure Event Hub | Real-time ingestion of supplier and logistics signals (8 partitions) |
| Azure Stream Analytics | Windowed aggregations for rolling supplier risk scores (6 SU) |
| Azure Synapse Analytics | Gold layer analytics, feature store (DW500c production) |
| ADLS Gen2 | Medallion data lake (Bronze/Silver/Gold) for raw and curated datasets |
| Azure Cosmos DB | Supplier profiles, risk scores, order history (serverless SQL API) |
| Azure Cache for Redis | Forecast cache, hot supplier data, session state |
| Azure Data Factory | Batch ETL from ERP systems with managed VNet IR |
| Azure Blob Storage | Raw file exports, ML model artifacts |
| Azure Key Vault | Secrets, API keys, connection strings (RBAC + purge protection) |
| Power BI Embedded | Interactive forecast dashboards, KPI reports (A2 tier) |
| Azure APIM | API gateway with OAuth2, rate limiting, caching |
| Application Insights | APM, distributed tracing, ML model monitoring |
| Log Analytics | Centralized logging (50GB/day) |

---

## Prerequisites

- **Azure Subscription** with the following resources:
  - Azure OpenAI Service (GPT-4o deployment)
  - Azure Machine Learning workspace with compute cluster (DS5_v2)
  - Azure Event Hub namespace (Standard tier)
  - Azure Stream Analytics job (6 SU)
  - Azure Synapse Analytics workspace (DW200c+ dedicated pool)
  - ADLS Gen2 storage account
  - Azure Cosmos DB (serverless)
  - Azure Data Factory with managed VNet integration runtime
- **Python 3.11+** with numpy
- **Azure Functions Core Tools v4**
- **Azure CLI** (authenticated)

---

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-8-supply-chain-optimizer

# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://<openai-resource>.openai.azure.com/"
export COSMOS_ENDPOINT="https://<cosmos-account>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<keyvault-name>.vault.azure.net/"
export ML_ENDPOINT="https://<ml-endpoint>.inference.ml.azure.com"
export EVENT_HUB_CONNECTION="<event-hub-connection-string>"
```

### 2. Install dependencies

```bash
cd src
pip install -r requirements.txt
```

### 3. Run locally

```bash
func start
```

### 4. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -var-file="env/dev.tfvars"
terraform apply -var-file="env/dev.tfvars"
```

### 5. Deploy function app

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

### 6. Train forecasting model

```bash
# Submit AutoML training job
az ml job create -f training/demand-forecast-automl.yml \
  --workspace-name <ml-workspace> --resource-group <rg>
```

---

## Testing

```bash
# Run unit tests
cd tests
python -m pytest -v

# Run tests with coverage
python -m pytest --cov=src --cov-report=html -v
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Entra ID OAuth2/OIDC with conditional access policies; federated identity for partner portal access
- **Authorization**: Fine-grained RBAC for supply chain planners, analysts, and partner users; API throttling per role
- **RBAC**: Separate roles for demand planners, procurement managers, and partner portal users
- **Managed Identity**: System-assigned managed identity for all Azure service calls -- zero credentials in code
- **Network Isolation**: Dedicated VNet with Application, Data, and Integration subnets; all PaaS services via Private Link; NSG deny-all default with least-privilege rules; Data Factory managed VNet IR for secure ETL

### Encryption

- **Data at Rest**: AES-256 encryption for ADLS Gen2, Cosmos DB, Synapse, and Blob Storage; CMK via Key Vault for sensitive supply chain data
- **Data in Transit**: TLS 1.3 for all service endpoints; encrypted Event Hub connections
- **Key Management**: Key Vault with RBAC, soft delete, and purge protection; partner-specific encryption key rotation policies
- **Data Classification**: Proprietary demand forecasts and pricing data marked confidential via Purview data classification

### Monitoring

- **Application Insights**: APM for Azure Functions with custom metrics for forecast latency, risk score distribution, and Event Hub throughput
- **Log Analytics**: Centralized logging (50GB/day) for function execution, Stream Analytics output, and Data Factory pipeline runs
- **Alerts**: Configured for forecast accuracy degradation, Event Hub consumer lag, Synapse pool saturation, and supplier risk threshold breaches
- **ML Model Monitoring**: Azure ML model monitoring for data drift, prediction accuracy, and retraining triggers
- **Dashboards**: Azure Monitor operational dashboards; cost management dashboard tracking compute and token spend

### Visualization

- **Power BI Embedded**: Interactive dashboards for demand forecasts, inventory levels, supplier rankings, and KPI scorecards (A2 tier with row-level security)
- **Web Dashboard**: React/Next.js supply chain command center UI
- **Mobile App**: React Native for on-the-go alerts and approvals

### Tracking

- **Request Tracing**: Application Insights distributed tracing with correlation IDs across forecast, optimization, and risk scoring calls
- **Correlation IDs**: MD5-hashed IDs generated per forecast, risk assessment, and event processing for end-to-end traceability
- **Audit Logs**: All supply chain events persisted to Cosmos DB `supplyChainEvents` container with event type, payload, processed timestamp, and enqueued time
- **Partner Access Audit**: All partner data exchange and API access logged for compliance

### Accuracy

- **Model Evaluation**: AutoML evaluates multiple algorithms (TCN, Prophet, ARIMA, ExponentialSmoothing) and selects best by MAPE/RMSE
- **Confidence Intervals**: Forecasts include `lower_bound` and `upper_bound` confidence intervals plus overall confidence score (0.0-1.0)
- **Statistical Features**: Each forecast includes computed `mean`, `std`, `trend_slope`, and data point count for validation
- **Inventory Math**: Safety stock calculated using z-score at 95% service level; EOQ based on standard economic order quantity formula
- **Retraining Schedule**: Weekly model retraining to prevent drift

### Explainability

- **Forecast Narratives**: GPT-4o generates natural language explanations of forecast drivers (e.g., "demand spike driven by seasonal pattern + promotional uplift")
- **Risk Breakdown**: Supplier risk assessments include individual `risk_factors` with per-factor scores and explanations
- **Trend Detection**: Forecasts explicitly report `trend` direction (increasing/decreasing/stable) and `seasonality_detected` flag
- **Inventory Actions**: Optimization results include clear `recommended_action` (URGENT_REORDER, REORDER, MONITOR, ADEQUATE) with supporting metrics

### Responsibility

- **Content Filtering**: Azure OpenAI content filters enabled for all insight generation
- **Bias Awareness**: Forecasting models validated across product categories and regions to detect systematic bias
- **Trade Compliance**: Export control screening (EAR/ITAR) for restricted goods in supply chain data
- **IP Protection**: Proprietary demand forecast algorithms and pricing data protected with access controls

### Interpretability

- **Feature Importance**: AutoML provides feature importance rankings for demand forecast models; statistical features (lag, seasonality, trend) explicitly computed
- **Decision Transparency**: Inventory optimization returns all intermediate calculations (daily demand mean/std, safety stock, reorder point, EOQ, days of supply)
- **Risk Factor Decomposition**: Supplier risk scored across multiple factors (lead time, quality, financial stability, geographic risk) with individual scores

### Portability

- **Infrastructure as Code**: Terraform modules in `infra/` for complete environment provisioning across dev/staging/production
- **Containerization**: Azure Functions can be containerized; ML endpoints use managed online endpoints with versioned model artifacts
- **Multi-Cloud Considerations**: Core forecasting logic uses numpy and standard Python; can be adapted for AWS SageMaker or GCP Vertex AI
- **Environment Configuration**: All service endpoints externalized via environment variables; Key Vault for sensitive configuration

---

## Project Structure

```
project-8-supply-chain-optimizer/
|-- docs/
|   +-- ARCHITECTURE.md
|-- infra/
|   +-- main.tf
|-- src/
|   +-- function_app.py
|-- tests/
+-- README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/demand-forecast` | Generate demand forecast with confidence intervals and trend analysis |
| POST | `/api/inventory-optimize` | Calculate optimal inventory levels, safety stock, and reorder points |
| POST | `/api/supplier-risk` | Score supplier risk with factor breakdown and mitigation recommendations |
| POST | `/api/supply-insights` | Generate GenAI executive narrative on overall supply chain health |
| GET | `/api/health` | Health check endpoint |
| -- | `SupplyChainEventProcessor` | Event Hub trigger: process real-time supply chain events |

---

## License

This project is licensed under the MIT License.
