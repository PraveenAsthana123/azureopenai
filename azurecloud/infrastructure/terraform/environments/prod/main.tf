#===============================================================================
# RAG Platform - Production Environment
# Complete Terraform Configuration with Claude Support
#===============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.11"
    }
  }

  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstateprod"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}

#-------------------------------------------------------------------------------
# Providers
#-------------------------------------------------------------------------------
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false  # Prod: keep soft delete
    }
    cognitive_account {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

provider "azapi" {}

#-------------------------------------------------------------------------------
# Variables
#-------------------------------------------------------------------------------
variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "rag"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "eastus2"
}

variable "location_secondary" {
  description = "Secondary Azure region for DR"
  type        = string
  default     = "westus2"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

# Claude deployment
variable "deploy_claude" {
  description = "Deploy Claude model from Azure AI Model Catalog"
  type        = bool
  default     = false  # Set to true when available in your region
}

variable "claude_model_id" {
  description = "Claude model ID from Azure AI Model Catalog"
  type        = string
  default     = "azureml://registries/azureml/models/Anthropic-Claude-3-5-Sonnet/versions/1"
}

# Feature flags
variable "enable_private_endpoints" {
  description = "Enable private endpoints for all services"
  type        = bool
  default     = true
}

variable "enable_zone_redundancy" {
  description = "Enable zone redundancy for high availability"
  type        = bool
  default     = true
}

#-------------------------------------------------------------------------------
# Local Variables
#-------------------------------------------------------------------------------
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge({
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    CostCenter  = "AI-Platform"
  }, var.tags)

  # OpenAI model deployments for production
  openai_deployments = [
    {
      name          = "gpt-4o"
      model_name    = "gpt-4o"
      model_version = "2024-08-06"
      capacity      = 40
    },
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

#-------------------------------------------------------------------------------
# Data Sources
#-------------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

#-------------------------------------------------------------------------------
# Resource Group
#-------------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

#-------------------------------------------------------------------------------
# Networking Module
#-------------------------------------------------------------------------------
module "networking" {
  source = "../../modules/networking"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  vnet_address_space = ["10.0.0.0/16"]

  subnets = {
    functions = {
      address_prefix = "10.0.1.0/24"
      delegation     = "Microsoft.Web/serverFarms"
    }
    private_endpoints = {
      address_prefix = "10.0.2.0/24"
      delegation     = null
    }
    compute = {
      address_prefix = "10.0.3.0/24"
      delegation     = null
    }
  }
}

#-------------------------------------------------------------------------------
# AI Foundry Module (with Claude support)
#-------------------------------------------------------------------------------
module "ai_foundry" {
  source = "../../modules/ai-foundry"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  openai_deployments = local.openai_deployments

  ai_search_sku            = "standard"
  enable_private_endpoints = var.enable_private_endpoints
  vnet_id                  = module.networking.vnet_id
  subnet_id                = module.networking.subnet_ids["private_endpoints"]

  # Claude deployment
  deploy_claude    = var.deploy_claude
  claude_model_id  = var.claude_model_id
}

#-------------------------------------------------------------------------------
# Storage Module
#-------------------------------------------------------------------------------
module "storage" {
  source = "../../modules/storage"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  enable_hierarchical_namespace = true
  enable_versioning            = true
  replication_type             = "GRS"  # Geo-redundant for prod

  containers = ["documents", "processed", "bronze", "silver", "gold"]
}

#-------------------------------------------------------------------------------
# Database Module (Cosmos DB)
#-------------------------------------------------------------------------------
module "database" {
  source = "../../modules/database"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  enable_serverless     = false  # Provisioned for prod
  throughput            = 4000
  enable_zone_redundancy = var.enable_zone_redundancy

  containers = {
    conversations = {
      partition_key = "/user_id"
      throughput    = 1000
    }
    documents = {
      partition_key = "/category"
      throughput    = 1000
    }
    evaluations = {
      partition_key = "/run_id"
      throughput    = 400
    }
  }
}

#-------------------------------------------------------------------------------
# Compute Module (Function App)
#-------------------------------------------------------------------------------
module "compute" {
  source = "../../modules/compute"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  sku_name    = "P1v3"  # Premium for prod
  worker_count = 2

  vnet_integration_subnet_id = module.networking.subnet_ids["functions"]

  app_settings = {
    AZURE_OPENAI_ENDPOINT          = module.ai_foundry.openai_endpoint
    AZURE_SEARCH_ENDPOINT          = module.ai_foundry.ai_search_endpoint
    AZURE_SEARCH_INDEX             = "rag-multimodal-index"
    COSMOS_ENDPOINT                = module.database.cosmos_endpoint
    COSMOS_DATABASE                = module.database.database_name
    AZURE_STORAGE_ACCOUNT_URL      = module.storage.primary_blob_endpoint
    KEY_VAULT_URL                  = module.ai_foundry.key_vault_uri
    CHAT_DEPLOYMENT                = "gpt-4o-mini"
    EMBEDDING_DEPLOYMENT           = "text-embedding-3-large"
    ENVIRONMENT                    = var.environment
  }
}

#-------------------------------------------------------------------------------
# Monitoring Module
#-------------------------------------------------------------------------------
module "monitoring" {
  source = "../../modules/monitoring"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  retention_days = 90

  # Alert recipients
  alert_email_addresses = []  # Add emails in tfvars
}

#-------------------------------------------------------------------------------
# RBAC Assignments
#-------------------------------------------------------------------------------

# Function App -> OpenAI
resource "azurerm_role_assignment" "func_openai" {
  scope                = module.ai_foundry.openai_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = module.compute.function_app_principal_id
}

# Function App -> AI Search
resource "azurerm_role_assignment" "func_search" {
  scope                = module.ai_foundry.ai_search_id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = module.compute.function_app_principal_id
}

# Function App -> Cosmos DB
resource "azurerm_role_assignment" "func_cosmos" {
  scope                = module.database.cosmos_account_id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = module.compute.function_app_principal_id
}

# Function App -> Storage
resource "azurerm_role_assignment" "func_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.compute.function_app_principal_id
}

# Function App -> Key Vault
resource "azurerm_role_assignment" "func_keyvault" {
  scope                = module.ai_foundry.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.compute.function_app_principal_id
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "function_app_url" {
  description = "Function App URL"
  value       = module.compute.function_app_url
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = module.ai_foundry.openai_endpoint
}

output "ai_search_endpoint" {
  description = "AI Search endpoint"
  value       = module.ai_foundry.ai_search_endpoint
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint"
  value       = module.database.cosmos_endpoint
}

output "storage_account_name" {
  description = "Storage account name"
  value       = module.storage.storage_account_name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = module.ai_foundry.key_vault_uri
}

output "ai_hub_name" {
  description = "AI Foundry Hub name"
  value       = module.ai_foundry.ai_hub_name
}

output "claude_deployed" {
  description = "Whether Claude was deployed"
  value       = module.ai_foundry.claude_deployed
}

output "claude_endpoint_name" {
  description = "Claude endpoint name (if deployed)"
  value       = module.ai_foundry.claude_endpoint_name
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.monitoring.app_insights_connection_string
  sensitive   = true
}
