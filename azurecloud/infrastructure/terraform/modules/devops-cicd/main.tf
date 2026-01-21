#===============================================================================
# Azure DevOps CI/CD Infrastructure Terraform Module
# Creates DevOps organization resources and CI/CD pipelines
#===============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azuredevops = {
      source  = "microsoft/azuredevops"
      version = "~> 1.0"
    }
  }
}

#-------------------------------------------------------------------------------
# Variables
#-------------------------------------------------------------------------------
variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "devops_org_name" {
  description = "Azure DevOps organization name"
  type        = string
}

variable "github_repo_url" {
  description = "GitHub repository URL (optional, for GitHub integration)"
  type        = string
  default     = null
}

variable "enable_self_hosted_agents" {
  description = "Enable self-hosted agent pool"
  type        = bool
  default     = false
}

variable "agent_vm_size" {
  description = "VM size for self-hosted agents"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "agent_count" {
  description = "Number of self-hosted agents"
  type        = number
  default     = 2
}

#-------------------------------------------------------------------------------
# Local Variables
#-------------------------------------------------------------------------------
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  default_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Module      = "devops-cicd"
  }

  tags = merge(local.default_tags, var.tags)
}

#-------------------------------------------------------------------------------
# Data Sources
#-------------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

data "azurerm_subscription" "current" {}

#-------------------------------------------------------------------------------
# Azure DevOps Project
#-------------------------------------------------------------------------------
resource "azuredevops_project" "main" {
  name               = var.project_name
  description        = "Azure AI/ML Platform - ${var.project_name}"
  visibility         = "private"
  version_control    = "Git"
  work_item_template = "Agile"

  features = {
    "boards"       = "enabled"
    "repositories" = "enabled"
    "pipelines"    = "enabled"
    "testplans"    = "disabled"
    "artifacts"    = "enabled"
  }
}

#-------------------------------------------------------------------------------
# Git Repository
#-------------------------------------------------------------------------------
resource "azuredevops_git_repository" "main" {
  project_id = azuredevops_project.main.id
  name       = "${var.project_name}-repo"

  initialization {
    init_type = "Clean"
  }
}

#-------------------------------------------------------------------------------
# Variable Groups
#-------------------------------------------------------------------------------
resource "azuredevops_variable_group" "azure_credentials" {
  project_id   = azuredevops_project.main.id
  name         = "Azure-Credentials-${var.environment}"
  description  = "Azure service connection credentials"
  allow_access = true

  variable {
    name  = "AZURE_SUBSCRIPTION_ID"
    value = data.azurerm_client_config.current.subscription_id
  }

  variable {
    name  = "AZURE_TENANT_ID"
    value = data.azurerm_client_config.current.tenant_id
  }

  variable {
    name  = "AZURE_RESOURCE_GROUP"
    value = var.resource_group_name
  }

  variable {
    name  = "ENVIRONMENT"
    value = var.environment
  }

  variable {
    name  = "LOCATION"
    value = var.location
  }
}

resource "azuredevops_variable_group" "app_settings" {
  project_id   = azuredevops_project.main.id
  name         = "App-Settings-${var.environment}"
  description  = "Application configuration"
  allow_access = true

  variable {
    name  = "PROJECT_NAME"
    value = var.project_name
  }

  variable {
    name  = "PYTHON_VERSION"
    value = "3.11"
  }

  variable {
    name  = "TERRAFORM_VERSION"
    value = "1.6.0"
  }
}

#-------------------------------------------------------------------------------
# Service Connection to Azure
#-------------------------------------------------------------------------------
resource "azuredevops_serviceendpoint_azurerm" "azure" {
  project_id            = azuredevops_project.main.id
  service_endpoint_name = "Azure-${var.environment}"
  description           = "Azure Resource Manager connection for ${var.environment}"

  azurerm_spn_tenantid      = data.azurerm_client_config.current.tenant_id
  azurerm_subscription_id   = data.azurerm_client_config.current.subscription_id
  azurerm_subscription_name = data.azurerm_subscription.current.display_name
}

#-------------------------------------------------------------------------------
# Build Pipeline (CI)
#-------------------------------------------------------------------------------
resource "azuredevops_build_definition" "ci" {
  project_id = azuredevops_project.main.id
  name       = "${var.project_name}-CI"
  path       = "\\CI"

  ci_trigger {
    use_yaml = true
  }

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.main.id
    branch_name = "refs/heads/main"
    yml_path    = "azure-pipelines-ci.yml"
  }

  variable_groups = [
    azuredevops_variable_group.azure_credentials.id,
    azuredevops_variable_group.app_settings.id
  ]
}

#-------------------------------------------------------------------------------
# Release Pipeline Definition (CD) - YAML
#-------------------------------------------------------------------------------
resource "azuredevops_build_definition" "cd" {
  project_id = azuredevops_project.main.id
  name       = "${var.project_name}-CD"
  path       = "\\CD"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.main.id
    branch_name = "refs/heads/main"
    yml_path    = "azure-pipelines-cd.yml"
  }

  variable_groups = [
    azuredevops_variable_group.azure_credentials.id,
    azuredevops_variable_group.app_settings.id
  ]
}

#-------------------------------------------------------------------------------
# Infrastructure Pipeline (Terraform)
#-------------------------------------------------------------------------------
resource "azuredevops_build_definition" "infra" {
  project_id = azuredevops_project.main.id
  name       = "${var.project_name}-Infrastructure"
  path       = "\\Infrastructure"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.main.id
    branch_name = "refs/heads/main"
    yml_path    = "azure-pipelines-infra.yml"
  }

  variable_groups = [
    azuredevops_variable_group.azure_credentials.id,
    azuredevops_variable_group.app_settings.id
  ]
}

#-------------------------------------------------------------------------------
# Self-Hosted Agent Pool (Optional)
#-------------------------------------------------------------------------------
resource "azuredevops_agent_pool" "self_hosted" {
  count = var.enable_self_hosted_agents ? 1 : 0

  name           = "${var.project_name}-agents"
  auto_provision = false
  auto_update    = true
}

resource "azuredevops_agent_queue" "self_hosted" {
  count = var.enable_self_hosted_agents ? 1 : 0

  project_id    = azuredevops_project.main.id
  agent_pool_id = azuredevops_agent_pool.self_hosted[0].id
}

#-------------------------------------------------------------------------------
# Self-Hosted Agent VMs (Optional)
#-------------------------------------------------------------------------------
resource "azurerm_virtual_machine_scale_set" "agents" {
  count = var.enable_self_hosted_agents ? 1 : 0

  name                = "${local.name_prefix}-agent-vmss"
  resource_group_name = var.resource_group_name
  location            = var.location

  sku {
    name     = var.agent_vm_size
    tier     = "Standard"
    capacity = var.agent_count
  }

  upgrade_policy_mode = "Manual"

  os_profile {
    computer_name_prefix = "agent"
    admin_username       = "azuredevops"
    admin_password       = "P@ssw0rd1234!" # Should use Key Vault in production
  }

  os_profile_linux_config {
    disable_password_authentication = false
  }

  storage_profile_os_disk {
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Premium_LRS"
  }

  storage_profile_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  network_profile {
    name    = "agentnetworkprofile"
    primary = true

    ip_configuration {
      name      = "agentipconfig"
      primary   = true
      subnet_id = var.enable_self_hosted_agents ? null : null # Add subnet_id if needed
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Azure Container Registry for Build Artifacts
#-------------------------------------------------------------------------------
resource "azurerm_container_registry" "devops" {
  name                = replace("${local.name_prefix}devopsacr", "-", "")
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Key Vault for Pipeline Secrets
#-------------------------------------------------------------------------------
resource "azurerm_key_vault" "devops" {
  name                       = "${local.name_prefix}-devops-kv"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  enable_rbac_authorization = true

  tags = local.tags
}

#-------------------------------------------------------------------------------
# Storage Account for Terraform State
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "tfstate" {
  name                     = replace("${local.name_prefix}tfstate", "-", "")
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = true
  }

  tags = local.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.tfstate.name
  container_access_type = "private"
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "devops_project_id" {
  description = "Azure DevOps Project ID"
  value       = azuredevops_project.main.id
}

output "devops_project_name" {
  description = "Azure DevOps Project name"
  value       = azuredevops_project.main.name
}

output "repository_url" {
  description = "Git repository URL"
  value       = azuredevops_git_repository.main.remote_url
}

output "ci_pipeline_id" {
  description = "CI Pipeline ID"
  value       = azuredevops_build_definition.ci.id
}

output "cd_pipeline_id" {
  description = "CD Pipeline ID"
  value       = azuredevops_build_definition.cd.id
}

output "infra_pipeline_id" {
  description = "Infrastructure Pipeline ID"
  value       = azuredevops_build_definition.infra.id
}

output "container_registry_login_server" {
  description = "Container Registry login server"
  value       = azurerm_container_registry.devops.login_server
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.devops.vault_uri
}

output "tfstate_storage_account" {
  description = "Terraform state storage account name"
  value       = azurerm_storage_account.tfstate.name
}

output "tfstate_container" {
  description = "Terraform state container name"
  value       = azurerm_storage_container.tfstate.name
}
