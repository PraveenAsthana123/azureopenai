subscription_id = "8f5bfeb0-c109-428c-98b7-7a9cb5ba6282"
tenant_id       = "dcc27d5a-fc17-45ca-8278-ce105af5f330"

resource_group_name = "rg-pasthana-1557"
location            = "eastus2"
prefix              = "pasthrag"
# Note: Random integer will use state value for consistency

# Networking
network_mode      = "private"
allowed_ip_ranges = []

# Azure Search
search_sku = "standard"

# Azure OpenAI deployment names
gpt4o_chat_deployment_name         = "gpt4o_chat"
gpt4o_mini_caption_deployment_name = "gpt4o_mini_caption"
embedding_deployment_name          = "embed_ada002"

# Azure OpenAI model names
gpt4o_chat_model_name  = "gpt-4o"
gpt4o_mini_model_name  = "gpt-4o-mini"
embedding_model_name   = "text-embedding-3-large"

# REQUIRED — Model versions from available models in eastus2
gpt4o_chat_model_version  = "2024-08-06"
gpt4o_mini_model_version  = "2024-07-18"
embedding_model_version   = "1"
