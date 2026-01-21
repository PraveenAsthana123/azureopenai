# =============================================================================
# Security Module - Outputs
# =============================================================================

output "key_vault_id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "app_identity_id" {
  description = "App managed identity ID"
  value       = azurerm_user_assigned_identity.app.id
}

output "app_identity_principal_id" {
  description = "App managed identity principal ID"
  value       = azurerm_user_assigned_identity.app.principal_id
}

output "app_identity_client_id" {
  description = "App managed identity client ID"
  value       = azurerm_user_assigned_identity.app.client_id
}

output "data_processor_identity_id" {
  description = "Data processor managed identity ID"
  value       = azurerm_user_assigned_identity.data_processor.id
}

output "data_processor_identity_principal_id" {
  description = "Data processor managed identity principal ID"
  value       = azurerm_user_assigned_identity.data_processor.principal_id
}
