# Production Environment Configuration

environment    = "prod"
project_name   = "genai-copilot"
location       = "eastus2"
location_short = "eus2"

owner_email = "admin@company.com"
cost_center = "AI-Platform-Prod"

# Networking
vnet_address_space = ["10.1.0.0/16"]

# VM Configuration
vm_admin_username = "azureadmin"
vm_size           = "Standard_D4s_v3"  # Larger for prod
vm_count          = 2                   # Multiple VMs for prod

# OpenAI Model Deployments
openai_model_deployments = [
  {
    name          = "gpt-4o"
    model_name    = "gpt-4o"
    model_version = "2024-05-13"
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
    capacity      = 200
  }
]

# Feature Flags
enable_private_endpoints   = true
enable_diagnostic_settings = true
