# Enterprise AI Platform - Zero-Trust Infrastructure

## Overview

This Terraform configuration deploys a complete enterprise-grade AI platform on Azure with Zero-Trust security architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE AI PLATFORM - ZERO-TRUST ARCHITECTURE              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  VNET (10.10.0.0/16)                             │
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ App Subnet  │  │ AI Subnet   │  │ Search Snet │  │ Data Subnet              │ │
│  │ 10.10.1.0/24│  │ 10.10.2.0/24│  │ 10.10.3.0/24│  │ 10.10.4.0/24            │ │
│  │             │  │             │  │             │  │                          │ │
│  │ - Functions │  │ - OpenAI PE │  │ - Search PE │  │ - ADLS PE (blob/dfs)    │ │
│  │ - APIM      │  │             │  │             │  │ - Cosmos PE             │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  │ - SQL PE                │ │
│                                                      │ - Key Vault PE          │ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  └─────────────────────────┘ │
│  │ Compute Snet│  │ Integration │  │ Firewall    │                              │
│  │ 10.10.5.0/24│  │ 10.10.6.0/24│  │ 10.10.7.0/24│                              │
│  │             │  │             │  │             │                              │
│  │ - AKS       │  │ - Function  │  │ (Reserved)  │                              │
│  │ - ACR PE    │  │   PE        │  │             │                              │
│  └─────────────┘  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PRIVATE DNS ZONES                                   │
│  privatelink.openai.azure.com    │  privatelink.blob.core.windows.net          │
│  privatelink.search.windows.net  │  privatelink.dfs.core.windows.net           │
│  privatelink.vaultcore.azure.net │  privatelink.documents.azure.com            │
│  privatelink.database.windows.net│  privatelink.azurecr.io                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Phase 1: Networking & Zero Trust
- Virtual Network with 7 subnets
- Network Security Groups (NSGs) per subnet
- Route Tables (UDRs)
- Private DNS Zones (8 zones)

### Phase 2: Security
- Key Vault (private, RBAC-enabled)
- User-Assigned Managed Identities (4 identities)
- RBAC role assignments

### Phase 3: Data Layer
- ADLS Gen2 (HNS-enabled, GRS replication)
- Cosmos DB (serverless, session consistency)
- Azure SQL (metadata/config store)
- Private endpoints for all data services

### Phase 4: AI Layer
- Azure OpenAI (private, AAD-only auth)
- Azure AI Search (standard, replicated)
- Model deployments via AzAPI (GPT-4o, embeddings)

### Phase 5: Compute
- Azure Container Registry (Premium, private)
- AKS (private cluster, workload identity)
- AI worker node pool

### Phase 6: Application
- Function App (Premium, VNet-integrated)
- API Management (Internal mode)
- APIM policies (rate limiting, CORS)

### Phase 7: Monitoring
- Log Analytics Workspace
- Application Insights
- Metric alerts (latency, errors, RUs)
- Container Insights
- Security Insights (Sentinel)

## Deployment

### Prerequisites

1. Azure CLI installed and logged in
2. Terraform >= 1.6.0
3. Azure subscription with required permissions
4. Service Principal for CI/CD (optional)

### Setup Terraform State Backend

```bash
# Create storage account for Terraform state
az group create -n terraform-state-rg -l eastus
az storage account create -n tfstateenterprise -g terraform-state-rg -l eastus --sku Standard_LRS
az storage container create -n tfstate --account-name tfstateenterprise
```

### Initialize and Deploy

```bash
cd infrastructure/terraform/enterprise

# Initialize Terraform
terraform init

# Create a terraform.tfvars file
cat > terraform.tfvars << EOF
prefix      = "ent-ai"
environment = "prod"
location    = "eastus"
location_dr = "centralus"

sql_admin_password = "YourSecurePassword123!"

tags = {
  project     = "enterprise-ai-platform"
  env         = "prod"
  owner       = "ai-team"
  cost_center = "ai-platform"
}
EOF

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

## Post-Deployment Checklist

After `terraform apply` completes:

### 1. Verify Private Endpoint DNS Resolution
```bash
# Test from within VNet (via Bastion/VM)
nslookup <openai-name>.openai.azure.com
nslookup <search-name>.search.windows.net
nslookup <storage-name>.blob.core.windows.net
```

### 2. Create AI Search Indexes
```bash
# AI Search indexes must be created separately (not supported in Terraform)
# Use CLI, SDK, or ARM template
./scripts/create-search-indexes.sh
```

### 3. Get AKS Credentials
```bash
az aks get-credentials -g ent-ai-prod-rg -n ent-ai-prod-aks --admin
kubectl get nodes
```

### 4. Push Container Images to ACR
```bash
az acr login -n entaiprodacr
docker tag myimage:latest entaiprodacr.azurecr.io/myimage:latest
docker push entaiprodacr.azurecr.io/myimage:latest
```

### 5. Deploy AKS Workloads
```bash
kubectl apply -f k8s/reranker-deployment.yaml
kubectl apply -f k8s/embedding-worker-deployment.yaml
```

### 6. Publish Function App
```bash
func azure functionapp publish ent-ai-prod-fn-orchestrator
```

### 7. Configure APIM Policies
```bash
# Import API specifications
# Configure OAuth2/OIDC
# Set up rate limits
```

### 8. Smoke Tests
```bash
# Test OpenAI endpoint
curl -X POST https://<apim-gateway>/ai/chat \
  -H "Ocp-Apim-Subscription-Key: xxx" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Security Features

| Feature | Implementation |
|---------|---------------|
| Network Isolation | All services use private endpoints |
| Zero Public Access | `public_network_access_enabled = false` |
| Identity-Based Auth | Managed Identities + RBAC |
| Encryption at Rest | Azure-managed keys (CMK optional) |
| Encryption in Transit | TLS 1.2+ enforced |
| Audit Logging | Diagnostic settings to Log Analytics |
| Threat Detection | SQL Advanced Threat Protection |

## Cost Estimation

| Component | SKU | Monthly Cost (USD) |
|-----------|-----|-------------------|
| Azure OpenAI | S0 | $500-5,000* |
| AI Search | Standard (2 replicas) | $500 |
| AKS | Standard_DS3_v2 (2+1 nodes) | $300 |
| Cosmos DB | Serverless | $50-500* |
| Azure SQL | S2 | $75 |
| Function App | EP1 | $180 |
| APIM | Developer | $50 |
| Storage | Standard GRS | $50 |
| **Total (Base)** | | **$1,700+** |

*Usage-dependent

## Troubleshooting

### Private Endpoint DNS Not Resolving
- Verify Private DNS Zone links to VNet
- Check if DNS query is from within VNet
- Validate Private Endpoint provisioning state

### AKS Cannot Pull from ACR
- Verify AcrPull role assignment
- Check ACR network rules allow AKS subnet
- Validate ACR private endpoint

### Function App Cannot Reach OpenAI
- Verify VNet integration is enabled
- Check NSG rules allow outbound
- Validate managed identity has OpenAI User role

## File Structure

```
enterprise/
├── providers.tf      # Terraform + Azure providers
├── backend.tf        # Remote state configuration
├── variables.tf      # Input variables
├── main.tf           # Resource groups + locals
├── network.tf        # VNet, subnets, NSGs, DNS
├── security.tf       # Key Vault, managed identities
├── data.tf           # ADLS, Cosmos DB, SQL
├── ai.tf             # OpenAI, AI Search
├── compute.tf        # ACR, AKS
├── app.tf            # Functions, APIM
├── monitoring.tf     # Log Analytics, alerts
├── outputs.tf        # Output values
└── README.md         # This file
```

## Support

For issues or enhancements, contact the AI Platform team.
