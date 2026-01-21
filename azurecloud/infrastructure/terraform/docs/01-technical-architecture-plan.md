# Technical Architecture Plan
## Enterprise GenAI Knowledge Copilot Platform

**Version:** 1.0
**Date:** November 2025
**Status:** Deployed (Japan East)

---

## 1. Executive Summary

The GenAI Knowledge Copilot Platform is an enterprise-grade, serverless AI solution built on Azure's cognitive services. It provides intelligent document processing, multi-modal content analysis, and searchable knowledge management capabilities.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTERNET / USERS                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AZURE BASTION (Secure Access)                        │
│                         bastion-genai-copilot-dev                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              VIRTUAL NETWORK                                 │
│                          vnet-genai-copilot-dev-jpe                          │
│                            Address Space: 10.0.0.0/16                        │
│  ┌──────────────────┬──────────────────┬──────────────────┬───────────────┐ │
│  │   Bastion Subnet │    VM Subnet     │  Functions Subnet│  PE Subnet    │ │
│  │   10.0.0.0/26    │   10.0.2.0/24    │   10.0.3.0/24    │  10.0.1.0/24  │ │
│  └──────────────────┴──────────────────┴──────────────────┴───────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐
│   COMPUTE       │    │   DATA LAYER    │    │      AI SERVICES            │
│                 │    │                 │    │                             │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────────────────┐ │
│ │  Linux VM   │ │    │ │  Cosmos DB  │ │    │ │   Document Intelligence │ │
│ │ Standard_D2s│ │    │ │  Serverless │ │    │ │   (Form Recognizer)     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────────────────┘ │
│                 │    │                 │    │                             │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────────────────┐ │
│ │  Functions  │ │    │ │   Storage   │ │    │ │    Computer Vision      │ │
│ │  (Disabled) │ │    │ │   Account   │ │    │ │    (Image Analysis)     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────────────────┘ │
└─────────────────┘    └─────────────────┘    │                             │
                                              │ ┌─────────────────────────┐ │
                                              │ │    Speech Services      │ │
                                              │ │   (Audio Processing)    │ │
                                              │ └─────────────────────────┘ │
                                              │                             │
                                              │ ┌─────────────────────────┐ │
                                              │ │      AI Search          │ │
                                              │ │   (Full-text + Vector)  │ │
                                              │ └─────────────────────────┘ │
                                              │                             │
                                              │ ┌─────────────────────────┐ │
                                              │ │    Azure OpenAI         │ │
                                              │ │   (Disabled - Quota)    │ │
                                              │ └─────────────────────────┘ │
                                              └─────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING & SECURITY                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  Log Analytics  │  │ App Insights    │  │      Key Vault              │  │
│  │   Workspace     │  │   (Telemetry)   │  │   (Secrets Management)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Inventory

| Component | Resource Name | SKU/Tier | Status |
|-----------|---------------|----------|--------|
| Resource Group | rg-genai-copilot-dev-jpe | - | Active |
| Virtual Network | vnet-genai-copilot-dev-jpe | - | Active |
| Linux VM | vm-genai-copilot-0 | Standard_D2s_v3 | Running |
| Bastion | bastion-genai-copilot-dev | Standard | Running |
| AI Search | search-genai-copilot-dev-rwc3az | Standard | Running |
| Document Intelligence | di-genai-copilot-dev-rwc3az | S0 | Running |
| Computer Vision | cv-genai-copilot-dev-rwc3az | S1 | Running |
| Speech Services | speech-genai-copilot-dev-rwc3az | S0 | Running |
| Cosmos DB | cosmos-genai-copilot-dev-rwc3az | Serverless | Running |
| Storage Account | stgenaicopilotdevrwc3az | Standard LRS | Active |
| Key Vault | kv-genai-copilot-rwc3az | Standard | Active |
| Log Analytics | log-genai-copilot-dev-rwc3az | PerGB2018 | Active |
| Application Insights | appi-genai-copilot-dev-rwc3az | - | Active |

---

## 3. Data Flow Architecture

### 3.1 Document Processing Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Upload     │────▶│   Storage    │────▶│   Document   │────▶│   Cosmos DB  │
│   Document   │     │    Blob      │     │ Intelligence │     │  (Metadata)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  AI Search   │
                                         │   (Index)    │
                                         └──────────────┘
```

### 3.2 Image Analysis Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Upload     │────▶│   Storage    │────▶│   Computer   │────▶│   Cosmos DB  │
│    Image     │     │    Blob      │     │   Vision     │     │  (Results)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  AI Search   │
                                         │ (Tags/Text)  │
                                         └──────────────┘
```

### 3.3 Audio Processing Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Upload     │────▶│   Storage    │────▶│   Speech     │────▶│   Cosmos DB  │
│    Audio     │     │    Blob      │     │  Services    │     │ (Transcript) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  AI Search   │
                                         │   (Index)    │
                                         └──────────────┘
```

---

## 4. Network Architecture

### 4.1 Subnet Design

| Subnet Name | CIDR | Purpose | NSG |
|-------------|------|---------|-----|
| AzureBastionSubnet | 10.0.0.0/26 | Azure Bastion access | Built-in |
| snet-privateendpoints | 10.0.1.0/24 | Private endpoints for PaaS | Restricted |
| snet-vm | 10.0.2.0/24 | Virtual machines | Application |
| snet-functions | 10.0.3.0/24 | Azure Functions (future) | Serverless |

### 4.2 Private Endpoints

All PaaS services are secured with Private Endpoints:

| Service | Private Endpoint | DNS Zone |
|---------|-----------------|----------|
| Document Intelligence | pe-di-rwc3az | privatelink.cognitiveservices.azure.com |
| Computer Vision | pe-cv-rwc3az | privatelink.cognitiveservices.azure.com |
| AI Search | pe-search-rwc3az | privatelink.search.windows.net |
| Cosmos DB | pe-cosmos-rwc3az | privatelink.documents.azure.com |
| Storage | pe-storage-rwc3az | privatelink.blob.core.windows.net |
| Key Vault | pe-kv-rwc3az | privatelink.vaultcore.azure.net |

---

## 5. Service Capabilities Matrix

| Service | Capability | Throughput | Limits |
|---------|-----------|------------|--------|
| Document Intelligence | Text extraction, OCR, Table extraction | 15 TPS | 500 pages/min |
| Computer Vision | Image analysis, OCR, Object detection | 20 TPS | 10 MB/image |
| Speech Services | STT, TTS, Translation | Real-time | 10 hours/month |
| AI Search | Full-text, Semantic, Vector search | 50 QPS | 15M docs |
| Cosmos DB | NoSQL document storage | Serverless autoscale | 5000 RU/s burst |

---

## 6. Future Architecture (With Azure OpenAI)

When Azure OpenAI quota is approved:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   User       │────▶│   OpenAI     │────▶│   Response   │
│   Query      │     │   gpt-4o-mini│     │  Generation  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │
       │                    ▼
       │            ┌──────────────┐
       │            │  Embeddings  │
       │            │text-embed-3  │
       │            └──────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  AI Search   │◀────│   Vector     │
│  (RAG Query) │     │   Index      │
└──────────────┘     └──────────────┘
```

---

## 7. Technology Stack

| Layer | Technology |
|-------|------------|
| Infrastructure as Code | Terraform >= 1.5.0 |
| Cloud Platform | Microsoft Azure |
| Compute | Azure VMs (Linux Ubuntu) |
| Serverless | Azure Functions (Y1 - Future) |
| AI/ML | Azure Cognitive Services |
| Search | Azure AI Search |
| Database | Azure Cosmos DB (Serverless) |
| Storage | Azure Blob Storage |
| Security | Azure Key Vault, Private Endpoints |
| Monitoring | Azure Monitor, Application Insights |
| Networking | Azure VNet, Bastion, NSGs |

---

## 8. Endpoints Reference

| Service | Endpoint |
|---------|----------|
| Document Intelligence | https://di-genai-copilot-dev-rwc3az.cognitiveservices.azure.com/ |
| Computer Vision | https://cv-genai-copilot-dev-rwc3az.cognitiveservices.azure.com/ |
| Speech Services | https://speech-genai-copilot-dev-rwc3az.cognitiveservices.azure.com/ |
| Cosmos DB | https://cosmos-genai-copilot-dev-rwc3az.documents.azure.com:443/ |
| Key Vault | https://kv-genai-copilot-rwc3az.vault.azure.net/ |
| Storage | https://stgenaicopilotdevrwc3az.blob.core.windows.net/ |

---

## 9. Appendix

### 9.1 Resource Naming Convention

```
{resource-type}-{project-name}-{environment}-{suffix}

Examples:
- rg-genai-copilot-dev-jpe (Resource Group)
- vnet-genai-copilot-dev-jpe (Virtual Network)
- di-genai-copilot-dev-rwc3az (Document Intelligence)
```

### 9.2 Tags Applied

| Tag | Value |
|-----|-------|
| Environment | dev |
| Project | GenAI-Copilot |
| ManagedBy | Terraform |
| Owner | pasthana@outlook.com |
| CostCenter | AI-Platform |
