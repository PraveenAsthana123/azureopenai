#!/usr/bin/env bash
###############################################################################
# Enterprise Copilot - Terraform Configuration Generator
#
# Reads terraform-inputs.json and generates complete Terraform modules and
# environment configurations.
#
# Prerequisites:
#   - Run collect-terraform-inputs.sh first to generate terraform-inputs.json
#   - jq installed
#
# Usage:
#   ./generate-terraform-config.sh [terraform-inputs.json]
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Input file
INPUT_FILE="${1:-terraform-inputs.json}"

# Output directory
OUTPUT_DIR="${OUTPUT_DIR:-./generated-terraform}"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

jq_read() {
    jq -r "$1" "$INPUT_FILE"
}

###############################################################################
# Validate Input
###############################################################################

print_header "Enterprise Copilot - Terraform Generator"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}Error: Input file not found: $INPUT_FILE${NC}"
    echo "Run collect-terraform-inputs.sh first to generate the input file."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    exit 1
fi

echo "Reading configuration from: $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Read key values
PROJECT_PREFIX=$(jq_read '.general.project_prefix')
DEFAULT_REGION=$(jq_read '.general.default_region')
SUB_ID=$(jq_read '.subscription.id')
TENANT_ID=$(jq_read '.subscription.tenant_id')

echo "Project Prefix: $PROJECT_PREFIX"
echo "Region: $DEFAULT_REGION"
echo ""

###############################################################################
# Create Directory Structure
###############################################################################

print_header "Creating Directory Structure"

mkdir -p "$OUTPUT_DIR"/{modules/{networking,security,openai,search,storage,cosmos,functions,monitoring},environments/{dev,staging,prod}}

print_step "Created modules directories"
print_step "Created environment directories"

###############################################################################
# Generate Main Variables File
###############################################################################

print_header "Generating variables.tf"

cat > "$OUTPUT_DIR/variables.tf" << 'EOF'
# =============================================================================
# Enterprise Copilot - Root Variables
# =============================================================================

variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
}

variable "tenant_id" {
  type        = string
  description = "Azure Tenant ID"
}

variable "default_region" {
  type        = string
  description = "Default Azure region for resources"
}

variable "project_prefix" {
  type        = string
  description = "Project prefix for resource naming"
}

variable "org_name" {
  type        = string
  description = "Organization name"
  default     = ""
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "default_tags" {
  type        = map(string)
  description = "Default tags for all resources"
  default     = {}
}

# Networking
variable "create_new_vnet" {
  type        = bool
  description = "Create new VNet or use existing"
  default     = true
}

variable "vnet_address_space" {
  type        = string
  description = "VNet address space CIDR"
  default     = "10.100.0.0/16"
}

variable "subnets" {
  type = map(object({
    cidr              = string
    service_endpoints = optional(list(string), [])
    delegation        = optional(object({
      name    = string
      service = string
      actions = list(string)
    }))
  }))
  description = "Subnet configurations"
  default     = {}
}

variable "create_private_dns_zones" {
  type        = bool
  description = "Create private DNS zones"
  default     = true
}

# Security
variable "create_ad_groups" {
  type        = bool
  description = "Create Entra ID groups"
  default     = true
}

variable "key_vault_config" {
  type = object({
    purge_protection_enabled   = bool
    soft_delete_retention_days = number
    sku_name                   = string
  })
  description = "Key Vault configuration"
  default = {
    purge_protection_enabled   = false
    soft_delete_retention_days = 7
    sku_name                   = "standard"
  }
}

# OpenAI
variable "openai_account_name" {
  type        = string
  description = "Azure OpenAI account name"
}

variable "openai_sku" {
  type        = string
  description = "Azure OpenAI SKU"
  default     = "S0"
}

variable "openai_deployments" {
  type = map(object({
    model_name    = string
    model_version = string
    capacity      = number
    sku_name      = string
  }))
  description = "OpenAI model deployments"
}

# AI Search
variable "search_service_name" {
  type        = string
  description = "AI Search service name"
}

variable "search_config" {
  type = map(object({
    sku        = string
    replicas   = number
    partitions = number
  }))
  description = "Search configuration per environment"
}

variable "search_semantic_enabled" {
  type        = bool
  description = "Enable semantic ranker"
  default     = true
}

# Storage
variable "storage_account_prefix" {
  type        = string
  description = "Storage account name prefix"
}

variable "storage_containers" {
  type        = list(string)
  description = "Storage containers to create"
  default     = ["raw-documents", "processed-documents", "chunks"]
}

# Add-ons
variable "deploy_cosmos_db" {
  type        = bool
  description = "Deploy Cosmos DB"
  default     = true
}

variable "deploy_data_factory" {
  type        = bool
  description = "Deploy Data Factory"
  default     = true
}

variable "deploy_functions" {
  type        = bool
  description = "Deploy Azure Functions"
  default     = true
}

variable "deploy_apim" {
  type        = bool
  description = "Deploy API Management"
  default     = false
}

# Observability
variable "log_analytics_name" {
  type        = string
  description = "Log Analytics workspace name"
}

variable "app_insights_name" {
  type        = string
  description = "Application Insights name"
}

variable "log_retention_days" {
  type        = number
  description = "Log retention in days"
  default     = 30
}
EOF

print_success "Generated variables.tf"

###############################################################################
# Generate Main Terraform File
###############################################################################

print_header "Generating main.tf"

cat > "$OUTPUT_DIR/main.tf" << 'EOF'
# =============================================================================
# Enterprise Copilot - Main Terraform Configuration
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = !var.key_vault_config.purge_protection_enabled
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

provider "azuread" {
  tenant_id = var.tenant_id
}

# -----------------------------------------------------------------------------
# Local Values
# -----------------------------------------------------------------------------

locals {
  resource_prefix = "${var.project_prefix}-${var.environment}"
  common_tags = merge(var.default_tags, {
    environment = var.environment
    managed_by  = "terraform"
    project     = var.project_prefix
  })
}

# -----------------------------------------------------------------------------
# Resource Groups
# -----------------------------------------------------------------------------

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.default_region
  tags     = local.common_tags
}

resource "azurerm_resource_group" "networking" {
  name     = "rg-${local.resource_prefix}-network"
  location = var.default_region
  tags     = local.common_tags
}

resource "azurerm_resource_group" "security" {
  name     = "rg-${local.resource_prefix}-security"
  location = var.default_region
  tags     = local.common_tags
}

resource "azurerm_resource_group" "data" {
  name     = "rg-${local.resource_prefix}-data"
  location = var.default_region
  tags     = local.common_tags
}

# -----------------------------------------------------------------------------
# Networking Module
# -----------------------------------------------------------------------------

module "networking" {
  source = "./modules/networking"

  resource_group_name  = azurerm_resource_group.networking.name
  location             = var.default_region
  resource_prefix      = local.resource_prefix
  create_new_vnet      = var.create_new_vnet
  vnet_address_space   = var.vnet_address_space
  subnets              = var.subnets
  create_private_dns   = var.create_private_dns_zones
  tags                 = local.common_tags
}

# -----------------------------------------------------------------------------
# Security Module (Key Vault)
# -----------------------------------------------------------------------------

module "security" {
  source = "./modules/security"

  resource_group_name = azurerm_resource_group.security.name
  location            = var.default_region
  resource_prefix     = local.resource_prefix
  tenant_id           = var.tenant_id
  key_vault_config    = var.key_vault_config
  subnet_id           = module.networking.subnet_ids["private-endpoints"]
  private_dns_zone_id = module.networking.private_dns_zone_ids["vault"]
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Azure OpenAI Module
# -----------------------------------------------------------------------------

module "openai" {
  source = "./modules/openai"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.default_region
  account_name        = var.openai_account_name
  sku                 = var.openai_sku
  deployments         = var.openai_deployments
  subnet_id           = module.networking.subnet_ids["private-endpoints"]
  private_dns_zone_id = module.networking.private_dns_zone_ids["openai"]
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# AI Search Module
# -----------------------------------------------------------------------------

module "search" {
  source = "./modules/search"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.default_region
  service_name        = var.search_service_name
  environment         = var.environment
  search_config       = var.search_config
  semantic_enabled    = var.search_semantic_enabled
  subnet_id           = module.networking.subnet_ids["private-endpoints"]
  private_dns_zone_id = module.networking.private_dns_zone_ids["search"]
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Storage Module
# -----------------------------------------------------------------------------

module "storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.data.name
  location            = var.default_region
  account_prefix      = var.storage_account_prefix
  environment         = var.environment
  containers          = var.storage_containers
  subnet_id           = module.networking.subnet_ids["private-endpoints"]
  private_dns_zone_id = module.networking.private_dns_zone_ids["blob"]
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Cosmos DB Module (Optional)
# -----------------------------------------------------------------------------

module "cosmos" {
  count  = var.deploy_cosmos_db ? 1 : 0
  source = "./modules/cosmos"

  resource_group_name = azurerm_resource_group.data.name
  location            = var.default_region
  resource_prefix     = local.resource_prefix
  subnet_id           = module.networking.subnet_ids["private-endpoints"]
  private_dns_zone_id = module.networking.private_dns_zone_ids["cosmos"]
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Monitoring Module
# -----------------------------------------------------------------------------

module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.default_region
  log_analytics_name  = var.log_analytics_name
  app_insights_name   = var.app_insights_name
  retention_days      = var.log_retention_days
  tags                = local.common_tags
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "resource_group_names" {
  value = {
    main       = azurerm_resource_group.main.name
    networking = azurerm_resource_group.networking.name
    security   = azurerm_resource_group.security.name
    data       = azurerm_resource_group.data.name
  }
}

output "openai_endpoint" {
  value     = module.openai.endpoint
  sensitive = true
}

output "search_endpoint" {
  value = module.search.endpoint
}

output "storage_account_name" {
  value = module.storage.account_name
}

output "key_vault_uri" {
  value = module.security.key_vault_uri
}

output "app_insights_connection_string" {
  value     = module.monitoring.connection_string
  sensitive = true
}
EOF

print_success "Generated main.tf"

###############################################################################
# Generate Networking Module
###############################################################################

print_header "Generating Networking Module"

cat > "$OUTPUT_DIR/modules/networking/main.tf" << 'EOF'
# =============================================================================
# Networking Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "resource_prefix" { type = string }
variable "create_new_vnet" { type = bool }
variable "vnet_address_space" { type = string }
variable "subnets" { type = any }
variable "create_private_dns" { type = bool }
variable "tags" { type = map(string) }

# VNet
resource "azurerm_virtual_network" "main" {
  count               = var.create_new_vnet ? 1 : 0
  name                = "vnet-${var.resource_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.vnet_address_space]
  tags                = var.tags
}

# Subnets
resource "azurerm_subnet" "subnets" {
  for_each             = var.subnets
  name                 = "snet-${each.key}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = var.create_new_vnet ? azurerm_virtual_network.main[0].name : ""
  address_prefixes     = [each.value.cidr]
  service_endpoints    = lookup(each.value, "service_endpoints", [])

  dynamic "delegation" {
    for_each = lookup(each.value, "delegation", null) != null ? [each.value.delegation] : []
    content {
      name = delegation.value.name
      service_delegation {
        name    = delegation.value.service
        actions = delegation.value.actions
      }
    }
  }
}

# Private DNS Zones
locals {
  dns_zones = var.create_private_dns ? {
    openai  = "privatelink.openai.azure.com"
    search  = "privatelink.search.windows.net"
    blob    = "privatelink.blob.core.windows.net"
    vault   = "privatelink.vaultcore.azure.net"
    cosmos  = "privatelink.documents.azure.com"
    web     = "privatelink.azurewebsites.net"
  } : {}
}

resource "azurerm_private_dns_zone" "zones" {
  for_each            = local.dns_zones
  name                = each.value
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "links" {
  for_each              = local.dns_zones
  name                  = "link-${each.key}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.zones[each.key].name
  virtual_network_id    = var.create_new_vnet ? azurerm_virtual_network.main[0].id : ""
  registration_enabled  = false
  tags                  = var.tags
}

# Outputs
output "vnet_id" {
  value = var.create_new_vnet ? azurerm_virtual_network.main[0].id : ""
}

output "subnet_ids" {
  value = { for k, v in azurerm_subnet.subnets : k => v.id }
}

output "private_dns_zone_ids" {
  value = { for k, v in azurerm_private_dns_zone.zones : k => v.id }
}
EOF

print_success "Generated modules/networking/main.tf"

###############################################################################
# Generate OpenAI Module
###############################################################################

print_header "Generating OpenAI Module"

cat > "$OUTPUT_DIR/modules/openai/main.tf" << 'EOF'
# =============================================================================
# Azure OpenAI Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "account_name" { type = string }
variable "sku" { type = string }
variable "deployments" { type = any }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_cognitive_account" "openai" {
  name                          = var.account_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = var.sku
  custom_subdomain_name         = var.account_name
  public_network_access_enabled = false
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "deployments" {
  for_each             = var.deployments
  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  sku {
    name     = each.value.sku_name
    capacity = each.value.capacity
  }
}

resource "azurerm_private_endpoint" "openai" {
  name                = "pe-${var.account_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.account_name}"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dns-${var.account_name}"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

output "id" {
  value = azurerm_cognitive_account.openai.id
}

output "endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "principal_id" {
  value = azurerm_cognitive_account.openai.identity[0].principal_id
}
EOF

print_success "Generated modules/openai/main.tf"

###############################################################################
# Generate Search Module
###############################################################################

print_header "Generating Search Module"

cat > "$OUTPUT_DIR/modules/search/main.tf" << 'EOF'
# =============================================================================
# Azure AI Search Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "service_name" { type = string }
variable "environment" { type = string }
variable "search_config" { type = any }
variable "semantic_enabled" { type = bool }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

locals {
  config = var.search_config[var.environment]
}

resource "azurerm_search_service" "main" {
  name                          = var.service_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = local.config.sku
  replica_count                 = local.config.replicas
  partition_count               = local.config.partitions
  public_network_access_enabled = false
  semantic_search_sku           = var.semantic_enabled ? "standard" : null
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_private_endpoint" "search" {
  name                = "pe-${var.service_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.service_name}"
    private_connection_resource_id = azurerm_search_service.main.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dns-${var.service_name}"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

output "id" {
  value = azurerm_search_service.main.id
}

output "endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "principal_id" {
  value = azurerm_search_service.main.identity[0].principal_id
}
EOF

print_success "Generated modules/search/main.tf"

###############################################################################
# Generate Storage Module
###############################################################################

print_header "Generating Storage Module"

cat > "$OUTPUT_DIR/modules/storage/main.tf" << 'EOF'
# =============================================================================
# Storage Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "account_prefix" { type = string }
variable "environment" { type = string }
variable "containers" { type = list(string) }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

locals {
  account_name = "${var.account_prefix}${var.environment}"
}

resource "azurerm_storage_account" "main" {
  name                          = local.account_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  account_tier                  = "Standard"
  account_replication_type      = var.environment == "prod" ? "GRS" : "LRS"
  account_kind                  = "StorageV2"
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = false
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.containers)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_private_endpoint" "blob" {
  name                = "pe-${local.account_name}-blob"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${local.account_name}-blob"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dns-${local.account_name}"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

output "account_name" {
  value = azurerm_storage_account.main.name
}

output "account_id" {
  value = azurerm_storage_account.main.id
}

output "primary_blob_endpoint" {
  value = azurerm_storage_account.main.primary_blob_endpoint
}
EOF

print_success "Generated modules/storage/main.tf"

###############################################################################
# Generate Security Module
###############################################################################

print_header "Generating Security Module"

cat > "$OUTPUT_DIR/modules/security/main.tf" << 'EOF'
# =============================================================================
# Security Module (Key Vault)
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "resource_prefix" { type = string }
variable "tenant_id" { type = string }
variable "key_vault_config" { type = any }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                          = "kv-${var.resource_prefix}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  tenant_id                     = var.tenant_id
  sku_name                      = var.key_vault_config.sku_name
  purge_protection_enabled      = var.key_vault_config.purge_protection_enabled
  soft_delete_retention_days    = var.key_vault_config.soft_delete_retention_days
  public_network_access_enabled = false
  enable_rbac_authorization     = true
  tags                          = var.tags
}

resource "azurerm_private_endpoint" "vault" {
  name                = "pe-kv-${var.resource_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-kv-${var.resource_prefix}"
    private_connection_resource_id = azurerm_key_vault.main.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dns-kv-${var.resource_prefix}"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}
EOF

print_success "Generated modules/security/main.tf"

###############################################################################
# Generate Cosmos Module
###############################################################################

print_header "Generating Cosmos Module"

cat > "$OUTPUT_DIR/modules/cosmos/main.tf" << 'EOF'
# =============================================================================
# Cosmos DB Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "resource_prefix" { type = string }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_cosmosdb_account" "main" {
  name                          = "cosmos-${var.resource_prefix}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false
  tags                          = var.tags

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cosmosdb_sql_database" "genai" {
  name                = "genai_platform"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = "sessions"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.genai.name
  partition_key_paths = ["/user_id"]

  autoscale_settings {
    max_throughput = 4000
  }
}

resource "azurerm_cosmosdb_sql_container" "answer_cache" {
  name                = "answer_cache"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.genai.name
  partition_key_paths = ["/query_hash"]

  default_ttl = 86400

  autoscale_settings {
    max_throughput = 4000
  }
}

resource "azurerm_private_endpoint" "cosmos" {
  name                = "pe-cosmos-${var.resource_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-cosmos-${var.resource_prefix}"
    private_connection_resource_id = azurerm_cosmosdb_account.main.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dns-cosmos-${var.resource_prefix}"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

output "account_id" {
  value = azurerm_cosmosdb_account.main.id
}

output "endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}
EOF

print_success "Generated modules/cosmos/main.tf"

###############################################################################
# Generate Monitoring Module
###############################################################################

print_header "Generating Monitoring Module"

cat > "$OUTPUT_DIR/modules/monitoring/main.tf" << 'EOF'
# =============================================================================
# Monitoring Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "log_analytics_name" { type = string }
variable "app_insights_name" { type = string }
variable "retention_days" { type = number }
variable "tags" { type = map(string) }

resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = var.app_insights_name
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = var.tags
}

output "log_analytics_id" {
  value = azurerm_log_analytics_workspace.main.id
}

output "workspace_id" {
  value = azurerm_log_analytics_workspace.main.workspace_id
}

output "app_insights_id" {
  value = azurerm_application_insights.main.id
}

output "instrumentation_key" {
  value     = azurerm_application_insights.main.instrumentation_key
  sensitive = true
}

output "connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}
EOF

print_success "Generated modules/monitoring/main.tf"

###############################################################################
# Generate Environment Files
###############################################################################

print_header "Generating Environment Configurations"

for ENV in dev staging prod; do
    cat > "$OUTPUT_DIR/environments/$ENV/main.tf" << EOF
# =============================================================================
# Enterprise Copilot - $ENV Environment
# =============================================================================

module "copilot" {
  source = "../../"

  # Pass all variables
  subscription_id      = var.subscription_id
  tenant_id            = var.tenant_id
  default_region       = var.default_region
  project_prefix       = var.project_prefix
  environment          = "$ENV"
  default_tags         = var.default_tags

  # Networking
  create_new_vnet      = var.create_new_vnet
  vnet_address_space   = var.vnet_address_space
  subnets              = var.subnets
  create_private_dns_zones = var.create_private_dns_zones

  # Security
  key_vault_config     = var.key_vault_config

  # OpenAI
  openai_account_name  = var.openai_account_name
  openai_sku           = var.openai_sku
  openai_deployments   = var.openai_deployments

  # Search
  search_service_name  = var.search_service_name
  search_config        = var.search_config
  search_semantic_enabled = var.search_semantic_enabled

  # Storage
  storage_account_prefix = var.storage_account_prefix
  storage_containers     = var.storage_containers

  # Add-ons
  deploy_cosmos_db     = var.deploy_cosmos_db
  deploy_data_factory  = var.deploy_data_factory
  deploy_functions     = var.deploy_functions

  # Monitoring
  log_analytics_name   = var.log_analytics_name
  app_insights_name    = var.app_insights_name
  log_retention_days   = var.log_retention_days
}

output "resource_groups" {
  value = module.copilot.resource_group_names
}
EOF

    # Copy variables
    cp "$OUTPUT_DIR/variables.tf" "$OUTPUT_DIR/environments/$ENV/variables.tf"

    print_step "Generated environments/$ENV/"
done

print_success "All environment configurations generated"

###############################################################################
# Summary
###############################################################################

print_header "Generation Complete"

echo ""
echo "Generated Terraform configuration at: $OUTPUT_DIR"
echo ""
tree "$OUTPUT_DIR" 2>/dev/null || find "$OUTPUT_DIR" -type f -name "*.tf"
echo ""

cat << EOF

${GREEN}NEXT STEPS${NC}

1. Copy the terraform-inputs.tfvars to each environment:
   ${CYAN}cp terraform-inputs.tfvars $OUTPUT_DIR/environments/dev/terraform.tfvars${NC}

2. Copy the backend configuration:
   ${CYAN}cp backend.tfvars $OUTPUT_DIR/environments/dev/backend.tfvars${NC}

3. Initialize and apply:
   ${CYAN}cd $OUTPUT_DIR/environments/dev${NC}
   ${CYAN}terraform init -backend-config=backend.tfvars${NC}
   ${CYAN}terraform plan -var-file=terraform.tfvars${NC}
   ${CYAN}terraform apply -var-file=terraform.tfvars${NC}

EOF

print_success "Terraform generation complete!"
