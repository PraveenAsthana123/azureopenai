#===============================================================================
# Compute Module - AKS with GPU Node Pools, ACR
#===============================================================================

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "subnet_ids" { type = map(string) }
variable "private_dns_zone_ids" { type = map(string) }
variable "managed_identity_ids" { type = map(string) }
variable "aks_config" { type = any }
variable "gpu_node_pools" { type = any }
variable "log_analytics_workspace_id" { type = string }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# Container Registry (Premium for private endpoints)
#-------------------------------------------------------------------------------
resource "azurerm_container_registry" "main" {
  name                          = replace("${var.name_prefix}acr", "-", "")
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = "Premium"
  admin_enabled                 = false
  public_network_access_enabled = false
  zone_redundancy_enabled       = false
  data_endpoint_enabled         = true

  network_rule_set {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  retention_policy_in_days = 30

  tags = var.tags
}

resource "azurerm_private_endpoint" "acr" {
  name                = "${var.name_prefix}-pe-acr"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_ids["aks"]
  tags                = var.tags

  private_service_connection {
    name                           = "${var.name_prefix}-psc-acr"
    private_connection_resource_id = azurerm_container_registry.main.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }

  private_dns_zone_group {
    name                 = "acr-dns"
    private_dns_zone_ids = [var.private_dns_zone_ids["acr"]]
  }
}

#-------------------------------------------------------------------------------
# AKS Managed Identity
#-------------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.name_prefix}-aks-mi"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

#-------------------------------------------------------------------------------
# AKS Cluster
#-------------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "main" {
  name                              = "${var.name_prefix}-aks"
  location                          = var.location
  resource_group_name               = var.resource_group_name
  dns_prefix                        = "${var.name_prefix}-aks"
  kubernetes_version                = var.aks_config.kubernetes_version
  private_cluster_enabled           = true
  private_cluster_public_fqdn_enabled = false
  local_account_disabled            = false
  sku_tier                          = "Standard"
  automatic_upgrade_channel         = "patch"

  default_node_pool {
    name                 = "system"
    node_count           = var.aks_config.system_node_count
    vm_size              = var.aks_config.system_node_size
    vnet_subnet_id       = var.subnet_ids["aks"]
    type                 = "VirtualMachineScaleSets"
    auto_scaling_enabled = true
    min_count            = 2
    max_count            = 5
    max_pods             = 50
    os_disk_type         = "Managed"
    os_disk_size_gb      = 128

    upgrade_settings {
      max_surge = "33%"
    }

    node_labels = {
      "nodepool" = "system"
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  kubelet_identity {
    client_id                 = azurerm_user_assigned_identity.aks.client_id
    object_id                 = azurerm_user_assigned_identity.aks.principal_id
    user_assigned_identity_id = azurerm_user_assigned_identity.aks.id
  }

  network_profile {
    network_plugin    = var.aks_config.network_plugin
    network_policy    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
    service_cidr      = "10.100.0.0/16"
    dns_service_ip    = "10.100.0.10"
  }

  oms_agent {
    log_analytics_workspace_id      = var.log_analytics_workspace_id
    msi_auth_for_monitoring_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  workload_identity_enabled = true
  oidc_issuer_enabled       = true

  tags = var.tags
}

#-------------------------------------------------------------------------------
# GPU Node Pools for MLC LLM
#-------------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  for_each = { for pool in var.gpu_node_pools : pool.name => pool }

  name                  = each.value.name
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = each.value.vm_size
  node_count            = each.value.node_count
  vnet_subnet_id        = var.subnet_ids["gpu"]
  auto_scaling_enabled  = true
  min_count             = each.value.min_count
  max_count             = each.value.max_count
  max_pods              = 30
  os_disk_type          = "Managed"
  os_disk_size_gb       = 256
  mode                  = "User"

  node_labels = each.value.labels
  node_taints = each.value.taints

  tags = var.tags
}

#-------------------------------------------------------------------------------
# RBAC - ACR Pull
#-------------------------------------------------------------------------------
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "aks_network" {
  scope                = var.subnet_ids["aks"]
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

resource "azurerm_role_assignment" "aks_gpu_network" {
  scope                = var.subnet_ids["gpu"]
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_cluster_id" {
  value = azurerm_kubernetes_cluster.main.id
}

output "aks_host" {
  value     = azurerm_kubernetes_cluster.main.kube_config[0].host
  sensitive = true
}

output "aks_client_certificate" {
  value     = azurerm_kubernetes_cluster.main.kube_config[0].client_certificate
  sensitive = true
}

output "aks_client_key" {
  value     = azurerm_kubernetes_cluster.main.kube_config[0].client_key
  sensitive = true
}

output "aks_cluster_ca_certificate" {
  value     = azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate
  sensitive = true
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "aks_oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "aks_fqdn" {
  value = azurerm_kubernetes_cluster.main.fqdn
}
