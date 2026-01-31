# Project 13: Enterprise Data Lakehouse with GenAI Insights

## Executive Summary

A unified data lakehouse platform built on Azure Synapse Analytics with ADLS Gen2, implementing the Medallion architecture (Bronze/Silver/Gold layers). The platform integrates GenAI capabilities to enable natural language analytics, allowing business users to query data using conversational English that's automatically translated to SQL.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE DATA LAKEHOUSE WITH GENAI                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                            │
│                                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐ │
│  │ ERP System │ │ CRM System │ │ IoT Devices│ │ Third-Party│ │ Streaming Events   │ │
│  │ (SAP/Oracle)│ │(Salesforce)│ │ (Sensors)  │ │ APIs       │ │ (Kafka/Event Hub)  │ │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────────┬──────────┘ │
│        │              │              │              │                  │            │
└────────┼──────────────┼──────────────┼──────────────┼──────────────────┼────────────┘
         │              │              │              │                  │
         └──────────────┴──────────────┴──────────────┴──────────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │     Azure Data Factory      │
                        │     (Orchestration)         │
                        │                             │
                        │  - 100+ connectors          │
                        │  - CDC pipelines            │
                        │  - Schedule triggers        │
                        │  - Data flow transformations│
                        └──────────────┬──────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    AZURE DATA LAKE STORAGE GEN2                                      │
│                    (MEDALLION ARCHITECTURE)                                          │
│                                       │                                              │
│  ┌────────────────────────────────────┼────────────────────────────────────────┐    │
│  │                                    ▼                                        │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │    │
│  │  │                      BRONZE LAYER (Raw)                              │   │    │
│  │  │                      /raw/                                           │   │    │
│  │  │                                                                      │   │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │   │    │
│  │  │  │ /erp/    │  │ /crm/    │  │ /iot/    │  │ /streaming/          │ │   │    │
│  │  │  │          │  │          │  │          │  │                      │ │   │    │
│  │  │  │ - Parquet│  │ - JSON   │  │ - Avro   │  │ - Delta streaming    │ │   │    │
│  │  │  │ - As-is  │  │ - Raw    │  │ - Raw    │  │ - Append-only        │ │   │    │
│  │  │  │ - Full   │  │ - Full   │  │ - Micro- │  │ - Checkpointing      │ │   │    │
│  │  │  │   history│  │   history│  │   batch  │  │                      │ │   │    │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │   │    │
│  │  └─────────────────────────────────┬───────────────────────────────────┘   │    │
│  │                                    │                                        │    │
│  │                                    ▼                                        │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │    │
│  │  │                      SILVER LAYER (Cleansed)                         │   │    │
│  │  │                      /silver/                                        │   │    │
│  │  │                                                                      │   │    │
│  │  │  ┌──────────────────────────────────────────────────────────────┐   │   │    │
│  │  │  │ Delta Lake Tables                                            │   │   │    │
│  │  │  │                                                              │   │   │    │
│  │  │  │ - Schema enforcement          - Deduplication                │   │   │    │
│  │  │  │ - Data type standardization   - Null handling                │   │   │    │
│  │  │  │ - PII masking                 - Referential integrity        │   │   │    │
│  │  │  │ - Time travel enabled         - Merge/Upsert operations      │   │   │    │
│  │  │  │                                                              │   │   │    │
│  │  │  │ Tables:                                                      │   │   │    │
│  │  │  │ - customers       - products       - transactions            │   │   │    │
│  │  │  │ - orders          - inventory      - events                  │   │   │    │
│  │  │  └──────────────────────────────────────────────────────────────┘   │   │    │
│  │  └─────────────────────────────────┬───────────────────────────────────┘   │    │
│  │                                    │                                        │    │
│  │                                    ▼                                        │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │    │
│  │  │                      GOLD LAYER (Curated)                            │   │    │
│  │  │                      /gold/                                          │   │    │
│  │  │                                                                      │   │    │
│  │  │  ┌──────────────────────────────────────────────────────────────┐   │   │    │
│  │  │  │ Business-Ready Aggregations & Data Marts                     │   │   │    │
│  │  │  │                                                              │   │   │    │
│  │  │  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │   │   │    │
│  │  │  │ │ Sales Mart   │ │ Finance Mart │ │ Operations Mart      │  │   │   │    │
│  │  │  │ │              │ │              │ │                      │  │   │   │    │
│  │  │  │ │ - Daily sales│ │ - Revenue    │ │ - Inventory levels   │  │   │   │    │
│  │  │  │ │ - Customer   │ │ - Costs      │ │ - Supply chain       │  │   │   │    │
│  │  │  │ │   segments   │ │ - Margins    │ │ - Fulfillment        │  │   │   │    │
│  │  │  │ │ - Product    │ │ - Forecasts  │ │ - Quality metrics    │  │   │   │    │
│  │  │  │ │   performance│ │              │ │                      │  │   │   │    │
│  │  │  │ └──────────────┘ └──────────────┘ └──────────────────────┘  │   │   │    │
│  │  │  └──────────────────────────────────────────────────────────────┘   │   │    │
│  │  └─────────────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE SYNAPSE ANALYTICS                                       │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                              │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │    │
│  │  │ Spark Pools      │  │ SQL Pools        │  │ Data Explorer Pool         │ │    │
│  │  │ (Big Data)       │  │ (Dedicated DW)   │  │ (Time Series)              │ │    │
│  │  │                  │  │                  │  │                            │ │    │
│  │  │ - ETL/ELT        │  │ - BI Reporting   │  │ - Log Analytics            │ │    │
│  │  │ - ML Training    │  │ - Ad-hoc queries │  │ - IoT Analytics            │ │    │
│  │  │ - Delta Lake ops │  │ - Dashboards     │  │ - Real-time queries        │ │    │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │    │
│  │                                                                              │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │    │
│  │  │ Serverless SQL   │  │ Pipelines        │  │ Link (Cosmos DB, etc.)     │ │    │
│  │  │ (On-demand)      │  │ (Orchestration)  │  │ (Live connections)         │ │    │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        GENAI ANALYTICS INTERFACE                                     │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Natural Language to SQL Pipeline                         │    │
│  │                                                                              │    │
│  │     User Query                                                               │    │
│  │     "Show me top 10 customers by revenue last quarter"                       │    │
│  │              │                                                               │    │
│  │              ▼                                                               │    │
│  │     ┌─────────────────────────────────────────────────────────────────┐     │    │
│  │     │              Schema Understanding                                │     │    │
│  │     │                                                                  │     │    │
│  │     │  - Table schemas from Unity Catalog / Synapse metadata           │     │    │
│  │     │  - Column descriptions                                           │     │    │
│  │     │  - Sample data                                                   │     │    │
│  │     │  - Relationship mappings                                         │     │    │
│  │     └─────────────────────────┬───────────────────────────────────────┘     │    │
│  │                               │                                              │    │
│  │                               ▼                                              │    │
│  │     ┌─────────────────────────────────────────────────────────────────┐     │    │
│  │     │              Azure OpenAI GPT-4o                                 │     │    │
│  │     │                                                                  │     │    │
│  │     │  System Prompt:                                                  │     │    │
│  │     │  "You are a SQL expert. Given the schema below, generate        │     │    │
│  │     │   valid Synapse SQL for the user's question..."                  │     │    │
│  │     │                                                                  │     │    │
│  │     │  Output: SQL Query                                               │     │    │
│  │     └─────────────────────────┬───────────────────────────────────────┘     │    │
│  │                               │                                              │    │
│  │                               ▼                                              │    │
│  │     ┌─────────────────────────────────────────────────────────────────┐     │    │
│  │     │              Query Validation & Execution                        │     │    │
│  │     │                                                                  │     │    │
│  │     │  - Syntax validation                                             │     │    │
│  │     │  - Permission check                                              │     │    │
│  │     │  - Cost estimation                                               │     │    │
│  │     │  - Execute on Synapse SQL                                        │     │    │
│  │     └─────────────────────────┬───────────────────────────────────────┘     │    │
│  │                               │                                              │    │
│  │                               ▼                                              │    │
│  │     ┌─────────────────────────────────────────────────────────────────┐     │    │
│  │     │              Response Generation                                 │     │    │
│  │     │                                                                  │     │    │
│  │     │  - Natural language summary of results                           │     │    │
│  │     │  - Auto-generated visualizations                                 │     │    │
│  │     │  - Follow-up question suggestions                                │     │    │
│  │     └─────────────────────────────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────┐     │
│  │ Conversational Chat UI │  │ Power BI Integration   │  │ Teams Bot          │     │
│  │ (React Web App)        │  │ (Embedded Copilot)     │  │ (Enterprise Chat)  │     │
│  └────────────────────────┘  └────────────────────────┘  └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        DATA GOVERNANCE & SECURITY                                    │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │ Microsoft Purview│  │ Unity Catalog    │  │ Column-Level     │  │ Data Lineage│  │
│  │ (Data Catalog)   │  │ (Synapse)        │  │ Security         │  │ Tracking    │  │
│  │                  │  │                  │  │                  │  │             │  │
│  │ - Auto-discovery│  │ - Access control │  │ - Dynamic masking│  │ - End-to-end│  │
│  │ - Classification│  │ - Audit logs     │  │ - Row filtering  │  │ - Impact    │  │
│  │ - Sensitivity   │  │ - Versioning     │  │ - Encryption     │  │   analysis  │  │
│  │   labels        │  │                  │  │                  │  │             │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ETL/ELT PIPELINE ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

     ┌───────────────────────────────────────────────────────────────────────────┐
     │                    DATA FACTORY ORCHESTRATION                              │
     │                                                                            │
     │    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              │
     │    │ Trigger │───►│ Ingest  │───►│Transform│───►│  Load   │              │
     │    │ (Sched/ │    │ (Copy   │    │ (Spark/ │    │ (Delta  │              │
     │    │  Event) │    │  Data)  │    │ SQL)    │    │  Merge) │              │
     │    └─────────┘    └─────────┘    └─────────┘    └─────────┘              │
     │                                                                            │
     └───────────────────────────────────────────────────────────────────────────┘

                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │   BATCH ETL   │  │  STREAMING    │  │   CDC         │
           │   (Daily)     │  │  (Real-time)  │  │   (Near-RT)   │
           │               │  │               │  │               │
           │ - Full load   │  │ - Event Hub   │  │ - Debezium    │
           │ - Incremental │  │ - Structured  │  │ - Kafka       │
           │ - Watermark   │  │   Streaming   │  │ - Change feed │
           └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      │
                                      ▼
                   ┌───────────────────────────────────────┐
                   │         SPARK PROCESSING              │
                   │                                       │
                   │  Bronze → Silver Transformation:      │
                   │  - Schema validation                  │
                   │  - Data quality checks                │
                   │  - Deduplication                      │
                   │  - Type casting                       │
                   │                                       │
                   │  Silver → Gold Transformation:        │
                   │  - Business aggregations              │
                   │  - Denormalization                    │
                   │  - KPI calculations                   │
                   │  - Dimension modeling                 │
                   └───────────────────────────────────────┘
```

---

## Azure Services Mapping

| Layer | Service | Purpose |
|-------|---------|---------|
| **Ingestion** | Data Factory | Orchestration, 100+ connectors |
| **Ingestion** | Event Hub | Real-time streaming |
| **Storage** | ADLS Gen2 | Data lake with hierarchical namespace |
| **Processing** | Synapse Spark | Big data transformations |
| **Processing** | Synapse SQL | Data warehousing, BI queries |
| **Format** | Delta Lake | ACID transactions, time travel |
| **GenAI** | Azure OpenAI | Natural language to SQL |
| **Catalog** | Purview | Data discovery, lineage |
| **Analytics** | Power BI | Dashboards, reports |
| **Security** | Key Vault | Secrets management |
| **Governance** | Purview + AAD | Access control, audit |

---

## Key Features

### 1. Medallion Architecture Benefits
- **Bronze**: Raw data preservation, full audit trail
- **Silver**: Cleaned, validated, enterprise-ready data
- **Gold**: Business-specific aggregations, fast queries

### 2. Delta Lake Capabilities
- ACID transactions on data lake
- Schema enforcement and evolution
- Time travel for point-in-time queries
- Efficient upserts (MERGE operations)

### 3. GenAI Analytics
- Natural language queries for non-technical users
- Auto-generated SQL with validation
- Conversational follow-up questions
- Visualization suggestions

---

## Interview Talking Points

### Architecture Decisions

1. **Why Medallion Architecture?**
   - Clear separation of concerns
   - Enables incremental processing
   - Supports data quality at each layer
   - Allows schema evolution without breaking downstream

2. **Why Delta Lake over Parquet?**
   - ACID transactions prevent data corruption
   - Time travel for debugging/compliance
   - Efficient MERGE for CDC workloads
   - Schema enforcement prevents bad data

3. **Why GenAI for Analytics?**
   - Democratizes data access for business users
   - Reduces dependency on data analysts
   - Natural language is more intuitive
   - Can handle complex analytical questions

4. **Synapse vs Databricks?**
   - Synapse: Tighter Azure integration, unified experience
   - Databricks: More advanced ML, better Spark ecosystem
   - Choice depends on existing Azure investment

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Internal Data Platform)
- **Visibility:** Internal (Data Team) — data engineers, data scientists, and analytics teams
- **Project Score:** 8.0 / 10 (Elevated)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | Synapse, ADLS Gen2, Purview, OpenAI via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC + ACL | Workspace and data lake ACL-based access control |
| Data | Column-Level Security | Sensitive columns restricted by data classification |
| Data | Dynamic Data Masking | PII/sensitive fields masked for non-privileged users |
| Data | Encryption | AES-256 at rest (ADLS), TLS 1.3 in transit |
| Data | Key Vault | Data encryption keys, service credentials |
| Application | Purview Integration | Automated data discovery and classification |
| Application | Data Quality Gates | Validation rules enforced at ingestion boundaries |
| Monitoring | Data Lineage | End-to-end lineage tracking via Purview |
| Monitoring | Access Audit | All data access and transformation operations logged |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Purview Data Catalog | Enforced | All datasets registered, classified, and documented |
| Data Lineage | Tracked | End-to-end lineage from source to consumption |
| Zone Governance | Defined | Raw/Curated/Consumption zones with promotion policies |
| Data Quality | Monitored | Quality scores tracked per dataset with SLA thresholds |
| Schema Governance | Versioned | Schema evolution policies with backward compatibility |
| Data Lifecycle | Managed | Retention, archival, and purge policies per classification |

### Regulatory Applicability
- **GDPR Article 30:** Records of processing activities via data catalog
- **CCPA:** Consumer data inventory and deletion capabilities
- **SOX:** Financial data integrity and audit trail in lakehouse
- **Industry-Specific:** Sector-specific data handling requirements
- **ISO 27001:** Information security for data platform assets
