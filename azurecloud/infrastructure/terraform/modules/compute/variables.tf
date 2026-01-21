# Compute Module Variables

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_suffix" {
  description = "Unique suffix for resources"
  type        = string
}

variable "vm_subnet_id" {
  description = "ID of the VM subnet"
  type        = string
}

variable "functions_subnet_id" {
  description = "ID of the Functions subnet"
  type        = string
}

variable "storage_account_name" {
  description = "Name of the storage account for functions"
  type        = string
}

variable "storage_account_access_key" {
  description = "Access key for the storage account"
  type        = string
  sensitive   = true
}

variable "key_vault_id" {
  description = "ID of the Key Vault"
  type        = string
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

variable "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
}

variable "vm_admin_username" {
  description = "Admin username for VMs"
  type        = string
}

variable "vm_admin_password" {
  description = "Admin password for VMs"
  type        = string
  sensitive   = true
}

variable "vm_size" {
  description = "Size of the VMs"
  type        = string
}

variable "vm_count" {
  description = "Number of VMs to create"
  type        = number
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
}

variable "deploy_functions" {
  description = "Whether to deploy Azure Functions (requires VM quota)"
  type        = bool
  default     = false
}
