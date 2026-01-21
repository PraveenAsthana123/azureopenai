#===============================================================================
# Security Module - Key Vault, Managed Identities, RBAC
#===============================================================================

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tenant_id" { type = string }
variable "object_id" { type = string }
variable "subnet_ids" { type = map(string) }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# Managed Identities
#-------------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.name_prefix}-app-mi"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "mlc_llm" {
  name                = "${var.name_prefix}-mlcllm-mi"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "data" {
  name                = "${var.name_prefix}-data-mi"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

#-------------------------------------------------------------------------------
# Key Vault
#-------------------------------------------------------------------------------
resource "azurerm_key_vault" "main" {
  name                          = "${var.name_prefix}-kv"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = true
  soft_delete_retention_days    = 14
  public_network_access_enabled = false
  rbac_authorization_enabled    = true

  network_acls {
    default_action             = "Deny"
    bypass                     = "AzureServices"
    virtual_network_subnet_ids = [var.subnet_ids["app"]]
  }

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Key Vault RBAC
#-------------------------------------------------------------------------------
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.object_id
}

resource "azurerm_role_assignment" "kv_app_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "kv_mlcllm_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.mlc_llm.principal_id
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "managed_identity_ids" {
  value = {
    app     = azurerm_user_assigned_identity.app.id
    mlc_llm = azurerm_user_assigned_identity.mlc_llm.id
    data    = azurerm_user_assigned_identity.data.id
  }
}

output "managed_identity_principal_ids" {
  value = {
    app     = azurerm_user_assigned_identity.app.principal_id
    mlc_llm = azurerm_user_assigned_identity.mlc_llm.principal_id
    data    = azurerm_user_assigned_identity.data.principal_id
  }
}

output "managed_identity_client_ids" {
  value = {
    app     = azurerm_user_assigned_identity.app.client_id
    mlc_llm = azurerm_user_assigned_identity.mlc_llm.client_id
    data    = azurerm_user_assigned_identity.data.client_id
  }
}
