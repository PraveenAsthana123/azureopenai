# =============================================================================
# Azure OpenAI Enterprise Platform - Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "Resource group ID"
  value       = azurerm_resource_group.main.id
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------

output "vnet_id" {
  description = "Virtual network ID"
  value       = module.networking.vnet_id
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value       = module.networking.subnet_ids
}

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

output "key_vault_id" {
  description = "Key Vault ID"
  value       = module.security.key_vault_id
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = module.security.key_vault_uri
}

# -----------------------------------------------------------------------------
# AI Services
# -----------------------------------------------------------------------------

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = module.ai_services.openai_endpoint
}

output "openai_deployment_names" {
  description = "Deployed OpenAI model names"
  value       = module.ai_services.deployment_names
}

output "search_endpoint" {
  description = "AI Search endpoint"
  value       = module.ai_services.search_endpoint
}

# -----------------------------------------------------------------------------
# Compute
# -----------------------------------------------------------------------------

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = module.compute.aks_cluster_name
}

output "aks_oidc_issuer_url" {
  description = "AKS OIDC issuer URL for workload identity"
  value       = module.compute.aks_oidc_issuer_url
}

output "functions_hostname" {
  description = "Azure Functions hostname"
  value       = module.compute.functions_default_hostname
}

output "acr_login_server" {
  description = "Container Registry login server"
  value       = module.compute.acr_login_server
}

# -----------------------------------------------------------------------------
# Storage
# -----------------------------------------------------------------------------

output "storage_account_name" {
  description = "Storage account name"
  value       = module.storage.storage_account_name
}

output "storage_blob_endpoint" {
  description = "Blob storage endpoint"
  value       = module.storage.storage_account_primary_blob_endpoint
}

# -----------------------------------------------------------------------------
# Monitoring
# -----------------------------------------------------------------------------

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = module.monitoring.log_analytics_workspace_id
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.monitoring.application_insights_connection_string
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Connection Information (for applications)
# -----------------------------------------------------------------------------

output "connection_info" {
  description = "Connection information for applications"
  value = {
    openai_endpoint = module.ai_services.openai_endpoint
    search_endpoint = module.ai_services.search_endpoint
    key_vault_uri   = module.security.key_vault_uri
    storage_endpoint = module.storage.storage_account_primary_blob_endpoint
  }
}
