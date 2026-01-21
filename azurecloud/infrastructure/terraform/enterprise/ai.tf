#===============================================================================
# Enterprise AI Platform - AI Services Layer
# Zero-Trust Architecture - Azure OpenAI, AI Search, Private Endpoints
#===============================================================================

#-------------------------------------------------------------------------------
# Azure OpenAI Cognitive Account
#-------------------------------------------------------------------------------
resource "azurerm_cognitive_account" "openai" {
  name                          = "${local.name_prefix}-aoai"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  kind                          = "OpenAI"
  sku_name                      = var.openai_sku
  custom_subdomain_name         = "${local.name_prefix}-aoai"
  public_network_access_enabled = false
  local_auth_enabled            = false

  network_acls {
    default_action = "Deny"
    ip_rules       = []
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Azure OpenAI Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_openai" {
  name                = "${local.name_prefix}-pe-aoai"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["ai"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-aoai"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "aoai-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["openai"].id]
  }
}

#-------------------------------------------------------------------------------
# Azure OpenAI Model Deployments (using AzAPI)
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

  response_export_values = ["properties.provisioningState"]
}

#-------------------------------------------------------------------------------
# Azure OpenAI RBAC Assignments
#-------------------------------------------------------------------------------
resource "azurerm_role_assignment" "openai_fn_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.fn_mi.principal_id
}

resource "azurerm_role_assignment" "openai_aks_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.aks_mi.principal_id
}

resource "azurerm_role_assignment" "openai_apim_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.apim_mi.principal_id
}

#-------------------------------------------------------------------------------
# Azure AI Search
#-------------------------------------------------------------------------------
resource "azurerm_search_service" "search" {
  name                          = "${local.name_prefix}-search"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = var.location
  sku                           = var.search_sku
  replica_count                 = var.search_replica_count
  partition_count               = var.search_partition_count
  public_network_access_enabled = false
  local_authentication_enabled  = false
  authentication_failure_mode   = "http403"

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Azure AI Search Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_search" {
  name                = "${local.name_prefix}-pe-search"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["search"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-search"
    private_connection_resource_id = azurerm_search_service.search.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }

  private_dns_zone_group {
    name                 = "search-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["search"].id]
  }
}

#-------------------------------------------------------------------------------
# Azure AI Search RBAC Assignments
#-------------------------------------------------------------------------------
resource "azurerm_role_assignment" "search_fn_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.fn_mi.principal_id
}

resource "azurerm_role_assignment" "search_fn_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.fn_mi.principal_id
}

resource "azurerm_role_assignment" "search_aks_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.aks_mi.principal_id
}

resource "azurerm_role_assignment" "search_apim_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.apim_mi.principal_id
}

# AI Search needs access to ADLS for data source
resource "azurerm_role_assignment" "search_adls_reader" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.search.identity[0].principal_id
}

# AI Search needs access to OpenAI for vectorization
resource "azurerm_role_assignment" "search_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.search.identity[0].principal_id
}

#-------------------------------------------------------------------------------
# Azure OpenAI Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "openai_diag" {
  name                       = "${local.name_prefix}-aoai-diag"
  target_resource_id         = azurerm_cognitive_account.openai.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  enabled_log {
    category = "Trace"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

#-------------------------------------------------------------------------------
# Azure AI Search Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "search_diag" {
  name                       = "${local.name_prefix}-search-diag"
  target_resource_id         = azurerm_search_service.search.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "OperationLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
