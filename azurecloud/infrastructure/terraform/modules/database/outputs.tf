# Database Module Outputs

output "cosmosdb_account_id" {
  description = "ID of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.id
}

output "cosmosdb_account_name" {
  description = "Name of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_endpoint" {
  description = "Endpoint of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_primary_key" {
  description = "Primary key of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "cosmosdb_connection_string" {
  description = "Primary connection string"
  value       = azurerm_cosmosdb_account.main.primary_sql_connection_string
  sensitive   = true
}

output "cosmosdb_database_name" {
  description = "Name of the Cosmos DB database"
  value       = azurerm_cosmosdb_sql_database.copilot.name
}

output "cosmosdb_containers" {
  description = "Map of container names"
  value = {
    conversations      = azurerm_cosmosdb_sql_container.conversations.name
    documents_metadata = azurerm_cosmosdb_sql_container.documents_metadata.name
    user_sessions      = azurerm_cosmosdb_sql_container.user_sessions.name
    embeddings_cache   = azurerm_cosmosdb_sql_container.embeddings_cache.name
    audit_logs         = azurerm_cosmosdb_sql_container.audit_logs.name
  }
}
