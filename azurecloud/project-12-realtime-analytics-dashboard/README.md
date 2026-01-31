# Real-Time Analytics Dashboard

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![Azure Data Explorer](https://img.shields.io/badge/Azure%20Data%20Explorer-Kusto-blue)
![Event Hub](https://img.shields.io/badge/Event%20Hub-Streaming-orange)
![Power BI](https://img.shields.io/badge/Power%20BI-Embedded-yellow)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

An enterprise real-time analytics platform that ingests high-velocity telemetry, application logs, and business events through Azure Event Hub and Stream Analytics, storing them in Azure Data Explorer (ADX/Kusto) for sub-second exploratory queries. The platform features a Natural Language-to-KQL (NL-to-KQL) engine powered by Azure OpenAI GPT-4o, enabling non-technical executives to ask plain-English questions that are automatically translated into optimized Kusto queries. Anomaly detection runs continuously on streaming data, triggering intelligent alerts with GenAI-narrated executive summaries delivered through Power BI Embedded dashboards and SignalR-powered real-time notifications.

## Architecture

```
Data Sources
  - IoT Hub Telemetry (MQTT/AMQP)
  - App Logs (Serilog HTTP)
  - Business Events (ERP/CRM Webhooks)
        |
        v
  Azure Event Hub (Kafka-compatible, 32 partitions)
        |
  +-----+-----+-----+
  |           |           |
  v           v           v
Stream       ADX          Blob Archive
Analytics    Streaming    (Cold Storage)
(Windowed    Ingest
 Agg.)       (Hot)
  |
  v
Anomaly Detection --> Azure Functions --> SignalR Push
                      (Alert + GenAI Summary)
        |
        v
Azure Functions (Analytics Engine)
  - NL-to-KQL Handler (GPT-4o)
  - Anomaly Processor
  - Summary Generator
  - Alert Dispatcher
        |
        v
  +-----+-----+-----+
  |           |           |
  v           v           v
Azure Data   Cosmos DB   Redis Cache
Explorer     (Alerts,    (Query Results)
(Kusto)      Metadata)
        |
        v
  User Interfaces
  - Power BI Embedded (Executive Reports)
  - React/Next Web Dashboard (D3.js Charts)
  - Mobile Alerts (Push/Email)
```

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure Data Explorer (ADX) | Primary analytics store; sub-second KQL queries on petabyte-scale data |
| Azure OpenAI (GPT-4o) | NL-to-KQL translation and executive summary generation |
| Azure Event Hub | High-throughput event ingestion (Kafka-compatible, 32 partitions) |
| Azure Stream Analytics | Real-time windowed aggregation (30s tumbling, 5m sliding) |
| Azure Functions (Python 3.11) | NL-to-KQL engine, anomaly processor, alert dispatcher |
| Azure Cosmos DB | Alert metadata, user queries, session history (serverless) |
| Azure SignalR Service | Real-time push notifications to dashboard clients |
| Power BI Embedded | Executive-facing reports and KPI visualizations |
| Azure Redis Cache | Query result caching, NL-to-KQL translation cache |
| Azure Blob Storage | Raw event archive with hot + cool tier lifecycle |
| Azure Front Door | Global load balancing, WAF, SSL termination |
| Azure API Management | OAuth2/JWT auth, rate limiting (100 req/min) |
| Azure Key Vault | ADX connection strings, OpenAI keys |

## Prerequisites

- Azure Subscription with Contributor access
- Azure OpenAI resource with GPT-4o deployed
- Azure Data Explorer cluster (D14_v2 recommended for production)
- Azure Event Hub namespace (Standard tier, 32 partitions)
- Python 3.11+
- Azure Functions Core Tools v4
- Terraform >= 1.5
- Azure CLI >= 2.50
- Node.js 18+ (for React dashboard)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-12-realtime-analytics-dashboard

# Set required environment variables
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export ADX_CLUSTER_URL="https://<your-adx>.eastus2.kusto.windows.net"
export ADX_DATABASE="telemetrydb"
export COSMOS_ENDPOINT="https://<your-cosmos>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<your-keyvault>.vault.azure.net/"
export EVENT_HUB_CONNECTION="<event-hub-connection-string>"
```

### 2. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Install Dependencies and Run Locally

```bash
cd ../src
pip install -r requirements.txt
func start
```

### 4. Test the NL-to-KQL Engine

```bash
# Natural language query
curl -X POST http://localhost:7071/api/nl-query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me the top 5 regions with highest error rates in the last 24 hours"}'

# Fetch dashboard data
curl http://localhost:7071/api/dashboard-data?lookback_hours=24
```

## Testing

```bash
cd tests

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -v -k "test_nl_to_kql"       # NL-to-KQL translation tests
pytest -v -k "test_anomaly"         # Anomaly detection tests
pytest -v -k "test_executive"       # Executive summary tests
pytest -v -k "test_streaming"       # Event Hub streaming tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID SSO with OAuth2/OIDC; Conditional Access policies enforced; MFA required
- **Authorization**: Fine-grained ADX database roles with read-only permissions for query service identity; no .set, .drop, or .alter allowed
- **RBAC**: Department-level access control for dashboards; PIM (Privileged Identity Management) for just-in-time ADX admin
- **Managed Identity**: System-assigned managed identity on all Functions for passwordless auth to ADX, Key Vault, Cosmos DB
- **Network Isolation**: Dedicated VNet (10.0.0.0/16) with Application, Data, and Integration subnets; all PaaS services on Private Link

### Encryption

- **Data at Rest**: AES-256 encryption for ADX, Event Hub, Cosmos DB, and Blob Storage; Customer-Managed Keys (CMK) for ADX and Event Hub via Key Vault
- **Data in Transit**: TLS 1.3 enforced across all services and client connections
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection

### Monitoring

- **Application Insights**: APM for all Azure Functions with distributed tracing across NL-to-KQL, anomaly detection, and alert pipelines
- **Log Analytics**: Centralized logging (100GB/month); ADX cluster diagnostics exported for query performance monitoring
- **Alerts**: Azure Monitor alerts on Stream Analytics input/output watermark lag, Event Hub throttled requests, ADX CPU/ingestion lag, and function error rates
- **Dashboards**: Operations dashboard for Event Hub metrics, Stream Analytics job health, ADX query diagnostics, and cost management

### Visualization

- **Power BI Embedded**: A2 SKU with executive-facing KPI reports, drill-down trend analysis, and anomaly highlights
- **React Web Dashboard**: Interactive analytics UI built with React, TypeScript, and D3.js; Monaco Editor for KQL preview pane
- **SignalR Alert Console**: Real-time anomaly alerts rendered with GenAI-narrated explanations pushed via WebSocket

### Tracking

- **Request Tracing**: Correlation IDs propagated from APIM through Functions, ADX query execution, and Cosmos DB writes
- **Query Audit**: Every NL-to-KQL translation logged in Cosmos DB with user identity, input text, generated KQL, and execution time
- **ADX Audit Logs**: All Kusto queries tracked for compliance and performance analysis
- **Sentinel Integration**: Anomalous data access patterns detected via Microsoft Sentinel SIEM

### Accuracy

- **KQL Validation**: All GPT-4o-generated KQL is parsed and validated before execution; syntax errors rejected before reaching ADX
- **Anomaly Scoring**: ADX built-in `series_decompose_anomalies()` function with configurable sensitivity (default 2.5); anomaly confirmation threshold > 0.8
- **Schema Context**: NL-to-KQL engine receives full ADX table schemas (Telemetry, Requests, Errors, Deployments) with column types and sample values for accurate query generation
- **Row Limits**: MAX_KQL_ROWS set to 10,000 to prevent unbounded queries

### Explainability

- NL-to-KQL responses include both the generated KQL query and a plain-English explanation of what the query does
- Executive summaries highlight the top 3 observations, call out concerning trends, and provide actionable recommendations in non-technical language
- Anomaly alerts include the metric name, observed value, expected range, severity classification, and human-readable description
- KQL preview pane allows power users to inspect and modify generated queries before execution

### Responsibility

- **Content Safety**: Azure AI Content Safety filters block prompt injection attempts in natural language input
- **KQL Injection Prevention**: Generated KQL is parsed and validated; raw string execution is never used
- **Rate Limiting**: APIM enforces 100 requests/min per user to prevent abuse of the OpenAI-backed translation endpoint
- **Human Oversight**: KQL preview pane enables review before execution; executive summaries are advisory, not prescriptive

### Interpretability

- Dashboard metrics are broken down by Region, Time Window, and Service Name for transparent drill-down
- Anomaly detection surfaces the specific metric, timestamp, and statistical deviation that triggered the alert
- Executive summaries are structured with highlights, risk level, and recommendations for clear decision-making
- All query results include column metadata and row counts for data transparency

### Portability

- **Containerization**: Azure Functions packaged as Docker containers; React dashboard deployable as Static Web App or container
- **Infrastructure as Code**: Full Terraform configuration in `infra/main.tf` with multi-environment support (dev/staging/prod)
- **Multi-Cloud Considerations**: Core NL-to-KQL logic decoupled from ADX SDK; Kusto query layer can be adapted to other time-series databases
- **CI/CD**: Azure DevOps pipeline with blue-green deployment strategy, canary rollout (10%), and automated ADX schema migration

## Project Structure

```
project-12-realtime-analytics-dashboard/
|-- docs/
|   |-- ARCHITECTURE.md
|-- infra/
|   |-- main.tf
|-- src/
|   |-- function_app.py
|-- tests/
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/nl-query` | Translate natural language to KQL and execute against ADX |
| POST | `/api/anomaly-detect` | Detect anomalies in metric data; optionally create alerts |
| POST | `/api/executive-summary` | Generate GenAI executive summary from dashboard KPIs |
| GET | `/api/dashboard-data` | Fetch aggregated dashboard data from ADX (lookback_hours param) |
| GET | `/api/health` | Health check endpoint |
| Event | `StreamingTelemetryProcessor` | Event Hub trigger for real-time telemetry anomaly screening |

## License

This project is licensed under the MIT License.
