# ==============================================================================
# Real-Time Analytics Dashboard - Terraform Infrastructure
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
    key                  = "realtime-analytics.tfstate"
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
  default = "rtanalytics"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Realtime-Analytics-Dashboard"
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
  address_space       = ["10.0.0.0/16"]

  tags = local.tags
}

resource "azurerm_subnet" "compute" {
  name                 = "snet-compute"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

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
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "endpoints" {
  name                 = "snet-endpoints"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  private_endpoint_network_policies_enabled = true
}

# ==============================================================================
# Azure OpenAI (NL-to-KQL Translation)
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
# Azure Data Explorer (KQL Query Engine)
# ==============================================================================

resource "azurerm_kusto_cluster" "main" {
  name                = "adx${replace(local.resource_prefix, "-", "")}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku {
    name     = var.environment == "prod" ? "Standard_D13_v2" : "Dev(No SLA)_Standard_E2a_v4"
    capacity = var.environment == "prod" ? 2 : 1
  }

  identity {
    type = "SystemAssigned"
  }

  streaming_ingestion_enabled = true
  purge_enabled               = true

  tags = local.tags
}

resource "azurerm_kusto_database" "analytics" {
  name                = "analytics"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  cluster_name        = azurerm_kusto_cluster.main.name

  hot_cache_period   = "P7D"
  soft_delete_period = "P31D"
}

# ==============================================================================
# Event Hub (Streaming Ingestion)
# ==============================================================================

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  capacity            = var.environment == "prod" ? 4 : 1

  tags = local.tags
}

resource "azurerm_eventhub" "telemetry" {
  name                = "telemetry-stream"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 32 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "alerts" {
  name                = "alerts-stream"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 2
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "adx_telemetry" {
  name                = "adx-ingestion"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.telemetry.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "stream_analytics" {
  name                = "stream-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.telemetry.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "functions_alerts" {
  name                = "functions-alerts"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.alerts.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Stream Analytics (Anomaly Detection)
# ==============================================================================

resource "azurerm_stream_analytics_job" "anomaly_detection" {
  name                                     = "asa-anomaly-${local.resource_prefix}"
  resource_group_name                      = azurerm_resource_group.main.name
  location                                 = azurerm_resource_group.main.location
  streaming_units                          = var.environment == "prod" ? 6 : 3
  compatibility_level                      = "1.2"
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 10
  events_out_of_order_max_delay_in_seconds = 5
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"

  transformation_query = <<QUERY
-- Real-time anomaly detection on telemetry stream
WITH AnomalyDetection AS (
    SELECT
        metric_name,
        metric_value,
        source_id,
        AnomalyDetection_SpikeAndDip(
            CAST(metric_value AS float),
            95,
            120,
            'spikesanddips'
        ) OVER (PARTITION BY metric_name LIMIT DURATION(second, 120)) AS anomaly_scores,
        System.Timestamp() AS event_time
    FROM telemetryInput TIMESTAMP BY event_time
),
AnomalyAlerts AS (
    SELECT
        metric_name,
        metric_value,
        source_id,
        event_time,
        anomaly_scores.IsAnomaly AS is_anomaly,
        anomaly_scores.Score AS anomaly_score
    FROM AnomalyDetection
    WHERE anomaly_scores.IsAnomaly = 1
)

SELECT
    metric_name,
    metric_value,
    source_id,
    event_time,
    anomaly_score,
    'spike_dip' AS anomaly_type
INTO alertsOutput
FROM AnomalyAlerts
QUERY

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Dashboard State & Query Cache)
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

resource "azurerm_cosmosdb_sql_database" "analytics" {
  name                = "analytics"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "dashboards" {
  name                = "dashboards"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.analytics.name
  partition_key_path  = "/userId"
}

resource "azurerm_cosmosdb_sql_container" "alerts" {
  name                = "alerts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.analytics.name
  partition_key_path  = "/alertType"
  default_ttl         = 604800
}

resource "azurerm_cosmosdb_sql_container" "query_cache" {
  name                = "query_cache"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.analytics.name
  partition_key_path  = "/queryHash"
  default_ttl         = 3600
}

# ==============================================================================
# Azure Functions (API & Orchestration)
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

    cors {
      allowed_origins = ["*"]
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AZURE_OPENAI_ENDPOINT"          = azurerm_cognitive_account.openai.endpoint
    "AZURE_OPENAI_DEPLOYMENT"        = azurerm_cognitive_deployment.gpt4o.name
    "ADX_ENDPOINT"                   = azurerm_kusto_cluster.main.uri
    "ADX_DATABASE"                   = azurerm_kusto_database.analytics.name
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "COSMOS_DATABASE"                = azurerm_cosmosdb_sql_database.analytics.name
    "EVENTHUB_CONNECTION"            = azurerm_eventhub_namespace.main.default_primary_connection_string
    "SIGNALR_CONNECTION_STRING"      = azurerm_signalr_service.main.primary_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
    "KEY_VAULT_URI"                  = azurerm_key_vault.main.vault_uri
  }

  tags = local.tags
}

# ==============================================================================
# SignalR Service (Real-Time Push to Clients)
# ==============================================================================

resource "azurerm_signalr_service" "main" {
  name                = "sigr-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku {
    name     = var.environment == "prod" ? "Standard_S1" : "Free_F1"
    capacity = 1
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
# Key Vault (Secrets Management)
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
      "Get",
      "List",
      "Set",
      "Delete",
      "Purge",
    ]
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_linux_function_app.main.identity[0].principal_id

    secret_permissions = [
      "Get",
      "List",
    ]
  }

  tags = local.tags
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-primary-key"
  value        = azurerm_cosmosdb_account.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "eventhub_connection" {
  name         = "eventhub-connection-string"
  value        = azurerm_eventhub_namespace.main.default_primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

# ==============================================================================
# Application Insights (Monitoring & Telemetry)
# ==============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

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

output "adx_endpoint" {
  value = azurerm_kusto_cluster.main.uri
}

output "eventhub_namespace" {
  value = azurerm_eventhub_namespace.main.name
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
