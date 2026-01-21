# Governance Module - RAG Platform Phase 10
# Provides infrastructure for policy enforcement, auditing, and model lifecycle management

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.85.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Cosmos DB Containers for Governance
# -----------------------------------------------------------------------------
resource "azurerm_cosmosdb_sql_container" "policy_store" {
  name                  = "policy_store"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/tenant_id"
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }

  default_ttl = -1

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }
}

resource "azurerm_cosmosdb_sql_container" "audit_findings" {
  name                  = "audit_findings"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/tenant_id"
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    composite_index {
      index {
        path  = "/tenant_id"
        order = "Ascending"
      }
      index {
        path  = "/timestamp"
        order = "Descending"
      }
    }

    composite_index {
      index {
        path  = "/severity"
        order = "Ascending"
      }
      index {
        path  = "/status"
        order = "Ascending"
      }
    }
  }

  default_ttl = 7776000 # 90 days retention
}

resource "azurerm_cosmosdb_sql_container" "model_registry" {
  name                  = "model_registry"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/model_id"
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    composite_index {
      index {
        path  = "/model_id"
        order = "Ascending"
      }
      index {
        path  = "/version"
        order = "Descending"
      }
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "model_evaluations" {
  name                  = "model_evaluations"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/model_version"
  partition_key_version = 2

  default_ttl = 15552000 # 180 days retention
}

resource "azurerm_cosmosdb_sql_container" "canary_deployments" {
  name                  = "canary_deployments"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/model_id"
  partition_key_version = 2
}

resource "azurerm_cosmosdb_sql_container" "model_baselines" {
  name                  = "model_baselines"
  resource_group_name   = var.resource_group_name
  account_name          = var.cosmos_account_name
  database_name         = var.cosmos_database_name
  partition_key_path    = "/model_id"
  partition_key_version = 2
}

# -----------------------------------------------------------------------------
# Event Grid Topic for Governance Events
# -----------------------------------------------------------------------------
resource "azurerm_eventgrid_topic" "governance" {
  name                = "${var.name_prefix}-governance-events"
  location            = var.location
  resource_group_name = var.resource_group_name

  input_schema = "EventGridSchema"

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Service Bus for Async Governance Operations
# -----------------------------------------------------------------------------
resource "azurerm_servicebus_namespace" "governance" {
  name                = "${var.name_prefix}-governance-sb"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.servicebus_sku

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_servicebus_queue" "policy_evaluation" {
  name         = "policy-evaluation"
  namespace_id = azurerm_servicebus_namespace.governance.id

  max_delivery_count = 10
  default_message_ttl = "P14D"
  lock_duration       = "PT5M"

  enable_partitioning = true
  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_queue" "audit_processing" {
  name         = "audit-processing"
  namespace_id = azurerm_servicebus_namespace.governance.id

  max_delivery_count = 5
  default_message_ttl = "P7D"
  lock_duration       = "PT5M"

  enable_partitioning = true
  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_queue" "model_lifecycle" {
  name         = "model-lifecycle"
  namespace_id = azurerm_servicebus_namespace.governance.id

  max_delivery_count = 3
  default_message_ttl = "P1D"
  lock_duration       = "PT10M"

  dead_lettering_on_message_expiration = true
}

# -----------------------------------------------------------------------------
# Azure Monitor Alerts for Governance
# -----------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "governance_alerts" {
  name                = "${var.name_prefix}-governance-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "GovAlerts"

  email_receiver {
    name          = "governance-team"
    email_address = var.governance_alert_email
  }

  dynamic "webhook_receiver" {
    for_each = var.governance_webhook_url != "" ? [1] : []
    content {
      name        = "teams-webhook"
      service_uri = var.governance_webhook_url
    }
  }

  tags = var.tags
}

resource "azurerm_monitor_metric_alert" "critical_policy_violations" {
  name                = "${var.name_prefix}-critical-violations"
  resource_group_name = var.resource_group_name
  scopes              = [var.log_analytics_workspace_id]
  description         = "Alert when critical policy violations exceed threshold"

  enabled   = true
  frequency = "PT5M"
  window_size = "PT15M"

  criteria {
    metric_namespace = "Microsoft.OperationalInsights/workspaces"
    metric_name      = "CustomMetric"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 5

    dimension {
      name     = "severity"
      operator = "Include"
      values   = ["critical"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.governance_alerts.id
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Logic App for Approval Workflows
# -----------------------------------------------------------------------------
resource "azurerm_logic_app_workflow" "model_promotion_approval" {
  name                = "${var.name_prefix}-model-approval"
  location            = var.location
  resource_group_name = var.resource_group_name

  identity {
    type = "SystemAssigned"
  }

  workflow_parameters = {
    "$connections" = jsonencode({
      defaultValue = {}
      type         = "Object"
    })
  }

  tags = var.tags
}

resource "azurerm_logic_app_workflow" "policy_exception_approval" {
  name                = "${var.name_prefix}-policy-exception"
  location            = var.location
  resource_group_name = var.resource_group_name

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "eventgrid_topic_endpoint" {
  value = azurerm_eventgrid_topic.governance.endpoint
}

output "servicebus_namespace" {
  value = azurerm_servicebus_namespace.governance.name
}

output "servicebus_connection_string" {
  value     = azurerm_servicebus_namespace.governance.default_primary_connection_string
  sensitive = true
}

output "action_group_id" {
  value = azurerm_monitor_action_group.governance_alerts.id
}
