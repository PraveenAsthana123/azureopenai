# =============================================================================
# AI Services Module - Outputs
# =============================================================================

output "openai_account_id" {
  description = "Azure OpenAI account ID"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_principal_id" {
  description = "Azure OpenAI managed identity principal ID"
  value       = azurerm_cognitive_account.openai.identity[0].principal_id
}

output "search_service_id" {
  description = "AI Search service ID"
  value       = azurerm_search_service.main.id
}

output "search_service_name" {
  description = "AI Search service name"
  value       = azurerm_search_service.main.name
}

output "search_endpoint" {
  description = "AI Search endpoint"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_principal_id" {
  description = "AI Search managed identity principal ID"
  value       = azurerm_search_service.main.identity[0].principal_id
}

output "document_intelligence_id" {
  description = "Document Intelligence ID"
  value       = var.enable_document_intelligence ? azurerm_cognitive_account.document_intelligence[0].id : null
}

output "document_intelligence_endpoint" {
  description = "Document Intelligence endpoint"
  value       = var.enable_document_intelligence ? azurerm_cognitive_account.document_intelligence[0].endpoint : null
}

output "deployment_names" {
  description = "List of deployed model names"
  value       = [for d in azurerm_cognitive_deployment.models : d.name]
}
