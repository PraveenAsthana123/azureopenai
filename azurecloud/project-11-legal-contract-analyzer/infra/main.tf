# ============================================================================
# Project 11 - Legal Contract Analyzer - Infrastructure
# Azure Functions v2 | Document Intelligence | GPT-4o | AI Search | Cosmos DB
# VNET: 10.11.0.0/16 | Dataset: CUAD_v1/ (510 contracts, 41 clause types)
# ============================================================================

# ============================================================================
# Terraform Configuration
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "legal-contract-analyzer.tfstate"
  }
}

# ============================================================================
# Provider
# ============================================================================

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "legalcontract"
}

variable "openai_model_deployments" {
  description = "OpenAI model deployments"
  type = map(object({
    model_name    = string
    model_version = string
    sku_capacity  = number
  }))
  default = {
    "gpt-4o" = {
      model_name    = "gpt-4o"
      model_version = "2024-05-13"
      sku_capacity  = 30
    }
    "text-embedding-ada-002" = {
      model_name    = "text-embedding-ada-002"
      model_version = "2"
      sku_capacity  = 120
    }
  }
}

# ============================================================================
# Locals
# ============================================================================

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = "Legal-Contract-Analyzer"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Dataset     = "CUAD_v1"
  }
}

# ============================================================================
# Data Sources
# ============================================================================

data "azurerm_client_config" "current" {}

# ============================================================================
# Resource Group
# ============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.tags
}

# ============================================================================
# Virtual Network (10.11.0.0/16)
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.11.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.11.1.0/24"]

  delegation {
    name = "functions-delegation"
    service_delegation {
      name = "Microsoft.Web/serverFarms"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/action",
      ]
    }
  }
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.11.2.0/24"]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.AzureCosmosDB",
    "Microsoft.KeyVault",
    "Microsoft.CognitiveServices",
  ]
}

resource "azurerm_subnet" "pe" {
  name                 = "snet-pe"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.11.3.0/24"]
}

# ============================================================================
# Network Security Group
# ============================================================================

resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

# ============================================================================
# Key Vault
# ============================================================================

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = local.tags
}

# ============================================================================
# Storage Account
# ============================================================================

resource "azurerm_storage_account" "main" {
  name                     = "st${replace(local.resource_prefix, "-", "")}01"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_container" "contracts_inbox" {
  name                  = "contracts-inbox"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "contracts_processed" {
  name                  = "contracts-processed"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "contracts_originals" {
  name                  = "contracts-originals"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "templates" {
  name                  = "templates"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# ============================================================================
# Azure OpenAI Service
# ============================================================================

resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.resource_prefix}"
  tags                  = local.tags
}

resource "azurerm_cognitive_deployment" "models" {
  for_each             = var.openai_model_deployments
  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  scale {
    type     = "Standard"
    capacity = each.value.sku_capacity
  }
}

# ============================================================================
# Document Intelligence (Form Recognizer)
# ============================================================================

resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "docint-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "docint-${local.resource_prefix}"
  tags                  = local.tags
}

# ============================================================================
# Azure AI Search
# ============================================================================

resource "azurerm_search_service" "main" {
  name                = "search-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "standard" : "basic"
  replica_count       = var.environment == "prod" ? 2 : 1
  partition_count     = 1
  tags                = local.tags
}

# ============================================================================
# Cosmos DB
# ============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  tags                = local.tags

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "legalcontracts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "contracts" {
  name                = "contracts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/contractId"
}

resource "azurerm_cosmosdb_sql_container" "clauses" {
  name                = "clauses"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/contractId"
}

resource "azurerm_cosmosdb_sql_container" "templates" {
  name                = "templates"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/templateId"
}

resource "azurerm_cosmosdb_sql_container" "obligations" {
  name                = "obligations"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/contractId"
}

# ============================================================================
# Event Grid System Topic (Storage Account)
# ============================================================================

resource "azurerm_eventgrid_system_topic" "storage" {
  name                   = "evgt-${local.resource_prefix}-storage"
  location               = azurerm_resource_group.main.location
  resource_group_name    = azurerm_resource_group.main.name
  source_arm_resource_id = azurerm_storage_account.main.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = local.tags
}

resource "azurerm_eventgrid_system_topic_event_subscription" "contract_upload" {
  name                = "evgs-contract-upload"
  system_topic        = azurerm_eventgrid_system_topic.storage.name
  resource_group_name = azurerm_resource_group.main.name

  included_event_types = ["Microsoft.Storage.BlobCreated"]

  subject_filter {
    subject_begins_with = "/blobServices/default/containers/contracts-inbox/"
  }

  webhook_endpoint {
    url = "https://${azurerm_linux_function_app.main.default_hostname}/runtime/webhooks/EventGrid?functionName=ContractUploadTrigger&code=${data.azurerm_function_app_host_keys.main.event_grid_extension_config_key}"
  }
}

data "azurerm_function_app_host_keys" "main" {
  name                = azurerm_linux_function_app.main.name
  resource_group_name = azurerm_resource_group.main.name
}

# ============================================================================
# Log Analytics & Application Insights
# ============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ============================================================================
# Function App (Linux, Python 3.11)
# ============================================================================

resource "azurerm_service_plan" "main" {
  name                = "asp-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.environment == "prod" ? "EP1" : "Y1"
  tags                = local.tags
}

resource "azurerm_linux_function_app" "main" {
  name                       = "func-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  virtual_network_subnet_id  = azurerm_subnet.app.id
  tags                       = local.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
    vnet_route_all_enabled = true
  }

  app_settings = {
    "AZURE_OPENAI_ENDPOINT"                 = azurerm_cognitive_account.openai.endpoint
    "AZURE_SEARCH_ENDPOINT"                 = "https://${azurerm_search_service.main.name}.search.windows.net"
    "COSMOS_ENDPOINT"                       = azurerm_cosmosdb_account.main.endpoint
    "DOCUMENT_INTELLIGENCE_ENDPOINT"        = azurerm_cognitive_account.document_intelligence.endpoint
    "KEY_VAULT_URL"                         = azurerm_key_vault.main.vault_uri
    "STORAGE_ACCOUNT_URL"                   = azurerm_storage_account.main.primary_blob_endpoint
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = azurerm_application_insights.main.instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "AzureWebJobsFeatureFlags"              = "EnableWorkerIndexing"
    "BUILD_FLAGS"                           = "UseExpressBuild"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"        = "true"
    "XDG_CACHE_HOME"                        = "/tmp/.cache"
  }
}

# ============================================================================
# RBAC Role Assignments
# ============================================================================

# Function App -> Azure OpenAI (Cognitive Services OpenAI User)
resource "azurerm_role_assignment" "function_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App -> AI Search (Search Index Data Contributor)
resource "azurerm_role_assignment" "function_search" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App -> Storage (Storage Blob Data Contributor)
resource "azurerm_role_assignment" "function_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App -> Cosmos DB (Cosmos DB Account Reader Role)
resource "azurerm_role_assignment" "function_cosmos" {
  scope                = azurerm_cosmosdb_account.main.id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App -> Key Vault (Key Vault Secrets User)
resource "azurerm_role_assignment" "function_keyvault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# Function App -> Document Intelligence (Cognitive Services User)
resource "azurerm_role_assignment" "function_docint" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

# ============================================================================
# Outputs
# ============================================================================

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "function_app_url" {
  description = "Function App default hostname"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
}
