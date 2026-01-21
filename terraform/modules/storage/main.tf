# =============================================================================
# Storage Module - Azure OpenAI Enterprise Platform
# =============================================================================
# Data Lake Gen2 for RAG Documents, Embeddings, and Audit Logs
# =============================================================================

# -----------------------------------------------------------------------------
# Storage Account (Data Lake Gen2)
# -----------------------------------------------------------------------------

resource "azurerm_storage_account" "main" {
  name                            = "st${replace(var.name_prefix, "-", "")}"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = var.storage_account_tier
  account_replication_type        = var.storage_account_replication_type
  account_kind                    = "StorageV2"
  is_hns_enabled                  = var.enable_hierarchical_namespace
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false  # Force AAD auth

  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    dynamic "delete_retention_policy" {
      for_each = var.enable_soft_delete ? [1] : []
      content {
        days = var.soft_delete_retention_days
      }
    }

    dynamic "container_delete_retention_policy" {
      for_each = var.enable_soft_delete ? [1] : []
      content {
        days = var.soft_delete_retention_days
      }
    }

    versioning_enabled = var.enable_versioning
  }

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Blob Containers
# -----------------------------------------------------------------------------

resource "azurerm_storage_container" "containers" {
  for_each = toset(var.containers)

  name                  = each.value
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# -----------------------------------------------------------------------------
# Data Lake File Systems (for hierarchical storage)
# -----------------------------------------------------------------------------

resource "azurerm_storage_data_lake_gen2_filesystem" "main" {
  count = var.enable_hierarchical_namespace ? 1 : 0

  name               = "datalake"
  storage_account_id = azurerm_storage_account.main.id

  properties = {
    purpose = "RAG-Documents"
  }
}

# -----------------------------------------------------------------------------
# Private Endpoint
# -----------------------------------------------------------------------------

resource "azurerm_private_endpoint" "blob" {
  name                = "pe-${var.name_prefix}-blob"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-blob"
    private_connection_resource_id = azurerm_storage_account.main.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "dfs" {
  count = var.enable_hierarchical_namespace ? 1 : 0

  name                = "pe-${var.name_prefix}-dfs"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-dfs"
    private_connection_resource_id = azurerm_storage_account.main.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Lifecycle Management Policy
# -----------------------------------------------------------------------------

resource "azurerm_storage_management_policy" "main" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "archive-old-documents"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
        delete_after_days_since_modification_greater_than          = 365
      }
      snapshot {
        delete_after_days_since_creation_greater_than = 90
      }
      version {
        delete_after_days_since_creation = 90
      }
    }
  }

  rule {
    name    = "cleanup-processed"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["processed/"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }

  rule {
    name    = "retain-audit-logs"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["audit-logs/"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 90
        tier_to_archive_after_days_since_modification_greater_than = 365
        # Never delete audit logs
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Diagnostic Settings
# -----------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "storage" {
  name                       = "diag-${var.name_prefix}-storage"
  target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "StorageRead"
  }

  enabled_log {
    category = "StorageWrite"
  }

  enabled_log {
    category = "StorageDelete"
  }

  metric {
    category = "Transaction"
    enabled  = true
  }

  metric {
    category = "Capacity"
    enabled  = true
  }
}

# -----------------------------------------------------------------------------
# Data Protection (Immutable Storage for Compliance)
# -----------------------------------------------------------------------------

resource "azurerm_storage_container" "compliance" {
  name                  = "compliance-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Note: Immutability policies should be configured based on compliance requirements
# This is a placeholder for WORM storage configuration
