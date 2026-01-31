# Disaster Recovery Plan — Azure OpenAI Enterprise RAG Platform

> Comprehensive disaster recovery strategy, failover procedures, and business continuity planning for the enterprise AI platform — aligned with **CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF**.

---

## Table of Contents

1. [DR Strategy Overview](#1-dr-strategy-overview)
2. [RTO/RPO Targets by Service](#2-rtorpo-targets-by-service)
3. [DR Region Architecture](#3-dr-region-architecture)
4. [Data Replication Strategy](#4-data-replication-strategy)
5. [DNS Failover Configuration](#5-dns-failover-configuration)
6. [Failover Procedure Runbook](#6-failover-procedure-runbook)
7. [Automated vs Manual Failover Decision Tree](#7-automated-vs-manual-failover-decision-tree)
8. [DR per Data Store](#8-dr-per-data-store)
9. [DR for Stateless Services](#9-dr-for-stateless-services)
10. [Data Backlog Handling During Failover](#10-data-backlog-handling-during-failover)
11. [Recovery Validation Tests](#11-recovery-validation-tests)
12. [Post-Recovery Verification Checklist](#12-post-recovery-verification-checklist)
13. [Communication Plan](#13-communication-plan)
14. [DR Drill Schedule and Procedure](#14-dr-drill-schedule-and-procedure)
15. [DR Testing Results Log Template](#15-dr-testing-results-log-template)
16. [Cost of DR Infrastructure](#16-cost-of-dr-infrastructure)

---

## 1. DR Strategy Overview

### 1.1 Business Continuity Objectives

The Azure OpenAI Enterprise RAG Platform is classified as a **Tier 1 Critical Application**. The DR strategy ensures continuous availability of AI-assisted operations across the enterprise, protecting against regional Azure outages, data corruption, and infrastructure failures.

| Attribute | Value |
|-----------|-------|
| **DR Tier** | Tier 1 — Mission Critical |
| **Primary Region** | East US 2 |
| **Secondary Region** | Central US |
| **DR Topology** | Active-Passive (Hot Standby for data, Warm for compute) |
| **Failover Mode** | Semi-automated with manual approval gate |
| **Maximum Tolerable Downtime** | 60 minutes |
| **Platform RTO** | 30 minutes (aggregate) |
| **Platform RPO** | 5 minutes (aggregate) |
| **DR Budget** | ~35% of production infrastructure cost |
| **Compliance Frameworks** | ISO 22301, ISO/IEC 42001, NIST SP 800-34, NIST AI RMF |

### 1.2 DR Strategy Classification

| Strategy | Description | Used For |
|----------|-------------|----------|
| **Hot Standby** | Continuously running replica in secondary region | Cosmos DB, Storage, Key Vault, Redis |
| **Warm Standby** | Infrastructure provisioned but scaled down | AKS, App Gateway, APIM |
| **Cold Standby** | Terraform definitions ready, deploy on demand | Functions, Document Intelligence, Content Safety |
| **Rebuild** | Reconstruct from source of truth on failover | AI Search indexes, ACR images |

---

## 2. RTO/RPO Targets by Service

### 2.1 Consolidated Service Recovery Matrix

| # | Azure Service | Tier | RTO | RPO | DR Strategy | Failover Type | Priority |
|---|---------------|------|-----|-----|-------------|---------------|----------|
| 1 | **Azure OpenAI** | AI | 15 min | 0 (stateless) | Multi-region deployment | Automatic (Traffic Manager) | P0 |
| 2 | **Azure Cosmos DB** | Data | 10 min | < 5 min | Multi-region write, PITR 30d | Automatic (SDK) | P0 |
| 3 | **Azure AI Search** | AI | 30 min | 15 min | Rebuild from Cosmos DB | Manual rebuild | P0 |
| 4 | **Azure Kubernetes Service** | Compute | 15 min | 0 (stateless) | Terraform redeploy | Semi-auto | P0 |
| 5 | **Azure Functions** | Compute | 10 min | 0 (stateless) | Redeploy from CI/CD | Semi-auto | P1 |
| 6 | **Azure Storage (ADLS Gen2)** | Data | 5 min | < 15 min | RA-GRS replication | Automatic | P0 |
| 7 | **Azure Key Vault** | Security | 5 min | 0 | Geo-replication (managed) | Automatic | P0 |
| 8 | **Azure API Management** | Network | 20 min | 0 (config) | Backup/restore + Terraform | Semi-auto | P1 |
| 9 | **Application Gateway (WAF v2)** | Network | 15 min | 0 (config) | Terraform redeploy | Semi-auto | P1 |
| 10 | **Azure Cache for Redis** | Data | 15 min | < 1 min | Geo-replication (Premium) | Manual trigger | P1 |
| 11 | **Azure Container Registry** | Compute | 10 min | < 5 min | Geo-replication (Premium) | Automatic | P1 |
| 12 | **Azure Entra ID** | Security | 0 min | 0 | Global service (Microsoft-managed) | N/A | P0 |
| 13 | **Azure Monitor** | Ops | 5 min | 0 | Global service + secondary workspace | Automatic | P2 |
| 14 | **Application Insights** | Ops | 5 min | < 5 min | Secondary workspace | Automatic | P2 |
| 15 | **Log Analytics Workspace** | Ops | 10 min | < 5 min | Cross-region query | Semi-auto | P2 |
| 16 | **Azure Front Door** | Network | 0 min | 0 | Global service (Microsoft-managed) | Automatic | P0 |
| 17 | **Azure Traffic Manager** | Network | 0 min | 0 | Global DNS-based routing | Automatic | P0 |
| 18 | **Virtual Network** | Network | 10 min | 0 (config) | Terraform redeploy | Semi-auto | P0 |
| 19 | **Network Security Groups** | Network | 10 min | 0 (config) | Terraform redeploy | Semi-auto | P1 |
| 20 | **Azure Bastion** | Network | 15 min | 0 (config) | Terraform redeploy | Manual | P2 |
| 21 | **DDoS Protection** | Security | 5 min | 0 | Paired region linkage | Semi-auto | P1 |
| 22 | **Private DNS Zones** | Network | 10 min | 0 (config) | Terraform redeploy | Semi-auto | P1 |
| 23 | **Private Endpoints** | Network | 10 min | 0 (config) | Terraform redeploy | Semi-auto | P1 |
| 24 | **Azure Document Intelligence** | AI | 20 min | 0 (stateless) | Redeploy in secondary | Manual | P2 |
| 25 | **Azure Content Safety** | AI | 20 min | 0 (stateless) | Redeploy in secondary | Manual | P2 |
| 26 | **Azure Defender for Cloud** | Security | 0 min | 0 | Global service (Microsoft-managed) | N/A | P2 |
| 27 | **Azure Sentinel** | Security | 10 min | < 5 min | Secondary workspace linkage | Semi-auto | P2 |
| 28 | **Azure Service Bus** | Data | 10 min | < 1 min | Geo-DR paired namespace | Automatic | P1 |
| 29 | **Azure Event Grid** | Data | 5 min | 0 | Multi-region subscriptions | Automatic | P1 |

### 2.2 Priority Classification

| Priority | Label | SLA | Services Count |
|----------|-------|-----|----------------|
| **P0** | Critical Path | Restore within 15 min | 10 |
| **P1** | High Impact | Restore within 30 min | 11 |
| **P2** | Supporting | Restore within 60 min | 8 |

---

## 3. DR Region Architecture

### 3.1 Dual-Region Topology

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE FRONT DOOR / TRAFFIC MANAGER                       │
│                         (Global DNS-based Load Balancing)                        │
│                      ┌──────────┐          ┌──────────┐                         │
│                      │ Health   │          │ Priority │                         │
│                      │ Probes   │          │ Routing  │                         │
│                      └────┬─────┘          └────┬─────┘                         │
└───────────────────────────┼─────────────────────┼───────────────────────────────┘
                            │                     │
              ┌─────────────▼─────────────┐  ┌────▼──────────────────────┐
              │   PRIMARY: EAST US 2      │  │  SECONDARY: CENTRAL US    │
              │   (Active)                │  │  (Passive / Hot Standby)  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │   App Gateway WAFv2 │  │  │  │   App Gateway WAFv2 │  │
              │  │   (Active)          │  │  │  │   (Warm Standby)    │  │
              │  └────────┬────────────┘  │  │  └────────┬────────────┘  │
              │           │               │  │           │               │
              │  ┌────────▼────────────┐  │  │  ┌────────▼────────────┐  │
              │  │   APIM Gateway      │  │  │  │   APIM Gateway      │  │
              │  │   (Active)          │  │  │  │   (Warm Standby)    │  │
              │  └────────┬────────────┘  │  │  └────────┬────────────┘  │
              │           │               │  │           │               │
              │  ┌────────▼────────────┐  │  │  ┌────────▼────────────┐  │
              │  │   AKS Cluster       │  │  │  │   AKS Cluster       │  │
              │  │   (3-10 nodes)      │  │  │  │   (2 nodes standby) │  │
              │  │   ┌──────────────┐  │  │  │  │   ┌──────────────┐  │  │
              │  │   │ RAG Service  │  │  │  │  │   │ RAG Service  │  │  │
              │  │   │ API Service  │  │  │  │  │   │ API Service  │  │  │
              │  │   │ Ingestion    │  │  │  │  │   │ (Scaled down)│  │  │
              │  │   └──────────────┘  │  │  │  │   └──────────────┘  │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Azure OpenAI       │──┼──┼──│  Azure OpenAI       │  │
              │  │  GPT-4o, Embeddings │  │  │  │  GPT-4o, Embeddings │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Cosmos DB          │◄─┼──┼─►│  Cosmos DB          │  │
              │  │  (Multi-Region      │  │  │  │  (Read Replica +    │  │
              │  │   Write)            │  │  │  │   Auto Failover)    │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Azure AI Search    │  │  │  │  Azure AI Search    │  │
              │  │  S2 (3 replicas)    │  │  │  │  S2 (1 replica)     │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Storage (ADLS v2)  │──┼──┼──│  Storage (RA-GRS)   │  │
              │  │  Primary            │  │  │  │  Read-Only Secondary │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Key Vault (HSM)    │──┼──┼──│  Key Vault (HSM)    │  │
              │  │  Primary            │  │  │  │  Geo-Replicated     │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              │  ┌─────────────────────┐  │  │  ┌─────────────────────┐  │
              │  │  Redis Cache (P1)   │──┼──┼──│  Redis Cache (P1)   │  │
              │  │  Primary            │  │  │  │  Geo-Secondary      │  │
              │  └─────────────────────┘  │  │  └─────────────────────┘  │
              │                           │  │                           │
              └───────────────────────────┘  └───────────────────────────┘

              ────────── Active traffic flow
              ─ ─ ─ ─ ─ Replication / sync
```

### 3.2 Network Topology — Secondary Region

```
┌───────────────────────────────────────────────────────┐
│  VNet: vnet-genai-dr-centralus (10.1.0.0/16)         │
│                                                       │
│  ┌──────────────────────────┐  ┌───────────────────┐  │
│  │ snet-aks  10.1.1.0/24   │  │ snet-pe 10.1.4/24 │  │
│  │ AKS nodes (standby)     │  │ Private Endpoints  │  │
│  └──────────────────────────┘  └───────────────────┘  │
│                                                       │
│  ┌──────────────────────────┐  ┌───────────────────┐  │
│  │ snet-agw  10.1.2.0/24   │  │ snet-bas 10.1.5/24│  │
│  │ App Gateway (standby)   │  │ Bastion (on-demand)│  │
│  └──────────────────────────┘  └───────────────────┘  │
│                                                       │
│  ┌──────────────────────────┐                         │
│  │ snet-func 10.1.3.0/24   │                         │
│  │ Functions (cold standby) │                         │
│  └──────────────────────────┘                         │
└───────────────────────────────────────────────────────┘
```

---

## 4. Data Replication Strategy

### 4.1 Replication Matrix by Service

| Service | Replication Type | Replication Lag | Consistency Model | Recovery Notes |
|---------|-----------------|-----------------|-------------------|----------------|
| **Cosmos DB** | Multi-region active-active | < 10 ms (async) | Session consistency | Automatic failover with SDK; PITR 30 days continuous |
| **Azure Storage (ADLS v2)** | RA-GRS (Read-Access Geo-Redundant) | < 15 min | Eventual | Read-only access in secondary until failover |
| **Azure Cache for Redis** | Geo-replication (Premium) | < 1 sec | Eventual | Manual failover trigger required; cache warm-up needed |
| **Azure AI Search** | No native replication | N/A (rebuild) | N/A | Full reindex from Cosmos DB source of truth (~25 min) |
| **Key Vault** | Azure-managed geo-replication | < 1 min | Strong | Automatic failover; read-only during transition |
| **Azure Container Registry** | Geo-replication (Premium) | < 5 min | Eventual | Images available in both regions |
| **Service Bus** | Geo-DR paired namespace | < 1 min | At-least-once | Alias-based connection string; metadata only |
| **Event Grid** | Multi-region subscriptions | 0 (event-driven) | At-least-once | Re-register subscriptions in secondary |
| **Log Analytics** | Cross-workspace query | N/A | N/A | Secondary workspace for DR region resources |
| **Application Insights** | Separate instance | N/A | N/A | New instance in secondary; historical data in primary |

### 4.2 Data Sync Flow

```
PRIMARY (East US 2)                    SECONDARY (Central US)
┌──────────────┐                      ┌──────────────┐
│  Cosmos DB   │ ──── Async Multi ───►│  Cosmos DB   │
│  (Write)     │      Region Write    │  (Read/Write)│
└──────────────┘                      └──────────────┘

┌──────────────┐                      ┌──────────────┐
│  Storage     │ ──── RA-GRS ────────►│  Storage     │
│  (Read/Write)│      ~15 min lag     │  (Read Only) │
└──────────────┘                      └──────────────┘

┌──────────────┐                      ┌──────────────┐
│  Redis Cache │ ──── Geo-Repl ──────►│  Redis Cache │
│  (Primary)   │      <1 sec lag      │  (Secondary) │
└──────────────┘                      └──────────────┘

┌──────────────┐                      ┌──────────────┐
│  AI Search   │                      │  AI Search   │
│  (Active)    │   No replication     │  (Standby)   │
│  3 replicas  │   Rebuild on demand  │  1 replica   │
└──────────────┘                      └──────────────┘
```

---

## 5. DNS Failover Configuration

### 5.1 Azure Front Door Configuration

**Azure Front Door** provides global Layer 7 load balancing with automatic failover based on health probes.

```yaml
# Front Door configuration (Bicep/ARM equivalent)
frontDoor:
  name: fd-genai-copilot-prod
  sku: Premium_AzureFrontDoor
  routingRules:
    - name: api-routing
      frontendEndpoints:
        - api.genai-copilot.enterprise.com
      backendPools:
        - name: primary-eastus2
          backends:
            - address: agw-genai-copilot-prod-eastus2.azurefd.net
              priority: 1
              weight: 100
              httpPort: 80
              httpsPort: 443
        - name: secondary-centralus
          backends:
            - address: agw-genai-copilot-dr-centralus.azurefd.net
              priority: 2
              weight: 100
              httpPort: 80
              httpsPort: 443
  healthProbeSettings:
    - name: api-health
      path: /health
      protocol: Https
      intervalInSeconds: 30
      healthProbeMethod: GET
      successStatusCodes: "200"
```

### 5.2 Azure Traffic Manager Profile

```bash
# Create Traffic Manager profile with priority routing
az network traffic-manager profile create \
  --name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --routing-method Priority \
  --unique-dns-name genai-copilot-prod \
  --monitor-protocol HTTPS \
  --monitor-port 443 \
  --monitor-path "/health" \
  --monitor-interval 30 \
  --monitor-timeout 10 \
  --monitor-failures 3

# Add primary endpoint (East US 2)
az network traffic-manager endpoint create \
  --name ep-primary-eastus2 \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --target-resource-id "/subscriptions/{sub-id}/resourceGroups/rg-genai-copilot-prod-eastus2/providers/Microsoft.Network/publicIPAddresses/pip-agw-prod" \
  --priority 1 \
  --endpoint-status Enabled

# Add secondary endpoint (Central US)
az network traffic-manager endpoint create \
  --name ep-secondary-centralus \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --target-resource-id "/subscriptions/{sub-id}/resourceGroups/rg-genai-copilot-dr-centralus/providers/Microsoft.Network/publicIPAddresses/pip-agw-dr" \
  --priority 2 \
  --endpoint-status Enabled
```

### 5.3 DNS Failover Flow

```
User Request
    │
    ▼
┌─────────────────────────┐
│  Azure Front Door       │
│  genai-copilot-prod     │
│  .azurefd.net           │
│                         │
│  Health Probe: /health  │
│  Interval: 30s          │
│  Failures to degrade: 3 │
└────────┬────────────────┘
         │
    ┌────▼────┐
    │ Primary │──── Healthy? ──── YES ──► Route to East US 2
    │ Probe   │                           agw-genai-copilot-prod-eastus2
    └────┬────┘
         │ NO (3 consecutive failures = 90s detection)
         │
    ┌────▼────┐
    │Secondary│──── Healthy? ──── YES ──► Route to Central US
    │ Probe   │                           agw-genai-copilot-dr-centralus
    └────┬────┘
         │ NO
         ▼
    Return 503 + Alert PagerDuty
```

---

## 6. Failover Procedure Runbook

### 6.1 Failover Trigger Criteria

| Trigger | Detection Method | Auto/Manual | Escalation |
|---------|-----------------|-------------|------------|
| **Regional Azure outage** | Azure Status + Front Door health | Automatic DNS + Manual compute | Platform Team Lead |
| **Single service degradation** | Application Insights alerts | Manual assessment | Service Owner |
| **Data corruption detected** | Cosmos DB consistency checks | Manual | Data Team Lead + CISO |
| **Security breach** | Sentinel/Defender alerts | Manual | CISO + Platform Lead |
| **Performance degradation > 30 min** | Monitor SLO breach | Manual | Platform Team |

### 6.2 Full Regional Failover Runbook

**Estimated Total Time: 25-35 minutes**

| Step | Action | Responsible Team | Time | Command / Procedure |
|------|--------|-----------------|------|-------------------|
| 1 | **Confirm outage is regional** — verify Azure Status page and internal monitoring | Platform Ops (On-Call) | 2 min | Check https://status.azure.com + PagerDuty |
| 2 | **Notify Incident Commander** — page DR lead and open bridge call | Platform Ops | 1 min | PagerDuty escalation policy |
| 3 | **Activate DR War Room** — open incident bridge, start logging | Incident Commander | 2 min | Teams channel: #dr-incident |
| 4 | **Verify secondary region health** — confirm all standby services operational | Platform Ops | 2 min | See Step 4 commands below |
| 5 | **Initiate Cosmos DB failover** (if not auto) | Data Team | 3 min | See Step 5 commands below |
| 6 | **Initiate Storage account failover** | Data Team | 2 min | See Step 6 commands below |
| 7 | **Promote Redis geo-secondary** | Data Team | 2 min | See Step 7 commands below |
| 8 | **Scale up AKS in secondary** | Platform Ops | 5 min | See Step 8 commands below |
| 9 | **Trigger AI Search reindex** | AI/ML Team | 1 min (trigger) | See Step 9 commands below |
| 10 | **Deploy Functions to secondary** | DevOps Team | 3 min | See Step 10 commands below |
| 11 | **Verify APIM secondary operational** | Platform Ops | 2 min | See Step 11 commands below |
| 12 | **Update App Gateway backend pools** | Network Team | 2 min | See Step 12 commands below |
| 13 | **Verify Front Door routing** | Network Team | 2 min | See Step 13 commands below |
| 14 | **Run smoke tests against secondary** | QA Team | 5 min | See Step 14 commands below |
| 15 | **Confirm failover complete** — update status page | Incident Commander | 1 min | StatusPage API update |
| 16 | **Begin post-failover monitoring** | Platform Ops | Ongoing | Grafana DR dashboard |

### 6.3 Failover Commands by Step

**Step 4 — Verify Secondary Region Health:**

```bash
# Check AKS cluster status in secondary
az aks show \
  --name aks-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "{Status:provisioningState, PowerState:powerState.code}" \
  --output table

# Verify Cosmos DB secondary region
az cosmosdb show \
  --name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --query "readLocations[?locationName=='Central US'].{Region:locationName, Status:provisioningState, Priority:failoverPriority}" \
  --output table
```

**Step 5 — Cosmos DB Failover:**

```bash
# Initiate manual failover for Cosmos DB
az cosmosdb failover-priority-change \
  --name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --failover-policies "Central US=0" "East US 2=1"

# Verify failover status
az cosmosdb show \
  --name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --query "writeLocations[0].locationName" \
  --output tsv
# Expected output: Central US
```

**Step 6 — Storage Account Failover:**

```bash
# Initiate storage account failover (promotes RA-GRS secondary)
az storage account failover \
  --name stgenaicopilotp001 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --yes

# Monitor failover progress
az storage account show \
  --name stgenaicopilotp001 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --query "statusOfPrimary" \
  --output tsv
```

**Step 7 — Redis Cache Geo-Failover:**

```bash
# Unlink geo-replication (promotes secondary to primary)
az redis server-link delete \
  --name redis-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --linked-server-name redis-genai-copilot-prod-eastus2

# Verify secondary is now standalone primary
az redis show \
  --name redis-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "{Name:name, ProvisioningState:provisioningState}" \
  --output table
```

**Step 8 — Scale Up AKS in Secondary:**

```bash
# Scale the AKS node pool from standby (2) to production (5)
az aks nodepool scale \
  --cluster-name aks-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --name systempool \
  --node-count 5

# Verify deployments are healthy
kubectl --context aks-genai-copilot-dr-centralus \
  get deployments -n genai-copilot -o wide

# Scale HPA targets
kubectl --context aks-genai-copilot-dr-centralus \
  patch hpa rag-service-hpa -n genai-copilot \
  --type merge -p '{"spec":{"minReplicas":3,"maxReplicas":10}}'
```

**Step 9 — Trigger AI Search Reindex:**

```bash
# Trigger indexer run to rebuild from Cosmos DB (now primary in Central US)
az search indexer run \
  --name cosmosdb-indexer \
  --service-name srch-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus

# Monitor indexer status
az search indexer status \
  --name cosmosdb-indexer \
  --service-name srch-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "lastResult.{Status:status, ItemsProcessed:itemsProcessed, Errors:errors}" \
  --output table
```

**Step 10 — Deploy Functions to Secondary:**

```bash
# Deploy pre-retrieval function
az functionapp deployment source config-zip \
  --name func-preretrieve-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --src ./artifacts/func-preretrieve-latest.zip

# Deploy RAG processor function
az functionapp deployment source config-zip \
  --name func-ragprocessor-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --src ./artifacts/func-ragprocessor-latest.zip

# Deploy ingestion function
az functionapp deployment source config-zip \
  --name func-ingestion-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --src ./artifacts/func-ingestion-latest.zip
```

**Step 11 — Verify APIM Secondary:**

```bash
# Check APIM service status
az apim show \
  --name apim-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "{Name:name, Status:provisioningState, GatewayUrl:gatewayUrl}" \
  --output table

# Restore latest APIM backup if needed
az apim backup \
  --name apim-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --storage-account-name stgenaibackups \
  --storage-account-container apim-backups \
  --blob-name apim-latest-backup \
  --restore true
```

**Step 12 — Update App Gateway Backend:**

```bash
# Verify App Gateway backend health in secondary
az network application-gateway show-backend-health \
  --name agw-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "backendAddressPools[].backendHttpSettingsCollection[].servers[].{Address:address, Health:health}" \
  --output table
```

**Step 13 — Verify Front Door Routing:**

```bash
# Check Traffic Manager endpoint status
az network traffic-manager endpoint show \
  --name ep-secondary-centralus \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --query "{Name:name, Status:endpointStatus, MonitorStatus:endpointMonitorStatus}" \
  --output table

# Force Traffic Manager to route to secondary (if automatic failover hasn't triggered)
az network traffic-manager endpoint update \
  --name ep-primary-eastus2 \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --endpoint-status Disabled
```

**Step 14 — Smoke Tests:**

```bash
# Run DR smoke test suite
curl -s -o /dev/null -w "%{http_code}" \
  https://api-dr.genai-copilot.enterprise.com/health

# Test RAG pipeline end-to-end
curl -X POST https://api-dr.genai-copilot.enterprise.com/v1/chat \
  -H "Authorization: Bearer ${DR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query": "DR smoke test query", "session_id": "dr-test-001"}' \
  | jq '.status'

# Verify Cosmos DB connectivity
curl -s https://api-dr.genai-copilot.enterprise.com/health/cosmos \
  | jq '.status, .region'
```

---

## 7. Automated vs Manual Failover Decision Tree

```
                    ┌──────────────────────┐
                    │  INCIDENT DETECTED   │
                    │  (Alert Triggered)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Is this a full      │
                    │  regional outage?    │
                    └──────────┬───────────┘
                          ┌────┴────┐
                         YES        NO
                          │         │
              ┌───────────▼──┐  ┌───▼───────────────┐
              │ Front Door   │  │ Single service     │
              │ auto-detects │  │ degradation?       │
              │ & routes to  │  └───┬───────────────┘
              │ secondary    │ ┌────┴────┐
              │ (AUTOMATIC)  │YES        NO
              └──────┬───────┘ │         │
                     │  ┌──────▼───────┐ │
                     │  │ Is the       │ │
                     │  │ affected svc │ ▼
                     │  │ stateful?    │ Monitor &
                     │  └──────┬───────┘ investigate
                     │    ┌────┴────┐
                     │   YES        NO
                     │    │         │
                     │ ┌──▼──────────┐ ┌──▼──────────────┐
                     │ │ MANUAL      │ │ AUTOMATIC        │
                     │ │ FAILOVER    │ │ FAILOVER         │
                     │ │             │ │                  │
                     │ │ Requires:   │ │ Stateless svcs   │
                     │ │ - IC apprvl │ │ redeploy via     │
                     │ │ - Data team │ │ Terraform/CI/CD  │
                     │ │ - Runbook   │ │ (< 15 min auto)  │
                     │ │   Steps 5-9 │ └──────────────────┘
                     │ └─────────────┘
                     │
              ┌──────▼───────────────────────┐
              │  POST-FAILOVER ACTIONS       │
              │                              │
              │  1. Scale up AKS secondary   │
              │  2. Trigger AI Search rebuild │
              │  3. Deploy Functions          │
              │  4. Validate data integrity   │
              │  5. Run smoke tests           │
              │  6. Update status page        │
              │  7. Notify stakeholders       │
              └──────────────────────────────┘
```

### 7.1 Failover Decision Matrix

| Scenario | DNS/Traffic | Compute | Data | AI Search | Decision |
|----------|------------|---------|------|-----------|----------|
| Full regional outage | Automatic | Manual scale-up | Auto (Cosmos) + Manual (Storage, Redis) | Manual rebuild | **Semi-Automatic** |
| Azure OpenAI regional issue | Automatic | No action | No action | No action | **Automatic** |
| Cosmos DB regional failure | No change | No action | Automatic failover | Manual reindex | **Semi-Automatic** |
| AKS cluster failure | Automatic (health probe) | Terraform redeploy | No action | No action | **Semi-Automatic** |
| Storage account failure | No change | No action | Manual failover | No action | **Manual** |
| Network / VNet issue | Automatic | Manual assessment | No action | No action | **Manual** |

---

## 8. DR per Data Store

### 8.1 Cosmos DB Disaster Recovery

**Configuration: Multi-Region Write with Automatic Failover**

| Parameter | Value |
|-----------|-------|
| **Consistency Level** | Session |
| **Write Regions** | East US 2 (primary), Central US (secondary) |
| **Automatic Failover** | Enabled |
| **PITR (Point-in-Time Restore)** | Enabled — 30 days continuous backup |
| **Backup Storage Redundancy** | Geo-redundant |
| **Conflict Resolution** | Last Writer Wins (LWW) on `_ts` |
| **Containers Protected** | chat-sessions, documents, embeddings-metadata, user-profiles, audit-logs, feedback, system-config |

```bash
# Enable multi-region write and automatic failover
az cosmosdb update \
  --name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --enable-automatic-failover true \
  --enable-multiple-write-locations true \
  --locations regionName="East US 2" failoverPriority=0 isZoneRedundant=true \
  --locations regionName="Central US" failoverPriority=1 isZoneRedundant=true

# Configure continuous backup (PITR 30 days)
az cosmosdb update \
  --name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --backup-policy-type Continuous \
  --continuous-tier Continuous30Days

# Restore to point-in-time (if data corruption detected)
az cosmosdb restore \
  --target-database-account-name cosmos-genai-copilot-restored \
  --account-name cosmos-genai-copilot-prod \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --restore-timestamp "2024-01-15T10:30:00Z" \
  --location "Central US"
```

### 8.2 Azure Storage (ADLS Gen2) Disaster Recovery

**Configuration: RA-GRS (Read-Access Geo-Redundant Storage)**

| Parameter | Value |
|-----------|-------|
| **Redundancy** | RA-GRS |
| **Primary Region** | East US 2 |
| **Secondary Region** | Central US (paired) |
| **Read Access** | Enabled in secondary (read-only) |
| **Replication Lag** | < 15 minutes (typical) |
| **Blob Versioning** | Enabled |
| **Soft Delete** | 30 days (blobs), 30 days (containers) |
| **Containers** | raw-documents, processed-documents, embeddings-export, backups |

```bash
# Check replication status
az storage account show \
  --name stgenaicopilotp001 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --query "{Primary:statusOfPrimary, Secondary:statusOfSecondary, LastSyncTime:geoReplicationStats.lastSyncTime}" \
  --output table

# Initiate account failover (promotes secondary to primary)
az storage account failover \
  --name stgenaicopilotp001 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --yes --no-wait

# Read from secondary endpoint (during degradation, before failover)
# Primary:   https://stgenaicopilotp001.blob.core.windows.net
# Secondary: https://stgenaicopilotp001-secondary.blob.core.windows.net
```

### 8.3 Azure AI Search Disaster Recovery

**Configuration: Rebuild from Cosmos DB (Source of Truth)**

| Parameter | Value |
|-----------|-------|
| **DR Strategy** | Rebuild index from Cosmos DB |
| **Secondary Instance** | srch-genai-copilot-dr-centralus (S2, 1 replica) |
| **Rebuild Time** | ~25 minutes (for current index size ~2.5M documents) |
| **Index Definition** | Stored in Git (IaC), deployed via CI/CD |
| **Indexer** | Cosmos DB change feed based |
| **Skillset** | Embeddings generation via Azure OpenAI |

```bash
# Create index in secondary (from stored definition)
az search index create \
  --name vector-index \
  --service-name srch-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --fields @./infra/search/index-definition.json

# Create and run indexer against Cosmos DB
az search indexer create \
  --name cosmosdb-indexer \
  --service-name srch-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --data-source-name cosmosdb-datasource \
  --target-index-name vector-index \
  --skillset-name embedding-skillset

# Monitor reindex progress
watch -n 10 "az search indexer status \
  --name cosmosdb-indexer \
  --service-name srch-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query 'lastResult.{Status:status, Items:itemsProcessed, Failed:itemsFailed}' \
  --output table"
```

### 8.4 Azure Cache for Redis Disaster Recovery

```bash
# Verify geo-replication link status
az redis server-link list \
  --name redis-genai-copilot-prod-eastus2 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --output table

# Promote secondary (break geo-link)
az redis server-link delete \
  --name redis-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --linked-server-name redis-genai-copilot-prod-eastus2

# Post-failover: warm cache with critical data
kubectl --context aks-genai-copilot-dr-centralus \
  exec -it deploy/cache-warmer -n genai-copilot -- \
  python warm_cache.py --source cosmos --target redis-dr
```

---

## 9. DR for Stateless Services

### 9.1 AKS (Azure Kubernetes Service)

**Strategy: Terraform Redeploy + GitOps — Target < 15 min**

| Component | DR Method | Recovery Time |
|-----------|-----------|---------------|
| **AKS cluster** | Pre-provisioned (warm standby, 2 nodes) | 0 min (already running) |
| **Node scaling** | Scale from 2 to 5+ nodes | 5 min |
| **Application pods** | Deployed via Flux/ArgoCD from Git | 3 min |
| **Ingress controller** | NGINX Ingress deployed via Helm | 2 min |
| **HPA / resource limits** | Applied via GitOps manifests | 1 min |
| **Secrets** | Synced from Key Vault via CSI driver | 1 min |

```bash
# Scale up DR AKS cluster
az aks nodepool scale \
  --cluster-name aks-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --name systempool \
  --node-count 5

# Force Flux reconciliation in DR cluster
kubectl --context aks-genai-copilot-dr-centralus \
  annotate gitrepository flux-system -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date +%s)" --overwrite

# Verify all pods are running
kubectl --context aks-genai-copilot-dr-centralus \
  get pods -n genai-copilot -o wide --field-selector=status.phase!=Running
```

### 9.2 Azure Functions

**Strategy: Redeploy from CI/CD Artifacts — Target < 10 min**

| Function App | Purpose | DR Deployment |
|-------------|---------|---------------|
| **func-preretrieve** | Query pre-processing, intent detection | ZIP deploy from artifact storage |
| **func-ragprocessor** | RAG orchestration, response assembly | ZIP deploy from artifact storage |
| **func-ingestion** | Document ingestion pipeline | ZIP deploy from artifact storage |

```bash
# Deploy all function apps to DR region (parallel execution)
for FUNC in preretrieve ragprocessor ingestion; do
  az functionapp deployment source config-zip \
    --name "func-${FUNC}-dr-centralus" \
    --resource-group rg-genai-copilot-dr-centralus \
    --src "./artifacts/func-${FUNC}-latest.zip" &
done
wait
echo "All function apps deployed to DR region."

# Update function app settings to point to DR data services
az functionapp config appsettings set \
  --name func-ragprocessor-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --settings \
    "COSMOS_ENDPOINT=https://cosmos-genai-copilot-prod.documents.azure.com:443/" \
    "SEARCH_ENDPOINT=https://srch-genai-copilot-dr-centralus.search.windows.net" \
    "OPENAI_ENDPOINT=https://oai-genai-copilot-dr-centralus.openai.azure.com/" \
    "REDIS_HOST=redis-genai-copilot-dr-centralus.redis.cache.windows.net"
```

### 9.3 Azure API Management

**Strategy: Backup/Restore + Terraform — Target < 20 min**

```bash
# Automated APIM backup (runs daily via Azure Automation)
az apim backup \
  --name apim-genai-copilot-prod-eastus2 \
  --resource-group rg-genai-copilot-prod-eastus2 \
  --storage-account-name stgenaibackups \
  --storage-account-container apim-backups \
  --blob-name "apim-backup-$(date +%Y%m%d).blob" \
  --storage-account-key "${STORAGE_KEY}"

# Restore to DR instance
az apim restore \
  --name apim-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --storage-account-name stgenaibackups \
  --storage-account-container apim-backups \
  --blob-name "apim-backup-latest.blob" \
  --storage-account-key "${STORAGE_KEY}"
```

---

## 10. Data Backlog Handling During Failover

### 10.1 Message Queue Backlog Strategy

During failover, incoming requests and data events may be queued or lost. The following strategy ensures **zero data loss** for critical operations.

```
FAILOVER WINDOW (t=0 to t=30min)
─────────────────────────────────────────────────────────────
│                                                           │
│  Incoming API Requests:                                   │
│  ┌─────────────┐     ┌──────────────────────┐            │
│  │ Front Door  │────►│ Returns 503 / queues  │            │
│  │ (detects    │     │ in retry buffer       │            │
│  │  failure)   │     │ Client retries w/     │            │
│  └─────────────┘     │ exponential backoff   │            │
│                      └──────────────────────┘            │
│                                                           │
│  Document Ingestion Pipeline:                             │
│  ┌─────────────┐     ┌──────────────────────┐            │
│  │ Service Bus │────►│ Messages persist in   │            │
│  │ (Geo-DR     │     │ paired namespace      │            │
│  │  namespace) │     │ TTL: 7 days           │            │
│  └─────────────┘     │ Processed after DR    │            │
│                      └──────────────────────┘            │
│                                                           │
│  Change Feed Events (Cosmos DB):                          │
│  ┌─────────────┐     ┌──────────────────────┐            │
│  │ Change Feed │────►│ Checkpoint preserved  │            │
│  │ Processor   │     │ Resumes from last     │            │
│  └─────────────┘     │ checkpoint in DR      │            │
│                      └──────────────────────┘            │
─────────────────────────────────────────────────────────────
```

### 10.2 Backlog Processing Priority

| Data Type | Backlog Location | Max Backlog Window | Processing Priority | Handling |
|-----------|-----------------|-------------------|-------------------|----------|
| **Chat requests** | Client retry queue | N/A (real-time) | P0 | Clients retry; no server-side backlog |
| **Document ingestion** | Service Bus (Geo-DR) | 7 days TTL | P1 | Process after DR stabilization |
| **Embeddings generation** | Cosmos DB change feed | Unlimited (checkpoint) | P2 | Resume from last checkpoint |
| **Audit logs** | Event Hub buffer | 7 days retention | P3 | Replay after recovery |
| **Analytics events** | Event Grid dead-letter | 24 hours | P3 | Re-emit from dead-letter queue |

### 10.3 Post-Failover Backlog Drain

```bash
# Check Service Bus backlog depth
az servicebus queue show \
  --name document-ingestion \
  --namespace-name sb-genai-copilot-dr-centralus \
  --resource-group rg-genai-copilot-dr-centralus \
  --query "{ActiveMessages:countDetails.activeMessageCount, DeadLetter:countDetails.deadLetterMessageCount}" \
  --output table

# Monitor Cosmos DB change feed lag (Kusto query)
```

```kusto
// Query: Change Feed Processor Lag (Log Analytics)
let ChangeFeedLag = AppMetrics
| where Name == "ChangeFeedProcessorLag"
| where TimeGenerated > ago(1h)
| summarize AvgLag=avg(Sum), MaxLag=max(Sum) by bin(TimeGenerated, 5m), Properties["PartitionId"]
| order by TimeGenerated desc;
ChangeFeedLag
```

---

## 11. Recovery Validation Tests

### 11.1 Post-Failover Validation Checklist

| # | Validation Test | Method | Expected Result | Pass/Fail |
|---|----------------|--------|-----------------|-----------|
| 1 | **API health endpoint** | `GET /health` | HTTP 200 + all dependencies green | ☐ |
| 2 | **RAG pipeline end-to-end** | Submit test query | Valid AI response within 5s | ☐ |
| 3 | **Cosmos DB read/write** | CRUD test on `chat-sessions` | Successful operations, < 50ms latency | ☐ |
| 4 | **AI Search query** | Vector search on test embedding | Returns relevant results, > 0 hits | ☐ |
| 5 | **Azure OpenAI inference** | GPT-4o completion request | Valid response, < 3s latency | ☐ |
| 6 | **Storage blob read** | Download test document | Successful, file integrity verified | ☐ |
| 7 | **Key Vault secret access** | Read application secrets | All secrets accessible | ☐ |
| 8 | **Redis cache operations** | GET/SET test keys | Successful, < 5ms latency | ☐ |
| 9 | **Authentication flow** | OAuth token acquisition via Entra ID | Valid token issued | ☐ |
| 10 | **APIM rate limiting** | Test throttling policy | Rate limit headers present | ☐ |
| 11 | **Document ingestion pipeline** | Upload test PDF | Processing completes, indexed in AI Search | ☐ |
| 12 | **WebSocket/streaming** | Streaming chat response | Tokens stream correctly | ☐ |
| 13 | **Monitoring & alerts** | Trigger test alert | Alert fires and reaches PagerDuty | ☐ |
| 14 | **DNS resolution** | nslookup api endpoint | Resolves to secondary region IP | ☐ |
| 15 | **TLS certificate** | Verify SSL cert chain | Valid certificate, no warnings | ☐ |

### 11.2 Automated Validation Script

```bash
#!/bin/bash
# DR Validation Script — run after failover completion
# Usage: ./scripts/dr-validate.sh --region centralus

REGION="${1:-centralus}"
API_BASE="https://api-dr.genai-copilot.enterprise.com"
PASS=0
FAIL=0

echo "========================================="
echo " DR Validation Suite — Region: ${REGION}"
echo " Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "========================================="

# Test 1: Health endpoint
echo -n "[TEST 1] Health endpoint... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health")
if [ "$STATUS" == "200" ]; then echo "PASS"; ((PASS++)); else echo "FAIL (HTTP $STATUS)"; ((FAIL++)); fi

# Test 2: RAG query
echo -n "[TEST 2] RAG pipeline... "
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/v1/chat" \
  -H "Authorization: Bearer ${DR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the platform architecture?","session_id":"dr-val-001"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "200" ]; then echo "PASS"; ((PASS++)); else echo "FAIL (HTTP $HTTP_CODE)"; ((FAIL++)); fi

# Test 3: Cosmos DB connectivity
echo -n "[TEST 3] Cosmos DB... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health/cosmos")
if [ "$STATUS" == "200" ]; then echo "PASS"; ((PASS++)); else echo "FAIL (HTTP $STATUS)"; ((FAIL++)); fi

# Test 4: AI Search
echo -n "[TEST 4] AI Search... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health/search")
if [ "$STATUS" == "200" ]; then echo "PASS"; ((PASS++)); else echo "FAIL (HTTP $STATUS)"; ((FAIL++)); fi

# Test 5: DNS resolution
echo -n "[TEST 5] DNS resolution... "
RESOLVED_IP=$(dig +short "${API_BASE#https://}" | head -1)
if [ -n "$RESOLVED_IP" ]; then echo "PASS (${RESOLVED_IP})"; ((PASS++)); else echo "FAIL"; ((FAIL++)); fi

# Test 6: TLS certificate
echo -n "[TEST 6] TLS certificate... "
CERT_VALID=$(echo | openssl s_client -connect "${API_BASE#https://}:443" 2>/dev/null | openssl x509 -noout -checkend 86400 2>/dev/null && echo "valid" || echo "invalid")
if [ "$CERT_VALID" == "valid" ]; then echo "PASS"; ((PASS++)); else echo "FAIL"; ((FAIL++)); fi

echo ""
echo "========================================="
echo " Results: ${PASS} passed, ${FAIL} failed"
echo "========================================="
exit $FAIL
```

---

## 12. Post-Recovery Verification Checklist

### 12.1 Immediate Post-Failover (0-60 minutes)

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Confirm all P0 services operational in secondary | Platform Ops | ☐ |
| 2 | Verify data consistency — Cosmos DB write region = Central US | Data Team | ☐ |
| 3 | Confirm AI Search index rebuild complete (100% documents) | AI/ML Team | ☐ |
| 4 | Validate all API endpoints responding correctly | QA Team | ☐ |
| 5 | Confirm monitoring and alerting operational in DR region | Platform Ops | ☐ |
| 6 | Verify DNS resolution points to secondary region | Network Team | ☐ |
| 7 | Run automated DR validation script (Section 11.2) | DevOps Team | ☐ |
| 8 | Update incident status page to "Operational (DR)" | Incident Commander | ☐ |

### 12.2 Stabilization Phase (1-24 hours)

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Process message backlog from Service Bus | Data Team | ☐ |
| 2 | Verify change feed processors resumed and caught up | Data Team | ☐ |
| 3 | Monitor error rates and latency (target: < 2x normal) | Platform Ops | ☐ |
| 4 | Confirm autoscaling policies active and functioning | Platform Ops | ☐ |
| 5 | Verify RBAC and access controls in DR region | Security Team | ☐ |
| 6 | Test backup/restore procedures for DR region | DevOps Team | ☐ |
| 7 | Validate cost monitoring for DR resource consumption | FinOps Team | ☐ |

### 12.3 Failback Planning (24-72 hours)

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Monitor primary region recovery status on Azure Status | Platform Ops | ☐ |
| 2 | Re-establish Cosmos DB replication to primary | Data Team | ☐ |
| 3 | Re-configure Storage RA-GRS (new primary → old primary) | Data Team | ☐ |
| 4 | Plan failback window (off-peak hours) | Incident Commander | ☐ |
| 5 | Execute failback runbook (reverse of Section 6.2) | All Teams | ☐ |
| 6 | Verify primary region fully operational | Platform Ops | ☐ |
| 7 | Re-enable geo-replication for Redis | Data Team | ☐ |
| 8 | Rebuild AI Search indexes in primary | AI/ML Team | ☐ |
| 9 | Conduct post-incident review (PIR) | All Stakeholders | ☐ |

---

## 13. Communication Plan

### 13.1 DR Communication Matrix

| Audience | Notification Method | Timing | Responsible |
|----------|-------------------|--------|-------------|
| **Platform Team (On-Call)** | PagerDuty + SMS | T+0 min (immediate) | Automated alert |
| **Incident Commander** | PagerDuty escalation | T+2 min | Platform Ops |
| **Engineering Leadership** | Teams + Email | T+5 min | Incident Commander |
| **Product Management** | Email + Status Page | T+10 min | Incident Commander |
| **Executive Stakeholders** | Email summary | T+15 min | Engineering Director |
| **End Users (Internal)** | Status Page banner | T+10 min | Communications Lead |
| **External Partners (if any)** | Email notification | T+30 min | Partner Relations |

### 13.2 Communication Templates

**Template 1 — Initial DR Activation Notice:**

```
SUBJECT: [P1 INCIDENT] DR Activation — Azure OpenAI Platform — {REGION} Outage

STATUS: DR FAILOVER IN PROGRESS
TIME DETECTED: {YYYY-MM-DD HH:MM UTC}
INCIDENT COMMANDER: {NAME}

IMPACT:
- Azure OpenAI Enterprise RAG Platform experiencing service disruption
  in {PRIMARY_REGION}
- DR failover to {SECONDARY_REGION} initiated
- Estimated time to restore: {ETA} minutes

AFFECTED SERVICES:
- AI Chat / RAG pipeline
- Document ingestion
- API endpoints

CURRENT ACTIONS:
- Automated DNS failover triggered via Front Door
- Data services failing over to secondary region
- Compute services scaling up in DR region

NEXT UPDATE: {TIME + 15 MIN}
BRIDGE CALL: {TEAMS_LINK}
STATUS PAGE: https://status.genai-copilot.enterprise.com
```

**Template 2 — DR Failover Complete:**

```
SUBJECT: [RESOLVED] DR Failover Complete — Platform Operational in {DR_REGION}

STATUS: OPERATIONAL (DR MODE)
FAILOVER COMPLETED: {YYYY-MM-DD HH:MM UTC}
TOTAL DOWNTIME: {MINUTES} minutes

SUMMARY:
- Platform is fully operational in {DR_REGION}
- All P0 and P1 services restored
- Data integrity confirmed — no data loss detected

REMAINING ACTIONS:
- AI Search index rebuild: {PERCENT}% complete (ETA: {TIME})
- Message backlog processing in progress
- Primary region recovery monitoring

POST-INCIDENT REVIEW: Scheduled for {DATE}
```

**Template 3 — Failback Complete:**

```
SUBJECT: [INFO] Failback Complete — Platform Restored to Primary Region

STATUS: FULLY OPERATIONAL (PRIMARY)
FAILBACK COMPLETED: {YYYY-MM-DD HH:MM UTC}

SUMMARY:
- Platform restored to primary region ({PRIMARY_REGION})
- All services operational at full capacity
- DR region returned to standby mode
- Geo-replication re-established

POST-INCIDENT REVIEW: {DATE} at {TIME}
INCIDENT REPORT: {LINK}
```

---

## 14. DR Drill Schedule and Procedure

### 14.1 Quarterly DR Drill Calendar

| Quarter | Drill Date | Drill Type | Scope | Duration | Lead |
|---------|-----------|------------|-------|----------|------|
| **Q1** | January (3rd Saturday) | **Tabletop Exercise** | Full platform — walkthrough only | 2 hours | Platform Lead |
| **Q2** | April (3rd Saturday) | **Partial Failover** | Data tier only (Cosmos DB, Storage, Redis) | 4 hours | Data Team Lead |
| **Q3** | July (3rd Saturday) | **Full DR Failover** | Complete regional failover to Central US | 6 hours | Incident Commander |
| **Q4** | October (3rd Saturday) | **Chaos Engineering** | Random service failures + automated recovery | 4 hours | SRE Lead |

### 14.2 DR Drill Procedure

**Phase 1 — Preparation (1 week before)**

| # | Task | Owner |
|---|------|-------|
| 1 | Schedule maintenance window and notify stakeholders | DR Lead |
| 2 | Verify DR infrastructure is provisioned and healthy | Platform Ops |
| 3 | Confirm runbooks are up to date | DevOps Team |
| 4 | Pre-stage deployment artifacts in DR region | DevOps Team |
| 5 | Brief all participating teams on drill objectives | DR Lead |
| 6 | Notify Azure support of planned DR drill | Platform Ops |

**Phase 2 — Execution**

| # | Task | Duration | Success Criteria |
|---|------|----------|-----------------|
| 1 | Simulate primary region failure (disable Traffic Manager endpoint) | 5 min | DNS routes to secondary |
| 2 | Execute failover runbook (Section 6.2) | 30 min | All steps complete |
| 3 | Run validation tests (Section 11) | 15 min | All tests pass |
| 4 | Operate in DR mode — execute synthetic workload | 60 min | < 5% error rate, P99 < 2x normal |
| 5 | Execute failback procedure | 30 min | Primary region restored |
| 6 | Run validation tests on primary | 15 min | All tests pass |
| 7 | Restore geo-replication | 15 min | Replication healthy |

**Phase 3 — Post-Drill Review**

| # | Task | Owner |
|---|------|-------|
| 1 | Collect drill metrics (RTO actual vs target, RPO actual vs target) | Platform Ops |
| 2 | Document issues encountered and lessons learned | All Teams |
| 3 | Update runbooks based on findings | DevOps Team |
| 4 | File DR drill results report (Section 15) | DR Lead |
| 5 | Track remediation items to completion | DR Lead |

### 14.3 DR Drill Simulation Commands

```bash
# Simulate primary region failure by disabling Traffic Manager endpoint
az network traffic-manager endpoint update \
  --name ep-primary-eastus2 \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --endpoint-status Disabled

# Verify traffic routes to secondary
dig genai-copilot-prod.trafficmanager.net +short

# After drill — re-enable primary endpoint
az network traffic-manager endpoint update \
  --name ep-primary-eastus2 \
  --profile-name tm-genai-copilot-prod \
  --resource-group rg-genai-copilot-global \
  --type azureEndpoints \
  --endpoint-status Enabled
```

---

## 15. DR Testing Results Log Template

### 15.1 Drill Summary Report

```
╔══════════════════════════════════════════════════════════════════╗
║              DR DRILL RESULTS REPORT                            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Drill ID:        DR-{YYYY}-Q{N}-{SEQ}                         ║
║  Date:            {YYYY-MM-DD}                                  ║
║  Type:            {Tabletop | Partial | Full | Chaos}           ║
║  Duration:        {HH:MM} (planned) / {HH:MM} (actual)         ║
║  Lead:            {NAME}                                        ║
║  Participants:    {COUNT} across {N} teams                      ║
║                                                                  ║
║  PRIMARY REGION:  East US 2                                     ║
║  DR REGION:       Central US                                    ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  RECOVERY METRICS                                                ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Platform RTO Target:   30 min    Actual:  {XX} min    {P/F}   ║
║  Platform RPO Target:   5 min     Actual:  {XX} min    {P/F}   ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  SERVICE-LEVEL RESULTS                                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Service            RTO Tgt  RTO Act  RPO Tgt  RPO Act   Result ║
║  ─────────────────  ───────  ───────  ───────  ───────  ─────── ║
║  Azure OpenAI       15 min   ___ min  0 min    ___ min  {P/F}  ║
║  Cosmos DB          10 min   ___ min  5 min    ___ min  {P/F}  ║
║  AI Search          30 min   ___ min  15 min   ___ min  {P/F}  ║
║  AKS                15 min   ___ min  0 min    ___ min  {P/F}  ║
║  Functions          10 min   ___ min  0 min    ___ min  {P/F}  ║
║  Storage            5 min    ___ min  15 min   ___ min  {P/F}  ║
║  Key Vault          5 min    ___ min  0 min    ___ min  {P/F}  ║
║  APIM               20 min   ___ min  0 min    ___ min  {P/F}  ║
║  Redis Cache        15 min   ___ min  1 min    ___ min  {P/F}  ║
║  App Gateway        15 min   ___ min  0 min    ___ min  {P/F}  ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  VALIDATION TESTS                                                ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Total Tests:    15       Passed: ___    Failed: ___            ║
║  Pass Rate:      ___%                                            ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  ISSUES & OBSERVATIONS                                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  1. {Issue description}                                          ║
║     Severity: {Critical|High|Medium|Low}                        ║
║     Remediation: {Action item}                                  ║
║     Owner: {Team/Person}                                        ║
║     Due: {Date}                                                 ║
║                                                                  ║
║  2. {Issue description}                                          ║
║     ...                                                          ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  SIGN-OFF                                                        ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  DR Lead:           ________________  Date: __________          ║
║  Platform Lead:     ________________  Date: __________          ║
║  Engineering Dir:   ________________  Date: __________          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### 15.2 Historical Drill Results Tracking

| Drill ID | Date | Type | RTO Target | RTO Actual | RPO Target | RPO Actual | Pass Rate | Issues Found |
|----------|------|------|-----------|-----------|-----------|-----------|-----------|-------------|
| DR-2024-Q1-001 | 2024-01-20 | Tabletop | 30 min | N/A | 5 min | N/A | N/A | 3 |
| DR-2024-Q2-001 | 2024-04-20 | Partial | 30 min | 22 min | 5 min | 3 min | 93% | 2 |
| DR-2024-Q3-001 | 2024-07-20 | Full | 30 min | — | 5 min | — | — | — |
| DR-2024-Q4-001 | 2024-10-19 | Chaos | 30 min | — | 5 min | — | — | — |

### 15.3 Kusto Query — DR Metrics Dashboard

```kusto
// DR Drill Performance Trend (Log Analytics)
let DrillMetrics = customEvents
| where name == "DRDrillResult"
| extend DrillId = tostring(customDimensions["DrillId"]),
         RtoTarget = toint(customDimensions["RtoTargetMin"]),
         RtoActual = toint(customDimensions["RtoActualMin"]),
         RpoTarget = toint(customDimensions["RpoTargetMin"]),
         RpoActual = toint(customDimensions["RpoActualMin"]),
         PassRate = todouble(customDimensions["ValidationPassRate"])
| project timestamp, DrillId, RtoTarget, RtoActual, RpoTarget, RpoActual, PassRate
| order by timestamp desc;
DrillMetrics
| render timechart
```

---

## 16. Cost of DR Infrastructure

### 16.1 DR Cost Summary by Strategy

| Strategy | Services | Monthly Cost (Est.) | % of Production | Justification |
|----------|----------|-------------------|-----------------|---------------|
| **Hot Standby** | Cosmos DB, Storage, Key Vault, Redis, ACR | $2,450 | 40% | Continuous replication; near-zero RTO for data |
| **Warm Standby** | AKS (2 nodes), App Gateway, APIM | $1,680 | 25% | Infrastructure running but scaled down |
| **Cold Standby** | Functions, Doc Intelligence, Content Safety | $85 | < 5% | No running cost; deploy on demand |
| **Rebuild** | AI Search (S2, 1 replica) | $720 | 30% of primary Search | Standby index; rebuilt on failover |
| **Global (No DR Cost)** | Front Door, Traffic Manager, Entra ID, Defender | $0 (included) | 0% | Microsoft-managed global services |
| **DR Automation** | Azure Automation, runbooks, monitoring | $45 | < 1% | DR orchestration overhead |

### 16.2 Detailed Monthly DR Cost Breakdown

| Service | SKU (DR) | DR Configuration | Monthly Cost |
|---------|----------|-----------------|-------------|
| **Cosmos DB** | Autoscale (400-4000 RU/s) | Multi-region write (Central US replica) | $680 |
| **Azure Storage** | Standard RA-GRS | Geo-redundant read-access | $120 |
| **Azure Cache for Redis** | Premium P1 | Geo-secondary (6 GB) | $410 |
| **Azure Container Registry** | Premium | Geo-replication to Central US | $140 |
| **Azure AI Search** | S2 (1 replica) | Standby index | $720 |
| **Azure Kubernetes Service** | Standard_D4s_v3 x2 | Warm standby (2 nodes) | $560 |
| **Application Gateway** | WAF_v2 | Warm standby (scaled down) | $380 |
| **API Management** | Developer | DR instance (upgrade to Standard on failover) | $150 |
| **Azure OpenAI** | Pay-as-you-go | Secondary deployment (no idle cost) | $0 |
| **Azure Functions** | Consumption | No idle cost | $0 |
| **Virtual Network + NSGs** | Standard | Pre-provisioned in Central US | $15 |
| **Private Endpoints** | Standard | 8 endpoints in DR region | $60 |
| **Private DNS Zones** | Standard | DR region zones | $5 |
| **Azure Monitor (DR)** | Standard | Secondary Log Analytics workspace | $85 |
| **Azure Automation** | Basic | DR runbooks, schedules | $45 |
| **Key Vault** | Premium | Geo-replicated (managed by Azure) | $30 |
| **Service Bus** | Standard | Geo-DR paired namespace | $30 |
| **Event Grid** | Standard | Multi-region subscriptions | $5 |
| **Azure Bastion** | Standard | Deploy on-demand only | $0 |
| **DDoS Protection** | Standard | Shared plan (no additional cost) | $0 |
| | | | |
| | | **Total DR Monthly Cost** | **$3,435** |

### 16.3 Cost Comparison: Hot vs Warm vs Cold

```
DR Strategy Cost Comparison (Monthly)
═══════════════════════════════════════════════════════════════

Hot Standby (Full Active-Active)
├── All services running at production scale in DR
├── Monthly Cost: ~$9,800
├── RTO: < 5 min (automatic)
└── ██████████████████████████████████████████████████ $9,800

Current Strategy (Hot Data + Warm Compute)
├── Data replicated hot, compute scaled down
├── Monthly Cost: ~$3,435
├── RTO: < 30 min (semi-automated)
└── █████████████████                                 $3,435

Cold Standby (Terraform-Only)
├── No running resources, deploy from IaC on demand
├── Monthly Cost: ~$150
├── RTO: 60-90 min (fully manual)
└── █                                                 $150

Production Reference
├── Full production infrastructure
├── Monthly Cost: ~$13,909
└── ████████████████████████████████████████████████████████████████████████ $13,909
```

### 16.4 DR Cost as Percentage of Production

| Metric | Value |
|--------|-------|
| **Production monthly cost** | $13,909 |
| **DR monthly cost (current strategy)** | $3,435 |
| **DR as % of production** | 24.7% |
| **Annual DR cost** | $41,220 |
| **Cost per hour of avoided downtime** (based on $50K/hr business impact) | $3,435 / ~720 hrs = $4.77/hr |

---

## Appendix A: Key Contacts

| Role | Name | Contact | Escalation Order |
|------|------|---------|-----------------|
| **Incident Commander (Primary)** | {Name} | PagerDuty + Mobile | 1st |
| **Incident Commander (Backup)** | {Name} | PagerDuty + Mobile | 2nd |
| **Platform Ops Lead** | {Name} | PagerDuty | 1st |
| **Data Team Lead** | {Name} | PagerDuty | 1st |
| **AI/ML Team Lead** | {Name} | PagerDuty | 1st |
| **Network Team Lead** | {Name} | PagerDuty | 1st |
| **Security (CISO)** | {Name} | Phone + Email | As needed |
| **Engineering Director** | {Name} | Email + Phone | T+15 min |
| **Azure Support** | N/A | Premier Support (Sev A) | As needed |

---

## Appendix B: Related Documents

| Document | Location | Relevance |
|----------|----------|-----------|
| Infrastructure & DevOps Guide | `docs/operations/INFRA-DEVOPS-DEPLOYMENT.md` | Service inventory, Terraform modules |
| Security & Compliance | `docs/security/SECURITY-COMPLIANCE.md` | Security controls during DR |
| Operations Guide | `docs/operations/OPERATIONS-GUIDE.md` | Monitoring, alerting, incident management |
| FinOps & Cost Management | `docs/operations/FINOPS-COST-MANAGEMENT.md` | Cost tracking during DR mode |
| Architecture Guide | `docs/architecture/ARCHITECTURE-GUIDE.md` | Platform architecture reference |
| Data Privacy & Compliance | `docs/security/DATA-PRIVACY-COMPLIANCE.md` | Data handling during failover |

---

## Document Control

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Review Cycle** | Quarterly (aligned with DR drills) |
| **Approval** | Engineering Director, CISO |
| **Distribution** | Platform Ops, Data Team, AI/ML Team, DevOps, Security, SRE |
| **Change Log** | v1.0 — Initial DR plan covering 29 Azure services |
