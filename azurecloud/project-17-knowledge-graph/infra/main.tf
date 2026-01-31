# ==============================================================================
# Knowledge Graph Builder - Terraform Infrastructure
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
    key                  = "knowledge-graph.tfstate"
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
  default = "knowledgegraph"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Knowledge-Graph"
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

  service_endpoints = [
    "Microsoft.AzureCosmosDB",
    "Microsoft.Storage",
    "Microsoft.KeyVault",
  ]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  service_endpoints = [
    "Microsoft.CognitiveServices",
    "Microsoft.Search",
  ]
}

# ==============================================================================
# Azure OpenAI (Entity Extraction & Relationship Inference)
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
# Cosmos DB with Gremlin API (Knowledge Graph Store)
# ==============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  capabilities {
    name = "EnableGremlin"
  }

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = local.tags
}

resource "azurerm_cosmosdb_gremlin_database" "main" {
  name                = "knowledge-graph"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = var.environment == "prod" ? 1000 : 400
}

resource "azurerm_cosmosdb_gremlin_graph" "entities" {
  name                = "entities"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_gremlin_database.main.name
  partition_key_path  = "/category"

  index_policy {
    automatic      = true
    indexing_mode  = "consistent"
    included_paths = ["/*"]
    excluded_paths = ["/\"_etag\"/?"]
  }

  unique_key {
    paths = ["/entityId"]
  }
}

# ==============================================================================
# Azure AI Search (Document & Entity Indexing)
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
# Document Intelligence (Document Parsing & Structure Extraction)
# ==============================================================================

resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "di-${local.resource_prefix}"
  location              = azurerm_resource_group.main.location
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
# Azure Functions (Graph Processing & RAG Orchestration)
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
    "FUNCTIONS_WORKER_RUNTIME"   = "python"
    "AZURE_OPENAI_ENDPOINT"      = azurerm_cognitive_account.openai.endpoint
    "COSMOS_GREMLIN_ENDPOINT"    = azurerm_cosmosdb_account.main.endpoint
    "SEARCH_ENDPOINT"            = "https://${azurerm_search_service.main.name}.search.windows.net"
    "DOCUMENT_INTEL_ENDPOINT"    = azurerm_cognitive_account.document_intelligence.endpoint
    "BLOB_STORAGE_ENDPOINT"      = azurerm_storage_account.documents.primary_blob_endpoint
    "REDIS_HOST"                 = azurerm_redis_cache.main.hostname
    "REDIS_PORT"                 = azurerm_redis_cache.main.ssl_port
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
    "KEY_VAULT_URI"              = azurerm_key_vault.main.vault_uri
  }

  tags = local.tags
}

# ==============================================================================
# Data Factory (Document Ingestion Pipelines)
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

resource "azurerm_data_factory_linked_service_azure_blob_storage" "documents" {
  name              = "ls-blob-documents"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = azurerm_storage_account.documents.primary_connection_string
}

resource "azurerm_data_factory_linked_service_cosmosdb" "graph" {
  name              = "ls-cosmosdb-graph"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = azurerm_cosmosdb_account.main.primary_sql_connection_string
  database          = azurerm_cosmosdb_gremlin_database.main.name
}

# ==============================================================================
# Blob Storage (Source Documents)
# ==============================================================================

resource "azurerm_storage_account" "documents" {
  name                     = "stdocs${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = true

    container_delete_retention_policy {
      days = 7
    }

    delete_retention_policy {
      days = 7
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "raw_documents" {
  name                  = "raw-documents"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed_documents" {
  name                  = "processed-documents"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "ontologies" {
  name                  = "ontologies"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
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

    key_permissions = [
      "Get",
      "List",
      "Create",
    ]
  }

  tags = local.tags
}

resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-primary-key"
  value        = azurerm_cosmosdb_account.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "search_key" {
  name         = "search-admin-key"
  value        = azurerm_search_service.main.primary_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_key" {
  name         = "redis-access-key"
  value        = azurerm_redis_cache.main.primary_access_key
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
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ==============================================================================
# Redis Cache (Graph Query Caching)
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
  description = "The name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint for entity extraction and relationship inference"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "cosmos_gremlin_endpoint" {
  description = "Cosmos DB Gremlin API endpoint for knowledge graph operations"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "search_endpoint" {
  description = "Azure AI Search endpoint for document and entity indexing"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "function_app_url" {
  description = "Function App URL for graph processing and RAG orchestration"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}
