# Network Architecture — Azure OpenAI Enterprise RAG Platform

> Comprehensive network topology, segmentation, DNS architecture, and traffic flow design for the Enterprise RAG Copilot platform — aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF**.

---

## Table of Contents

1. [Network Topology Overview](#1-network-topology-overview)
2. [VNet Design & CIDR Allocation](#2-vnet-design--cidr-allocation)
3. [Subnet Purpose & Sizing Rationale](#3-subnet-purpose--sizing-rationale)
4. [Network Security Groups (NSGs)](#4-network-security-groups-nsgs)
5. [Private Endpoints & DNS Resolution](#5-private-endpoints--dns-resolution)
6. [Private DNS Zones](#6-private-dns-zones)
7. [Application Gateway Routing](#7-application-gateway-routing)
8. [API Management Backend Configuration](#8-api-management-backend-configuration)
9. [Traffic Flow — External User Request](#9-traffic-flow--external-user-request)
10. [Traffic Flow — Service-to-Service Internal](#10-traffic-flow--service-to-service-internal)
11. [DNS Architecture](#11-dns-architecture)
12. [Network Segmentation Rationale](#12-network-segmentation-rationale)
13. [ADR: Hub-Spoke vs Flat VNet](#13-adr-hub-spoke-vs-flat-vnet)
14. [Hybrid Connectivity — ExpressRoute / VPN](#14-hybrid-connectivity--expressroute--vpn)
15. [Network Monitoring & Observability](#15-network-monitoring--observability)
16. [Azure Firewall Rules Summary](#16-azure-firewall-rules-summary)
17. [Document Control](#17-document-control)

---

## 1. Network Topology Overview

### Full Network Topology Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         INTERNET                                                    │
│                                            │                                                        │
│                                   ┌────────▼────────┐                                               │
│                                   │   Azure DDoS    │                                               │
│                                   │   Protection    │                                               │
│                                   │   (Standard)    │                                               │
│                                   └────────┬────────┘                                               │
│                                            │                                                        │
│ ┌──────────────────────────────────────────┼───────────────────────────────────────────────────────┐ │
│ │                          VNet: rag-platform-vnet (10.0.0.0/16)                                  │ │
│ │                                          │                                                      │ │
│ │  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │ │
│ │  │  appgw-subnet (10.0.8.0/24)                                                             │   │ │
│ │  │  ┌──────────────────────────────────────────────────┐                                    │   │ │
│ │  │  │  Application Gateway + WAF v2                    │                                    │   │ │
│ │  │  │  - Public IP: rag-appgw-pip                      │                                    │   │ │
│ │  │  │  - WAF Policy: OWASP 3.2                         │                                    │   │ │
│ │  │  │  - SSL Termination (TLS 1.2+)                    │                                    │   │ │
│ │  │  └──────────────────────┬───────────────────────────┘                                    │   │ │
│ │  └─────────────────────────┼───────────────────────────────────────────────────────────────┘   │ │
│ │                            │                                                                    │ │
│ │  ┌─────────────────────────▼───────────────────────────────────────────────────────────────┐   │ │
│ │  │  apim-subnet (10.0.9.0/24)                                                              │   │ │
│ │  │  ┌──────────────────────────────────────────────────┐                                    │   │ │
│ │  │  │  API Management (Premium, Internal Mode)         │                                    │   │ │
│ │  │  │  - Rate Limiting, Throttling, JWT Validation     │                                    │   │ │
│ │  │  │  - OAuth 2.0 / Managed Identity Auth             │                                    │   │ │
│ │  │  │  - Subscription Key Enforcement                  │                                    │   │ │
│ │  │  └──────────────────────┬───────────────────────────┘                                    │   │ │
│ │  └─────────────────────────┼───────────────────────────────────────────────────────────────┘   │ │
│ │                            │                                                                    │ │
│ │  ┌─────────────────────────▼───────────────────────────────────────────────────────────────┐   │ │
│ │  │  aks-subnet (10.0.0.0/21) — 2046 Usable IPs                                            │   │ │
│ │  │                                                                                          │   │ │
│ │  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐            │   │ │
│ │  │  │  System Pool   │ │  App Pool      │ │  RAG Worker    │ │  Ingestion     │            │   │ │
│ │  │  │  (3 nodes)     │ │  (3-10 nodes)  │ │  Pool          │ │  Pool          │            │   │ │
│ │  │  │  D4s_v5        │ │  D8s_v5        │ │  (2-8 nodes)   │ │  (1-4 nodes)   │            │   │ │
│ │  │  └────────────────┘ └────────────────┘ │  D8s_v5        │ │  D4s_v5        │            │   │ │
│ │  │                                         └────────────────┘ └────────────────┘            │   │ │
│ │  │  Services: Copilot API, RAG Orchestrator, Embedding Service, Ingestion Pipeline          │   │ │
│ │  └─────────────────┬──────────────────────┬──────────────────┬─────────────────────────────┘   │ │
│ │                    │ Private Endpoints     │                  │                                  │ │
│ │  ┌─────────────────▼──────────────────────▼──────────────────▼─────────────────────────────┐   │ │
│ │  │  pe-subnet (10.0.10.0/24) — Private Endpoints                                           │   │ │
│ │  │                                                                                          │   │ │
│ │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │ │
│ │  │  │ OpenAI   │ │ AI       │ │ Cosmos   │ │ Storage  │ │ Key      │ │ Redis    │         │   │ │
│ │  │  │ PE       │ │ Search   │ │ DB PE    │ │ PE       │ │ Vault PE │ │ PE       │         │   │ │
│ │  │  │ 10.0.10.4│ │ PE       │ │10.0.10.6 │ │10.0.10.7 │ │10.0.10.8 │ │10.0.10.9 │         │   │ │
│ │  │  └──────────┘ │10.0.10.5 │ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │   │ │
│ │  │               └──────────┘                                                               │   │ │
│ │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                                    │   │ │
│ │  │  │ Doc      │ │ Content  │ │ ACR PE   │ │ App      │                                    │   │ │
│ │  │  │ Intel PE │ │ Safety   │ │10.0.10.12│ │ Insights │                                    │   │ │
│ │  │  │10.0.10.10│ │ PE       │ └──────────┘ │ PE       │                                    │   │ │
│ │  │  └──────────┘ │10.0.10.11│              │10.0.10.13│                                    │   │ │
│ │  │               └──────────┘              └──────────┘                                    │   │ │
│ │  └─────────────────────────────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                                                │ │
│ │  ┌─────────────────────────────────────────────────────────────────────────────────────────┐   │ │
│ │  │  functions-subnet (10.0.11.0/24) — Azure Functions VNet Integration                     │   │ │
│ │  │  ┌────────────────────────────────────────────┐                                          │   │ │
│ │  │  │  Timer-Triggered Functions                  │                                          │   │ │
│ │  │  │  - Document Ingestion Scheduler             │                                          │   │ │
│ │  │  │  - Index Maintenance                        │                                          │   │ │
│ │  │  │  - Cost Aggregation                         │                                          │   │ │
│ │  │  └────────────────────────────────────────────┘                                          │   │ │
│ │  └─────────────────────────────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                                                │ │
│ │  ┌─────────────────────────────────────────────────────────────────────────────────────────┐   │ │
│ │  │  data-subnet (10.0.12.0/24) — Data Services Delegation                                  │   │ │
│ │  │  ┌────────────────────────────────────────────┐                                          │   │ │
│ │  │  │  Delegated for future data service needs    │                                          │   │ │
│ │  │  │  - Managed Instances / Flex Server           │                                          │   │ │
│ │  │  │  - Data Factory Integration Runtime          │                                          │   │ │
│ │  │  └────────────────────────────────────────────┘                                          │   │ │
│ │  └─────────────────────────────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                                                │ │
│ └────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                    │
│  Azure Monitor / Sentinel / Network Watcher ──── Monitoring all subnets                          │
│  ON-PREMISES (Optional) ──── ExpressRoute / S2S VPN ──── VPN GW (10.0.15.0/24)                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. VNet Design & CIDR Allocation

### Primary VNet

| Property | Value |
|----------|-------|
| **VNet Name** | `rag-platform-vnet` |
| **Address Space** | `10.0.0.0/16` (65,536 IPs) |
| **Region** | East US 2 (primary), West US 2 (DR) |
| **DNS Servers** | Azure-provided (168.63.129.16) + Custom forwarders |
| **DDoS Protection** | Standard plan enabled |
| **Resource Group** | `rg-rag-platform-network` |

### Address Space Allocation Summary

```
10.0.0.0/16 — rag-platform-vnet (Total: 65,536 IPs)
│
├── 10.0.0.0/21   — aks-subnet          (2,048 IPs)  ██████████████████████ 3.1%
├── 10.0.8.0/24   — appgw-subnet        (  256 IPs)  ███                    0.4%
├── 10.0.9.0/24   — apim-subnet         (  256 IPs)  ███                    0.4%
├── 10.0.10.0/24  — pe-subnet           (  256 IPs)  ███                    0.4%
├── 10.0.11.0/24  — functions-subnet     (  256 IPs)  ███                    0.4%
├── 10.0.12.0/24  — data-subnet         (  256 IPs)  ███                    0.4%
├── 10.0.13.0/24  — bastion-subnet      (  256 IPs)  ███                    0.4%
├── 10.0.14.0/24  — devops-subnet       (  256 IPs)  ███                    0.4%
├── 10.0.15.0/24  — gateway-subnet      (  256 IPs)  ███                    0.4%
├── 10.0.16.0/24  — firewall-subnet     (  256 IPs)  ███                    0.4%
│
└── 10.0.17.0 – 10.0.255.255 — Reserved for future use (93.5% headroom)
```

**Design Principles:** /16 provides scaling headroom. AKS gets /21 for Azure CNI (30 pods/node x 50 nodes). All other subnets /24. No overlap with on-prem (172.16.0.0/12). Contiguous allocation for auditing.

---

## 3. Subnet Purpose & Sizing Rationale

| Subnet Name | CIDR Block | Usable IPs | Purpose | Services Hosted | NSG | Route Table |
|-------------|-----------|------------|---------|-----------------|-----|-------------|
| **aks-subnet** | `10.0.0.0/21` | 2,046 | AKS nodes + pods (Azure CNI) | AKS system pool, app pool, RAG worker pool, ingestion pool | `nsg-aks` | `rt-aks` |
| **appgw-subnet** | `10.0.8.0/24` | 251 | Application Gateway v2 + WAF | Application Gateway, WAF v2 policy | `nsg-appgw` | `rt-appgw` |
| **apim-subnet** | `10.0.9.0/24` | 251 | API Management (Internal VNet) | APIM Premium instance | `nsg-apim` | `rt-apim` |
| **pe-subnet** | `10.0.10.0/24` | 251 | Private Endpoints for PaaS | OpenAI, AI Search, Cosmos DB, Storage, Key Vault, Redis, Doc Intel, Content Safety, ACR, App Insights | `nsg-pe` | `rt-default` |
| **functions-subnet** | `10.0.11.0/24` | 251 | Azure Functions VNet Integration | Timer functions, event-driven processors | `nsg-functions` | `rt-default` |
| **data-subnet** | `10.0.12.0/24` | 251 | Data service delegation | Future: Managed SQL, Data Factory IR | `nsg-data` | `rt-default` |
| **bastion-subnet** | `10.0.13.0/24` | 251 | Azure Bastion (secure RDP/SSH) | Azure Bastion Standard | `nsg-bastion` | — |
| **devops-subnet** | `10.0.14.0/24` | 251 | Self-hosted build agents | Azure DevOps agents, GitHub runners | `nsg-devops` | `rt-default` |
| **gateway-subnet** | `10.0.15.0/24` | 251 | VPN / ExpressRoute Gateway | VPN Gateway or ExpressRoute Gateway | — | `rt-gateway` |
| **firewall-subnet** | `10.0.16.0/24` | 251 | Azure Firewall (if enabled) | Azure Firewall Premium | — | — |

**AKS Sizing:** 50 nodes x 30 pods = 1,500 pod IPs + 50 node IPs + 10 LB IPs + 20% buffer = 1,872 IPs needed. /21 = 2,046 usable (9% headroom).

---

## 4. Network Security Groups (NSGs)

### 4.1 NSG: nsg-appgw (Application Gateway Subnet)

| Priority | Name | Direction | Source | Destination | Port | Protocol | Action |
|----------|------|-----------|--------|-------------|------|----------|--------|
| 100 | `Allow-Internet-HTTPS` | Inbound | Internet | 10.0.8.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-Internet-HTTP` | Inbound | Internet | 10.0.8.0/24 | 80 | TCP | **Allow** |
| 120 | `Allow-GatewayManager` | Inbound | GatewayManager | 10.0.8.0/24 | 65200-65535 | TCP | **Allow** |
| 130 | `Allow-AzureLoadBalancer` | Inbound | AzureLoadBalancer | 10.0.8.0/24 | * | * | **Allow** |
| 4096 | `Deny-All-Inbound` | Inbound | * | * | * | * | **Deny** |
| 100 | `Allow-To-APIM` | Outbound | 10.0.8.0/24 | 10.0.9.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-To-AKS` | Outbound | 10.0.8.0/24 | 10.0.0.0/21 | 443 | TCP | **Allow** |
| 120 | `Allow-HealthProbe` | Outbound | 10.0.8.0/24 | Internet | 443 | TCP | **Allow** |
| 4096 | `Deny-All-Outbound` | Outbound | * | * | * | * | **Deny** |

### 4.2 NSG: nsg-apim (API Management Subnet)

| Priority | Name | Direction | Source | Destination | Port | Protocol | Action |
|----------|------|-----------|--------|-------------|------|----------|--------|
| 100 | `Allow-From-AppGW` | Inbound | 10.0.8.0/24 | 10.0.9.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-APIM-Mgmt` | Inbound | ApiManagement | 10.0.9.0/24 | 3443 | TCP | **Allow** |
| 120 | `Allow-AzureLB` | Inbound | AzureLoadBalancer | 10.0.9.0/24 | 6390 | TCP | **Allow** |
| 4096 | `Deny-All-Inbound` | Inbound | * | * | * | * | **Deny** |
| 100 | `Allow-To-AKS` | Outbound | 10.0.9.0/24 | 10.0.0.0/21 | 443 | TCP | **Allow** |
| 110 | `Allow-To-Storage` | Outbound | 10.0.9.0/24 | Storage | 443 | TCP | **Allow** |
| 120 | `Allow-To-SQL` | Outbound | 10.0.9.0/24 | Sql | 1433 | TCP | **Allow** |
| 130 | `Allow-To-KeyVault` | Outbound | 10.0.9.0/24 | AzureKeyVault | 443 | TCP | **Allow** |
| 4096 | `Deny-All-Outbound` | Outbound | * | * | * | * | **Deny** |

### 4.3 NSG: nsg-aks (AKS Subnet)

| Priority | Name | Direction | Source | Destination | Port | Protocol | Action |
|----------|------|-----------|--------|-------------|------|----------|--------|
| 100 | `Allow-From-APIM` | Inbound | 10.0.9.0/24 | 10.0.0.0/21 | 443 | TCP | **Allow** |
| 110 | `Allow-From-AppGW` | Inbound | 10.0.8.0/24 | 10.0.0.0/21 | 443 | TCP | **Allow** |
| 120 | `Allow-IntraSubnet` | Inbound | 10.0.0.0/21 | 10.0.0.0/21 | * | * | **Allow** |
| 130 | `Allow-AzureLB` | Inbound | AzureLoadBalancer | 10.0.0.0/21 | * | * | **Allow** |
| 4096 | `Deny-All-Inbound` | Inbound | * | * | * | * | **Deny** |
| 100 | `Allow-To-PE-Subnet` | Outbound | 10.0.0.0/21 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-To-KeyVault` | Outbound | 10.0.0.0/21 | AzureKeyVault | 443 | TCP | **Allow** |
| 120 | `Allow-To-AzureMonitor` | Outbound | 10.0.0.0/21 | AzureMonitor | 443 | TCP | **Allow** |
| 130 | `Allow-To-MCR` | Outbound | 10.0.0.0/21 | MicrosoftContainerRegistry | 443 | TCP | **Allow** |
| 140 | `Allow-To-AzureAD` | Outbound | 10.0.0.0/21 | AzureActiveDirectory | 443 | TCP | **Allow** |
| 150 | `Allow-DNS` | Outbound | 10.0.0.0/21 | * | 53 | UDP | **Allow** |
| 160 | `Allow-NTP` | Outbound | 10.0.0.0/21 | * | 123 | UDP | **Allow** |
| 4096 | `Deny-All-Outbound` | Outbound | * | * | * | * | **Deny** |

### 4.4 NSG: nsg-pe (Private Endpoint Subnet)

| Priority | Name | Direction | Source | Destination | Port | Protocol | Action |
|----------|------|-----------|--------|-------------|------|----------|--------|
| 100 | `Allow-From-AKS` | Inbound | 10.0.0.0/21 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-From-Functions` | Inbound | 10.0.11.0/24 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 120 | `Allow-From-DevOps` | Inbound | 10.0.14.0/24 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 4096 | `Deny-All-Inbound` | Inbound | * | * | * | * | **Deny** |
| 4096 | `Deny-All-Outbound` | Outbound | * | * | * | * | **Deny** |

### 4.5 NSG: nsg-functions (Functions Subnet)

| Priority | Name | Direction | Source | Destination | Port | Protocol | Action |
|----------|------|-----------|--------|-------------|------|----------|--------|
| 100 | `Allow-From-AKS` | Inbound | 10.0.0.0/21 | 10.0.11.0/24 | 443 | TCP | **Allow** |
| 4096 | `Deny-All-Inbound` | Inbound | * | * | * | * | **Deny** |
| 100 | `Allow-To-PE-Subnet` | Outbound | 10.0.11.0/24 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 110 | `Allow-To-AzureMonitor` | Outbound | 10.0.11.0/24 | AzureMonitor | 443 | TCP | **Allow** |
| 120 | `Allow-DNS` | Outbound | 10.0.11.0/24 | * | 53 | UDP | **Allow** |
| 4096 | `Deny-All-Outbound` | Outbound | * | * | * | * | **Deny** |

---

## 5. Private Endpoints & DNS Resolution

### Private Endpoint Inventory

| Service | Private Endpoint Name | Private IP | Subnet | Private DNS Zone |
|---------|-----------------------|-----------|--------|------------------|
| **Azure OpenAI** | `pe-openai-rag` | 10.0.10.4 | pe-subnet | `privatelink.openai.azure.com` |
| **AI Search** | `pe-search-rag` | 10.0.10.5 | pe-subnet | `privatelink.search.windows.net` |
| **Cosmos DB** | `pe-cosmos-rag` | 10.0.10.6 | pe-subnet | `privatelink.documents.azure.com` |
| **Storage Account** | `pe-storage-rag` | 10.0.10.7 | pe-subnet | `privatelink.blob.core.windows.net` |
| **Key Vault** | `pe-kv-rag` | 10.0.10.8 | pe-subnet | `privatelink.vaultcore.azure.net` |
| **Redis Cache** | `pe-redis-rag` | 10.0.10.9 | pe-subnet | `privatelink.redis.cache.windows.net` |
| **Document Intelligence** | `pe-docintel-rag` | 10.0.10.10 | pe-subnet | `privatelink.cognitiveservices.azure.com` |
| **Content Safety** | `pe-contentsafety-rag` | 10.0.10.11 | pe-subnet | `privatelink.cognitiveservices.azure.com` |
| **Container Registry** | `pe-acr-rag` | 10.0.10.12 | pe-subnet | `privatelink.azurecr.io` |
| **Application Insights** | `pe-appinsights-rag` | 10.0.10.13 | pe-subnet | `privatelink.monitor.azure.com` |

### DNS Resolution Flow Diagram

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                        PRIVATE ENDPOINT DNS RESOLUTION FLOW                           │
└───────────────────────────────────────────────────────────────────────────────────────┘

  AKS Pod requests: "rag-openai.openai.azure.com"
       │
       ▼
  ┌─────────────────────┐
  │  CoreDNS (AKS)      │   Step 1: Pod sends DNS query to CoreDNS
  │  10.0.0.10          │            (configured as cluster DNS)
  └──────────┬──────────┘
             │ forwards to
             ▼
  ┌─────────────────────┐
  │  Azure DNS          │   Step 2: CoreDNS forwards to Azure DNS
  │  168.63.129.16      │            (Azure-provided recursive resolver)
  └──────────┬──────────┘
             │ resolves CNAME
             ▼
  ┌─────────────────────────────────────────────────┐
  │  CNAME Resolution                                │
  │                                                  │
  │  rag-openai.openai.azure.com                     │
  │    └─► rag-openai.privatelink.openai.azure.com   │   Step 3: Public DNS returns
  │          └─► (Private DNS Zone lookup)            │            CNAME to privatelink
  └──────────────────────┬──────────────────────────┘
                         │ queries
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Private DNS Zone                                │
  │  privatelink.openai.azure.com                    │   Step 4: Private DNS Zone
  │                                                  │            resolves to PE IP
  │  A Record:                                       │
  │    rag-openai → 10.0.10.4                        │
  └──────────────────────┬──────────────────────────┘
                         │ returns
                         ▼
  ┌─────────────────────────────────────────────────┐
  │  Result: 10.0.10.4                               │   Step 5: Traffic flows to
  │  Traffic → pe-subnet → Private Endpoint          │            private endpoint
  │         → Azure OpenAI backend                   │            over VNet backbone
  └─────────────────────────────────────────────────┘
```

### DNS Resolution Verification

```bash
# From AKS pod or VNet-connected VM — expected: 10.0.10.4 (PE IP, not public)
nslookup rag-openai.openai.azure.com
# rag-openai.openai.azure.com → CNAME → rag-openai.privatelink.openai.azure.com → 10.0.10.4
```

---

## 6. Private DNS Zones

### Zone Configuration

| Private DNS Zone | Linked VNet | Auto-Registration | Records | Purpose |
|-----------------|-------------|-------------------|---------|---------|
| `privatelink.openai.azure.com` | rag-platform-vnet | No | `rag-openai` → 10.0.10.4 | Azure OpenAI private access |
| `privatelink.search.windows.net` | rag-platform-vnet | No | `rag-search` → 10.0.10.5 | AI Search private access |
| `privatelink.documents.azure.com` | rag-platform-vnet | No | `rag-cosmos` → 10.0.10.6 | Cosmos DB private access |
| `privatelink.blob.core.windows.net` | rag-platform-vnet | No | `ragplatformsa` → 10.0.10.7 | Storage blob private access |
| `privatelink.vaultcore.azure.net` | rag-platform-vnet | No | `rag-kv` → 10.0.10.8 | Key Vault private access |
| `privatelink.redis.cache.windows.net` | rag-platform-vnet | No | `rag-redis` → 10.0.10.9 | Redis Cache private access |
| `privatelink.cognitiveservices.azure.com` | rag-platform-vnet | No | `rag-docintel` → 10.0.10.10, `rag-contentsafety` → 10.0.10.11 | Cognitive Services private access |
| `privatelink.azurecr.io` | rag-platform-vnet | No | `ragacr` → 10.0.10.12 | Container Registry private access |
| `privatelink.monitor.azure.com` | rag-platform-vnet | No | `rag-appinsights` → 10.0.10.13 | Application Insights private access |

### Terraform Reference

```hcl
# Private DNS Zone + VNet Link + Private Endpoint (pattern for all services)
resource "azurerm_private_dns_zone" "openai" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = azurerm_resource_group.network.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "openai_vnet_link" {
  name                  = "link-openai-to-vnet"
  resource_group_name   = azurerm_resource_group.network.name
  private_dns_zone_name = azurerm_private_dns_zone.openai.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
}
```

---

## 7. Application Gateway Routing

### Listeners

| Listener Name | Frontend IP | Port | Protocol | Hostname | SSL Certificate |
|---------------|-----------|------|----------|----------|-----------------|
| `lst-https-copilot` | Public | 443 | HTTPS | `copilot.rag-platform.example.com` | `cert-copilot-tls` (Key Vault) |
| `lst-https-api` | Public | 443 | HTTPS | `api.rag-platform.example.com` | `cert-api-tls` (Key Vault) |
| `lst-https-portal` | Public | 443 | HTTPS | `portal.rag-platform.example.com` | `cert-portal-tls` (Key Vault) |
| `lst-http-redirect` | Public | 80 | HTTP | `*` | — (redirect only) |

### Backend Pools

| Backend Pool | Targets | Health Probe | Port | Protocol |
|--------------|---------|-------------|------|----------|
| `bp-apim` | 10.0.9.4 (APIM internal IP) | `/status-0123456789abcdef` | 443 | HTTPS |
| `bp-aks-ingress` | 10.0.0.100 (AKS NGINX Ingress LB) | `/healthz` | 443 | HTTPS |
| `bp-portal` | 10.0.0.101 (AKS Portal Service) | `/health` | 443 | HTTPS |

### Routing Rules

| Rule Name | Listener | Backend Pool | Path Pattern | Rewrite Rules | Priority |
|-----------|----------|-------------|-------------|---------------|----------|
| `rule-api-to-apim` | `lst-https-api` | `bp-apim` | `/api/*` | Strip `/api` prefix, add `X-Forwarded-Host` | 100 |
| `rule-copilot-to-aks` | `lst-https-copilot` | `bp-aks-ingress` | `/*` | Add `X-Request-ID`, `X-Real-IP` | 200 |
| `rule-portal-to-aks` | `lst-https-portal` | `bp-portal` | `/*` | Add `X-Forwarded-Proto: https` | 300 |
| `rule-http-redirect` | `lst-http-redirect` | — | `/*` | Redirect HTTP → HTTPS (301) | 400 |

### WAF Policy Summary

| Setting | Value |
|---------|-------|
| **Managed Rule Set** | OWASP 3.2 (all rules enabled) |
| **Bot Protection** | Microsoft_BotManagerRuleSet 1.0 |
| **Mode** | Prevention |
| **Request Body Check** | Enabled (max 128 KB) |
| **File Upload Limit** | 100 MB |

**Custom Rules:**

| Priority | Name | Type | Action | Condition |
|----------|------|------|--------|-----------|
| 1 | `RateLimitPerIP` | RateLimitRule | Block | >100 req/min from non-internal IPs |
| 2 | `BlockMaliciousUA` | MatchRule | Block | User-Agent contains sqlmap, nikto, nmap, masscan |

---

## 8. API Management Backend Configuration

### APIM Instance Configuration

| Property | Value |
|----------|-------|
| **SKU** | Premium |
| **VNet Mode** | Internal |
| **Subnet** | `apim-subnet` (10.0.9.0/24) |
| **Internal IP** | 10.0.9.4 |
| **Gateway URL** | `https://rag-apim.azure-api.net` |
| **Management URL** | `https://rag-apim.management.azure-api.net` |
| **Identity** | System-assigned Managed Identity |

### Backend API Configuration

| API Name | Backend URL | Auth Method | Rate Limit | Cache TTL | Products |
|----------|------------|-------------|------------|-----------|----------|
| **Copilot Chat** | `https://10.0.0.100/api/v1/chat` | Managed Identity + JWT | 60 req/min/user | — | Copilot |
| **RAG Query** | `https://10.0.0.100/api/v1/query` | Managed Identity + JWT | 30 req/min/user | 300s | Copilot, Internal |
| **Document Upload** | `https://10.0.0.100/api/v1/documents` | Managed Identity + JWT | 10 req/min/user | — | Admin |
| **Index Management** | `https://10.0.0.100/api/v1/indexes` | Managed Identity + JWT | 5 req/min/user | — | Admin |
| **Health Check** | `https://10.0.0.100/healthz` | None | — | — | System |
| **OpenAI Proxy** | `https://10.0.10.4/openai` | Managed Identity | 120 req/min/app | — | Internal |
| **Search Proxy** | `https://10.0.10.5` | API Key (Key Vault) | 100 req/min/app | 60s | Internal |

### APIM Policy Summary

| Policy | Scope | Configuration |
|--------|-------|---------------|
| **JWT Validation** | Inbound | Azure AD OpenID Connect, audience: `api://rag-platform-copilot`, roles: `Copilot.User`, `Copilot.Admin` |
| **Rate Limiting** | Inbound | 60 calls/min per JWT subject |
| **Request Headers** | Inbound | Inject `X-Request-ID` from context |
| **Backend Routing** | Backend | Forward to `https://10.0.0.100`, timeout: 120s |
| **Security Headers** | Outbound | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` |

---

## 9. Traffic Flow — External User Request

### End-to-End Request Path

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL USER REQUEST — COPILOT CHAT QUERY                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
 │          │ (1)  │              │ (2)  │              │ (3)  │                  │
 │  User    │─────>│  Azure DDoS  │─────>│  App Gateway │─────>│  APIM            │
 │ Browser  │ HTTPS│  Protection  │      │  + WAF v2    │ HTTPS│  (Internal VNet) │
 │          │  443 │              │      │  10.0.8.x    │  443 │  10.0.9.4        │
 └──────────┘      └──────────────┘      └──────────────┘      └────────┬─────────┘
                                                                         │ (4) HTTPS 443
                                                                         ▼
                                                                ┌──────────────────┐
                                                                │  AKS Ingress     │
                                                                │  Controller      │
                                                                │  (NGINX)         │
                                                                │  10.0.0.100      │
                                                                └────────┬─────────┘
                                                                         │ (5) ClusterIP
                                                                         ▼
                                                                ┌──────────────────┐
                                                                │  Copilot API     │
                                                                │  Service (Pod)   │
                                                                │  10.0.x.x        │
                                                                └────────┬─────────┘
                                                                         │ (6)
                                          ┌──────────────────────────────┼──────────────────┐
                                          │                              │                  │
                                          ▼                              ▼                  ▼
                                 ┌────────────────┐            ┌────────────────┐  ┌────────────────┐
                                 │  Redis Cache   │            │  AI Search     │  │  Azure OpenAI  │
                                 │  (Semantic     │            │  (Hybrid       │  │  (GPT-4o)      │
                                 │   Cache)       │            │   Search)      │  │  via PE        │
                                 │  10.0.10.9     │            │  10.0.10.5     │  │  10.0.10.4     │
                                 └────────────────┘            └────────────────┘  └────────────────┘
                                          │                              │                  │
                                          └──────────────────────────────┼──────────────────┘
                                                                         │ (7)
                                                                         ▼
                                                                ┌──────────────────┐
                                                                │  Response        │
                                                                │  assembled with  │
                                                                │  citations &     │
                                                                │  confidence      │
                                                                └────────┬─────────┘
                                                                         │ (8) Reverse path
                                                                         ▼
 ┌──────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
 │  User    │<─────│  App Gateway │<─────│    APIM      │<─────│  AKS Pod         │
 │ Browser  │  TLS │              │  443 │              │  443 │                  │
 └──────────┘      └──────────────┘      └──────────────┘      └──────────────────┘
```

### Request Flow Steps

| Step | Component | Action | Network Path | Port |
|------|-----------|--------|-------------|------|
| 1 | **User Browser** | HTTPS request to `copilot.rag-platform.example.com` | Internet → Public IP | 443 |
| 2 | **DDoS Protection** | Volumetric attack mitigation, traffic scrubbing | Azure backbone | — |
| 3 | **App Gateway + WAF** | SSL termination, OWASP rule evaluation, route to backend | appgw-subnet → apim-subnet | 443 |
| 4 | **API Management** | JWT validation, rate limiting, request transform | apim-subnet → aks-subnet | 443 |
| 5 | **AKS Ingress** | Route to Copilot API service via Kubernetes Service | aks-subnet (internal) | 443 |
| 6 | **Copilot API Pod** | Orchestrate: cache check → search → LLM completion | aks-subnet → pe-subnet | 443 |
| 7 | **Backend Services** | Redis cache, AI Search retrieval, OpenAI completion | pe-subnet (private endpoints) | 443 |
| 8 | **Response** | Reverse path: AKS → APIM → App GW → User | Reverse of above | 443 |

---

## 10. Traffic Flow — Service-to-Service Internal

### Internal RAG Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    INTERNAL SERVICE-TO-SERVICE TRAFFIC FLOWS                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  AKS Cluster (aks-subnet: 10.0.0.0/21)                                        │
  │                                                                                 │
  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐          │
  │  │  RAG Orchestrator│───>│  Embedding       │    │  Ingestion       │          │
  │  │  Service         │    │  Service         │    │  Pipeline        │          │
  │  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘          │
  │           │                       │                        │                    │
  └───────────┼───────────────────────┼────────────────────────┼────────────────────┘
              │                       │                        │
              │ (All traffic via Private Endpoints in pe-subnet: 10.0.10.0/24)
              │                       │                        │
    ┌─────────┼───────────────────────┼────────────────────────┼─────────────────┐
    │         ▼                       ▼                        ▼                 │
    │  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐             │
    │  │ Azure OpenAI │  │ Azure OpenAI     │  │ Storage Account  │             │
    │  │ GPT-4o       │  │ text-embedding-  │  │ (Blob)           │             │
    │  │ Completion   │  │ 3-large          │  │ Document Upload  │             │
    │  │ PE: 10.0.10.4│  │ PE: 10.0.10.4   │  │ PE: 10.0.10.7   │             │
    │  └──────────────┘  └──────────────────┘  └──────────────────┘             │
    │                                                     │                     │
    │  ┌──────────────┐  ┌──────────────────┐             ▼                     │
    │  │ AI Search    │  │ Cosmos DB        │  ┌──────────────────┐             │
    │  │ Hybrid Query │  │ Chat History &   │  │ Document         │             │
    │  │ + Semantic   │  │ Audit Logs       │  │ Intelligence     │             │
    │  │ Ranking      │  │                  │  │ (OCR + Layout)   │             │
    │  │ PE: 10.0.10.5│  │ PE: 10.0.10.6   │  │ PE: 10.0.10.10  │             │
    │  └──────────────┘  └──────────────────┘  └────────┬─────────┘             │
    │                                                    │                      │
    │  ┌──────────────┐  ┌──────────────────┐            ▼                      │
    │  │ Key Vault    │  │ Redis Cache      │  ┌──────────────────┐             │
    │  │ Secrets &    │  │ Semantic Cache   │  │ Content Safety   │             │
    │  │ Certificates │  │ + Session Store  │  │ Text Moderation  │             │
    │  │ PE: 10.0.10.8│  │ PE: 10.0.10.9   │  │ PE: 10.0.10.11  │             │
    │  └──────────────┘  └──────────────────┘  └──────────────────┘             │
    │                                                                           │
    │                      pe-subnet (10.0.10.0/24)                             │
    └───────────────────────────────────────────────────────────────────────────┘

  Key: All internal traffic uses HTTPS (443) over private endpoints.
       No service-to-service traffic traverses the public internet.
       All DNS resolution goes through Private DNS Zones.
```

### Service Dependency Matrix

| Source Service | Target Service | Protocol | Port | Auth Method | Traffic Pattern |
|---------------|----------------|----------|------|-------------|-----------------|
| **RAG Orchestrator** | Azure OpenAI | HTTPS | 443 | Managed Identity | Synchronous (streaming) |
| **RAG Orchestrator** | AI Search | HTTPS | 443 | API Key (Key Vault) | Synchronous |
| **RAG Orchestrator** | Redis Cache | HTTPS | 6380 | Access Key (Key Vault) | Synchronous |
| **RAG Orchestrator** | Cosmos DB | HTTPS | 443 | Managed Identity | Synchronous |
| **RAG Orchestrator** | Content Safety | HTTPS | 443 | Managed Identity | Synchronous |
| **Embedding Service** | Azure OpenAI | HTTPS | 443 | Managed Identity | Synchronous (batch) |
| **Ingestion Pipeline** | Storage Account | HTTPS | 443 | Managed Identity | Async (event-driven) |
| **Ingestion Pipeline** | Document Intelligence | HTTPS | 443 | Managed Identity | Async (polling) |
| **Ingestion Pipeline** | AI Search | HTTPS | 443 | API Key (Key Vault) | Synchronous (indexing) |
| **All Services** | Key Vault | HTTPS | 443 | Managed Identity | On-demand secret fetch |
| **All Services** | Application Insights | HTTPS | 443 | Connection String | Async (telemetry push) |

---

## 11. DNS Architecture

### DNS Resolution Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DNS ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
  │  AKS Pods       │         │  Azure Functions │         │  DevOps Agents  │
  │  (CoreDNS)      │         │  (Azure DNS)     │         │  (Azure DNS)    │
  └────────┬────────┘         └────────┬─────────┘         └────────┬────────┘
           │                           │                            │
           └───────────────────────────┼────────────────────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │  Azure DNS Resolver      │
                          │  168.63.129.16           │
                          │                          │
                          │  Resolution Order:       │
                          │  1. Private DNS Zones    │
                          │  2. VNet DNS settings    │
                          │  3. Azure Public DNS     │
                          └────────────┬─────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
                    ▼                  ▼                   ▼
  ┌──────────────────────┐  ┌────────────────┐  ┌────────────────────┐
  │  Private DNS Zones   │  │  Conditional   │  │  Public Azure DNS  │
  │                      │  │  Forwarder     │  │                    │
  │  privatelink.*.com   │  │  (Hybrid only) │  │  *.azure.com       │
  │  privatelink.*.net   │  │                │  │  *.windows.net     │
  │  privatelink.*.io    │  │  corp.local →  │  │                    │
  │                      │  │  10.1.0.4 (DC) │  │                    │
  │  Returns: 10.0.10.x  │  │                │  │  Returns: Public   │
  │  (PE private IPs)    │  │                │  │  IPs (blocked by   │
  │                      │  │                │  │  service firewall) │
  └──────────────────────┘  └────────────────┘  └────────────────────┘
```

### DNS Forwarding Rules (Hybrid Scenario)

| Rule Name | Domain | Target DNS | Port | Purpose |
|-----------|--------|-----------|------|---------|
| `fwd-corporate` | `corp.example.com` | 10.1.0.4, 10.1.0.5 | 53 | On-prem AD/DNS resolution |
| `fwd-intranet` | `intranet.example.com` | 10.1.0.4 | 53 | On-prem intranet sites |
| `fwd-default` | `.` (all others) | 168.63.129.16 | 53 | Azure DNS (default) |

### DNS Private Resolver (Hybrid)

| Endpoint | Subnet | IP Address | Purpose |
|----------|--------|-----------|---------|
| **Inbound** | `dns-inbound-subnet` (10.0.17.0/28) | 10.0.17.4 | On-prem queries into Azure private zones |
| **Outbound** | `dns-outbound-subnet` (10.0.17.16/28) | Dynamic | Azure queries forwarded to on-prem DNS |

---

## 12. Network Segmentation Rationale

### Zero-Trust Network Principles

| Principle | Implementation | Enforcement Mechanism |
|-----------|---------------|----------------------|
| **Deny All by Default** | Every NSG ends with explicit deny-all rules (priority 4096) | NSG default rules overridden |
| **Least Privilege Access** | Each subnet only allows traffic from known, required sources | Per-subnet NSG with source/dest specificity |
| **Micro-Segmentation** | Each service tier has its own subnet and NSG | 10 subnets with independent security policies |
| **No Lateral Movement** | Inter-subnet traffic explicitly controlled; no blanket VNet allow | NSG rules reference specific CIDR blocks |
| **Encrypted in Transit** | All internal traffic uses HTTPS/TLS 1.2+ | Application-level TLS enforcement |
| **Identity-Based Access** | Managed Identity for all service-to-service auth | Azure AD + RBAC, no shared keys |
| **Private-Only PaaS** | All PaaS services accessible only via private endpoints | Public network access disabled on all services |

### Segmentation Matrix

| Source \ Dest | appgw | apim | aks | pe | funcs | data |
|---------------|-------|------|-----|-----|-------|------|
| **appgw** | -- | 443 | 443 | DENY | DENY | DENY |
| **apim** | DENY | -- | 443 | DENY | DENY | DENY |
| **aks** | DENY | DENY | ALL | 443 | 443 | DENY |
| **pe** | DENY | DENY | DENY | -- | DENY | DENY |
| **funcs** | DENY | DENY | DENY | 443 | -- | DENY |
| **data** | DENY | DENY | DENY | 443 | DENY | -- |

### Defense-in-Depth Layers

| Layer | Control | Function |
|-------|---------|----------|
| 1 | **DDoS Protection Standard** | Volumetric attack mitigation |
| 2 | **Application Gateway WAF v2** | OWASP 3.2, bot protection, custom rules |
| 3 | **Network Security Groups** | Subnet-level L4 filtering (deny-all default) |
| 4 | **API Management Policies** | JWT validation, rate limiting, IP filtering |
| 5 | **Private Endpoints** | No public internet exposure for PaaS |
| 6 | **Service-Level Firewalls** | Per-service network ACLs (deny public) |
| 7 | **Application Auth** | Managed Identity, RBAC, OAuth 2.0 |

---

## 13. ADR: Hub-Spoke vs Flat VNet

### ADR-NET-001: Network Topology Selection

| Field | Value |
|-------|-------|
| **Title** | Hub-Spoke vs Flat VNet for RAG Platform |
| **Status** | Accepted |
| **Date** | 2024-01 |
| **Deciders** | Platform Team, Network Architects, Security Team |

### Context

The enterprise RAG platform requires a network topology that supports:

- **~29 Azure services** interconnected via private endpoints
- **Zero-trust segmentation** with deny-all defaults
- **Hybrid connectivity** to on-premises networks (future requirement)
- **Multi-environment** support (dev, staging, production)
- **Compliance** with ISO/IEC 42001 and NIST AI RMF network controls

Two primary options were evaluated:

| Criterion | Hub-Spoke | Flat VNet (Single) |
|-----------|-----------|-------------------|
| **Complexity** | High — requires peering, UDRs, firewall | Low — single VNet, simple routing |
| **Cost** | Higher — hub firewall, extra VNets, peering | Lower — no peering or hub infra |
| **Hybrid Ready** | Native — VPN/ER in hub, shared by spokes | Requires gateway in same VNet |
| **Isolation** | Strong — environment separation via VNets | Moderate — subnet-level only |
| **Operational Overhead** | Higher — more resources to manage | Lower — fewer resources |
| **Scalability** | Excellent — add spokes for new workloads | Good — add subnets (within /16) |
| **Latency** | +0.5-1ms per VNet hop | Minimal — single VNet |

### Decision

**Flat VNet (single VNet) with strict subnet segmentation** for the initial deployment.

### Rationale

1. **Single workload platform** — This is a dedicated RAG platform, not a shared enterprise hub
2. **Latency sensitive** — AI inference workloads benefit from minimal network hops
3. **Cost efficiency** — Avoids ~$1,200/month for Azure Firewall in a hub
4. **Sufficient isolation** — NSG-per-subnet with deny-all defaults provides adequate segmentation
5. **Future migration path** — Can evolve to hub-spoke by peering this VNet as a spoke

### Consequences

| Positive | Negative |
|----------|----------|
| Simpler operations, fewer resources | Less isolation than separate VNets per environment |
| Lower cost (no hub firewall or peering) | Hybrid connectivity requires gateway in workload VNet |
| Lower latency for inter-service traffic | Subnet-level segmentation only (vs VNet-level) |
| Faster time to production | Must manually manage CIDR allocation for growth |

### Migration Path to Hub-Spoke

When hub-spoke is needed: peer `rag-platform-vnet` (10.0.0.0/16) as a spoke to a new `hub-vnet` (10.1.0.0/16) containing Azure Firewall, VPN/ER Gateway, and DNS Resolver. Move gateway-subnet and firewall-subnet resources to the hub. No re-IP of workload subnets required.

---

## 14. Hybrid Connectivity — ExpressRoute / VPN

### Connectivity Options

| Option | Bandwidth | Latency | SLA | Monthly Cost | Use Case |
|--------|-----------|---------|-----|-------------|----------|
| **ExpressRoute** (Standard) | 50 Mbps – 10 Gbps | <10ms | 99.95% | $218 – $14,760 | Production hybrid |
| **S2S VPN** (VpnGw2) | Up to 1.25 Gbps | 10-50ms | 99.95% | ~$380 | Dev/staging, backup |
| **P2S VPN** | Per-client | Variable | — | ~$150 | Developer access |

### VPN Gateway Configuration

```bash
# Create VPN Gateway (if hybrid connectivity is needed)
az network vnet-gateway create \
  --name vpn-gw-rag-platform \
  --resource-group rg-rag-platform-network \
  --vnet rag-platform-vnet \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw2 \
  --generation Generation2 \
  --public-ip-address vpn-gw-pip \
  --no-wait
```

### IPsec/IKEv2 Policy

| Parameter | Value |
|-----------|-------|
| **SA Lifetime** | 3,600 seconds |
| **IPsec Encryption** | AES256 |
| **IPsec Integrity** | SHA256 |
| **IKE Encryption** | AES256 |
| **IKE Integrity** | SHA256 |
| **DH Group** | DHGroup14 |
| **PFS Group** | PFS2048 |

### Hybrid DNS Flow

| Direction | Query Pattern | Forwarded To | Purpose |
|-----------|--------------|-------------|---------|
| **On-prem to Azure** | `*.privatelink.*` | Azure DNS Private Resolver inbound (10.0.17.4) | Access Azure PaaS via private endpoints |
| **Azure to On-prem** | `corp.example.com` | On-prem DNS (10.1.0.4) via outbound endpoint | Resolve corporate domain resources |

---

## 15. Network Monitoring & Observability

### Monitoring Components

| Component | Purpose | Data Collected | Retention | Destination |
|-----------|---------|---------------|-----------|-------------|
| **NSG Flow Logs v2** | Network traffic audit | Source/dest IP, port, protocol, action, bytes | 90 days | Storage Account + Log Analytics |
| **Traffic Analytics** | Traffic pattern analysis | Geo-location, bandwidth, denied flows, anomalies | 90 days | Log Analytics |
| **Network Watcher** | Connectivity diagnostics | Packet captures, next hop, IP flow verify | On-demand | Storage Account |
| **Connection Monitor** | Endpoint reachability | Latency, packet loss, reachability state | 30 days | Log Analytics |
| **Azure Monitor Metrics** | Network performance | VNet gateway throughput, AppGW metrics, APIM metrics | 93 days | Azure Monitor |
| **Microsoft Sentinel** | Security analytics | NSG flow correlation, threat intelligence, anomaly detection | 365 days | Log Analytics (Sentinel) |

### NSG Flow Log Configuration

| Parameter | Value |
|-----------|-------|
| **Flow Log Version** | v2 |
| **Format** | JSON |
| **Retention** | 90 days |
| **Traffic Analytics** | Enabled (10-min interval) |
| **Storage Account** | `ragflowlogssa` |
| **Log Analytics** | `rag-log-analytics` |
| **NSGs Covered** | nsg-appgw, nsg-apim, nsg-aks, nsg-pe, nsg-functions, nsg-data |

### Key KQL Monitoring Queries

```bash
# Top denied flows (last 24 hours)
AzureNetworkAnalytics_CL
| where TimeGenerated > ago(24h) and FlowStatus_s == "D"
| summarize DeniedCount=count() by SrcIP_s, DestIP_s, DestPort_d, NSGRule_s
| top 20 by DeniedCount desc

# Anomalous outbound traffic (potential data exfiltration)
AzureNetworkAnalytics_CL
| where TimeGenerated > ago(1h) and FlowDirection_s == "O" and FlowStatus_s == "A"
| where not(DestIP_s startswith "10.0.")
| summarize OutboundBytes=sum(BytesSrcToDest_d) by SrcIP_s
| where OutboundBytes > 1073741824
```

### Alert Rules

| Alert Name | Condition | Severity | Action Group |
|------------|-----------|----------|--------------|
| `High Denied Flow Rate` | Denied flows > 1000 in 5 min | Sev 2 (Warning) | `ag-network-ops` |
| `Private Endpoint Unreachable` | Connection monitor failure for any PE | Sev 1 (Error) | `ag-platform-oncall` |
| `VPN Gateway Down` | Gateway connection status = NotConnected | Sev 0 (Critical) | `ag-platform-oncall` |
| `AppGW Backend Unhealthy` | Unhealthy backend count > 0 for 5 min | Sev 1 (Error) | `ag-platform-oncall` |
| `Anomalous Outbound Traffic` | Outbound > 5 GB in 1 hour from AKS | Sev 2 (Warning) | `ag-security-ops` |
| `NSG Rule Change` | Azure Activity Log: NSG write operation | Sev 3 (Info) | `ag-security-ops` |

---

## 16. Azure Firewall Rules Summary

> **Note:** Azure Firewall is optional in the flat VNet topology. This section documents the rules for when Azure Firewall Premium is added (e.g., during hub-spoke migration or for regulatory compliance).

### Network Rules Collection

| Priority | Name | Source | Destination | Port | Protocol | Action |
|----------|------|--------|-------------|------|----------|--------|
| 100 | `Allow-AKS-to-API` | 10.0.0.0/21 | 10.0.9.0/24 | 443 | TCP | **Allow** |
| 200 | `Allow-AKS-to-PE` | 10.0.0.0/21 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 300 | `Allow-Functions-to-PE` | 10.0.11.0/24 | 10.0.10.0/24 | 443 | TCP | **Allow** |
| 400 | `Allow-DNS` | 10.0.0.0/16 | * | 53 | UDP/TCP | **Allow** |
| 500 | `Allow-NTP` | 10.0.0.0/16 | * | 123 | UDP | **Allow** |
| 65000 | `Deny-All` | * | * | * | * | **Deny** |

### Application Rules Collection

| Priority | Name | Source | FQDN Target | Port | Protocol | Action |
|----------|------|--------|-------------|------|----------|--------|
| 100 | `Allow-AzureServices` | 10.0.0.0/16 | `*.azure.com, *.microsoft.com` | 443 | HTTPS | **Allow** |
| 200 | `Allow-MCR` | 10.0.0.0/21 | `mcr.microsoft.com, *.data.mcr.microsoft.com` | 443 | HTTPS | **Allow** |
| 300 | `Allow-AzureAD` | 10.0.0.0/16 | `login.microsoftonline.com, graph.microsoft.com` | 443 | HTTPS | **Allow** |
| 400 | `Allow-AzureMonitor` | 10.0.0.0/16 | `*.ods.opinsights.azure.com, *.oms.opinsights.azure.com` | 443 | HTTPS | **Allow** |
| 500 | `Allow-KeyVault` | 10.0.0.0/16 | `*.vault.azure.net` | 443 | HTTPS | **Allow** |
| 600 | `Allow-Ubuntu-Updates` | 10.0.0.0/21 | `azure.archive.ubuntu.com, security.ubuntu.com` | 80,443 | HTTP/HTTPS | **Allow** |
| 65000 | `Deny-All` | * | * | * | * | **Deny** |

### IDPS & TLS Inspection (Firewall Premium)

IDPS mode: **Alert and Deny** (all signature categories). TLS inspection enabled for AKS outbound traffic; bypassed for `*.vault.azure.net` and `*.monitor.azure.com`.

### Route Table for Firewall Integration

| Route Name | Address Prefix | Next Hop Type | Next Hop IP | Associated Subnet |
|------------|---------------|---------------|-------------|-------------------|
| `route-to-firewall` | `0.0.0.0/0` | VirtualAppliance | 10.0.16.4 | aks-subnet |
| `route-internet-via-fw` | Internet | VirtualAppliance | 10.0.16.4 | aks-subnet |
| `route-funcs-to-fw` | `0.0.0.0/0` | VirtualAppliance | 10.0.16.4 | functions-subnet |

---

## 17. Document Control

| Field | Value |
|-------|-------|
| **Document Title** | Network Architecture — Azure OpenAI Enterprise RAG Platform |
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly |
| **Approved By** | Chief Architect, Network Security Lead |
| **Framework Alignment** | CMMI Level 3, ISO/IEC 42001, NIST AI RMF |
