# =============================================================================
# Monitoring Module - Azure OpenAI Enterprise Platform
# =============================================================================
# Log Analytics, Application Insights, Alerts - Observability Stack
# =============================================================================

# -----------------------------------------------------------------------------
# Log Analytics Workspace
# -----------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.log_analytics_sku
  retention_in_days   = var.log_retention_days

  daily_quota_gb = var.log_daily_quota_gb

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Application Insights
# -----------------------------------------------------------------------------

resource "azurerm_application_insights" "main" {
  name                = "appi-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  retention_in_days   = var.log_retention_days
  sampling_percentage = 100

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Action Group for Alerts
# -----------------------------------------------------------------------------

resource "azurerm_monitor_action_group" "critical" {
  name                = "ag-${var.name_prefix}-critical"
  resource_group_name = var.resource_group_name
  short_name          = "Critical"

  dynamic "email_receiver" {
    for_each = var.alert_email_addresses
    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

resource "azurerm_monitor_action_group" "warning" {
  name                = "ag-${var.name_prefix}-warning"
  resource_group_name = var.resource_group_name
  short_name          = "Warning"

  dynamic "email_receiver" {
    for_each = var.alert_email_addresses
    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Metric Alerts - OpenAI Token Usage
# -----------------------------------------------------------------------------

resource "azurerm_monitor_metric_alert" "openai_rate_limit" {
  name                = "alert-${var.name_prefix}-openai-rate-limit"
  resource_group_name = var.resource_group_name
  scopes              = [var.openai_account_id]
  description         = "Alert when OpenAI rate limit is approaching"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "TokenTransaction"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 80000  # Adjust based on your quota
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = var.tags

  count = var.openai_account_id != null ? 1 : 0
}

# -----------------------------------------------------------------------------
# Log Query Alerts - Error Rate
# -----------------------------------------------------------------------------

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_error_rate" {
  name                = "alert-${var.name_prefix}-high-error-rate"
  resource_group_name = var.resource_group_name
  location            = var.location
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when error rate exceeds threshold"
  severity            = 1

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(15m)
      | summarize
          total = count(),
          failed = countif(success == false)
      | extend error_rate = (failed * 100.0) / total
      | where error_rate > 5
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.critical.id]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Log Query Alerts - AI/GenAI Specific
# -----------------------------------------------------------------------------

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "ai_latency" {
  name                = "alert-${var.name_prefix}-ai-latency"
  resource_group_name = var.resource_group_name
  location            = var.location
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when AI response latency is high"
  severity            = 2

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(15m)
      | where name contains "openai" or name contains "chat" or name contains "completion"
      | summarize p95_duration = percentile(duration, 95)
      | where p95_duration > 10000
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.warning.id]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Microsoft Sentinel (Optional - for Security Monitoring)
# -----------------------------------------------------------------------------

resource "azurerm_sentinel_log_analytics_workspace_onboarding" "main" {
  count = var.enable_sentinel ? 1 : 0

  workspace_id = azurerm_log_analytics_workspace.main.id
}

# -----------------------------------------------------------------------------
# Workbook - AI Platform Dashboard
# -----------------------------------------------------------------------------

resource "azurerm_application_insights_workbook" "ai_dashboard" {
  name                = "wb-${var.name_prefix}-ai-dashboard"
  resource_group_name = var.resource_group_name
  location            = var.location
  display_name        = "AI Platform Dashboard"

  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      {
        type  = 1
        content = {
          json = "# AI Platform Monitoring Dashboard\n\nReal-time monitoring for Azure OpenAI, AI Search, and RAG pipeline."
        }
      },
      {
        type = 3
        content = {
          version = "KqlItem/1.0"
          query   = "requests | summarize count() by bin(timestamp, 1h) | render timechart"
        }
      }
    ]
  })

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Container Insights Solution (for AKS)
# -----------------------------------------------------------------------------

resource "azurerm_log_analytics_solution" "container_insights" {
  count = var.enable_container_insights ? 1 : 0

  solution_name         = "ContainerInsights"
  location              = var.location
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.main.id
  workspace_name        = azurerm_log_analytics_workspace.main.name

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/ContainerInsights"
  }
}
