#!/usr/bin/env bash
###############################################################################
# Enterprise Copilot - Azure Terraform Inputs Collector
#
# This script auto-discovers Azure resources and collects all inputs needed
# to generate a complete Terraform configuration for Enterprise Copilot.
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - jq installed (sudo apt-get install jq -y)
#   - Appropriate Azure permissions (Contributor + User Access Admin recommended)
#
# Usage:
#   chmod +x collect-terraform-inputs.sh
#   ./collect-terraform-inputs.sh
#
# Output:
#   - terraform-inputs.json (machine-readable)
#   - terraform-inputs.tfvars (ready for Terraform)
#   - Console summary
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Output files
OUTPUT_JSON="terraform-inputs.json"
OUTPUT_TFVARS="terraform-inputs.tfvars"
OUTPUT_BACKEND="backend.tfvars"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

print_section() {
    echo ""
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "   $1"
}

have_jq() {
    command -v jq >/dev/null 2>&1
}

check_name_available() {
    local type="$1"
    local name="$2"
    local result=""

    case "$type" in
        "openai")
            result=$(az cognitiveservices account list --query "[?name=='$name'].name" -o tsv 2>/dev/null || echo "")
            if [[ -z "$result" ]]; then
                echo "available"
            else
                echo "taken"
            fi
            ;;
        "search")
            result=$(az search service list --query "[?name=='$name'].name" -o tsv 2>/dev/null || echo "")
            if [[ -z "$result" ]]; then
                echo "available"
            else
                echo "taken"
            fi
            ;;
        "storage")
            result=$(az storage account check-name --name "$name" --query "nameAvailable" -o tsv 2>/dev/null || echo "false")
            if [[ "$result" == "true" ]]; then
                echo "available"
            else
                echo "taken"
            fi
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local value=""

    read -rp "$prompt [$default]: " value
    if [[ -z "$value" ]]; then
        value="$default"
    fi
    eval "$var_name='$value'"
}

prompt_yes_no() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local value=""

    while true; do
        read -rp "$prompt (yes/no) [$default]: " value
        if [[ -z "$value" ]]; then
            value="$default"
        fi
        case "$value" in
            yes|YES|y|Y) eval "$var_name='true'"; break ;;
            no|NO|n|N) eval "$var_name='false'"; break ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

###############################################################################
# Pre-flight Checks
###############################################################################

print_header "Enterprise Copilot - Azure Terraform Inputs Collector"

echo ""
echo "This script will collect all inputs needed to generate Terraform"
echo "configuration for your Enterprise Copilot deployment."
echo ""

# Check for Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Please install it first:"
    echo "  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check for jq
if ! have_jq; then
    print_warning "jq not found. Installing..."
    sudo apt-get update -qq && sudo apt-get install -y jq
fi

# Check Azure login
print_section "Checking Azure CLI login status..."
if ! az account show &>/dev/null; then
    print_warning "Not logged in to Azure. Starting login..."
    az login
fi
print_success "Azure CLI authenticated"

###############################################################################
# SECTION 1: Subscription & Tenant Basics
###############################################################################

print_header "1. Subscription & Tenant Information"

ACCT_JSON=$(az account show -o json)
SUB_ID=$(echo "$ACCT_JSON" | jq -r '.id')
TENANT_ID=$(echo "$ACCT_JSON" | jq -r '.tenantId')
SUB_NAME=$(echo "$ACCT_JSON" | jq -r '.name')
USER_NAME=$(echo "$ACCT_JSON" | jq -r '.user.name')
USER_TYPE=$(echo "$ACCT_JSON" | jq -r '.user.type')

print_info "Subscription Name : $SUB_NAME"
print_info "Subscription ID   : $SUB_ID"
print_info "Tenant ID         : $TENANT_ID"
print_info "Signed-in User    : $USER_NAME ($USER_TYPE)"

# List available subscriptions
echo ""
echo "Available subscriptions:"
az account list --query "[].{Name:name, ID:id, IsDefault:isDefault}" -o table

echo ""
read -rp "Use current subscription? (yes to continue, or enter different Sub ID): " SUB_CHOICE
if [[ "$SUB_CHOICE" != "yes" && "$SUB_CHOICE" != "" ]]; then
    SUB_ID="$SUB_CHOICE"
    az account set --subscription "$SUB_ID"
    ACCT_JSON=$(az account show -o json)
    SUB_NAME=$(echo "$ACCT_JSON" | jq -r '.name')
    print_success "Switched to subscription: $SUB_NAME"
fi

# Select region
print_section "Selecting Default Region"
echo ""
echo "Popular regions for Azure OpenAI + AI Search:"
echo "  eastus, eastus2, westus, westus2, westus3"
echo "  canadacentral, canadaeast"
echo "  northeurope, westeurope, uksouth, ukwest"
echo "  australiaeast, japaneast, southeastasia"
echo ""

# Show regions with OpenAI availability
echo "Regions with Azure OpenAI availability:"
az cognitiveservices account list-skus --kind OpenAI --query "[].{Location:locations[0]}" -o table 2>/dev/null | sort -u | head -20 || echo "  (Could not query - check Azure portal)"

echo ""
prompt_with_default "Enter default region" "eastus2" DEFAULT_REGION

# Environment names
print_section "Environment Configuration"
prompt_with_default "Environment names (comma-separated)" "dev,staging,prod" ENV_NAMES

###############################################################################
# SECTION 2: Naming & Tagging Conventions
###############################################################################

print_header "2. Naming & Tagging Conventions"

prompt_with_default "Project short prefix (3-10 chars, e.g., ecp, copilot)" "ecp" PROJECT_PREFIX
prompt_with_default "Organization short name (optional)" "contoso" ORG_NAME

print_section "Required Tags"
prompt_with_default "Project tag value" "enterprise-copilot" TAG_PROJECT
prompt_with_default "Owner tag value" "platform-team" TAG_OWNER
prompt_with_default "Cost Center tag value" "AI-001" TAG_COST_CENTER

###############################################################################
# SECTION 3: Networking Configuration
###############################################################################

print_header "3. Networking Configuration"

# List existing VNets
print_section "Existing Virtual Networks"
VNETS_JSON=$(az network vnet list -o json 2>/dev/null || echo "[]")
VNET_COUNT=$(echo "$VNETS_JSON" | jq 'length')

if [[ "$VNET_COUNT" -gt 0 ]]; then
    echo "$VNETS_JSON" | jq -r '.[] | "  \(.name) | RG: \(.resourceGroup) | Location: \(.location) | CIDR: \(.addressSpace.addressPrefixes | join(","))"'
    echo ""
    echo "Subnets:"
    echo "$VNETS_JSON" | jq -r '.[] | .name as $vnet | (.subnets[]? | "    \($vnet)/\(.name): \(.addressPrefix)")'
else
    print_info "No existing VNets found in this subscription."
fi

echo ""
prompt_yes_no "Create new VNet for Enterprise Copilot?" "yes" CREATE_NEW_VNET

if [[ "$CREATE_NEW_VNET" == "true" ]]; then
    prompt_with_default "VNet address space (CIDR)" "10.100.0.0/16" VNET_CIDR
    prompt_with_default "Private Endpoints subnet CIDR" "10.100.1.0/24" SUBNET_PE_CIDR
    prompt_with_default "Application subnet CIDR (Functions/Apps)" "10.100.2.0/24" SUBNET_APP_CIDR
    prompt_with_default "AKS subnet CIDR (if using AKS)" "10.100.10.0/23" SUBNET_AKS_CIDR
    EXISTING_VNET_NAME=""
    EXISTING_VNET_RG=""
else
    read -rp "Enter existing VNet name: " EXISTING_VNET_NAME
    read -rp "Enter existing VNet resource group: " EXISTING_VNET_RG
    VNET_CIDR=""
    SUBNET_PE_CIDR=""
    SUBNET_APP_CIDR=""
    SUBNET_AKS_CIDR=""
fi

print_section "Private DNS Zones"
prompt_yes_no "Create Private DNS zones for private endpoints?" "yes" CREATE_PRIVATE_DNS

###############################################################################
# SECTION 4: Security / Identity Configuration
###############################################################################

print_header "4. Security & Identity Configuration"

print_section "Entra ID Groups"
prompt_yes_no "Create Entra ID groups via Terraform?" "yes" CREATE_AD_GROUPS

if [[ "$CREATE_AD_GROUPS" == "true" ]]; then
    prompt_with_default "Admin group name" "${PROJECT_PREFIX}-admins" GROUP_ADMINS
    prompt_with_default "Users group name" "${PROJECT_PREFIX}-users" GROUP_USERS
    prompt_with_default "Developers group name" "${PROJECT_PREFIX}-devs" GROUP_DEVS
fi

print_section "Key Vault Configuration"
prompt_yes_no "Enable purge protection? (use 'no' for dev/temporary)" "no" KV_PURGE_PROTECTION
prompt_with_default "Soft delete retention days (7-90)" "7" KV_SOFT_DELETE_DAYS

###############################################################################
# SECTION 5: Azure OpenAI Configuration
###############################################################################

print_header "5. Azure OpenAI Configuration"

# Generate unique name suggestion
OPENAI_NAME_SUGGESTION="openai-${PROJECT_PREFIX}-${DEFAULT_REGION}"
prompt_with_default "Azure OpenAI account name (globally unique)" "$OPENAI_NAME_SUGGESTION" OPENAI_ACCOUNT_NAME

# Check availability
OPENAI_AVAIL=$(check_name_available "openai" "$OPENAI_ACCOUNT_NAME")
if [[ "$OPENAI_AVAIL" == "taken" ]]; then
    print_warning "Name '$OPENAI_ACCOUNT_NAME' may already exist. Consider a different name."
fi

print_section "Model Deployments"
echo ""
echo "Available models (check region availability in Azure portal):"
echo "  Chat: gpt-4o, gpt-4o-mini, gpt-4, gpt-35-turbo"
echo "  Embeddings: text-embedding-3-large, text-embedding-3-small, text-embedding-ada-002"
echo ""

prompt_with_default "Chat model" "gpt-4o" OPENAI_CHAT_MODEL
prompt_with_default "Chat deployment name" "chat-gpt4o" OPENAI_CHAT_DEPLOY_NAME
prompt_with_default "Chat model capacity (1000s of TPM)" "30" OPENAI_CHAT_CAPACITY

prompt_with_default "Embedding model" "text-embedding-3-large" OPENAI_EMBED_MODEL
prompt_with_default "Embedding deployment name" "embed-3-large" OPENAI_EMBED_DEPLOY_NAME
prompt_with_default "Embedding model capacity (1000s of TPM)" "120" OPENAI_EMBED_CAPACITY

prompt_with_default "OpenAI SKU" "S0" OPENAI_SKU

###############################################################################
# SECTION 6: Azure AI Search Configuration
###############################################################################

print_header "6. Azure AI Search Configuration"

SEARCH_NAME_SUGGESTION="search-${PROJECT_PREFIX}-${DEFAULT_REGION}"
prompt_with_default "AI Search service name (globally unique)" "$SEARCH_NAME_SUGGESTION" SEARCH_SERVICE_NAME

# Check availability
SEARCH_AVAIL=$(check_name_available "search" "$SEARCH_SERVICE_NAME")
if [[ "$SEARCH_AVAIL" == "taken" ]]; then
    print_warning "Name '$SEARCH_SERVICE_NAME' may already exist. Consider a different name."
fi

echo ""
echo "AI Search SKU tiers:"
echo "  free     - 50MB, 3 indexes (dev only)"
echo "  basic    - 2GB, 15 indexes, vectors supported"
echo "  standard - 25GB per partition, semantic ranker"
echo "  standard2/3 - Higher scale"
echo ""

prompt_with_default "Search SKU for dev" "basic" SEARCH_SKU_DEV
prompt_with_default "Search SKU for prod" "standard" SEARCH_SKU_PROD
prompt_with_default "Replica count (dev)" "1" SEARCH_REPLICAS_DEV
prompt_with_default "Replica count (prod)" "2" SEARCH_REPLICAS_PROD
prompt_with_default "Partition count (dev)" "1" SEARCH_PARTITIONS_DEV
prompt_with_default "Partition count (prod)" "2" SEARCH_PARTITIONS_PROD
prompt_yes_no "Enable semantic ranker?" "yes" SEARCH_SEMANTIC_ENABLED

###############################################################################
# SECTION 7: Storage & Ingestion Configuration
###############################################################################

print_header "7. Storage & Ingestion Configuration"

# Storage account name must be 3-24 chars, lowercase alphanumeric only
STORAGE_PREFIX_SUGGESTION="st${PROJECT_PREFIX}$(echo $RANDOM | md5sum | head -c 4)"
prompt_with_default "Storage account prefix (3-24 chars, alphanumeric)" "$STORAGE_PREFIX_SUGGESTION" STORAGE_PREFIX

# Validate storage name
STORAGE_NAME="${STORAGE_PREFIX}dev"
STORAGE_AVAIL=$(check_name_available "storage" "$STORAGE_NAME")
if [[ "$STORAGE_AVAIL" == "taken" ]]; then
    print_warning "Storage name pattern may conflict. Consider a different prefix."
fi

print_section "Storage Containers"
prompt_with_default "Raw documents container" "raw-documents" CONTAINER_RAW
prompt_with_default "Processed documents container" "processed-documents" CONTAINER_PROCESSED
prompt_with_default "Chunks container" "chunks" CONTAINER_CHUNKS

print_section "Ingestion Services"
prompt_yes_no "Deploy Azure Data Factory?" "yes" DEPLOY_ADF
prompt_yes_no "Deploy Azure Functions for ingestion?" "yes" DEPLOY_FUNCTIONS

if [[ "$DEPLOY_FUNCTIONS" == "true" ]]; then
    echo ""
    echo "Functions runtime options: python, dotnet, node"
    prompt_with_default "Functions runtime" "python" FUNCTIONS_RUNTIME
    echo ""
    echo "Functions hosting plans:"
    echo "  Consumption - Pay per execution (dev)"
    echo "  Premium     - Pre-warmed, VNet integration (prod)"
    prompt_with_default "Functions plan (consumption/premium)" "consumption" FUNCTIONS_PLAN
fi

###############################################################################
# SECTION 8: Observability Configuration
###############################################################################

print_header "8. Observability Configuration"

prompt_with_default "Log Analytics workspace name" "log-${PROJECT_PREFIX}" LOG_ANALYTICS_NAME
prompt_with_default "Application Insights name" "appi-${PROJECT_PREFIX}" APP_INSIGHTS_NAME
prompt_with_default "Log retention days" "30" LOG_RETENTION_DAYS

print_section "Alerting"
prompt_with_default "Alert notification email" "" ALERT_EMAIL
prompt_with_default "Teams webhook URL (optional)" "" ALERT_TEAMS_WEBHOOK

###############################################################################
# SECTION 9: Terraform Backend Configuration
###############################################################################

print_header "9. Terraform State Backend Configuration"

# List existing storage accounts
print_section "Existing Storage Accounts"
az storage account list --query "[].{Name:name, RG:resourceGroup, Location:primaryLocation}" -o table 2>/dev/null || true

echo ""
prompt_yes_no "Create new storage account for Terraform state?" "yes" CREATE_TF_BACKEND

if [[ "$CREATE_TF_BACKEND" == "true" ]]; then
    TF_STORAGE_SUGGESTION="tfstate${PROJECT_PREFIX}$(echo $RANDOM | md5sum | head -c 4)"
    prompt_with_default "Terraform state storage account name" "$TF_STORAGE_SUGGESTION" TF_STORAGE_ACCOUNT
    prompt_with_default "Terraform state resource group" "rg-${PROJECT_PREFIX}-tfstate" TF_STORAGE_RG
    prompt_with_default "Terraform state container name" "tfstate" TF_STORAGE_CONTAINER
else
    read -rp "Existing storage account name: " TF_STORAGE_ACCOUNT
    read -rp "Existing resource group: " TF_STORAGE_RG
    prompt_with_default "Container name" "tfstate" TF_STORAGE_CONTAINER
fi

print_section "CI/CD Platform"
echo "Options: github, azuredevops, none"
prompt_with_default "CI/CD platform" "github" CICD_PLATFORM

###############################################################################
# SECTION 10: Optional Enterprise Add-ons
###############################################################################

print_header "10. Optional Enterprise Add-ons"

echo "Select which additional services to deploy:"
echo ""

prompt_yes_no "Cosmos DB (chat history, metadata, caching)?" "yes" DEPLOY_COSMOS
prompt_yes_no "API Management (API gateway, rate limiting)?" "no" DEPLOY_APIM
prompt_yes_no "Redis Cache (retrieval caching)?" "no" DEPLOY_REDIS
prompt_yes_no "Azure Front Door + WAF?" "no" DEPLOY_FRONTDOOR
prompt_yes_no "Container Apps / AKS for RAG orchestrator?" "no" DEPLOY_CONTAINERS

if [[ "$DEPLOY_COSMOS" == "true" ]]; then
    prompt_with_default "Cosmos DB account name" "cosmos-${PROJECT_PREFIX}" COSMOS_ACCOUNT_NAME
    prompt_with_default "Cosmos DB throughput (RU/s)" "400" COSMOS_THROUGHPUT
fi

###############################################################################
# Generate Output Files
###############################################################################

print_header "Generating Configuration Files"

# Generate JSON output
cat > "$OUTPUT_JSON" << EOF
{
  "subscription": {
    "id": "$SUB_ID",
    "name": "$SUB_NAME",
    "tenant_id": "$TENANT_ID"
  },
  "general": {
    "default_region": "$DEFAULT_REGION",
    "environments": "$(echo $ENV_NAMES | tr ',' ' ')",
    "project_prefix": "$PROJECT_PREFIX",
    "org_name": "$ORG_NAME"
  },
  "tags": {
    "project": "$TAG_PROJECT",
    "owner": "$TAG_OWNER",
    "cost_center": "$TAG_COST_CENTER"
  },
  "networking": {
    "create_new_vnet": $CREATE_NEW_VNET,
    "vnet_cidr": "$VNET_CIDR",
    "subnet_pe_cidr": "$SUBNET_PE_CIDR",
    "subnet_app_cidr": "$SUBNET_APP_CIDR",
    "subnet_aks_cidr": "$SUBNET_AKS_CIDR",
    "existing_vnet_name": "$EXISTING_VNET_NAME",
    "existing_vnet_rg": "$EXISTING_VNET_RG",
    "create_private_dns": $CREATE_PRIVATE_DNS
  },
  "security": {
    "create_ad_groups": $CREATE_AD_GROUPS,
    "group_admins": "${GROUP_ADMINS:-}",
    "group_users": "${GROUP_USERS:-}",
    "group_devs": "${GROUP_DEVS:-}",
    "kv_purge_protection": $KV_PURGE_PROTECTION,
    "kv_soft_delete_days": $KV_SOFT_DELETE_DAYS
  },
  "openai": {
    "account_name": "$OPENAI_ACCOUNT_NAME",
    "sku": "$OPENAI_SKU",
    "chat_model": "$OPENAI_CHAT_MODEL",
    "chat_deployment_name": "$OPENAI_CHAT_DEPLOY_NAME",
    "chat_capacity": $OPENAI_CHAT_CAPACITY,
    "embed_model": "$OPENAI_EMBED_MODEL",
    "embed_deployment_name": "$OPENAI_EMBED_DEPLOY_NAME",
    "embed_capacity": $OPENAI_EMBED_CAPACITY
  },
  "search": {
    "service_name": "$SEARCH_SERVICE_NAME",
    "sku_dev": "$SEARCH_SKU_DEV",
    "sku_prod": "$SEARCH_SKU_PROD",
    "replicas_dev": $SEARCH_REPLICAS_DEV,
    "replicas_prod": $SEARCH_REPLICAS_PROD,
    "partitions_dev": $SEARCH_PARTITIONS_DEV,
    "partitions_prod": $SEARCH_PARTITIONS_PROD,
    "semantic_enabled": $SEARCH_SEMANTIC_ENABLED
  },
  "storage": {
    "prefix": "$STORAGE_PREFIX",
    "container_raw": "$CONTAINER_RAW",
    "container_processed": "$CONTAINER_PROCESSED",
    "container_chunks": "$CONTAINER_CHUNKS"
  },
  "ingestion": {
    "deploy_adf": $DEPLOY_ADF,
    "deploy_functions": $DEPLOY_FUNCTIONS,
    "functions_runtime": "${FUNCTIONS_RUNTIME:-python}",
    "functions_plan": "${FUNCTIONS_PLAN:-consumption}"
  },
  "observability": {
    "log_analytics_name": "$LOG_ANALYTICS_NAME",
    "app_insights_name": "$APP_INSIGHTS_NAME",
    "retention_days": $LOG_RETENTION_DAYS,
    "alert_email": "$ALERT_EMAIL",
    "alert_teams_webhook": "$ALERT_TEAMS_WEBHOOK"
  },
  "terraform_backend": {
    "create_new": $CREATE_TF_BACKEND,
    "storage_account": "$TF_STORAGE_ACCOUNT",
    "resource_group": "$TF_STORAGE_RG",
    "container": "$TF_STORAGE_CONTAINER"
  },
  "cicd": {
    "platform": "$CICD_PLATFORM"
  },
  "addons": {
    "cosmos_db": $DEPLOY_COSMOS,
    "cosmos_account_name": "${COSMOS_ACCOUNT_NAME:-}",
    "cosmos_throughput": ${COSMOS_THROUGHPUT:-400},
    "apim": $DEPLOY_APIM,
    "redis": $DEPLOY_REDIS,
    "frontdoor": $DEPLOY_FRONTDOOR,
    "containers": $DEPLOY_CONTAINERS
  }
}
EOF

print_success "Generated $OUTPUT_JSON"

# Generate tfvars output
cat > "$OUTPUT_TFVARS" << EOF
# =============================================================================
# Enterprise Copilot - Terraform Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# =============================================================================

# -----------------------------------------------------------------------------
# Subscription & General
# -----------------------------------------------------------------------------
subscription_id = "$SUB_ID"
tenant_id       = "$TENANT_ID"
default_region  = "$DEFAULT_REGION"
project_prefix  = "$PROJECT_PREFIX"
org_name        = "$ORG_NAME"

environments = [$(echo $ENV_NAMES | sed 's/,/", "/g' | sed 's/^/"/' | sed 's/$/"/')]

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------
default_tags = {
  project     = "$TAG_PROJECT"
  owner       = "$TAG_OWNER"
  cost_center = "$TAG_COST_CENTER"
  managed_by  = "terraform"
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------
create_new_vnet    = $CREATE_NEW_VNET
vnet_address_space = "$VNET_CIDR"

subnets = {
  private-endpoints = {
    cidr                          = "$SUBNET_PE_CIDR"
    service_endpoints             = ["Microsoft.CognitiveServices", "Microsoft.Storage", "Microsoft.KeyVault"]
    private_endpoint_network_policies_enabled = true
  }
  applications = {
    cidr              = "$SUBNET_APP_CIDR"
    service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.Web"]
    delegation = {
      name    = "functions"
      service = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
  aks = {
    cidr              = "$SUBNET_AKS_CIDR"
    service_endpoints = ["Microsoft.Storage", "Microsoft.ContainerRegistry"]
  }
}

create_private_dns_zones = $CREATE_PRIVATE_DNS

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
create_ad_groups   = $CREATE_AD_GROUPS
ad_group_admins    = "${GROUP_ADMINS:-}"
ad_group_users     = "${GROUP_USERS:-}"
ad_group_devs      = "${GROUP_DEVS:-}"

key_vault_config = {
  purge_protection_enabled   = $KV_PURGE_PROTECTION
  soft_delete_retention_days = $KV_SOFT_DELETE_DAYS
  sku_name                   = "standard"
}

# -----------------------------------------------------------------------------
# Azure OpenAI
# -----------------------------------------------------------------------------
openai_account_name = "$OPENAI_ACCOUNT_NAME"
openai_sku          = "$OPENAI_SKU"

openai_deployments = {
  "$OPENAI_CHAT_DEPLOY_NAME" = {
    model_name    = "$OPENAI_CHAT_MODEL"
    model_version = "2024-08-06"
    capacity      = $OPENAI_CHAT_CAPACITY
    sku_name      = "Standard"
  }
  "$OPENAI_EMBED_DEPLOY_NAME" = {
    model_name    = "$OPENAI_EMBED_MODEL"
    model_version = "1"
    capacity      = $OPENAI_EMBED_CAPACITY
    sku_name      = "Standard"
  }
}

# -----------------------------------------------------------------------------
# Azure AI Search
# -----------------------------------------------------------------------------
search_service_name = "$SEARCH_SERVICE_NAME"
search_semantic_enabled = $SEARCH_SEMANTIC_ENABLED

search_config = {
  dev = {
    sku        = "$SEARCH_SKU_DEV"
    replicas   = $SEARCH_REPLICAS_DEV
    partitions = $SEARCH_PARTITIONS_DEV
  }
  staging = {
    sku        = "$SEARCH_SKU_DEV"
    replicas   = $SEARCH_REPLICAS_DEV
    partitions = $SEARCH_PARTITIONS_DEV
  }
  prod = {
    sku        = "$SEARCH_SKU_PROD"
    replicas   = $SEARCH_REPLICAS_PROD
    partitions = $SEARCH_PARTITIONS_PROD
  }
}

# -----------------------------------------------------------------------------
# Storage
# -----------------------------------------------------------------------------
storage_account_prefix = "$STORAGE_PREFIX"

storage_containers = [
  "$CONTAINER_RAW",
  "$CONTAINER_PROCESSED",
  "$CONTAINER_CHUNKS"
]

# -----------------------------------------------------------------------------
# Ingestion
# -----------------------------------------------------------------------------
deploy_data_factory = $DEPLOY_ADF
deploy_functions    = $DEPLOY_FUNCTIONS
functions_runtime   = "${FUNCTIONS_RUNTIME:-python}"
functions_plan      = "${FUNCTIONS_PLAN:-consumption}"

# -----------------------------------------------------------------------------
# Observability
# -----------------------------------------------------------------------------
log_analytics_name     = "$LOG_ANALYTICS_NAME"
app_insights_name      = "$APP_INSIGHTS_NAME"
log_retention_days     = $LOG_RETENTION_DAYS
alert_email            = "$ALERT_EMAIL"
alert_teams_webhook    = "$ALERT_TEAMS_WEBHOOK"

# -----------------------------------------------------------------------------
# Add-ons
# -----------------------------------------------------------------------------
deploy_cosmos_db    = $DEPLOY_COSMOS
cosmos_account_name = "${COSMOS_ACCOUNT_NAME:-}"
cosmos_throughput   = ${COSMOS_THROUGHPUT:-400}

deploy_apim       = $DEPLOY_APIM
deploy_redis      = $DEPLOY_REDIS
deploy_frontdoor  = $DEPLOY_FRONTDOOR
deploy_containers = $DEPLOY_CONTAINERS
EOF

print_success "Generated $OUTPUT_TFVARS"

# Generate backend config
cat > "$OUTPUT_BACKEND" << EOF
# Terraform Backend Configuration
resource_group_name  = "$TF_STORAGE_RG"
storage_account_name = "$TF_STORAGE_ACCOUNT"
container_name       = "$TF_STORAGE_CONTAINER"
key                  = "enterprise-copilot.tfstate"
EOF

print_success "Generated $OUTPUT_BACKEND"

###############################################################################
# Print Summary
###############################################################################

print_header "Configuration Summary"

cat << EOF

${GREEN}SUBSCRIPTION & IDENTITY${NC}
  Subscription ID : $SUB_ID
  Tenant ID       : $TENANT_ID
  Region          : $DEFAULT_REGION
  Environments    : $ENV_NAMES

${GREEN}NAMING${NC}
  Project Prefix  : $PROJECT_PREFIX
  Organization    : $ORG_NAME

${GREEN}NETWORKING${NC}
  Create New VNet : $CREATE_NEW_VNET
  VNet CIDR       : ${VNET_CIDR:-"Using existing: $EXISTING_VNET_NAME"}
  Private DNS     : $CREATE_PRIVATE_DNS

${GREEN}AZURE OPENAI${NC}
  Account Name    : $OPENAI_ACCOUNT_NAME
  Chat Model      : $OPENAI_CHAT_MODEL ($OPENAI_CHAT_DEPLOY_NAME)
  Embed Model     : $OPENAI_EMBED_MODEL ($OPENAI_EMBED_DEPLOY_NAME)

${GREEN}AI SEARCH${NC}
  Service Name    : $SEARCH_SERVICE_NAME
  Dev SKU         : $SEARCH_SKU_DEV (${SEARCH_REPLICAS_DEV}R/${SEARCH_PARTITIONS_DEV}P)
  Prod SKU        : $SEARCH_SKU_PROD (${SEARCH_REPLICAS_PROD}R/${SEARCH_PARTITIONS_PROD}P)
  Semantic Ranker : $SEARCH_SEMANTIC_ENABLED

${GREEN}STORAGE${NC}
  Prefix          : $STORAGE_PREFIX
  Containers      : $CONTAINER_RAW, $CONTAINER_PROCESSED, $CONTAINER_CHUNKS

${GREEN}ADD-ONS${NC}
  Cosmos DB       : $DEPLOY_COSMOS
  Data Factory    : $DEPLOY_ADF
  Functions       : $DEPLOY_FUNCTIONS ${FUNCTIONS_RUNTIME:-}
  APIM            : $DEPLOY_APIM
  Redis           : $DEPLOY_REDIS
  Front Door      : $DEPLOY_FRONTDOOR

${GREEN}TERRAFORM BACKEND${NC}
  Storage Account : $TF_STORAGE_ACCOUNT
  Resource Group  : $TF_STORAGE_RG
  Container       : $TF_STORAGE_CONTAINER

${GREEN}OUTPUT FILES${NC}
  $OUTPUT_JSON      - Machine-readable configuration
  $OUTPUT_TFVARS    - Ready-to-use Terraform variables
  $OUTPUT_BACKEND   - Backend configuration

EOF

###############################################################################
# Create Terraform Backend (if requested)
###############################################################################

if [[ "$CREATE_TF_BACKEND" == "true" ]]; then
    print_section "Creating Terraform State Backend"

    echo ""
    read -rp "Create Terraform state storage now? (yes/no): " CREATE_NOW

    if [[ "$CREATE_NOW" == "yes" ]]; then
        echo "Creating resource group..."
        az group create \
            --name "$TF_STORAGE_RG" \
            --location "$DEFAULT_REGION" \
            --tags project="$TAG_PROJECT" owner="$TAG_OWNER" purpose="terraform-state" \
            --output none

        echo "Creating storage account..."
        az storage account create \
            --name "$TF_STORAGE_ACCOUNT" \
            --resource-group "$TF_STORAGE_RG" \
            --location "$DEFAULT_REGION" \
            --sku Standard_LRS \
            --kind StorageV2 \
            --https-only true \
            --min-tls-version TLS1_2 \
            --allow-blob-public-access false \
            --tags project="$TAG_PROJECT" owner="$TAG_OWNER" purpose="terraform-state" \
            --output none

        echo "Creating blob container..."
        az storage container create \
            --name "$TF_STORAGE_CONTAINER" \
            --account-name "$TF_STORAGE_ACCOUNT" \
            --auth-mode login \
            --output none

        print_success "Terraform backend created successfully!"
    fi
fi

###############################################################################
# Final Instructions
###############################################################################

print_header "Next Steps"

cat << EOF

1. Review the generated files:
   ${CYAN}cat $OUTPUT_TFVARS${NC}

2. Copy files to your Terraform directory:
   ${CYAN}cp $OUTPUT_TFVARS infrastructure/terraform/environments/dev/terraform.tfvars${NC}
   ${CYAN}cp $OUTPUT_BACKEND infrastructure/terraform/environments/dev/backend.tfvars${NC}

3. Initialize and apply Terraform:
   ${CYAN}cd infrastructure/terraform/environments/dev${NC}
   ${CYAN}terraform init -backend-config=backend.tfvars${NC}
   ${CYAN}terraform plan -var-file=terraform.tfvars${NC}
   ${CYAN}terraform apply -var-file=terraform.tfvars${NC}

4. For additional environments, copy and modify tfvars:
   ${CYAN}cp terraform.tfvars ../staging/terraform.tfvars${NC}
   ${CYAN}# Edit environment-specific values${NC}

${YELLOW}IMPORTANT:${NC}
- Review all values before applying
- Ensure Azure quotas are sufficient for OpenAI models
- Verify networking doesn't conflict with existing resources

EOF

print_success "Input collection complete!"
