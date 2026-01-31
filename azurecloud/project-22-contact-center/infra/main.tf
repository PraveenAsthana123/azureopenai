# ==============================================================================
# AI Contact Center Platform - Terraform Infrastructure
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
    key                  = "contact-center.tfstate"
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
  default = "contactctr"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Contact-Center"
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
# Virtual Network
# ==============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "services" {
  name                 = "snet-services"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "functions" {
  name                 = "snet-functions"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "functions-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]
}

# ==============================================================================
# Azure OpenAI (Agent Assist & Auto-Responses)
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
# Azure Communication Services (Voice / Chat / SMS)
# ==============================================================================

resource "azurerm_communication_service" "main" {
  name                = "acs-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  data_location       = "United States"
  tags                = local.tags
}

# ==============================================================================
# Azure Speech Services (Real-time Transcription)
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
# Azure Translator (Multi-language Support)
# ==============================================================================

resource "azurerm_cognitive_account" "translator" {
  name                  = "translator-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "TextTranslation"
  sku_name              = "S1"
  custom_subdomain_name = "translator-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure AI Search (Knowledge Base for Agent Assist)
# ==============================================================================

resource "azurerm_search_service" "main" {
  name                = "srch-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "prod" ? "standard" : "basic"
  replica_count       = var.environment == "prod" ? 2 : 1
  partition_count     = 1

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure Bot Service (Chat & Messaging Channels)
# ==============================================================================

resource "azurerm_bot_channels_registration" "main" {
  name                = "bot-${local.resource_prefix}"
  location            = "global"
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "S1" : "F0"
  microsoft_app_id    = data.azurerm_client_config.current.client_id

  tags = local.tags
}

# ==============================================================================
# Event Hub (Call Events, Chat Events, Quality Events)
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

resource "azurerm_eventhub" "chat_events" {
  name                = "chat-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "quality_events" {
  name                = "quality-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 8 : 2
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "sentiment_scoring" {
  name                = "sentiment-scoring"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.call_events.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "quality_analysis" {
  name                = "quality-analysis"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.quality_events.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Stream Analytics (Real-time Sentiment Scoring)
# ==============================================================================

resource "azurerm_stream_analytics_job" "sentiment" {
  name                                     = "asa-sentiment-${local.resource_prefix}"
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
-- Real-time sentiment scoring for contact center interactions
WITH SentimentCalc AS (
    SELECT
        interaction_id,
        agent_id,
        customer_id,
        channel,
        sentiment_score,
        AVG(sentiment_score) OVER (PARTITION BY interaction_id LIMIT DURATION(minute, 5)) as avg_sentiment,
        MIN(sentiment_score) OVER (PARTITION BY interaction_id LIMIT DURATION(minute, 5)) as min_sentiment,
        System.Timestamp() as event_time
    FROM callEvents TIMESTAMP BY event_time
)

SELECT
    interaction_id,
    agent_id,
    customer_id,
    channel,
    sentiment_score,
    avg_sentiment,
    min_sentiment,
    CASE
        WHEN min_sentiment < 0.2 THEN 'ESCALATION_NEEDED'
        WHEN avg_sentiment < 0.4 THEN 'AT_RISK'
        ELSE 'NORMAL'
    END as alert_level,
    event_time
INTO sentimentOutput
FROM SentimentCalc
QUERY

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Interactions, Sessions, Quality, Sentiment, Knowledge)
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
  name                = "contact-center"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "interactions" {
  name                = "interactions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/customer_id"
  default_ttl         = -1
}

resource "azurerm_cosmosdb_sql_container" "agent_sessions" {
  name                = "agent_sessions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/agent_id"
  default_ttl         = 604800
}

resource "azurerm_cosmosdb_sql_container" "quality_scores" {
  name                = "quality_scores"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/interaction_id"
  default_ttl         = -1
}

resource "azurerm_cosmosdb_sql_container" "customer_sentiment" {
  name                = "customer_sentiment"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/customer_id"
  default_ttl         = 2592000
}

resource "azurerm_cosmosdb_sql_container" "knowledge_articles" {
  name                = "knowledge_articles"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/category"
  default_ttl         = -1
}

# ==============================================================================
# Azure Functions (Contact Center Orchestration)
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
  name                       = "func-${local.resource_prefix}"
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
    "AZURE_TRANSLATOR_ENDPOINT"      = azurerm_cognitive_account.translator.endpoint
    "AZURE_SEARCH_ENDPOINT"          = "https://${azurerm_search_service.main.name}.search.windows.net"
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "EVENTHUB_CONNECTION"            = azurerm_eventhub_namespace.main.default_primary_connection_string
    "SIGNALR_CONNECTION"             = azurerm_signalr_service.main.primary_connection_string
    "REDIS_CONNECTION"               = azurerm_redis_cache.main.primary_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# SignalR Service (Real-time Agent Desktop Updates)
# ==============================================================================

resource "azurerm_signalr_service" "main" {
  name                = "sigr-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku {
    name     = var.environment == "prod" ? "Standard_S1" : "Free_F1"
    capacity = var.environment == "prod" ? 2 : 1
  }

  connectivity_logs_enabled = true
  messaging_logs_enabled    = true
  service_mode              = "Serverless"

  cors {
    allowed_origins = ["*"]
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
      "Get", "List", "Create", "Delete", "Purge"
    ]
  }

  tags = local.tags
}

# ==============================================================================
# Application Insights
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  tags                = local.tags
}

# ==============================================================================
# Redis Cache (Session State & Real-time Caching)
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
# Blob Storage (Call Recordings with Retention Policies)
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

resource "azurerm_storage_container" "call_recordings" {
  name                  = "call-recordings"
  storage_account_name  = azurerm_storage_account.recordings.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "chat_transcripts" {
  name                  = "chat-transcripts"
  storage_account_name  = azurerm_storage_account.recordings.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "quality_reports" {
  name                  = "quality-reports"
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

  rule {
    name    = "archive-old-transcripts"
    enabled = true

    filters {
      prefix_match = ["chat-transcripts/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 60
        tier_to_archive_after_days_since_modification_greater_than = 180
        delete_after_days_since_modification_greater_than          = 730
      }
    }
  }
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

output "communication_services_endpoint" {
  value = "https://${azurerm_communication_service.main.name}.communication.azure.com"
}

output "speech_endpoint" {
  value = azurerm_cognitive_account.speech.endpoint
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "signalr_endpoint" {
  value = azurerm_signalr_service.main.hostname
}

output "bot_endpoint" {
  value = "https://${azurerm_bot_channels_registration.main.name}.azurewebsites.net/api/messages"
}
