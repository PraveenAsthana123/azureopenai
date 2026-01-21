# =============================================================================
# Security Module - Azure OpenAI Enterprise Platform
# =============================================================================
# Key Vault, Managed Identities, RBAC - Zero Trust Aligned
# =============================================================================

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------

resource "azurerm_key_vault" "main" {
  name                        = "kv-${replace(var.name_prefix, "-", "")}"
  location                    = var.location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = var.key_vault_sku

  enabled_for_deployment          = false
  enabled_for_disk_encryption     = false
  enabled_for_template_deployment = false
  enable_rbac_authorization       = true  # Use RBAC instead of access policies
  purge_protection_enabled        = var.enable_purge_protection
  soft_delete_retention_days      = var.soft_delete_retention_days

  public_network_access_enabled   = false

  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Key Vault Private Endpoint
# -----------------------------------------------------------------------------

resource "azurerm_private_endpoint" "keyvault" {
  name                = "pe-${var.name_prefix}-kv"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-keyvault"
    private_connection_resource_id = azurerm_key_vault.main.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Managed Identities
# -----------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.name_prefix}-app"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_user_assigned_identity" "data_processor" {
  name                = "id-${var.name_prefix}-data"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# -----------------------------------------------------------------------------
# RBAC Role Assignments - Admin Group
# -----------------------------------------------------------------------------

resource "azurerm_role_assignment" "admin_keyvault" {
  for_each = toset(var.admin_group_object_ids)

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "admin_rg_contributor" {
  for_each = toset(var.admin_group_object_ids)

  scope                = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  role_definition_name = "Contributor"
  principal_id         = each.value
}

# -----------------------------------------------------------------------------
# RBAC Role Assignments - Developer Group
# -----------------------------------------------------------------------------

resource "azurerm_role_assignment" "dev_keyvault_reader" {
  for_each = toset(var.developer_group_object_ids)

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "dev_rg_reader" {
  for_each = toset(var.developer_group_object_ids)

  scope                = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  role_definition_name = "Reader"
  principal_id         = each.value
}

# -----------------------------------------------------------------------------
# Current User - Key Vault Admin (for initial setup)
# -----------------------------------------------------------------------------

resource "azurerm_role_assignment" "current_user_keyvault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.current_user_object_id
}

# -----------------------------------------------------------------------------
# Diagnostic Settings
# -----------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "keyvault" {
  count = var.log_analytics_workspace_id != null ? 1 : 0

  name                       = "diag-${var.name_prefix}-kv"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_log {
    category = "AzurePolicyEvaluationDetails"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

data "azurerm_subscription" "current" {}
