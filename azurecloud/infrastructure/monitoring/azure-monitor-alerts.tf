# =============================================================================
# Azure Monitor Alert Rules for Enterprise Copilot
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# Variables
variable "resource_group_name" {
  type        = string
  description = "Resource group for monitoring resources"
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "environment" {
  type        = string
  description = "Environment (dev, staging, prod)"
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID"
}

variable "app_insights_id" {
  type        = string
  description = "Application Insights resource ID"
}

variable "openai_resource_id" {
  type        = string
  description = "Azure OpenAI resource ID"
}

variable "search_service_id" {
  type        = string
  description = "Azure AI Search resource ID"
}

variable "cosmos_db_id" {
  type        = string
  description = "Cosmos DB account ID"
}

variable "function_app_id" {
  type        = string
  description = "Function App resource ID"
}

variable "action_group_id" {
  type        = string
  description = "Action group for alert notifications"
}

locals {
  alert_prefix = "copilot-${var.environment}"
}

# =============================================================================
# Action Group for Alert Notifications
# =============================================================================

resource "azurerm_monitor_action_group" "copilot_alerts" {
  name                = "ag-${local.alert_prefix}-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "CopilotAG"

  email_receiver {
    name                    = "ops-team"
    email_address           = "copilot-ops@company.com"
    use_common_alert_schema = true
  }

  email_receiver {
    name                    = "oncall"
    email_address           = "oncall@company.com"
    use_common_alert_schema = true
  }

  webhook_receiver {
    name                    = "pagerduty"
    service_uri             = "https://events.pagerduty.com/integration/INTEGRATION_KEY/enqueue"
    use_common_alert_schema = true
  }

  webhook_receiver {
    name                    = "teams"
    service_uri             = "https://outlook.office.com/webhook/WEBHOOK_ID"
    use_common_alert_schema = true
  }

  tags = {
    Environment = var.environment
    Application = "enterprise-copilot"
    Component   = "monitoring"
  }
}

# =============================================================================
# P1 CRITICAL ALERTS - Immediate Response Required
# =============================================================================

# API Total Failure - No successful requests
resource "azurerm_monitor_metric_alert" "api_total_failure" {
  name                = "${local.alert_prefix}-api-total-failure"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_insights_id]
  description         = "P1: Complete API failure - no successful requests in 5 minutes"
  severity            = 0
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/count"
    aggregation      = "Count"
    operator         = "LessThan"
    threshold        = 1

    dimension {
      name     = "request/resultCode"
      operator = "Include"
      values   = ["200", "201", "202", "204"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P1"
    Environment = var.environment
  }
}

# High Error Rate > 10%
resource "azurerm_monitor_metric_alert" "high_error_rate_critical" {
  name                = "${local.alert_prefix}-high-error-rate-critical"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_insights_id]
  description         = "P1: Error rate exceeded 10% - critical service degradation"
  severity            = 0
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P1"
    Environment = var.environment
  }
}

# OpenAI Service Unavailable
resource "azurerm_monitor_metric_alert" "openai_unavailable" {
  name                = "${local.alert_prefix}-openai-unavailable"
  resource_group_name = var.resource_group_name
  scopes              = [var.openai_resource_id]
  description         = "P1: Azure OpenAI service unavailable"
  severity            = 0
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "SuccessfulCalls"
    aggregation      = "Count"
    operator         = "LessThan"
    threshold        = 1
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P1"
    Environment = var.environment
  }
}

# =============================================================================
# P2 HIGH ALERTS - Response within 1 hour
# =============================================================================

# High Latency P95 > 5 seconds
resource "azurerm_monitor_metric_alert" "high_latency_p95" {
  name                = "${local.alert_prefix}-high-latency-p95"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_insights_id]
  description         = "P2: P95 latency exceeded 5 seconds"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/duration"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 5000 # 5 seconds in milliseconds
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P2"
    Environment = var.environment
  }
}

# Error Rate > 2%
resource "azurerm_monitor_metric_alert" "elevated_error_rate" {
  name                = "${local.alert_prefix}-elevated-error-rate"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_insights_id]
  description         = "P2: Error rate exceeded 2%"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 2
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P2"
    Environment = var.environment
  }
}

# OpenAI Rate Limiting (429 errors)
resource "azurerm_monitor_metric_alert" "openai_rate_limited" {
  name                = "${local.alert_prefix}-openai-rate-limited"
  resource_group_name = var.resource_group_name
  scopes              = [var.openai_resource_id]
  description         = "P2: Azure OpenAI rate limiting detected"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "RateLimitedCalls"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P2"
    Environment = var.environment
  }
}

# Cosmos DB RU Consumption High
resource "azurerm_monitor_metric_alert" "cosmos_ru_high" {
  name                = "${local.alert_prefix}-cosmos-ru-high"
  resource_group_name = var.resource_group_name
  scopes              = [var.cosmos_db_id]
  description         = "P2: Cosmos DB RU consumption above 80%"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "NormalizedRUConsumption"
    aggregation      = "Maximum"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P2"
    Environment = var.environment
  }
}

# Search Service Query Latency
resource "azurerm_monitor_metric_alert" "search_latency_high" {
  name                = "${local.alert_prefix}-search-latency-high"
  resource_group_name = var.resource_group_name
  scopes              = [var.search_service_id]
  description         = "P2: AI Search query latency exceeding thresholds"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.Search/searchServices"
    metric_name      = "SearchLatency"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 500 # 500ms
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P2"
    Environment = var.environment
  }
}

# =============================================================================
# P3 MEDIUM ALERTS - Response within 4 hours
# =============================================================================

# Cache Hit Rate Low
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "cache_hit_rate_low" {
  name                = "${local.alert_prefix}-cache-hit-rate-low"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "P3: Cache hit rate below 30%"
  severity            = 2

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT15M"
  window_duration          = "PT1H"
  auto_mitigation_enabled  = true

  criteria {
    query = <<-KQL
      customMetrics
      | where name == "cache_hit_rate"
      | summarize avg_hit_rate = avg(value) by bin(timestamp, 15m)
      | where avg_hit_rate < 30
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "P3"
    Environment = var.environment
  }
}

# Ingestion Pipeline Failures
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "ingestion_failures" {
  name                = "${local.alert_prefix}-ingestion-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "P3: Document ingestion failures detected"
  severity            = 2

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT15M"
  window_duration          = "PT1H"
  auto_mitigation_enabled  = true

  criteria {
    query = <<-KQL
      traces
      | where operation_Name contains "ingestion"
      | where severityLevel >= 3
      | summarize failures = count() by bin(timestamp, 15m)
      | where failures > 5
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "P3"
    Environment = var.environment
  }
}

# Low Retrieval Quality
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "low_retrieval_quality" {
  name                = "${local.alert_prefix}-low-retrieval-quality"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "P3: Retrieval quality metrics below threshold"
  severity            = 2

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT30M"
  window_duration          = "PT2H"
  auto_mitigation_enabled  = true

  criteria {
    query = <<-KQL
      customMetrics
      | where name == "retrieval_ndcg"
      | summarize avg_ndcg = avg(value) by bin(timestamp, 30m)
      | where avg_ndcg < 0.6
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "P3"
    Environment = var.environment
  }
}

# Function App Exceptions
resource "azurerm_monitor_metric_alert" "function_exceptions" {
  name                = "${local.alert_prefix}-function-exceptions"
  resource_group_name = var.resource_group_name
  scopes              = [var.function_app_id]
  description         = "P3: Function App exception count elevated"
  severity            = 2
  frequency           = "PT15M"
  window_size         = "PT1H"
  auto_mitigate       = true

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "FunctionExecutionUnits"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 100
  }

  action {
    action_group_id = azurerm_monitor_action_group.copilot_alerts.id
  }

  tags = {
    Severity    = "P3"
    Environment = var.environment
  }
}

# =============================================================================
# P4 LOW ALERTS - Informational / Next Sprint
# =============================================================================

# Search Index Size Anomaly
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "index_size_anomaly" {
  name                = "${local.alert_prefix}-index-size-anomaly"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "P4: Search index document count anomaly detected"
  severity            = 3

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT1H"
  window_duration          = "PT6H"
  auto_mitigation_enabled  = true

  criteria {
    query = <<-KQL
      AzureMetrics
      | where ResourceProvider == "MICROSOFT.SEARCH"
      | where MetricName == "DocumentCount"
      | summarize doc_count = avg(Average) by bin(TimeGenerated, 1h)
      | extend prev_count = prev(doc_count, 1)
      | where prev_count > 0
      | extend change_pct = (doc_count - prev_count) / prev_count * 100
      | where change_pct < -10 or change_pct > 50
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "P4"
    Environment = var.environment
  }
}

# Token Usage Approaching Quota
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "token_quota_warning" {
  name                = "${local.alert_prefix}-token-quota-warning"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "P4: OpenAI token usage approaching quota limit"
  severity            = 3

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT1H"
  window_duration          = "PT24H"
  auto_mitigation_enabled  = true

  criteria {
    query = <<-KQL
      AzureMetrics
      | where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
      | where MetricName == "TokenTransaction"
      | summarize daily_tokens = sum(Total) by bin(TimeGenerated, 1d)
      | where daily_tokens > 900000  // 90% of 1M daily quota
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "P4"
    Environment = var.environment
  }
}

# =============================================================================
# Security Alerts
# =============================================================================

# Potential RBAC Bypass Attempt
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "rbac_bypass_attempt" {
  name                = "${local.alert_prefix}-rbac-bypass-attempt"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "SECURITY: Potential RBAC bypass attempt detected"
  severity            = 0

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT5M"
  window_duration          = "PT15M"
  auto_mitigation_enabled  = false

  criteria {
    query = <<-KQL
      traces
      | where message contains "unauthorized" or message contains "access denied"
      | where customDimensions.user_id != ""
      | summarize attempts = count() by user_id = tostring(customDimensions.user_id), bin(timestamp, 5m)
      | where attempts > 10
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "Security"
    Environment = var.environment
  }
}

# Unusual Query Pattern
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "unusual_query_pattern" {
  name                = "${local.alert_prefix}-unusual-query-pattern"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "SECURITY: Unusual query pattern detected (potential prompt injection)"
  severity            = 1

  scopes                   = [var.log_analytics_workspace_id]
  evaluation_frequency     = "PT5M"
  window_duration          = "PT15M"
  auto_mitigation_enabled  = false

  criteria {
    query = <<-KQL
      traces
      | where operation_Name == "rag_query"
      | where message contains "ignore" and message contains "instruction"
          or message contains "system prompt"
          or message contains "jailbreak"
      | summarize count() by bin(timestamp, 5m)
    KQL

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.copilot_alerts.id]
  }

  tags = {
    Severity    = "Security"
    Environment = var.environment
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "action_group_id" {
  value       = azurerm_monitor_action_group.copilot_alerts.id
  description = "Action group ID for external references"
}

output "alert_rule_ids" {
  value = {
    api_total_failure    = azurerm_monitor_metric_alert.api_total_failure.id
    high_error_rate      = azurerm_monitor_metric_alert.high_error_rate_critical.id
    openai_unavailable   = azurerm_monitor_metric_alert.openai_unavailable.id
    high_latency         = azurerm_monitor_metric_alert.high_latency_p95.id
    elevated_error_rate  = azurerm_monitor_metric_alert.elevated_error_rate.id
    openai_rate_limited  = azurerm_monitor_metric_alert.openai_rate_limited.id
    cosmos_ru_high       = azurerm_monitor_metric_alert.cosmos_ru_high.id
    search_latency       = azurerm_monitor_metric_alert.search_latency_high.id
    cache_hit_rate_low   = azurerm_monitor_scheduled_query_rules_alert_v2.cache_hit_rate_low.id
    ingestion_failures   = azurerm_monitor_scheduled_query_rules_alert_v2.ingestion_failures.id
    rbac_bypass          = azurerm_monitor_scheduled_query_rules_alert_v2.rbac_bypass_attempt.id
  }
  description = "Alert rule IDs"
}
