#===============================================================================
# WebLLM + MLC LLM Platform - Variables
#===============================================================================

#-------------------------------------------------------------------------------
# General Settings
#-------------------------------------------------------------------------------
variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "prefix" {
  description = "Resource naming prefix"
  type        = string
  default     = "webllm"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "japaneast"
}

variable "location_dr" {
  description = "DR Azure region"
  type        = string
  default     = "japanwest"
}

#-------------------------------------------------------------------------------
# Network Configuration
#-------------------------------------------------------------------------------
variable "address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.20.0.0/16"]
}

variable "subnets" {
  description = "Subnet configurations"
  type        = map(object({
    address_prefix = string
    delegation     = optional(string)
    service_endpoints = optional(list(string))
  }))
  default = {
    app = {
      address_prefix = "10.20.1.0/24"
      delegation     = "Microsoft.Web/serverFarms"
      service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault"]
    }
    ai = {
      address_prefix = "10.20.2.0/24"
      service_endpoints = ["Microsoft.CognitiveServices"]
    }
    data = {
      address_prefix = "10.20.3.0/24"
      service_endpoints = ["Microsoft.Storage", "Microsoft.AzureCosmosDB"]
    }
    aks = {
      address_prefix = "10.20.4.0/22"
      service_endpoints = ["Microsoft.ContainerRegistry", "Microsoft.Storage"]
    }
    gpu = {
      address_prefix = "10.20.8.0/22"
      service_endpoints = ["Microsoft.ContainerRegistry", "Microsoft.Storage"]
    }
    integration = {
      address_prefix = "10.20.12.0/24"
    }
  }
}

#-------------------------------------------------------------------------------
# Azure OpenAI Configuration
#-------------------------------------------------------------------------------
variable "openai_deployments" {
  description = "Azure OpenAI model deployments"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    scale_type    = string
    capacity      = number
  }))
  default = [
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
}

#-------------------------------------------------------------------------------
# AI Search Configuration
#-------------------------------------------------------------------------------
variable "search_sku" {
  description = "AI Search SKU"
  type        = string
  default     = "basic"
}

#-------------------------------------------------------------------------------
# AKS Configuration
#-------------------------------------------------------------------------------
variable "aks_config" {
  description = "AKS cluster configuration"
  type = object({
    kubernetes_version = string
    system_node_count  = number
    system_node_size   = string
    network_plugin     = string
  })
  default = {
    kubernetes_version = "1.29"
    system_node_count  = 2
    system_node_size   = "Standard_D4s_v3"
    network_plugin     = "azure"
  }
}

variable "gpu_node_pools" {
  description = "GPU node pools for MLC LLM"
  type = list(object({
    name         = string
    vm_size      = string
    node_count   = number
    min_count    = number
    max_count    = number
    gpu_type     = string
    labels       = map(string)
    taints       = list(string)
  }))
  default = [
    {
      name       = "gpua100"
      vm_size    = "Standard_NC24ads_A100_v4"
      node_count = 2
      min_count  = 1
      max_count  = 4
      gpu_type   = "a100"
      labels = {
        "gpu-type"    = "a100"
        "workload"    = "mlc-llm-large"
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
        "gpu-type"    = "t4"
        "workload"    = "mlc-llm-small"
      }
      taints = ["nvidia.com/gpu=true:NoSchedule"]
    }
  ]
}

#-------------------------------------------------------------------------------
# MLC LLM Models Configuration
#-------------------------------------------------------------------------------
variable "mlc_llm_models" {
  description = "MLC LLM models to deploy"
  type = list(object({
    name           = string
    model_id       = string
    quantization   = string
    gpu_type       = string
    gpu_count      = number
    replicas       = number
    max_batch_size = number
  }))
  default = [
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
      name           = "qwen2-72b"
      model_id       = "Qwen/Qwen2-72B-Instruct"
      quantization   = "q4f16_1"
      gpu_type       = "a100"
      gpu_count      = 4
      replicas       = 2
      max_batch_size = 32
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
}

#-------------------------------------------------------------------------------
# Cosmos DB Configuration
#-------------------------------------------------------------------------------
variable "cosmos_config" {
  description = "Cosmos DB configuration"
  type = object({
    consistency_level  = string
    enable_serverless  = bool
  })
  default = {
    consistency_level  = "Session"
    enable_serverless  = true
  }
}

#-------------------------------------------------------------------------------
# Monitoring Configuration
#-------------------------------------------------------------------------------
variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Email for alerts"
  type        = string
  default     = "ai-ops@company.com"
}

#-------------------------------------------------------------------------------
# Tags
#-------------------------------------------------------------------------------
variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
