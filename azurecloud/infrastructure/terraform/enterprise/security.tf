#===============================================================================
# Enterprise AI Platform - Security Configuration
# Zero-Trust Architecture - Key Vault, Managed Identities, RBAC
#===============================================================================

#-------------------------------------------------------------------------------
# User Assigned Managed Identities
#-------------------------------------------------------------------------------

# Function App Identity
resource "azurerm_user_assigned_identity" "fn_mi" {
  name                = "${local.name_prefix}-fn-mi"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

# AKS Identity
resource "azurerm_user_assigned_identity" "aks_mi" {
  name                = "${local.name_prefix}-aks-mi"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

# APIM Identity
resource "azurerm_user_assigned_identity" "apim_mi" {
  name                = "${local.name_prefix}-apim-mi"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

# Data Pipeline Identity
resource "azurerm_user_assigned_identity" "data_mi" {
  name                = "${local.name_prefix}-data-mi"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

#-------------------------------------------------------------------------------
# Key Vault
#-------------------------------------------------------------------------------
resource "azurerm_key_vault" "kv" {
  name                          = "${var.prefix}kv${var.environment}01"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = true
  soft_delete_retention_days    = 14
  public_network_access_enabled = false
  rbac_authorization_enabled    = true

  network_acls {
    default_action             = "Deny"
    bypass                     = "AzureServices"
    virtual_network_subnet_ids = [azurerm_subnet.subnets["app"].id]
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Key Vault Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_kv" {
  name                = "${local.name_prefix}-pe-kv"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["data"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-kv"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  private_dns_zone_group {
    name                 = "kv-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["keyvault"].id]
  }
}

#-------------------------------------------------------------------------------
# Key Vault RBAC Assignments
#-------------------------------------------------------------------------------

# Terraform SP gets full access
resource "azurerm_role_assignment" "kv_terraform_admin" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Function App identity gets secrets access
resource "azurerm_role_assignment" "kv_fn_secrets" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.fn_mi.principal_id
}

# AKS identity gets secrets access
resource "azurerm_role_assignment" "kv_aks_secrets" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.aks_mi.principal_id
}

# APIM identity gets secrets access
resource "azurerm_role_assignment" "kv_apim_secrets" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.apim_mi.principal_id
}

# Data pipeline identity gets secrets access
resource "azurerm_role_assignment" "kv_data_secrets" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.data_mi.principal_id
}

#-------------------------------------------------------------------------------
# Key Vault Secrets (Placeholders - populate post-deploy)
#-------------------------------------------------------------------------------
resource "azurerm_key_vault_secret" "sql_password" {
  name         = "sql-admin-password"
  value        = var.sql_admin_password
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [azurerm_role_assignment.kv_terraform_admin]
}

#-------------------------------------------------------------------------------
# Key Vault Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "kv_diag" {
  name                       = "${local.name_prefix}-kv-diag"
  target_resource_id         = azurerm_key_vault.kv.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_log {
    category = "AzurePolicyEvaluationDetails"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
