# Terraform Variables for GenAI Copilot Platform

environment       = "dev"
owner_email       = "pasthana@outlook.com"
vm_admin_password = "P@ssw0rd2024!Secure"

# Japan East - Supports gpt-4o-mini and text-embedding-3-small with good quota
location       = "japaneast"
location_short = "jpe"

# VM settings - try Standard_D2s_v3 as B2s isn't available in Japan East
vm_size  = "Standard_D2s_v3"
vm_count = 1

# Enable AI services for Japan East region
# Note: Azure OpenAI requires quota approval - disabled for now
deploy_openai         = false  # Disabled - no quota for gpt-4o-mini in any region
deploy_functions      = false  # Disabled - no quota for Dynamic VMs in Japan East
deploy_content_safety = false  # Disabled - requires special quota
