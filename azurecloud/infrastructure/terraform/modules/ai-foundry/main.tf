#===============================================================================
# Azure AI Foundry (AI Studio) Terraform Module
# Creates AI Hub, Projects, and connected AI services
#===============================================================================

terraform {
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
}

#-------------------------------------------------------------------------------
# Variables
#-------------------------------------------------------------------------------
variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "openai_deployments" {
  description = "OpenAI model deployments"
  type = list(object({
    name           = string
    model_name     = string
    model_version  = string
    capacity       = number
  }))
  default = [
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
      capacity      = 50
    }
  ]
}

variable "ai_search_sku" {
  description = "AI Search SKU"
  type        = string
  default     = "basic"
}

variable "enable_private_endpoints" {
  description = "Enable private endpoints for services"
  type        = bool
  default     = false
}

variable "vnet_id" {
  description = "VNet ID for private endpoints"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Subnet ID for private endpoints"
  type        = string
  default     = null
}

# =============================================================================
# Claude Model Deployment Variables
# =============================================================================

variable "deploy_claude" {
  description = "Deploy Claude model from Azure AI Model Catalog (requires regional availability)"
  type        = bool
  default     = false
}

variable "claude_model_id" {
  description = "Claude model ID from Azure AI Model Catalog"
  type        = string
  default     = "azureml://registries/azureml/models/Anthropic-Claude-3-5-Sonnet/versions/1"
}

variable "claude_endpoint_name" {
  description = "Name for Claude serverless endpoint"
  type        = string
  default     = "claude-sonnet-endpoint"
}

#-------------------------------------------------------------------------------
# Local Variables
#-------------------------------------------------------------------------------
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  default_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Module      = "ai-foundry"
  }

  tags = merge(local.default_tags, var.tags)
}

#-------------------------------------------------------------------------------
# Data Sources
#-------------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

#-------------------------------------------------------------------------------
# Storage Account (for AI Hub)
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "ai_hub" {
  name                     = replace("${local.name_prefix}aihubsa", "-", "")
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  is_hns_enabled = true  # Enable hierarchical namespace for ML

  blob_properties {
    versioning_enabled = true
  }

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Key Vault (for AI Hub)
#-------------------------------------------------------------------------------
resource "azurerm_key_vault" "ai_hub" {
  name                       = "${local.name_prefix}-aihub-kv"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  enable_rbac_authorization = true

  network_acls {
    bypass         = "AzureServices"
    default_action = var.enable_private_endpoints ? "Deny" : "Allow"
  }

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Application Insights (for AI Hub)
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "ai_hub" {
  name                = "${local.name_prefix}-aihub-law"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

resource "azurerm_application_insights" "ai_hub" {
  name                = "${local.name_prefix}-aihub-insights"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.ai_hub.id
  application_type    = "web"

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Container Registry (for AI Hub)
#-------------------------------------------------------------------------------
resource "azurerm_container_registry" "ai_hub" {
  name                = replace("${local.name_prefix}aihubacr", "-", "")
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Azure OpenAI Service
#-------------------------------------------------------------------------------
resource "azurerm_cognitive_account" "openai" {
  name                  = "${local.name_prefix}-openai"
  resource_group_name   = var.resource_group_name
  location              = var.location
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "${local.name_prefix}-openai"

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = var.enable_private_endpoints ? "Deny" : "Allow"
    ip_rules       = []
  }

  tags = local.tags
}

# OpenAI Model Deployments
resource "azurerm_cognitive_deployment" "models" {
  for_each = { for d in var.openai_deployments : d.name => d }

  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  sku {
    name     = "Standard"
    capacity = each.value.capacity
  }
}

#-------------------------------------------------------------------------------
# AI Search Service
#-------------------------------------------------------------------------------
resource "azurerm_search_service" "ai_search" {
  name                = "${local.name_prefix}-search"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.ai_search_sku

  replica_count   = 1
  partition_count = 1

  public_network_access_enabled = !var.enable_private_endpoints

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

#-------------------------------------------------------------------------------
# AI Foundry Hub (using AzAPI for latest features)
#-------------------------------------------------------------------------------
resource "azapi_resource" "ai_hub" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-04-01"
  name      = "${local.name_prefix}-ai-hub"
  location  = var.location
  parent_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"

  identity {
    type = "SystemAssigned"
  }

  body = jsonencode({
    kind = "Hub"
    properties = {
      description         = "AI Foundry Hub for ${var.project_name}"
      friendlyName        = "${var.project_name} AI Hub"
      storageAccount      = azurerm_storage_account.ai_hub.id
      keyVault            = azurerm_key_vault.ai_hub.id
      applicationInsights = azurerm_application_insights.ai_hub.id
      containerRegistry   = azurerm_container_registry.ai_hub.id

      publicNetworkAccess = var.enable_private_endpoints ? "Disabled" : "Enabled"

      managedNetwork = {
        isolationMode = var.enable_private_endpoints ? "AllowInternetOutbound" : "Disabled"
      }
    }
    sku = {
      name = "Basic"
      tier = "Basic"
    }
  })

  tags = local.tags

  depends_on = [
    azurerm_storage_account.ai_hub,
    azurerm_key_vault.ai_hub,
    azurerm_application_insights.ai_hub,
    azurerm_container_registry.ai_hub
  ]
}

#-------------------------------------------------------------------------------
# AI Foundry Project
#-------------------------------------------------------------------------------
resource "azapi_resource" "ai_project" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-04-01"
  name      = "${local.name_prefix}-ai-project"
  location  = var.location
  parent_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"

  identity {
    type = "SystemAssigned"
  }

  body = jsonencode({
    kind = "Project"
    properties = {
      description  = "AI Project for ${var.project_name}"
      friendlyName = "${var.project_name} AI Project"
      hubResourceId = azapi_resource.ai_hub.id
    }
    sku = {
      name = "Basic"
      tier = "Basic"
    }
  })

  tags = local.tags

  depends_on = [azapi_resource.ai_hub]
}

#-------------------------------------------------------------------------------
# AI Hub Connections (OpenAI and AI Search)
#-------------------------------------------------------------------------------
resource "azapi_resource" "openai_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-04-01"
  name      = "aoai-connection"
  parent_id = azapi_resource.ai_hub.id

  body = jsonencode({
    properties = {
      category      = "AzureOpenAI"
      target        = azurerm_cognitive_account.openai.endpoint
      authType      = "AAD"
      isSharedToAll = true
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_cognitive_account.openai.id
      }
    }
  })

  depends_on = [azapi_resource.ai_hub, azurerm_cognitive_account.openai]
}

resource "azapi_resource" "search_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-04-01"
  name      = "search-connection"
  parent_id = azapi_resource.ai_hub.id

  body = jsonencode({
    properties = {
      category      = "CognitiveSearch"
      target        = "https://${azurerm_search_service.ai_search.name}.search.windows.net"
      authType      = "AAD"
      isSharedToAll = true
      metadata = {
        ResourceId = azurerm_search_service.ai_search.id
      }
    }
  })

  depends_on = [azapi_resource.ai_hub, azurerm_search_service.ai_search]
}

#-------------------------------------------------------------------------------
# RBAC Assignments
#-------------------------------------------------------------------------------
# AI Hub identity gets access to OpenAI
resource "azurerm_role_assignment" "hub_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azapi_resource.ai_hub.identity[0].principal_id
}

# AI Hub identity gets access to AI Search
resource "azurerm_role_assignment" "hub_search" {
  scope                = azurerm_search_service.ai_search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azapi_resource.ai_hub.identity[0].principal_id
}

# AI Hub identity gets access to Storage
resource "azurerm_role_assignment" "hub_storage" {
  scope                = azurerm_storage_account.ai_hub.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azapi_resource.ai_hub.identity[0].principal_id
}

# AI Hub identity gets access to Key Vault
resource "azurerm_role_assignment" "hub_keyvault" {
  scope                = azurerm_key_vault.ai_hub.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azapi_resource.ai_hub.identity[0].principal_id
}

#-------------------------------------------------------------------------------
# Claude Serverless Endpoint (Model Catalog)
#-------------------------------------------------------------------------------
# Deploys Claude from Azure AI Model Catalog as serverless endpoint
# Note: Claude availability varies by region - check Azure documentation

resource "azapi_resource" "claude_endpoint" {
  count = var.deploy_claude ? 1 : 0

  type      = "Microsoft.MachineLearningServices/workspaces/serverlessEndpoints@2024-04-01"
  name      = var.claude_endpoint_name
  location  = var.location
  parent_id = azapi_resource.ai_hub.id

  body = jsonencode({
    properties = {
      modelSettings = {
        modelId = var.claude_model_id
      }
      authMode = "Key"
    }
    sku = {
      name = "Consumption"
    }
  })

  tags = local.tags

  depends_on = [azapi_resource.ai_hub]
}

# Store Claude endpoint URI in Key Vault
resource "azurerm_key_vault_secret" "claude_endpoint_uri" {
  count = var.deploy_claude ? 1 : 0

  name         = "claude-endpoint-uri"
  value        = try(jsondecode(azapi_resource.claude_endpoint[0].output).properties.inferenceEndpoint.uri, "")
  key_vault_id = azurerm_key_vault.ai_hub.id

  depends_on = [
    azapi_resource.claude_endpoint,
    azurerm_role_assignment.hub_keyvault
  ]
}

# Anthropic API Connection (for direct API access from AI Foundry)
resource "azapi_resource" "anthropic_connection" {
  count = var.deploy_claude ? 1 : 0

  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-04-01"
  name      = "claude-connection"
  parent_id = azapi_resource.ai_hub.id

  body = jsonencode({
    properties = {
      category      = "CustomKeys"
      target        = try(jsondecode(azapi_resource.claude_endpoint[0].output).properties.inferenceEndpoint.uri, "https://placeholder")
      authType      = "CustomKeys"
      isSharedToAll = true
      credentials = {
        keys = {
          "api-key" = "managed-by-azure"
        }
      }
      metadata = {
        ModelProvider = "Anthropic"
        ModelName     = "Claude"
      }
    }
  })

  depends_on = [azapi_resource.ai_hub, azapi_resource.claude_endpoint]
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "ai_hub_id" {
  description = "AI Foundry Hub ID"
  value       = azapi_resource.ai_hub.id
}

output "ai_hub_name" {
  description = "AI Foundry Hub name"
  value       = azapi_resource.ai_hub.name
}

output "ai_project_id" {
  description = "AI Foundry Project ID"
  value       = azapi_resource.ai_project.id
}

output "ai_project_name" {
  description = "AI Foundry Project name"
  value       = azapi_resource.ai_project.name
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_id" {
  description = "Azure OpenAI resource ID"
  value       = azurerm_cognitive_account.openai.id
}

output "ai_search_endpoint" {
  description = "AI Search endpoint"
  value       = "https://${azurerm_search_service.ai_search.name}.search.windows.net"
}

output "ai_search_id" {
  description = "AI Search resource ID"
  value       = azurerm_search_service.ai_search.id
}

output "storage_account_id" {
  description = "Storage account ID"
  value       = azurerm_storage_account.ai_hub.id
}

output "key_vault_id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.ai_hub.id
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.ai_hub.vault_uri
}

# Claude outputs
output "claude_endpoint_id" {
  description = "Claude serverless endpoint ID"
  value       = var.deploy_claude ? azapi_resource.claude_endpoint[0].id : null
}

output "claude_endpoint_name" {
  description = "Claude serverless endpoint name"
  value       = var.deploy_claude ? azapi_resource.claude_endpoint[0].name : null
}

output "claude_deployed" {
  description = "Whether Claude was deployed"
  value       = var.deploy_claude
}
