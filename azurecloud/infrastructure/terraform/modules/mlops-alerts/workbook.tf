# ============================================================================
# Terraform: Azure Workbook Deployment
# ============================================================================
# Deploys RAG MLOps Observability Workbook using AzAPI provider
# for full JSON template support.
# ============================================================================

terraform {
  required_providers {
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.0"
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "deploy_workbook" {
  description = "Whether to deploy the workbook"
  type        = bool
  default     = true
}

variable "workbook_name" {
  description = "Name for the workbook"
  type        = string
  default     = "rag-mlops-observability"
}

# ============================================================================
# Workbook Content (inline JSON)
# ============================================================================

locals {
  workbook_content = jsonencode({
    "$schema" = "https://github.com/Microsoft/Application-Insights-Workbooks/blob/master/schema/workbook.json"
    version   = "Notebook/1.0"
    items = [
      {
        type = 1
        content = {
          json = "# RAG MLOps Observability Dashboard\n\nComprehensive monitoring for Enterprise RAG Platform."
        }
        name = "header"
      },
      {
        type = 9
        content = {
          version = "KqlParameterItem/1.0"
          parameters = [
            {
              id       = "timeRange"
              version  = "KqlParameterItem/1.0"
              name     = "TimeRange"
              type     = 4
              isRequired = true
              value = {
                durationMs = 86400000
              }
              typeSettings = {
                selectableValues = [
                  { durationMs = 3600000, displayText = "Last hour" },
                  { durationMs = 14400000, displayText = "Last 4 hours" },
                  { durationMs = 86400000, displayText = "Last 24 hours" },
                  { durationMs = 604800000, displayText = "Last 7 days" }
                ]
              }
            }
          ]
        }
        name = "parameters"
      },
      {
        type = 11
        content = {
          version = "LinkItem/1.0"
          style   = "tabs"
          links = [
            { id = "overview", cellValue = "tab", linkTarget = "parameter", linkLabel = "Overview", subTarget = "overview" },
            { id = "latency", cellValue = "tab", linkTarget = "parameter", linkLabel = "Latency", subTarget = "latency" },
            { id = "cost", cellValue = "tab", linkTarget = "parameter", linkLabel = "Cost", subTarget = "cost" },
            { id = "quality", cellValue = "tab", linkTarget = "parameter", linkLabel = "Quality", subTarget = "quality" },
            { id = "safety", cellValue = "tab", linkTarget = "parameter", linkLabel = "Safety", subTarget = "safety" }
          ]
        }
        name = "tabs"
      },
      {
        type = 12
        content = {
          version   = "NotebookGroup/1.0"
          groupType = "editable"
          items = [
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "requests | where url contains '/chat' | summarize total=count(), success_rate=round(countif(success==true)*100.0/count(),1), p95=round(percentile(duration,95),0) | project total, success_rate, p95"
                size    = 4
                title   = "Summary"
                queryType     = 0
                visualization = "tiles"
              }
              name = "summary"
            },
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "requests | where url contains '/chat' | summarize p50=percentile(duration,50), p95=percentile(duration,95), p99=percentile(duration,99) by bin(timestamp, 5m) | render timechart"
                size    = 0
                title   = "Request Latency"
                queryType     = 0
                visualization = "timechart"
              }
              customWidth = "50"
              name        = "latency-chart"
            },
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "requests | summarize success=countif(success==true), failed=countif(success==false) by bin(timestamp, 5m) | render timechart"
                size    = 0
                title   = "Success/Failure"
                queryType     = 0
                visualization = "timechart"
              }
              customWidth = "50"
              name        = "success-chart"
            }
          ]
        }
        conditionalVisibility = {
          parameterName = "tab"
          comparison    = "isEqualTo"
          value         = "overview"
        }
        name = "overview-group"
      },
      {
        type = 12
        content = {
          version   = "NotebookGroup/1.0"
          groupType = "editable"
          items = [
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "traces | where customDimensions.step in ('hybrid_search','openai_completion','embedding') | extend step=tostring(customDimensions.step), latency=toint(customDimensions.latency_ms) | summarize avg(latency), p95=percentile(latency,95) by step, bin(timestamp,5m) | render timechart"
                size    = 0
                title   = "Component Latency"
                queryType     = 0
                visualization = "timechart"
              }
              name = "component-latency"
            }
          ]
        }
        conditionalVisibility = {
          parameterName = "tab"
          comparison    = "isEqualTo"
          value         = "latency"
        }
        name = "latency-group"
      },
      {
        type = 12
        content = {
          version   = "NotebookGroup/1.0"
          groupType = "editable"
          items = [
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "traces | where customDimensions.step=='openai_completion' | extend pt=toint(customDimensions.prompt_tokens), ct=toint(customDimensions.completion_tokens) | summarize prompt=sum(pt), completion=sum(ct) by bin(timestamp,1h) | extend cost=round((prompt/1e6*2.5)+(completion/1e6*10.0),2) | render timechart"
                size    = 0
                title   = "Hourly Cost (USD)"
                queryType     = 0
                visualization = "timechart"
              }
              name = "cost-chart"
            }
          ]
        }
        conditionalVisibility = {
          parameterName = "tab"
          comparison    = "isEqualTo"
          value         = "cost"
        }
        name = "cost-group"
      },
      {
        type = 12
        content = {
          version   = "NotebookGroup/1.0"
          groupType = "editable"
          items = [
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "traces | where customDimensions.event=='online_eval_summary' | extend g=todouble(customDimensions.groundedness_avg), r=todouble(customDimensions.relevance_avg) | summarize avg(g), avg(r) by bin(timestamp,1d) | render timechart"
                size    = 0
                title   = "Quality Metrics"
                queryType     = 0
                visualization = "timechart"
              }
              name = "quality-chart"
            }
          ]
        }
        conditionalVisibility = {
          parameterName = "tab"
          comparison    = "isEqualTo"
          value         = "quality"
        }
        name = "quality-group"
      },
      {
        type = 12
        content = {
          version   = "NotebookGroup/1.0"
          groupType = "editable"
          items = [
            {
              type = 3
              content = {
                version = "KqlItem/1.0"
                query   = "traces | where customDimensions.event=='safety_violation' | extend type=tostring(customDimensions.violation_type) | summarize count() by type, bin(timestamp,1d) | render columnchart"
                size    = 0
                title   = "Safety Violations"
                queryType     = 0
                visualization = "columnchart"
              }
              name = "safety-chart"
            }
          ]
        }
        conditionalVisibility = {
          parameterName = "tab"
          comparison    = "isEqualTo"
          value         = "safety"
        }
        name = "safety-group"
      }
    ]
    fallbackResourceIds = [var.app_insights_id]
  })
}

# ============================================================================
# Workbook Resource (using AzAPI)
# ============================================================================

resource "azapi_resource" "workbook" {
  count = var.deploy_workbook ? 1 : 0

  type      = "Microsoft.Insights/workbooks@2022-04-01"
  name      = "${var.name_prefix}-${var.workbook_name}-${var.environment}"
  location  = var.location
  parent_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"

  body = jsonencode({
    kind = "shared"
    properties = {
      displayName    = "RAG MLOps Observability - ${title(var.environment)}"
      category       = "workbook"
      sourceId       = var.app_insights_id
      serializedData = local.workbook_content
    }
  })

  tags = var.tags
}

# ============================================================================
# Data Sources
# ============================================================================

data "azurerm_client_config" "current" {}

# ============================================================================
# Outputs
# ============================================================================

output "workbook_id" {
  description = "Workbook resource ID"
  value       = var.deploy_workbook ? azapi_resource.workbook[0].id : null
}

output "workbook_name" {
  description = "Workbook name"
  value       = var.deploy_workbook ? "${var.name_prefix}-${var.workbook_name}-${var.environment}" : null
}
