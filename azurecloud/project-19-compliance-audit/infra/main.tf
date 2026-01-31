# ==============================================================================
# Compliance Audit Automation - Terraform Infrastructure
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
    key                  = "compliance-audit.tfstate"
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
  default = "compaudit"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Compliance-Audit"
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

resource "azurerm_subnet" "compute" {
  name                 = "snet-compute"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "function-delegation"
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
  service_endpoints    = ["Microsoft.CognitiveServices", "Microsoft.Storage", "Microsoft.AzureCosmosDB"]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]
  service_endpoints    = ["Microsoft.KeyVault", "Microsoft.Storage"]
}

# ==============================================================================
# Azure OpenAI (Compliance Analysis)
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
# Document Intelligence (Evidence Extraction)
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
# Azure AI Search (Audit Evidence Indexing)
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
# Cosmos DB (Audit Data Store)
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
  name                = "compliance"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "audits" {
  name                = "audits"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/auditId"
}

resource "azurerm_cosmosdb_sql_container" "evidence" {
  name                = "evidence"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/evidenceId"
}

resource "azurerm_cosmosdb_sql_container" "controls" {
  name                = "controls"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/controlId"
}

resource "azurerm_cosmosdb_sql_container" "findings" {
  name                = "findings"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/findingId"
}

# ==============================================================================
# Azure Functions (Compliance Processing)
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
  name                       = "func-audit-${local.resource_prefix}"
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
    "SEARCH_ENDPOINT"                = "https://${azurerm_search_service.main.name}.search.windows.net"
    "DOCUMENT_INTELLIGENCE_ENDPOINT" = azurerm_cognitive_account.document_intelligence.endpoint
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
    "KEY_VAULT_URI"                  = azurerm_key_vault.main.vault_uri
    "AUDIT_STORAGE_ACCOUNT"          = azurerm_storage_account.evidence.name
    "LOG_ANALYTICS_WORKSPACE_ID"     = azurerm_log_analytics_workspace.main.workspace_id
  }

  tags = local.tags
}

# ==============================================================================
# Data Factory (Evidence Collection Pipelines)
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

resource "azurerm_data_factory_linked_service_cosmosdb" "main" {
  name             = "ls-cosmos-compliance"
  data_factory_id  = azurerm_data_factory.main.id
  connection_string = azurerm_cosmosdb_account.main.connection_strings[0]
  database          = "compliance"
}

resource "azurerm_data_factory_linked_service_azure_blob_storage" "evidence" {
  name              = "ls-blob-evidence"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = azurerm_storage_account.evidence.primary_connection_string
}

# ==============================================================================
# Log Analytics Workspace (Audit Trail Analysis)
# ==============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 365 : 90

  tags = local.tags
}

resource "azurerm_log_analytics_solution" "audit" {
  solution_name         = "AuditTrailAnalytics"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  workspace_resource_id = azurerm_log_analytics_workspace.main.id
  workspace_name        = azurerm_log_analytics_workspace.main.name

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/SecurityCenterFree"
  }
}

# ==============================================================================
# Blob Storage (Audit Evidence & Reports)
# ==============================================================================

resource "azurerm_storage_account" "evidence" {
  name                     = "stevid${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  tags = local.tags
}

resource "azurerm_storage_container" "evidence" {
  name                  = "audit-evidence"
  storage_account_name  = azurerm_storage_account.evidence.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "reports" {
  name                  = "audit-reports"
  storage_account_name  = azurerm_storage_account.evidence.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "control_documents" {
  name                  = "control-documents"
  storage_account_name  = azurerm_storage_account.evidence.name
  container_access_type = "private"
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

resource "azurerm_key_vault_secret" "cosmos_connection" {
  name         = "cosmos-connection-string"
  value        = azurerm_cosmosdb_account.main.connection_strings[0]
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "search_api_key" {
  name         = "search-api-key"
  value        = azurerm_search_service.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

# ==============================================================================
# Application Insights
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.tags
}

# ==============================================================================
# Storage Account for Immutable Audit Logs
# ==============================================================================

resource "azurerm_storage_account" "immutable_logs" {
  name                     = "stlog${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true

    container_delete_retention_policy {
      days = 365
    }

    delete_retention_policy {
      days = 365
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "immutable_audit_logs" {
  name                  = "immutable-audit-logs"
  storage_account_name  = azurerm_storage_account.immutable_logs.name
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "immutable_logs_policy" {
  storage_account_id = azurerm_storage_account.immutable_logs.id

  rule {
    name    = "immutable-audit-retention"
    enabled = true

    filters {
      prefix_match = ["immutable-audit-logs/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
      }
    }
  }
}

resource "azurerm_storage_container" "audit_trail_archive" {
  name                  = "audit-trail-archive"
  storage_account_name  = azurerm_storage_account.immutable_logs.name
  container_access_type = "private"
}

# ==============================================================================
# Diagnostic Settings (Audit Trail for All Resources)
# ==============================================================================

resource "azurerm_monitor_diagnostic_setting" "keyvault" {
  name                       = "diag-keyvault-audit"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AuditEvent"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "cosmos" {
  name                       = "diag-cosmos-audit"
  target_resource_id         = azurerm_cosmosdb_account.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "DataPlaneRequests"
  }

  enabled_log {
    category = "QueryRuntimeStatistics"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "function_app" {
  name                       = "diag-func-audit"
  target_resource_id         = azurerm_linux_function_app.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "FunctionAppLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
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

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.workspace_id
}
