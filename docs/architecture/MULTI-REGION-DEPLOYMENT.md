# Multi-Region Deployment — Azure OpenAI Enterprise RAG Platform

> Global resilience, data residency enforcement, and latency-optimized routing for enterprise AI workloads — aligned with CMMI Level 3 | ISO/IEC 42001 | NIST AI RMF.

---

## Table of Contents

1. [Architecture Decision Record: Active-Active vs Active-Passive](#1-architecture-decision-record-active-active-vs-active-passive)
2. [Global Traffic Routing: Azure Front Door](#2-global-traffic-routing-azure-front-door)
3. [Data Replication: Cosmos DB Multi-Region](#3-data-replication-cosmos-db-multi-region)
4. [Search Index Synchronization](#4-search-index-synchronization)
5. [Session Affinity and Sticky Routing](#5-session-affinity-and-sticky-routing)
6. [Conflict Resolution for Multi-Writer Cosmos DB](#6-conflict-resolution-for-multi-writer-cosmos-db)
7. [Latency-Based Routing Configuration](#7-latency-based-routing-configuration)
8. [Regional Data Residency Enforcement](#8-regional-data-residency-enforcement)
9. [Cost of Multi-Region Deployment](#9-cost-of-multi-region-deployment)
10. [Migration Path: Single to Multi-Region](#10-migration-path-single-to-multi-region)
11. [Regional Failover Testing](#11-regional-failover-testing)
12. [Multi-Region Terraform Structure](#12-multi-region-terraform-structure)
13. [DNS and Certificate Management](#13-dns-and-certificate-management)
14. [Monitoring: Per-Region Dashboards](#14-monitoring-per-region-dashboards)
15. [Multi-Region AI Search Strategy](#15-multi-region-ai-search-strategy)

---

## 1. Architecture Decision Record: Active-Active vs Active-Passive

### ADR-007: Multi-Region Topology Selection

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2024-01-15 |
| **Deciders** | Platform Team, SRE Lead, Security Architect |
| **Category** | Architecture / Resilience |

### Context

The Enterprise RAG platform serves users across North America and Europe. Requirements include:

- **RTO < 5 minutes** for Tier-1 workloads (real-time RAG queries)
- **RPO < 1 minute** for conversation history and user state
- **GDPR compliance** requiring EU data to remain in EU regions
- **P95 latency < 800ms** for end-to-end RAG responses globally
- **99.99% SLA** contractual obligation

### Options Evaluated

| Criteria | Active-Active | Active-Passive | Active-Active (Regional Scope) |
|----------|--------------|----------------|-------------------------------|
| **RTO** | ~0 (instant failover) | 2–10 minutes | ~0 within scope |
| **RPO** | ~0 (multi-write) | 1–5 min (async replication) | ~0 within scope |
| **Complexity** | High | Medium | Medium-High |
| **Cost multiplier** | 2.0–2.3x | 1.3–1.5x | 1.7–2.0x |
| **Data residency** | Complex (requires geo-fencing) | Simpler (single primary) | Natural fit |
| **Conflict resolution** | Required | Not needed | Scoped per region |
| **Latency** | Optimal (local reads/writes) | Cold-start on failover | Optimal per region |

### Decision

**Active-Active with Regional Scope** — each region operates as a full-stack deployment handling both reads and writes for its geo-fenced user base. Cross-region replication is limited to shared configuration and global analytics.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DECISION: REGIONAL ACTIVE-ACTIVE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────┐          ┌──────────────────────┐                │
│   │   REGION: East US    │          │   REGION: West Europe│                │
│   │   ┌────────────────┐ │          │   ┌────────────────┐ │                │
│   │   │ AKS Cluster    │ │          │   │ AKS Cluster    │ │                │
│   │   │ OpenAI Service │ │   Async  │   │ OpenAI Service │ │                │
│   │   │ AI Search      │◄├─── ── ──┤►  │ AI Search      │ │                │
│   │   │ Cosmos DB      │ │  Repl.   │   │ Cosmos DB      │ │                │
│   │   │ Redis Cache    │ │          │   │ Redis Cache    │ │                │
│   │   └────────────────┘ │          │   └────────────────┘ │                │
│   │   Scope: US users    │          │   Scope: EU users    │                │
│   └──────────────────────┘          └──────────────────────┘                │
│                                                                             │
│   Shared Global: Azure Front Door, DNS, Certificates, Terraform State      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Consequences

| Consequence | Impact | Mitigation |
|-------------|--------|------------|
| **Positive:** Near-zero RTO/RPO | Eliminates cold-start failover penalty | — |
| **Positive:** Natural data residency | EU data never leaves EU regions | — |
| **Negative:** Higher cost | ~1.8x single-region cost | FinOps optimization, reserved instances |
| **Negative:** Index sync complexity | Search indexes must stay consistent | Event-driven rebuild with staleness tolerance |
| **Negative:** Operational overhead | Two full stacks to manage | IaC parity enforced via Terraform modules |

---

## 2. Global Traffic Routing: Azure Front Door

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GLOBAL TRAFFIC ROUTING                                │
│                                                                                 │
│                          ┌─────────────────────┐                                │
│                          │   Client Request     │                                │
│                          │  rag.company.com     │                                │
│                          └─────────┬───────────┘                                │
│                                    │                                            │
│                                    ▼                                            │
│                    ┌───────────────────────────────┐                             │
│                    │      AZURE FRONT DOOR         │                             │
│                    │   (Global Load Balancer)       │                             │
│                    │                               │                             │
│                    │  ┌─────────────────────────┐  │                             │
│                    │  │    WAF Policy (OWASP)   │  │                             │
│                    │  │    Rate Limiting         │  │                             │
│                    │  │    Geo-Filtering         │  │                             │
│                    │  └─────────────────────────┘  │                             │
│                    │                               │                             │
│                    │  ┌─────────────────────────┐  │                             │
│                    │  │   ROUTING ENGINE         │  │                             │
│                    │  │                         │  │                             │
│                    │  │  1. Geo-match (data res.)│  │                             │
│                    │  │  2. Latency-based        │  │                             │
│                    │  │  3. Weighted fallback     │  │                             │
│                    │  └──────────┬──────────────┘  │                             │
│                    └─────────────┼─────────────────┘                             │
│                          ┌───────┴────────┐                                     │
│                          │                │                                     │
│                  ┌───────▼──────┐  ┌──────▼───────┐                             │
│                  │  ORIGIN      │  │  ORIGIN      │                             │
│                  │  GROUP: US   │  │  GROUP: EU   │                             │
│                  │              │  │              │                             │
│                  │ ┌──────────┐ │  │ ┌──────────┐ │                             │
│                  │ │ East US  │ │  │ │West EUR  │ │                             │
│                  │ │ AKS LB   │ │  │ │ AKS LB   │ │                             │
│                  │ │ (Primary)│ │  │ │ (Primary)│ │                             │
│                  │ └──────────┘ │  │ └──────────┘ │                             │
│                  │ ┌──────────┐ │  │ ┌──────────┐ │                             │
│                  │ │ West US  │ │  │ │North EUR │ │                             │
│                  │ │ AKS LB   │ │  │ │ AKS LB   │ │                             │
│                  │ │(Failover)│ │  │ │(Failover)│ │                             │
│                  │ └──────────┘ │  │ └──────────┘ │                             │
│                  └──────────────┘  └──────────────┘                             │
│                                                                                 │
│  Health Probes: GET /healthz every 30s │ Timeout: 5s │ Threshold: 3 failures    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Azure Front Door Terraform Configuration

```terraform
# ──────────────────────────────────────────────────────────────────
# Azure Front Door — Global Traffic Manager
# ──────────────────────────────────────────────────────────────────

resource "azurerm_cdn_frontdoor_profile" "rag_platform" {
  name                = "fd-rag-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.global.name
  sku_name            = "Premium_AzureFrontDoor"

  tags = local.common_tags
}

# ── Origin Groups ────────────────────────────────────────────────

resource "azurerm_cdn_frontdoor_origin_group" "us_origins" {
  name                     = "og-us-rag-api"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.rag_platform.id
  session_affinity_enabled = false

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
    additional_latency_in_milliseconds = 50
  }

  health_probe {
    path                = "/healthz"
    protocol            = "Https"
    interval_in_seconds = 30
    request_type        = "GET"
  }
}

resource "azurerm_cdn_frontdoor_origin_group" "eu_origins" {
  name                     = "og-eu-rag-api"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.rag_platform.id
  session_affinity_enabled = false

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
    additional_latency_in_milliseconds = 50
  }

  health_probe {
    path                = "/healthz"
    protocol            = "Https"
    interval_in_seconds = 30
    request_type        = "GET"
  }
}

# ── Origins ──────────────────────────────────────────────────────

resource "azurerm_cdn_frontdoor_origin" "eastus_aks" {
  name                          = "origin-eastus-aks"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.us_origins.id
  enabled                       = true

  host_name          = module.aks_eastus.ingress_fqdn
  http_port          = 80
  https_port         = 443
  origin_host_header = module.aks_eastus.ingress_fqdn
  priority           = 1
  weight             = 1000
  certificate_name_check_enabled = true

  private_link {
    location               = "eastus"
    private_link_target_id = module.aks_eastus.private_link_service_id
    request_message        = "Front Door PLS"
  }
}

resource "azurerm_cdn_frontdoor_origin" "westeurope_aks" {
  name                          = "origin-westeurope-aks"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.eu_origins.id
  enabled                       = true

  host_name          = module.aks_westeurope.ingress_fqdn
  http_port          = 80
  https_port         = 443
  origin_host_header = module.aks_westeurope.ingress_fqdn
  priority           = 1
  weight             = 1000
  certificate_name_check_enabled = true

  private_link {
    location               = "westeurope"
    private_link_target_id = module.aks_westeurope.private_link_service_id
    request_message        = "Front Door PLS"
  }
}

# ── Routing Rules ────────────────────────────────────────────────

resource "azurerm_cdn_frontdoor_route" "us_route" {
  name                          = "route-us-api"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.rag_api.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.us_origins.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.eastus_aks.id]

  supported_protocols    = ["Https"]
  patterns_to_match      = ["/api/*"]
  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true

  cdn_frontdoor_rule_set_ids = [
    azurerm_cdn_frontdoor_rule_set.geo_routing.id
  ]
}

# ── Geo-Routing Rule Set ─────────────────────────────────────────

resource "azurerm_cdn_frontdoor_rule_set" "geo_routing" {
  name                     = "GeoRoutingRules"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.rag_platform.id
}

resource "azurerm_cdn_frontdoor_rule" "eu_geo_override" {
  name                      = "RouteEUTraffic"
  cdn_frontdoor_rule_set_id = azurerm_cdn_frontdoor_rule_set.geo_routing.id
  order                     = 1

  conditions {
    remote_address_condition {
      operator = "GeoMatch"
      match_values = [
        "DE", "FR", "NL", "IT", "ES", "BE", "AT",
        "IE", "PT", "FI", "SE", "DK", "PL", "CZ"
      ]
    }
  }

  actions {
    route_configuration_override_action {
      cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.eu_origins.id
    }
  }
}
```

### Front Door Routing Decision Matrix

| Traffic Source | Routing Rule | Primary Origin | Failover Origin | Data Residency |
|---------------|-------------|----------------|-----------------|----------------|
| **US / Canada** | Latency-based | East US AKS | West US AKS | US data stays in US |
| **EU (GDPR)** | Geo-match override | West Europe AKS | North Europe AKS | EU data stays in EU |
| **APAC** | Latency-based | East US AKS | West Europe AKS | No restriction |
| **Other** | Latency-based | Nearest healthy origin | Next-nearest | No restriction |

---

## 3. Data Replication: Cosmos DB Multi-Region

### Consistency Level Trade-offs

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 COSMOS DB CONSISTENCY SPECTRUM                          │
│                                                                         │
│  ◄──────────────────────────────────────────────────────────────────►   │
│  STRONG            BOUNDED      SESSION      CONSISTENT    EVENTUAL    │
│                    STALENESS                  PREFIX                    │
│                                                                         │
│  ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌──────────┐ │
│  │Lineariz- │   │Bounded   │  │Read-your-│  │No out-of-│ │Highest   │ │
│  │able reads│   │lag window│  │own-writes│  │order     │ │throughput│ │
│  │          │   │          │  │          │  │reads     │ │          │ │
│  │Latency:  │   │Latency:  │  │Latency:  │  │Latency:  │ │Latency:  │ │
│  │  HIGH    │   │  MEDIUM  │  │  LOW     │  │  LOW     │ │  LOWEST  │ │
│  │          │   │          │  │          │  │          │ │          │ │
│  │Cost:     │   │Cost:     │  │Cost:     │  │Cost:     │ │Cost:     │ │
│  │  2x RU   │   │  2x RU   │  │  1x RU   │  │  1x RU   │ │  1x RU   │ │
│  └──────────┘   └──────────┘  └──────────┘  └──────────┘ └──────────┘ │
│                                    ▲                                    │
│                                    │                                    │
│                            SELECTED FOR RAG                             │
│                            (Session Consistency)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Consistency Selection per Data Type

| Data Type | Consistency Level | Justification | RU Impact |
|-----------|------------------|---------------|-----------|
| **Conversation history** | Session | User reads own writes; cross-user consistency not needed | 1x RU |
| **User preferences** | Session | Same-user updates; rare cross-region access | 1x RU |
| **Tenant configuration** | Bounded Staleness (5s) | Admin changes must propagate within seconds | 2x RU |
| **Token usage/billing** | Strong | Financial accuracy required; no stale reads | 2x RU |
| **RAG evaluation logs** | Eventual | Analytics workload; staleness acceptable | 1x RU |
| **Audit trail** | Bounded Staleness (10s) | Compliance requires near-real-time propagation | 2x RU |

### Cosmos DB Multi-Region Terraform

```terraform
# ──────────────────────────────────────────────────────────────────
# Cosmos DB — Multi-Region Write Configuration
# ──────────────────────────────────────────────────────────────────

resource "azurerm_cosmosdb_account" "rag_platform" {
  name                = "cosmos-rag-${var.environment}"
  location            = var.primary_region
  resource_group_name = azurerm_resource_group.data.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  # Enable multi-region writes
  enable_multiple_write_locations = true
  enable_automatic_failover       = true

  # Session consistency — balances latency and read-your-own-writes
  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  # Primary region
  geo_location {
    location          = "eastus"
    failover_priority = 0
    zone_redundant    = true
  }

  # Secondary region (EU)
  geo_location {
    location          = "westeurope"
    failover_priority = 1
    zone_redundant    = true
  }

  # Tertiary region (failover)
  geo_location {
    location          = "westus2"
    failover_priority = 2
    zone_redundant    = false
  }

  # Network security
  is_virtual_network_filter_enabled = true
  public_network_access_enabled     = false

  virtual_network_rule {
    id = module.vnet_eastus.cosmosdb_subnet_id
  }

  virtual_network_rule {
    id = module.vnet_westeurope.cosmosdb_subnet_id
  }

  # Backup policy
  backup {
    type                = "Continuous"
    tier                = "Continuous7Days"
  }

  tags = local.common_tags
}

# ── Database and Containers ──────────────────────────────────────

resource "azurerm_cosmosdb_sql_database" "rag_db" {
  name                = "rag-platform"
  resource_group_name = azurerm_resource_group.data.name
  account_name        = azurerm_cosmosdb_account.rag_platform.name
}

resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_resource_group.data.name
  account_name        = azurerm_cosmosdb_account.rag_platform.name
  database_name       = azurerm_cosmosdb_sql_database.rag_db.name

  partition_key_paths = ["/tenantId"]

  autoscale_settings {
    max_throughput = 10000
  }

  # Conflict resolution: last writer wins on _ts
  conflict_resolution_policy {
    mode                          = "LastWriterWins"
    conflict_resolution_path      = "/_ts"
  }

  # TTL for conversation expiry (90 days)
  default_ttl = 7776000

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/tenantId/?"
    }
    included_path {
      path = "/userId/?"
    }
    included_path {
      path = "/createdAt/?"
    }
    excluded_path {
      path = "/messages/*"
    }
  }
}
```

---

## 4. Search Index Synchronization

### Strategy Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│            SEARCH INDEX SYNC: DUAL-WRITE vs EVENT-DRIVEN                │
│                                                                         │
│  OPTION A: DUAL-WRITE                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                           │
│  │ Ingestion│───►│ Index    │───►│ US Search│                           │
│  │ Pipeline │    │ Builder  │    │ Index    │                           │
│  │          │──┐ │          │ ┌─►│          │                           │
│  └──────────┘  │ └──────────┘ │  └──────────┘                           │
│                │              │                                         │
│                │  ┌──────────┐│  ┌──────────┐                           │
│                └─►│ Index    │└─►│ EU Search│                           │
│                   │ Builder  │   │ Index    │                           │
│                   │ (copy)   │   │          │                           │
│                   └──────────┘   └──────────┘                           │
│  Risk: Partial failure leaves indexes inconsistent                      │
│                                                                         │
│  ═══════════════════════════════════════════════════════════════         │
│                                                                         │
│  OPTION B: EVENT-DRIVEN REBUILD  ◄── SELECTED                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Ingestion│───►│ Blob     │───►│ Event    │───►│ US Search│          │
│  │ Pipeline │    │ Storage  │    │ Grid /   │    │ Index    │          │
│  │          │    │ (source  │    │ Service  │ ┌─►│          │          │
│  └──────────┘    │  of truth│    │ Bus      │ │  └──────────┘          │
│                  └──────────┘    │          │ │                         │
│                                  │          │ │  ┌──────────┐          │
│                                  │          │ └─►│ EU Search│          │
│                                  └──────────┘    │ Index    │          │
│                                                  │          │          │
│                                                  └──────────┘          │
│  Benefit: Blob is single source of truth; indexes are derived state     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Staleness Tolerance by Content Type

| Content Type | Max Staleness | Rebuild Trigger | Strategy |
|-------------|---------------|-----------------|----------|
| **Policy documents** | 5 minutes | Blob upload event | Event Grid → indexer run |
| **Knowledge base articles** | 15 minutes | Scheduled + event | Hybrid: event + 15-min sweep |
| **Training materials** | 1 hour | Scheduled rebuild | Hourly indexer schedule |
| **Archived documents** | 24 hours | Daily rebuild | Nightly batch re-index |
| **User-uploaded docs** | 2 minutes | Blob upload event | Priority event queue |

### Event-Driven Index Sync Configuration

```yaml
# Service Bus topic for cross-region index synchronization
apiVersion: servicebus/v1
kind: Topic
metadata:
  name: index-sync-events
spec:
  maxSizeInMegabytes: 5120
  defaultMessageTimeToLive: PT1H
  duplicateDetectionHistoryTimeWindow: PT10M
  enablePartitioning: true

  subscriptions:
    - name: us-search-indexer
      filter:
        sqlExpression: "targetRegion = 'us' OR targetRegion = 'all'"
      maxDeliveryCount: 5
      deadLetterOnExpiration: true

    - name: eu-search-indexer
      filter:
        sqlExpression: "targetRegion = 'eu' OR targetRegion = 'all'"
      maxDeliveryCount: 5
      deadLetterOnExpiration: true
```

---

## 5. Session Affinity and Sticky Routing

### When to Use Session Affinity

```
┌──────────────────────────────────────────────────────────────────────┐
│                 SESSION AFFINITY DECISION TREE                       │
│                                                                      │
│                    ┌─────────────────┐                                │
│                    │ Incoming Request │                                │
│                    └────────┬────────┘                                │
│                             │                                        │
│                    ┌────────▼────────┐                                │
│                    │  Is the API     │                                │
│                    │  stateless?     │                                │
│                    └───┬─────────┬───┘                                │
│                   YES  │         │  NO                                │
│              ┌─────────▼──┐  ┌──▼──────────┐                         │
│              │ No session │  │ Check state  │                         │
│              │ affinity   │  │ storage      │                         │
│              │            │  └──┬───────┬───┘                         │
│              │ Route by:  │     │       │                             │
│              │ - Latency  │  External  In-Memory                     │
│              │ - Geo      │  (Redis/   (WebSocket,                   │
│              │ - Weight   │  Cosmos)   streaming)                    │
│              └────────────┘     │       │                             │
│                          ┌─────▼──┐ ┌──▼──────────┐                  │
│                          │ No     │ │ STICKY       │                  │
│                          │affinity│ │ SESSION      │                  │
│                          │(state  │ │ REQUIRED     │                  │
│                          │ in DB) │ │              │                  │
│                          └────────┘ │ Use cookie:  │                  │
│                                     │ ARRAffinity  │                  │
│                                     └──────────────┘                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Affinity Requirements per Endpoint

| Endpoint | Stateful? | State Location | Affinity Required | Rationale |
|----------|-----------|---------------|-------------------|-----------|
| `POST /api/chat` | No | Cosmos DB (conversation) | **No** | State externalized to Cosmos |
| `GET /api/documents` | No | AI Search index | **No** | Stateless query |
| `WS /api/chat/stream` | Yes | In-memory (WebSocket) | **Yes** | WebSocket connection bound to node |
| `POST /api/upload` | No | Blob Storage | **No** | Upload target is external |
| `GET /api/health` | No | None | **No** | Stateless probe |
| `POST /api/evaluate` | Partial | In-memory (batch job) | **Yes** | Long-running evaluation session |

---

## 6. Conflict Resolution for Multi-Writer Cosmos DB

### Conflict Resolution Strategies

| Strategy | Mechanism | Use Case | Data Loss Risk |
|----------|-----------|----------|---------------|
| **Last-Writer-Wins (LWW)** | Highest `_ts` wins | Conversation messages, logs | Low (append-only data) |
| **Custom Merge Procedure** | Stored procedure resolves | Token budgets, counters | None (merge logic) |
| **Region-Scoped Writes** | Write to home region only | User profiles, tenant config | None (no conflicts) |

### Conflict Resolution by Container

```
┌──────────────────────────────────────────────────────────────────────┐
│              CONFLICT RESOLUTION MAP                                 │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐    │
│  │  conversations     │  │  Strategy: Last-Writer-Wins (_ts)    │    │
│  │  (append-only msgs)│──│  Reason: Messages are immutable once │    │
│  │                    │  │  created; conflicts are rare          │    │
│  └────────────────────┘  └──────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐    │
│  │  token_usage       │  │  Strategy: Custom Merge (sproc)      │    │
│  │  (counters)        │──│  Reason: Counters must be summed,    │    │
│  │                    │  │  not overwritten; merge adds deltas   │    │
│  └────────────────────┘  └──────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐    │
│  │  tenant_config     │  │  Strategy: Region-Scoped Writes      │    │
│  │  (admin-managed)   │──│  Reason: Config changes originate    │    │
│  │                    │  │  from admin portal (single region)    │    │
│  └────────────────────┘  └──────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐    │
│  │  audit_logs        │  │  Strategy: Last-Writer-Wins (_ts)    │    │
│  │  (immutable)       │──│  Reason: Logs are write-once; no     │    │
│  │                    │  │  updates means no real conflicts      │    │
│  └────────────────────┘  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Custom Merge Stored Procedure for Token Counters

```json
{
  "id": "resolveTokenConflict",
  "body": "function resolveTokenConflict(incomingRecord, existingRecord, isTombstone, conflictingRecords) {\n    if (isTombstone) { return; }\n\n    var merged = existingRecord;\n    merged.totalTokensUsed = (existingRecord.totalTokensUsed || 0);\n\n    for (var i = 0; i < conflictingRecords.length; i++) {\n        var delta = conflictingRecords[i].totalTokensUsed - existingRecord.totalTokensUsed;\n        if (delta > 0) {\n            merged.totalTokensUsed += delta;\n        }\n    }\n\n    merged._ts = Math.max(existingRecord._ts, incomingRecord._ts);\n    return merged;\n}"
}
```

---

## 7. Latency-Based Routing Configuration

### Routing Rules and Health Probes

```
┌──────────────────────────────────────────────────────────────────────┐
│                LATENCY-BASED ROUTING FLOW                            │
│                                                                      │
│  User (Frankfurt) ──► Front Door PoP (Frankfurt)                     │
│                            │                                         │
│                  Measure latency to origins:                         │
│                  ┌─────────────────────────────────┐                 │
│                  │ East US:     120ms               │                 │
│                  │ West Europe:  18ms  ◄── WINNER   │                 │
│                  │ West US 2:   160ms               │                 │
│                  └─────────────────────────────────┘                 │
│                            │                                         │
│                            ▼                                         │
│                  Route to West Europe AKS                             │
│                  (within 50ms sensitivity)                            │
│                                                                      │
│  ────────────────────────────────────────────────────                │
│                                                                      │
│  User (New York) ──► Front Door PoP (New York)                       │
│                            │                                         │
│                  Measure latency to origins:                         │
│                  ┌─────────────────────────────────┐                 │
│                  │ East US:      8ms  ◄── WINNER   │                 │
│                  │ West Europe: 95ms                │                 │
│                  │ West US 2:   65ms                │                 │
│                  └─────────────────────────────────┘                 │
│                            │                                         │
│                            ▼                                         │
│                  Route to East US AKS                                 │
│                  (within 50ms sensitivity)                            │
└──────────────────────────────────────────────────────────────────────┘
```

### Health Probe Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Protocol** | HTTPS | End-to-end encryption |
| **Path** | `/healthz` | Kubernetes liveness probe endpoint |
| **Interval** | 30 seconds | Balance between freshness and cost |
| **Timeout** | 5 seconds | Detect unresponsive backends quickly |
| **Failure threshold** | 3 consecutive | Avoid flapping on transient errors |
| **Success threshold** | 1 | Fast recovery once backend is healthy |
| **Method** | GET | Lightweight, no side effects |

### Latency Sensitivity Configuration

```bash
# Azure CLI — configure latency sensitivity for origin group
az afd origin-group update \
  --resource-group rg-rag-global \
  --profile-name fd-rag-platform-prod \
  --origin-group-name og-us-rag-api \
  --additional-latency-in-milliseconds 50

# A value of 50ms means:
# - If Origin A has 10ms latency and Origin B has 55ms latency,
#   traffic goes to Origin A (difference > 50ms threshold)
# - If Origin A has 10ms latency and Origin B has 45ms latency,
#   traffic is load-balanced across both (difference < 50ms)
```

---

## 8. Regional Data Residency Enforcement

### Data Residency Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│               DATA RESIDENCY ENFORCEMENT                             │
│                                                                      │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐    │
│  │      US DATA BOUNDARY       │  │      EU DATA BOUNDARY       │    │
│  │                             │  │                             │    │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │
│  │  │ Cosmos DB             │  │  │  │ Cosmos DB             │  │    │
│  │  │ Partition: tenantId   │  │  │  │ Partition: tenantId   │  │    │
│  │  │ Region: East US       │  │  │  │ Region: West Europe   │  │    │
│  │  │ Writes: LOCAL ONLY    │  │  │  │ Writes: LOCAL ONLY    │  │    │
│  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │
│  │                             │  │                             │    │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │
│  │  │ Blob Storage          │  │  │  │ Blob Storage          │  │    │
│  │  │ Account: stragus...   │  │  │  │ Account: strageu...   │  │    │
│  │  │ GRS within US only    │  │  │  │ GRS within EU only    │  │    │
│  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │
│  │                             │  │                             │    │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │
│  │  │ AI Search Index       │  │  │  │ AI Search Index       │  │    │
│  │  │ US documents only     │  │  │  │ EU documents only     │  │    │
│  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │
│  │                             │  │                             │    │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │    │
│  │  │ OpenAI Service        │  │  │  │ OpenAI Service        │  │    │
│  │  │ Region: East US       │  │  │  │ Region: France Central│  │    │
│  │  └───────────────────────┘  │  │  └───────────────────────┘  │    │
│  │                             │  │                             │    │
│  └─────────────────────────────┘  └─────────────────────────────┘    │
│                                                                      │
│  CROSS-BOUNDARY DATA: NONE (except global config, anonymized metrics)│
└──────────────────────────────────────────────────────────────────────┘
```

### Cosmos DB Partition Strategy for Data Residency

| Tenant Region | Partition Key | Write Region | Read Regions | Replication |
|--------------|---------------|-------------|-------------|-------------|
| **US tenants** | `/tenantId` | East US | East US, West US 2 | Within US only |
| **EU tenants** | `/tenantId` | West Europe | West Europe, North Europe | Within EU only |
| **Global config** | `/configType` | East US (primary) | All regions | Cross-region (non-PII) |

### Enforcement Mechanisms

```terraform
# ──────────────────────────────────────────────────────────────────
# Azure Policy — Enforce Data Residency
# ──────────────────────────────────────────────────────────────────

resource "azurerm_policy_assignment" "eu_data_residency" {
  name                 = "enforce-eu-data-residency"
  scope                = azurerm_resource_group.eu_data.id
  policy_definition_id = azurerm_policy_definition.allowed_locations.id
  display_name         = "EU Data Residency — Restrict to EU Regions"

  parameters = jsonencode({
    listOfAllowedLocations = {
      value = ["westeurope", "northeurope", "francecentral", "germanywestcentral"]
    }
  })
}

resource "azurerm_policy_definition" "allowed_locations" {
  name         = "allowed-locations-eu"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Restrict resource locations to EU"

  policy_rule = jsonencode({
    if = {
      not = {
        field = "location"
        in    = "[parameters('listOfAllowedLocations')]"
      }
    }
    then = {
      effect = "deny"
    }
  })

  parameters = jsonencode({
    listOfAllowedLocations = {
      type = "Array"
      metadata = {
        description = "Allowed Azure regions for EU data"
        displayName = "Allowed Locations"
      }
    }
  })
}
```

### Application-Level Residency Routing

```json
{
  "tenantResidencyMap": {
    "tenant-acme-corp": { "region": "us", "writeEndpoint": "eastus", "searchIndex": "rag-index-us" },
    "tenant-eureka-gmbh": { "region": "eu", "writeEndpoint": "westeurope", "searchIndex": "rag-index-eu" },
    "tenant-globex-intl": { "region": "us", "writeEndpoint": "eastus", "searchIndex": "rag-index-us" }
  },
  "residencyRules": {
    "us": {
      "allowedCosmosRegions": ["eastus", "westus2"],
      "allowedStorageAccounts": ["stragusprod", "stragusproddr"],
      "allowedSearchServices": ["search-rag-us-prod"]
    },
    "eu": {
      "allowedCosmosRegions": ["westeurope", "northeurope"],
      "allowedStorageAccounts": ["strageuprod", "strageuproddr"],
      "allowedSearchServices": ["search-rag-eu-prod"]
    }
  }
}
```

---

## 9. Cost of Multi-Region Deployment

### Component-Level Cost Comparison

| Component | Single-Region (Monthly) | Dual-Region (Monthly) | Multiplier | Notes |
|-----------|------------------------|----------------------|------------|-------|
| **AKS Cluster** (3-node D4s_v5) | $1,260 | $2,520 | 2.0x | Full cluster per region |
| **Azure OpenAI** (GPT-4o) | $2,500 | $5,000 | 2.0x | Independent deployments |
| **Cosmos DB** (multi-write) | $800 | $1,280 | 1.6x | Multi-write adds 25% RU surcharge |
| **AI Search** (S1) | $750 | $1,500 | 2.0x | Separate index per region |
| **Blob Storage** (100TB, GRS) | $2,100 | $3,150 | 1.5x | GRS within region boundary |
| **Redis Cache** (C2) | $340 | $680 | 2.0x | Per-region cache instance |
| **Azure Front Door** (Premium) | $0 | $335 | N/A | Only needed for multi-region |
| **App Gateway** (WAF v2) | $530 | $1,060 | 2.0x | Per-region WAF |
| **Key Vault** | $10 | $20 | 2.0x | Per-region instance |
| **Log Analytics** | $450 | $720 | 1.6x | Cross-region workspace federation |
| **Private Endpoints** (x8) | $60 | $120 | 2.0x | Per-region endpoints |
| **DNS / Certificates** | $50 | $75 | 1.5x | Shared certs, per-region DNS |
| **Service Bus** (cross-region) | $0 | $100 | N/A | Index sync messaging |
| | | | | |
| **TOTAL** | **$8,850** | **$16,560** | **1.87x** | |

### Cost Optimization Strategies

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| **Reserved Instances** (1-year AKS) | ~$4,500/yr | Commit to D4s_v5 across both regions |
| **Autoscale secondary** | ~$600/mo | Scale down secondary AKS during off-peak |
| **Shared AI Search** (read replicas) | ~$375/mo | Use replicas instead of separate service |
| **Cosmos DB autopilot** | ~$200/mo | Auto-scale RUs during low-traffic windows |
| **Spot nodes** (non-critical workloads) | ~$300/mo | Index rebuild jobs on spot instances |
| | | |
| **Optimized Multi-Region Total** | | **~$13,800/mo** (1.56x multiplier) |

---

## 10. Migration Path: Single to Multi-Region

### Phased Rollout Plan

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                 SINGLE → MULTI-REGION MIGRATION TIMELINE                     │
│                                                                              │
│  Week:  1    2    3    4    5    6    7    8    9   10   11   12              │
│         │    │    │    │    │    │    │    │    │    │    │    │              │
│  ═══════╪════╪════╪════╪════╪════╪════╪════╪════╪════╪════╪════╪══           │
│         │    │    │    │    │    │    │    │    │    │    │    │              │
│  PHASE 1: FOUNDATION (Weeks 1-3)                                             │
│  ├──────┤    │    │    │    │    │    │    │    │    │    │    │              │
│  │ Deploy secondary region infrastructure (Terraform)                │       │
│  │ ├── VNet, NSGs, Private Endpoints                                │       │
│  │ ├── AKS cluster (zero traffic)                                    │       │
│  │ └── Key Vault, ACR replication                                    │       │
│  │         ├──────┤                                                   │       │
│  │         │ Cosmos DB: Enable multi-region write                     │       │
│  │         │ ├── Add West Europe geo-location                         │       │
│  │         │ └── Validate replication lag                             │       │
│  │         │         ├──────┤                                         │       │
│  │         │         │ Deploy app to secondary AKS (shadow mode)      │       │
│  │         │         │ └── No live traffic; internal testing only      │       │
│  │         │         │                                                 │       │
│  PHASE 2: DATA LAYER (Weeks 4-6)                                             │
│  │         │         │    ├──────┤                                     │       │
│  │         │         │    │ Blob Storage: Replicate documents to EU    │       │
│  │         │         │    │ ├── AzCopy with incremental sync          │       │
│  │         │         │    │ └── Verify checksums cross-region         │       │
│  │         │         │    │         ├──────┤                           │       │
│  │         │         │    │         │ AI Search: Build EU index        │       │
│  │         │         │    │         │ ├── Full re-index from EU blob   │       │
│  │         │         │    │         │ └── Validate doc count parity    │       │
│  │         │         │    │         │         ├──────┤                 │       │
│  │         │         │    │         │         │ Event-driven sync live │       │
│  │         │         │    │         │         │ └── Service Bus topics │       │
│  │         │         │    │         │         │                        │       │
│  PHASE 3: TRAFFIC ROUTING (Weeks 7-9)                                        │
│  │         │         │    │         │         │    ├──────┤            │       │
│  │         │         │    │         │         │    │ Deploy Front Door │       │
│  │         │         │    │         │         │    │ ├── Canary: 5% EU │       │
│  │         │         │    │         │         │    │ └── Monitor errors│       │
│  │         │         │    │         │         │    │         ├──────┤  │       │
│  │         │         │    │         │         │    │         │ Ramp EU │       │
│  │         │         │    │         │         │    │         │ 25→50→  │       │
│  │         │         │    │         │         │    │         │ 100%    │       │
│  │         │         │    │         │         │    │         │    ├────┤       │
│  │         │         │    │         │         │    │         │    │Full│       │
│  │         │         │    │         │         │    │         │    │geo │       │
│  │         │         │    │         │         │    │         │    │rout│       │
│  │         │         │    │         │         │    │         │    │    │       │
│  PHASE 4: VALIDATION (Weeks 10-12)                                           │
│  │         │         │    │         │         │    │         │    │  ├─┤──┤    │
│  │         │         │    │         │         │    │         │    │  │Chaos│   │
│  │         │         │    │         │         │    │         │    │  │test │   │
│  │         │         │    │         │         │    │         │    │  │    ├┤   │
│  │         │         │    │         │         │    │         │    │  │    ││   │
│  │         │         │    │         │         │    │         │    │  │  Sign│   │
│  │         │         │    │         │         │    │         │    │  │  Off │   │
│  ═══════════════════════════════════════════════════════════════════════       │
│                                                                              │
│  Rollback gates at each phase boundary. No-go = revert to single-region.     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Phase Checklist

| Phase | Week | Milestone | Go/No-Go Criteria |
|-------|------|-----------|-------------------|
| **1: Foundation** | 1–3 | Secondary infra deployed, Cosmos DB replicating | Replication lag < 100ms, AKS pods healthy |
| **2: Data Layer** | 4–6 | EU Search index built, event sync running | Index doc count parity ±1%, sync lag < 5min |
| **3: Traffic** | 7–9 | Front Door live, geo-routing active | Error rate < 0.1%, P95 latency < 800ms |
| **4: Validation** | 10–12 | Chaos tests passed, sign-off complete | Failover RTO < 5min, zero data loss during test |

---

## 11. Regional Failover Testing

### Chaos Testing Framework

```
┌──────────────────────────────────────────────────────────────────────┐
│             REGIONAL FAILURE SIMULATION MATRIX                       │
│                                                                      │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐   │
│  │  TEST 1:       │     │  TEST 2:       │     │  TEST 3:       │   │
│  │  AKS Cluster   │     │  Cosmos DB     │     │  Full Region   │   │
│  │  Failure       │     │  Region Fail   │     │  Outage        │   │
│  │                │     │                │     │                │   │
│  │  Action:       │     │  Action:       │     │  Action:       │   │
│  │  Scale AKS to  │     │  Disable write │     │  Block all     │   │
│  │  0 nodes in    │     │  region in     │     │  traffic to    │   │
│  │  East US       │     │  Cosmos DB     │     │  East US       │   │
│  │                │     │                │     │                │   │
│  │  Expected:     │     │  Expected:     │     │  Expected:     │   │
│  │  Front Door    │     │  Auto-failover │     │  Front Door    │   │
│  │  routes to     │     │  to secondary  │     │  drains to     │   │
│  │  West US       │     │  write region  │     │  EU origins    │   │
│  │                │     │                │     │                │   │
│  │  RTO: < 2min   │     │  RTO: < 30s    │     │  RTO: < 5min   │   │
│  │  RPO: 0        │     │  RPO: 0        │     │  RPO: < 1min   │   │
│  └────────────────┘     └────────────────┘     └────────────────┘   │
│                                                                      │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐   │
│  │  TEST 4:       │     │  TEST 5:       │     │  TEST 6:       │   │
│  │  AI Search     │     │  OpenAI        │     │  DNS Failure   │   │
│  │  Unavailable   │     │  Throttled     │     │                │   │
│  │                │     │                │     │                │   │
│  │  Action:       │     │  Action:       │     │  Action:       │   │
│  │  Stop Search   │     │  Inject 429s   │     │  Poison DNS    │   │
│  │  service in    │     │  on primary    │     │  for primary   │   │
│  │  primary       │     │  OpenAI        │     │  region FQDN   │   │
│  │                │     │                │     │                │   │
│  │  Expected:     │     │  Expected:     │     │  Expected:     │   │
│  │  Fallback to   │     │  Route to      │     │  Front Door    │   │
│  │  secondary     │     │  secondary     │     │  bypasses via  │   │
│  │  search        │     │  OpenAI        │     │  health probe  │   │
│  │                │     │                │     │                │   │
│  │  RTO: < 1min   │     │  RTO: < 10s    │     │  RTO: < 3min   │   │
│  │  RPO: 0        │     │  RPO: 0        │     │  RPO: 0        │   │
│  └────────────────┘     └────────────────┘     └────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Automated Chaos Test Script

```bash
#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# Regional Failover Test — Automated Chaos Script
# Run: ./chaos-test.sh --test aks-failover --region eastus
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

TEST_NAME="${1:---test aks-failover}"
REGION="${2:---region eastus}"
MONITOR_DURATION=300  # 5 minutes observation window
ACCEPTABLE_RTO=300    # 5 minutes max RTO
ALERT_WEBHOOK="${TEAMS_WEBHOOK_URL}"

echo "╔════════════════════════════════════════════════════╗"
echo "║  CHAOS TEST: ${TEST_NAME}                          ║"
echo "║  TARGET REGION: ${REGION}                          ║"
echo "║  STARTED: $(date -u +%Y-%m-%dT%H:%M:%SZ)          ║"
echo "╚════════════════════════════════════════════════════╝"

# Pre-test: Capture baseline metrics
echo "[1/5] Capturing baseline metrics..."
BASELINE_P95=$(az monitor metrics list \
  --resource "/subscriptions/${SUB_ID}/resourceGroups/rg-rag-prod/providers/Microsoft.Cdn/profiles/fd-rag-platform-prod" \
  --metric TotalLatency \
  --aggregation Average \
  --interval PT1M \
  --query "value[0].timeseries[0].data[-1].average" -o tsv)
echo "  Baseline P95 latency: ${BASELINE_P95}ms"

# Inject failure: Scale AKS to 0 in target region
echo "[2/5] Injecting failure — scaling AKS to 0 nodes..."
az aks nodepool scale \
  --resource-group "rg-rag-${REGION}-prod" \
  --cluster-name "aks-rag-${REGION}-prod" \
  --name systempool \
  --node-count 0

FAILURE_TIME=$(date +%s)

# Monitor: Wait for Front Door to detect and reroute
echo "[3/5] Monitoring failover (${MONITOR_DURATION}s window)..."
FAILOVER_DETECTED=false
for i in $(seq 1 $MONITOR_DURATION); do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Host: rag.company.com" \
    "https://fd-rag-platform-prod.azurefd.net/api/health")

  if [ "$HTTP_STATUS" == "200" ] && [ "$FAILOVER_DETECTED" == "false" ]; then
    RECOVERY_TIME=$(date +%s)
    RTO=$((RECOVERY_TIME - FAILURE_TIME))
    FAILOVER_DETECTED=true
    echo "  Failover detected at ${RTO}s (limit: ${ACCEPTABLE_RTO}s)"
  fi
  sleep 1
done

# Restore: Scale AKS back
echo "[4/5] Restoring AKS nodes..."
az aks nodepool scale \
  --resource-group "rg-rag-${REGION}-prod" \
  --cluster-name "aks-rag-${REGION}-prod" \
  --name systempool \
  --node-count 3

# Report
echo "[5/5] Generating report..."
if [ "$FAILOVER_DETECTED" == "true" ] && [ "$RTO" -le "$ACCEPTABLE_RTO" ]; then
  echo "  ✓ PASS — RTO: ${RTO}s (within ${ACCEPTABLE_RTO}s limit)"
  EXIT_CODE=0
else
  echo "  ✗ FAIL — Failover not completed within ${ACCEPTABLE_RTO}s"
  EXIT_CODE=1
fi

exit $EXIT_CODE
```

### Failover Test Schedule

| Test | Frequency | Window | Notification |
|------|-----------|--------|-------------|
| **AKS cluster failure** | Monthly | Tuesday 02:00 UTC | SRE on-call + Teams channel |
| **Cosmos DB region fail** | Quarterly | Saturday 04:00 UTC | SRE + Data team |
| **Full region outage** | Bi-annual | Planned maintenance window | All engineering + leadership |
| **AI Search failover** | Monthly | Wednesday 02:00 UTC | SRE on-call |
| **OpenAI throttle sim** | Weekly | Automated in CI | Pipeline notification |
| **DNS failure** | Quarterly | Saturday 04:00 UTC | SRE + Network team |

---

## 12. Multi-Region Terraform Structure

### Repository Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│                TERRAFORM MULTI-REGION STRUCTURE                      │
│                                                                      │
│  terraform/                                                          │
│  ├── environments/                                                   │
│  │   ├── prod/                                                       │
│  │   │   ├── main.tf              # Root module — wires regions      │
│  │   │   ├── variables.tf         # Environment-level vars           │
│  │   │   ├── terraform.tfvars     # Prod values                     │
│  │   │   ├── backend.tf           # Remote state (global)            │
│  │   │   └── providers.tf         # Azure provider aliases           │
│  │   └── staging/                                                    │
│  │       └── ...                  # Same structure, single-region    │
│  │                                                                   │
│  ├── modules/                                                        │
│  │   ├── global/                  # Shared across all regions        │
│  │   │   ├── front-door/          #   Azure Front Door               │
│  │   │   ├── dns/                 #   Azure DNS zones                │
│  │   │   ├── cosmosdb/            #   Cosmos DB (multi-region)       │
│  │   │   └── acr/                 #   Container Registry (geo-rep)   │
│  │   │                                                               │
│  │   └── regional/                # Deployed per region              │
│  │       ├── aks/                 #   AKS cluster                    │
│  │       ├── ai-search/           #   AI Search service              │
│  │       ├── openai/              #   OpenAI deployment              │
│  │       ├── networking/          #   VNet, NSGs, Private Endpoints  │
│  │       ├── storage/             #   Blob Storage                   │
│  │       ├── redis/               #   Redis Cache                    │
│  │       ├── keyvault/            #   Key Vault                      │
│  │       └── monitoring/          #   Log Analytics, App Insights    │
│  │                                                                   │
│  └── shared/                                                         │
│      ├── naming.tf               # Naming conventions                │
│      ├── tags.tf                 # Common tag definitions            │
│      └── versions.tf             # Provider version constraints      │
└──────────────────────────────────────────────────────────────────────┘
```

### Root Module: Multi-Region Wiring

```terraform
# ──────────────────────────────────────────────────────────────────
# environments/prod/main.tf — Multi-Region Root Module
# ──────────────────────────────────────────────────────────────────

locals {
  regions = {
    us = {
      location       = "eastus"
      failover       = "westus2"
      address_space  = "10.1.0.0/16"
      openai_region  = "eastus"
    }
    eu = {
      location       = "westeurope"
      failover       = "northeurope"
      address_space  = "10.2.0.0/16"
      openai_region  = "francecentral"
    }
  }

  common_tags = {
    Environment = var.environment
    Project     = "rag-platform"
    ManagedBy   = "terraform"
    CostCenter  = "platform-engineering"
  }
}

# ── Global Resources (deployed once) ────────────────────────────

module "global_frontdoor" {
  source              = "../../modules/global/front-door"
  environment         = var.environment
  resource_group_name = azurerm_resource_group.global.name
  regions             = local.regions
  tags                = local.common_tags
}

module "global_cosmosdb" {
  source              = "../../modules/global/cosmosdb"
  environment         = var.environment
  resource_group_name = azurerm_resource_group.data.name
  regions             = local.regions
  tags                = local.common_tags
}

module "global_dns" {
  source              = "../../modules/global/dns"
  domain_name         = var.domain_name
  resource_group_name = azurerm_resource_group.global.name
  tags                = local.common_tags
}

module "global_acr" {
  source              = "../../modules/global/acr"
  environment         = var.environment
  resource_group_name = azurerm_resource_group.global.name
  replication_regions = [for r in local.regions : r.location]
  tags                = local.common_tags
}

# ── Regional Resources (deployed per region) ────────────────────

module "region" {
  source   = "../../modules/regional"
  for_each = local.regions

  region_key         = each.key
  location           = each.value.location
  address_space      = each.value.address_space
  openai_region      = each.value.openai_region
  environment        = var.environment
  cosmosdb_id        = module.global_cosmosdb.account_id
  acr_id             = module.global_acr.acr_id
  tags               = local.common_tags
}
```

### Cross-Region AKS Terraform

```terraform
# ──────────────────────────────────────────────────────────────────
# modules/regional/aks/main.tf — Per-Region AKS Cluster
# ──────────────────────────────────────────────────────────────────

resource "azurerm_kubernetes_cluster" "rag" {
  name                = "aks-rag-${var.region_key}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "aks-rag-${var.region_key}"
  kubernetes_version  = "1.29"

  default_node_pool {
    name                = "system"
    node_count          = 3
    vm_size             = "Standard_D4s_v5"
    vnet_subnet_id      = var.aks_subnet_id
    zones               = ["1", "2", "3"]
    os_disk_size_gb     = 128
    max_pods            = 50
    enable_auto_scaling = true
    min_count           = 3
    max_count           = 10

    node_labels = {
      "region" = var.region_key
      "tier"   = "system"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
    outbound_type     = "userDefinedRouting"
    service_cidr      = var.service_cidr
    dns_service_ip    = var.dns_service_ip
  }

  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "5m"
  }

  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_ids
  }

  private_cluster_enabled             = true
  private_cluster_public_fqdn_enabled = false

  tags = var.tags
}

# User node pool for RAG workloads
resource "azurerm_kubernetes_cluster_node_pool" "rag_workers" {
  name                  = "ragpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.rag.id
  vm_size               = "Standard_D8s_v5"
  zones                 = ["1", "2", "3"]
  enable_auto_scaling   = true
  min_count             = 2
  max_count             = 20
  vnet_subnet_id        = var.aks_subnet_id

  node_labels = {
    "workload" = "rag-api"
    "region"   = var.region_key
  }

  node_taints = ["workload=rag-api:NoSchedule"]

  tags = var.tags
}
```

---

## 13. DNS and Certificate Management

### DNS Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    DNS & CERTIFICATE TOPOLOGY                        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    PUBLIC DNS (Azure DNS)                       │  │
│  │                                                                │  │
│  │  rag.company.com          CNAME → fd-rag-prod.azurefd.net     │  │
│  │  api.rag.company.com     CNAME → fd-rag-prod.azurefd.net     │  │
│  │  status.rag.company.com  A     → 20.x.x.x (Status Page)     │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│                     ┌─────────▼─────────┐                            │
│                     │  AZURE FRONT DOOR  │                            │
│                     │  (TLS termination) │                            │
│                     │                   │                            │
│                     │  Certs:           │                            │
│                     │  ├─ AFD-managed   │                            │
│                     │  │  (auto-renew)  │                            │
│                     │  └─ Custom cert   │                            │
│                     │     (Key Vault)   │                            │
│                     └─────────┬─────────┘                            │
│                        ┌──────┴──────┐                               │
│                        │             │                               │
│              ┌─────────▼───┐  ┌──────▼──────┐                        │
│              │ PRIVATE DNS  │  │ PRIVATE DNS  │                        │
│              │ (East US)    │  │ (West EUR)   │                        │
│              │              │  │              │                        │
│              │ aks.internal │  │ aks.internal │                        │
│              │ cosmos.int   │  │ cosmos.int   │                        │
│              │ search.int   │  │ search.int   │                        │
│              │ kv.internal  │  │ kv.internal  │                        │
│              └──────────────┘  └──────────────┘                        │
│                                                                      │
│  Certificate Lifecycle:                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │
│  │ Key Vault  │─►│ Auto-Renew │─►│ Front Door │─►│ TLS 1.3    │     │
│  │ (storage)  │  │ (90-day)   │  │ (binding)  │  │ (enforced) │     │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### Certificate Management Configuration

| Certificate | Type | Storage | Renewal | Scope |
|------------|------|---------|---------|-------|
| **rag.company.com** | AFD-managed | Front Door | Auto (60-day) | Global endpoint |
| **api.rag.company.com** | Custom (EV) | Key Vault (US) | 90-day auto-renew | API endpoint |
| **Internal mTLS** | Self-signed CA | Key Vault (per region) | 365-day, auto-rotate | Service mesh |
| **Cosmos DB private endpoint** | Azure-managed | Azure platform | Auto | Private connectivity |

### Private DNS Zone Configuration

```terraform
# ──────────────────────────────────────────────────────────────────
# Private DNS Zones — Per-Region with Cross-Region Links
# ──────────────────────────────────────────────────────────────────

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "search" {
  name                = "privatelink.search.windows.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "keyvault" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "openai" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link DNS zones to VNets in both regions
resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_links" {
  for_each = var.vnet_ids

  name                  = "link-cosmos-${each.key}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = each.value
  registration_enabled  = false
  tags                  = var.tags
}
```

---

## 14. Monitoring: Per-Region Dashboards

### Monitoring Topology

```
┌──────────────────────────────────────────────────────────────────────┐
│              MULTI-REGION MONITORING ARCHITECTURE                     │
│                                                                      │
│  ┌──────────────────┐              ┌──────────────────┐              │
│  │  East US Region   │              │  West Europe      │              │
│  │                  │              │  Region           │              │
│  │  ┌────────────┐  │              │  ┌────────────┐  │              │
│  │  │App Insights│  │              │  │App Insights│  │              │
│  │  │(regional)  │──┼──────┐       │  │(regional)  │──┼──────┐      │
│  │  └────────────┘  │      │       │  └────────────┘  │      │      │
│  │  ┌────────────┐  │      │       │  ┌────────────┐  │      │      │
│  │  │Log         │  │      │       │  │Log         │  │      │      │
│  │  │Analytics   │──┼──┐   │       │  │Analytics   │──┼──┐   │      │
│  │  │(regional)  │  │  │   │       │  │(regional)  │  │  │   │      │
│  │  └────────────┘  │  │   │       │  └────────────┘  │  │   │      │
│  └──────────────────┘  │   │       └──────────────────┘  │   │      │
│                        │   │                             │   │      │
│              ┌─────────▼───▼─────────────────────────────▼───▼──┐   │
│              │          AZURE MONITOR (Global)                   │   │
│              │                                                   │   │
│              │  ┌─────────────────────────────────────────────┐  │   │
│              │  │  Cross-Region Dashboard                      │  │   │
│              │  │                                             │  │   │
│              │  │  ┌─────────────┐  ┌─────────────────────┐  │  │   │
│              │  │  │ Latency     │  │ Availability by     │  │  │   │
│              │  │  │ Heatmap     │  │ Region              │  │  │   │
│              │  │  │ (US vs EU)  │  │ US: 99.99%          │  │  │   │
│              │  │  │             │  │ EU: 99.98%          │  │  │   │
│              │  │  └─────────────┘  └─────────────────────┘  │  │   │
│              │  │                                             │  │   │
│              │  │  ┌─────────────┐  ┌─────────────────────┐  │  │   │
│              │  │  │ Replication │  │ Token Usage by      │  │  │   │
│              │  │  │ Lag (ms)    │  │ Region              │  │  │   │
│              │  │  │ Cosmos: 45  │  │ US: 1.2M/day        │  │  │   │
│              │  │  │ Search: 120 │  │ EU: 800K/day        │  │  │   │
│              │  │  └─────────────┘  └─────────────────────┘  │  │   │
│              │  └─────────────────────────────────────────────┘  │   │
│              │                                                   │   │
│              │  Alerts → PagerDuty / Teams / Email                │   │
│              └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Metrics per Region

| Metric | Source | Alert Threshold | Severity |
|--------|--------|----------------|----------|
| **P95 end-to-end latency** | App Insights | > 800ms for 5 min | Sev 2 |
| **Error rate (5xx)** | App Insights | > 1% for 3 min | Sev 1 |
| **Cosmos DB replication lag** | Azure Monitor | > 500ms for 10 min | Sev 2 |
| **Search index freshness** | Custom metric | > 15 min behind | Sev 3 |
| **AKS node availability** | Container Insights | < 3 ready nodes | Sev 1 |
| **OpenAI 429 rate** | App Insights | > 5% of requests | Sev 2 |
| **Front Door origin health** | Front Door diagnostics | Any origin unhealthy | Sev 1 |
| **Cross-region latency** | Synthetic test | > 200ms between regions | Sev 3 |
| **Certificate expiry** | Key Vault | < 30 days to expiry | Sev 2 |
| **Token budget utilization** | Custom metric | > 80% of monthly budget | Sev 3 |

### Cross-Region Latency Tracking Query

```bash
# KQL query for cross-region latency comparison dashboard
az monitor app-insights query \
  --app "ai-rag-global-prod" \
  --analytics-query '
requests
| where timestamp > ago(24h)
| extend region = tostring(customDimensions["deployment_region"])
| summarize
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99),
    errorRate = countif(resultCode >= 500) * 100.0 / count(),
    requestCount = count()
  by region, bin(timestamp, 1h)
| order by timestamp desc, region asc
'
```

### Alert Configuration

```terraform
# ──────────────────────────────────────────────────────────────────
# Cross-Region Alert Rules
# ──────────────────────────────────────────────────────────────────

resource "azurerm_monitor_metric_alert" "cosmos_replication_lag" {
  name                = "alert-cosmos-replication-lag"
  resource_group_name = azurerm_resource_group.monitoring.name
  scopes              = [module.global_cosmosdb.account_id]
  description         = "Cosmos DB replication lag exceeds 500ms"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "ReplicationLatency"
    aggregation      = "Maximum"
    operator         = "GreaterThan"
    threshold        = 500
  }

  action {
    action_group_id = azurerm_monitor_action_group.sre_oncall.id
  }

  tags = local.common_tags
}

resource "azurerm_monitor_metric_alert" "frontdoor_origin_health" {
  name                = "alert-frontdoor-origin-unhealthy"
  resource_group_name = azurerm_resource_group.monitoring.name
  scopes              = [module.global_frontdoor.profile_id]
  description         = "Front Door origin health below threshold"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Cdn/profiles"
    metric_name      = "OriginHealthPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 90
  }

  action {
    action_group_id = azurerm_monitor_action_group.sre_oncall.id
  }

  tags = local.common_tags
}
```

---

## 15. Multi-Region AI Search Strategy

### Replica vs Separate Indexes

```
┌──────────────────────────────────────────────────────────────────────┐
│          AI SEARCH: REPLICA vs SEPARATE INDEXES                      │
│                                                                      │
│  OPTION A: READ REPLICAS (Single Service, Multiple Replicas)         │
│  ┌────────────────────────────────────────────────────────┐          │
│  │  AI Search Service (East US, S1)                       │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │          │
│  │  │ Replica 1│ │ Replica 2│ │ Replica 3│               │          │
│  │  │ (R/W)    │ │ (Read)   │ │ (Read)   │               │          │
│  │  └──────────┘ └──────────┘ └──────────┘               │          │
│  │                                                        │          │
│  │  Pros: Simple management, automatic consistency        │          │
│  │  Cons: Single-region; doesn't solve data residency     │          │
│  │        or cross-region latency                          │          │
│  └────────────────────────────────────────────────────────┘          │
│                                                                      │
│  ═══════════════════════════════════════════════════════════          │
│                                                                      │
│  OPTION B: SEPARATE INDEXES PER REGION  ◄── SELECTED                 │
│  ┌──────────────────────┐    ┌──────────────────────┐                │
│  │ AI Search (East US)  │    │ AI Search (West EUR) │                │
│  │ Service: S1          │    │ Service: S1          │                │
│  │ Index: rag-index-us  │    │ Index: rag-index-eu  │                │
│  │ Replicas: 2          │    │ Replicas: 2          │                │
│  │ Partitions: 2        │    │ Partitions: 2        │                │
│  │                      │    │                      │                │
│  │ Data: US documents   │    │ Data: EU documents   │                │
│  │ + global shared docs │    │ + global shared docs │                │
│  └──────────┬───────────┘    └──────────┬───────────┘                │
│             │                           │                            │
│             └───────────┬───────────────┘                            │
│                         │                                            │
│              ┌──────────▼──────────┐                                 │
│              │  Event-Driven Sync  │                                 │
│              │  (Service Bus)      │                                 │
│              │  Source: Blob Store  │                                 │
│              └─────────────────────┘                                 │
│                                                                      │
│  Pros: Data residency enforced, local latency, independent scaling   │
│  Cons: Sync complexity, potential staleness, higher cost (2x)        │
└──────────────────────────────────────────────────────────────────────┘
```

### Decision Matrix

| Criteria | Read Replicas | Separate Indexes | Winner |
|----------|--------------|------------------|--------|
| **Data residency** | Single region only | Per-region isolation | Separate |
| **Query latency** | Single-region optimized | Both regions optimized | Separate |
| **Consistency** | Automatic | Eventual (event-driven) | Replicas |
| **Cost** | 1x (replicas within service) | 2x (separate services) | Replicas |
| **Operational complexity** | Low | Medium-High | Replicas |
| **Failover** | Within-region only | Cross-region possible | Separate |
| **Index customization** | Identical indexes | Per-region tuning possible | Separate |
| **GDPR compliance** | Requires careful filtering | Natural boundary | Separate |

**Decision:** Separate indexes per region, aligned with the regional active-active topology and data residency requirements.

### Index Sync Monitoring

| Metric | Target | Alert Threshold | Check Interval |
|--------|--------|----------------|---------------|
| **Document count delta** | 0 (for shared docs) | > 10 documents | 5 min |
| **Sync event processing lag** | < 2 min | > 5 min | 1 min |
| **Failed index operations** | 0 | > 5 per hour | 1 min |
| **Index freshness** | < 5 min | > 15 min | 5 min |
| **Embedding generation errors** | < 0.1% | > 1% | 5 min |

---

## Appendix A: Multi-Region Deployment Checklist

| # | Category | Task | Owner | Status |
|---|----------|------|-------|--------|
| 1 | **Infrastructure** | Deploy secondary region VNet and subnets | Platform Team | ☐ |
| 2 | **Infrastructure** | Provision AKS cluster in secondary region | Platform Team | ☐ |
| 3 | **Infrastructure** | Deploy Azure Front Door with origin groups | Platform Team | ☐ |
| 4 | **Data** | Enable Cosmos DB multi-region write | Data Team | ☐ |
| 5 | **Data** | Replicate Blob Storage to secondary region | Data Team | ☐ |
| 6 | **Data** | Build secondary AI Search index | Data Team | ☐ |
| 7 | **Data** | Configure event-driven index sync | Data Team | ☐ |
| 8 | **Security** | Deploy Key Vault in secondary region | Security Team | ☐ |
| 9 | **Security** | Configure private endpoints (secondary) | Security Team | ☐ |
| 10 | **Security** | Set up private DNS zone links | Network Team | ☐ |
| 11 | **Security** | Provision and bind TLS certificates | Security Team | ☐ |
| 12 | **Networking** | Configure geo-routing rules in Front Door | Network Team | ☐ |
| 13 | **Networking** | Set up health probes for all origins | Network Team | ☐ |
| 14 | **Application** | Deploy RAG application to secondary AKS | Dev Team | ☐ |
| 15 | **Application** | Configure regional Cosmos DB endpoints | Dev Team | ☐ |
| 16 | **Application** | Configure regional AI Search endpoints | Dev Team | ☐ |
| 17 | **Monitoring** | Deploy App Insights (secondary region) | SRE Team | ☐ |
| 18 | **Monitoring** | Create cross-region dashboard | SRE Team | ☐ |
| 19 | **Monitoring** | Configure cross-region alerts | SRE Team | ☐ |
| 20 | **Testing** | Execute AKS failover chaos test | SRE Team | ☐ |
| 21 | **Testing** | Execute Cosmos DB regional failure test | SRE Team | ☐ |
| 22 | **Testing** | Execute full region outage simulation | SRE Team | ☐ |
| 23 | **Compliance** | Validate EU data residency enforcement | Security Team | ☐ |
| 24 | **Compliance** | Audit cross-region data flows | Security Team | ☐ |
| 25 | **Sign-off** | Architecture review board approval | Platform Lead | ☐ |

---

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **Active-Active** | Both regions serve live traffic simultaneously |
| **Active-Passive** | Primary region serves traffic; secondary on standby |
| **RTO** | Recovery Time Objective — max acceptable downtime |
| **RPO** | Recovery Point Objective — max acceptable data loss |
| **LWW** | Last-Writer-Wins — conflict resolution by timestamp |
| **Geo-fencing** | Restricting data and traffic to specific geographic boundaries |
| **Origin Group** | Azure Front Door concept grouping backend origins for routing |
| **Session Affinity** | Routing subsequent requests from same client to same backend |
| **Staleness Tolerance** | Acceptable delay between data write and read availability |
| **PLS** | Private Link Service — enables private connectivity to Front Door |

---

## Document Control

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Classification** | Internal |
| **Owner** | Platform Team |
| **Last Updated** | 2024-01 |
| **Reviewers** | SRE Lead, Security Architect, Data Engineering Lead |
| **Approval** | Architecture Review Board |
| **Next Review** | 2024-07 |
| **Change Log** | v1.0 — Initial multi-region deployment architecture |
