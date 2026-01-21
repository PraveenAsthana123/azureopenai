# AI Services Module - Azure OpenAI, AI Search, Document Intelligence, Computer Vision

# Azure OpenAI Service (conditionally deployed based on quota availability)
resource "azurerm_cognitive_account" "openai" {
  count                 = var.deploy_openai ? 1 : 0
  name                  = "oai-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${var.project_name}-${var.environment}-${var.resource_suffix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# OpenAI Model Deployments (only if OpenAI is deployed)
resource "azurerm_cognitive_deployment" "models" {
  for_each = var.deploy_openai ? { for deployment in var.openai_model_deployments : deployment.name => deployment } : {}

  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.openai[0].id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  scale {
    type     = "GlobalStandard"
    capacity = each.value.capacity
  }
}

# Azure AI Search Service
resource "azurerm_search_service" "main" {
  name                = "search-${var.project_name}-${var.environment}-${var.resource_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "standard"
  replica_count       = 1
  partition_count     = 1

  public_network_access_enabled = false
  local_authentication_enabled  = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Document Intelligence (Form Recognizer)
resource "azurerm_cognitive_account" "document_intelligence" {
  name                  = "di-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "di-${var.project_name}-${var.environment}-${var.resource_suffix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Computer Vision Service
resource "azurerm_cognitive_account" "computer_vision" {
  name                  = "cv-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "ComputerVision"
  sku_name              = "S1"
  custom_subdomain_name = "cv-${var.project_name}-${var.environment}-${var.resource_suffix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Speech Service (for audio processing)
resource "azurerm_cognitive_account" "speech" {
  name                  = "speech-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "SpeechServices"
  sku_name              = "S0"
  custom_subdomain_name = "speech-${var.project_name}-${var.environment}-${var.resource_suffix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Content Safety Service (conditionally deployed - requires special quota)
resource "azurerm_cognitive_account" "content_safety" {
  count                 = var.deploy_content_safety ? 1 : 0
  name                  = "cs-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "ContentSafety"
  sku_name              = "S0"
  custom_subdomain_name = "cs-${var.project_name}-${var.environment}-${var.resource_suffix}"

  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Private Endpoints

# OpenAI Private Endpoint (only if OpenAI is deployed)
resource "azurerm_private_endpoint" "openai" {
  count               = var.deploy_openai ? 1 : 0
  name                = "pe-openai-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-openai"
    private_connection_resource_id = azurerm_cognitive_account.openai[0].id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_ids["openai"]]
  }
}

# AI Search Private Endpoint
resource "azurerm_private_endpoint" "search" {
  name                = "pe-search-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-search"
    private_connection_resource_id = azurerm_search_service.main.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_ids["search"]]
  }
}

# Document Intelligence Private Endpoint
resource "azurerm_private_endpoint" "document_intelligence" {
  name                = "pe-di-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-di"
    private_connection_resource_id = azurerm_cognitive_account.document_intelligence.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_ids["cognitiveservices"]]
  }
}

# Computer Vision Private Endpoint
resource "azurerm_private_endpoint" "computer_vision" {
  name                = "pe-cv-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-cv"
    private_connection_resource_id = azurerm_cognitive_account.computer_vision.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_ids["cognitiveservices"]]
  }
}
