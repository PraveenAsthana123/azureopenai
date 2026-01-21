# Infrastructure Plan
## Enterprise GenAI Knowledge Copilot Platform

**Version:** 1.0
**Date:** November 2025
**Region:** Japan East (japaneast)

---

## 1. Infrastructure Overview

### 1.1 Deployment Summary

| Attribute | Value |
|-----------|-------|
| Cloud Provider | Microsoft Azure |
| Region | Japan East (japaneast) |
| Environment | Development (dev) |
| IaC Tool | Terraform >= 1.5.0 |
| Total Resources | 62 |
| Resource Group | rg-genai-copilot-dev-jpe |

### 1.2 Resource Suffix

All resources use unique suffix: `rwc3az`

---

## 2. Compute Infrastructure

### 2.1 Virtual Machines

| Attribute | Configuration |
|-----------|---------------|
| Name | vm-genai-copilot-0 |
| Size | Standard_D2s_v3 |
| vCPUs | 2 |
| Memory | 8 GB |
| OS | Ubuntu 22.04 LTS |
| Disk | 128 GB Premium SSD |
| Private IP | 10.0.2.4 |
| Public IP | None (Bastion access) |
| Admin User | azureadmin |

### 2.2 Azure Bastion

| Attribute | Configuration |
|-----------|---------------|
| Name | bastion-genai-copilot-dev |
| SKU | Standard |
| Subnet | AzureBastionSubnet (10.0.0.0/26) |
| Public IP | pip-bastion-genai-copilot-dev |

---

## 3. Networking Infrastructure

### 3.1 Virtual Network

```
┌─────────────────────────────────────────────────────────────┐
│           vnet-genai-copilot-dev-jpe (10.0.0.0/16)          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ AzureBastionSubnet  │  │ snet-privateendpoints       │  │
│  │    10.0.0.0/26      │  │      10.0.1.0/24            │  │
│  │   (64 addresses)    │  │    (256 addresses)          │  │
│  │                     │  │                             │  │
│  │  - Azure Bastion    │  │  - Private Endpoints:       │  │
│  │                     │  │    - Cosmos DB              │  │
│  └─────────────────────┘  │    - Storage                │  │
│                           │    - Key Vault              │  │
│                           │    - AI Services            │  │
│                           │    - AI Search              │  │
│                           └─────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │     snet-vm         │  │     snet-functions          │  │
│  │   10.0.2.0/24       │  │      10.0.3.0/24            │  │
│  │  (256 addresses)    │  │    (256 addresses)          │  │
│  │                     │  │                             │  │
│  │  - Linux VMs        │  │  - Azure Functions          │  │
│  │  - Application      │  │    (Future)                 │  │
│  │    workloads        │  │                             │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Private DNS Zones

| DNS Zone | Purpose |
|----------|---------|
| privatelink.cognitiveservices.azure.com | Cognitive Services |
| privatelink.openai.azure.com | Azure OpenAI |
| privatelink.search.windows.net | AI Search |
| privatelink.documents.azure.com | Cosmos DB |
| privatelink.blob.core.windows.net | Blob Storage |
| privatelink.vaultcore.azure.net | Key Vault |

---

## 4. Data Infrastructure

### 4.1 Azure Cosmos DB

| Attribute | Configuration |
|-----------|---------------|
| Name | cosmos-genai-copilot-dev-rwc3az |
| API | SQL (Core) |
| Capacity Mode | Serverless |
| Consistency | Session |
| Multi-region | Disabled |
| Backup | Periodic (24h retention) |

### 4.2 Azure Storage Account

| Attribute | Configuration |
|-----------|---------------|
| Name | stgenaicopilotdevrwc3az |
| Performance | Standard |
| Replication | LRS |
| Access Tier | Hot |
| TLS Version | 1.2 |

---

## 5. AI Services Infrastructure

### 5.1 Cognitive Services

| Service | SKU | Endpoint |
|---------|-----|----------|
| Document Intelligence | S0 | di-genai-copilot-dev-rwc3az.cognitiveservices.azure.com |
| Computer Vision | S1 | cv-genai-copilot-dev-rwc3az.cognitiveservices.azure.com |
| Speech Services | S0 | speech-genai-copilot-dev-rwc3az.cognitiveservices.azure.com |

### 5.2 Azure AI Search

| Attribute | Configuration |
|-----------|---------------|
| Name | search-genai-copilot-dev-rwc3az |
| SKU | Standard |
| Replicas | 1 |
| Partitions | 1 |
| Semantic Search | Enabled |

---

## 6. Security Infrastructure

### 6.1 Azure Key Vault

| Attribute | Configuration |
|-----------|---------------|
| Name | kv-genai-copilot-rwc3az |
| SKU | Standard |
| Soft Delete | Enabled (90 days) |
| Purge Protection | Enabled |

---

## 7. Monitoring Infrastructure

### 7.1 Log Analytics Workspace

| Attribute | Configuration |
|-----------|---------------|
| Name | log-genai-copilot-dev-rwc3az |
| SKU | PerGB2018 |
| Retention | 30 days |

### 7.2 Application Insights

| Attribute | Configuration |
|-----------|---------------|
| Name | appi-genai-copilot-dev-rwc3az |
| Workspace Mode | Connected to Log Analytics |

---

## 8. Cost Estimation

### 8.1 Monthly Cost Breakdown (Estimated)

| Service | SKU | Est. Monthly Cost |
|---------|-----|-------------------|
| Azure Bastion | Standard | $140 |
| Virtual Machine | D2s_v3 | $80 |
| AI Search | Standard | $250 |
| Document Intelligence | S0 | $50 |
| Computer Vision | S1 | $30 |
| Speech Services | S0 | $20 |
| Cosmos DB | Serverless | ~$5-50 (usage) |
| Storage | Standard LRS | ~$5-20 |
| Key Vault | Standard | ~$1 |
| Log Analytics | PerGB | ~$5-20 |
| **Total Estimated** | | **~$600-650/month** |

---

## 9. Terraform Module Structure

```
infrastructure/terraform/
├── main.tf                 # Root module
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── terraform.tfvars        # Variable values
└── modules/
    ├── networking/         # VNet, subnets, NSGs, DNS
    ├── storage/            # Storage account, containers
    ├── database/           # Cosmos DB
    ├── ai-services/        # Cognitive Services, AI Search
    ├── compute/            # VMs, Functions
    └── monitoring/         # Log Analytics, App Insights, Key Vault
```

---

## 10. Deployment Commands

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply deployment
terraform apply tfplan

# Destroy infrastructure
terraform destroy

# Show current state
terraform show

# List resources
terraform state list
```
