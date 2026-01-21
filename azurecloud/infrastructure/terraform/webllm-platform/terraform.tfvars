#===============================================================================
# WebLLM + MLC LLM Platform - Hardcoded Configuration (Japan Region)
#===============================================================================

# Azure Subscription
subscription_id = "8f5bfeb0-c109-428c-98b7-7a9cb5ba6282"

# General Settings
prefix      = "webllm"
environment = "dev"
location    = "japaneast"
location_dr = "japanwest"

# Network Configuration
address_space = ["10.20.0.0/16"]

subnets = {
  app = {
    address_prefix    = "10.20.1.0/24"
    delegation        = "Microsoft.Web/serverFarms"
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
  }
  ai = {
    address_prefix    = "10.20.2.0/24"
    service_endpoints = ["Microsoft.CognitiveServices"]
  }
  data = {
    address_prefix    = "10.20.3.0/24"
    service_endpoints = ["Microsoft.Storage", "Microsoft.AzureCosmosDB"]
  }
  aks = {
    address_prefix    = "10.20.4.0/22"
    service_endpoints = ["Microsoft.ContainerRegistry", "Microsoft.Storage"]
  }
  gpu = {
    address_prefix    = "10.20.8.0/22"
    service_endpoints = ["Microsoft.ContainerRegistry", "Microsoft.Storage"]
  }
  integration = {
    address_prefix = "10.20.12.0/24"
  }
}

# Azure OpenAI Models
openai_deployments = [
  {
    name          = "gpt-4o"
    model_name    = "gpt-4o"
    model_version = "2024-08-06"
    scale_type    = "Standard"
    capacity      = 30
  },
  {
    name          = "gpt-4-vision"
    model_name    = "gpt-4"
    model_version = "vision-preview"
    scale_type    = "Standard"
    capacity      = 10
  },
  {
    name          = "text-embedding-3-large"
    model_name    = "text-embedding-3-large"
    model_version = "1"
    scale_type    = "Standard"
    capacity      = 100
  },
  {
    name          = "whisper"
    model_name    = "whisper"
    model_version = "001"
    scale_type    = "Standard"
    capacity      = 10
  },
  {
    name          = "dall-e-3"
    model_name    = "dall-e-3"
    model_version = "3.0"
    scale_type    = "Standard"
    capacity      = 5
  }
]

# AI Search
search_sku = "basic"

# AKS Configuration
aks_config = {
  kubernetes_version = "1.29"
  system_node_count  = 2
  system_node_size   = "Standard_D4s_v3"
  network_plugin     = "azure"
}

# GPU Node Pools for MLC LLM
gpu_node_pools = [
  {
    name       = "gpua100"
    vm_size    = "Standard_NC24ads_A100_v4"
    node_count = 2
    min_count  = 1
    max_count  = 4
    gpu_type   = "a100"
    labels = {
      "gpu-type" = "a100"
      "workload" = "mlc-llm-large"
    }
    taints = ["nvidia.com/gpu=true:NoSchedule"]
  },
  {
    name       = "gput4"
    vm_size    = "Standard_NC4as_T4_v3"
    node_count = 4
    min_count  = 2
    max_count  = 8
    gpu_type   = "t4"
    labels = {
      "gpu-type" = "t4"
      "workload" = "mlc-llm-small"
    }
    taints = ["nvidia.com/gpu=true:NoSchedule"]
  }
]

# MLC LLM Models to Deploy
mlc_llm_models = [
  {
    name           = "llama-3-1-70b"
    model_id       = "meta-llama/Llama-3.1-70B-Instruct"
    quantization   = "q4f16_1"
    gpu_type       = "a100"
    gpu_count      = 4
    replicas       = 2
    max_batch_size = 32
  },
  {
    name           = "llama-3-1-8b"
    model_id       = "meta-llama/Llama-3.1-8B-Instruct"
    quantization   = "q4f16_1"
    gpu_type       = "t4"
    gpu_count      = 1
    replicas       = 4
    max_batch_size = 64
  },
  {
    name           = "mistral-7b"
    model_id       = "mistralai/Mistral-7B-Instruct-v0.3"
    quantization   = "q4f16_1"
    gpu_type       = "t4"
    gpu_count      = 1
    replicas       = 4
    max_batch_size = 64
  },
  {
    name           = "codellama-34b"
    model_id       = "codellama/CodeLlama-34b-Instruct-hf"
    quantization   = "q4f16_1"
    gpu_type       = "a100"
    gpu_count      = 2
    replicas       = 2
    max_batch_size = 16
  },
  {
    name           = "bge-large-embed"
    model_id       = "BAAI/bge-large-en-v1.5"
    quantization   = "f16"
    gpu_type       = "t4"
    gpu_count      = 1
    replicas       = 8
    max_batch_size = 256
  }
]

# Cosmos DB
cosmos_config = {
  consistency_level = "Session"
  enable_serverless = true
}

# Monitoring
log_retention_days = 30
alert_email        = "ai-ops@company.com"

# Tags
tags = {
  project     = "webllm-mlc-platform"
  region      = "japan"
  cost_center = "ai-platform"
}
