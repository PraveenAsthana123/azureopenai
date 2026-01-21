#===============================================================================
# WebLLM Platform - Terraform Outputs
#===============================================================================

output "resource_group_name" {
  description = "Name of the primary resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the primary resource group"
  value       = azurerm_resource_group.main.location
}

output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = module.compute.aks_cluster_name
}

output "aks_cluster_fqdn" {
  description = "FQDN of the AKS cluster"
  value       = module.compute.aks_fqdn
}

output "acr_login_server" {
  description = "Login server for the Azure Container Registry"
  value       = module.compute.acr_login_server
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = module.ai_services.openai_endpoint
  sensitive   = true
}

output "search_endpoint" {
  description = "Azure AI Search endpoint"
  value       = module.ai_services.search_endpoint
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint"
  value       = module.data.cosmos_endpoint
  sensitive   = true
}

output "cosmos_database_name" {
  description = "Cosmos DB database name"
  value       = module.data.cosmos_database_name
}

output "redis_hostname" {
  description = "Redis cache hostname"
  value       = module.data.redis_hostname
  sensitive   = true
}

output "storage_account_name" {
  description = "ADLS Gen2 storage account name"
  value       = module.data.storage_account_name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = module.security.key_vault_uri
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = module.monitoring.log_analytics_workspace_id
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.monitoring.application_insights_connection_string
  sensitive   = true
}

output "mlc_llm_namespace" {
  description = "Kubernetes namespace for MLC LLM"
  value       = module.mlc_llm.mlc_llm_namespace
}

output "mlc_llm_services" {
  description = "MLC LLM service names"
  value       = module.mlc_llm.mlc_llm_services
}

#-------------------------------------------------------------------------------
# Connection Information
#-------------------------------------------------------------------------------
output "connection_info" {
  description = "Connection information for all services"
  value = {
    aks = {
      cluster_name = module.compute.aks_cluster_name
      get_credentials = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.compute.aks_cluster_name}"
    }
    acr = {
      login_server = module.compute.acr_login_server
      login_command = "az acr login --name ${split(".", module.compute.acr_login_server)[0]}"
    }
  }
}
