# =============================================================================
# Compute Module - Variables
# =============================================================================

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

# -----------------------------------------------------------------------------
# AKS Configuration
# -----------------------------------------------------------------------------

variable "aks_kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "aks_node_count" {
  description = "Number of nodes in system pool"
  type        = number
  default     = 2
}

variable "aks_node_vm_size" {
  description = "VM size for system nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "aks_workload_node_vm_size" {
  description = "VM size for workload nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "aks_subnet_id" {
  description = "Subnet ID for AKS"
  type        = string
}

variable "enable_aks_monitoring" {
  description = "Enable AKS monitoring"
  type        = bool
  default     = true
}

variable "enable_azure_policy" {
  description = "Enable Azure Policy for AKS"
  type        = bool
  default     = true
}

variable "enable_oms_agent" {
  description = "Enable OMS agent for AKS"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Azure Functions Configuration
# -----------------------------------------------------------------------------

variable "functions_subnet_id" {
  description = "Subnet ID for Azure Functions"
  type        = string
}

variable "functions_sku" {
  description = "SKU for Azure Functions"
  type        = string
  default     = "Y1"
}

# -----------------------------------------------------------------------------
# Container Registry Configuration
# -----------------------------------------------------------------------------

variable "enable_acr" {
  description = "Enable Azure Container Registry"
  type        = bool
  default     = true
}

variable "acr_sku" {
  description = "SKU for ACR"
  type        = string
  default     = "Standard"
}

variable "acr_georeplication_locations" {
  description = "Geo-replication locations for ACR (Premium only)"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Integration
# -----------------------------------------------------------------------------

variable "key_vault_id" {
  description = "Key Vault ID"
  type        = string
}

variable "key_vault_uri" {
  description = "Key Vault URI"
  type        = string
  default     = ""
}

variable "storage_account_id" {
  description = "Storage account ID"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  type        = string
}

variable "application_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
