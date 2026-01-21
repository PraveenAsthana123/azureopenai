# Enterprise GenAI Knowledge Copilot - Deployment Guide

## Overview

This guide covers deploying the GenAI Knowledge Copilot platform to Azure, including:
- Infrastructure provisioning with Terraform
- Azure Functions deployment (Serverless)
- VM-based frontend deployment
- CI/CD setup with Azure DevOps

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        End Users                                 │
│                   (Web Browser / Teams)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Load Balancer                          │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   VM Backend 1  │ │   VM Backend 2  │ │  (Serverless)   │
│   (Frontend +   │ │   (Frontend +   │ │ Azure Functions │
│    Nginx)       │ │    Nginx)       │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Azure AI Services                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ OpenAI   │ │ AI Search│ │ Doc Intel│ │ Computer │           │
│  │ GPT-4o   │ │ (Vector) │ │  (OCR)   │ │  Vision  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │ Cosmos DB│ │   Blob   │ │ Key Vault│                        │
│  │ (NoSQL)  │ │ Storage  │ │ (Secrets)│                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Local Development Machine

1. **Azure CLI** (v2.50+)
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

2. **Terraform** (v1.5+)
   ```bash
   sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt-get update && sudo apt-get install -y terraform
   ```

3. **Azure Functions Core Tools** (v4)
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

4. **Node.js** (v20+) and **Python** (v3.11+)

### Azure Requirements

- Azure Subscription with Contributor access
- Azure AD App Registration (for authentication)
- Sufficient quota for:
  - Azure OpenAI (GPT-4o, GPT-4o-mini, text-embedding-3-large)
  - Azure AI Search (Standard tier)
  - Virtual Machines (Standard_D4s_v3)

## Quick Start

### 1. Setup Azure CLI and Login

```bash
# Run the setup script
chmod +x scripts/deployment/setup-azure-cli.sh
./scripts/deployment/setup-azure-cli.sh
```

This script will:
- Install all prerequisites
- Login to Azure
- Set your subscription
- Create Terraform backend storage

### 2. Deploy Infrastructure

```bash
# Initialize and deploy to dev environment
./scripts/deployment/deploy-infrastructure.sh -e dev -a apply -p "YourVMPassword123!"
```

### 3. Deploy Azure Functions

```bash
# Deploy all function apps
./scripts/deployment/deploy-functions.sh -e dev
```

### 4. Setup Search Index

```bash
# Create Azure AI Search index
./scripts/deployment/setup-search-index.sh -e dev
```

### 5. Deploy Frontend to VMs

```bash
# Deploy frontend to VMs
./scripts/deployment/deploy-to-vm.sh -e dev
```

## Detailed Deployment Steps

### Step 1: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-app-client-id

# Terraform Backend
TF_STATE_RG=tfstate-rg
TF_STATE_STORAGE=tfstateaccount

# VM Configuration
VM_ADMIN_PASSWORD=YourSecurePassword123!
```

### Step 2: Infrastructure Deployment

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init \
  -backend-config="resource_group_name=$TF_STATE_RG" \
  -backend-config="storage_account_name=$TF_STATE_STORAGE" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=genai-copilot-dev.tfstate"

# Plan deployment
terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -var="vm_admin_password=$VM_ADMIN_PASSWORD"

# Apply
terraform apply \
  -var-file=environments/dev/terraform.tfvars \
  -var="vm_admin_password=$VM_ADMIN_PASSWORD"
```

### Step 3: Configure Azure AD Authentication

1. Register an Azure AD Application
2. Configure redirect URIs
3. Create client secret
4. Update frontend environment variables

```bash
# frontend/.env
VITE_AZURE_CLIENT_ID=your-client-id
VITE_AZURE_TENANT_ID=your-tenant-id
VITE_API_BASE_URL=/api
```

### Step 4: Deploy Function Apps

```bash
cd backend/azure-functions/api-gateway
func azure functionapp publish func-api-genai-copilot-xxxxxx --python
```

### Step 5: Configure Function App Settings

Set environment variables in Azure Portal or via CLI:

```bash
FUNC_NAME=func-api-genai-copilot-xxxxxx

az functionapp config appsettings set \
  --name $FUNC_NAME \
  --resource-group rg-genai-copilot-dev-eus2 \
  --settings \
    AZURE_OPENAI_ENDPOINT=https://oai-xxx.openai.azure.com \
    AZURE_OPENAI_KEY=@Microsoft.KeyVault(SecretUri=https://kv-xxx.vault.azure.net/secrets/openai-key) \
    AZURE_SEARCH_ENDPOINT=https://search-xxx.search.windows.net \
    COSMOS_CONNECTION_STRING=@Microsoft.KeyVault(SecretUri=https://kv-xxx.vault.azure.net/secrets/cosmos-connection)
```

## CI/CD Setup with Azure DevOps

### 1. Create Service Connection

In Azure DevOps:
1. Project Settings → Service Connections
2. New Service Connection → Azure Resource Manager
3. Service principal (automatic)
4. Name: `Azure-Service-Connection`

### 2. Create Variable Group

Create variable group `genai-copilot-vars` with:
- `TF_STATE_RG`
- `TF_STATE_STORAGE`
- `VM_ADMIN_PASSWORD` (secret)
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`

### 3. Import Pipelines

Import the YAML pipelines from `azure-devops/pipelines/`:
- `infrastructure-pipeline.yml`
- `functions-pipeline.yml`
- `frontend-pipeline.yml`

### 4. Create Environments

Create environments with approval gates:
- `dev` - No approval required
- `prod` - Require approval from admins

## Destroying Infrastructure

To tear down all resources:

```bash
./scripts/deployment/deploy-infrastructure.sh -e dev -a destroy
```

## Troubleshooting

### Common Issues

1. **Terraform state lock**
   ```bash
   terraform force-unlock LOCK_ID
   ```

2. **Function deployment fails**
   - Check Python version matches (3.11)
   - Ensure all dependencies in requirements.txt

3. **Private endpoint connectivity**
   - VMs must be in the same VNet
   - Check NSG rules allow traffic

4. **OpenAI quota errors**
   - Check TPM limits in Azure Portal
   - Request quota increase if needed

### Logs and Monitoring

- **Function App Logs**: Azure Portal → Function App → Log Stream
- **Application Insights**: Azure Portal → Application Insights
- **VM Logs**: `/var/log/nginx/` and `/opt/genai-copilot/logs/`

## Security Considerations

- All services use private endpoints
- Secrets stored in Key Vault
- VNet integration for network isolation
- Azure AD authentication required
- RBAC for access control

## Cost Optimization

- Use consumption plan for API Gateway (serverless)
- Premium plan only for VNet-integrated functions
- Scale VMs based on usage
- Use GPT-4o-mini for non-critical operations
- Enable auto-shutdown for dev VMs

## Support

For issues and questions:
- Check the troubleshooting section
- Review Azure service health
- Contact the platform team
