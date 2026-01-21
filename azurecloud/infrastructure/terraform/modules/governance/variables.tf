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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "cosmos_account_name" {
  description = "Name of the Cosmos DB account"
  type        = string
}

variable "cosmos_database_name" {
  description = "Name of the Cosmos DB database"
  type        = string
}

variable "servicebus_sku" {
  description = "SKU for Service Bus namespace"
  type        = string
  default     = "Standard"
}

variable "governance_alert_email" {
  description = "Email for governance alerts"
  type        = string
}

variable "governance_webhook_url" {
  description = "Webhook URL for governance alerts (e.g., Teams)"
  type        = string
  default     = ""
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for alerts"
  type        = string
}
