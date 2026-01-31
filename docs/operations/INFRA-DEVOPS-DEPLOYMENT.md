# Infrastructure, DevOps & Deployment Guide — Azure OpenAI Enterprise Platform

> Infrastructure planning, Terraform IaC, DevOps pipelines, org setup, cloud integration, desktop-to-cloud migration, zone selection, service lifecycle, and deployment strategies.

---

## Table of Contents

1. [Infrastructure Plan](#1-infrastructure-plan)
2. [DevOps Plan](#2-devops-plan)
3. [Terraform Plan](#3-terraform-plan)
4. [Organization Setup](#4-organization-setup)
5. [Cloud Integration](#5-cloud-integration)
6. [Deployment Strategy](#6-deployment-strategy)
7. [Desktop-to-Cloud Integration](#7-desktop-to-cloud-integration)
8. [Infrastructure Setup](#8-infrastructure-setup)
9. [Infrastructure as Code Service](#9-infrastructure-as-code-service)
10. [List of Services, Instances & Deployments](#10-list-of-services-instances--deployments)
11. [Zone Selection](#11-zone-selection)
12. [Service Creation Strategy](#12-service-creation-strategy)
13. [Service Deletion Strategy](#13-service-deletion-strategy)
14. [Smoke Testing Strategy (Infra)](#14-smoke-testing-strategy-infra)
15. [Trust AI — Infrastructure Perspective](#15-trust-ai--infrastructure-perspective)
16. [Explainable AI — Infrastructure Perspective](#16-explainable-ai--infrastructure-perspective)

---

## 1. Infrastructure Plan

### 1.1 Infrastructure Overview

```
Azure Subscription
├── Resource Group: rg-genai-copilot-{env}-{region}
│
├── Networking Layer
│   ├── VNet (10.0.0.0/16) + 5 Subnets
│   ├── Application Gateway (WAF v2)
│   ├── Azure Bastion (Standard)
│   ├── DDoS Protection (Standard)
│   ├── 8 Private Endpoints
│   ├── NSGs (per subnet)
│   └── Private DNS Zones (8 zones)
│
├── Compute Layer
│   ├── AKS Cluster (3-10 nodes)
│   ├── Azure Functions (3 apps: pre-retrieval, rag-processor, ingestion)
│   └── Azure Container Registry (Premium)
│
├── AI Layer
│   ├── Azure OpenAI (GPT-4o, GPT-4o-mini, text-embedding-3-large)
│   ├── Azure AI Search (S2, 3 replicas)
│   ├── Azure Document Intelligence (S0)
│   └── Azure Content Safety (S0)
│
├── Data Layer
│   ├── Azure Cosmos DB (7 containers, autoscale)
│   ├── Azure Cache for Redis (Premium P1)
│   └── Azure Storage Account (Data Lake Gen2)
│
├── Security Layer
│   ├── Azure Key Vault (Premium, HSM-backed)
│   ├── Azure Entra ID (P2)
│   ├── Azure Defender for Cloud
│   └── Azure Sentinel
│
└── Monitoring Layer
    ├── Application Insights
    ├── Log Analytics Workspace
    └── Azure Monitor (alerts, action groups)
```

### 1.2 Environment Strategy

| Environment | Purpose | Scale | Monthly Cost |
|-------------|---------|-------|-------------|
| **Dev** | Development, experimentation | Minimal SKUs, single instance | $782 |
| **Staging** | Integration testing, pre-prod validation | Production-like, reduced scale | $2,318 |
| **Production** | Live workload | Full scale, HA, autoscale | $13,909 |

### 1.3 Infrastructure Sizing

| Service | Dev | Staging | Production |
|---------|-----|---------|------------|
| AKS Nodes | 1 × D2s_v3 | 2 × D4s_v3 | 3-10 × D4s_v3 |
| Functions Plan | Consumption | EP1 | EP2 |
| AI Search | Basic (1 replica) | S1 (2 replicas) | S2 (3 replicas, 2 partitions) |
| Cosmos DB | Serverless | Autoscale 400-2000 | Autoscale 400-4000 |
| Redis | Basic C0 | Standard C1 | Premium P1 |
| Key Vault | Standard | Standard | Premium (HSM) |
| App Gateway | — | WAF v2 (1 instance) | WAF v2 (2-10 autoscale) |
| Bastion | — | Basic | Standard |
| ACR | Basic | Standard | Premium |

### 1.4 Infrastructure Dependencies

```
Order of provisioning (dependency graph):

Phase 1: Foundation
├── Resource Group
├── VNet + Subnets
├── NSGs
├── Key Vault
├── Storage Account
└── Log Analytics Workspace

Phase 2: Security
├── Entra ID App Registrations
├── Private DNS Zones
├── DDoS Protection
└── Application Gateway + WAF

Phase 3: Data
├── Cosmos DB + Private Endpoint
├── Redis Cache + Private Endpoint
├── AI Search + Private Endpoint
└── Document Intelligence + Private Endpoint

Phase 4: AI & Compute
├── Azure OpenAI + Private Endpoint
├── Content Safety
├── ACR + Private Endpoint
├── AKS Cluster (depends on VNet, ACR, Key Vault)
└── Azure Functions (depends on VNet, Storage, Key Vault)

Phase 5: Monitoring & Security Ops
├── Application Insights
├── Sentinel
├── Defender for Cloud
├── Alert Rules
└── Bastion
```

---

## 2. DevOps Plan

### 2.1 DevOps Toolchain

| Tool | Purpose | Integration |
|------|---------|-------------|
| **GitHub** | Source code, PRs, issues | Central repository |
| **GitHub Actions** | CI/CD pipelines | Build, test, deploy |
| **Terraform** | Infrastructure as Code | Azure provider |
| **Docker** | Container packaging | Build → ACR → AKS |
| **Helm** | Kubernetes packaging | AKS deployments |
| **pytest** | Test framework | CI pipeline |
| **Ruff** | Python linting | Pre-commit |
| **mypy** | Type checking | CI pipeline |
| **Bandit** | SAST (Python) | Security scan |
| **Trivy** | Container scanning | Image vulnerability |
| **detect-secrets** | Secret detection | Pre-commit |
| **k6 / Locust** | Load testing | Performance pipeline |
| **SonarQube** | Code quality | PR quality gate |

### 2.2 CI/CD Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CI/CD Pipeline                                │
├──────────┬───────────┬────────────┬──────────┬──────────┬───────────┤
│  Stage 1 │  Stage 2  │  Stage 3   │ Stage 4  │ Stage 5  │  Stage 6  │
│  Build   │ Security  │ Functional │ Staging  │ Evaluate │Production │
│          │   Scan    │   Test     │  Deploy  │  Gate    │  Deploy   │
├──────────┼───────────┼────────────┼──────────┼──────────┼───────────┤
│ lint     │ dep scan  │ happy path │ terraform│ golden   │ canary 10%│
│ typecheck│ SAST      │ error cases│ apply    │ dataset  │ smoke test│
│ unit test│ secrets   │ contract   │ smoke    │ quality  │ canary 50%│
│ build    │ container │            │ integr.  │ gates    │ full 100% │
│ publish  │ scan      │            │ tests    │          │ verify    │
├──────────┼───────────┼────────────┼──────────┼──────────┼───────────┤
│ <2 min   │ <3 min    │ <5 min     │ <15 min  │ <30 min  │ <10 min   │
│ Every    │ Every PR  │ Every PR   │ Merge to │ Pre-     │ Manual    │
│ commit   │           │            │ main     │ release  │ approval  │
└──────────┴───────────┴────────────┴──────────┴──────────┴───────────┘
```

### 2.3 Branching Strategy

```
main (protected, requires PR)
├── develop (integration branch)
│   ├── feature/add-cache-layer
│   ├── feature/multi-tenant-rbac
│   └── feature/evaluation-pipeline
├── release/v1.0.0
├── hotfix/fix-pii-leak
└── infra/terraform-networking
```

**Branch Policies:**
- `main`: Requires PR with 2 approvals, all CI checks pass, no direct push
- `develop`: Requires PR with 1 approval, CI checks pass
- `feature/*`: Created from develop, merged back via PR
- `release/*`: Created from main, deployed to staging then production
- `hotfix/*`: Created from main, fast-tracked with 1 approval

### 2.4 Release Process

```
Release v1.2.0:
1. Create release branch from main
2. Update version in pyproject.toml, CHANGELOG.md
3. Deploy to staging → run full test suite
4. Run evaluation pipeline → quality gates
5. Approval: Product Owner + Tech Lead
6. Deploy to production (canary → full)
7. Tag release in GitHub
8. Merge release branch back to main and develop
```

### 2.5 Incident Response DevOps

| Severity | Detection | Response Time | Resolution | Communication |
|----------|-----------|-------------|------------|---------------|
| P0 (Critical) | Auto-alert | Immediate | <1 hour | Page + Slack + email |
| P1 (High) | Auto-alert | <15 min | <4 hours | Page + Slack |
| P2 (Medium) | Alert | <1 hour | <24 hours | Slack |
| P3 (Low) | Manual | Next business day | <1 week | Ticket |

---

## 3. Terraform Plan

### 3.1 Module Structure

```
infrastructure/terraform/
├── main.tf                    # Root module, backend config
├── variables.tf               # Global variables
├── outputs.tf                 # Global outputs
├── terraform.tfvars           # Variable values (per env)
├── backend.tf                 # Remote state configuration
│
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── production.tfvars
│
├── modules/
│   ├── networking/
│   │   ├── main.tf            # VNet, subnets, NSGs, private DNS
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── private_endpoints.tf
│   │
│   ├── compute/
│   │   ├── aks.tf             # AKS cluster, node pools
│   │   ├── functions.tf       # 3 Function apps + plans
│   │   ├── acr.tf             # Container registry
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── data/
│   │   ├── cosmos.tf          # Cosmos DB account + containers
│   │   ├── storage.tf         # Data Lake Gen2
│   │   ├── redis.tf           # Redis cache
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── ai/
│   │   ├── openai.tf          # Azure OpenAI + model deployments
│   │   ├── search.tf          # AI Search + index
│   │   ├── doc_intelligence.tf # Document Intelligence
│   │   ├── content_safety.tf  # Content Safety
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── security/
│   │   ├── keyvault.tf        # Key Vault + secrets
│   │   ├── waf.tf             # Application Gateway WAF
│   │   ├── bastion.tf         # Azure Bastion
│   │   ├── ddos.tf            # DDoS Protection
│   │   ├── entra.tf           # App registrations, groups
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── monitoring/
│       ├── app_insights.tf    # Application Insights
│       ├── log_analytics.tf   # Log Analytics workspace
│       ├── sentinel.tf        # Sentinel
│       ├── alerts.tf          # Alert rules + action groups
│       ├── variables.tf
│       └── outputs.tf
│
└── scripts/
    ├── init.sh                # Initialize backend
    ├── plan.sh                # Plan with env selection
    ├── apply.sh               # Apply with approval
    └── destroy.sh             # Destroy with safety checks
```

### 3.2 Terraform State Management

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "genai-copilot.terraform.tfstate"
    use_oidc             = true  # GitHub Actions OIDC
  }
}
```

**State Management Best Practices:**
- Remote state in Azure Storage with state locking
- Separate state files per environment
- State encryption at rest (Storage Account encryption)
- Access via managed identity (no storage keys)
- Regular state backup (Azure Storage versioning)

### 3.3 Terraform Execution Plan

```bash
# Dev environment
terraform plan -var-file="environments/dev.tfvars" -out="dev.tfplan"
terraform apply "dev.tfplan"

# Staging environment
terraform plan -var-file="environments/staging.tfvars" -out="staging.tfplan"
terraform apply "staging.tfplan"

# Production environment (requires approval)
terraform plan -var-file="environments/production.tfvars" -out="prod.tfplan"
# Manual review of plan output
terraform apply "prod.tfplan"
```

### 3.4 Key Terraform Resources

```hcl
# Example: Azure OpenAI with model deployment
resource "azurerm_cognitive_account" "openai" {
  name                = "oai-genai-copilot-${var.environment}-${var.region_code}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  network_acls {
    default_action = "Deny"
    ip_rules       = []
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  sku {
    name     = "Standard"
    capacity = 80  # TPM in thousands
  }
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  sku {
    name     = "Standard"
    capacity = 120
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-3-large"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = 350
  }
}
```

### 3.5 Terraform Drift Detection

```yaml
# .github/workflows/drift-detection.yml
name: Terraform Drift Detection

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM

jobs:
  drift:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, staging, production]
    steps:
      - uses: actions/checkout@v4
      - name: Terraform Plan (drift check)
        run: |
          terraform init
          terraform plan -var-file="environments/${{ matrix.environment }}.tfvars" \
            -detailed-exitcode -out=/dev/null
        # Exit code 2 = changes detected (drift)
      - name: Alert on drift
        if: failure()
        run: |
          curl -X POST $SLACK_WEBHOOK -d '{"text":"⚠️ Terraform drift detected in ${{ matrix.environment }}"}'
```

---

## 4. Organization Setup

### 4.1 Azure Subscription & Management Group Structure

```
Root Management Group
├── Platform Management Group
│   ├── Connectivity Subscription
│   │   ├── Hub VNet (shared networking)
│   │   ├── DNS Zones
│   │   └── Firewall / ExpressRoute
│   │
│   └── Management Subscription
│       ├── Log Analytics Workspace (central)
│       ├── Sentinel
│       └── Automation Accounts
│
└── Workload Management Group
    └── GenAI Copilot Subscription
        ├── rg-genai-copilot-dev-{region}
        ├── rg-genai-copilot-staging-{region}
        ├── rg-genai-copilot-prod-{region}
        └── rg-terraform-state
```

### 4.2 Resource Group Naming Convention

```
rg-{workload}-{environment}-{region_code}

Examples:
rg-genai-copilot-dev-eus2      (East US 2, Development)
rg-genai-copilot-staging-eus2  (East US 2, Staging)
rg-genai-copilot-prod-eus2     (East US 2, Production)
rg-genai-copilot-prod-weu      (West Europe, Production DR)
```

### 4.3 Resource Naming Convention

```
{resource_type_prefix}-{workload}-{environment}-{region_code}

Prefixes:
  oai-   Azure OpenAI
  srch-  AI Search
  di-    Document Intelligence
  cs-    Content Safety
  aks-   AKS Cluster
  func-  Azure Functions
  acr-   Container Registry
  cosmos-Cosmos DB
  redis- Redis Cache
  st-    Storage Account
  kv-    Key Vault
  apim-  API Management
  agw-   Application Gateway
  bas-   Bastion
  vnet-  Virtual Network
  nsg-   Network Security Group
  pe-    Private Endpoint
  pip-   Public IP
  ai-    Application Insights
  law-   Log Analytics Workspace

Examples:
  oai-genai-copilot-prod-eus2
  srch-genai-copilot-prod-eus2
  aks-genai-copilot-prod-eus2
  kv-genai-copilot-prod-eus2
```

### 4.4 Tagging Strategy

| Tag | Required | Purpose | Example |
|-----|----------|---------|---------|
| `environment` | Yes | Environment classification | dev, staging, production |
| `workload` | Yes | Application name | genai-copilot |
| `cost-center` | Yes | Billing allocation | CC-AI-Platform |
| `owner` | Yes | Responsible team | platform-engineering |
| `managed-by` | Yes | IaC tool | terraform |
| `data-classification` | Yes | Data sensitivity | confidential |
| `created-date` | Yes | Provisioning date | 2024-11-15 |
| `sla-tier` | Prod only | SLA level | tier-1 |
| `dr-priority` | Prod only | Recovery priority | p1 |

### 4.5 Team Structure & RACI

| Role | Responsibilities |
|------|-----------------|
| **Platform Engineering** | Infrastructure, Terraform, AKS, networking |
| **ML Engineering** | RAG pipeline, model configuration, evaluation |
| **Security Engineering** | RBAC, encryption, pen testing, compliance |
| **DevOps Engineering** | CI/CD, monitoring, alerting, incident response |
| **Product Management** | Requirements, roadmap, stakeholder communication |
| **QA Engineering** | Testing strategy, golden datasets, quality gates |

| Activity | Platform | ML | Security | DevOps | Product | QA |
|----------|----------|-----|----------|--------|---------|-----|
| Infrastructure provisioning | **R/A** | C | C | I | I | I |
| RAG pipeline development | C | **R/A** | C | I | I | C |
| Security implementation | C | I | **R/A** | C | I | C |
| CI/CD pipeline | C | I | C | **R/A** | I | C |
| Quality evaluation | I | C | I | I | C | **R/A** |
| Production deployment | C | C | C | **R/A** | A | C |

---

## 5. Cloud Integration

### 5.1 Azure Service Integration Map

```
External Systems → Azure Integration Points:

[SharePoint Online]
     │ Microsoft Graph API
     ▼
[Azure Data Factory] ─── Pipeline ───→ [Azure Storage] → [Ingestion Function]

[On-Premises File Share]
     │ Azure File Sync / VPN
     ▼
[Azure Storage] → [Ingestion Function]

[Copilot Studio]
     │ Bot Framework
     ▼
[APIM Gateway] → [RAG Pipeline Functions]

[Power BI]
     │ Direct Query
     ▼
[Log Analytics] ← [App Insights] ← [Application Metrics]

[ServiceNow / Jira]
     │ Webhook
     ▼
[Logic Apps] ← [Sentinel Playbooks] ← [Security Alerts]

[Teams]
     │ Bot Framework / Adaptive Cards
     ▼
[Copilot Studio] → [APIM] → [RAG Pipeline]
```

### 5.2 Integration Patterns

| Pattern | Use Case | Implementation |
|---------|----------|---------------|
| **API Gateway** | External API access | APIM with JWT validation |
| **Event-Driven** | Document ingestion triggers | Event Grid → Functions |
| **Batch ETL** | SharePoint sync | Data Factory pipelines |
| **Webhook** | Incident notifications | Logic Apps → ServiceNow |
| **Direct Query** | Reporting | Power BI → Log Analytics |
| **Bot Framework** | Chat interface | Copilot Studio → APIM |

### 5.3 Authentication Patterns for Integration

| Source System | Auth Pattern | Token Flow |
|--------------|-------------|------------|
| Copilot Studio | OAuth 2.0 + Entra ID | User → Entra → JWT → APIM |
| Power BI | Service Principal | SP → Entra → Token → Log Analytics |
| Data Factory | Managed Identity | MI → Entra → Token → Storage |
| Logic Apps | Managed Identity | MI → Entra → Token → Sentinel |
| External API | Subscription Key + OAuth | Client → APIM subscription key + JWT |
| On-premises | Service Principal + VPN | SP → Entra → Token → Storage (via VPN) |

---

## 6. Deployment Strategy

### 6.1 Deployment Methods

| Method | When | Risk | Rollback |
|--------|------|------|----------|
| **Blue-Green** | Major releases | Low | Swap back to blue |
| **Canary** | Feature releases | Low | Redirect traffic back |
| **Rolling** | Minor updates | Medium | Rolling back pods |
| **Recreate** | Breaking changes (dev only) | High | Redeploy previous |

### 6.2 Blue-Green Deployment

```
Current State:
[App Gateway] → [Blue (v1.0)] ← Active
                 [Green (v1.1)] ← Staging

Deployment:
1. Deploy v1.1 to Green slot
2. Run smoke tests against Green
3. Run canary tests (internal traffic)
4. Switch App Gateway backend to Green
5. Monitor for 30 minutes
6. If issues: switch back to Blue (< 1 min)
7. If success: decommission Blue after 24 hours
```

### 6.3 Canary Deployment

```
Phase 1: 10% traffic
├── Deploy v1.1 to canary pods
├── Route 10% traffic via APIM weighted backend
├── Run canary validation tests
├── Compare error rate, latency, quality vs baseline
├── Duration: 30 minutes minimum
└── Auto-rollback if error rate > 5% or P95 > 5s

Phase 2: 50% traffic
├── If Phase 1 passes, increase to 50%
├── Monitor for 1 hour
├── Run quality evaluation
└── Auto-rollback if quality degrades > 5%

Phase 3: 100% traffic
├── If Phase 2 passes, promote to 100%
├── Monitor for 24 hours
└── Old version kept as rollback target
```

### 6.4 AKS Deployment (Helm)

```yaml
# values-production.yaml
replicaCount: 3

image:
  repository: acr-genai-copilot-prod.azurecr.io/rag-api
  tag: v1.1.0
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0

podDisruptionBudget:
  minAvailable: 2

env:
  - name: AZURE_KEY_VAULT_URL
    value: https://kv-genai-copilot-prod.vault.azure.net/
  - name: ENVIRONMENT
    value: production
```

### 6.5 Azure Functions Deployment

```bash
# Deploy Functions via Azure CLI
func azure functionapp publish func-pre-retrieval-prod-eus2 \
  --python --build remote

func azure functionapp publish func-rag-processor-prod-eus2 \
  --python --build remote

func azure functionapp publish func-ingestion-prod-eus2 \
  --python --build remote

# Or via GitHub Actions:
# - name: Deploy Azure Functions
#   uses: Azure/functions-action@v1
#   with:
#     app-name: func-pre-retrieval-prod-eus2
#     package: ./backend/azure-functions/pre-retrieval
```

---

## 7. Desktop-to-Cloud Integration

### 7.1 Migration Path

```
Phase 1: Local Development → Cloud Development
├── Developer machines use Docker Compose locally
├── Azure CLI + managed identity for cloud service access
├── VS Code with Azure Extensions
└── Local tests → remote staging tests via CI/CD

Phase 2: On-Premises Data → Cloud Storage
├── Azure File Sync for file shares
├── Data Factory for database migration
├── Azure Storage Explorer for manual uploads
└── VPN / ExpressRoute for secure connectivity

Phase 3: On-Premises Apps → Cloud Services
├── Containerize applications → ACR → AKS
├── Migrate SQL → Cosmos DB (where applicable)
├── Replace file-based caching → Redis
└── Replace local monitoring → App Insights

Phase 4: Full Cloud-Native
├── All workloads on AKS / Functions
├── All data in cloud (Storage, Cosmos DB)
├── All monitoring via App Insights / Log Analytics
└── On-premises: VPN connectivity for hybrid scenarios
```

### 7.2 Developer Desktop Setup

```bash
# Prerequisites
- Docker Desktop (for local development)
- Azure CLI 2.50+
- Terraform 1.5+
- Python 3.11+
- VS Code + Azure Extensions
- kubectl + Helm
- Git

# Local development environment
docker-compose up -d  # Starts local Redis, Cosmos DB emulator

# Connect to Azure (dev environment)
az login
az account set --subscription "GenAI-Copilot-Dev"

# Fetch secrets from Key Vault
export AZURE_OPENAI_KEY=$(az keyvault secret show \
  --vault-name kv-genai-copilot-dev --name openai-key --query value -o tsv)

# Run application locally
python -m uvicorn backend.main:app --reload --port 8000

# Run tests locally
pytest tests/unit/ -v
```

### 7.3 Hybrid Connectivity

| Connection Type | Use Case | Bandwidth | Latency |
|----------------|----------|-----------|---------|
| VPN Gateway | Dev team access, small data sync | Up to 1.25 Gbps | 10-30ms |
| ExpressRoute | Large data transfer, production hybrid | Up to 10 Gbps | 1-5ms |
| Azure File Sync | File share synchronization | Variable | Minutes |
| Data Factory | Batch data migration | Variable | Scheduled |

---

## 8. Infrastructure Setup

### 8.1 Step-by-Step Provisioning

```bash
# Step 1: Create Terraform state backend
az group create --name rg-terraform-state --location eastus2
az storage account create --name stterraformstate --resource-group rg-terraform-state \
  --sku Standard_LRS --encryption-services blob
az storage container create --name tfstate --account-name stterraformstate

# Step 2: Initialize Terraform
cd infrastructure/terraform
terraform init -backend-config="environments/dev.backend.hcl"

# Step 3: Plan (review changes)
terraform plan -var-file="environments/dev.tfvars" -out="dev.tfplan"

# Step 4: Apply
terraform apply "dev.tfplan"

# Step 5: Verify
terraform output  # Shows all output values (endpoints, IDs)

# Step 6: Configure application
# Secrets auto-populated in Key Vault by Terraform
# Application reads from Key Vault via managed identity
```

### 8.2 Post-Provisioning Validation

```bash
# Validate all services are running
az resource list --resource-group rg-genai-copilot-dev-eus2 \
  --output table

# Check private endpoint connectivity
az network private-endpoint list \
  --resource-group rg-genai-copilot-dev-eus2 --output table

# Verify Key Vault secrets
az keyvault secret list --vault-name kv-genai-copilot-dev --output table

# Check AKS cluster
az aks get-credentials --resource-group rg-genai-copilot-dev-eus2 \
  --name aks-genai-copilot-dev-eus2
kubectl get nodes
kubectl get pods --all-namespaces

# Check Functions
az functionapp list --resource-group rg-genai-copilot-dev-eus2 --output table
```

---

## 9. Infrastructure as Code Service

### 9.1 IaC Principles

| Principle | Implementation |
|-----------|---------------|
| **Declarative** | Terraform HCL defines desired state |
| **Version controlled** | All Terraform in Git |
| **Idempotent** | `terraform apply` produces same result regardless of runs |
| **Immutable** | Replace resources instead of mutating (where applicable) |
| **Modular** | Reusable modules per service category |
| **Tested** | `terraform validate`, `tflint`, `checkov` in CI |
| **Documented** | Variables have descriptions, modules have README |

### 9.2 IaC Pipeline

```yaml
# .github/workflows/terraform.yml
name: Terraform Pipeline

on:
  pull_request:
    paths: ['infrastructure/terraform/**']
  push:
    branches: [main]
    paths: ['infrastructure/terraform/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Terraform Format Check
        run: terraform fmt -check -recursive
      - name: Terraform Validate
        run: terraform validate
      - name: TFLint
        run: tflint --recursive
      - name: Checkov Security Scan
        run: checkov -d infrastructure/terraform/ --framework terraform

  plan:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - name: Terraform Plan
        run: terraform plan -var-file="environments/$ENV.tfvars" -out="plan.tfplan"
      - name: Post Plan to PR
        uses: actions/github-script@v7  # Comment plan output on PR

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: ${{ matrix.environment }}  # Requires approval
    steps:
      - name: Terraform Apply
        run: terraform apply "plan.tfplan"
```

### 9.3 IaC Security Scanning

| Tool | Purpose | Integration |
|------|---------|-------------|
| **Checkov** | Terraform security best practices | CI pipeline |
| **tfsec** | Terraform static analysis | CI pipeline |
| **TFLint** | Terraform linting and validation | CI pipeline + pre-commit |
| **Sentinel** (HashiCorp) | Policy-as-code | Terraform Cloud (optional) |
| **Azure Policy** | Runtime compliance enforcement | Azure subscription |

---

## 10. List of Services, Instances & Deployments

### 10.1 Complete Service Inventory

| # | Service | Resource Type | Dev Instance | Staging Instance | Production Instance |
|---|---------|--------------|-------------|-----------------|-------------------|
| 1 | Azure OpenAI | Cognitive Account | oai-*-dev | oai-*-staging | oai-*-prod |
| 2 | AI Search | Search Service | srch-*-dev | srch-*-staging | srch-*-prod |
| 3 | Document Intelligence | Cognitive Account | di-*-dev | di-*-staging | di-*-prod |
| 4 | Content Safety | Cognitive Account | cs-*-dev | cs-*-staging | cs-*-prod |
| 5 | AKS | Kubernetes Cluster | aks-*-dev | aks-*-staging | aks-*-prod |
| 6 | Functions (Pre-Retrieval) | Function App | func-pre-*-dev | func-pre-*-staging | func-pre-*-prod |
| 7 | Functions (RAG Processor) | Function App | func-rag-*-dev | func-rag-*-staging | func-rag-*-prod |
| 8 | Functions (Ingestion) | Function App | func-ing-*-dev | func-ing-*-staging | func-ing-*-prod |
| 9 | Container Registry | Container Registry | — (shared) | — (shared) | acr-*-prod |
| 10 | Cosmos DB | Database Account | cosmos-*-dev | cosmos-*-staging | cosmos-*-prod |
| 11 | Redis Cache | Redis Cache | redis-*-dev | redis-*-staging | redis-*-prod |
| 12 | Storage (Data Lake) | Storage Account | st*dev | st*staging | st*prod |
| 13 | Key Vault | Key Vault | kv-*-dev | kv-*-staging | kv-*-prod |
| 14 | VNet | Virtual Network | vnet-*-dev | vnet-*-staging | vnet-*-prod |
| 15 | App Gateway + WAF | Application Gateway | — | agw-*-staging | agw-*-prod |
| 16 | Bastion | Bastion Host | — | — | bas-*-prod |
| 17 | DDoS Protection | DDoS Plan | — | — | ddos-*-prod |
| 18 | APIM | API Management | apim-*-dev | apim-*-staging | apim-*-prod |
| 19 | App Insights | Application Insights | ai-*-dev | ai-*-staging | ai-*-prod |
| 20 | Log Analytics | Log Analytics WS | law-*-dev | law-*-staging | law-*-prod |
| 21 | Sentinel | Sentinel | — | — | sentinel-*-prod |
| 22 | Entra ID | Identity | Shared | Shared | Shared |
| 23 | Defender | Security Center | Shared | Shared | Shared |
| 24 | NSGs | Network Security | nsg-*-dev (5) | nsg-*-staging (5) | nsg-*-prod (5) |
| 25 | Private Endpoints | Private Endpoint | pe-*-dev (8) | pe-*-staging (8) | pe-*-prod (8) |
| 26 | Private DNS Zones | DNS Zone | Shared | Shared | Shared |
| 27 | Event Grid | System Topic | eg-*-dev | eg-*-staging | eg-*-prod |
| 28 | Data Factory | Data Factory | — | adf-*-staging | adf-*-prod |
| 29 | Purview | Microsoft Purview | — | — | purv-*-prod |

### 10.2 Model Deployments (Azure OpenAI)

| Model | Deployment Name | Dev TPM | Staging TPM | Prod TPM |
|-------|----------------|---------|-------------|----------|
| GPT-4o | gpt-4o | 10K | 40K | 80K |
| GPT-4o-mini | gpt-4o-mini | 20K | 60K | 120K |
| text-embedding-3-large | embedding-large | 50K | 150K | 350K |

### 10.3 Cosmos DB Containers (per environment)

| Container | Partition Key | Dev RU/s | Prod RU/s | TTL |
|-----------|-------------|----------|-----------|-----|
| conversations | /tenantId | 400 | 400-4000 | 90d |
| sessions | /tenantId | 400 | 400-2000 | 24h |
| evaluations | /tenantId | 400 | 400-1000 | 365d |
| feedback | /tenantId | 400 | 400-1000 | 730d |
| audit-events | /tenantId | 400 | 400-2000 | 2555d |
| tenant-config | /tenantId | 400 | 400 | None |
| model-metrics | /modelId | 400 | 400-1000 | 365d |

---

## 11. Zone Selection

### 11.1 Region Selection Criteria

| Criterion | Weight | Evaluation |
|-----------|--------|------------|
| Azure OpenAI model availability | 30% | GPT-4o, GPT-4o-mini, embeddings |
| AI Search SKU availability | 15% | S2 with semantic ranker |
| Data residency requirements | 20% | GDPR, data sovereignty |
| Latency to users | 15% | Proximity to user base |
| Cost | 10% | Regional pricing variations |
| DR paired region | 10% | Paired region availability |

### 11.2 Recommended Regions

| Scenario | Primary Region | DR Region | Justification |
|----------|---------------|-----------|---------------|
| North America (US) | East US 2 | West US 2 | Full OpenAI model availability, paired |
| North America (Canada) | Canada Central | Canada East | Data residency, OpenAI available |
| Europe (GDPR) | West Europe | North Europe | EU data residency, paired |
| UK | UK South | UK West | UK GDPR, paired |
| Asia Pacific | Japan East | Japan West | OpenAI available, paired |
| Australia | Australia East | Australia Southeast | Data residency, paired |

### 11.3 Availability Zone Strategy

```
Production:
├── Zone 1: AKS node pool (1-4 nodes), Cosmos DB replica
├── Zone 2: AKS node pool (1-3 nodes), Cosmos DB replica
└── Zone 3: AKS node pool (1-3 nodes), Cosmos DB replica

PaaS Services (zone-redundant):
├── AI Search: S2 with 3 replicas across zones
├── Cosmos DB: Multi-AZ write region
├── Redis Premium: Zone-redundant
├── Key Vault: Zone-redundant
├── Storage: ZRS (zone-redundant storage)
└── App Gateway: Multi-zone deployment
```

### 11.4 Service Availability by Region

| Service | East US 2 | West Europe | Japan East | Notes |
|---------|-----------|-------------|------------|-------|
| GPT-4o | ✅ | ✅ | ✅ | Check latest availability |
| GPT-4o-mini | ✅ | ✅ | ✅ | |
| text-embedding-3-large | ✅ | ✅ | ✅ | |
| AI Search S2 | ✅ | ✅ | ✅ | |
| Semantic Ranker | ✅ | ✅ | ✅ | |
| Document Intelligence | ✅ | ✅ | ✅ | |
| Content Safety | ✅ | ✅ | ✅ | |
| AKS (3 AZs) | ✅ | ✅ | ✅ | |
| Cosmos DB (Multi-AZ) | ✅ | ✅ | ✅ | |
| Premium Redis | ✅ | ✅ | ✅ | |

---

## 12. Service Creation Strategy

### 12.1 Service Creation Order

```
Creation follows dependency graph (Section 1.4):

Phase 1: Foundation (Day 1)
  1. Resource Group
  2. VNet + Subnets + NSGs
  3. Key Vault (for secrets during setup)
  4. Storage Account (Data Lake)
  5. Log Analytics Workspace

Phase 2: Security & Networking (Day 1-2)
  6. Private DNS Zones
  7. Application Gateway + WAF
  8. DDoS Protection Plan
  9. Entra ID App Registrations

Phase 3: Data Services (Day 2-3)
  10. Cosmos DB Account + Containers + Private Endpoint
  11. Redis Cache + Private Endpoint
  12. AI Search + Index + Private Endpoint
  13. Document Intelligence + Private Endpoint

Phase 4: AI & Compute (Day 3-4)
  14. Azure OpenAI + Model Deployments + Private Endpoint
  15. Content Safety + Private Endpoint
  16. ACR + Private Endpoint
  17. AKS Cluster (depends on VNet, ACR, Key Vault)
  18. Azure Functions (3 apps, depends on VNet, Storage, Key Vault)

Phase 5: Integration & Monitoring (Day 4-5)
  19. APIM
  20. Application Insights
  21. Sentinel
  22. Defender Plans
  23. Alert Rules + Action Groups
  24. Bastion
  25. Event Grid Subscriptions
  26. Data Factory (if needed)
```

### 12.2 Service Creation Pre-Checks

```bash
# Before creating any service, verify:

# 1. Subscription quota
az vm list-usage --location eastus2 -o table
az cognitiveservices account list-usage --name oai-* --resource-group rg-*

# 2. Resource provider registration
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.DocumentDB
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.Web

# 3. Region availability
az cognitiveservices account list-skus --kind OpenAI --location eastus2
az search service list-skus --location eastus2

# 4. Naming availability
az cognitiveservices account check-name --name oai-genai-copilot-prod
az storage account check-name --name stgenaicopilotprod
```

### 12.3 Service Creation Validation

| Service | Validation Check | Command/Method |
|---------|-----------------|----------------|
| OpenAI | Model deployment accessible | `az cognitiveservices deployment list` |
| AI Search | Index created, searchable | Search explorer query |
| Cosmos DB | Container created, RU/s configured | `az cosmosdb sql container show` |
| AKS | Nodes ready, pods running | `kubectl get nodes && kubectl get pods` |
| Functions | Health endpoint returns 200 | `curl https://func-*/health` |
| Key Vault | Secrets accessible | `az keyvault secret list` |
| Private Endpoints | DNS resolution works | `nslookup *.privatelink.*` |
| Redis | Connection test passes | `redis-cli ping` |

### 12.4 Rollback Strategy for Failed Creation

```
If service creation fails:

1. Terraform: `terraform destroy -target=module.failed_module`
   - Targeted destroy of failed resource only
   - Re-run `terraform apply` after fixing

2. Manual (if Terraform state is inconsistent):
   - `terraform state rm module.failed_resource`
   - Delete resource manually via Azure CLI
   - Re-import or recreate via Terraform

3. Full environment rollback:
   - Only for dev/staging (never delete production)
   - `terraform destroy -var-file="environments/dev.tfvars"`
   - Recreate from scratch
```

---

## 13. Service Deletion Strategy

### 13.1 Deletion Safety Framework

```
Deletion Risk Matrix:

HIGH RISK (requires double approval):
├── Cosmos DB (data loss)
├── Storage Account (data loss)
├── Key Vault (secret loss — soft delete protects for 90 days)
├── AI Search (index loss — rebuild from source)
└── Production anything

MEDIUM RISK (requires single approval):
├── AKS Cluster (stateless, rebuildable)
├── Functions (code in Git, rebuildable)
├── Redis Cache (cache only, rebuildable)
├── APIM (configuration in Git)
└── Staging services

LOW RISK (self-service):
├── Dev environment services
├── Private endpoints (rebuildable)
├── NSGs (defined in Terraform)
└── Log Analytics (data loss acceptable for dev)
```

### 13.2 Deletion Process

```
Service Deletion Procedure:

1. PRE-DELETION CHECKS
   □ Confirm no active users/traffic
   □ Verify data backup exists (if applicable)
   □ Confirm deletion is in approved change window
   □ Verify no dependent services will break
   □ Get required approvals (per risk matrix)

2. DATA PRESERVATION
   □ Export data from Cosmos DB containers
   □ Export AI Search index to Storage
   □ Backup Key Vault secrets
   □ Archive relevant logs from Log Analytics
   □ Export APIM configuration

3. DEPENDENCY REMOVAL
   □ Remove private endpoints referencing this service
   □ Update DNS records
   □ Remove references in other service configurations
   □ Update Terraform state

4. DELETION
   □ Terraform: `terraform destroy -target=module.service`
   □ Or: Remove from Terraform config + `terraform apply`

5. POST-DELETION VERIFICATION
   □ Confirm resource is deleted
   □ Verify no orphaned resources (PEs, DNS records)
   □ Verify no broken dependencies
   □ Update documentation
   □ Update cost forecasts

6. SOFT DELETE RECOVERY (if mistake)
   □ Key Vault: 90-day soft delete recovery
   □ Cosmos DB: Point-in-time restore (30 days)
   □ Storage: Soft delete recovery (7-30 days)
   □ AI Search: No soft delete — rebuild from source
```

### 13.3 Environment Teardown

```bash
# Dev environment full teardown
# WARNING: Destroys all resources in dev

# 1. Verify targeting correct environment
terraform workspace select dev
terraform plan -var-file="environments/dev.tfvars" -destroy

# 2. Review plan output carefully
# 3. Execute destroy
terraform destroy -var-file="environments/dev.tfvars" -auto-approve

# 4. Verify
az resource list --resource-group rg-genai-copilot-dev-eus2 --output table
# Should return empty

# 5. Optionally delete resource group
az group delete --name rg-genai-copilot-dev-eus2 --yes
```

### 13.4 Service Decommissioning Checklist

| Step | Action | Owner | Verification |
|------|--------|-------|-------------|
| 1 | Redirect traffic away from service | DevOps | Monitor shows zero traffic |
| 2 | Wait for drain period (24 hours) | DevOps | No requests in logs |
| 3 | Export data/configuration | Platform | Backup verified |
| 4 | Remove from monitoring/alerts | DevOps | No false alerts |
| 5 | Remove from Terraform | Platform | Plan shows only destroy |
| 6 | Execute deletion | Platform | Resource gone |
| 7 | Clean up DNS, PEs, references | Platform | No orphaned resources |
| 8 | Update documentation | All | Docs current |
| 9 | Update cost forecasts | FinOps | Budget adjusted |
| 10 | Close decommission ticket | PM | Ticket closed |

---

## 14. Smoke Testing Strategy (Infra)

### 14.1 Infrastructure Smoke Tests

```bash
#!/bin/bash
# infrastructure/scripts/smoke-test-infra.sh

echo "=== Infrastructure Smoke Tests ==="

# 1. VNet connectivity
echo "Testing VNet..."
az network vnet show -g $RG -n $VNET --query "provisioningState" -o tsv
# Expected: Succeeded

# 2. AKS cluster health
echo "Testing AKS..."
kubectl get nodes -o wide
kubectl get pods -n kube-system --field-selector=status.phase!=Running
# Expected: All nodes Ready, no non-Running system pods

# 3. Private endpoint DNS resolution
echo "Testing Private Endpoints..."
for service in openai search cosmos keyvault redis storage acr docint; do
  nslookup $service_hostname | grep "10.0.17"
  # Expected: Resolves to private endpoint IP
done

# 4. Key Vault access
echo "Testing Key Vault..."
az keyvault secret list --vault-name $KV_NAME --query "length(@)" -o tsv
# Expected: > 0

# 5. Cosmos DB connectivity
echo "Testing Cosmos DB..."
az cosmosdb sql database list --account-name $COSMOS --resource-group $RG -o table
# Expected: Lists databases

# 6. Redis connectivity
echo "Testing Redis..."
redis-cli -h $REDIS_HOST -p 6380 -a $REDIS_KEY --tls ping
# Expected: PONG

# 7. AI Search health
echo "Testing AI Search..."
curl -s "https://$SEARCH_HOST/indexes?api-version=2024-07-01" \
  -H "api-key: $SEARCH_KEY" | jq '.value | length'
# Expected: > 0

# 8. Functions health
echo "Testing Functions..."
for func in pre-retrieval rag-processor ingestion; do
  curl -s -o /dev/null -w "%{http_code}" "https://func-$func-$ENV/health"
  # Expected: 200
done

# 9. APIM gateway
echo "Testing APIM..."
curl -s -o /dev/null -w "%{http_code}" "https://apim-$NAME/status-0123456789abcdef"
# Expected: 200

echo "=== Smoke Tests Complete ==="
```

### 14.2 Post-Deployment Infra Validation

| Test | Command | Expected Result |
|------|---------|----------------|
| Resource count | `az resource list -g $RG --query "length(@)"` | 29+ resources |
| NSG rules applied | `az network nsg rule list` | Rules per security-layers.md |
| Encryption enabled | `az storage account show --query "encryption"` | CMK enabled |
| Diagnostic settings | `az monitor diagnostic-settings list` | All services logging |
| Tags applied | `az resource list --query "[?tags.environment]"` | All resources tagged |

---

## 15. Trust AI — Infrastructure Perspective

### 15.1 Trusted Infrastructure Components

| Component | Trust Mechanism | Verification |
|-----------|----------------|-------------|
| **AKS Workload Identity** | Pods authenticate via Entra ID | No secrets in pods |
| **Key Vault HSM** | FIPS 140-2 Level 2 hardware | Key operations audited |
| **Private Endpoints** | No public internet exposure | Network scan confirms |
| **TLS 1.2+** | Encrypted communication | SSL scan report |
| **CMK Encryption** | Customer-managed keys | Key Vault audit logs |
| **Managed Identity** | No password/key management | Zero secrets in code |
| **RBAC** | Least privilege access | Access review quarterly |

### 15.2 Trust Verification Pipeline

```yaml
# Trust verification runs weekly
- name: Verify Trust Controls
  steps:
    - Verify all PEs are connected and DNS resolving
    - Verify no public endpoints on PaaS services
    - Verify all encryption is CMK-based
    - Verify all pods use Workload Identity
    - Verify Key Vault access policies are minimal
    - Verify NSG rules match approved baseline
    - Verify Defender security score ≥ 90%
    - Verify no secrets in code (detect-secrets scan)
```

---

## 16. Explainable AI — Infrastructure Perspective

### 16.1 Infrastructure Observability for AI Explainability

| What to Explain | Infrastructure Support | Service |
|----------------|----------------------|---------|
| Why was this document retrieved? | Search score logs, filter audit | AI Search + App Insights |
| Why did the model give this answer? | Token usage, model config audit | OpenAI + App Insights |
| Why was PII masked? | PII detection logs, entity details | Functions + Cosmos DB audit |
| Why was content blocked? | Content Safety severity scores | Content Safety + App Insights |
| Why was the response slow? | Distributed trace with latency | App Insights (full trace) |
| Why was this user denied access? | RBAC evaluation logs, ACL details | Entra ID + AI Search |

### 16.2 Explainability Data Flow

```
Every query generates:
1. App Insights: Operation trace (full latency breakdown)
2. AI Search: Search scores per result (pre/post rerank)
3. OpenAI: Token usage, model version, parameters used
4. Cosmos DB: Audit event (documents accessed, PII detected)
5. Redis: Cache hit/miss for each tier
6. Log Analytics: Aggregated metrics for dashboards

Accessible at 4 levels:
- End User: Confidence score + citations
- Analyst: + search scores, retrieval details
- Engineer: + full trace, token usage, latency breakdown
- Auditor: + PII events, RBAC decisions, full audit trail
```

---

## Cross-References

- [TECH-STACK-SERVICES.md](../reference/TECH-STACK-SERVICES.md) — Service inventory
- [AZURE-SERVICE-DEEP-DIVE.md](../reference/AZURE-SERVICE-DEEP-DIVE.md) — Per-service details
- [FINOPS-COST-MANAGEMENT.md](./FINOPS-COST-MANAGEMENT.md) — Cost management
- [SECURITY-LAYERS.md](../security/SECURITY-LAYERS.md) — Security architecture
- [TESTING-STRATEGY.md](../testing/TESTING-STRATEGY.md) — Testing approach
- [PROJECT-BUSINESS-CASE.md](../architecture/PROJECT-BUSINESS-CASE.md) — Business case
- [DEMO-PLAYBOOK.md](../reference/DEMO-PLAYBOOK.md) — Demo scenarios
- [INTERVIEW-KNOWLEDGE-GUIDE.md](../reference/INTERVIEW-KNOWLEDGE-GUIDE.md) — Interview Q&A
