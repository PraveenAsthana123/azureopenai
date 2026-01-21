# High-Level Design (HLD) Document
# Enterprise GenAI Knowledge Copilot Platform

**Document Version:** 1.0
**Date:** November 2024
**Status:** Approved

---

## 1. Document Overview

### 1.1 Purpose
This High-Level Design document provides an architectural overview of the Enterprise GenAI Knowledge Copilot Platform, describing the system components, their interactions, data flows, and deployment architecture.

### 1.2 Scope
This document covers:
- System architecture overview
- Component descriptions
- Integration patterns
- Security architecture
- Deployment topology
- Technology stack decisions

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         ENTERPRISE GENAI COPILOT PLATFORM                         │
│                              HIGH-LEVEL ARCHITECTURE                              │
└──────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │   USERS     │
                                    │ (Corporate) │
                                    └──────┬──────┘
                                           │
                                           │ HTTPS
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         React Frontend (SPA)                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │ Chat UI      │  │ Search UI    │  │ Document Mgmt│  │ Admin Panel │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                             │
│                         Hosted on Azure VMs / Azure Static Web Apps             │
└──────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ REST API / WebSocket
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                 API LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    Azure Functions (Serverless)                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │ API Gateway  │  │ Orchestrator │  │ Ingestion    │  │RAG Processor│ │    │
│  │  │ (Y1 Consump.)│  │ (EP1 Premium)│  │ (Y1 Consump.)│  │(EP1 Premium)│ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                             │
│                         VNet Integrated / Private Endpoints                      │
└──────────────────────────────────────────────────────────────────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│      AI SERVICES        │  │     DATA SERVICES       │  │    SUPPORT SERVICES     │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │ Azure OpenAI      │  │  │  │ Azure AI Search   │  │  │  │ Key Vault         │  │
│  │ • GPT-4o-mini     │  │  │  │ • Vector Index    │  │  │  │ • Secrets Mgmt    │  │
│  │ • text-embedding  │  │  │  │ • Hybrid Search   │  │  │  └───────────────────┘  │
│  │   -3-small        │  │  │  └───────────────────┘  │  │  ┌───────────────────┐  │
│  └───────────────────┘  │  │  ┌───────────────────┐  │  │  │ App Insights      │  │
│  ┌───────────────────┐  │  │  │ Cosmos DB         │  │  │  │ • Monitoring      │  │
│  │ Document Intel.   │  │  │  │ • Conversations   │  │  │  │ • Logging         │  │
│  │ • OCR             │  │  │  │ • Metadata        │  │  │  └───────────────────┘  │
│  │ • Form Extraction │  │  │  │ • User Sessions   │  │  │  ┌───────────────────┐  │
│  └───────────────────┘  │  │  └───────────────────┘  │  │  │ Azure Bastion     │  │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │  │  │ • Secure Access   │  │
│  │ Computer Vision   │  │  │  │ Blob Storage      │  │  │  └───────────────────┘  │
│  │ • Image Analysis  │  │  │  │ • Documents       │  │  └─────────────────────────┘
│  └───────────────────┘  │  │  │ • Embeddings      │  │
│  ┌───────────────────┐  │  │  └───────────────────┘  │
│  │ Content Safety    │  │  └─────────────────────────┘
│  │ • Moderation      │  │
│  └───────────────────┘  │
└─────────────────────────┘

                    ALL SERVICES CONNECTED VIA PRIVATE ENDPOINTS
                              WITHIN AZURE VIRTUAL NETWORK
```

### 2.2 Architecture Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Security First** | All data and services protected | Private endpoints, no public access |
| **Serverless Priority** | Minimize infrastructure management | Azure Functions, Cosmos DB serverless |
| **Scalability** | Handle variable workloads | Auto-scaling, consumption plans |
| **Cost Optimization** | Pay for what you use | Serverless SKUs, right-sizing |
| **Observability** | Full visibility into system | App Insights, Log Analytics |
| **Modularity** | Loosely coupled components | Microservices, event-driven |

---

## 3. Component Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            COMPONENT ARCHITECTURE                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND COMPONENTS                                 │
│                                                                                 │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐                │
│  │  Chat Module   │    │ Search Module  │    │ Document Mgmt  │                │
│  │  ────────────  │    │  ────────────  │    │  ────────────  │                │
│  │ • Chat UI      │    │ • Search Bar   │    │ • Upload UI    │                │
│  │ • History      │    │ • Filters      │    │ • List View    │                │
│  │ • Citations    │    │ • Results      │    │ • Processing   │                │
│  └───────┬────────┘    └───────┬────────┘    └───────┬────────┘                │
│          │                     │                     │                          │
│          └─────────────────────┴─────────────────────┘                          │
│                                │                                                │
│                    ┌───────────┴───────────┐                                   │
│                    │    State Management    │                                   │
│                    │    (React Context)     │                                   │
│                    └───────────┬───────────┘                                   │
│                                │                                                │
│                    ┌───────────┴───────────┐                                   │
│                    │     API Client         │                                   │
│                    │   (Axios/Fetch)        │                                   │
│                    └───────────┬───────────┘                                   │
└────────────────────────────────┼────────────────────────────────────────────────┘
                                 │
                                 │ HTTPS/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND COMPONENTS                                  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         API Gateway Function                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │   │
│  │  │ /api/chat    │  │ /api/search  │  │ /api/docs    │                   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   │   │
│  │  • Authentication    • Rate Limiting    • Request Validation            │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                               │
│           ┌─────────────────────┼─────────────────────┐                        │
│           ▼                     ▼                     ▼                        │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐               │
│  │  Orchestrator   │    │  Ingestion     │    │  RAG Processor │               │
│  │  ────────────── │    │  ────────────  │    │  ────────────  │               │
│  │ • Workflow Mgmt │    │ • File Parser  │    │ • Query Build  │               │
│  │ • Context Build │    │ • OCR Process  │    │ • Search Exec  │               │
│  │ • Response Agg  │    │ • Chunking     │    │ • LLM Call     │               │
│  └───────┬────────┘    └───────┬────────┘    └───────┬────────┘               │
│          │                     │                     │                         │
│          └─────────────────────┴─────────────────────┘                         │
│                                │                                               │
└────────────────────────────────┼───────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE COMPONENTS                                  │
│                                                                                 │
│    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│    │   AI Services    │    │   Data Services  │    │ Security Services│        │
│    │   ────────────   │    │   ────────────   │    │   ────────────   │        │
│    │ • Azure OpenAI   │    │ • AI Search      │    │ • Key Vault      │        │
│    │ • Doc Intel.     │    │ • Cosmos DB      │    │ • Azure AD       │        │
│    │ • Content Safety │    │ • Blob Storage   │    │ • Managed Id     │        │
│    └──────────────────┘    └──────────────────┘    └──────────────────┘        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Chat Module** | User interaction for Q&A | React, TypeScript |
| **Search Module** | Document search interface | React, TypeScript |
| **API Gateway** | Request routing, auth, rate limiting | Azure Functions (Python) |
| **Orchestrator** | Workflow management | Azure Functions (Python) |
| **Ingestion** | Document processing pipeline | Azure Functions (Python) |
| **RAG Processor** | AI query processing | Azure Functions (Python) |

---

## 4. Data Flow Architecture

### 4.1 Query Processing Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           QUERY PROCESSING DATA FLOW                              │
└──────────────────────────────────────────────────────────────────────────────────┘

  Step 1          Step 2          Step 3          Step 4          Step 5
  ───────         ───────         ───────         ───────         ───────

┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  User   │    │   API   │    │  Query  │    │ Hybrid  │    │  RAG    │
│  Query  │───▶│ Gateway │───▶│ Embed   │───▶│ Search  │───▶│ Context │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │
     │         Validates      Generates       Searches       Builds
     │         & Routes       Vector         Vector +       Context
     │                                       Keyword        Window
     │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼

┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│Response │◀───│ Format  │◀───│  LLM    │◀───│ Prompt  │◀───│Retrieved│
│   UI    │    │ Output  │    │ Generate│    │ Builder │    │ Chunks  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │
     │         Formats         GPT-4o       Constructs    Top-K
     │         Citations       Response     System +      Relevant
     │         & Sources                    User Prompt   Chunks
     │              │              │              │              │

  Step 10         Step 9          Step 8          Step 7          Step 6
  ───────         ───────         ───────         ───────         ───────
```

### 4.2 Document Ingestion Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT INGESTION DATA FLOW                              │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   Upload    │
│  Document   │
└──────┬──────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Blob      │────▶│  Ingestion   │────▶│   Document   │
│   Storage    │     │   Function   │     │ Intelligence │
│  (Raw Docs)  │     │  (Trigger)   │     │    (OCR)     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │   Chunking   │◀────│  Extracted   │
                     │   Service    │     │    Text      │
                     └──────┬───────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Embedding   │
                     │  Generation  │
                     │  (OpenAI)    │
                     └──────┬───────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  AI Search   │ │  Cosmos DB   │ │    Blob      │
    │   Index      │ │  Metadata    │ │  Embeddings  │
    └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 5. Integration Architecture

### 5.1 External Integrations

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          INTEGRATION ARCHITECTURE                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AZURE SERVICES                                      │
│                                                                                 │
│    ┌───────────────────────────────────────────────────────────────────────┐   │
│    │                         IDENTITY & ACCESS                              │   │
│    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │   │
│    │  │  Azure AD    │────│  Managed     │────│    RBAC      │            │   │
│    │  │  (Entra ID)  │    │  Identities  │    │              │            │   │
│    │  └──────────────┘    └──────────────┘    └──────────────┘            │   │
│    └───────────────────────────────────────────────────────────────────────┘   │
│                                    │                                            │
│                                    │ OAuth 2.0 / OIDC                          │
│                                    ▼                                            │
│    ┌───────────────────────────────────────────────────────────────────────┐   │
│    │                         APPLICATION LAYER                              │   │
│    │                                                                        │   │
│    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │   │
│    │  │  Functions   │◀──▶│  Key Vault   │◀──▶│  App Config  │            │   │
│    │  │              │    │  (Secrets)   │    │  (Settings)  │            │   │
│    │  └──────────────┘    └──────────────┘    └──────────────┘            │   │
│    │         │                   │                   │                     │   │
│    │         └───────────────────┴───────────────────┘                     │   │
│    │                            │                                          │   │
│    └────────────────────────────┼──────────────────────────────────────────┘   │
│                                 │                                               │
│                    Private Endpoints                                            │
│                                 │                                               │
│    ┌────────────────────────────┼──────────────────────────────────────────┐   │
│    │                         DATA LAYER                                     │   │
│    │                            │                                           │   │
│    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │   │
│    │  │  Azure       │◀──▶│  Cosmos DB   │◀──▶│    Blob      │            │   │
│    │  │  AI Search   │    │              │    │   Storage    │            │   │
│    │  └──────────────┘    └──────────────┘    └──────────────┘            │   │
│    │                                                                        │   │
│    └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 API Contracts

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/chat` | POST | Submit question, get AI response | Bearer Token |
| `/api/search` | GET | Search documents | Bearer Token |
| `/api/documents` | POST | Upload document | Bearer Token |
| `/api/documents/{id}` | GET | Get document details | Bearer Token |
| `/api/conversations` | GET | Get conversation history | Bearer Token |
| `/api/health` | GET | Health check | None |

---

## 6. Security Architecture

### 6.1 Security Layers

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY ARCHITECTURE                                   │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: PERIMETER SECURITY                                                    │
│  ═══════════════════════════                                                    │
│  • Azure DDoS Protection                                                        │
│  • Web Application Firewall (WAF)                                               │
│  • Azure Front Door (optional)                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: NETWORK SECURITY                                                      │
│  ═════════════════════════                                                      │
│  • Virtual Network (VNet) isolation                                             │
│  • Private Endpoints (no public IPs)                                            │
│  • Network Security Groups (NSG)                                                │
│  • Azure Bastion for admin access                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: IDENTITY & ACCESS                                                     │
│  ═════════════════════════                                                      │
│  • Azure AD / Entra ID authentication                                           │
│  • Managed Identities (no stored credentials)                                   │
│  • RBAC (Role-Based Access Control)                                             │
│  • Conditional Access policies                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: APPLICATION SECURITY                                                  │
│  ════════════════════════════                                                   │
│  • Input validation                                                             │
│  • Output encoding                                                              │
│  • Content Safety API (moderation)                                              │
│  • Rate limiting                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: DATA SECURITY                                                         │
│  ═════════════════════                                                          │
│  • Encryption at rest (AES-256)                                                 │
│  • Encryption in transit (TLS 1.2+)                                             │
│  • Key Vault for secrets                                                        │
│  • Customer-managed keys (optional)                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│  User  │     │Frontend│     │Azure AD│     │  API   │     │ Backend│
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │              │
    │  1. Login    │              │              │              │
    │─────────────▶│              │              │              │
    │              │              │              │              │
    │              │ 2. Redirect  │              │              │
    │              │─────────────▶│              │              │
    │              │              │              │              │
    │  3. Authenticate            │              │              │
    │────────────────────────────▶│              │              │
    │              │              │              │              │
    │              │ 4. ID Token  │              │              │
    │◀─────────────────────────────              │              │
    │              │              │              │              │
    │  5. Access Token            │              │              │
    │─────────────▶│              │              │              │
    │              │              │              │              │
    │              │ 6. API Call + Bearer Token  │              │
    │              │───────────────────────────▶│              │
    │              │              │              │              │
    │              │              │ 7. Validate  │              │
    │              │              │◀─────────────│              │
    │              │              │              │              │
    │              │              │ 8. Valid     │              │
    │              │              │─────────────▶│              │
    │              │              │              │              │
    │              │              │              │ 9. Process   │
    │              │              │              │─────────────▶│
    │              │              │              │              │
    │              │ 10. Response │              │              │
    │◀──────────────────────────────────────────│◀─────────────│
    │              │              │              │              │
```

---

## 7. Deployment Architecture

### 7.1 Azure Resource Topology

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           AZURE DEPLOYMENT TOPOLOGY                               │
│                              Region: West US 2                                    │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                     RESOURCE GROUP: rg-genai-copilot-dev-wus2                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                        VIRTUAL NETWORK: vnet-genai-copilot                │ │
│  │                            Address Space: 10.0.0.0/16                     │ │
│  │                                                                           │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │ │
│  │  │ snet-private-eps    │  │   snet-functions    │  │    snet-vm       │  │ │
│  │  │   10.0.1.0/24       │  │    10.0.2.0/24      │  │   10.0.3.0/24    │  │ │
│  │  │                     │  │                     │  │                  │  │ │
│  │  │ • Cosmos DB PE      │  │ • Function Apps     │  │ • Backend VMs    │  │ │
│  │  │ • AI Search PE      │  │   (VNet Integration)│  │ • Nginx          │  │ │
│  │  │ • OpenAI PE         │  │                     │  │                  │  │ │
│  │  │ • Storage PE        │  │                     │  │                  │  │ │
│  │  │ • Key Vault PE      │  │                     │  │                  │  │ │
│  │  └─────────────────────┘  └─────────────────────┘  └──────────────────┘  │ │
│  │                                                                           │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐│ │
│  │  │            AzureBastionSubnet: 10.0.254.0/27                         ││ │
│  │  │                    • Azure Bastion Host                              ││ │
│  │  └──────────────────────────────────────────────────────────────────────┘│ │
│  │                                                                           │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐             │
│  │      COMPUTE RESOURCES      │  │       AI SERVICES           │             │
│  │  ─────────────────────────  │  │  ─────────────────────────  │             │
│  │  • asp-func-consumption     │  │  • oai-genai-copilot       │             │
│  │  • func-api-genai-copilot   │  │  • search-genai-copilot    │             │
│  │  • func-orch-genai-copilot  │  │  • di-genai-copilot        │             │
│  │  • func-ingest-genai-copilot│  │  • cv-genai-copilot        │             │
│  │  • func-rag-genai-copilot   │  │  • cs-genai-copilot        │             │
│  │  • vm-backend-1             │  │                             │             │
│  └─────────────────────────────┘  └─────────────────────────────┘             │
│                                                                                 │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐             │
│  │      DATA SERVICES          │  │     MONITORING              │             │
│  │  ─────────────────────────  │  │  ─────────────────────────  │             │
│  │  • stgenaicopilotdev        │  │  • log-genai-copilot       │             │
│  │  • stfuncdev                │  │  • appi-genai-copilot      │             │
│  │  • cosmos-genai-copilot     │  │  • kv-genai-copilot        │             │
│  └─────────────────────────────┘  └─────────────────────────────┘             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Environment Strategy

| Environment | Purpose | SKU Tier | Estimated Cost |
|-------------|---------|----------|----------------|
| **Dev** | Development & Testing | Consumption/Basic | ~$400-500/mo |
| **Staging** | Pre-production validation | Standard | ~$600-800/mo |
| **Prod** | Production workloads | Premium | ~$1000-1500/mo |

---

## 8. Technology Stack

### 8.1 Stack Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           TECHNOLOGY STACK                                        │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   React    │  │ TypeScript │  │  Tailwind  │  │   Vite     │               │
│  │   18.x     │  │   5.x      │  │    CSS     │  │   5.x      │               │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               BACKEND                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Python    │  │   Azure    │  │   FastAPI  │  │  LangChain │               │
│  │   3.11     │  │ Functions  │  │            │  │  (optional)│               │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AI SERVICES                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   Azure    │  │   Azure    │  │  Document  │  │  Content   │               │
│  │  OpenAI    │  │ AI Search  │  │Intelligence│  │   Safety   │               │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Cosmos DB │  │    Blob    │  │    Redis   │  │  AI Search │               │
│  │ (NoSQL)    │  │  Storage   │  │  (Cache)   │  │  (Vector)  │               │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ Terraform  │  │   Azure    │  │   Azure    │  │   GitHub   │               │
│  │   1.5+     │  │  DevOps    │  │  Monitor   │  │  Actions   │               │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Scalability & Performance

### 9.1 Scaling Strategy

| Component | Scaling Type | Trigger | Max Scale |
|-----------|-------------|---------|-----------|
| API Gateway | Auto (Consumption) | Requests | Unlimited |
| Orchestrator | Auto (Premium EP1) | Queue length | 20 instances |
| RAG Processor | Auto (Premium EP1) | CPU/Memory | 20 instances |
| AI Search | Manual | Document count | 3 replicas |
| Cosmos DB | Auto (Serverless) | RU consumption | 4000 RU/s |

### 9.2 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search Latency | < 500ms | P95 |
| AI Response Time | < 5 seconds | P95 |
| Document Processing | < 60s/page | Average |
| Availability | 99.9% | Monthly |
| Concurrent Users | 100+ | Simultaneous |

---

## 10. Appendices

### 10.1 Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - AI technique combining search with LLM |
| **LLM** | Large Language Model (e.g., GPT-4o) |
| **Embedding** | Vector representation of text for semantic search |
| **Chunking** | Splitting documents into smaller pieces for processing |
| **Private Endpoint** | Azure feature for private network access to services |

### 10.2 References

- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/)

---

*Document End*
