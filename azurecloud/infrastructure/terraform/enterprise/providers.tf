#===============================================================================
# Enterprise AI Platform - Terraform Providers
# Zero-Trust Architecture Configuration
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
  }
}

provider "azurerm" {
  subscription_id = "8f5bfeb0-c109-428c-98b7-7a9cb5ba6282"
  use_cli         = true
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    cognitive_account {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

provider "azapi" {}

provider "azuread" {}
