#===============================================================================
# WebLLM + MLC LLM Hybrid AI Platform - Main Configuration
# Three-Tier Architecture: Browser (WebLLM) + On-Premise (MLC LLM) + Cloud (Azure OpenAI)
#===============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.110.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = ">= 1.13.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 2.47.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.12.0"
    }
  }
}

#-------------------------------------------------------------------------------
# Providers
#-------------------------------------------------------------------------------
provider "azurerm" {
  subscription_id = var.subscription_id
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    cognitive_account {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "azapi" {}
provider "azuread" {}

provider "kubernetes" {
  host                   = module.compute.aks_host
  client_certificate     = base64decode(module.compute.aks_client_certificate)
  client_key             = base64decode(module.compute.aks_client_key)
  cluster_ca_certificate = base64decode(module.compute.aks_cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = module.compute.aks_host
    client_certificate     = base64decode(module.compute.aks_client_certificate)
    client_key             = base64decode(module.compute.aks_client_key)
    cluster_ca_certificate = base64decode(module.compute.aks_cluster_ca_certificate)
  }
}

#-------------------------------------------------------------------------------
# Data Sources
#-------------------------------------------------------------------------------
data "azurerm_client_config" "current" {}
data "azurerm_subscription" "current" {}

#-------------------------------------------------------------------------------
# Local Variables
#-------------------------------------------------------------------------------
locals {
  name_prefix = "${var.prefix}-${var.environment}"

  common_tags = {
    project     = "webllm-mlc-platform"
    environment = var.environment
    managed_by  = "terraform"
    created_at  = timestamp()
  }
}

#-------------------------------------------------------------------------------
# Resource Groups
#-------------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_resource_group" "dr" {
  name     = "${local.name_prefix}-dr-rg"
  location = var.location_dr
  tags     = local.common_tags
}

#-------------------------------------------------------------------------------
# Modules
#-------------------------------------------------------------------------------
module "networking" {
  source = "./modules/networking"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  address_space       = var.address_space
  subnets             = var.subnets
  tags                = local.common_tags
}

module "security" {
  source = "./modules/security"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = data.azurerm_client_config.current.object_id
  subnet_ids          = module.networking.subnet_ids
  tags                = local.common_tags
}

module "ai_services" {
  source = "./modules/ai-services"

  name_prefix              = local.name_prefix
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  subnet_ids               = module.networking.subnet_ids
  private_dns_zone_ids     = module.networking.private_dns_zone_ids
  openai_deployments       = var.openai_deployments
  search_sku               = var.search_sku
  managed_identity_ids     = module.security.managed_identity_ids
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  tags                     = local.common_tags
}

module "compute" {
  source = "./modules/compute"

  name_prefix              = local.name_prefix
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  subnet_ids               = module.networking.subnet_ids
  private_dns_zone_ids     = module.networking.private_dns_zone_ids
  managed_identity_ids     = module.security.managed_identity_ids
  aks_config               = var.aks_config
  gpu_node_pools           = var.gpu_node_pools
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  tags                     = local.common_tags
}

module "mlc_llm" {
  source = "./modules/mlc-llm"

  name_prefix              = local.name_prefix
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  aks_cluster_name         = module.compute.aks_cluster_name
  acr_login_server         = module.compute.acr_login_server
  storage_account_name     = module.data.storage_account_name
  mlc_llm_models           = var.mlc_llm_models
  tags                     = local.common_tags

  depends_on = [module.compute]
}

module "data" {
  source = "./modules/data"

  name_prefix              = local.name_prefix
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  subnet_ids               = module.networking.subnet_ids
  private_dns_zone_ids     = module.networking.private_dns_zone_ids
  managed_identity_ids     = module.security.managed_identity_ids
  cosmos_config            = var.cosmos_config
  tags                     = local.common_tags
}

module "monitoring" {
  source = "./modules/monitoring"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  retention_days      = var.log_retention_days
  alert_email         = var.alert_email
  tags                = local.common_tags
}
