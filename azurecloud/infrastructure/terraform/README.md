# RAG Platform - Terraform Infrastructure

Infrastructure as Code for deploying the RAG Platform on Azure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Azure Cloud                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   AI Foundry    │  │  Azure OpenAI   │  │   AI Search     │     │
│  │   (Hub/Project) │  │  (GPT-4o, Embed)│  │  (Vector+Semantic)│   │
│  │   + Claude      │  │                 │  │                 │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Cosmos DB     │  │  Blob Storage   │  │  Function App   │     │
│  │  (Conversations)│  │  (Documents)    │  │  (RAG API)      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Key Vault     │  │  App Insights   │  │  VNet + NSGs    │     │
│  │  (Secrets)      │  │  (Monitoring)   │  │  (Networking)   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Azure CLI** (v2.50+)
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   az login
   ```

2. **Terraform** (v1.5+)
   ```bash
   # Ubuntu/Debian
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   ```

3. **Azure Subscription** with permissions to create resources

## Quick Start

### 1. Setup Terraform Backend (One-time)

```bash
cd infrastructure/terraform/scripts
chmod +x setup-backend.sh
./setup-backend.sh prod eastus2
```

### 2. Configure Variables

```bash
cd environments/prod
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Deploy

```bash
cd infrastructure/terraform/scripts
chmod +x deploy.sh

# Initialize
./deploy.sh prod init

# Plan (review changes)
./deploy.sh prod plan

# Apply
./deploy.sh prod apply
```

## Directory Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf              # Dev environment config
│   │   └── terraform.tfvars     # Dev variables (gitignored)
│   └── prod/
│       ├── main.tf              # Prod environment config
│       └── terraform.tfvars     # Prod variables (gitignored)
├── modules/
│   ├── ai-foundry/              # AI Hub, Project, OpenAI, Search, Claude
│   ├── ai-services/             # Cognitive Services
│   ├── compute/                 # Function App, Container Apps
│   ├── database/                # Cosmos DB
│   ├── monitoring/              # App Insights, Log Analytics
│   ├── networking/              # VNet, Subnets, NSGs
│   ├── storage/                 # Blob Storage, Data Lake
│   └── governance/              # Policies, RBAC
├── scripts/
│   ├── setup-backend.sh         # Create Terraform state storage
│   └── deploy.sh                # Deployment helper script
├── variables.tf                 # Root variables
├── outputs.tf                   # Root outputs
└── README.md
```

## Modules

### ai-foundry

Deploys Azure AI Foundry (Hub + Project) with:
- Azure OpenAI (GPT-4o, GPT-4o-mini, text-embedding-3-large)
- Azure AI Search with vector + semantic capabilities
- **Claude** (optional, from Azure AI Model Catalog)
- Key Vault for secrets
- Application Insights

```hcl
module "ai_foundry" {
  source = "../../modules/ai-foundry"

  project_name        = "rag"
  environment         = "prod"
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.main.name

  # Deploy Claude from Model Catalog
  deploy_claude   = true
  claude_model_id = "azureml://registries/azureml/models/Anthropic-Claude-3-5-Sonnet/versions/1"

  # OpenAI models
  openai_deployments = [
    {
      name          = "gpt-4o-mini"
      model_name    = "gpt-4o-mini"
      model_version = "2024-07-18"
      capacity      = 80
    },
    {
      name          = "text-embedding-3-large"
      model_name    = "text-embedding-3-large"
      model_version = "1"
      capacity      = 120
    }
  ]
}
```

### networking

Creates VNet with subnets for:
- Function App integration
- Private endpoints
- Compute resources

### compute

Deploys Function App with:
- Python 3.11 runtime
- System-assigned managed identity
- VNet integration
- Application settings from other modules

## Environments

### Development (dev)

- Smaller SKUs (Basic, B1)
- No zone redundancy
- Public endpoints (faster iteration)
- Lower throughput limits

### Production (prod)

- Premium SKUs (Standard, P1v3)
- Zone redundancy enabled
- Private endpoints
- Geo-redundant storage
- Higher throughput limits

## Commands Reference

```bash
# Initialize
./deploy.sh prod init

# Validate configuration
./deploy.sh prod validate

# Plan changes
./deploy.sh prod plan

# Apply changes
./deploy.sh prod apply

# Show outputs
./deploy.sh prod output

# List resources in state
./deploy.sh prod state

# Destroy (careful!)
./deploy.sh prod destroy
```

## Claude Deployment

Claude is deployed via Azure AI Foundry Model Catalog:

1. Check availability in your region
2. Set `deploy_claude = true` in terraform.tfvars
3. Run terraform apply

```hcl
# terraform.tfvars
deploy_claude   = true
claude_model_id = "azureml://registries/azureml/models/Anthropic-Claude-3-5-Sonnet/versions/1"
```

The Claude endpoint URI is stored in Key Vault automatically.

## State Management

Terraform state is stored in Azure Blob Storage:

| Environment | Storage Account | Container | State File |
|-------------|----------------|-----------|------------|
| dev | tfstatedev* | tfstate | dev.terraform.tfstate |
| prod | tfstateprod* | tfstate | prod.terraform.tfstate |

Features:
- Blob versioning (state recovery)
- Soft delete (30 days)
- State locking (prevents concurrent changes)

## Cost Estimation

| Resource | Dev (Monthly) | Prod (Monthly) |
|----------|---------------|----------------|
| Azure OpenAI | ~$50-200 | ~$200-2000 |
| AI Search (Basic/Standard) | ~$75 / ~$250 | ~$250+ |
| Cosmos DB | ~$25 | ~$100-500 |
| Function App | ~$10 | ~$75-200 |
| Storage | ~$5 | ~$20-50 |
| Key Vault | ~$3 | ~$3 |
| App Insights | ~$10 | ~$50-100 |
| **Total** | **~$175-300** | **~$700-3000** |

*Costs vary significantly based on usage (tokens, requests, storage)*

## Troubleshooting

### "Backend not initialized"

```bash
./deploy.sh prod init
```

### "State lock"

```bash
# Check who has the lock
terraform force-unlock LOCK_ID
```

### "Resource already exists"

Import the existing resource:
```bash
terraform import azurerm_resource_group.main /subscriptions/.../resourceGroups/rg-rag-prod
```

### "Claude model not available"

Check region availability:
```bash
az ml model list --registry-name azureml --query "[?contains(name, 'Claude')]" -o table
```

## Security

- All secrets in Key Vault (never in state)
- Managed identities (no API keys in code)
- Private endpoints (optional, recommended for prod)
- NSGs restrict traffic
- TLS 1.2+ enforced
