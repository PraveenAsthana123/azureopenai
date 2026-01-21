# Storage Module Outputs

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_access_key" {
  description = "Primary access key for the storage account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "storage_account_primary_connection_string" {
  description = "Primary connection string"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "functions_storage_account_name" {
  description = "Name of the functions storage account"
  value       = azurerm_storage_account.functions.name
}

output "functions_storage_account_primary_access_key" {
  description = "Primary access key for the functions storage account"
  value       = azurerm_storage_account.functions.primary_access_key
  sensitive   = true
}

output "documents_container_name" {
  description = "Name of the documents container"
  value       = azurerm_storage_container.documents.name
}

output "processed_container_name" {
  description = "Name of the processed container"
  value       = azurerm_storage_container.processed.name
}

output "embeddings_container_name" {
  description = "Name of the embeddings container"
  value       = azurerm_storage_container.embeddings.name
}
