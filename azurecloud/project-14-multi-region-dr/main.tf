terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.105"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azapi" {}

data "azurerm_client_config" "current" {}

# -----------------------------
# Resource group (existing)
# -----------------------------
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

resource "random_integer" "rand" {
  min = 1000
  max = 9999
}

locals {
  location     = coalesce(var.location, data.azurerm_resource_group.rg.location)
  private_only = var.network_mode == "private"

  private_dns_zones = [
    "privatelink.blob.core.windows.net",
    "privatelink.search.windows.net",
    "privatelink.openai.azure.com",
    "privatelink.cognitiveservices.azure.com",
    "privatelink.documents.azure.com",
    "privatelink.mongo.cosmos.azure.com",
    "privatelink.vaultcore.azure.net"
  ]
}

# -----------------------------
# Networking (optional private)
# -----------------------------
resource "azurerm_virtual_network" "vnet" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-vnet"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  address_space       = ["10.10.0.0/16"]
  tags                = var.tags
}

resource "azurerm_subnet" "private_endpoints" {
  count                = local.private_only ? 1 : 0
  name                 = "snet-private-endpoints"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet[0].name
  address_prefixes     = ["10.10.1.0/24"]

  private_endpoint_network_policies_enabled = false
}

resource "azurerm_subnet" "functions" {
  count                = local.private_only ? 1 : 0
  name                 = "snet-functions"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet[0].name
  address_prefixes     = ["10.10.2.0/24"]

  delegation {
    name = "functions"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_private_dns_zone" "zones" {
  for_each            = local.private_only ? toset(local.private_dns_zones) : toset([])
  name                = each.value
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "links" {
  for_each              = local.private_only ? azurerm_private_dns_zone.zones : {}
  name                  = "${var.prefix}-link-${replace(each.key, ".", "-")}"
  resource_group_name   = data.azurerm_resource_group.rg.name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.vnet[0].id
  tags                  = var.tags
}

# -----------------------------
# Storage (raw pdf, images, chunks)
# -----------------------------
resource "azurerm_storage_account" "st" {
  name                     = lower(replace("${var.prefix}st${random_integer.rand.result}", "-", ""))
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  public_network_access_enabled = true  # Temporarily enabled for container creation
  tags                     = var.tags

  dynamic "network_rules" {
    for_each = local.private_only ? [] : [1]
    content {
      default_action = "Allow"  # Allow during creation
      ip_rules       = var.allowed_ip_ranges
      bypass         = ["AzureServices"]
    }
  }
}

resource "azurerm_storage_container" "pdf_raw" {
  name                  = "pdf-raw"
  storage_account_name  = azurerm_storage_account.st.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "images" {
  name                  = "images"
  storage_account_name  = azurerm_storage_account.st.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "chunks" {
  name                  = "chunks"
  storage_account_name  = azurerm_storage_account.st.name
  container_access_type = "private"
}

resource "azurerm_private_endpoint" "st_blob_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-st-blob-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-st-conn"
    private_connection_resource_id = azurerm_storage_account.st.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "blob-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.blob.core.windows.net"].id]
  }

  tags = var.tags
}

# -----------------------------
# Key Vault (RBAC + Secrets Officer)
# -----------------------------
resource "azurerm_key_vault" "kv" {
  name                       = "${var.prefix}-kv-${random_integer.rand.result}"
  location                   = local.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  public_network_access_enabled = local.private_only ? false : true
  tags                       = var.tags
}

resource "azurerm_role_assignment" "kv_secrets_officer" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_private_endpoint" "kv_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-kv-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-kv-conn"
    private_connection_resource_id = azurerm_key_vault.kv.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "kv-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.vaultcore.azure.net"].id]
  }

  tags = var.tags
}

# -----------------------------
# Azure AI Search (Standard for vectors)
# -----------------------------
resource "azurerm_search_service" "search" {
  name                = "${var.prefix}-search-${random_integer.rand.result}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = local.location
  sku                 = var.search_sku
  replica_count       = 1
  partition_count     = 1
  public_network_access_enabled = local.private_only ? false : true
  tags                = var.tags
}

resource "azurerm_private_endpoint" "search_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-search-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-search-conn"
    private_connection_resource_id = azurerm_search_service.search.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "search-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.search.windows.net"].id]
  }

  tags = var.tags
}

# -----------------------------
# Azure OpenAI account
# -----------------------------
resource "azurerm_cognitive_account" "aoai" {
  name                = "${var.prefix}-aoai-${random_integer.rand.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
  custom_subdomain_name = "${var.prefix}-aoai-${random_integer.rand.result}"
  public_network_access_enabled = local.private_only ? false : true
  tags                = var.tags

  dynamic "network_acls" {
    for_each = local.private_only ? [] : [1]
    content {
      default_action = "Deny"
      ip_rules       = var.allowed_ip_ranges
    }
  }
}

resource "azurerm_private_endpoint" "aoai_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-aoai-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-aoai-conn"
    private_connection_resource_id = azurerm_cognitive_account.aoai.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "aoai-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.openai.azure.com"].id]
  }

  tags = var.tags
}

# -----------------------------
# AOAI Deployments (AzAPI 2.x compatible)
# IMPORTANT: Set versions from your "az rest .../models" output.
# -----------------------------
resource "azapi_resource" "aoai_gpt4o_chat" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = var.gpt4o_chat_deployment_name
  parent_id = azurerm_cognitive_account.aoai.id

  body = {
    sku = {
      name     = "Standard"
      capacity = 10
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.gpt4o_chat_model_name
        version = var.gpt4o_chat_model_version
      }
    }
  }
}

resource "azapi_resource" "aoai_gpt4o_mini_caption" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = var.gpt4o_mini_caption_deployment_name
  parent_id = azurerm_cognitive_account.aoai.id

  body = {
    sku = {
      name     = "Standard"
      capacity = 5
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.gpt4o_mini_model_name
        version = var.gpt4o_mini_model_version
      }
    }
  }
}

resource "azapi_resource" "aoai_embed" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = var.embedding_deployment_name
  parent_id = azurerm_cognitive_account.aoai.id

  body = {
    sku = {
      name     = "Standard"
      capacity = 5
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.embedding_model_name
        version = var.embedding_model_version
      }
    }
  }
}

# -----------------------------
# Document Intelligence
# -----------------------------
resource "azurerm_cognitive_account" "docint" {
  name                = "${var.prefix}-docint-${random_integer.rand.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "FormRecognizer"
  sku_name            = "S0"
  custom_subdomain_name = "${var.prefix}-docint-${random_integer.rand.result}"
  public_network_access_enabled = local.private_only ? false : true
  tags                = var.tags

  dynamic "network_acls" {
    for_each = local.private_only ? [] : [1]
    content {
      default_action = "Deny"
      ip_rules       = var.allowed_ip_ranges
    }
  }
}

resource "azurerm_private_endpoint" "docint_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-docint-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-docint-conn"
    private_connection_resource_id = azurerm_cognitive_account.docint.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "docint-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.cognitiveservices.azure.com"].id]
  }

  tags = var.tags
}

# -----------------------------
# Content Safety (optional but recommended)
# -----------------------------
resource "azurerm_cognitive_account" "safety" {
  name                = "${var.prefix}-safety-${random_integer.rand.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "ContentSafety"
  sku_name            = "S0"
  custom_subdomain_name = "${var.prefix}-safety-${random_integer.rand.result}"
  public_network_access_enabled = local.private_only ? false : true
  tags                = var.tags

  dynamic "network_acls" {
    for_each = local.private_only ? [] : [1]
    content {
      default_action = "Deny"
      ip_rules       = var.allowed_ip_ranges
    }
  }
}

resource "azurerm_private_endpoint" "safety_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-safety-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-safety-conn"
    private_connection_resource_id = azurerm_cognitive_account.safety.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "safety-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.cognitiveservices.azure.com"].id]
  }

  tags = var.tags
}

# -----------------------------
# Cosmos DB (SQL API)
# -----------------------------
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = "${var.prefix}-cosmos-${random_integer.rand.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = local.location
    failover_priority = 0
  }

  public_network_access_enabled = local.private_only ? false : true
  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = "ragdb"
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = "sessions"
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.db.name
  partition_key_path  = "/sessionId"
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "messages" {
  name                = "messages"
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.db.name
  partition_key_path  = "/sessionId"
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "doc_acl" {
  name                = "doc_acl"
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.db.name
  partition_key_path  = "/documentId"
  throughput          = 400
}

resource "azurerm_private_endpoint" "cosmos_pe" {
  count               = local.private_only ? 1 : 0
  name                = "${var.prefix}-cosmos-pe"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "${var.prefix}-cosmos-conn"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmos.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.mongo.cosmos.azure.com"].id]
  }

  tags = var.tags
}

# -----------------------------
# Logging
# -----------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.prefix}-law"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "appi" {
  name                = "${var.prefix}-appi"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.law.id
  tags                = var.tags
}

# -----------------------------
# Azure Function (Consumption by default)
# NOTE: Commented out due to 0 quota for Basic VMs
# Request quota increase from Azure Support if needed
# -----------------------------
# resource "azurerm_service_plan" "plan" {
#   name                = "${var.prefix}-plan"
#   location            = local.location
#   resource_group_name = data.azurerm_resource_group.rg.name
#   os_type             = "Linux"
#   sku_name            = "B1" # Basic tier (Consumption Y1 has quota 0)
#   tags                = var.tags
# }

# Function storage account is already imported
resource "azurerm_storage_account" "funcst" {
  name                     = lower(replace("${var.prefix}funcst${random_integer.rand.result}", "-", ""))
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  public_network_access_enabled = local.private_only ? false : true
  tags                     = var.tags
}

# resource "azurerm_linux_function_app" "func" {
#   name                       = "${var.prefix}-func"
#   location                   = local.location
#   resource_group_name        = data.azurerm_resource_group.rg.name
#   service_plan_id            = azurerm_service_plan.plan.id
#   storage_account_name       = azurerm_storage_account.funcst.name
#   storage_account_access_key = azurerm_storage_account.funcst.primary_access_key
#   https_only                 = true
#   tags                       = var.tags
#
#   site_config {
#     application_stack {
#       python_version = "3.11"
#     }
#
#     app_service_logs {
#       disk_quota_mb         = 35
#       retention_period_days = 7
#     }
#   }
#
#   app_settings = {
#     "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.appi.instrumentation_key
#     "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.appi.connection_string
#
#     "STORAGE_ACCOUNT_NAME" = azurerm_storage_account.st.name
#     "SEARCH_SERVICE_NAME"  = azurerm_search_service.search.name
#     "AOAI_ENDPOINT"        = azurerm_cognitive_account.aoai.endpoint
#     "DOCINT_ENDPOINT"      = azurerm_cognitive_account.docint.endpoint
#     "COSMOS_ACCOUNT"       = azurerm_cosmosdb_account.cosmos.name
#   }
# }
