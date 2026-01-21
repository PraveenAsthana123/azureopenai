# =============================================================================
# Azure OpenAI Enterprise Platform - Variables
# =============================================================================

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "Name of the project (used in resource naming)"
  type        = string
  default     = "aoai"

  validation {
    condition     = length(var.project_name) <= 10 && can(regex("^[a-z0-9]+$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric and max 10 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus2"
}

variable "openai_location" {
  description = "Azure region for OpenAI (limited availability)"
  type        = string
  default     = "eastus2"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "AI-Platform"
}

variable "data_classification" {
  description = "Data classification level"
  type        = string
  default     = "Confidential"

  validation {
    condition     = contains(["Public", "Internal", "Confidential", "Restricted"], var.data_classification)
    error_message = "Data classification must be Public, Internal, Confidential, or Restricted."
  }
}

variable "owner_email" {
  description = "Email of the resource owner"
  type        = string
}

# -----------------------------------------------------------------------------
# Networking Configuration
# -----------------------------------------------------------------------------

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_configurations" {
  description = "Subnet configurations"
  type = map(object({
    address_prefixes                      = list(string)
    service_endpoints                     = optional(list(string), [])
    private_endpoint_network_policies     = optional(string, "Enabled")
    private_link_service_network_policies = optional(string, "Enabled")
    delegation                            = optional(object({
      name    = string
      actions = list(string)
    }), null)
  }))
  default = {
    "aks" = {
      address_prefixes  = ["10.0.0.0/22"]
      service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.CognitiveServices"]
    }
    "functions" = {
      address_prefixes  = ["10.0.4.0/24"]
      service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.CognitiveServices"]
      delegation = {
        name    = "Microsoft.Web/serverFarms"
        actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
      }
    }
    "private-endpoints" = {
      address_prefixes                  = ["10.0.5.0/24"]
      private_endpoint_network_policies = "Disabled"
    }
    "bastion" = {
      address_prefixes = ["10.0.6.0/26"]
    }
    "app-gateway" = {
      address_prefixes = ["10.0.7.0/24"]
    }
  }
}

variable "enable_bastion" {
  description = "Enable Azure Bastion for secure VM access"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Security & Identity Configuration
# -----------------------------------------------------------------------------

variable "admin_group_object_ids" {
  description = "Azure AD group object IDs for admin access"
  type        = list(string)
  default     = []
}

variable "developer_group_object_ids" {
  description = "Azure AD group object IDs for developer access"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Monitoring Configuration
# -----------------------------------------------------------------------------

variable "alert_email_addresses" {
  description = "Email addresses for alert notifications"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Azure OpenAI Configuration
# -----------------------------------------------------------------------------

variable "openai_deployments" {
  description = "Azure OpenAI model deployments"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    scale_type    = optional(string, "Standard")
    capacity      = optional(number, 10)
  }))
  default = [
    {
      name          = "gpt-4o"
      model_name    = "gpt-4o"
      model_version = "2024-08-06"
      capacity      = 30
    },
    {
      name          = "gpt-4o-mini"
      model_name    = "gpt-4o-mini"
      model_version = "2024-07-18"
      capacity      = 50
    },
    {
      name          = "text-embedding-3-large"
      model_name    = "text-embedding-3-large"
      model_version = "1"
      capacity      = 50
    }
  ]
}

# -----------------------------------------------------------------------------
# AKS Configuration
# -----------------------------------------------------------------------------

variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.29"
}
