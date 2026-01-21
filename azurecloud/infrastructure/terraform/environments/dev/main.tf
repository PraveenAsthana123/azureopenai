#===============================================================================
# Azure AI/ML Platform - Development Environment
# Main Terraform Configuration
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
    azuredevops = {
      source  = "microsoft/azuredevops"
      version = "~> 1.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatedev"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}

#-------------------------------------------------------------------------------
# Providers
#-------------------------------------------------------------------------------
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
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
  default     = "aiml"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
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
    CreatedDate = timestamp()
  }, var.tags)
}

#-------------------------------------------------------------------------------
# Data Sources
#-------------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

#-------------------------------------------------------------------------------
# Resource Group
#-------------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

#-------------------------------------------------------------------------------
# AI Foundry Module
#-------------------------------------------------------------------------------
module "ai_foundry" {
  source = "../../modules/ai-foundry"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  openai_deployments = [
    {
      name          = "gpt-4o"
      model_name    = "gpt-4o"
      model_version = "2024-05-13"
      capacity      = 10
    },
    {
      name          = "text-embedding-3-large"
      model_name    = "text-embedding-3-large"
      model_version = "1"
      capacity      = 30
    }
  ]

  ai_search_sku            = "basic"
  enable_private_endpoints = false
}

#-------------------------------------------------------------------------------
# Additional Storage for Data Lake
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "datalake" {
  name                     = replace("${local.name_prefix}datalake", "-", "")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
  }

  tags = local.common_tags
}

# Data Lake containers
resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

#-------------------------------------------------------------------------------
# Cosmos DB for Application Data
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_account" "main" {
  name                = "${local.name_prefix}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  tags = local.common_tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "appdata"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/userId"
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "documents" {
  name                = "documents"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/category"
  throughput          = 400
}

#-------------------------------------------------------------------------------
# Function App for API
#-------------------------------------------------------------------------------
resource "azurerm_service_plan" "functions" {
  name                = "${local.name_prefix}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "EP1"

  tags = local.common_tags
}

resource "azurerm_linux_function_app" "main" {
  name                       = "${local.name_prefix}-func"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = var.location
  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.datalake.name
  storage_account_access_key = azurerm_storage_account.datalake.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME       = "python"
    WEBSITE_RUN_FROM_PACKAGE       = "1"
    AZURE_OPENAI_ENDPOINT          = module.ai_foundry.openai_endpoint
    AZURE_SEARCH_ENDPOINT          = module.ai_foundry.ai_search_endpoint
    COSMOS_DB_ENDPOINT             = azurerm_cosmosdb_account.main.endpoint
    KEY_VAULT_URL                  = module.ai_foundry.key_vault_uri
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Application Insights
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-law"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

resource "azurerm_application_insights" "main" {
  name                = "${local.name_prefix}-insights"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# RBAC Assignments
#-------------------------------------------------------------------------------
# Function App gets access to Cosmos DB
resource "azurerm_role_assignment" "func_cosmos" {
  scope                = azurerm_cosmosdb_account.main.id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App gets access to OpenAI
resource "azurerm_role_assignment" "func_openai" {
  scope                = module.ai_foundry.openai_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App gets access to AI Search
resource "azurerm_role_assignment" "func_search" {
  scope                = module.ai_foundry.ai_search_id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App gets access to Key Vault
resource "azurerm_role_assignment" "func_keyvault" {
  scope                = module.ai_foundry.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App gets access to Storage
resource "azurerm_role_assignment" "func_storage" {
  scope                = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "ai_hub_name" {
  value = module.ai_foundry.ai_hub_name
}

output "ai_project_name" {
  value = module.ai_foundry.ai_project_name
}

output "openai_endpoint" {
  value = module.ai_foundry.openai_endpoint
}

output "ai_search_endpoint" {
  value = module.ai_foundry.ai_search_endpoint
}

output "cosmos_db_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "datalake_name" {
  value = azurerm_storage_account.datalake.name
}

output "key_vault_uri" {
  value = module.ai_foundry.key_vault_uri
}

output "application_insights_connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}
