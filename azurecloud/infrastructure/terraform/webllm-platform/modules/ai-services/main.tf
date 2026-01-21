#===============================================================================
# AI Services Module - Azure OpenAI, AI Search
#===============================================================================

terraform {
  required_providers {
    azapi = {
      source = "Azure/azapi"
    }
  }
}

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "subnet_ids" { type = map(string) }
variable "private_dns_zone_ids" { type = map(string) }
variable "openai_deployments" { type = any }
variable "search_sku" { type = string }
variable "managed_identity_ids" { type = map(string) }
variable "log_analytics_workspace_id" { type = string }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# Azure OpenAI
#-------------------------------------------------------------------------------
resource "azurerm_cognitive_account" "openai" {
  name                          = "${var.name_prefix}-aoai"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = "${var.name_prefix}-aoai"
  public_network_access_enabled = false
  local_auth_enabled            = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "openai" {
  name                = "${var.name_prefix}-pe-aoai"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["ai"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-aoai"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "openai-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["openai"]]
  }
}

#-------------------------------------------------------------------------------
# OpenAI Model Deployments
#-------------------------------------------------------------------------------
resource "azapi_resource" "openai_deployments" {
  for_each = { for d in var.openai_deployments : d.name => d }

  type      = "Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview"
  name      = each.value.name
  parent_id = azurerm_cognitive_account.openai.id

  body = jsonencode({
    properties = {
      model = {
        format  = "OpenAI"
        name    = each.value.model_name
        version = each.value.model_version
      }
      raiPolicyName = "Microsoft.Default"
    }
    sku = {
      name     = each.value.scale_type
      capacity = each.value.capacity
    }
  })
}

#-------------------------------------------------------------------------------
# Azure AI Search
#-------------------------------------------------------------------------------
resource "azurerm_search_service" "main" {
  name                          = "${var.name_prefix}-search"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.search_sku
  replica_count                 = 1
  partition_count               = 1
  public_network_access_enabled = false
  local_authentication_enabled  = false
  authentication_failure_mode   = "http403"

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "search" {
  name                = "${var.name_prefix}-pe-search"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["ai"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-search"
    private_connection_resource_id = azurerm_search_service.main.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }

  private_dns_zone_group {
    name                 = "search-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["search"]]
  }
}

#-------------------------------------------------------------------------------
# Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "openai" {
  name                       = "${var.name_prefix}-aoai-diag"
  target_resource_id         = azurerm_cognitive_account.openai.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log { category = "Audit" }
  enabled_log { category = "RequestResponse" }
  enabled_log { category = "Trace" }
  enabled_metric { category = "AllMetrics" }
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_id" {
  value = azurerm_cognitive_account.openai.id
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_id" {
  value = azurerm_search_service.main.id
}
