#===============================================================================
# Enterprise AI Platform - Outputs
# Zero-Trust Architecture
#===============================================================================

#-------------------------------------------------------------------------------
# Resource Group Outputs
#-------------------------------------------------------------------------------
output "resource_group_name" {
  description = "Primary resource group name"
  value       = azurerm_resource_group.rg.name
}

output "resource_group_id" {
  description = "Primary resource group ID"
  value       = azurerm_resource_group.rg.id
}

output "resource_group_dr_name" {
  description = "DR resource group name"
  value       = azurerm_resource_group.rg_dr.name
}

#-------------------------------------------------------------------------------
# Network Outputs
#-------------------------------------------------------------------------------
output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.vnet.id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = azurerm_virtual_network.vnet.name
}

output "subnet_ids" {
  description = "Map of subnet IDs"
  value       = { for k, v in azurerm_subnet.subnets : k => v.id }
}

#-------------------------------------------------------------------------------
# Security Outputs
#-------------------------------------------------------------------------------
output "key_vault_id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.kv.id
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.kv.vault_uri
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.kv.name
}

output "managed_identity_fn_id" {
  description = "Function App Managed Identity ID"
  value       = azurerm_user_assigned_identity.fn_mi.id
}

output "managed_identity_fn_client_id" {
  description = "Function App Managed Identity Client ID"
  value       = azurerm_user_assigned_identity.fn_mi.client_id
}

output "managed_identity_aks_id" {
  description = "AKS Managed Identity ID"
  value       = azurerm_user_assigned_identity.aks_mi.id
}

#-------------------------------------------------------------------------------
# Data Outputs
#-------------------------------------------------------------------------------
output "adls_account_name" {
  description = "ADLS Storage Account name"
  value       = azurerm_storage_account.adls.name
}

output "adls_primary_dfs_endpoint" {
  description = "ADLS Primary DFS endpoint"
  value       = azurerm_storage_account.adls.primary_dfs_endpoint
}

output "adls_primary_blob_endpoint" {
  description = "ADLS Primary Blob endpoint"
  value       = azurerm_storage_account.adls.primary_blob_endpoint
}

output "cosmos_db_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.cosmos.endpoint
}

output "cosmos_db_name" {
  description = "Cosmos DB account name"
  value       = azurerm_cosmosdb_account.cosmos.name
}

output "cosmos_db_database_name" {
  description = "Cosmos DB database name"
  value       = azurerm_cosmosdb_sql_database.sessions.name
}

output "sql_server_fqdn" {
  description = "SQL Server FQDN"
  value       = azurerm_mssql_server.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "SQL Database name"
  value       = azurerm_mssql_database.metadb.name
}

#-------------------------------------------------------------------------------
# AI Outputs
#-------------------------------------------------------------------------------
output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_id" {
  description = "Azure OpenAI resource ID"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_name" {
  description = "Azure OpenAI account name"
  value       = azurerm_cognitive_account.openai.name
}

output "search_endpoint" {
  description = "AI Search endpoint"
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "search_id" {
  description = "AI Search resource ID"
  value       = azurerm_search_service.search.id
}

output "search_name" {
  description = "AI Search service name"
  value       = azurerm_search_service.search.name
}

#-------------------------------------------------------------------------------
# Compute Outputs
#-------------------------------------------------------------------------------
output "acr_login_server" {
  description = "ACR login server"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_name" {
  description = "ACR name"
  value       = azurerm_container_registry.acr.name
}

output "aks_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "aks_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.aks.id
}

output "aks_oidc_issuer_url" {
  description = "AKS OIDC issuer URL (for workload identity)"
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}

output "aks_private_fqdn" {
  description = "AKS private FQDN"
  value       = azurerm_kubernetes_cluster.aks.private_fqdn
}

#-------------------------------------------------------------------------------
# App Outputs
#-------------------------------------------------------------------------------
output "function_app_name" {
  description = "Function App name"
  value       = azurerm_linux_function_app.orchestrator.name
}

output "function_app_hostname" {
  description = "Function App default hostname"
  value       = azurerm_linux_function_app.orchestrator.default_hostname
}

output "function_app_id" {
  description = "Function App ID"
  value       = azurerm_linux_function_app.orchestrator.id
}

output "apim_gateway_url" {
  description = "APIM Gateway URL"
  value       = azurerm_api_management.apim.gateway_url
}

output "apim_name" {
  description = "APIM name"
  value       = azurerm_api_management.apim.name
}

output "apim_private_ip" {
  description = "APIM private IP addresses"
  value       = azurerm_api_management.apim.private_ip_addresses
}

#-------------------------------------------------------------------------------
# Monitoring Outputs
#-------------------------------------------------------------------------------
output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.law.id
}

output "log_analytics_workspace_name" {
  description = "Log Analytics Workspace name"
  value       = azurerm_log_analytics_workspace.law.name
}

output "application_insights_id" {
  description = "Application Insights ID"
  value       = azurerm_application_insights.appi.id
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.appi.connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.appi.instrumentation_key
  sensitive   = true
}

#-------------------------------------------------------------------------------
# Private DNS Zone Outputs
#-------------------------------------------------------------------------------
output "private_dns_zone_ids" {
  description = "Map of private DNS zone IDs"
  value       = { for k, v in azurerm_private_dns_zone.zones : k => v.id }
}

#-------------------------------------------------------------------------------
# Summary Output
#-------------------------------------------------------------------------------
output "deployment_summary" {
  description = "Deployment summary"
  value = {
    environment     = var.environment
    location        = var.location
    location_dr     = var.location_dr
    resource_prefix = local.name_prefix

    endpoints = {
      openai = azurerm_cognitive_account.openai.endpoint
      search = "https://${azurerm_search_service.search.name}.search.windows.net"
      cosmos = azurerm_cosmosdb_account.cosmos.endpoint
      adls   = azurerm_storage_account.adls.primary_dfs_endpoint
      apim   = azurerm_api_management.apim.gateway_url
    }

    private_endpoints = {
      openai = azurerm_private_endpoint.pe_openai.private_service_connection[0].private_ip_address
      search = azurerm_private_endpoint.pe_search.private_service_connection[0].private_ip_address
      cosmos = azurerm_private_endpoint.pe_cosmos.private_service_connection[0].private_ip_address
      kv     = azurerm_private_endpoint.pe_kv.private_service_connection[0].private_ip_address
    }
  }
}
