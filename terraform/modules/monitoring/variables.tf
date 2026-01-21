# =============================================================================
# Monitoring Module - Variables
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

variable "log_analytics_sku" {
  description = "SKU for Log Analytics"
  type        = string
  default     = "PerGB2018"
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 90
}

variable "log_daily_quota_gb" {
  description = "Daily quota for Log Analytics in GB (-1 for unlimited)"
  type        = number
  default     = -1
}

variable "enable_sentinel" {
  description = "Enable Microsoft Sentinel"
  type        = bool
  default     = false
}

variable "enable_container_insights" {
  description = "Enable Container Insights for AKS"
  type        = bool
  default     = true
}

variable "alert_email_addresses" {
  description = "Email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "openai_account_id" {
  description = "Azure OpenAI account ID for alerts"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
