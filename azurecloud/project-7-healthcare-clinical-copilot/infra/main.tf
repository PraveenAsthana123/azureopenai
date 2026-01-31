# ==============================================================================
# Healthcare Clinical Copilot - Terraform Infrastructure
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
    key                  = "healthcare-copilot.tfstate"
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
  default = "healthcopilot"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Healthcare-Clinical-Copilot"
    ManagedBy   = "Terraform"
  }
}

# ==============================================================================
# Data Sources
# ==============================================================================

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

  tags = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "app-delegation"
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

  service_endpoints = [
    "Microsoft.CognitiveServices",
    "Microsoft.AzureCosmosDB",
    "Microsoft.KeyVault",
    "Microsoft.Storage"
  ]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  service_endpoints = [
    "Microsoft.Web",
    "Microsoft.Storage"
  ]
}

# ==============================================================================
# Azure OpenAI (Clinical Reasoning)
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
# Azure Health Data Services (FHIR)
# ==============================================================================

resource "azurerm_healthcare_workspace" "main" {
  name                = "hcw-${replace(local.resource_prefix, "-", "")}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.tags
}

resource "azurerm_healthcare_fhir_service" "main" {
  name                = "fhir-${replace(local.resource_prefix, "-", "")}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_healthcare_workspace.main.id
  kind                = "fhir-R4"

  identity {
    type = "SystemAssigned"
  }

  authentication {
    authority = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}"
    audience  = "https://${azurerm_healthcare_workspace.main.name}-fhir-${replace(local.resource_prefix, "-", "")}.fhir.azurehealthcareapis.com"
  }

  access_policy_object_ids = [
    data.azurerm_client_config.current.object_id
  ]

  configuration_export_storage_account_name = azurerm_storage_account.clinical_docs.name

  tags = local.tags
}

# ==============================================================================
# Azure AI Search (Clinical Knowledge Index)
# ==============================================================================

resource "azurerm_search_service" "main" {
  name                = "srch-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.environment == "prod" ? "standard" : "basic"
  replica_count       = var.environment == "prod" ? 3 : 1
  partition_count     = var.environment == "prod" ? 2 : 1

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure Functions (Clinical Copilot API)
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

resource "azurerm_linux_function_app" "clinical_api" {
  name                       = "func-clinical-${local.resource_prefix}"
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
    "FHIR_ENDPOINT"                  = "https://${azurerm_healthcare_workspace.main.name}-fhir-${replace(local.resource_prefix, "-", "")}.fhir.azurehealthcareapis.com"
    "SEARCH_ENDPOINT"                = "https://${azurerm_search_service.main.name}.search.windows.net"
    "REDIS_CONNECTION"               = azurerm_redis_cache.main.primary_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
    "KEY_VAULT_URI"                  = azurerm_key_vault.main.vault_uri
    "CLINICAL_DOCS_STORAGE"          = azurerm_storage_account.clinical_docs.primary_blob_endpoint
  }

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Clinical Data Store)
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
  name                = "clinical-copilot"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "patient_summaries" {
  name                = "patient_summaries"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/patient_id"
  default_ttl         = -1
}

resource "azurerm_cosmosdb_sql_container" "drug_interactions" {
  name                = "drug_interactions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/drug_pair_key"
  default_ttl         = -1
}

resource "azurerm_cosmosdb_sql_container" "clinical_sessions" {
  name                = "clinical_sessions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/session_id"
  default_ttl         = 2592000
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
      "Recover",
      "Backup",
      "Restore"
    ]

    key_permissions = [
      "Get",
      "List",
      "Create",
      "Delete",
      "Recover",
      "Backup",
      "Restore"
    ]

    certificate_permissions = [
      "Get",
      "List",
      "Create",
      "Delete",
      "Recover",
      "Backup",
      "Restore"
    ]
  }

  tags = local.tags
}

# ==============================================================================
# Application Insights (Observability)
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  retention_in_days   = var.environment == "prod" ? 90 : 30
  tags                = local.tags
}

# ==============================================================================
# Storage Account (Clinical Documents)
# ==============================================================================

resource "azurerm_storage_account" "clinical_docs" {
  name                     = "stclin${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_storage_container" "clinical_notes" {
  name                  = "clinical-notes"
  storage_account_name  = azurerm_storage_account.clinical_docs.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "medical_records" {
  name                  = "medical-records"
  storage_account_name  = azurerm_storage_account.clinical_docs.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "lab_results" {
  name                  = "lab-results"
  storage_account_name  = azurerm_storage_account.clinical_docs.name
  container_access_type = "private"
}

# ==============================================================================
# Redis Cache (Session & Low-Latency Cache)
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

output "fhir_endpoint" {
  value = "https://${azurerm_healthcare_workspace.main.name}-fhir-${replace(local.resource_prefix, "-", "")}.fhir.azurehealthcareapis.com"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.clinical_api.default_hostname}"
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}
