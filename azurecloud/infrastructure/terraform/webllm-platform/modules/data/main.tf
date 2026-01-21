#===============================================================================
# Data Module - ADLS Gen2, Cosmos DB, Redis Cache, Service Bus
#===============================================================================

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "subnet_ids" { type = map(string) }
variable "private_dns_zone_ids" { type = map(string) }
variable "managed_identity_ids" { type = map(string) }
variable "cosmos_config" { type = any }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# ADLS Gen2 Storage Account
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "adls" {
  name                            = replace("${var.name_prefix}adls", "-", "")
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  public_network_access_enabled   = false
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true
    delete_retention_policy { days = 30 }
    container_delete_retention_policy { days = 30 }
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [var.subnet_ids["data"]]
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Storage Containers
#-------------------------------------------------------------------------------
resource "azurerm_storage_container" "containers" {
  for_each = toset(["raw", "processed", "embeddings", "models", "cache"])

  name                  = each.value
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

#-------------------------------------------------------------------------------
# Storage Private Endpoints
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "blob" {
  name                = "${var.name_prefix}-pe-blob"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["data"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-blob"
    private_connection_resource_id = azurerm_storage_account.adls.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "blob-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["blob"]]
  }
}

#-------------------------------------------------------------------------------
# Cosmos DB
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_account" "main" {
  name                          = "${var.name_prefix}-cosmos"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false
  ip_range_filter               = []
  is_virtual_network_filter_enabled = true

  consistency_policy {
    consistency_level = var.cosmos_config.consistency_level
  }

  dynamic "capabilities" {
    for_each = var.cosmos_config.enable_serverless ? [1] : []
    content {
      name = "EnableServerless"
    }
  }

  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }

  virtual_network_rule {
    id = var.subnet_ids["data"]
  }

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Cosmos DB Databases & Containers
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "webllm-platform"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = "sessions"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/sessionId"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path { path = "/*" }
  }
  default_ttl = 86400
}

resource "azurerm_cosmosdb_sql_container" "agent_states" {
  name                = "agent-states"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/agentId"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path { path = "/*" }
  }
}

resource "azurerm_cosmosdb_sql_container" "agent_memory" {
  name                = "agent-memory"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/agentId"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path { path = "/*" }
  }
}

resource "azurerm_cosmosdb_sql_container" "task_history" {
  name                = "task-history"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/taskId"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path { path = "/*" }
  }
  default_ttl = 604800
}

#-------------------------------------------------------------------------------
# Cosmos DB Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "cosmos" {
  name                = "${var.name_prefix}-pe-cosmos"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["data"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-cosmos"
    private_connection_resource_id = azurerm_cosmosdb_account.main.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["cosmos"]]
  }
}

#-------------------------------------------------------------------------------
# Redis Cache (for KV cache and response caching)
#-------------------------------------------------------------------------------
resource "azurerm_redis_cache" "main" {
  name                          = "${var.name_prefix}-redis"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  capacity                      = 1
  family                        = "C"
  sku_name                      = "Standard"
  public_network_access_enabled = false
  minimum_tls_version           = "1.2"

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "redis" {
  name                = "${var.name_prefix}-pe-redis"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["data"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-redis"
    private_connection_resource_id = azurerm_redis_cache.main.id
    is_manual_connection           = false
    subresource_names              = ["redisCache"]
  }

  private_dns_zone_group {
    name                 = "redis-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["redis"]]
  }
}

#-------------------------------------------------------------------------------
# Service Bus (Agent-to-Agent Communication)
#-------------------------------------------------------------------------------
resource "azurerm_servicebus_namespace" "main" {
  name                          = "${var.name_prefix}-sb"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  sku                           = "Standard"
  public_network_access_enabled = false

  tags = var.tags
}

resource "azurerm_servicebus_topic" "agent_requests" {
  name                = "agent-requests"
  namespace_id        = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

resource "azurerm_servicebus_topic" "agent_responses" {
  name                = "agent-responses"
  namespace_id        = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

resource "azurerm_servicebus_topic" "agent_broadcast" {
  name                = "agent-broadcast"
  namespace_id        = azurerm_servicebus_namespace.main.id
  max_size_in_megabytes = 1024
}

resource "azurerm_private_endpoint" "servicebus" {
  name                = "${var.name_prefix}-pe-sb"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["integration"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-sb"
    private_connection_resource_id = azurerm_servicebus_namespace.main.id
    is_manual_connection           = false
    subresource_names              = ["namespace"]
  }

  private_dns_zone_group {
    name                 = "servicebus-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["servicebus"]]
  }
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "storage_account_name" {
  value = azurerm_storage_account.adls.name
}

output "storage_account_endpoint" {
  value = azurerm_storage_account.adls.primary_dfs_endpoint
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "cosmos_database_name" {
  value = azurerm_cosmosdb_sql_database.main.name
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "servicebus_namespace" {
  value = azurerm_servicebus_namespace.main.name
}
