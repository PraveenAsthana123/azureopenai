# =============================================================================
# Staging Environment Configuration
# =============================================================================

environment   = "staging"
project_name  = "aoai"
location      = "eastus2"
openai_location = "eastus2"

owner_email         = "admin@example.com"
cost_center         = "AI-Platform-Staging"
data_classification = "Internal"

# Networking
vnet_address_space = ["10.0.0.0/16"]
enable_bastion     = false

# Alert recipients
alert_email_addresses = [
  "devops@example.com"
]

# Azure AD Groups (replace with actual object IDs)
admin_group_object_ids     = []
developer_group_object_ids = []

# OpenAI Deployments - Staging (mirrors prod)
openai_deployments = [
  {
    name          = "gpt-4o"
    model_name    = "gpt-4o"
    model_version = "2024-08-06"
    capacity      = 20
  },
  {
    name          = "gpt-4o-mini"
    model_name    = "gpt-4o-mini"
    model_version = "2024-07-18"
    capacity      = 30
  },
  {
    name          = "text-embedding-3-large"
    model_name    = "text-embedding-3-large"
    model_version = "1"
    capacity      = 30
  }
]

# AKS
aks_kubernetes_version = "1.29"
