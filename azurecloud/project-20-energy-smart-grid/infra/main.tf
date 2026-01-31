# ==============================================================================
# Energy & Utilities Smart Grid - Terraform Infrastructure
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
    key                  = "energy-smart-grid.tfstate"
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
  default = "smartgrid"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Energy-Smart-Grid"
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
  tags                = local.tags
}

resource "azurerm_subnet" "iot" {
  name                 = "snet-iot"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "analytics" {
  name                 = "snet-analytics"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "functions" {
  name                 = "snet-functions"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  delegation {
    name = "functions-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# ==============================================================================
# Azure OpenAI (Load Forecasting & Outage Prediction)
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
# IoT Hub (Smart Meter Ingestion)
# ==============================================================================

resource "azurerm_iothub" "main" {
  name                = "iot-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = var.environment == "prod" ? "S2" : "S1"
    capacity = var.environment == "prod" ? 2 : 1
  }

  route {
    name           = "telemetry-to-eventhub"
    source         = "DeviceMessages"
    condition      = "true"
    endpoint_names = ["eventhub-meter-readings"]
    enabled        = true
  }

  route {
    name           = "grid-events-route"
    source         = "DeviceMessages"
    condition      = "$body.messageType = 'gridEvent'"
    endpoint_names = ["eventhub-grid-events"]
    enabled        = true
  }

  tags = local.tags
}

# ==============================================================================
# Event Hub Namespace & Event Hubs
# ==============================================================================

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  capacity            = var.environment == "prod" ? 4 : 1

  tags = local.tags
}

resource "azurerm_eventhub" "meter_readings" {
  name                = "meter-readings"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 32 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "grid_events" {
  name                = "grid-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "stream_analytics" {
  name                = "stream-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.meter_readings.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "ml_forecasting" {
  name                = "ml-forecasting"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.meter_readings.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "outage_detection" {
  name                = "outage-detection"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.grid_events.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Stream Analytics (Real-time Meter Aggregation)
# ==============================================================================

resource "azurerm_stream_analytics_job" "meter_aggregation" {
  name                                     = "asa-meter-${local.resource_prefix}"
  resource_group_name                      = azurerm_resource_group.main.name
  location                                 = azurerm_resource_group.main.location
  streaming_units                          = var.environment == "prod" ? 12 : 3
  compatibility_level                      = "1.2"
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 10
  events_out_of_order_max_delay_in_seconds = 5
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"

  transformation_query = <<QUERY
-- Aggregate smart meter readings per substation in real-time
WITH MeterAggregation AS (
    SELECT
        substation_id,
        COUNT(*) as reading_count,
        AVG(power_consumption_kwh) as avg_consumption,
        MAX(power_consumption_kwh) as peak_consumption,
        MIN(power_consumption_kwh) as min_consumption,
        SUM(power_consumption_kwh) as total_consumption,
        AVG(voltage) as avg_voltage,
        STDEV(voltage) as voltage_deviation,
        System.Timestamp() as window_end
    FROM meterReadingsInput TIMESTAMP BY event_time
    GROUP BY substation_id, TumblingWindow(minute, 15)
),
AnomalyDetection AS (
    SELECT
        substation_id,
        avg_consumption,
        peak_consumption,
        voltage_deviation,
        CASE
            WHEN voltage_deviation > 10.0 THEN 'HIGH'
            WHEN voltage_deviation > 5.0 THEN 'MEDIUM'
            ELSE 'NORMAL'
        END as anomaly_level,
        window_end
    FROM MeterAggregation
)

SELECT
    substation_id,
    avg_consumption,
    peak_consumption,
    voltage_deviation,
    anomaly_level,
    window_end
INTO aggregationOutput
FROM AnomalyDetection
WHERE anomaly_level != 'NORMAL'
QUERY

  tags = local.tags
}

# ==============================================================================
# Azure ML Workspace (Load Forecasting & Outage Prediction)
# ==============================================================================

resource "azurerm_application_insights" "ml" {
  name                = "appi-ml-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  tags                = local.tags
}

resource "azurerm_key_vault" "ml" {
  name                = "kv-ml-${local.resource_prefix}"
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
  application_insights_id = azurerm_application_insights.ml.id
  key_vault_id            = azurerm_key_vault.ml.id
  storage_account_id      = azurerm_storage_account.ml.id

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Meters, Forecasts, Outages, Recommendations)
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
  name                = "smart-grid"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "meters" {
  name                = "meters"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/meter_id"
}

resource "azurerm_cosmosdb_sql_container" "forecasts" {
  name                = "forecasts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/substation_id"
  default_ttl         = 604800
}

resource "azurerm_cosmosdb_sql_container" "outages" {
  name                = "outages"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/region_id"
}

resource "azurerm_cosmosdb_sql_container" "recommendations" {
  name                = "recommendations"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/customer_id"
  default_ttl         = 2592000
}

# ==============================================================================
# Azure Functions (Grid Analytics Processing)
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

resource "azurerm_linux_function_app" "grid_analytics" {
  name                       = "func-grid-${local.resource_prefix}"
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
    "IOTHUB_CONNECTION"              = azurerm_iothub.main.hostname
    "EVENTHUB_NAMESPACE"             = azurerm_eventhub_namespace.main.name
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# ADLS Gen2 Storage (Telemetry Data Lake)
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

resource "azurerm_storage_data_lake_gen2_filesystem" "raw_telemetry" {
  name               = "raw-telemetry"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "processed" {
  name               = "processed"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "models" {
  name               = "models"
  storage_account_id = azurerm_storage_account.datalake.id
}

# ==============================================================================
# Time Series Insights (Gen2)
# ==============================================================================

resource "azurerm_iot_time_series_insights_gen2_environment" "main" {
  name                = "tsi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "L1"
  id_properties       = ["meter_id"]

  storage {
    name = azurerm_storage_account.datalake.name
    key  = azurerm_storage_account.datalake.primary_access_key
  }

  tags = local.tags
}

# ==============================================================================
# Key Vault (Secrets & Certificates)
# ==============================================================================

resource "azurerm_key_vault" "main" {
  name                = "kv-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = true
  soft_delete_retention_days = 90

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

    key_permissions = [
      "Get",
      "List",
      "Create",
      "Delete",
    ]

    certificate_permissions = [
      "Get",
      "List",
      "Create",
      "Delete",
    ]
  }

  tags = local.tags
}

# ==============================================================================
# Application Insights (Monitoring & Diagnostics)
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  retention_in_days   = 90

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

output "iothub_hostname" {
  value = azurerm_iothub.main.hostname
}

output "eventhub_namespace" {
  value = azurerm_eventhub_namespace.main.name
}

output "ml_workspace_name" {
  value = azurerm_machine_learning_workspace.main.name
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.grid_analytics.default_hostname}"
}
