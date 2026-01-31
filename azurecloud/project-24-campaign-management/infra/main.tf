# ==============================================================================
# AI Campaign Management Platform - Terraform Infrastructure
# ==============================================================================

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
    key                  = "campaign-mgmt.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# ==============================================================================
# Variables
# ==============================================================================

variable "environment" {
  type    = string
  default = "dev"
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "project_name" {
  type    = string
  default = "campaign"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Campaign-Management"
    ManagedBy   = "Terraform"
  }
}

data "azurerm_client_config" "current" {}

# ==============================================================================
# Resource Group
# ==============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.tags
}

# ==============================================================================
# Virtual Network & Subnets
# ==============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.24.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.24.1.0/24"]

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
  address_prefixes     = ["10.24.2.0/24"]
  service_endpoints    = ["Microsoft.Storage", "Microsoft.CognitiveServices", "Microsoft.EventHub"]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.24.3.0/24"]
  service_endpoints    = ["Microsoft.Sql", "Microsoft.Storage"]
}

# ==============================================================================
# Azure OpenAI (Campaign Content Generation & Audience Insights)
# ==============================================================================

resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  scale {
    type     = "Standard"
    capacity = 30
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }

  scale {
    type     = "Standard"
    capacity = 30
  }
}

# ==============================================================================
# Azure ML Workspace (Audience Segmentation)
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  tags                = local.tags
}

resource "azurerm_key_vault" "main" {
  name                = "kv-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  tags = local.tags
}

resource "azurerm_storage_account" "ml" {
  name                     = "stml${replace(local.resource_prefix, "-", "")}"
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags
}

resource "azurerm_machine_learning_workspace" "main" {
  name                    = "mlw-${local.resource_prefix}"
  location                = azurerm_resource_group.main.location
  resource_group_name     = azurerm_resource_group.main.name
  application_insights_id = azurerm_application_insights.main.id
  key_vault_id            = azurerm_key_vault.main.id
  storage_account_id      = azurerm_storage_account.ml.id

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure Communication Services (Email & SMS Channels)
# ==============================================================================

resource "azurerm_communication_service" "main" {
  name                = "acs-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  data_location       = "United States"
  tags                = local.tags
}

# ==============================================================================
# Azure Notification Hubs (Push Notifications)
# ==============================================================================

resource "azurerm_notification_hub_namespace" "main" {
  name                = "nhns-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  namespace_type      = "NotificationHub"
  sku_name            = var.environment == "prod" ? "Standard" : "Free"
  tags                = local.tags
}

resource "azurerm_notification_hub" "main" {
  name                = "nh-${local.resource_prefix}"
  namespace_name      = azurerm_notification_hub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# ==============================================================================
# Event Hub (Campaign Events & Channel Responses)
# ==============================================================================

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  capacity            = var.environment == "prod" ? 4 : 1

  tags = local.tags
}

resource "azurerm_eventhub" "campaign_events" {
  name                = "campaign-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "channel_responses" {
  name                = "channel-responses"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "campaign_analytics" {
  name                = "campaign-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.campaign_events.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "response_processing" {
  name                = "response-processing"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.channel_responses.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Data Factory (Customer Data Ingestion)
# ==============================================================================

resource "azurerm_data_factory" "main" {
  name                = "adf-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# ADLS Gen2 (Campaign Data Lake)
# ==============================================================================

resource "azurerm_storage_account" "datalake" {
  name                     = "stadl${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  tags = local.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "raw" {
  name               = "raw"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "segments" {
  name               = "segments"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "analytics" {
  name               = "analytics"
  storage_account_id = azurerm_storage_account.datalake.id
}

# ==============================================================================
# Synapse Analytics Workspace
# ==============================================================================

resource "azurerm_synapse_workspace" "main" {
  name                                 = "syn-${local.resource_prefix}"
  resource_group_name                  = azurerm_resource_group.main.name
  location                             = azurerm_resource_group.main.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.analytics.id
  sql_administrator_login              = "sqladmin"
  sql_administrator_login_password     = "P@ssw0rd1234!"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_synapse_firewall_rule" "allow_azure" {
  name                 = "AllowAllWindowsAzureIps"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

# ==============================================================================
# Cosmos DB (Campaign Data Store)
# ==============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

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

  tags = local.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "campaigns"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "campaigns" {
  name                = "campaigns"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/campaignId"
}

resource "azurerm_cosmosdb_sql_container" "audiences" {
  name                = "audiences"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/segmentId"
}

resource "azurerm_cosmosdb_sql_container" "content" {
  name                = "content"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/contentType"
}

resource "azurerm_cosmosdb_sql_container" "performance" {
  name                = "performance"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/campaignId"
  default_ttl         = 7776000
}

resource "azurerm_cosmosdb_sql_container" "journeys" {
  name                = "journeys"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/journeyId"
}

# ==============================================================================
# Azure Functions (Campaign Orchestration)
# ==============================================================================

resource "azurerm_storage_account" "functions" {
  name                     = "stfunc${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags
}

resource "azurerm_service_plan" "functions" {
  name                = "asp-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.environment == "prod" ? "EP1" : "Y1"
  tags                = local.tags
}

resource "azurerm_linux_function_app" "main" {
  name                       = "func-campaign-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AZURE_OPENAI_ENDPOINT"          = azurerm_cognitive_account.openai.endpoint
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "ML_WORKSPACE_NAME"              = azurerm_machine_learning_workspace.main.name
    "COMMUNICATION_CONNECTION_STRING" = azurerm_communication_service.main.primary_connection_string
    "EVENTHUB_NAMESPACE"             = azurerm_eventhub_namespace.main.name
    "REDIS_HOST"                     = azurerm_redis_cache.main.hostname
    "REDIS_PORT"                     = tostring(azurerm_redis_cache.main.ssl_port)
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
    "DATALAKE_ACCOUNT_NAME"          = azurerm_storage_account.datalake.name
    "SYNAPSE_ENDPOINT"               = azurerm_synapse_workspace.main.connectivity_endpoints["sqlOnDemand"]
  }

  tags = local.tags
}

# ==============================================================================
# Redis Cache (Session & Campaign State)
# ==============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "redis-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.environment == "prod" ? 2 : 0
  family              = var.environment == "prod" ? "C" : "C"
  sku_name            = var.environment == "prod" ? "Standard" : "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = local.tags
}

# ==============================================================================
# Outputs
# ==============================================================================

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "ml_workspace" {
  value = azurerm_machine_learning_workspace.main.name
}

output "communication_endpoint" {
  value = azurerm_communication_service.main.name
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "synapse_endpoint" {
  value = azurerm_synapse_workspace.main.connectivity_endpoints["sqlOnDemand"]
}
