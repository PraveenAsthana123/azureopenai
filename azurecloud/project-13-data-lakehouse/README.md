# Enterprise Data Lakehouse with GenAI Insights

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![Synapse Analytics](https://img.shields.io/badge/Synapse%20Analytics-Data%20Warehouse-blue)
![ADLS Gen2](https://img.shields.io/badge/ADLS%20Gen2-Data%20Lake-0078D4)
![Delta Lake](https://img.shields.io/badge/Delta%20Lake-ACID-red)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

A unified data lakehouse platform built on Azure Synapse Analytics with ADLS Gen2, implementing the Medallion architecture (Bronze/Silver/Gold layers) with Delta Lake for ACID transactions and time travel. The platform integrates GenAI capabilities powered by Azure OpenAI GPT-4o to enable natural language analytics, allowing business users to query enterprise data using conversational English that is automatically translated to validated Synapse SQL. Data is ingested from ERP, CRM, IoT, and streaming sources through Azure Data Factory, with governance enforced by Microsoft Purview.

## Architecture

```
Data Sources
  - ERP (SAP/Oracle) --> Parquet
  - CRM (Salesforce)  --> JSON
  - IoT Devices       --> Avro
  - Third-Party APIs  --> REST
  - Streaming Events  --> Kafka / Event Hub
        |
        v
  Azure Data Factory (Orchestration)
  - 100+ connectors, CDC pipelines, schedule triggers
        |
        v
  ADLS Gen2 (Medallion Architecture)
  +-------------------------------+
  | BRONZE (/raw/)                |
  | Raw data as-is, full history  |
  +-------------------------------+
  | SILVER (/silver/)             |
  | Delta Lake: Schema enforce,   |
  | dedup, PII masking, merge     |
  | Tables: customers, orders,    |
  |   products, inventory, events |
  +-------------------------------+
  | GOLD (/gold/)                 |
  | Business-ready aggregations   |
  | Sales Mart | Finance Mart |   |
  | Operations Mart               |
  +-------------------------------+
        |
        v
  Azure Synapse Analytics
  - Spark Pools (ETL, ML)
  - SQL Pools (BI, ad-hoc)
  - Serverless SQL (on-demand)
  - Data Explorer Pool (time series)
        |
        v
  GenAI Analytics Interface
  - NL-to-SQL Pipeline (GPT-4o)
  - Schema context + validation
  - Follow-up suggestions
  - Auto-generated visualizations
        |
        v
  Consumers
  - React Chat UI
  - Power BI (Embedded Copilot)
  - Teams Bot

  Data Governance: Microsoft Purview + Unity Catalog
```

## Azure Services Used

| Service | Layer | Purpose |
|---------|-------|---------|
| Azure Data Factory | Ingestion | Orchestration with 100+ connectors, CDC pipelines |
| Azure Event Hub | Ingestion | Real-time streaming ingestion |
| ADLS Gen2 | Storage | Data lake with hierarchical namespace |
| Delta Lake | Format | ACID transactions, schema enforcement, time travel |
| Azure Synapse Spark Pools | Processing | Big data ETL/ELT transformations |
| Azure Synapse SQL Pools | Processing | Data warehousing and BI queries |
| Azure Synapse Serverless SQL | Processing | On-demand ad-hoc queries |
| Azure OpenAI (GPT-4o) | GenAI | Natural language to SQL translation |
| Microsoft Purview | Governance | Data discovery, classification, lineage |
| Power BI | Analytics | Dashboards, reports, embedded copilot |
| Azure Key Vault | Security | Secrets and key management |
| Azure Databricks | Processing | Advanced ML and Spark workloads (optional) |

## Prerequisites

- Azure Subscription with Contributor access
- Azure OpenAI resource with GPT-4o deployed
- Azure Synapse Analytics workspace
- ADLS Gen2 storage account with hierarchical namespace enabled
- Microsoft Purview account
- Python 3.11+
- Terraform >= 1.5
- Azure CLI >= 2.50
- ODBC Driver 18 for SQL Server

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-13-data-lakehouse

# Set required environment variables
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
export SYNAPSE_WORKSPACE_NAME="<your-synapse-workspace>"
export SYNAPSE_SQL_ENDPOINT="<your-synapse>.sql.azuresynapse.net"
export DATABASE_NAME="gold_layer"
```

### 2. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Run the NL-to-SQL Engine

```python
from src.genai_analytics.nl_to_sql import AnalyticsSession

session = AnalyticsSession(user_id="analyst@company.com")

result = session.ask("Show me top 10 customers by revenue last quarter")
print(result["sql"])
print(result["summary"])
print(result["follow_up_questions"])
```

## Testing

```bash
cd tests

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -v -k "test_nl_to_sql"       # NL-to-SQL translation tests
pytest -v -k "test_schema"          # Schema management tests
pytest -v -k "test_validation"      # SQL validation tests
pytest -v -k "test_session"         # Analytics session tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID with ActiveDirectoryDefault authentication for Synapse SQL connections
- **Authorization**: Workspace-level and data lake ACL-based access control; Column-Level Security for sensitive data
- **RBAC**: Synapse workspace roles for data engineers, scientists, and analysts; ADLS Gen2 ACLs per zone
- **Managed Identity**: Zero-secret architecture; DefaultAzureCredential for all service-to-service authentication
- **Network Isolation**: Dedicated VNet with NSG rules; Synapse, ADLS Gen2, Purview, and OpenAI accessed via Private Link

### Encryption

- **Data at Rest**: AES-256 SSE for ADLS Gen2 storage; Synapse SQL transparent data encryption
- **Data in Transit**: TLS 1.3 enforced for all client and service communications
- **Key Management**: Azure Key Vault for data encryption keys and service credentials

### Monitoring

- **Application Insights**: APM for Synapse pipeline executions and NL-to-SQL engine interactions
- **Log Analytics**: Centralized logging for Spark job diagnostics, SQL pool query metrics, and pipeline run history
- **Alerts**: Azure Monitor alerts for pipeline failures, Spark pool utilization, and SQL pool DTU consumption
- **Dashboards**: Synapse Monitor for pipeline health, Spark job performance, and SQL query profiling

### Visualization

- **Power BI**: Embedded dashboards with copilot integration for executive KPIs; direct query mode from Gold layer
- **React Chat UI**: Conversational analytics interface with NL-to-SQL and auto-generated charts
- **Teams Bot**: Enterprise chat integration for ad-hoc analytics queries

### Tracking

- **Data Lineage**: End-to-end lineage tracking via Microsoft Purview from source to Gold layer consumption
- **Query Audit**: All NL-to-SQL translations logged with user identity, generated SQL, confidence score, and execution results
- **Pipeline Tracking**: Data Factory pipeline runs tracked with start/end times, row counts, and error details
- **Delta Lake Time Travel**: Full versioned history of all data changes for audit and rollback

### Accuracy

- **SQL Validation**: Generated SQL validated for syntax and safety; dangerous keywords (DROP, DELETE, TRUNCATE, ALTER, CREATE, INSERT, UPDATE) blocked
- **Read-Only Enforcement**: Only SELECT and WITH (CTE) queries permitted; write operations rejected at validation layer
- **Confidence Scoring**: Each NL-to-SQL translation includes a confidence score (0.0-1.0) for transparency
- **Data Quality Gates**: Validation rules enforced at Bronze-to-Silver and Silver-to-Gold boundaries

### Explainability

- NL-to-SQL responses include generated SQL, a plain-English explanation, tables used, and confidence score
- Query results are accompanied by a 2-3 sentence natural language summary highlighting key insights
- Follow-up question suggestions guide users toward deeper analytical exploration
- Schema context (table descriptions, column types, sample data) provided to GPT-4o for grounded responses

### Responsibility

- **Content Filtering**: Azure OpenAI content safety for all prompts; SQL injection prevention via validation layer
- **Data Masking**: Dynamic Data Masking on PII/sensitive fields for non-privileged users in the Silver layer
- **Human Oversight**: Generated SQL can be reviewed before execution; conversational context preserves session history
- **Data Minimization**: Purview sensitivity labels classify and restrict access to sensitive datasets

### Interpretability

- Medallion architecture provides clear data provenance: Bronze (raw), Silver (validated), Gold (business-ready)
- Each query result includes column metadata, row count, and the tables referenced
- Schema descriptions provide business context for every table and column
- Conversation history maintained for multi-turn analytical sessions

### Portability

- **Infrastructure as Code**: Full Terraform configuration in `infra/main.tf` for reproducible multi-environment deployments
- **Containerization**: NL-to-SQL engine can be packaged as a Docker container for deployment flexibility
- **Multi-Cloud Considerations**: Core NL-to-SQL logic uses standard pyodbc; adaptable to other SQL engines (Databricks SQL, BigQuery)
- **Delta Lake**: Open format (Parquet-based) for cross-platform compatibility with Databricks, Fabric, and Spark

## Project Structure

```
project-13-data-lakehouse/
|-- docs/
|   |-- ARCHITECTURE.md
|-- infra/
|   |-- main.tf
|-- src/
|   |-- genai_analytics/
|       |-- nl_to_sql.py
|-- tests/
|-- README.md
```

## API Reference

| Class / Method | Description |
|----------------|-------------|
| `NLToSQLEngine.generate_sql(user_query)` | Convert natural language to validated Synapse SQL |
| `NLToSQLEngine.validate_sql(sql)` | Validate SQL syntax and block dangerous operations |
| `NLToSQLEngine.execute_query(sql, max_rows)` | Execute validated SQL against Synapse with row limits |
| `NLToSQLEngine.generate_summary(query, results)` | Generate natural language summary of query results |
| `NLToSQLEngine.suggest_follow_ups(query, sql)` | Suggest follow-up analytical questions |
| `AnalyticsSession.ask(question)` | End-to-end: generate SQL, validate, execute, summarize |
| `AnalyticsSession.get_history()` | Retrieve query history for the session |
| `AnalyticsSession.clear_context()` | Clear conversation context for a fresh start |
| `SchemaManager.get_table_schemas(tables)` | Retrieve database schema metadata for AI context |

## License

This project is licensed under the MIT License.
