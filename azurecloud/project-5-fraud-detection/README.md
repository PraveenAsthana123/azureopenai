# Financial Fraud Detection Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure ML](https://img.shields.io/badge/Azure_ML-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-00A4EF?style=flat&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-Ensemble-EC6100?style=flat)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade fraud detection system combining traditional ML anomaly detection with GenAI-powered explainability. The platform processes financial transactions in real-time through a weighted ensemble model (Isolation Forest 30% + XGBoost 45% + Neural Network 25%), applies business rules, and generates human-readable explanations for fraud analysts using Azure OpenAI GPT-4o. Transactions are scored 0-100 and routed to ALLOW (<30), REVIEW (30-70), or BLOCK (>=70) with sub-200ms P99 latency targets.

## Architecture

```
Data Sources (Core Banking / Card Networks / Payment Gateways)
        |
   Azure Event Hub (Transaction Stream, 7-day retention)
        |
   +----+----+----+
   |         |         |
Stream     Azure     Azure ML
Analytics  Functions  Real-time
(Velocity  (Feature   Endpoint
 Agg.)     Enrich.)  (Scoring)
        |
   Fraud Decision Engine
   |         |              |
Rules     ML Ensemble    Decision
Engine    (IF+XGB+NN)   Aggregator
                         (0-100)
        |
   +----+----+----+
   |         |         |
ALLOW     REVIEW     BLOCK
(<30)    (30-70)    (>=70)
              |
   GenAI Explainability (GPT-4o)
   (Case Summary + Risk Explanation + Recommended Actions)
              |
   Fraud Analyst Dashboard
        |
   +----+----+
   |         |
Synapse   Power BI
(Data     (Dashboards)
 Lake)
```

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure ML | Workspace + Endpoints | Model training, registry, real-time scoring endpoints |
| Azure OpenAI | GPT-4o | Case summarization, risk explanation, recommended actions |
| Azure Stream Analytics | Standard | Real-time velocity aggregations (txn/hour, amount/window) |
| Azure Event Hub | Standard | High-throughput transaction streaming (partitioned by account) |
| Azure Cosmos DB | Serverless | Customer profiles, velocity features, real-time feature lookup |
| Azure Databricks | Premium | Feature engineering, graph analysis, batch processing |
| Azure Synapse Analytics | Serverless | Data lake (raw, curated zones), feature store, analytics |
| ADLS Gen2 | Hot tier | Raw zone, curated zone (Delta Lake), model artifacts |
| Azure SQL | Standard | Transaction metadata, case management |
| Azure Key Vault | Standard | Secrets, CMK encryption keys, model signing keys |
| Azure Purview | Standard | Data governance, lineage tracking, classification |
| Azure Functions | Premium EP1 (Python 3.11) | Feature enrichment, scoring API, rules engine |
| Application Insights | Pay-as-you-go | Application telemetry, scoring latency tracking |
| Power BI | Premium | Fraud dashboards, false positive rate, detection metrics |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50
- Terraform >= 1.5
- Python 3.11+
- Azure ML workspace with compute clusters
- Azure OpenAI resource with GPT-4o deployment
- Required Python packages: `xgboost`, `scikit-learn`, `shap`, `mlflow`, `pandas`, `numpy`

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-5-fraud-detection

# Copy environment template
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### 2. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Train the ensemble model

```bash
cd src/ml
pip install -r requirements.txt

python training_pipeline.py \
  --data-path /mnt/data/transactions \
  --output-path /mnt/outputs \
  --experiment-name fraud-detection
```

### 4. Run the real-time scoring function

```bash
cd ../realtime
func start
```

### 5. Score a transaction

```bash
curl -X POST http://localhost:7071/api/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-001",
    "customer_id": "CUST-123",
    "amount": 5000.00,
    "merchant_name": "Unknown Electronics",
    "merchant_category_code": "5732"
  }'
```

## Testing

```bash
# Run all tests
cd tests
python -m pytest -v

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Run ML pipeline tests
python -m pytest test_training_pipeline.py -v

# Run scoring function tests
python -m pytest test_scoring_function.py -v
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID for analyst and operator authentication; managed identity for all service-to-service communication
- **Authorization**: Strict RBAC role separation -- data scientists, fraud ops, and auditors have distinct role assignments with least-privilege access
- **Managed Identity**: Zero-secret architecture; system-assigned managed identity for all Azure resources
- **Network Isolation**: Dedicated VNet with NSG rules; Event Hub, ML Workspace, Cosmos DB, and OpenAI accessed via Private Link endpoints; no public endpoints
- **Model Governance**: Signed models with tamper detection, version control in Azure ML registry, and approval gates for production deployment
- **PCI DSS Level 1**: Cardholder data encrypted, tokenized, and masked; no PAN in logs or telemetry

### Encryption

- **Data at Rest**: AES-256 with customer-managed keys (CMK) via Key Vault for all databases, data lake, and model artifacts; transparent data encryption (TDE) on Azure SQL
- **Data in Transit**: TLS 1.2+ enforced across all services including Event Hub streams and ML scoring endpoints
- **Data Masking**: Dynamic data masking for non-privileged users; sensitive fields (PAN, SSN) never stored in plain text
- **Key Management**: Azure Key Vault with CMK for encryption, model signing keys, and certificate management

### Monitoring

- **Application Insights**: Scoring latency (P50, P99), throughput, and error rate tracking in real-time
- **Log Analytics**: Centralized decision logs, model performance drift monitoring, and security event correlation
- **Alerts**: Alerts on scoring latency P99 > 200ms, false positive rate spikes, model drift, and service degradation
- **Azure Sentinel**: Real-time security event correlation for detecting fraudulent access patterns

### Visualization

- **Power BI Dashboards**: Fraud detection metrics -- false positive rate, true positive rate, detection latency, financial impact, and case review backlog
- **Fraud Analyst Dashboard**: Priority-sorted case queue with AI-generated explanations, similar case history, and decision action buttons

### Tracking

- **SOX Audit Trail**: Immutable decision logs for every transaction scored -- includes risk score, rules triggered, ML scores, and final decision
- **Data Lineage**: Azure Purview tracks data lineage from raw transaction ingestion through feature engineering to model scoring
- **Model Registry**: MLflow-based model registry in Azure ML with experiment tracking, version history, and A/B test metadata
- **Correlation IDs**: Transaction-level correlation IDs from Event Hub ingestion through scoring, decision, and analyst review

### Accuracy

- **Ensemble Model**: Weighted combination of Isolation Forest (novel fraud), XGBoost (known patterns), and Neural Network (temporal sequences)
- **Target Metrics**: >95% true positive rate, <0.5% false positive rate, precision optimized at 95% recall
- **Evaluation Pipeline**: AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix, and precision-at-95%-recall tracked per training run
- **Model Drift Detection**: Daily automated performance monitoring with alerts on metric degradation
- **Class Imbalance Handling**: SMOTE oversampling, cost-sensitive learning (scale_pos_weight: 100), and stratified cross-validation

### Explainability

- **SHAP Values**: TreeExplainer computes feature importance for every XGBoost prediction, identifying top contributing factors
- **GenAI Summaries**: GPT-4o generates human-readable case summaries, key concerns (top 3), and recommended actions (top 2) for flagged transactions
- **Feature Importance**: Global and per-prediction feature importance rankings available for model audit
- **Evidence Grounding**: AI explanations are grounded in transaction data, risk score breakdown, and rules triggered

### Responsibility

- **Bias Monitoring**: Continuous ECOA/Fair Lending compliance monitoring -- fraud scoring analyzed across customer demographics to detect disparate impact
- **FinCEN/SAR**: Suspicious Activity Reports auto-generated for transactions exceeding regulatory thresholds
- **Human-in-the-Loop**: REVIEW-range transactions (30-70) routed to fraud analysts with AI explanations before final decision
- **Model Approval Gates**: New model versions require evaluation against fairness metrics and approval before production deployment

### Interpretability

- **Risk Score Decomposition**: Final score (0-100) broken down into ML score, rules adjustment, and individual rule contributions
- **Rules Transparency**: Every triggered rule includes rule ID, description, and score adjustment -- fully auditable
- **Decision Thresholds**: ALLOW/REVIEW/BLOCK thresholds configurable and documented; decision logic is deterministic given the risk score
- **Feature Groups**: Features organized into transparent categories (basic, velocity, behavioral, customer, graph) for interpretability

### Portability

- **Infrastructure as Code**: All Azure resources defined in Terraform with modular environment configuration
- **MLflow Integration**: Model training, metrics, and artifacts tracked in MLflow -- compatible with multi-cloud ML platforms
- **Containerized Scoring**: Real-time scoring function deployable as Docker container or Azure Functions
- **Standard Formats**: Models saved in standard formats (joblib for scikit-learn, JSON for XGBoost) for framework portability
- **Data Lake Architecture**: ADLS Gen2 with Delta Lake format for interoperability with Spark, Databricks, and Synapse

## Project Structure

```
project-5-fraud-detection/
|-- docs/
|   +-- ARCHITECTURE.md             # Detailed architecture documentation
|-- infra/
|   +-- main.tf                     # Terraform infrastructure definitions
|-- src/
|   |-- ml/
|   |   +-- training_pipeline.py    # ML training: feature engineering, Isolation Forest,
|   |                               #   XGBoost, ensemble, SHAP, MLflow tracking
|   +-- realtime/
|       +-- scoring_function.py     # Real-time scoring: feature enrichment, rules engine,
|                                   #   GenAI explainability, HTTP endpoints
|-- tests/
|   |-- (test files)               # Unit and integration tests
+-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/score` | Score a transaction in real-time (returns decision + risk score) |
| `GET` | `/api/health` | Health check -- returns service status |

### POST /api/score

**Request:**
```json
{
  "transaction_id": "TXN-2024-001",
  "customer_id": "CUST-123",
  "amount": 5000.00,
  "currency": "USD",
  "merchant_name": "Unknown Electronics",
  "merchant_category_code": "5732",
  "channel": "online",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

**Response:**
```json
{
  "transaction_id": "TXN-2024-001",
  "decision": "REVIEW",
  "risk_score": 55.0,
  "latency_ms": 45.2
}
```

### ML Training CLI

```bash
python training_pipeline.py \
  --data-path /path/to/transactions.parquet \
  --output-path /path/to/outputs \
  --experiment-name fraud-detection-v2
```

**Metrics Output (metrics.json):**
```json
{
  "auc_roc": 0.987,
  "auc_pr": 0.842,
  "precision": 0.91,
  "recall": 0.95,
  "f1": 0.93,
  "false_positive_rate": 0.004,
  "precision_at_95_recall": 0.88
}
```

## License

This project is licensed under the MIT License.
