# =============================================================================
# Compute Module - Azure OpenAI Enterprise Platform
# =============================================================================
# AKS, Azure Functions, Container Registry - Compute Layer
# =============================================================================

# -----------------------------------------------------------------------------
# Azure Container Registry
# -----------------------------------------------------------------------------

resource "azurerm_container_registry" "main" {
  count = var.enable_acr ? 1 : 0

  name                          = "acr${replace(var.name_prefix, "-", "")}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.acr_sku
  admin_enabled                 = false
  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }

  # Geo-replication for Premium SKU
  dynamic "georeplications" {
    for_each = var.acr_sku == "Premium" && length(var.acr_georeplication_locations) > 0 ? var.acr_georeplication_locations : []
    content {
      location = georeplications.value
    }
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# AKS Cluster
# -----------------------------------------------------------------------------

resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.name_prefix
  kubernetes_version  = var.aks_kubernetes_version

  # Private cluster
  private_cluster_enabled = true

  # System node pool
  default_node_pool {
    name                 = "system"
    node_count           = var.aks_node_count
    vm_size              = var.aks_node_vm_size
    vnet_subnet_id       = var.aks_subnet_id
    type                 = "VirtualMachineScaleSets"
    enable_auto_scaling  = true
    min_count            = var.aks_node_count
    max_count            = var.aks_node_count * 2
    max_pods             = 110
    os_disk_size_gb      = 128
    os_disk_type         = "Managed"

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  # Azure AD RBAC
  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    managed            = true
  }

  # Network configuration
  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
    service_cidr      = "10.1.0.0/16"
    dns_service_ip    = "10.1.0.10"
  }

  # Monitoring
  dynamic "oms_agent" {
    for_each = var.enable_oms_agent ? [1] : []
    content {
      log_analytics_workspace_id = var.log_analytics_workspace_id
    }
  }

  # Azure Policy
  azure_policy_enabled = var.enable_azure_policy

  # Key Vault Secrets Provider
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  # Workload Identity
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# AKS User Node Pool (for workloads)
# -----------------------------------------------------------------------------

resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  name                  = "workload"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.aks_workload_node_vm_size
  vnet_subnet_id        = var.aks_subnet_id

  enable_auto_scaling = true
  min_count           = 1
  max_count           = 10
  max_pods            = 110

  node_labels = {
    "workload" = "ai-services"
  }

  node_taints = []

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Azure Functions - App Service Plan
# -----------------------------------------------------------------------------

resource "azurerm_service_plan" "functions" {
  name                = "asp-${var.name_prefix}-func"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = var.functions_sku

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Azure Functions - Storage Account
# -----------------------------------------------------------------------------

resource "azurerm_storage_account" "functions" {
  name                            = "stfunc${replace(var.name_prefix, "-", "")}"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Azure Functions App
# -----------------------------------------------------------------------------

resource "azurerm_linux_function_app" "main" {
  name                       = "func-${var.name_prefix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  virtual_network_subnet_id = var.functions_subnet_id

  https_only                    = true
  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                              = var.functions_sku != "Y1"
    ftps_state                             = "Disabled"
    minimum_tls_version                    = "1.2"
    application_insights_connection_string = var.application_insights_connection_string

    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = []
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "WEBSITE_RUN_FROM_PACKAGE"       = "1"
    "KEY_VAULT_URI"                  = var.key_vault_uri
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.application_insights_connection_string
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# RBAC - AKS to ACR
# -----------------------------------------------------------------------------

resource "azurerm_role_assignment" "aks_acr" {
  count = var.enable_acr ? 1 : 0

  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

# -----------------------------------------------------------------------------
# Diagnostic Settings
# -----------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "aks" {
  name                       = "diag-${var.name_prefix}-aks"
  target_resource_id         = azurerm_kubernetes_cluster.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "kube-apiserver"
  }

  enabled_log {
    category = "kube-controller-manager"
  }

  enabled_log {
    category = "kube-scheduler"
  }

  enabled_log {
    category = "kube-audit"
  }

  enabled_log {
    category = "cluster-autoscaler"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "functions" {
  name                       = "diag-${var.name_prefix}-func"
  target_resource_id         = azurerm_linux_function_app.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "FunctionAppLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
