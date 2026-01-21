# =============================================================================
# Storage Module - Outputs
# =============================================================================

output "storage_account_id" {
  description = "Storage account ID"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "storage_account_primary_dfs_endpoint" {
  description = "Primary DFS endpoint (Data Lake)"
  value       = azurerm_storage_account.main.primary_dfs_endpoint
}

output "container_names" {
  description = "List of created container names"
  value       = [for c in azurerm_storage_container.containers : c.name]
}

output "data_lake_filesystem_id" {
  description = "Data Lake filesystem ID"
  value       = var.enable_hierarchical_namespace ? azurerm_storage_data_lake_gen2_filesystem.main[0].id : null
}
