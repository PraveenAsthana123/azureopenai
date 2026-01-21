# Azure AI/ML Platform Infrastructure

Centralized infrastructure as code for Azure AI/ML enterprise projects.

## Directory Structure

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── ai-foundry/          # Azure AI Foundry (Hub + Projects)
│   │   └── devops-cicd/         # Azure DevOps CI/CD setup
│   └── environments/
│       ├── dev/                 # Development environment
│       ├── staging/             # Staging environment
│       └── prod/                # Production environment
├── pipelines/
│   ├── azure-pipelines-ci.yml   # Continuous Integration
│   ├── azure-pipelines-cd.yml   # Continuous Deployment
│   ├── azure-pipelines-infra.yml # Infrastructure deployment
│   └── templates/
│       └── deploy-steps.yml     # Reusable deployment steps
└── scripts/
    ├── discovery/
    │   ├── azure_resource_discovery.sh    # Discover existing Azure resources
    │   └── azure_ai_foundry_discovery.sh  # Discover AI Foundry resources
    ├── instance-creation/
    │   └── create_azure_resources.sh      # Create Azure resources
    └── activation/
        └── activate_azure_services.sh     # Register resource providers
```

## Quick Start

### 1. Prerequisites

- Azure CLI installed and logged in (`az login`)
- Terraform >= 1.5.0
- jq (for scripts)

### 2. Discover Existing Resources

```bash
# Discover all Azure resources
./scripts/discovery/azure_resource_discovery.sh ./discovered_resources

# Discover AI Foundry specific resources
./scripts/discovery/azure_ai_foundry_discovery.sh ./ai_foundry_discovery
```

### 3. Activate Required Services

```bash
# Register all required resource providers
./scripts/activation/activate_azure_services.sh
```

### 4. Create Resources (Script Method)

```bash
# Generate config template
./scripts/instance-creation/create_azure_resources.sh

# Edit resource_config.json with your settings
# Then run again to create resources
./scripts/instance-creation/create_azure_resources.sh resource_config.json
```

### 5. Deploy with Terraform

```bash
cd terraform/environments/dev

# Initialize
terraform init

# Plan
terraform plan -var-file=variables.tf

# Apply
terraform apply -var-file=variables.tf
```

## Terraform Modules

### AI Foundry Module

Creates a complete Azure AI Foundry setup:
- AI Hub with shared resources
- AI Project for development
- Azure OpenAI with model deployments
- AI Search service
- Connected storage and Key Vault
- RBAC assignments

```hcl
module "ai_foundry" {
  source = "../../modules/ai-foundry"

  project_name        = "myproject"
  environment         = "dev"
  location            = "eastus"
  resource_group_name = azurerm_resource_group.main.name

  openai_deployments = [
    {
      name          = "gpt-4o"
      model_name    = "gpt-4o"
      model_version = "2024-05-13"
      capacity      = 10
    }
  ]
}
```

### DevOps CI/CD Module

Sets up Azure DevOps project with pipelines:
- DevOps Project
- Git Repository
- Variable Groups
- Service Connections
- CI/CD/Infrastructure Pipelines
- Optional self-hosted agent pool

```hcl
module "devops" {
  source = "../../modules/devops-cicd"

  project_name        = "myproject"
  environment         = "dev"
  devops_org_name     = "myorg"
  resource_group_name = azurerm_resource_group.main.name
}
```

## Scripts Reference

### azure_resource_discovery.sh

Discovers existing Azure resources and generates Terraform variables.

**Output:**
- JSON files for each resource type
- `terraform.tfvars` with discovered resource info
- `DISCOVERY_SUMMARY.md` report

### azure_ai_foundry_discovery.sh

Discovers AI Foundry specific resources:
- AI Hubs and Projects
- Azure OpenAI services and deployments
- AI Search services and indexes
- Document Intelligence accounts
- ML Workspaces
- AI connections

### create_azure_resources.sh

Creates Azure resources from a JSON configuration file.

**Supported Resources:**
- Resource Groups
- Virtual Networks and Subnets
- Storage Accounts (with HNS)
- Key Vaults
- Azure OpenAI with deployments
- AI Search
- Cosmos DB with databases
- Function Apps
- ML Workspaces

### activate_azure_services.sh

Registers required Azure resource providers for AI/ML workloads.

## CI/CD Pipelines

### CI Pipeline (azure-pipelines-ci.yml)
- Triggers on push to main/develop/feature branches
- Python linting and formatting checks
- Unit tests with coverage
- Security scanning (bandit, safety)
- Docker image build (on main)

### CD Pipeline (azure-pipelines-cd.yml)
- Multi-stage deployment (dev → staging → prod)
- Environment approvals
- Integration tests on staging
- Health checks post-deployment
- Rollback on failure

### Infrastructure Pipeline (azure-pipelines-infra.yml)
- Terraform validate and format check
- Plan with artifact publishing
- Environment-specific approvals
- State management in Azure Storage

## Cost Estimation

| Environment | Monthly Cost (USD) |
|-------------|-------------------|
| Development | $500 - $1,500 |
| Staging | $800 - $2,000 |
| Production | $2,000 - $10,000+ |

*Costs vary based on usage and model consumption.*

## Security Best Practices

1. **Use Managed Identities** - All services use system-assigned identities
2. **RBAC over Access Keys** - Role-based access for all resources
3. **Private Endpoints** - Enable for production environments
4. **Key Vault Integration** - Store secrets in Key Vault
5. **Network Security** - Use VNets and NSGs in production

## Support

For issues or questions, refer to the main project documentation or open an issue.
