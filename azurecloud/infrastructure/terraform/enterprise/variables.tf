#===============================================================================
# Enterprise AI Platform - Variables
# Zero-Trust Architecture Configuration
#===============================================================================

#-------------------------------------------------------------------------------
# General Settings
#-------------------------------------------------------------------------------
variable "prefix" {
  description = "Resource naming prefix"
  type        = string
  default     = "ent-ai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "eastus"
}

variable "location_dr" {
  description = "DR/Secondary Azure region"
  type        = string
  default     = "centralus"
}

#-------------------------------------------------------------------------------
# Network Configuration
#-------------------------------------------------------------------------------
variable "address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.10.0.0/16"]
}

variable "subnets" {
  description = "Subnet address prefixes"
  type        = map(string)
  default = {
    app         = "10.10.1.0/24"
    ai          = "10.10.2.0/24"
    search      = "10.10.3.0/24"
    data        = "10.10.4.0/24"
    compute     = "10.10.5.0/24"
    integration = "10.10.6.0/24"
    firewall    = "10.10.7.0/24"
  }
}

#-------------------------------------------------------------------------------
# Azure OpenAI Configuration
#-------------------------------------------------------------------------------
variable "openai_sku" {
  description = "Azure OpenAI SKU"
  type        = string
  default     = "S0"
}

variable "openai_deployments" {
  description = "OpenAI model deployments"
  type = list(object({
    name           = string
    model_name     = string
    model_version  = string
    scale_type     = string
    capacity       = optional(number, 10)
  }))
  default = [
    {
      name          = "gpt-4o"
      model_name    = "gpt-4o"
      model_version = "2024-05-13"
      scale_type    = "Standard"
      capacity      = 10
    },
    {
      name          = "text-embedding-3-large"
      model_name    = "text-embedding-3-large"
      model_version = "1"
      scale_type    = "Standard"
      capacity      = 50
    }
  ]
}

#-------------------------------------------------------------------------------
# AI Search Configuration
#-------------------------------------------------------------------------------
variable "search_sku" {
  description = "AI Search SKU (basic, standard, standard2, standard3)"
  type        = string
  default     = "standard"
}

variable "search_replica_count" {
  description = "AI Search replica count"
  type        = number
  default     = 2
}

variable "search_partition_count" {
  description = "AI Search partition count"
  type        = number
  default     = 1
}

#-------------------------------------------------------------------------------
# Database Configuration
#-------------------------------------------------------------------------------
variable "cosmos_consistency_level" {
  description = "Cosmos DB consistency level"
  type        = string
  default     = "Session"
}

variable "cosmos_enable_serverless" {
  description = "Enable serverless for Cosmos DB"
  type        = bool
  default     = true
}

variable "sql_admin_login" {
  description = "SQL Server admin login"
  type        = string
  default     = "sqladminuser"
  sensitive   = true
}

variable "sql_admin_password" {
  description = "SQL Server admin password"
  type        = string
  sensitive   = true
}

variable "sql_sku" {
  description = "SQL Database SKU"
  type        = string
  default     = "S2"
}

#-------------------------------------------------------------------------------
# Compute Configuration
#-------------------------------------------------------------------------------
variable "aks_node_count" {
  description = "AKS default node pool count"
  type        = number
  default     = 2
}

variable "aks_node_size" {
  description = "AKS default node pool VM size"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "function_sku" {
  description = "Function App plan SKU"
  type        = string
  default     = "EP1"
}

#-------------------------------------------------------------------------------
# APIM Configuration
#-------------------------------------------------------------------------------
variable "apim_sku" {
  description = "API Management SKU (Developer_1, Basic, Standard, Premium)"
  type        = string
  default     = "Developer_1"
}

variable "apim_publisher_name" {
  description = "APIM publisher name"
  type        = string
  default     = "Enterprise AI"
}

variable "apim_publisher_email" {
  description = "APIM publisher email"
  type        = string
  default     = "ai-admin@corp.com"
}

#-------------------------------------------------------------------------------
# Monitoring Configuration
#-------------------------------------------------------------------------------
variable "log_retention_days" {
  description = "Log Analytics retention in days"
  type        = number
  default     = 30
}

#-------------------------------------------------------------------------------
# Tags
#-------------------------------------------------------------------------------
variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    project     = "enterprise-ai-platform"
    env         = "prod"
    owner       = "ai-arch"
    cost_center = "ai-platform"
    managed_by  = "terraform"
  }
}
