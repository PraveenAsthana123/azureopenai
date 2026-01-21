# AI Services Module Variables

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

variable "subnet_id" {
  description = "ID of the subnet for private endpoints"
  type        = string
}

variable "private_dns_zone_ids" {
  description = "Map of private DNS zone IDs"
  type        = map(string)
}

variable "openai_model_deployments" {
  description = "List of OpenAI model deployments"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    capacity      = number
  }))
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
}

variable "deploy_openai" {
  description = "Whether to deploy Azure OpenAI resources (requires quota approval)"
  type        = bool
  default     = false
}

variable "deploy_content_safety" {
  description = "Whether to deploy Content Safety service (requires quota)"
  type        = bool
  default     = false
}
