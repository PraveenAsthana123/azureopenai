# ==============================================================================
# Voice AI Outbound Platform - Terraform Infrastructure
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
    key                  = "voice-ai-outbound.tfstate"
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
  default = "voiceai"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Voice-AI-Outbound"
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
  address_space       = ["10.26.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "functions" {
  name                 = "snet-functions"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.26.1.0/24"]

  delegation {
    name = "functions-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "services" {
  name                 = "snet-services"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.26.2.0/24"]
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.26.3.0/24"]
}

# ==============================================================================
# Azure OpenAI (GPT-4o Deployment)
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

# ==============================================================================
# Azure Communication Services (Voice Calling)
# ==============================================================================

resource "azurerm_communication_service" "main" {
  name                = "acs-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  data_location       = "United States"
  tags                = local.tags
}

# ==============================================================================
# Azure Speech Services (Neural TTS / STT)
# ==============================================================================

resource "azurerm_cognitive_account" "speech" {
  name                  = "speech-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "SpeechServices"
  sku_name              = "S0"
  custom_subdomain_name = "speech-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure AI Language (Sentiment Analysis)
# ==============================================================================

resource "azurerm_cognitive_account" "language" {
  name                  = "lang-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "TextAnalytics"
  sku_name              = "S"
  custom_subdomain_name = "lang-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure Bot Service
# ==============================================================================

resource "azurerm_bot_channels_registration" "main" {
  name                = "bot-${local.resource_prefix}"
  location            = "global"
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "S1"
  microsoft_app_id    = data.azurerm_client_config.current.client_id

  tags = local.tags
}

# ==============================================================================
# Service Bus (Call Orchestration Queues)
# ==============================================================================

resource "azurerm_servicebus_namespace" "main" {
  name                = "sbns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Premium" : "Standard"
  capacity            = var.environment == "prod" ? 1 : 0

  tags = local.tags
}

resource "azurerm_servicebus_queue" "outbound_call" {
  name         = "outbound-call-queue"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_delivery_count        = 10
  lock_duration             = "PT5M"
  default_message_ttl       = "P1D"
  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_queue" "callback" {
  name         = "callback-queue"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_delivery_count        = 5
  lock_duration             = "PT2M"
  default_message_ttl       = "P1D"
  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_queue" "escalation" {
  name         = "escalation-queue"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_delivery_count        = 3
  lock_duration             = "PT1M"
  default_message_ttl       = "PT12H"
  dead_lettering_on_message_expiration = true
}

# ==============================================================================
# Event Hub (Call Events & Analytics)
# ==============================================================================

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  capacity            = var.environment == "prod" ? 4 : 1

  tags = local.tags
}

resource "azurerm_eventhub" "call_events" {
  name                = "call-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "analytics_events" {
  name                = "analytics-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 8 : 2
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "stream_analytics" {
  name                = "stream-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.call_events.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "realtime_dashboard" {
  name                = "realtime-dashboard"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.analytics_events.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Stream Analytics (Real-time Call Analytics)
# ==============================================================================

resource "azurerm_stream_analytics_job" "call_analytics" {
  name                                     = "asa-calls-${local.resource_prefix}"
  resource_group_name                      = azurerm_resource_group.main.name
  location                                 = azurerm_resource_group.main.location
  streaming_units                          = var.environment == "prod" ? 6 : 3
  compatibility_level                      = "1.2"
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 5
  events_out_of_order_max_delay_in_seconds = 0
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"

  transformation_query = <<QUERY
-- Real-time call analytics aggregation
WITH CallMetrics AS (
    SELECT
        campaign_id,
        COUNT(*) as total_calls,
        SUM(CASE WHEN outcome = 'connected' THEN 1 ELSE 0 END) as connected_calls,
        AVG(duration_seconds) as avg_duration,
        AVG(sentiment_score) as avg_sentiment,
        System.Timestamp() as window_end
    FROM callEvents TIMESTAMP BY event_time
    GROUP BY campaign_id, TumblingWindow(minute, 5)
)

SELECT
    campaign_id,
    total_calls,
    connected_calls,
    avg_duration,
    avg_sentiment,
    CAST(connected_calls AS float) / CAST(total_calls AS float) as connect_rate,
    window_end
INTO analyticsOutput
FROM CallMetrics
QUERY

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Campaign Data & Call Records)
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
  name                = "voice-ai"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "campaigns" {
  name                = "campaigns"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/campaign_id"
}

resource "azurerm_cosmosdb_sql_container" "call_records" {
  name                = "call_records"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/campaign_id"
  default_ttl         = 7776000  # 90 days
}

resource "azurerm_cosmosdb_sql_container" "dnc_list" {
  name                = "dnc_list"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/phone_hash"
}

resource "azurerm_cosmosdb_sql_container" "scripts" {
  name                = "scripts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/script_id"
}

resource "azurerm_cosmosdb_sql_container" "outcomes" {
  name                = "outcomes"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/call_id"
  default_ttl         = 15552000  # 180 days
}

# ==============================================================================
# Azure Functions (Call Orchestration)
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

resource "azurerm_linux_function_app" "orchestrator" {
  name                       = "func-voice-${local.resource_prefix}"
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
    "AZURE_SPEECH_ENDPOINT"          = azurerm_cognitive_account.speech.endpoint
    "AZURE_LANGUAGE_ENDPOINT"        = azurerm_cognitive_account.language.endpoint
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "SERVICEBUS_CONNECTION"          = azurerm_servicebus_namespace.main.default_primary_connection_string
    "COMMUNICATION_CONNECTION"       = azurerm_communication_service.main.primary_connection_string
    "REDIS_CONNECTION"               = azurerm_redis_cache.main.primary_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# Blob Storage (Call Recordings with Retention)
# ==============================================================================

resource "azurerm_storage_account" "recordings" {
  name                     = "strec${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 14
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "recordings" {
  name                  = "call-recordings"
  storage_account_name  = azurerm_storage_account.recordings.name
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "recordings_lifecycle" {
  storage_account_id = azurerm_storage_account.recordings.id

  rule {
    name    = "archive-old-recordings"
    enabled = true

    filters {
      prefix_match = ["call-recordings/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
        delete_after_days_since_modification_greater_than          = 365
      }
    }
  }
}

# ==============================================================================
# Redis Cache (DNC List Cache & Session State)
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
# Key Vault
# ==============================================================================

resource "azurerm_key_vault" "main" {
  name                = "kv-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge"
    ]

    key_permissions = [
      "Get", "List", "Create", "Delete"
    ]
  }

  tags = local.tags
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "speech_key" {
  name         = "speech-api-key"
  value        = azurerm_cognitive_account.speech.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "language_key" {
  name         = "language-api-key"
  value        = azurerm_cognitive_account.language.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-primary-key"
  value        = azurerm_cosmosdb_account.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_key" {
  name         = "redis-access-key"
  value        = azurerm_redis_cache.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

# ==============================================================================
# Application Insights
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  retention_in_days   = 90
  tags                = local.tags
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

output "communication_endpoint" {
  value = "https://${azurerm_communication_service.main.name}.communication.azure.com"
}

output "speech_endpoint" {
  value = azurerm_cognitive_account.speech.endpoint
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.orchestrator.default_hostname}"
}

output "servicebus_namespace" {
  value = azurerm_servicebus_namespace.main.name
}
