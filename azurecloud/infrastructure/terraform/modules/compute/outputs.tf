# Compute Module Outputs

# Function Apps (conditional outputs)
output "function_app_names" {
  description = "Names of the Function Apps"
  value = var.deploy_functions ? {
    api_gateway   = azurerm_windows_function_app.api_gateway[0].name
    orchestrator  = azurerm_windows_function_app.orchestrator[0].name
    ingestion     = azurerm_windows_function_app.ingestion[0].name
    rag_processor = azurerm_windows_function_app.rag_processor[0].name
  } : {}
}

output "function_app_default_hostnames" {
  description = "Default hostnames of Function Apps"
  value = var.deploy_functions ? {
    api_gateway   = azurerm_windows_function_app.api_gateway[0].default_hostname
    orchestrator  = azurerm_windows_function_app.orchestrator[0].default_hostname
    ingestion     = azurerm_windows_function_app.ingestion[0].default_hostname
    rag_processor = azurerm_windows_function_app.rag_processor[0].default_hostname
  } : {}
}

output "function_app_principal_ids" {
  description = "Principal IDs of Function Apps managed identities"
  value = var.deploy_functions ? {
    api_gateway   = azurerm_windows_function_app.api_gateway[0].identity[0].principal_id
    orchestrator  = azurerm_windows_function_app.orchestrator[0].identity[0].principal_id
    ingestion     = azurerm_windows_function_app.ingestion[0].identity[0].principal_id
    rag_processor = azurerm_windows_function_app.rag_processor[0].identity[0].principal_id
  } : {}
}

# VMs
output "vm_ids" {
  description = "IDs of the VMs"
  value       = azurerm_linux_virtual_machine.backend[*].id
}

output "vm_names" {
  description = "Names of the VMs"
  value       = azurerm_linux_virtual_machine.backend[*].name
}

output "vm_private_ips" {
  description = "Private IP addresses of VMs"
  value       = azurerm_network_interface.vm[*].private_ip_address
}

output "vm_principal_ids" {
  description = "Principal IDs of VM managed identities"
  value       = azurerm_linux_virtual_machine.backend[*].identity[0].principal_id
}
