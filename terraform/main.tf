# =============================================================================
# Azure OpenAI Enterprise Platform - Main Terraform Configuration
# =============================================================================
# Aligned with: CMMI L3, ISO 42001, NIST AI RMF, Zero-Trust Architecture
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {
    # Configure in environments/<env>/backend.tfvars
    # resource_group_name  = "rg-terraform-state"
    # storage_account_name = "stterraformstate"
    # container_name       = "tfstate"
    # key                  = "azure-openai.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

provider "azuread" {}

# =============================================================================
# Data Sources
# =============================================================================

data "azurerm_client_config" "current" {}

data "azuread_client_config" "current" {}

# =============================================================================
# Resource Group
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location

  tags = local.common_tags
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  common_tags = {
    Project             = var.project_name
    Environment         = var.environment
    ManagedBy           = "Terraform"
    CostCenter          = var.cost_center
    DataClassification  = var.data_classification
    ComplianceFramework = "ISO42001-NIST-CMMI"
    Owner               = var.owner_email
  }

  name_prefix = "${var.project_name}-${var.environment}"
}

# =============================================================================
# Networking Module
# =============================================================================

module "networking" {
  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix

  vnet_address_space    = var.vnet_address_space
  subnet_configurations = var.subnet_configurations

  enable_ddos_protection = var.environment == "prod"
  enable_bastion         = var.enable_bastion

  tags = local.common_tags
}

# =============================================================================
# Security Module (Key Vault, RBAC, Managed Identities)
# =============================================================================

module "security" {
  source = "./modules/security"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix

  tenant_id                  = data.azurerm_client_config.current.tenant_id
  current_user_object_id     = data.azurerm_client_config.current.object_id

  key_vault_sku             = var.environment == "prod" ? "premium" : "standard"
  enable_purge_protection   = var.environment == "prod"
  soft_delete_retention_days = 90

  private_endpoint_subnet_id = module.networking.subnet_ids["private-endpoints"]

  admin_group_object_ids    = var.admin_group_object_ids
  developer_group_object_ids = var.developer_group_object_ids

  tags = local.common_tags
}

# =============================================================================
# Monitoring Module (Log Analytics, App Insights, Alerts)
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix

  log_analytics_sku          = var.environment == "prod" ? "PerGB2018" : "PerGB2018"
  log_retention_days         = var.environment == "prod" ? 365 : 90

  enable_sentinel            = var.environment == "prod"
  enable_container_insights  = true

  alert_email_addresses      = var.alert_email_addresses

  tags = local.common_tags
}

# =============================================================================
# Storage Module (Data Lake, Blob for RAG)
# =============================================================================

module "storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix

  storage_account_tier             = var.environment == "prod" ? "Premium" : "Standard"
  storage_account_replication_type = var.environment == "prod" ? "GRS" : "LRS"

  enable_hierarchical_namespace = true  # Data Lake Gen2
  enable_versioning             = true
  enable_soft_delete            = true
  soft_delete_retention_days    = 30

  private_endpoint_subnet_id = module.networking.subnet_ids["private-endpoints"]

  # RAG document containers
  containers = [
    "documents",
    "embeddings",
    "processed",
    "audit-logs"
  ]

  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id

  tags = local.common_tags
}

# =============================================================================
# AI Services Module (Azure OpenAI, AI Search, Document Intelligence)
# =============================================================================

module "ai_services" {
  source = "./modules/ai-services"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.openai_location  # OpenAI may have limited regions
  name_prefix         = local.name_prefix

  # Azure OpenAI Configuration
  openai_sku                    = "S0"
  openai_custom_subdomain_name  = "${local.name_prefix}-openai"

  openai_deployments = var.openai_deployments

  # AI Search Configuration
  search_sku                    = var.environment == "prod" ? "standard" : "basic"
  search_replica_count          = var.environment == "prod" ? 2 : 1
  search_partition_count        = 1
  search_semantic_search_sku    = "standard"

  # Document Intelligence
  enable_document_intelligence  = true
  document_intelligence_sku     = "S0"

  # Network Configuration
  private_endpoint_subnet_id    = module.networking.subnet_ids["private-endpoints"]
  allowed_subnet_ids            = [module.networking.subnet_ids["aks"], module.networking.subnet_ids["functions"]]

  # Key Vault for API Keys
  key_vault_id                  = module.security.key_vault_id

  # Monitoring
  log_analytics_workspace_id    = module.monitoring.log_analytics_workspace_id

  tags = local.common_tags
}

# =============================================================================
# Compute Module (AKS, Functions, Container Apps)
# =============================================================================

module "compute" {
  source = "./modules/compute"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix

  # AKS Configuration
  aks_kubernetes_version    = var.aks_kubernetes_version
  aks_node_count            = var.environment == "prod" ? 3 : 2
  aks_node_vm_size          = var.environment == "prod" ? "Standard_D4s_v3" : "Standard_D2s_v3"
  aks_subnet_id             = module.networking.subnet_ids["aks"]

  enable_aks_monitoring     = true
  enable_azure_policy       = true
  enable_oms_agent          = true

  # Azure Functions Configuration
  functions_subnet_id       = module.networking.subnet_ids["functions"]
  functions_sku             = var.environment == "prod" ? "EP1" : "Y1"

  # Managed Identities
  key_vault_id              = module.security.key_vault_id
  storage_account_id        = module.storage.storage_account_id

  # Monitoring
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  application_insights_connection_string = module.monitoring.application_insights_connection_string

  # Container Registry
  enable_acr                = true
  acr_sku                   = var.environment == "prod" ? "Premium" : "Standard"

  tags = local.common_tags
}

# =============================================================================
# RBAC Assignments (Zero-Trust)
# =============================================================================

# AKS Managed Identity -> Key Vault Secrets User
resource "azurerm_role_assignment" "aks_keyvault" {
  scope                = module.security.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.compute.aks_kubelet_identity_object_id
}

# AKS Managed Identity -> Storage Blob Data Reader
resource "azurerm_role_assignment" "aks_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = module.compute.aks_kubelet_identity_object_id
}

# Functions Managed Identity -> Key Vault Secrets User
resource "azurerm_role_assignment" "functions_keyvault" {
  scope                = module.security.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.compute.functions_identity_principal_id
}

# Functions Managed Identity -> Storage Blob Data Contributor
resource "azurerm_role_assignment" "functions_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.compute.functions_identity_principal_id
}

# Functions Managed Identity -> Cognitive Services OpenAI User
resource "azurerm_role_assignment" "functions_openai" {
  scope                = module.ai_services.openai_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = module.compute.functions_identity_principal_id
}
