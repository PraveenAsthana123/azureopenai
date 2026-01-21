# Outputs for Enterprise GenAI Knowledge Copilot Platform

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

# Networking
output "vnet_id" {
  description = "ID of the Virtual Network"
  value       = module.networking.vnet_id
}

output "vnet_name" {
  description = "Name of the Virtual Network"
  value       = module.networking.vnet_name
}

# Storage
output "storage_account_name" {
  description = "Name of the storage account"
  value       = module.storage.storage_account_name
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = module.storage.storage_account_primary_blob_endpoint
}

# Database
output "cosmosdb_account_name" {
  description = "Name of the Cosmos DB account"
  value       = module.database.cosmosdb_account_name
}

output "cosmosdb_endpoint" {
  description = "Endpoint of the Cosmos DB account"
  value       = module.database.cosmosdb_endpoint
}

# AI Services
output "openai_endpoint" {
  description = "Endpoint of Azure OpenAI service"
  value       = module.ai_services.openai_endpoint
}

output "search_service_name" {
  description = "Name of Azure AI Search service"
  value       = module.ai_services.search_service_name
}

output "document_intelligence_endpoint" {
  description = "Endpoint of Document Intelligence service"
  value       = module.ai_services.document_intelligence_endpoint
}

output "computer_vision_endpoint" {
  description = "Endpoint of Computer Vision service"
  value       = module.ai_services.computer_vision_endpoint
}

# Compute
output "function_app_names" {
  description = "Names of the Function Apps"
  value       = module.compute.function_app_names
}

output "function_app_default_hostnames" {
  description = "Default hostnames of Function Apps"
  value       = module.compute.function_app_default_hostnames
}

output "vm_private_ips" {
  description = "Private IP addresses of VMs"
  value       = module.compute.vm_private_ips
}

# Monitoring
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = module.monitoring.key_vault_name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.monitoring.key_vault_uri
}

output "app_insights_name" {
  description = "Name of Application Insights"
  value       = module.monitoring.app_insights_name
}

output "log_analytics_workspace_id" {
  description = "ID of Log Analytics Workspace"
  value       = module.monitoring.log_analytics_workspace_id
}
