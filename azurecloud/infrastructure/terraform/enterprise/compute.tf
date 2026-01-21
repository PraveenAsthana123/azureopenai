#===============================================================================
# Enterprise AI Platform - Compute Layer
# Zero-Trust Architecture - ACR, AKS
#===============================================================================

#-------------------------------------------------------------------------------
# Azure Container Registry
#-------------------------------------------------------------------------------
resource "azurerm_container_registry" "acr" {
  name                          = replace("${var.prefix}acr${var.environment}01", "-", "")
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = var.location
  sku                           = "Premium"
  admin_enabled                 = false
  public_network_access_enabled = false
  zone_redundancy_enabled       = false
  anonymous_pull_enabled        = false
  data_endpoint_enabled         = true

  network_rule_set {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  retention_policy_in_days = 30

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# ACR Private Endpoint
#-------------------------------------------------------------------------------
resource "azurerm_private_endpoint" "pe_acr" {
  name                = "${local.name_prefix}-pe-acr"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.subnets["compute"].id
  tags                = local.common_tags

  private_service_connection {
    name                           = "${local.name_prefix}-psc-acr"
    private_connection_resource_id = azurerm_container_registry.acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }

  private_dns_zone_group {
    name                 = "acr-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["acr"].id]
  }
}

#-------------------------------------------------------------------------------
# Azure Kubernetes Service (AKS)
#-------------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "aks" {
  name                              = "${local.name_prefix}-aks"
  location                          = var.location
  resource_group_name               = azurerm_resource_group.rg.name
  dns_prefix                        = "${local.name_prefix}-aks"
  kubernetes_version                = "1.29"
  private_cluster_enabled           = true
  private_cluster_public_fqdn_enabled = false
  local_account_disabled            = true
  sku_tier                          = "Standard"
  automatic_upgrade_channel         = "patch"

  default_node_pool {
    name                 = "system"
    node_count           = var.aks_node_count
    vm_size              = var.aks_node_size
    vnet_subnet_id       = azurerm_subnet.subnets["compute"].id
    type                 = "VirtualMachineScaleSets"
    auto_scaling_enabled = true
    min_count            = 2
    max_count            = 5
    max_pods             = 50
    os_disk_type         = "Managed"
    os_disk_size_gb      = 128
    zones                = []

    upgrade_settings {
      max_surge = "33%"
    }

    node_labels = {
      "nodepool" = "system"
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_mi.id]
  }

  kubelet_identity {
    client_id                 = azurerm_user_assigned_identity.aks_mi.client_id
    object_id                 = azurerm_user_assigned_identity.aks_mi.principal_id
    user_assigned_identity_id = azurerm_user_assigned_identity.aks_mi.id
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
    service_cidr      = "10.100.0.0/16"
    dns_service_ip    = "10.100.0.10"
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled     = true
    admin_group_object_ids = []
  }

  oms_agent {
    log_analytics_workspace_id      = azurerm_log_analytics_workspace.law.id
    msi_auth_for_monitoring_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  workload_identity_enabled = true
  oidc_issuer_enabled       = true

  maintenance_window_auto_upgrade {
    frequency   = "Weekly"
    interval    = 1
    duration    = 4
    day_of_week = "Sunday"
    start_time  = "02:00"
    utc_offset  = "+00:00"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# AKS User Node Pool (for AI workloads)
#-------------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster_node_pool" "ai_workers" {
  name                  = "aiworkers"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D8s_v3"
  node_count            = 1
  vnet_subnet_id        = azurerm_subnet.subnets["compute"].id
  auto_scaling_enabled  = true
  min_count             = 1
  max_count             = 10
  max_pods              = 30
  os_disk_type          = "Managed"
  os_disk_size_gb       = 256
  mode                  = "User"
  zones                 = []

  node_labels = {
    "nodepool" = "ai-workers"
    "workload" = "ai"
  }

  node_taints = [
    "workload=ai:NoSchedule"
  ]

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# AKS RBAC Assignments
#-------------------------------------------------------------------------------

# AKS identity needs ACR pull permission
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# AKS identity network contributor on subnet
resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                = azurerm_subnet.subnets["compute"].id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_mi.principal_id
}

#-------------------------------------------------------------------------------
# AKS Diagnostic Settings
#-------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "aks_diag" {
  name                       = "${local.name_prefix}-aks-diag"
  target_resource_id         = azurerm_kubernetes_cluster.aks.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log {
    category = "kube-apiserver"
  }

  enabled_log {
    category = "kube-audit"
  }

  enabled_log {
    category = "kube-controller-manager"
  }

  enabled_log {
    category = "kube-scheduler"
  }

  enabled_log {
    category = "cluster-autoscaler"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
