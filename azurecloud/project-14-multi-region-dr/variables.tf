variable "subscription_id" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type    = string
  default = "" # if empty, we use the RG location
}

variable "prefix" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

# -----------------------------
# Networking
# -----------------------------
variable "network_mode" {
  type    = string
  default = "private" # "private" or "public"
  validation {
    condition     = contains(["private", "public"], var.network_mode)
    error_message = "network_mode must be either 'private' or 'public'."
  }
}

variable "allowed_ip_ranges" {
  type    = list(string)
  default = []
}

# -----------------------------
# Azure AI Search
# -----------------------------
variable "search_sku" {
  type    = string
  default = "standard"
}

# -----------------------------
# Azure OpenAI deployments (names)
# -----------------------------
variable "gpt4o_chat_deployment_name" {
  type    = string
  default = "gpt4o_chat"
}

variable "gpt4o_mini_caption_deployment_name" {
  type    = string
  default = "gpt4o_mini_caption"
}

variable "embedding_deployment_name" {
  type    = string
  default = "embed_ada002"
}

# -----------------------------
# Azure OpenAI models (name + version)
# IMPORTANT: Versions MUST match your region/account list.
# -----------------------------
variable "gpt4o_chat_model_name" {
  type    = string
  default = "gpt-4o"
}

variable "gpt4o_chat_model_version" {
  type = string
}

variable "gpt4o_mini_model_name" {
  type    = string
  default = "gpt-4o-mini"
}

variable "gpt4o_mini_model_version" {
  type = string
}

variable "embedding_model_name" {
  type    = string
  default = "text-embedding-3-large"
}

variable "embedding_model_version" {
  type = string
}
