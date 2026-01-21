#===============================================================================
# Enterprise AI Platform - Main Configuration
# Zero-Trust Architecture - Resource Group & Shared Resources
#===============================================================================

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

  # Merge environment into tags
  common_tags = merge(var.tags, {
    environment = var.environment
    created_at  = timestamp()
  })

  # Private DNS zone names
  private_dns_zones = {
    openai   = "privatelink.openai.azure.com"
    search   = "privatelink.search.windows.net"
    blob     = "privatelink.blob.core.windows.net"
    dfs      = "privatelink.dfs.core.windows.net"
    keyvault = "privatelink.vaultcore.azure.net"
    cosmos   = "privatelink.documents.azure.com"
    sql      = "privatelink.database.windows.net"
    acr      = "privatelink.azurecr.io"
  }
}

#-------------------------------------------------------------------------------
# Resource Group
#-------------------------------------------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

#-------------------------------------------------------------------------------
# DR Resource Group (Secondary Region)
#-------------------------------------------------------------------------------
resource "azurerm_resource_group" "rg_dr" {
  name     = "${local.name_prefix}-dr-rg"
  location = var.location_dr
  tags     = local.common_tags
}
