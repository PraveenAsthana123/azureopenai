#===============================================================================
# Enterprise AI Platform - Monitoring Layer
# Zero-Trust Architecture - Log Analytics, Application Insights, Alerts
#===============================================================================

#-------------------------------------------------------------------------------
# Log Analytics Workspace
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${local.name_prefix}-law"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  daily_quota_gb                      = -1
  internet_ingestion_enabled          = true
  internet_query_enabled              = true
  reservation_capacity_in_gb_per_day  = null

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Application Insights
#-------------------------------------------------------------------------------
resource "azurerm_application_insights" "appi" {
  name                = "${local.name_prefix}-appi"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
  retention_in_days   = 90

  sampling_percentage = 100
  disable_ip_masking  = false

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Log Analytics Solutions
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_solution" "container_insights" {
  solution_name         = "ContainerInsights"
  location              = var.location
  resource_group_name   = azurerm_resource_group.rg.name
  workspace_resource_id = azurerm_log_analytics_workspace.law.id
  workspace_name        = azurerm_log_analytics_workspace.law.name

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/ContainerInsights"
  }

  tags = local.common_tags
}

resource "azurerm_log_analytics_solution" "security_insights" {
  solution_name         = "SecurityInsights"
  location              = var.location
  resource_group_name   = azurerm_resource_group.rg.name
  workspace_resource_id = azurerm_log_analytics_workspace.law.id
  workspace_name        = azurerm_log_analytics_workspace.law.name

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/SecurityInsights"
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Action Group for Alerts
#-------------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "critical" {
  name                = "${local.name_prefix}-ag-critical"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "Critical"

  email_receiver {
    name          = "ai-ops-team"
    email_address = var.apim_publisher_email
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Alert Rules
#-------------------------------------------------------------------------------

# OpenAI - High Latency Alert
resource "azurerm_monitor_metric_alert" "openai_latency" {
  name                = "${local.name_prefix}-alert-aoai-latency"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cognitive_account.openai.id]
  description         = "Alert when Azure OpenAI latency exceeds threshold"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "Latency"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 5000 # 5 seconds
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

# OpenAI - Token Rate Limit Alert
resource "azurerm_monitor_metric_alert" "openai_tokens" {
  name                = "${local.name_prefix}-alert-aoai-tokens"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cognitive_account.openai.id]
  description         = "Alert when Azure OpenAI token usage is high"
  severity            = 3
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "TokenTransaction"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 100000
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

# AI Search - Query Latency Alert
resource "azurerm_monitor_metric_alert" "search_latency" {
  name                = "${local.name_prefix}-alert-search-latency"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_search_service.search.id]
  description         = "Alert when AI Search query latency exceeds threshold"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.Search/searchServices"
    metric_name      = "SearchLatency"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 500 # 500ms
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

# Function App - Error Rate Alert
resource "azurerm_monitor_metric_alert" "fn_errors" {
  name                = "${local.name_prefix}-alert-fn-errors"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_linux_function_app.orchestrator.id]
  description         = "Alert when Function App error rate is high"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

# Cosmos DB - Request Units Alert
resource "azurerm_monitor_metric_alert" "cosmos_ru" {
  name                = "${local.name_prefix}-alert-cosmos-ru"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cosmosdb_account.cosmos.id]
  description         = "Alert when Cosmos DB RU consumption is high"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "TotalRequestUnits"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10000
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

# AKS - Node CPU Alert
resource "azurerm_monitor_metric_alert" "aks_cpu" {
  name                = "${local.name_prefix}-alert-aks-cpu"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when AKS node CPU usage is high"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = local.common_tags
}

#-------------------------------------------------------------------------------
# Log Analytics Saved Searches
#-------------------------------------------------------------------------------
resource "azurerm_log_analytics_saved_search" "openai_requests" {
  name                       = "OpenAI-Request-Analysis"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  category                   = "AI Platform"
  display_name               = "OpenAI Request Analysis"
  query                      = <<QUERY
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
| where Category == "RequestResponse"
| summarize
    TotalRequests = count(),
    AvgDuration = avg(DurationMs),
    ErrorCount = countif(ResultType != "Success")
    by bin(TimeGenerated, 1h)
| order by TimeGenerated desc
QUERY
}

resource "azurerm_log_analytics_saved_search" "search_queries" {
  name                       = "AI-Search-Query-Analysis"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  category                   = "AI Platform"
  display_name               = "AI Search Query Analysis"
  query                      = <<QUERY
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.SEARCH"
| where Category == "OperationLogs"
| summarize
    QueryCount = count(),
    AvgLatency = avg(DurationMs)
    by bin(TimeGenerated, 1h)
| order by TimeGenerated desc
QUERY
}
