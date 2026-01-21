# Azure OpenAI Enterprise Platform — Architecture Guide

> **Technical Deep-Dive for Architects & Engineers**

---

## Table of Contents

1. [Architecture Principles](#architecture-principles)
2. [Network Architecture](#network-architecture)
3. [Compute Architecture](#compute-architecture)
4. [AI Services Architecture](#ai-services-architecture)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Monitoring Architecture](#monitoring-architecture)
8. [RAG Pipeline Architecture](#rag-pipeline-architecture)

---

## Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Zero Trust** | Private endpoints, no public access, AAD auth |
| **Defense in Depth** | Multiple security layers (network, identity, data) |
| **Least Privilege** | RBAC, JIT access, scoped permissions |
| **Immutable Infrastructure** | Terraform IaC, GitOps deployment |
| **Observability** | Centralized logging, distributed tracing |
| **Resilience** | Auto-scaling, multi-zone, disaster recovery |
| **Cost Optimization** | Right-sizing, auto-shutdown, lifecycle policies |

---

## Network Architecture

### Virtual Network Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    VNet: 10.0.0.0/16                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │  snet-aks          │  │  snet-functions    │                │
│  │  10.0.0.0/22       │  │  10.0.4.0/24       │                │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │                │
│  │  │ AKS Nodes    │  │  │  │ Functions    │  │                │
│  │  │ (Private)    │  │  │  │ (VNet Int)   │  │                │
│  │  └──────────────┘  │  │  └──────────────┘  │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │  snet-pe           │  │  snet-bastion      │                │
│  │  10.0.5.0/24       │  │  10.0.6.0/26       │                │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │                │
│  │  │ Private      │  │  │  │ Bastion Host │  │                │
│  │  │ Endpoints    │  │  │  │ (Prod only)  │  │                │
│  │  └──────────────┘  │  │  └──────────────┘  │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌────────────────────┐                                         │
│  │  snet-appgw        │                                         │
│  │  10.0.7.0/24       │                                         │
│  │  ┌──────────────┐  │                                         │
│  │  │ App Gateway  │  │                                         │
│  │  │ + WAF        │  │                                         │
│  │  └──────────────┘  │                                         │
│  └────────────────────┘                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Private DNS Zones

| Zone | Purpose |
|------|---------|
| `privatelink.vaultcore.azure.net` | Key Vault |
| `privatelink.blob.core.windows.net` | Blob Storage |
| `privatelink.openai.azure.com` | Azure OpenAI |
| `privatelink.search.windows.net` | AI Search |
| `privatelink.cognitiveservices.azure.com` | Cognitive Services |
| `privatelink.azurecr.io` | Container Registry |

### Network Security Groups

| NSG | Rules |
|-----|-------|
| **nsg-aks** | Allow HTTPS outbound, deny all other outbound |
| **nsg-functions** | Allow HTTPS from VNet |
| **nsg-pe** | Allow VNet, deny internet |

---

## Compute Architecture

### AKS Cluster

```yaml
AKS Configuration:
  Type: Private Cluster
  Network: Azure CNI + Calico
  Identity: System Assigned Managed Identity
  RBAC: Azure AD RBAC Enabled

  Node Pools:
    - Name: system
      Purpose: System pods
      VM Size: Standard_D2s_v3 (dev) / D4s_v3 (prod)
      Scaling: Auto-scale 2-4 (dev) / 3-6 (prod)

    - Name: workload
      Purpose: AI workloads
      VM Size: Standard_D4s_v3
      Scaling: Auto-scale 1-10
      Labels: workload=ai-services

  Add-ons:
    - Azure Policy
    - Key Vault Secrets Provider
    - Container Insights
    - Workload Identity
```

### Azure Functions

```yaml
Functions Configuration:
  Runtime: Python 3.11
  Plan: Elastic Premium (prod) / Consumption (dev)
  Network: VNet Integration

  Features:
    - Managed Identity
    - Key Vault References
    - Application Insights
    - HTTPS Only
```

---

## AI Services Architecture

### Azure OpenAI

```yaml
Azure OpenAI:
  SKU: S0
  Network: Private Endpoint Only
  Authentication: Azure AD (no API keys)

  Deployments:
    - gpt-4o (capacity: 50 TPM)
    - gpt-4o-mini (capacity: 100 TPM)
    - text-embedding-3-large (capacity: 100 TPM)

  Monitoring:
    - Token usage alerts
    - Latency tracking
    - Error rate monitoring
```

### AI Search

```yaml
AI Search:
  SKU: Standard (prod) / Basic (dev)
  Network: Private Endpoint Only
  Authentication: Azure AD

  Features:
    - Semantic Search
    - Vector Search (HNSW)
    - Hybrid Search

  Indexes:
    - documents (full-text + vectors)
    - embeddings (vector-only)
```

### Document Intelligence

```yaml
Document Intelligence:
  SKU: S0
  Network: Private Endpoint Only

  Models:
    - prebuilt-read (OCR)
    - prebuilt-layout (structure)
    - prebuilt-document (general)
```

---

## Data Architecture

### Storage Account (Data Lake Gen2)

```
Storage Structure:
├── documents/           # Source documents
│   ├── raw/            # Original uploads
│   ├── processed/      # Chunked documents
│   └── failed/         # Processing failures
│
├── embeddings/          # Vector embeddings
│   ├── full/           # Full document embeddings
│   └── chunks/         # Chunk embeddings
│
├── audit-logs/          # Audit trail
│   ├── access/         # Access logs
│   ├── changes/        # Change logs
│   └── ai-usage/       # AI usage logs
│
└── compliance-data/     # Immutable storage
```

### Lifecycle Policies

| Path | Cool (days) | Archive (days) | Delete (days) |
|------|-------------|----------------|---------------|
| `documents/` | 30 | 90 | 365 |
| `processed/` | - | - | 30 |
| `audit-logs/` | 90 | 365 | Never |

---

## Security Architecture

### Identity & Access

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure AD                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Users                    Groups                           │
│   ├── Developers    ──>   ├── SG-AI-Developers             │
│   ├── Operators     ──>   ├── SG-AI-Operators              │
│   ├── Admins        ──>   ├── SG-AI-Admins                 │
│   └── Auditors      ──>   └── SG-AI-Auditors               │
│                                                              │
│   Managed Identities                                        │
│   ├── id-aoai-app         (Application workloads)          │
│   ├── id-aoai-data        (Data processing)                │
│   ├── AKS Kubelet         (AKS cluster)                    │
│   └── Functions MI        (Azure Functions)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### RBAC Model

| Role | Key Vault | Storage | OpenAI | AKS |
|------|-----------|---------|--------|-----|
| Admin | Administrator | Owner | Contributor | Admin |
| Developer | Secrets User | Reader | User | User |
| Operator | Reader | Contributor | User | Operator |
| Auditor | Reader | Reader | Reader | Reader |

### Secrets Management

```yaml
Key Vault Secrets:
  - openai-endpoint
  - search-endpoint
  - storage-connection-string
  - app-insights-key

Access Pattern:
  1. Application uses Managed Identity
  2. Requests secret from Key Vault
  3. Key Vault validates RBAC
  4. Secret returned (no keys in code)
```

---

## Monitoring Architecture

### Observability Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Log Analytics Workspace                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Data Sources:                                             │
│   ├── AKS Logs (kube-audit, apiserver, etc.)               │
│   ├── Functions Logs                                        │
│   ├── OpenAI Logs (requests, responses)                    │
│   ├── Key Vault Audit Logs                                 │
│   ├── Storage Access Logs                                  │
│   └── NSG Flow Logs                                        │
│                                                              │
│   Solutions:                                                │
│   ├── Container Insights                                   │
│   ├── Sentinel (prod only)                                 │
│   └── Security Center                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Application Insights                         │
├─────────────────────────────────────────────────────────────┤
│   ├── Requests & Dependencies                               │
│   ├── Exceptions & Traces                                  │
│   ├── Performance Metrics                                  │
│   └── Custom Events (AI usage)                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Alert Rules                               │
├─────────────────────────────────────────────────────────────┤
│   Critical:                                                 │
│   ├── High error rate (> 5%)                               │
│   ├── Service unavailable                                  │
│   └── Security incidents                                   │
│                                                              │
│   Warning:                                                  │
│   ├── OpenAI rate limit approaching                        │
│   ├── High latency (p95 > 10s)                            │
│   └── Storage capacity (> 80%)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## RAG Pipeline Architecture

### Document Ingestion Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Upload  │───>│ Document│───>│ Chunking│───>│Embedding│
│ (Blob)  │    │ Intel   │    │ Service │    │ (OpenAI)│
└─────────┘    └─────────┘    └─────────┘    └────┬────┘
                                                   │
                                                   ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Response│<───│ OpenAI  │<───│ Search  │<───│ Index   │
│         │    │ (LLM)   │    │ (Query) │    │ (Store) │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Query Flow

```
User Query
    │
    ▼
┌─────────────────────┐
│ 1. Embed Query      │  (text-embedding-3-large)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Hybrid Search    │  (vector + keyword)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. Rerank Results   │  (semantic reranker)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Build Prompt     │  (context + query)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. Generate Answer  │  (GPT-4o)
└──────────┬──────────┘
           │
           ▼
      Response
```

---

## Deployment Architecture

### GitOps Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Code   │───>│   CI    │───>│   CD    │───>│  Azure  │
│  (Git)  │    │(Actions)│    │(Actions)│    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                   │              │
                   ▼              ▼
              ┌─────────┐   ┌─────────┐
              │  Test   │   │Terraform│
              │  Scan   │   │  Apply  │
              └─────────┘   └─────────┘
```

---

## Disaster Recovery

| Component | RPO | RTO | Strategy |
|-----------|-----|-----|----------|
| AKS | 0 | 1 hour | Multi-zone, re-deploy |
| Storage | 0 | 1 hour | GRS replication |
| OpenAI | N/A | N/A | Regional failover |
| Key Vault | 0 | 15 min | Soft delete + backup |
| AI Search | 1 hour | 2 hours | Index rebuild |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Architecture Team |
