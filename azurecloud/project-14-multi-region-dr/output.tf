output "location" {
  value = data.azurerm_resource_group.rg.location
}

output "storage_account_name" {
  value = azurerm_storage_account.st.name
}

output "search_service_name" {
  value = azurerm_search_service.search.name
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "aoai_name" {
  value = azurerm_cognitive_account.aoai.name
}

output "aoai_endpoint" {
  value = azurerm_cognitive_account.aoai.endpoint
}

output "docint_name" {
  value = azurerm_cognitive_account.docint.name
}

output "docint_endpoint" {
  value = azurerm_cognitive_account.docint.endpoint
}

# Commented out due to 0 quota for App Service Plan
# output "function_app_name" {
#   value = azurerm_linux_function_app.func.name
# }

output "cosmos_account_name" {
  value = azurerm_cosmosdb_account.cosmos.name
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}
