# ==============================================================================
# Multi-Modal Content Platform - Terraform Infrastructure
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
    key                  = "multimodal-content.tfstate"
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
  default = "multimodal"
}

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Project     = "MultiModal-Content"
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
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "integration" {
  name                 = "snet-integration"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  delegation {
    name = "func-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# ==============================================================================
# Azure OpenAI (Content Generation)
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

resource "azurerm_cognitive_deployment" "dalle3" {
  name                 = "dall-e-3"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "dall-e-3"
    version = "3.0"
  }

  scale {
    type     = "Standard"
    capacity = 2
  }
}

# ==============================================================================
# Azure AI Vision (Image Analysis)
# ==============================================================================

resource "azurerm_cognitive_account" "vision" {
  name                  = "cv-${local.resource_prefix}"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "ComputerVision"
  sku_name              = "S1"
  custom_subdomain_name = "cv-${local.resource_prefix}"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ==============================================================================
# Azure AI Speech (Audio Analysis & Generation)
# ==============================================================================

resource "azurerm_cognitive_account" "speech" {
  name                  = "speech-${local.resource_prefix}"
  location              = var.location
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
# Azure AI Search (Content Indexing)
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
# Cosmos DB (Content Platform Data)
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
  name                = "content-platform"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "assets" {
  name                = "assets"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/asset_type"
}

resource "azurerm_cosmosdb_sql_container" "workflows" {
  name                = "workflows"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/workflow_id"
}

resource "azurerm_cosmosdb_sql_container" "generated_content" {
  name                = "generated_content"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/content_type"
}

resource "azurerm_cosmosdb_sql_container" "accessibility_tags" {
  name                = "accessibility_tags"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/asset_id"
}

# ==============================================================================
# Azure Functions (Content Processing)
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

resource "azurerm_linux_function_app" "content_processor" {
  name                       = "func-content-${local.resource_prefix}"
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
    "FUNCTIONS_WORKER_RUNTIME"    = "python"
    "AZURE_OPENAI_ENDPOINT"       = azurerm_cognitive_account.openai.endpoint
    "AZURE_VISION_ENDPOINT"       = azurerm_cognitive_account.vision.endpoint
    "AZURE_SPEECH_ENDPOINT"       = azurerm_cognitive_account.speech.endpoint
    "COSMOS_ENDPOINT"             = azurerm_cosmosdb_account.main.endpoint
    "SEARCH_ENDPOINT"             = "https://${azurerm_search_service.main.name}.search.windows.net"
    "MEDIA_STORAGE_ACCOUNT"       = azurerm_storage_account.media.name
    "REDIS_CONNECTION"            = azurerm_redis_cache.main.primary_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }

  tags = local.tags
}

# ==============================================================================
# Blob Storage (Media Assets - Hot Tier)
# ==============================================================================

resource "azurerm_storage_account" "media" {
  name                     = "stmedia${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD", "PUT"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }

    versioning_enabled = true
  }

  tags = local.tags
}

resource "azurerm_storage_container" "images" {
  name                  = "images"
  storage_account_name  = azurerm_storage_account.media.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "videos" {
  name                  = "videos"
  storage_account_name  = azurerm_storage_account.media.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "audio" {
  name                  = "audio"
  storage_account_name  = azurerm_storage_account.media.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "generated" {
  name                  = "generated"
  storage_account_name  = azurerm_storage_account.media.name
  container_access_type = "private"
}

# ==============================================================================
# CDN Profile & Endpoint (Content Delivery)
# ==============================================================================

resource "azurerm_cdn_profile" "main" {
  name                = "cdn-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard_Microsoft"
  tags                = local.tags
}

resource "azurerm_cdn_endpoint" "media" {
  name                = "cdn-media-${local.resource_prefix}"
  profile_name        = azurerm_cdn_profile.main.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  origin {
    name      = "media-storage"
    host_name = azurerm_storage_account.media.primary_blob_host
  }

  origin_host_header = azurerm_storage_account.media.primary_blob_host

  delivery_rule {
    name  = "CacheImages"
    order = 1

    url_path_condition {
      operator     = "BeginsWith"
      match_values = ["/images/"]
    }

    cache_expiration_action {
      behavior = "Override"
      duration = "7.00:00:00"
    }
  }

  delivery_rule {
    name  = "CacheVideos"
    order = 2

    url_path_condition {
      operator     = "BeginsWith"
      match_values = ["/videos/"]
    }

    cache_expiration_action {
      behavior = "Override"
      duration = "30.00:00:00"
    }
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

# ==============================================================================
# Application Insights
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
# Redis Cache (Content Caching)
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
# Media Services (Video Processing)
# ==============================================================================

resource "azurerm_storage_account" "media_services" {
  name                     = "stms${replace(local.resource_prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags
}

resource "azurerm_media_services_account" "main" {
  name                = "ms${replace(local.resource_prefix, "-", "")}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  storage_account {
    id         = azurerm_storage_account.media_services.id
    is_primary = true
  }

  identity {
    type = "SystemAssigned"
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

output "vision_endpoint" {
  value = azurerm_cognitive_account.vision.endpoint
}

output "speech_endpoint" {
  value = azurerm_cognitive_account.speech.endpoint
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.content_processor.default_hostname}"
}

output "cdn_endpoint" {
  value = "https://${azurerm_cdn_endpoint.media.fqdn}"
}
