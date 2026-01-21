# ============================================================================
# Terraform Module: RAG MLOps Alerts
# ============================================================================
# Deploys Azure Monitor alert rules for RAG platform:
# - Latency alerts
# - Error rate alerts
# - Cost budget alerts
# - Quality (groundedness) alerts
# - User satisfaction alerts
# - Safety violation alerts
# ============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "rag"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_insights_id" {
  description = "Application Insights resource ID"
  type        = string
}

variable "alert_email_addresses" {
  description = "Email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "daily_cost_budget_usd" {
  description = "Daily cost budget in USD"
  type        = number
  default     = 100
}

variable "latency_threshold_ms" {
  description = "P95 latency threshold in milliseconds"
  type        = number
  default     = 5000
}

variable "error_rate_threshold_percent" {
  description = "Error rate threshold percentage"
  type        = number
  default     = 5
}

variable "groundedness_threshold" {
  description = "Groundedness threshold (0-1)"
  type        = number
  default     = 0.8
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}

# ============================================================================
# Action Group
# ============================================================================

resource "azurerm_monitor_action_group" "rag_ops" {
  name                = "${var.name_prefix}-ops-alerts-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "ragops"

  dynamic "email_receiver" {
    for_each = var.alert_email_addresses
    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  dynamic "webhook_receiver" {
    for_each = var.slack_webhook_url != "" ? [1] : []
    content {
      name                    = "slack"
      service_uri             = var.slack_webhook_url
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

# ============================================================================
# Alert: High P95 Latency
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_latency" {
  name                = "${var.name_prefix}-high-latency-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "RAG API P95 latency exceeded ${var.latency_threshold_ms}ms"
  severity            = 2
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      requests
      | where url contains "/chat" or url contains "/query"
      | summarize p95 = percentile(duration, 95) by bin(timestamp, 5m)
      | where p95 > ${var.latency_threshold_ms}
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 2
      number_of_evaluation_periods             = 3
    }
  }

  auto_mitigation_enabled = true

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: High Error Rate
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_error_rate" {
  name                = "${var.name_prefix}-error-rate-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "RAG API error rate exceeded ${var.error_rate_threshold_percent}%"
  severity            = 1
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      requests
      | where timestamp > ago(15m)
      | summarize errors = countif(success == false), total = count()
      | extend error_rate = todouble(errors) / total * 100
      | where error_rate > ${var.error_rate_threshold_percent}
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = true

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: Daily Cost Budget
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "cost_budget" {
  name                = "${var.name_prefix}-cost-budget-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Daily token cost exceeded $${var.daily_cost_budget_usd}"
  severity            = 2
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT1H"
  window_duration      = "P1D"

  criteria {
    query = <<-KQL
      traces
      | where customDimensions.step == "openai_completion"
      | where timestamp > ago(1d)
      | extend pt = toint(customDimensions.prompt_tokens), ct = toint(customDimensions.completion_tokens)
      | summarize cost = sum(pt / 1000000.0 * 2.5 + ct / 1000000.0 * 10.0)
      | where cost > ${var.daily_cost_budget_usd}
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = false

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: Groundedness Drop (Quality)
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "groundedness" {
  name                = "${var.name_prefix}-groundedness-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "RAG groundedness dropped below ${var.groundedness_threshold}"
  severity            = 2
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT1H"
  window_duration      = "P1D"

  criteria {
    query = <<-KQL
      traces
      | where customDimensions.event == "online_eval_summary"
      | where timestamp > ago(1d)
      | extend g = todouble(customDimensions.groundedness_avg)
      | summarize avg_g = avg(g)
      | where avg_g < ${var.groundedness_threshold}
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = false

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: User Dissatisfaction
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "dissatisfaction" {
  name                = "${var.name_prefix}-dissatisfaction-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "User dissatisfaction rate exceeded 20%"
  severity            = 3
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT6H"
  window_duration      = "P1D"

  criteria {
    query = <<-KQL
      traces
      | where customDimensions.event == "user_feedback"
      | where timestamp > ago(1d)
      | extend rating = tostring(customDimensions.rating)
      | summarize down = countif(rating == "down"), total = count()
      | extend rate = todouble(down) / total * 100
      | where rate > 20
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = false

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: Safety Violations
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "safety" {
  name                = "${var.name_prefix}-safety-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Multiple safety violations detected"
  severity            = 1
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query = <<-KQL
      traces
      | where customDimensions.event == "safety_violation"
      | where timestamp > ago(1h)
      | summarize violations = count()
      | where violations > 5
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = false

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Alert: Retrieval Drift
# ============================================================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "retrieval_drift" {
  name                = "${var.name_prefix}-retrieval-drift-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Retrieval score drift detected (>15% drop)"
  severity            = 3
  enabled             = true

  scopes               = [var.app_insights_id]
  evaluation_frequency = "PT6H"
  window_duration      = "P1D"

  criteria {
    query = <<-KQL
      traces
      | where customDimensions.step == "hybrid_search"
      | where timestamp > ago(1d)
      | extend score = todouble(customDimensions.top_score)
      | summarize current_avg = avg(score)
      | extend baseline = 0.7
      | extend drop = (baseline - current_avg) / baseline * 100
      | where drop > 15
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = false

  action {
    action_groups = [azurerm_monitor_action_group.rag_ops.id]
  }

  tags = var.tags
}

# ============================================================================
# Outputs
# ============================================================================

output "action_group_id" {
  description = "Action group ID"
  value       = azurerm_monitor_action_group.rag_ops.id
}

output "alert_rule_ids" {
  description = "Map of alert rule IDs"
  value = {
    high_latency    = azurerm_monitor_scheduled_query_rules_alert_v2.high_latency.id
    error_rate      = azurerm_monitor_scheduled_query_rules_alert_v2.high_error_rate.id
    cost_budget     = azurerm_monitor_scheduled_query_rules_alert_v2.cost_budget.id
    groundedness    = azurerm_monitor_scheduled_query_rules_alert_v2.groundedness.id
    dissatisfaction = azurerm_monitor_scheduled_query_rules_alert_v2.dissatisfaction.id
    safety          = azurerm_monitor_scheduled_query_rules_alert_v2.safety.id
    retrieval_drift = azurerm_monitor_scheduled_query_rules_alert_v2.retrieval_drift.id
  }
}
