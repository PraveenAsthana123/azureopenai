# Project 20: Energy & Utilities Smart Grid

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-blue?style=flat)
![IoT Hub](https://img.shields.io/badge/IoT%20Hub-S3-green?style=flat)
![Azure ML](https://img.shields.io/badge/Azure%20ML-LightGBM%20%7C%20XGBoost-orange?style=flat)
![Stream Analytics](https://img.shields.io/badge/Stream%20Analytics-Real--time%20CEP-purple?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade smart grid analytics platform that ingests real-time smart meter telemetry, performs load forecasting and outage prediction using Azure ML, and delivers GenAI-powered grid optimization recommendations via Azure OpenAI GPT-4o. The system processes millions of meter readings per minute through IoT Hub and Event Hub, applies stream analytics for anomaly detection, and stores time-series data for historical analysis. Grid operators receive natural language optimization recommendations, demand response strategies, and predictive maintenance alerts through a real-time operations dashboard powered by Power BI.

## Architecture

```
Smart Meters / Grid Sensors / Weather APIs
                |
         Azure IoT Hub (Device Management, D2C Messaging)
                |
    +-----------+-----------+
    |           |           |
IoT Edge    Event Hub    Stream Analytics
(Local AI)  (High-Thru)  (Real-time CEP)
                |              |
    +-----------+         Anomaly Detection --> Alert Processing (Functions)
    |           |
Time Series  ADLS Gen2    Cosmos DB        Azure ML
Insights     (Raw/Curated) (Processed)    (Load Forecast / Outage Prediction)
                |                              |
         Synapse Analytics              Azure Functions
         (Historical Agg)              (Grid Optimizer)
                |                              |
         Feature Engineering            GPT-4o (NL Recommendations)
                                               |
                                    Power BI / Grid Ops Portal / Mobile Alerts
```

**Key Components:**
- **Grid Operations Portal** (React + TypeScript) -- Real-time grid monitoring, operator workbench
- **Power BI Dashboard** (Embedded, DirectQuery) -- Executive KPIs, load curves, outage maps
- **Azure Functions** (Python 3.11) -- Grid optimization, alert processing, demand response management
- **Azure ML** -- Load forecasting (LightGBM/Prophet), outage prediction (XGBoost/LSTM)

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure IoT Hub (S3) | Device management, D2C telemetry for millions of smart meters |
| Azure IoT Edge | Local anomaly detection, data filtering, protocol translation |
| Azure Event Hub (Premium) | Partitioned ingestion of 1M+ events/sec |
| Azure Stream Analytics | Windowed aggregations, anomaly detection, complex event processing |
| Azure OpenAI (GPT-4o) | Natural language grid optimization recommendations |
| Azure ML Workspace | Load forecasting, outage prediction, anomaly detection models |
| Azure Cosmos DB | Processed meter events, device state, alert history |
| Azure Time Series Insights | Hot path telemetry storage and time-series queries |
| Azure Data Lake Storage Gen2 | Raw/curated/serving data lake for meter data and forecasts |
| Azure Synapse Analytics | Historical aggregations, seasonal analysis, feature engineering |
| Azure Functions | Grid optimization, alert processing, demand response orchestration |
| Power BI Embedded | Real-time streaming dashboards, load curves, outage maps |
| Azure Key Vault (HSM) | SCADA credentials, API keys, grid certificates |
| Application Insights | APM for all cloud services |
| Log Analytics | Centralized logging and diagnostics |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- Azure IoT Hub provisioned
- Event Hub namespace provisioned
- Azure ML workspace provisioned

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-20-energy-smart-grid

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
IOT_HUB_CONNECTION=<iot-hub-connection-string>
COSMOS_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/
ML_ENDPOINT=https://<your-ml-endpoint>.azureml.ms
EVENT_HUB_CONNECTION=<event-hub-connection-string>
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

- **Authentication**: Azure Entra ID (OAuth2/OIDC) with Conditional Access (location + device based) and MFA enforcement for all grid operators
- **Authorization**: RBAC with role separation for Operator, Engineer, and Admin; PIM for just-in-time grid admin access elevation
- **Managed Identity**: System-assigned managed identity for zero-credential cloud service authentication
- **Network Isolation**: Dedicated VNet with OT/IT separation (Application, Data, Integration subnets); all PaaS services behind Private Link; SCADA network air-gapped with DMZ for IT/OT integration
- **IoT Device Security**: X.509 certificate-based device attestation; IoT Hub IP filtering for authorized meter connections only
- **NERC CIP Compliance**: CIP-005 electronic security perimeter, CIP-007 system security management, US-only geo-fencing for grid control

### Encryption

- **Data at Rest**: AES-256 encryption for all data stores; HSM-backed Customer-Managed Keys (CMK) via Key Vault
- **Data in Transit**: TLS 1.3 enforced for all communication; end-to-end encryption for SCADA grid telemetry
- **Key Management**: Azure Key Vault Premium (HSM-backed) for SCADA credentials, grid encryption keys, and device certificates
- **Consumer PII**: Energy usage data encrypted and access-controlled; meter ID anonymization for GDPR/CCPA compliance

### Monitoring

- **Application Insights**: APM for Azure Functions, with custom metrics for grid optimization latency and forecast accuracy
- **Log Analytics**: Centralized diagnostics across IoT Hub, Stream Analytics, ML endpoints, and Functions (100GB/month)
- **Alerts**: Azure Monitor alerts on IoT Hub throttling, Stream Analytics watermark delays, ML endpoint latency degradation, and grid anomalies
- **IoT Diagnostics**: IoT Hub diagnostic logs for device connectivity, message routing, and telemetry delivery

### Visualization

- **Power BI Dashboard**: Real-time streaming datasets with live load curves, outage maps, forecast accuracy metrics, and executive KPIs
- **Grid Operations Portal**: React-based operator workbench with real-time grid state visualization
- **Mobile Alerts**: Push notifications for critical outage and threshold breach alerts
- **NERC CIP Dashboard**: Continuous compliance monitoring for CIP standards

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across IoT Hub ingestion, Stream Analytics processing, ML inference, and GPT-4o optimization
- **Correlation IDs**: End-to-end correlation from meter reading through anomaly detection to operator alert
- **Audit Logs**: 90-day retention for all grid operations; NERC CIP-compliant continuous compliance logging
- **Device Telemetry**: All device readings and alerts persisted in Cosmos DB with timestamps and device metadata

### Accuracy

- **Load Forecasting**: Azure ML models (LightGBM/Prophet) evaluated with MAE, RMSE, and MAPE metrics; champion/challenger model comparison prevents forecast drift
- **Outage Prediction**: XGBoost/LSTM models scored with precision, recall, and AUC-ROC; automated retraining with new meter data
- **Anomaly Detection**: Z-score threshold (2.5 sigma) for consumption spikes and voltage deviations; Stream Analytics ML functions for real-time meter tamper detection
- **Confidence Intervals**: Load forecasts include upper and lower bound predictions for each hourly interval

### Explainability

- Grid optimization recommendations are generated in natural language by GPT-4o, explaining the reasoning behind each action (demand response, DER dispatch, load balancing)
- Load forecast results include the contributing weather factors, historical patterns, and seasonal adjustments that influenced predictions
- Outage predictions include sensor-level alert details showing which readings deviated from normal ranges and by how much

### Responsibility

- **Responsible AI Dashboard**: Azure ML provides model explainability required by utility regulators
- **Consumer Privacy**: Energy usage data anonymized; consumer PII protected per GDPR/CCPA requirements
- **Safety First**: Grid optimization recommendations are advisory; all critical grid control actions require human operator confirmation
- **Environmental Monitoring**: Carbon intensity tracking and renewable generation optimization as part of grid recommendations

### Interpretability

- **Feature Importance**: Load forecasting models expose feature weights (temperature, humidity, day-of-week, historical demand) via Azure ML Responsible AI dashboard
- **Decision Transparency**: Outage predictions include per-sensor severity scores and deviation calculations; grid health scores show weighted component breakdown
- **Threshold Visibility**: All anomaly thresholds (voltage, consumption, temperature) are configurable and visible to operators

### Portability

- **Containerization**: Azure Functions deployable as Docker containers; ML models exportable as ONNX for edge deployment
- **Infrastructure as Code**: Full Terraform configuration in `infra/` for reproducible multi-environment deployments (dev with 1K meters, prod with 5M meters)
- **IoT Edge**: Staged rollout strategy for firmware and model updates across 5M+ devices
- **Multi-Cloud Considerations**: IoT Hub patterns transferable to AWS IoT Core; ML models portable via MLflow/ONNX; Stream Analytics logic portable as Apache Flink jobs
- **Standards**: IEEE standards for grid protection; NERC CIP standards are industry-standard across all cloud providers

## Project Structure

```
project-20-energy-smart-grid/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (meter analysis, forecast, outage, optimize, health)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/meter-analysis` | Analyze smart meter readings for consumption patterns and anomalies |
| POST | `/api/load-forecast` | Generate 24-hour load forecast for a grid region with weather data |
| POST | `/api/outage-predict` | Predict potential outages from sensor anomalies in a grid sector |
| POST | `/api/grid-optimize` | Generate GenAI grid optimization recommendations from current state |
| GET | `/api/grid-health` | Compute weighted grid health score from operational metrics |
| GET | `/api/health` | Health check endpoint |
| Event Hub | `MeterReadingProcessor` | Real-time batch processing of smart meter readings |
| Event Hub | `GridDeviceTelemetry` | Process device telemetry from IoT Hub (transformers, sensors, switches) |

## License

This project is licensed under the MIT License.
