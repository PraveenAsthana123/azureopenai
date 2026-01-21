# =============================================================================
# AI Services Module - Variables
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
# Azure OpenAI Configuration
# -----------------------------------------------------------------------------

variable "openai_sku" {
  description = "SKU for Azure OpenAI"
  type        = string
  default     = "S0"
}

variable "openai_custom_subdomain_name" {
  description = "Custom subdomain for Azure OpenAI"
  type        = string
}

variable "openai_deployments" {
  description = "List of model deployments"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    scale_type    = optional(string, "Standard")
    capacity      = optional(number, 10)
  }))
  default = []
}

# -----------------------------------------------------------------------------
# AI Search Configuration
# -----------------------------------------------------------------------------

variable "search_sku" {
  description = "SKU for AI Search"
  type        = string
  default     = "basic"
}

variable "search_replica_count" {
  description = "Number of replicas for AI Search"
  type        = number
  default     = 1
}

variable "search_partition_count" {
  description = "Number of partitions for AI Search"
  type        = number
  default     = 1
}

variable "search_semantic_search_sku" {
  description = "SKU for semantic search"
  type        = string
  default     = "standard"
}

# -----------------------------------------------------------------------------
# Document Intelligence Configuration
# -----------------------------------------------------------------------------

variable "enable_document_intelligence" {
  description = "Enable Document Intelligence"
  type        = bool
  default     = true
}

variable "document_intelligence_sku" {
  description = "SKU for Document Intelligence"
  type        = string
  default     = "S0"
}

# -----------------------------------------------------------------------------
# Network Configuration
# -----------------------------------------------------------------------------

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoints"
  type        = string
}

variable "allowed_subnet_ids" {
  description = "List of subnet IDs allowed to access AI services"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Integration
# -----------------------------------------------------------------------------

variable "key_vault_id" {
  description = "Key Vault ID for storing secrets"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
