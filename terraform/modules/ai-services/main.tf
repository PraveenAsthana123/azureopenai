# =============================================================================
# AI Services Module - Azure OpenAI Enterprise Platform
# =============================================================================
# Azure OpenAI, AI Search, Document Intelligence - RAG Ready
# =============================================================================

# -----------------------------------------------------------------------------
# Azure OpenAI Service
# -----------------------------------------------------------------------------

resource "azurerm_cognitive_account" "openai" {
  name                          = "oai-${var.name_prefix}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "OpenAI"
  sku_name                      = var.openai_sku
  custom_subdomain_name         = var.openai_custom_subdomain_name
  public_network_access_enabled = false
  local_auth_enabled            = false  # Force AAD auth

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = "Deny"

    dynamic "virtual_network_rules" {
      for_each = var.allowed_subnet_ids
      content {
        subnet_id = virtual_network_rules.value
      }
    }
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Azure OpenAI Model Deployments
# -----------------------------------------------------------------------------

resource "azurerm_cognitive_deployment" "models" {
  for_each = { for d in var.openai_deployments : d.name => d }

  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  sku {
    name     = each.value.scale_type
    capacity = each.value.capacity
  }
}

# -----------------------------------------------------------------------------
# Azure AI Search
# -----------------------------------------------------------------------------

resource "azurerm_search_service" "main" {
  name                          = "srch-${var.name_prefix}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  sku                           = var.search_sku
  replica_count                 = var.search_replica_count
  partition_count               = var.search_partition_count
  public_network_access_enabled = false
  local_authentication_enabled  = false  # Force AAD auth
  semantic_search_sku           = var.search_semantic_search_sku

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Document Intelligence (Form Recognizer)
# -----------------------------------------------------------------------------

resource "azurerm_cognitive_account" "document_intelligence" {
  count = var.enable_document_intelligence ? 1 : 0

  name                          = "di-${var.name_prefix}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "FormRecognizer"
  sku_name                      = var.document_intelligence_sku
  public_network_access_enabled = false
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = "Deny"
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Private Endpoints
# -----------------------------------------------------------------------------

resource "azurerm_private_endpoint" "openai" {
  name                = "pe-${var.name_prefix}-openai"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-openai"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "search" {
  name                = "pe-${var.name_prefix}-search"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-search"
    private_connection_resource_id = azurerm_search_service.main.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "document_intelligence" {
  count = var.enable_document_intelligence ? 1 : 0

  name                = "pe-${var.name_prefix}-di"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-di"
    private_connection_resource_id = azurerm_cognitive_account.document_intelligence[0].id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Store API Keys in Key Vault (as secrets)
# -----------------------------------------------------------------------------

resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = var.key_vault_id
}

resource "azurerm_key_vault_secret" "search_endpoint" {
  name         = "search-endpoint"
  value        = "https://${azurerm_search_service.main.name}.search.windows.net"
  key_vault_id = var.key_vault_id
}

# -----------------------------------------------------------------------------
# Diagnostic Settings
# -----------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "openai" {
  name                       = "diag-${var.name_prefix}-openai"
  target_resource_id         = azurerm_cognitive_account.openai.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  enabled_log {
    category = "Trace"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "search" {
  name                       = "diag-${var.name_prefix}-search"
  target_resource_id         = azurerm_search_service.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "OperationLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# -----------------------------------------------------------------------------
# RBAC - AI Search to OpenAI
# -----------------------------------------------------------------------------

resource "azurerm_role_assignment" "search_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}
