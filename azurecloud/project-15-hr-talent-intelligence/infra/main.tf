# ==============================================================================
# HR Talent Intelligence Platform - Terraform Infrastructure
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
    key                  = "hr-talent.tfstate"
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
  default = "hrtalent"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "HR-Talent-Intelligence"
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

  tags = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
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

  service_endpoints = [
    "Microsoft.CognitiveServices",
    "Microsoft.Storage",
    "Microsoft.AzureCosmosDB"
  ]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault"
  ]
}

# ==============================================================================
# Azure OpenAI (Resume Analysis & Skill Extraction)
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
# Azure AI Search (Resume & Skill Indexing)
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
# Document Intelligence (Resume Parsing)
# ==============================================================================

resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "docint-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "docint-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Candidates, Skills, Job Matches, Workforce Plans)
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
  name                = "hr-talent"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "candidates" {
  name                = "candidates"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/candidate_id"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/resume_text/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "skills" {
  name                = "skills"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/skill_category"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "job_matches" {
  name                = "job_matches"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/job_id"
  default_ttl         = 2592000
}

resource "azurerm_cosmosdb_sql_container" "workforce_plans" {
  name                = "workforce_plans"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/department_id"
}

# ==============================================================================
# Azure Functions (Resume Processing & Skill Analysis)
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
    "AZURE_SEARCH_ENDPOINT"          = "https://${azurerm_search_service.main.name}.search.windows.net"
    "DOCUMENT_INTELLIGENCE_ENDPOINT" = azurerm_cognitive_account.document_intelligence.endpoint
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "DATALAKE_ENDPOINT"              = azurerm_storage_account.datalake.primary_dfs_endpoint
    "REDIS_HOST"                     = azurerm_redis_cache.main.hostname
    "REDIS_PORT"                     = azurerm_redis_cache.main.ssl_port
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# Data Factory (HR System Data Ingestion)
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
  database         = azurerm_cosmosdb_sql_database.main.name
}

# ==============================================================================
# ADLS Gen2 Storage (Resumes, Profiles, Analytics)
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

resource "azurerm_storage_data_lake_gen2_filesystem" "resumes" {
  name               = "resumes"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "profiles" {
  name               = "profiles"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "analytics" {
  name               = "analytics"
  storage_account_id = azurerm_storage_account.datalake.id
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

  tags = local.tags
}

# ==============================================================================
# Redis Cache (Skill Taxonomy & Session Caching)
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

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "datalake_endpoint" {
  value = azurerm_storage_account.datalake.primary_dfs_endpoint
}
