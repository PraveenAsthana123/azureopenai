# =============================================================================
# Production Environment Configuration
# =============================================================================

environment   = "prod"
project_name  = "aoai"
location      = "eastus2"
openai_location = "eastus2"

owner_email         = "admin@example.com"
cost_center         = "AI-Platform-Prod"
data_classification = "Confidential"

# Networking
vnet_address_space = ["10.0.0.0/16"]
enable_bastion     = true

# Alert recipients
alert_email_addresses = [
  "devops@example.com",
  "oncall@example.com",
  "security@example.com"
]

# Azure AD Groups (replace with actual object IDs)
admin_group_object_ids     = []
developer_group_object_ids = []

# OpenAI Deployments - Production scale
openai_deployments = [
  {
    name          = "gpt-4o"
    model_name    = "gpt-4o"
    model_version = "2024-08-06"
    capacity      = 50
  },
  {
    name          = "gpt-4o-mini"
    model_name    = "gpt-4o-mini"
    model_version = "2024-07-18"
    capacity      = 100
  },
  {
    name          = "text-embedding-3-large"
    model_name    = "text-embedding-3-large"
    model_version = "1"
    capacity      = 100
  }
]

# AKS - Production config
aks_kubernetes_version = "1.29"
