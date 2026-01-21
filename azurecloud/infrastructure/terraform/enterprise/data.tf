#===============================================================================
# Enterprise AI Platform - Data Layer
# Zero-Trust Architecture - ADLS Gen2, Cosmos DB, Azure SQL
#===============================================================================

#-------------------------------------------------------------------------------
# ADLS Gen2 Storage Account
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "adls" {
  name                          = replace("${var.prefix}adls${var.environment}01", "-", "")
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = var.location
  account_tier                  = "Standard"
  account_replication_type      = "GRS"
  account_kind                  = "StorageV2"
  is_hns_enabled                = true
  public_network_access_enabled = false
  min_tls_version               = "TLS1_2"
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
    virtual_network_subnet_ids = [azurerm_subnet.subnets["data"].id]
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Storage Containers
#-------------------------------------------------------------------------------
resource "azurerm_storage_container" "raw" {
  name                  = "raw"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed" {
  name                  = "processed"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "chunks" {
  name                  = "chunks"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "embeddings" {
  name                  = "embeddings"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "ocr" {
  name                  = "ocr"
  storage_account_name  = azurerm_storage_account.adls.name
  container_access_type = "private"
}

#-------------------------------------------------------------------------------
# ADLS Private Endpoints (Blob + DFS)
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_blob" {
  name                = "${local.name_prefix}-pe-blob"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["data"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-blob"
    private_connection_resource_id = azurerm_storage_account.adls.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "blob-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["blob"].id]
  }
}

resource "azurerm_private_endpoint" "pe_dfs" {
  name                = "${local.name_prefix}-pe-dfs"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["data"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-dfs"
    private_connection_resource_id = azurerm_storage_account.adls.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  private_dns_zone_group {
    name                 = "dfs-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["dfs"].id]
  }
}

#-------------------------------------------------------------------------------
# ADLS RBAC Assignments
#-------------------------------------------------------------------------------
resource "azurerm_role_assignment" "adls_fn_contributor" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.fn_mi.principal_id
}

resource "azurerm_role_assignment" "adls_aks_contributor" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_mi.principal_id
}

resource "azurerm_role_assignment" "adls_data_contributor" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.data_mi.principal_id
}

#-------------------------------------------------------------------------------
# Cosmos DB Account (Serverless)
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_account" "cosmos" {
  name                          = "${local.name_prefix}-cosmos"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false
  ip_range_filter               = []
  is_virtual_network_filter_enabled = true

  consistency_policy {
    consistency_level = var.cosmos_consistency_level
  }

  dynamic "capabilities" {
    for_each = var.cosmos_enable_serverless ? [1] : []
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
    id = azurerm_subnet.subnets["data"].id
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Cosmos DB Database & Containers
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_sql_database" "sessions" {
  name                = "sessions"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.sessions.name
  partition_key_paths = ["/sessionId"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path {
      path = "/*"
    }
  }

  default_ttl = 86400 # 24 hours
}

resource "azurerm_cosmosdb_sql_container" "cache" {
  name                = "cache"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.sessions.name
  partition_key_paths = ["/cacheKey"]

  indexing_policy {
    indexing_mode = "consistent"
    included_path {
      path = "/*"
    }
  }

  default_ttl = 3600 # 1 hour
}

#-------------------------------------------------------------------------------
# Cosmos DB Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_cosmos" {
  name                = "${local.name_prefix}-pe-cosmos"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["data"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-cosmos"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmos.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["cosmos"].id]
  }
}

#-------------------------------------------------------------------------------
# Cosmos DB RBAC Assignments
#-------------------------------------------------------------------------------
resource "azurerm_cosmosdb_sql_role_assignment" "fn_contributor" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  role_definition_id  = "${azurerm_cosmosdb_account.cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.fn_mi.principal_id
  scope               = azurerm_cosmosdb_account.cosmos.id
}

#-------------------------------------------------------------------------------
# Azure SQL Server
#-------------------------------------------------------------------------------
resource "azurerm_mssql_server" "sql" {
  name                          = "${local.name_prefix}-sqlsrv"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = var.location
  version                       = "12.0"
  administrator_login           = var.sql_admin_login
  administrator_login_password  = var.sql_admin_password
  public_network_access_enabled = false
  minimum_tls_version           = "1.2"

  azuread_administrator {
    login_username              = "AzureAD Admin"
    object_id                   = data.azurerm_client_config.current.object_id
    azuread_authentication_only = false
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Azure SQL Database (Metadata/Config)
#-------------------------------------------------------------------------------
resource "azurerm_mssql_database" "metadb" {
  name         = "${local.name_prefix}-metadb"
  server_id    = azurerm_mssql_server.sql.id
  collation    = "SQL_Latin1_General_CP1_CI_AS"
  max_size_gb  = 50
  sku_name     = var.sql_sku
  zone_redundant = false

  threat_detection_policy {
    state                = "Enabled"
    email_account_admins = "Enabled"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Azure SQL Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_sql" {
  name                = "${local.name_prefix}-pe-sql"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["data"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-sql"
    private_connection_resource_id = azurerm_mssql_server.sql.id
    is_manual_connection           = false
    subresource_names              = ["sqlServer"]
  }

  private_dns_zone_group {
    name                 = "sql-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["sql"].id]
  }
}
