# Compute Module - Azure Functions (Serverless) + VMs

# App Service Plan for Functions (conditionally deployed)
resource "azurerm_service_plan" "functions_consumption" {
  count               = var.deploy_functions ? 1 : 0
  name                = "asp-func-consumption-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Windows"
  sku_name            = "Y1"  # Consumption plan

  tags = var.tags
}

# Function App - API Gateway (conditionally deployed)
resource "azurerm_windows_function_app" "api_gateway" {
  count                      = var.deploy_functions ? 1 : 0
  name                       = "func-api-${var.project_name}-${var.resource_suffix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.functions_consumption[0].id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key

  site_config {
    application_stack {
      dotnet_version = "v8.0"
    }

    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "dotnet-isolated"
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Function App - Orchestrator (conditionally deployed)
resource "azurerm_windows_function_app" "orchestrator" {
  count                      = var.deploy_functions ? 1 : 0
  name                       = "func-orch-${var.project_name}-${var.resource_suffix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.functions_consumption[0].id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key

  site_config {
    application_stack {
      dotnet_version = "v8.0"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "dotnet-isolated"
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Function App - Ingestion Pipeline (conditionally deployed)
resource "azurerm_windows_function_app" "ingestion" {
  count                      = var.deploy_functions ? 1 : 0
  name                       = "func-ingest-${var.project_name}-${var.resource_suffix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.functions_consumption[0].id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key

  site_config {
    application_stack {
      dotnet_version = "v8.0"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "dotnet-isolated"
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Function App - RAG Processor (conditionally deployed)
resource "azurerm_windows_function_app" "rag_processor" {
  count                      = var.deploy_functions ? 1 : 0
  name                       = "func-rag-${var.project_name}-${var.resource_suffix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.functions_consumption[0].id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key

  site_config {
    application_stack {
      dotnet_version = "v8.0"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "dotnet-isolated"
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# VM Network Interfaces
resource "azurerm_network_interface" "vm" {
  count               = var.vm_count
  name                = "nic-vm-${count.index + 1}-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.vm_subnet_id
    private_ip_address_allocation = "Dynamic"
  }

  tags = var.tags
}

# Linux VMs for Backend Processing
resource "azurerm_linux_virtual_machine" "backend" {
  count               = var.vm_count
  name                = "vm-backend-${count.index + 1}-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  size                = var.vm_size
  admin_username      = var.vm_admin_username
  admin_password      = var.vm_admin_password

  disable_password_authentication = false

  network_interface_ids = [
    azurerm_network_interface.vm[count.index].id
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  custom_data = base64encode(<<-EOF
    #!/bin/bash
    # Update system
    apt-get update && apt-get upgrade -y

    # Install Python and dependencies
    apt-get install -y python3.11 python3.11-venv python3-pip

    # Install Node.js (for frontend build)
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs

    # Install Azure CLI
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash

    # Install nginx for serving frontend
    apt-get install -y nginx

    # Create app directories
    mkdir -p /opt/genai-copilot/{backend,frontend,logs}

    # Set permissions
    chown -R ${var.vm_admin_username}:${var.vm_admin_username} /opt/genai-copilot

    echo "VM initialization complete" >> /var/log/vm-init.log
    EOF
  )

  tags = var.tags
}

# VM Extension for monitoring
resource "azurerm_virtual_machine_extension" "monitoring" {
  count                      = var.vm_count
  name                       = "AzureMonitorLinuxAgent"
  virtual_machine_id         = azurerm_linux_virtual_machine.backend[count.index].id
  publisher                  = "Microsoft.Azure.Monitor"
  type                       = "AzureMonitorLinuxAgent"
  type_handler_version       = "1.0"
  automatic_upgrade_enabled  = true
  auto_upgrade_minor_version = true
}
