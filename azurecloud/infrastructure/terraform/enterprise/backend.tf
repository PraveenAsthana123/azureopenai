#===============================================================================
# Enterprise AI Platform - Terraform Backend
# Local State for Initial Deployment
#===============================================================================

# Using local backend for initial deployment
# To use remote state, create the storage account first and uncomment:
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "terraform-state-rg"
#     storage_account_name = "tfstateenterprise"
#     container_name       = "tfstate"
#     key                  = "enterprise.terraform.tfstate"
#     use_azuread_auth     = true
#   }
# }
