#===============================================================================
# Enterprise AI Platform - Hardcoded Configuration for Japan Region
#===============================================================================

# General Settings
prefix      = "ent-ai"
environment = "dev"
location    = "japaneast"
location_dr = "japanwest"

# Network Configuration
address_space = ["10.10.0.0/16"]
subnets = {
  app         = "10.10.1.0/24"
  ai          = "10.10.2.0/24"
  search      = "10.10.3.0/24"
  data        = "10.10.4.0/24"
  compute     = "10.10.5.0/24"
  integration = "10.10.6.0/24"
  firewall    = "10.10.7.0/24"
}

# Azure OpenAI Configuration
openai_sku = "S0"
openai_deployments = [
  {
    name          = "gpt-4o"
    model_name    = "gpt-4o"
    model_version = "2024-05-13"
    scale_type    = "Standard"
    capacity      = 10
  },
  {
    name          = "text-embedding-3-large"
    model_name    = "text-embedding-3-large"
    model_version = "1"
    scale_type    = "Standard"
    capacity      = 50
  }
]

# AI Search Configuration
search_sku             = "basic"
search_replica_count   = 1
search_partition_count = 1

# Database Configuration
cosmos_consistency_level = "Session"
cosmos_enable_serverless = true
sql_admin_login          = "sqladminuser"
sql_admin_password       = "P@ssw0rd2026!Secure#Japan"
sql_sku                  = "S0"

# Compute Configuration
aks_node_count = 2
aks_node_size  = "Standard_DS2_v2"
function_sku   = "EP1"

# APIM Configuration
apim_sku             = "Developer_1"
apim_publisher_name  = "Enterprise AI Platform"
apim_publisher_email = "ai-admin@enterprise.com"

# Monitoring Configuration
log_retention_days = 30

# Tags
tags = {
  project     = "enterprise-ai-platform"
  env         = "dev"
  owner       = "ai-arch"
  cost_center = "ai-platform"
  managed_by  = "terraform"
  region      = "japan"
}
