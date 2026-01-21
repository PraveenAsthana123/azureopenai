# Azure OpenAI Enterprise Platform - Terraform Infrastructure

> **Infrastructure as Code for Enterprise AI/GenAI/RAG Platform**
>
> Aligned with: CMMI L3, ISO 42001, NIST AI RMF, Zero-Trust Architecture

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Azure OpenAI Enterprise Platform                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Azure      │  │   Azure      │  │   Azure      │  │  Document    │    │
│  │   OpenAI     │  │   AI Search  │  │   Functions  │  │  Intelligence│    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│           │                │                │                │              │
│           └────────────────┴────────────────┴────────────────┘              │
│                                    │                                         │
│                        ┌───────────┴───────────┐                            │
│                        │   Private Endpoints    │                            │
│                        └───────────┬───────────┘                            │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────┐     │
│  │                     Virtual Network (Zero Trust)                    │     │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │     │
│  │  │   AKS   │  │Functions│  │ Private │  │ Bastion │  │App GW   │ │     │
│  │  │ Subnet  │  │ Subnet  │  │Endpoints│  │ Subnet  │  │ Subnet  │ │     │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Key Vault   │  │   Storage    │  │     ACR      │  │Log Analytics │    │
│  │  (Secrets)   │  │ (Data Lake)  │  │ (Containers) │  │ (Monitoring) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
terraform/
├── main.tf                 # Main orchestration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── modules/
│   ├── networking/         # VNet, Subnets, NSGs, Private DNS
│   ├── security/           # Key Vault, Managed Identities, RBAC
│   ├── ai-services/        # Azure OpenAI, AI Search, Document Intelligence
│   ├── monitoring/         # Log Analytics, App Insights, Alerts
│   ├── compute/            # AKS, Functions, ACR
│   └── storage/            # Data Lake Gen2, Blob Storage
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

---

## Quick Start

### Prerequisites

- Azure CLI installed and authenticated
- Terraform >= 1.5.0
- Azure subscription with required permissions

### 1. Initialize Backend (First Time)

```bash
# Create storage account for state
az group create -n rg-terraform-state -l eastus2
az storage account create -n stterraformstate -g rg-terraform-state -l eastus2 --sku Standard_LRS
az storage container create -n tfstate --account-name stterraformstate
```

### 2. Deploy Infrastructure

```bash
# Development
cd terraform
terraform init -backend-config="environments/dev/backend.tfvars"
terraform plan -var-file="environments/dev/terraform.tfvars"
terraform apply -var-file="environments/dev/terraform.tfvars"

# Production
terraform init -backend-config="environments/prod/backend.tfvars"
terraform plan -var-file="environments/prod/terraform.tfvars"
terraform apply -var-file="environments/prod/terraform.tfvars"
```

---

## Security Controls (Zero Trust)

| Control | Implementation |
|---------|----------------|
| Network Isolation | Private VNet, NSGs, Private Endpoints |
| Identity | Azure AD, Managed Identities, No local auth |
| Secrets | Key Vault, RBAC, No keys in code |
| Data | Encryption at rest/transit, Soft delete |
| Monitoring | Log Analytics, Sentinel, Alerts |
| Access | JIT, Least privilege, MFA |

---

## Compliance Alignment

| Framework | Coverage |
|-----------|----------|
| **ISO 42001** | AI governance, risk assessment, data controls |
| **NIST AI RMF** | Map, Measure, Manage, Govern functions |
| **CMMI L3** | Defined processes, change management |
| **NIST 800-53** | Security controls, access management |

---

## Resource Naming Convention

```
{resource-type}-{project}-{environment}[-{region}][-{instance}]

Examples:
- rg-aoai-prod              (Resource Group)
- vnet-aoai-prod            (Virtual Network)
- kv-aoaiprod               (Key Vault - no hyphens)
- oai-aoai-prod             (Azure OpenAI)
- aks-aoai-prod             (AKS Cluster)
```

---

## Environment Differences

| Resource | Dev | Staging | Prod |
|----------|-----|---------|------|
| AKS Nodes | 2 | 2 | 3+ |
| AKS VM Size | D2s_v3 | D2s_v3 | D4s_v3 |
| OpenAI Capacity | Low | Medium | High |
| AI Search SKU | Basic | Basic | Standard |
| Key Vault SKU | Standard | Standard | Premium |
| Storage Replication | LRS | LRS | GRS |
| Log Retention | 90 days | 90 days | 365 days |
| DDoS Protection | No | No | Yes |
| Bastion | No | No | Yes |
| Sentinel | No | No | Yes |

---

## Outputs Reference

After deployment, access key outputs:

```bash
# Get all outputs
terraform output

# Specific outputs
terraform output openai_endpoint
terraform output aks_cluster_name
terraform output -json connection_info
```

---

## Cost Optimization

| Tip | Implementation |
|-----|----------------|
| Right-size AKS | Use autoscaling, smaller VMs in dev |
| OpenAI Quota | Match capacity to actual usage |
| Storage Lifecycle | Archive old documents, delete processed |
| Reserved Instances | For production AKS nodes |
| Dev/Test Pricing | Use dev/test subscriptions |

---

## Troubleshooting

### Common Issues

1. **OpenAI Region Availability**
   - Check [Azure OpenAI availability](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#model-summary-table-and-region-availability)
   - Update `openai_location` variable

2. **Quota Limits**
   - Request quota increase in Azure portal
   - Reduce `capacity` in deployments

3. **Private Endpoint DNS**
   - Ensure Private DNS zones linked to VNet
   - Check DNS resolution from within VNet

---

## Maintenance

### Regular Tasks

- [ ] Review and rotate secrets (quarterly)
- [ ] Update Kubernetes version (monthly)
- [ ] Review access permissions (quarterly)
- [ ] Test disaster recovery (annually)
- [ ] Update Terraform providers (monthly)

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Last Updated | 2024-01 |
| Owner | Platform Team |
| Classification | Internal |
