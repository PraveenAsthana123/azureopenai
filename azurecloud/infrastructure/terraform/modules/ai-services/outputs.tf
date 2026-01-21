# AI Services Module Outputs

# Azure OpenAI (conditionally output based on deployment)
output "openai_id" {
  description = "ID of Azure OpenAI service"
  value       = var.deploy_openai ? azurerm_cognitive_account.openai[0].id : ""
}

output "openai_endpoint" {
  description = "Endpoint of Azure OpenAI service"
  value       = var.deploy_openai ? azurerm_cognitive_account.openai[0].endpoint : ""
}

output "openai_primary_access_key" {
  description = "Primary access key for Azure OpenAI"
  value       = var.deploy_openai ? azurerm_cognitive_account.openai[0].primary_access_key : ""
  sensitive   = true
}

output "openai_principal_id" {
  description = "Principal ID of Azure OpenAI managed identity"
  value       = var.deploy_openai ? azurerm_cognitive_account.openai[0].identity[0].principal_id : ""
}

# Azure AI Search
output "search_service_id" {
  description = "ID of Azure AI Search service"
  value       = azurerm_search_service.main.id
}

output "search_service_name" {
  description = "Name of Azure AI Search service"
  value       = azurerm_search_service.main.name
}

output "search_service_primary_key" {
  description = "Primary admin key for Azure AI Search"
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}

output "search_service_query_keys" {
  description = "Query keys for Azure AI Search"
  value       = azurerm_search_service.main.query_keys
  sensitive   = true
}

# Document Intelligence
output "document_intelligence_id" {
  description = "ID of Document Intelligence service"
  value       = azurerm_cognitive_account.document_intelligence.id
}

output "document_intelligence_endpoint" {
  description = "Endpoint of Document Intelligence service"
  value       = azurerm_cognitive_account.document_intelligence.endpoint
}

output "document_intelligence_primary_access_key" {
  description = "Primary access key for Document Intelligence"
  value       = azurerm_cognitive_account.document_intelligence.primary_access_key
  sensitive   = true
}

# Computer Vision
output "computer_vision_id" {
  description = "ID of Computer Vision service"
  value       = azurerm_cognitive_account.computer_vision.id
}

output "computer_vision_endpoint" {
  description = "Endpoint of Computer Vision service"
  value       = azurerm_cognitive_account.computer_vision.endpoint
}

output "computer_vision_primary_access_key" {
  description = "Primary access key for Computer Vision"
  value       = azurerm_cognitive_account.computer_vision.primary_access_key
  sensitive   = true
}

# Speech Service
output "speech_id" {
  description = "ID of Speech service"
  value       = azurerm_cognitive_account.speech.id
}

output "speech_endpoint" {
  description = "Endpoint of Speech service"
  value       = azurerm_cognitive_account.speech.endpoint
}

output "speech_primary_access_key" {
  description = "Primary access key for Speech service"
  value       = azurerm_cognitive_account.speech.primary_access_key
  sensitive   = true
}

# Content Safety (conditionally output based on deployment)
output "content_safety_id" {
  description = "ID of Content Safety service"
  value       = var.deploy_content_safety ? azurerm_cognitive_account.content_safety[0].id : ""
}

output "content_safety_endpoint" {
  description = "Endpoint of Content Safety service"
  value       = var.deploy_content_safety ? azurerm_cognitive_account.content_safety[0].endpoint : ""
}

output "content_safety_primary_access_key" {
  description = "Primary access key for Content Safety"
  value       = var.deploy_content_safety ? azurerm_cognitive_account.content_safety[0].primary_access_key : ""
  sensitive   = true
}
