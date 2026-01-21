#===============================================================================
# Monitoring Module - Log Analytics, Application Insights, Alerts
#===============================================================================

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "retention_days" { type = number }
variable "alert_email" { type = string }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# Log Analytics Workspace
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.name_prefix}-law"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Application Insights
#-------------------------------------------------------------------------------
resource "azurerm_application_insights" "main" {
  name                = "${var.name_prefix}-appi"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  retention_in_days   = 90

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Action Group
#-------------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "critical" {
  name                = "${var.name_prefix}-ag-critical"
  resource_group_name = var.resource_group_name
  short_name          = "Critical"

  email_receiver {
    name          = "ai-ops-team"
    email_address = var.alert_email
  }

  tags = var.tags
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}

output "application_insights_id" {
  value = azurerm_application_insights.main.id
}

output "application_insights_connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}

output "action_group_id" {
  value = azurerm_monitor_action_group.critical.id
}
