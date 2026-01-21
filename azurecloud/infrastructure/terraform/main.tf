# Enterprise GenAI Knowledge Copilot Platform - Main Terraform Configuration
# No Kubernetes, No Docker - VM + Serverless Architecture

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
  }

  backend "azurerm" {
    # Configure in environments/<env>/backend.tfvars
    # resource_group_name  = "tfstate-rg"
    # storage_account_name = "tfstateaccount"
    # container_name       = "tfstate"
    # key                  = "genai-copilot.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  skip_provider_registration = true
}

provider "azuread" {}

# Data sources for current context
data "azurerm_client_config" "current" {}
data "azuread_client_config" "current" {}

# Random suffix for unique naming
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Local variables
locals {
  resource_suffix = random_string.suffix.result
  common_tags = {
    Environment = var.environment
    Project     = "GenAI-Copilot"
    ManagedBy   = "Terraform"
    Owner       = var.owner_email
    CostCenter  = var.cost_center
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${var.location_short}"
  location = var.location
  tags     = local.common_tags
}

# Networking Module
module "networking" {
  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment
  resource_suffix     = local.resource_suffix
  address_space       = var.vnet_address_space
  tags                = local.common_tags
}

# Storage Module
module "storage" {
  source = "./modules/storage"

  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
  project_name          = var.project_name
  environment           = var.environment
  resource_suffix       = local.resource_suffix
  subnet_id             = module.networking.private_endpoints_subnet_id
  private_dns_zone_ids  = module.networking.private_dns_zone_ids
  tags                  = local.common_tags

  depends_on = [module.networking]
}

# Database Module (Cosmos DB)
module "database" {
  source = "./modules/database"

  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
  project_name          = var.project_name
  environment           = var.environment
  resource_suffix       = local.resource_suffix
  subnet_id             = module.networking.private_endpoints_subnet_id
  private_dns_zone_ids  = module.networking.private_dns_zone_ids
  tags                  = local.common_tags

  depends_on = [module.networking]
}

# AI Services Module
module "ai_services" {
  source = "./modules/ai-services"

  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  project_name             = var.project_name
  environment              = var.environment
  resource_suffix          = local.resource_suffix
  subnet_id                = module.networking.private_endpoints_subnet_id
  private_dns_zone_ids     = module.networking.private_dns_zone_ids
  openai_model_deployments = var.openai_model_deployments
  deploy_openai            = var.deploy_openai
  deploy_content_safety    = var.deploy_content_safety
  tags                     = local.common_tags

  depends_on = [module.networking]
}

# Compute Module (VMs + Functions)
module "compute" {
  source = "./modules/compute"

  resource_group_name            = azurerm_resource_group.main.name
  location                       = azurerm_resource_group.main.location
  project_name                   = var.project_name
  environment                    = var.environment
  resource_suffix                = local.resource_suffix
  vm_subnet_id                   = module.networking.vm_subnet_id
  functions_subnet_id            = module.networking.functions_subnet_id
  storage_account_name           = module.storage.storage_account_name
  storage_account_access_key     = module.storage.storage_account_primary_access_key
  key_vault_id                   = module.monitoring.key_vault_id
  app_insights_connection_string = module.monitoring.app_insights_connection_string
  app_insights_instrumentation_key = module.monitoring.app_insights_instrumentation_key
  vm_admin_username              = var.vm_admin_username
  vm_admin_password              = var.vm_admin_password
  vm_size                        = var.vm_size
  vm_count                       = var.vm_count
  deploy_functions               = var.deploy_functions  # Enabled for Southeast Asia (Singapore)
  tags                           = local.common_tags

  depends_on = [module.networking, module.storage, module.monitoring]
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment
  resource_suffix     = local.resource_suffix
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = data.azurerm_client_config.current.object_id
  subnet_id           = module.networking.private_endpoints_subnet_id
  private_dns_zone_ids = module.networking.private_dns_zone_ids
  tags                = local.common_tags

  depends_on = [module.networking]
}
