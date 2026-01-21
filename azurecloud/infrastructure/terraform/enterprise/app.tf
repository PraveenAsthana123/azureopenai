#===============================================================================
# Enterprise AI Platform - Application Layer
# Zero-Trust Architecture - Function App, API Management
#===============================================================================

#-------------------------------------------------------------------------------
# Function App Service Plan (Premium)
#-------------------------------------------------------------------------------
resource "azurerm_service_plan" "fn_plan" {
  name                = "${local.name_prefix}-fn-plan"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = var.function_sku

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Function App Storage Account
#-------------------------------------------------------------------------------
resource "azurerm_storage_account" "fn_storage" {
  name                          = replace("${var.prefix}fnst${var.environment}01", "-", "")
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = var.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = false
  min_tls_version               = "TLS1_2"

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Function App (Orchestrator)
#-------------------------------------------------------------------------------
resource "azurerm_linux_function_app" "orchestrator" {
  name                          = "${local.name_prefix}-fn-orchestrator"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  service_plan_id               = azurerm_service_plan.fn_plan.id
  storage_account_name          = azurerm_storage_account.fn_storage.name
  storage_account_access_key    = azurerm_storage_account.fn_storage.primary_access_key
  https_only                    = true
  public_network_access_enabled = false
  virtual_network_subnet_id     = azurerm_subnet.subnets["app"].id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.fn_mi.id]
  }

  site_config {
    always_on                              = true
    http2_enabled                          = true
    vnet_route_all_enabled                 = true
    application_insights_connection_string = azurerm_application_insights.appi.connection_string
    ftps_state                             = "Disabled"
    minimum_tls_version                    = "1.2"

    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = []
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "WEBSITE_RUN_FROM_PACKAGE"              = "1"
    "AZURE_OPENAI_ENDPOINT"                 = azurerm_cognitive_account.openai.endpoint
    "AZURE_SEARCH_ENDPOINT"                 = "https://${azurerm_search_service.search.name}.search.windows.net"
    "COSMOS_DB_ENDPOINT"                    = azurerm_cosmosdb_account.cosmos.endpoint
    "COSMOS_DB_DATABASE"                    = azurerm_cosmosdb_sql_database.sessions.name
    "ADLS_ACCOUNT_URL"                      = azurerm_storage_account.adls.primary_dfs_endpoint
    "KEYVAULT_URI"                          = azurerm_key_vault.kv.vault_uri
    "AZURE_CLIENT_ID"                       = azurerm_user_assigned_identity.fn_mi.client_id
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.appi.connection_string
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Function App Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_fn" {
  name                = "${local.name_prefix}-pe-fn"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["integration"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-fn"
    private_connection_resource_id = azurerm_linux_function_app.orchestrator.id
    is_manual_connection           = false
    subresource_names              = ["sites"]
  }
}

#-------------------------------------------------------------------------------
# API Management (Internal Gateway)
#-------------------------------------------------------------------------------
resource "azurerm_api_management" "apim" {
  name                          = "${local.name_prefix}-apim"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  publisher_name                = var.apim_publisher_name
  publisher_email               = var.apim_publisher_email
  sku_name                      = var.apim_sku
  public_network_access_enabled = false
  virtual_network_type          = "Internal"

  virtual_network_configuration {
    subnet_id = azurerm_subnet.subnets["integration"].id
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apim_mi.id]
  }

  protocols {
    http2_enabled = true
  }

  security {
    backend_ssl30_enabled  = false
    backend_tls10_enabled  = false
    backend_tls11_enabled  = false
    frontend_ssl30_enabled = false
    frontend_tls10_enabled = false
    frontend_tls11_enabled = false
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# APIM API - AI Orchestrator
#-------------------------------------------------------------------------------
resource "azurerm_api_management_api" "orchestrator" {
  name                = "ai-orchestrator-api"
  resource_group_name = azurerm_resource_group.rg.name
  api_management_name = azurerm_api_management.apim.name
  revision            = "1"
  display_name        = "AI Orchestrator API"
  path                = "ai"
  protocols           = ["https"]
  service_url         = "https://${azurerm_linux_function_app.orchestrator.default_hostname}/api"

  subscription_required = true
  subscription_key_parameter_names {
    header = "Ocp-Apim-Subscription-Key"
    query  = "subscription-key"
  }
}

#-------------------------------------------------------------------------------
# APIM Product
#-------------------------------------------------------------------------------
resource "azurerm_api_management_product" "enterprise" {
  product_id            = "enterprise-ai"
  api_management_name   = azurerm_api_management.apim.name
  resource_group_name   = azurerm_resource_group.rg.name
  display_name          = "Enterprise AI Platform"
  subscription_required = true
  approval_required     = true
  published             = true
  description           = "Enterprise AI Platform APIs"
}

resource "azurerm_api_management_product_api" "orchestrator" {
  api_name            = azurerm_api_management_api.orchestrator.name
  product_id          = azurerm_api_management_product.enterprise.product_id
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = azurerm_resource_group.rg.name
}

#-------------------------------------------------------------------------------
# APIM Global Policy
#-------------------------------------------------------------------------------
resource "azurerm_api_management_policy" "global" {
  api_management_id = azurerm_api_management.apim.id
  xml_content       = <<XML
<policies>
  <inbound>
    <cors allow-credentials="false">
      <allowed-origins>
        <origin>*</origin>
      </allowed-origins>
      <allowed-methods>
        <method>GET</method>
        <method>POST</method>
        <method>PUT</method>
        <method>DELETE</method>
        <method>OPTIONS</method>
      </allowed-methods>
      <allowed-headers>
        <header>*</header>
      </allowed-headers>
    </cors>
    <rate-limit calls="100" renewal-period="60" />
    <quota calls="10000" renewal-period="86400" />
  </inbound>
  <backend>
    <forward-request />
  </backend>
  <outbound />
  <on-error>
    <set-header name="ErrorSource" exists-action="override">
      <value>@(context.LastError.Source)</value>
    </set-header>
    <set-header name="ErrorReason" exists-action="override">
      <value>@(context.LastError.Reason)</value>
    </set-header>
  </on-error>
</policies>
XML
}

#-------------------------------------------------------------------------------
# APIM Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "apim_diag" {
  name                       = "${local.name_prefix}-apim-diag"
  target_resource_id         = azurerm_api_management.apim.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "GatewayLogs"
  }

  enabled_log {
    category = "WebSocketConnectionLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

#-------------------------------------------------------------------------------
# Function App Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "fn_diag" {
  name                       = "${local.name_prefix}-fn-diag"
  target_resource_id         = azurerm_linux_function_app.orchestrator.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "FunctionAppLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
