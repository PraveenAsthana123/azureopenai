# =============================================================================
# Compute Module - Outputs
# =============================================================================

output "aks_cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.main.id
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_kubelet_identity_object_id" {
  description = "AKS kubelet managed identity object ID"
  value       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

output "aks_oidc_issuer_url" {
  description = "AKS OIDC issuer URL for workload identity"
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "aks_kube_config" {
  description = "AKS kubeconfig"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

output "functions_app_id" {
  description = "Azure Functions app ID"
  value       = azurerm_linux_function_app.main.id
}

output "functions_app_name" {
  description = "Azure Functions app name"
  value       = azurerm_linux_function_app.main.name
}

output "functions_identity_principal_id" {
  description = "Azure Functions managed identity principal ID"
  value       = azurerm_linux_function_app.main.identity[0].principal_id
}

output "functions_default_hostname" {
  description = "Azure Functions default hostname"
  value       = azurerm_linux_function_app.main.default_hostname
}

output "acr_id" {
  description = "Container Registry ID"
  value       = var.enable_acr ? azurerm_container_registry.main[0].id : null
}

output "acr_login_server" {
  description = "Container Registry login server"
  value       = var.enable_acr ? azurerm_container_registry.main[0].login_server : null
}
