# API Management Module - Gateway for all API traffic
# Implements rate limiting, JWT validation, routing as per LLD

resource "azurerm_api_management" "main" {
  name                = "apim-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  publisher_name      = var.publisher_name
  publisher_email     = var.publisher_email

  sku_name = var.environment == "prod" ? "Standard_1" : "Developer_1"

  identity {
    type = "SystemAssigned"
  }

  # Virtual Network integration
  virtual_network_type = "Internal"

  virtual_network_configuration {
    subnet_id = var.apim_subnet_id
  }

  tags = var.tags
}

# Named Value for OpenAI Key (from Key Vault)
resource "azurerm_api_management_named_value" "openai_key" {
  name                = "openai-api-key"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  display_name        = "OpenAI API Key"
  secret              = true

  value_from_key_vault {
    secret_id = var.openai_key_secret_id
  }
}

# API - GenAI Copilot
resource "azurerm_api_management_api" "copilot" {
  name                  = "genai-copilot-api"
  resource_group_name   = var.resource_group_name
  api_management_name   = azurerm_api_management.main.name
  revision              = "1"
  display_name          = "GenAI Copilot API"
  path                  = "api"
  protocols             = ["https"]
  subscription_required = true

  import {
    content_format = "openapi+json"
    content_value  = file("${path.module}/api-spec.json")
  }
}

# Product - Enterprise
resource "azurerm_api_management_product" "enterprise" {
  product_id            = "enterprise"
  api_management_name   = azurerm_api_management.main.name
  resource_group_name   = var.resource_group_name
  display_name          = "Enterprise"
  subscription_required = true
  approval_required     = true
  published             = true
}

# Rate Limiting Policy (Global)
resource "azurerm_api_management_policy" "global" {
  api_management_id = azurerm_api_management.main.id

  xml_content = <<XML
<policies>
  <inbound>
    <!-- JWT Validation for Entra ID -->
    <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
      <openid-config url="https://login.microsoftonline.com/${var.tenant_id}/v2.0/.well-known/openid-configuration" />
      <audiences>
        <audience>${var.api_audience}</audience>
      </audiences>
      <issuers>
        <issuer>https://sts.windows.net/${var.tenant_id}/</issuer>
      </issuers>
      <required-claims>
        <claim name="roles" match="any">
          <value>Copilot.User</value>
          <value>Copilot.Admin</value>
        </claim>
      </required-claims>
    </validate-jwt>

    <!-- Rate Limiting -->
    <rate-limit-by-key calls="100" renewal-period="60" counter-key="@(context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()?.Subject)" />

    <!-- Quota -->
    <quota-by-key calls="10000" renewal-period="86400" counter-key="@(context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()?.Subject)" />

    <!-- Extract user info for ACL -->
    <set-variable name="userId" value="@(context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()?.Subject)" />
    <set-variable name="userGroups" value="@(String.Join(",", context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()?.Claims.GetValueOrDefault("groups", new string[0])))" />

    <!-- CORS -->
    <cors allow-credentials="true">
      <allowed-origins>
        <origin>https://*.azurewebsites.net</origin>
        <origin>https://teams.microsoft.com</origin>
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
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
    <!-- Add request ID for tracing -->
    <set-header name="X-Request-Id" exists-action="override">
      <value>@(context.RequestId.ToString())</value>
    </set-header>
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
XML
}

# Backend - Pre-Retrieval Function
resource "azurerm_api_management_backend" "pre_retrieval" {
  name                = "pre-retrieval-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "https://${var.pre_retrieval_function_hostname}/api"

  credentials {
    header = {
      "x-functions-key" = var.pre_retrieval_function_key
    }
  }
}

# Backend - RAG Processor Function
resource "azurerm_api_management_backend" "rag_processor" {
  name                = "rag-processor-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "https://${var.rag_processor_function_hostname}/api"

  credentials {
    header = {
      "x-functions-key" = var.rag_processor_function_key
    }
  }
}

# Diagnostic Settings
resource "azurerm_monitor_diagnostic_setting" "apim" {
  name                       = "diag-apim"
  target_resource_id         = azurerm_api_management.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "GatewayLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
