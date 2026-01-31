# ==============================================================================
# Document Summarization Platform - Terraform Infrastructure
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
    key                  = "doc-summarizer.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    cognitive_account {
      purge_soft_delete_on_destroy = false
    }
  }
}

# ==============================================================================
# Variables
# ==============================================================================

variable "environment" {
  description = "Environment name (dev, stg, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "docsummarizer"
}

variable "openai_model_deployments" {
  description = "OpenAI model deployments"
  type = list(object({
    name       = string
    model_name = string
    version    = string
    capacity   = number
  }))
  default = [
    {
      name       = "gpt-4o"
      model_name = "gpt-4o"
      version    = "2024-08-06"
      capacity   = 30
    },
    {
      name       = "text-embedding-ada-002"
      model_name = "text-embedding-ada-002"
      version    = "2"
      capacity   = 120
    }
  ]
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "Document-Summarizer"
    ManagedBy   = "Terraform"
    CostCenter  = "AI-Platform"
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
# Virtual Network & Subnets
# ==============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.6.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.6.1.0/24"]

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
  address_prefixes     = ["10.6.2.0/24"]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.CognitiveServices"
  ]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-pe"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.6.3.0/24"]
}

# ==============================================================================
# Network Security Groups
# ==============================================================================

resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "AzureFrontDoor.Backend"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

# ==============================================================================
# Key Vault
# ==============================================================================

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  enable_rbac_authorization = true

  network_acls {
    default_action             = "Deny"
    bypass                     = "AzureServices"
    virtual_network_subnet_ids = [azurerm_subnet.data.id]
  }

  tags = local.tags
}

# ==============================================================================
# Storage Account (Documents)
# ==============================================================================

resource "azurerm_storage_account" "documents" {
  name                     = "st${replace(local.resource_prefix, "-", "")}docs"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [azurerm_subnet.data.id]
  }

  tags = local.tags
}

resource "azurerm_storage_container" "documents_inbox" {
  name                  = "documents-inbox"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "documents_processed" {
  name                  = "documents-processed"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "csv_uploads" {
  name                  = "csv-uploads"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

# ==============================================================================
# Azure OpenAI
# ==============================================================================

resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.resource_prefix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_cognitive_deployment" "models" {
  for_each = { for d in var.openai_model_deployments : d.name => d }

  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.version
  }

  scale {
    type     = "Standard"
    capacity = each.value.capacity
  }
}

# ==============================================================================
# Document Intelligence
# ==============================================================================

resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "di-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "di-${local.resource_prefix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure AI Search
# ==============================================================================

resource "azurerm_search_service" "main" {
  name                = "srch-${local.resource_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "prod" ? "standard" : "basic"
  replica_count       = var.environment == "prod" ? 3 : 1
  partition_count     = 1

  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Cosmos DB (Document Summaries)
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

  public_network_access_enabled     = false
  is_virtual_network_filter_enabled = true

  tags = local.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "docsummarizer"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "summaries" {
  name                = "summaries"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/documentId"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "extractions" {
  name                = "extractions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/documentId"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# ==============================================================================
# Redis Cache
# ==============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "redis-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.environment == "prod" ? 1 : 0
  family              = var.environment == "prod" ? "P" : "C"
  sku_name            = var.environment == "prod" ? "Premium" : "Basic"

  minimum_tls_version           = "1.2"
  public_network_access_enabled = false

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = local.tags
}

# ==============================================================================
# Event Grid (Document Upload Trigger)
# ==============================================================================

resource "azurerm_eventgrid_system_topic" "storage" {
  name                   = "evgt-${local.resource_prefix}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  source_arm_resource_id = azurerm_storage_account.documents.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = local.tags
}

# ==============================================================================
# Application Insights & Log Analytics
# ==============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 90

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
# Azure Functions (Document Summarizer)
# ==============================================================================

resource "azurerm_storage_account" "functions" {
  name                     = "st${replace(local.resource_prefix, "-", "")}func"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version = "TLS1_2"

  tags = local.tags
}

resource "azurerm_service_plan" "functions" {
  name                = "asp-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.environment == "prod" ? "EP1" : "Y1"

  tags = local.tags
}

resource "azurerm_linux_function_app" "summarizer" {
  name                       = "func-docsum-${local.resource_prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  virtual_network_subnet_id = azurerm_subnet.app.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                              = var.environment == "prod"
    application_insights_connection_string = azurerm_application_insights.main.connection_string

    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["https://*.azurewebsites.net"]
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AzureWebJobsFeatureFlags"       = "EnableWorkerIndexing"
    "AZURE_OPENAI_ENDPOINT"          = azurerm_cognitive_account.openai.endpoint
    "AZURE_SEARCH_ENDPOINT"          = "https://${azurerm_search_service.main.name}.search.windows.net"
    "COSMOS_ENDPOINT"                = azurerm_cosmosdb_account.main.endpoint
    "DOCUMENT_INTELLIGENCE_ENDPOINT" = azurerm_cognitive_account.document_intelligence.endpoint
    "STORAGE_ACCOUNT_URL"            = azurerm_storage_account.documents.primary_blob_endpoint
    "KEY_VAULT_URL"                  = azurerm_key_vault.main.vault_uri
    "REDIS_HOST"                     = azurerm_redis_cache.main.hostname
  }

  tags = local.tags
}

# ==============================================================================
# RBAC Role Assignments
# ==============================================================================

# Function App -> OpenAI
resource "azurerm_role_assignment" "function_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# Function App -> AI Search
resource "azurerm_role_assignment" "function_search" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# Function App -> Storage
resource "azurerm_role_assignment" "function_storage" {
  scope                = azurerm_storage_account.documents.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# Function App -> Cosmos DB
resource "azurerm_role_assignment" "function_cosmos" {
  scope                = azurerm_cosmosdb_account.main.id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# Function App -> Key Vault
resource "azurerm_role_assignment" "function_keyvault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# Function App -> Document Intelligence
resource "azurerm_role_assignment" "function_docint" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_function_app.summarizer.identity[0].principal_id
}

# ==============================================================================
# Outputs
# ==============================================================================

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.summarizer.default_hostname}"
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "document_intelligence_endpoint" {
  value = azurerm_cognitive_account.document_intelligence.endpoint
}
