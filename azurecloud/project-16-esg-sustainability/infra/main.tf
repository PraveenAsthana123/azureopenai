# ==============================================================================
# ESG & Sustainability Reporter - Terraform Infrastructure
# ==============================================================================
# Project 16: ESG data extraction, carbon footprint analytics,
# CSRD/TCFD compliance reporting powered by Azure OpenAI.
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
    key                  = "esg-sustainability.tfstate"
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
  default = "esgreport"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "ESG-Sustainability"
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

resource "azurerm_subnet" "default" {
  name                 = "snet-default"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  service_endpoints = [
    "Microsoft.CognitiveServices",
    "Microsoft.Storage",
    "Microsoft.KeyVault"
  ]
}

resource "azurerm_subnet" "functions" {
  name                 = "snet-functions"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "functions-delegation"
    service_delegation {
      name = "Microsoft.Web/serverFarms"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/action"
      ]
    }
  }
}

resource "azurerm_subnet" "synapse" {
  name                 = "snet-synapse"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  service_endpoints = [
    "Microsoft.Sql",
    "Microsoft.Storage"
  ]
}

# ==============================================================================
# Azure OpenAI (ESG Analysis & Report Generation)
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
# Document Intelligence (ESG Report Extraction)
# ==============================================================================

resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "di-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "di-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure AI Search (ESG Document Indexing)
# ==============================================================================

resource "azurerm_search_service" "main" {
  name                = "srch-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "standard" : "basic"
  replica_count       = var.environment == "prod" ? 2 : 1
  partition_count     = 1

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (ESG Reports, Metrics & Compliance Records)
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

resource "azurerm_cosmosdb_sql_database" "esg" {
  name                = "esg"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "reports" {
  name                = "reports"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.esg.name
  partition_key_path  = "/reportId"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "metrics" {
  name                = "metrics"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.esg.name
  partition_key_path  = "/metricCategory"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "compliance_records" {
  name                = "compliance_records"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.esg.name
  partition_key_path  = "/frameworkId"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "carbon_data" {
  name                = "carbon_data"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.esg.name
  partition_key_path  = "/scopeType"
  default_ttl         = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# ==============================================================================
# Azure Functions (ESG Processing & Scoring)
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

resource "azurerm_linux_function_app" "esg_processor" {
  name                       = "func-esg-${local.resource_prefix}"
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
      allowed_origins = ["https://portal.azure.com"]
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AZURE_OPENAI_ENDPOINT"          = azurerm_cognitive_account.openai.endpoint
    "DOCUMENT_INTELLIGENCE_ENDPOINT" = azurerm_cognitive_account.document_intelligence.endpoint
    "SEARCH_ENDPOINT"                = "https://${azurerm_search_service.main.name}.search.windows.net"
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "DATALAKE_ENDPOINT"              = azurerm_storage_account.datalake.primary_dfs_endpoint
    "KEY_VAULT_URI"                  = azurerm_key_vault.main.vault_uri
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# Data Factory (ESG Data Pipeline Ingestion)
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

resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "datalake" {
  name                 = "ls-datalake"
  data_factory_id      = azurerm_data_factory.main.id
  url                  = azurerm_storage_account.datalake.primary_dfs_endpoint
  use_managed_identity = true
}

resource "azurerm_data_factory_linked_service_cosmosdb" "cosmos" {
  name             = "ls-cosmosdb"
  data_factory_id  = azurerm_data_factory.main.id
  account_endpoint = azurerm_cosmosdb_account.main.endpoint
  account_key      = azurerm_cosmosdb_account.main.primary_key
  database         = azurerm_cosmosdb_sql_database.esg.name
}

# ==============================================================================
# ADLS Gen2 Storage (ESG Data Lake)
# ==============================================================================

resource "azurerm_storage_account" "datalake" {
  name                     = "stadl${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  tags = local.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "raw_reports" {
  name               = "raw-reports"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "processed" {
  name               = "processed"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "analytics" {
  name               = "analytics"
  storage_account_id = azurerm_storage_account.datalake.id
}

# ==============================================================================
# Synapse Analytics (ESG Analytics Workspace)
# ==============================================================================

resource "azurerm_storage_account" "synapse" {
  name                     = "stsyn${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  tags = local.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "synapse_fs" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.synapse.id
}

resource "azurerm_synapse_workspace" "main" {
  name                                 = "syn-${local.resource_prefix}"
  location                             = azurerm_resource_group.main.location
  resource_group_name                  = azurerm_resource_group.main.name
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse_fs.id
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
      "Purge"
    ]

    key_permissions = [
      "Get",
      "List",
      "Create"
    ]
  }

  tags = local.tags
}

resource "azurerm_key_vault_secret" "cosmos_connection" {
  name         = "cosmos-connection-string"
  value        = azurerm_cosmosdb_account.main.primary_sql_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "search_key" {
  name         = "search-api-key"
  value        = azurerm_search_service.main.primary_key
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
  retention_in_days   = var.environment == "prod" ? 90 : 30

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
# Purview Account (Data Governance & Lineage)
# ==============================================================================

resource "azurerm_purview_account" "main" {
  name                = "pview-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Outputs
# ==============================================================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "openai_endpoint" {
  description = "Azure OpenAI service endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "search_endpoint" {
  description = "Azure AI Search service endpoint"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "cosmos_endpoint" {
  description = "Cosmos DB account endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  description = "ESG processor function app URL"
  value       = "https://${azurerm_linux_function_app.esg_processor.default_hostname}"
}

output "synapse_endpoint" {
  description = "Synapse Analytics workspace endpoint"
  value       = azurerm_synapse_workspace.main.connectivity_endpoints
}

output "datalake_endpoint" {
  description = "ADLS Gen2 data lake DFS endpoint"
  value       = azurerm_storage_account.datalake.primary_dfs_endpoint
}
