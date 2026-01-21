# Azure Enterprise AI/ML Portfolio - Complete Project Index

## Overview

This portfolio contains **10 enterprise-grade Azure projects** demonstrating end-to-end architecture skills across AI, ML, Data Engineering, and Cloud Infrastructure.

---

## Projects At A Glance

| # | Project | Key Technologies | Primary Use Case |
|---|---------|------------------|------------------|
| 1 | [RAG Knowledge Copilot](./project-1-rag-copilot/) | Azure OpenAI, AI Search, Functions | Enterprise document Q&A |
| 2 | [Document Processing](./project-2-document-processing/) | Document Intelligence, Azure ML | Intelligent document classification |
| 3 | [Call Center Copilot](./project-3-call-center-copilot/) | Speech Services, Translator, OpenAI | Multilingual voice/chat AI |
| 4 | [Agentic Platform](./project-4-agentic-platform/) | OpenAI Function Calling, Durable Functions | Multi-step workflow automation |
| 5 | [Fraud Detection](./project-5-fraud-detection/) | Azure ML, Stream Analytics, OpenAI | Real-time fraud scoring + explainability |
| 6 | [Customer 360](./project-6-customer-360/) | Data Factory, Azure ML, Cosmos DB | Unified customer profiles + personalization |
| 9 | [IoT Predictive Maintenance](./project-9-iot-predictive-maintenance/) | IoT Hub, Azure ML, Stream Analytics | Equipment failure prediction |
| 11 | [Legal Contract Analyzer](./project-11-legal-contract-analyzer/) | Document Intelligence, OpenAI, AI Search | Contract clause extraction + risk |
| 13 | [Data Lakehouse](./project-13-data-lakehouse/) | Synapse, ADLS Gen2, Delta Lake | NL-to-SQL analytics |
| 14 | [Multi-Region DR](./project-14-multi-region-dr/) | Traffic Manager, Cosmos DB, Front Door | Disaster recovery for AI platforms |

---

## Detailed Project Summaries

### Project 1: Enterprise RAG Knowledge Copilot
**Directory:** `project-1-rag-copilot/`

Enterprise knowledge assistant enabling natural language Q&A over company documents with citation support.

**Key Features:** Hybrid search, Document ingestion pipeline, Multi-turn conversations

**Azure Services:** Azure OpenAI, AI Search, Document Intelligence, Functions, Cosmos DB, Key Vault, APIM

---

### Project 2: Intelligent Document Processing
**Directory:** `project-2-document-processing/`

Automated document extraction, classification, and routing with human-in-the-loop validation.

**Key Features:** OCR extraction, ML classification, Confidence-based routing, Feedback loop

**Azure Services:** Document Intelligence, Azure ML, Event Grid, Durable Functions, Cosmos DB, Power Apps

---

### Project 3: Automated Call Center Copilot
**Directory:** `project-3-call-center-copilot/`

Multilingual conversational AI for call centers with real-time transcription and intelligent responses.

**Key Features:** 100+ languages, Real-time STT/TTS, Agent assist, Post-call summarization

**Azure Services:** Speech Services, Translator, Azure OpenAI, SignalR, Bot Framework, Cosmos DB

---

### Project 4: GenAI Agentic Automation Platform
**Directory:** `project-4-agentic-platform/`

Multi-agent system executing enterprise workflows through natural language using function calling.

**Key Features:** ReAct pattern, 25+ tools, Human-in-the-loop, Multi-system integration

**Azure Services:** Azure OpenAI (Function Calling), Durable Functions, Logic Apps, APIM, Graph API

---

### Project 5: Financial Fraud Detection Platform
**Directory:** `project-5-fraud-detection/`

Real-time fraud detection with ML ensemble models and GenAI-powered explainability.

**Key Features:** <200ms latency, 96% detection rate, GenAI explanations, Rules engine

**Azure Services:** Azure ML, Event Hub, Stream Analytics, Azure OpenAI, Synapse, Cosmos DB

---

### Project 6: Customer 360 Personalization Engine
**Directory:** `project-6-customer-360/`

Unified customer data platform with identity resolution and AI-powered personalization.

**Key Features:** Identity resolution, RFM scoring, Churn prediction, Recommendation engine

**Azure Services:** Data Factory, Azure ML, Cosmos DB, Azure OpenAI, Event Hub, Power BI

---

### Project 9: IoT Predictive Maintenance
**Directory:** `project-9-iot-predictive-maintenance/`

IoT platform predicting equipment failures using sensor data and ML models.

**Key Features:** Edge processing, RUL prediction, Anomaly detection, GenAI insights

**Azure Services:** IoT Hub, IoT Edge, Event Hub, Stream Analytics, Azure ML, Azure OpenAI

---

### Project 11: Legal Contract Analyzer
**Directory:** `project-11-legal-contract-analyzer/`

AI-powered contract analysis extracting clauses, identifying risks, and comparing versions.

**Key Features:** Clause extraction, Risk scoring, Version comparison, Playbook compliance

**Azure Services:** Document Intelligence, Azure OpenAI, AI Search, Functions, Cosmos DB

---

### Project 13: Enterprise Data Lakehouse
**Directory:** `project-13-data-lakehouse/`

Unified data platform with Medallion architecture and natural language analytics.

**Key Features:** Bronze/Silver/Gold layers, Delta Lake, NL-to-SQL, Data governance

**Azure Services:** Synapse Analytics, ADLS Gen2, Data Factory, Azure OpenAI, Purview

---

### Project 14: Multi-Region Disaster Recovery
**Directory:** `project-14-multi-region-dr/`

Multi-region DR architecture for AI platforms with automated failover and GenAI reporting.

**Key Features:** Active-active Cosmos DB, Geo-replicated AI Search, Automated failover, DR reports

**Azure Services:** Front Door, Traffic Manager, Cosmos DB, RA-GRS Storage, Azure Monitor

---

## Azure Services Master Coverage

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE AZURE SERVICES COVERAGE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  AI/ML Services                          Data Services                           │
│  ├── Azure OpenAI [1,3,4,5,6,9,11,13]   ├── Synapse [5,13]                      │
│  ├── AI Search [1,11]                   ├── ADLS Gen2 [2,5,6,9,13]              │
│  ├── Document Intelligence [1,2,11]      ├── Cosmos DB [1,2,3,4,5,6,11,14]      │
│  ├── Speech Services [3]                ├── Event Hub [5,6,9]                   │
│  ├── Translator [3]                     ├── Data Factory [6,13]                 │
│  └── Azure ML [2,5,6,9]                 └── Redis [4,14]                        │
│                                                                                  │
│  Compute Services                        Integration Services                    │
│  ├── Azure Functions [ALL]              ├── Logic Apps [2,4]                    │
│  ├── Durable Functions [1,2,4]          ├── APIM [1,3,4,11]                     │
│  ├── AKS [2]                            ├── Graph API [4]                       │
│  ├── Stream Analytics [5,9]             └── SignalR [3]                         │
│  └── IoT Hub/Edge [9]                                                            │
│                                                                                  │
│  Security & Identity                     Observability                           │
│  ├── Key Vault [ALL]                    ├── App Insights [ALL]                  │
│  ├── Managed Identity [ALL]             ├── Log Analytics [ALL]                 │
│  ├── Private Link [ALL]                 ├── Azure Monitor [ALL]                 │
│  └── Entra ID [ALL]                     └── Power BI [5,6,9]                    │
│                                                                                  │
│  DR & Global                             IaC                                     │
│  ├── Front Door [14]                    └── Terraform [ALL]                     │
│  ├── Traffic Manager [14]                                                        │
│  └── Geo-Replication [14]                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Deployment

```bash
# Deploy any project
cd project-{N}-{name}/infra
terraform init
terraform apply -var="environment=dev"
```

---

## Interview Resources

See **[INTERVIEW_GUIDE.md](./INTERVIEW_GUIDE.md)** for:
- Resume-ready project descriptions
- Technical deep-dive Q&A
- Architecture talking points
- Portfolio roadmap

---

## Cost Estimation (Dev Environment)

| Project | Monthly Cost (USD) |
|---------|-------------------|
| Projects with OpenAI + Compute | $400-1,000 each |
| Projects with ML Training | $600-1,500 each |
| DR Infrastructure | $800-2,000 |
| **Full Portfolio** | **$5,000-10,000** |

*Production: 3-5x higher depending on scale*
