# Variables for Enterprise GenAI Knowledge Copilot Platform

# General Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "genai-copilot"
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

variable "location_short" {
  description = "Short form of Azure region"
  type        = string
  default     = "eus2"
}

variable "owner_email" {
  description = "Email of the project owner"
  type        = string
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "AI-Platform"
}

# Networking Variables
variable "vnet_address_space" {
  description = "Address space for VNet"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

# VM Variables
variable "vm_admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "azureadmin"
}

variable "vm_admin_password" {
  description = "Admin password for VMs"
  type        = string
  sensitive   = true
}

variable "vm_size" {
  description = "Size of the VMs"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "vm_count" {
  description = "Number of VMs to create"
  type        = number
  default     = 2
}

# Azure OpenAI Model Deployments
variable "openai_model_deployments" {
  description = "List of OpenAI model deployments"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    capacity      = number
  }))
  default = [
    {
      name          = "gpt-4o-mini"
      model_name    = "gpt-4o-mini"
      model_version = "2024-07-18"
      capacity      = 10
    },
    {
      name          = "text-embedding-3-small"
      model_name    = "text-embedding-3-small"
      model_version = "1"
      capacity      = 10
    }
  ]
}

# Feature Flags
variable "enable_private_endpoints" {
  description = "Enable private endpoints for all services"
  type        = bool
  default     = true
}

variable "enable_diagnostic_settings" {
  description = "Enable diagnostic settings for monitoring"
  type        = bool
  default     = true
}

# Deployment Feature Flags
variable "deploy_openai" {
  description = "Whether to deploy Azure OpenAI resources (depends on regional availability)"
  type        = bool
  default     = true
}

variable "deploy_functions" {
  description = "Whether to deploy Azure Functions (depends on regional quota)"
  type        = bool
  default     = true
}

variable "deploy_content_safety" {
  description = "Whether to deploy Content Safety service (requires special quota)"
  type        = bool
  default     = false
}
