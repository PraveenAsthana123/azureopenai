# ==============================================================================
# Supply Chain Optimizer - Terraform Infrastructure
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
    key                  = "supply-chain.tfstate"
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
  default = "supplychain"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Supply-Chain-Optimizer"
    ManagedBy   = "Terraform"
  }
}

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

  tags = local.tags
}

resource "azurerm_subnet" "compute" {
  name                 = "snet-compute"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.CognitiveServices",
  ]
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.AzureCosmosDB",
    "Microsoft.EventHub",
  ]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
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
# Azure OpenAI (Demand Forecasting & Supplier Risk Analysis)
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
# Event Hub (Supply Chain Events & Demand Signals)
# ==============================================================================

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  capacity            = var.environment == "prod" ? 4 : 1

  tags = local.tags
}

resource "azurerm_eventhub" "supply_events" {
  name                = "supply-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub" "demand_signals" {
  name                = "demand-signals"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.environment == "prod" ? 16 : 4
  message_retention   = 7
}

resource "azurerm_eventhub_consumer_group" "demand_analytics" {
  name                = "demand-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.demand_signals.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_eventhub_consumer_group" "supply_ml" {
  name                = "supply-ml-processing"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.supply_events.name
  resource_group_name = azurerm_resource_group.main.name
}

# ==============================================================================
# Stream Analytics (Demand Signal Processing)
# ==============================================================================

resource "azurerm_stream_analytics_job" "demand" {
  name                                     = "asa-demand-${local.resource_prefix}"
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
-- Aggregate demand signals per product and region
WITH DemandAggregation AS (
    SELECT
        product_id,
        region,
        COUNT(*) as signal_count,
        SUM(quantity) as total_demand,
        AVG(CAST(quantity AS float)) as avg_demand,
        MAX(quantity) as peak_demand,
        System.Timestamp() as window_end
    FROM demandSignals TIMESTAMP BY event_time
    GROUP BY product_id, region, TumblingWindow(hour, 1)
),
SupplyAlerts AS (
    SELECT
        supplier_id,
        product_id,
        event_type,
        severity,
        COUNT(*) as alert_count,
        System.Timestamp() as window_end
    FROM supplyEvents TIMESTAMP BY event_time
    WHERE event_type IN ('delay', 'shortage', 'quality_issue')
    GROUP BY supplier_id, product_id, event_type, severity, TumblingWindow(hour, 1)
)

SELECT
    product_id,
    region,
    signal_count,
    total_demand,
    avg_demand,
    peak_demand,
    window_end
INTO demandOutput
FROM DemandAggregation

SELECT
    supplier_id,
    product_id,
    event_type,
    severity,
    alert_count,
    window_end
INTO supplyAlertOutput
FROM SupplyAlerts
QUERY

  tags = local.tags
}

# ==============================================================================
# Azure ML Workspace (Forecasting Models)
# ==============================================================================

resource "azurerm_application_insights" "ml" {
  name                = "appi-ml-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  tags                = local.tags
}

data "azurerm_client_config" "current" {}

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
# Data Factory (Supply Chain Data Pipelines)
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
# Data Lake Storage Gen2 (Supply Chain Data)
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

resource "azurerm_storage_data_lake_gen2_filesystem" "curated" {
  name               = "curated"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "features" {
  name               = "features"
  storage_account_id = azurerm_storage_account.datalake.id
}

# ==============================================================================
# Cosmos DB (Forecasts, Inventory & Supplier Risk)
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
  name                = "supply-chain"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "forecasts" {
  name                = "forecasts"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/product_id"
  default_ttl         = 2592000 # 30 days
}

resource "azurerm_cosmosdb_sql_container" "inventory" {
  name                = "inventory"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/warehouse_id"
}

resource "azurerm_cosmosdb_sql_container" "supplier_risk" {
  name                = "supplier_risk"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/supplier_id"
  default_ttl         = 7776000 # 90 days
}

# ==============================================================================
# Azure Functions (Optimization Engine)
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

resource "azurerm_linux_function_app" "optimizer" {
  name                       = "func-optimizer-${local.resource_prefix}"
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
    "EVENTHUB_NAMESPACE"             = azurerm_eventhub_namespace.main.name
    "DATALAKE_ACCOUNT_NAME"          = azurerm_storage_account.datalake.name
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
  }

  tags = local.tags
}

# ==============================================================================
# Key Vault (Secrets Management)
# ==============================================================================

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
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
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_linux_function_app.optimizer.identity[0].principal_id

    secret_permissions = [
      "Get",
      "List",
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
  value = "https://${azurerm_linux_function_app.optimizer.default_hostname}"
}
