#!/bin/bash
#===============================================================================
# Azure Resource Instance Creation Script
# Creates Azure resources for AI/ML projects with best practices
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration file
CONFIG_FILE="${1:-./resource_config.json}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Azure Resource Creation Tool${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Config file not found. Creating template...${NC}"
    cat > "$CONFIG_FILE" << 'EOF'
{
  "project_name": "myproject",
  "environment": "dev",
  "location": "eastus",
  "tags": {
    "Environment": "dev",
    "Project": "AI-ML-Platform",
    "ManagedBy": "Script"
  },
  "resources": {
    "resource_group": {
      "enabled": true,
      "name_suffix": "rg"
    },
    "storage_account": {
      "enabled": true,
      "sku": "Standard_LRS",
      "kind": "StorageV2",
      "hierarchical_namespace": true
    },
    "key_vault": {
      "enabled": true,
      "sku": "standard",
      "soft_delete": true,
      "purge_protection": false
    },
    "openai": {
      "enabled": true,
      "sku": "S0",
      "deployments": [
        {
          "name": "gpt-4o",
          "model": "gpt-4o",
          "version": "2024-05-13",
          "capacity": 10
        },
        {
          "name": "text-embedding-3-large",
          "model": "text-embedding-3-large",
          "version": "1",
          "capacity": 10
        }
      ]
    },
    "ai_search": {
      "enabled": true,
      "sku": "basic",
      "replica_count": 1,
      "partition_count": 1
    },
    "cosmos_db": {
      "enabled": true,
      "kind": "GlobalDocumentDB",
      "consistency_level": "Session",
      "databases": [
        {
          "name": "appdata",
          "throughput": 400
        }
      ]
    },
    "function_app": {
      "enabled": true,
      "runtime": "python",
      "runtime_version": "3.11",
      "sku": "Y1"
    },
    "ml_workspace": {
      "enabled": false,
      "sku": "Basic"
    },
    "vnet": {
      "enabled": true,
      "address_space": "10.0.0.0/16",
      "subnets": [
        {
          "name": "default",
          "address_prefix": "10.0.1.0/24"
        },
        {
          "name": "private-endpoints",
          "address_prefix": "10.0.2.0/24"
        },
        {
          "name": "functions",
          "address_prefix": "10.0.3.0/24",
          "delegation": "Microsoft.Web/serverFarms"
        }
      ]
    }
  }
}
EOF
    echo -e "${GREEN}Template created: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Please edit the config file and run again.${NC}"
    exit 0
fi

# Read configuration
PROJECT_NAME=$(jq -r '.project_name' "$CONFIG_FILE")
ENVIRONMENT=$(jq -r '.environment' "$CONFIG_FILE")
LOCATION=$(jq -r '.location' "$CONFIG_FILE")
TAGS=$(jq -r '.tags | to_entries | map("\(.key)=\(.value)") | join(" ")' "$CONFIG_FILE")

# Generate resource names
RESOURCE_GROUP="${PROJECT_NAME}-${ENVIRONMENT}-rg"
STORAGE_ACCOUNT="${PROJECT_NAME}${ENVIRONMENT}sa"
KEY_VAULT="${PROJECT_NAME}-${ENVIRONMENT}-kv"
OPENAI_NAME="${PROJECT_NAME}-${ENVIRONMENT}-openai"
SEARCH_NAME="${PROJECT_NAME}-${ENVIRONMENT}-search"
COSMOS_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cosmos"
FUNCTION_APP="${PROJECT_NAME}-${ENVIRONMENT}-func"
ML_WORKSPACE="${PROJECT_NAME}-${ENVIRONMENT}-ml"
VNET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-vnet"

# Clean up storage account name (lowercase, alphanumeric only, max 24 chars)
STORAGE_ACCOUNT=$(echo "$STORAGE_ACCOUNT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | cut -c1-24)

echo -e "\n${YELLOW}Configuration:${NC}"
echo -e "  Project: $PROJECT_NAME"
echo -e "  Environment: $ENVIRONMENT"
echo -e "  Location: $LOCATION"
echo -e "  Resource Group: $RESOURCE_GROUP"

#-------------------------------------------------------------------------------
# 1. Create Resource Group
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.resource_group.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[1/9] Creating Resource Group...${NC}"

    if az group show -n "$RESOURCE_GROUP" &>/dev/null; then
        echo -e "${GREEN}  ✓ Resource Group already exists${NC}"
    else
        az group create \
            --name "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Resource Group: $RESOURCE_GROUP${NC}"
    fi
else
    echo -e "\n${YELLOW}[1/9] Skipping Resource Group (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 2. Create Virtual Network
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.vnet.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[2/9] Creating Virtual Network...${NC}"

    ADDRESS_SPACE=$(jq -r '.resources.vnet.address_space' "$CONFIG_FILE")

    if az network vnet show -g "$RESOURCE_GROUP" -n "$VNET_NAME" &>/dev/null; then
        echo -e "${GREEN}  ✓ VNet already exists${NC}"
    else
        az network vnet create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$VNET_NAME" \
            --address-prefixes "$ADDRESS_SPACE" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created VNet: $VNET_NAME${NC}"
    fi

    # Create subnets
    echo -e "  Creating subnets..."
    jq -c '.resources.vnet.subnets[]' "$CONFIG_FILE" | while read -r subnet; do
        SUBNET_NAME=$(echo "$subnet" | jq -r '.name')
        SUBNET_PREFIX=$(echo "$subnet" | jq -r '.address_prefix')
        DELEGATION=$(echo "$subnet" | jq -r '.delegation // empty')

        if az network vnet subnet show -g "$RESOURCE_GROUP" --vnet-name "$VNET_NAME" -n "$SUBNET_NAME" &>/dev/null; then
            echo -e "${GREEN}    ✓ Subnet $SUBNET_NAME already exists${NC}"
        else
            if [ -n "$DELEGATION" ]; then
                az network vnet subnet create \
                    --resource-group "$RESOURCE_GROUP" \
                    --vnet-name "$VNET_NAME" \
                    --name "$SUBNET_NAME" \
                    --address-prefixes "$SUBNET_PREFIX" \
                    --delegations "$DELEGATION" \
                    --output none
            else
                az network vnet subnet create \
                    --resource-group "$RESOURCE_GROUP" \
                    --vnet-name "$VNET_NAME" \
                    --name "$SUBNET_NAME" \
                    --address-prefixes "$SUBNET_PREFIX" \
                    --output none
            fi
            echo -e "${GREEN}    ✓ Created subnet: $SUBNET_NAME${NC}"
        fi
    done
else
    echo -e "\n${YELLOW}[2/9] Skipping Virtual Network (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 3. Create Storage Account
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.storage_account.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[3/9] Creating Storage Account...${NC}"

    SKU=$(jq -r '.resources.storage_account.sku' "$CONFIG_FILE")
    KIND=$(jq -r '.resources.storage_account.kind' "$CONFIG_FILE")
    HNS=$(jq -r '.resources.storage_account.hierarchical_namespace' "$CONFIG_FILE")

    if az storage account show -g "$RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" &>/dev/null; then
        echo -e "${GREEN}  ✓ Storage Account already exists${NC}"
    else
        HNS_FLAG=""
        if [ "$HNS" == "true" ]; then
            HNS_FLAG="--enable-hierarchical-namespace true"
        fi

        az storage account create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$STORAGE_ACCOUNT" \
            --location "$LOCATION" \
            --sku "$SKU" \
            --kind "$KIND" \
            $HNS_FLAG \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Storage Account: $STORAGE_ACCOUNT${NC}"
    fi
else
    echo -e "\n${YELLOW}[3/9] Skipping Storage Account (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 4. Create Key Vault
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.key_vault.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[4/9] Creating Key Vault...${NC}"

    KV_SKU=$(jq -r '.resources.key_vault.sku' "$CONFIG_FILE")

    if az keyvault show -g "$RESOURCE_GROUP" -n "$KEY_VAULT" &>/dev/null; then
        echo -e "${GREEN}  ✓ Key Vault already exists${NC}"
    else
        az keyvault create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$KEY_VAULT" \
            --location "$LOCATION" \
            --sku "$KV_SKU" \
            --enable-rbac-authorization true \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Key Vault: $KEY_VAULT${NC}"
    fi
else
    echo -e "\n${YELLOW}[4/9] Skipping Key Vault (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 5. Create Azure OpenAI
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.openai.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[5/9] Creating Azure OpenAI...${NC}"

    OPENAI_SKU=$(jq -r '.resources.openai.sku' "$CONFIG_FILE")

    if az cognitiveservices account show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" &>/dev/null; then
        echo -e "${GREEN}  ✓ Azure OpenAI already exists${NC}"
    else
        az cognitiveservices account create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$OPENAI_NAME" \
            --location "$LOCATION" \
            --kind OpenAI \
            --sku "$OPENAI_SKU" \
            --custom-domain "$OPENAI_NAME" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Azure OpenAI: $OPENAI_NAME${NC}"
    fi

    # Create deployments
    echo -e "  Creating model deployments..."
    jq -c '.resources.openai.deployments[]' "$CONFIG_FILE" | while read -r deployment; do
        DEPLOY_NAME=$(echo "$deployment" | jq -r '.name')
        MODEL_NAME=$(echo "$deployment" | jq -r '.model')
        MODEL_VERSION=$(echo "$deployment" | jq -r '.version')
        CAPACITY=$(echo "$deployment" | jq -r '.capacity')

        if az cognitiveservices account deployment show -g "$RESOURCE_GROUP" -n "$OPENAI_NAME" --deployment-name "$DEPLOY_NAME" &>/dev/null; then
            echo -e "${GREEN}    ✓ Deployment $DEPLOY_NAME already exists${NC}"
        else
            az cognitiveservices account deployment create \
                --resource-group "$RESOURCE_GROUP" \
                --name "$OPENAI_NAME" \
                --deployment-name "$DEPLOY_NAME" \
                --model-name "$MODEL_NAME" \
                --model-version "$MODEL_VERSION" \
                --model-format OpenAI \
                --sku-name Standard \
                --sku-capacity "$CAPACITY" \
                --output none 2>/dev/null || echo -e "${YELLOW}    ! Deployment $DEPLOY_NAME may need manual setup${NC}"
            echo -e "${GREEN}    ✓ Created deployment: $DEPLOY_NAME${NC}"
        fi
    done
else
    echo -e "\n${YELLOW}[5/9] Skipping Azure OpenAI (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 6. Create AI Search
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.ai_search.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[6/9] Creating AI Search...${NC}"

    SEARCH_SKU=$(jq -r '.resources.ai_search.sku' "$CONFIG_FILE")
    REPLICA_COUNT=$(jq -r '.resources.ai_search.replica_count' "$CONFIG_FILE")
    PARTITION_COUNT=$(jq -r '.resources.ai_search.partition_count' "$CONFIG_FILE")

    if az search service show -g "$RESOURCE_GROUP" -n "$SEARCH_NAME" &>/dev/null; then
        echo -e "${GREEN}  ✓ AI Search already exists${NC}"
    else
        az search service create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$SEARCH_NAME" \
            --location "$LOCATION" \
            --sku "$SEARCH_SKU" \
            --replica-count "$REPLICA_COUNT" \
            --partition-count "$PARTITION_COUNT" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created AI Search: $SEARCH_NAME${NC}"
    fi
else
    echo -e "\n${YELLOW}[6/9] Skipping AI Search (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 7. Create Cosmos DB
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.cosmos_db.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[7/9] Creating Cosmos DB...${NC}"

    COSMOS_KIND=$(jq -r '.resources.cosmos_db.kind' "$CONFIG_FILE")
    CONSISTENCY=$(jq -r '.resources.cosmos_db.consistency_level' "$CONFIG_FILE")

    if az cosmosdb show -g "$RESOURCE_GROUP" -n "$COSMOS_NAME" &>/dev/null; then
        echo -e "${GREEN}  ✓ Cosmos DB already exists${NC}"
    else
        az cosmosdb create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$COSMOS_NAME" \
            --locations regionName="$LOCATION" failoverPriority=0 \
            --default-consistency-level "$CONSISTENCY" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Cosmos DB: $COSMOS_NAME${NC}"
    fi

    # Create databases
    echo -e "  Creating databases..."
    jq -c '.resources.cosmos_db.databases[]' "$CONFIG_FILE" | while read -r db; do
        DB_NAME=$(echo "$db" | jq -r '.name')
        THROUGHPUT=$(echo "$db" | jq -r '.throughput')

        if az cosmosdb sql database show -g "$RESOURCE_GROUP" -a "$COSMOS_NAME" -n "$DB_NAME" &>/dev/null; then
            echo -e "${GREEN}    ✓ Database $DB_NAME already exists${NC}"
        else
            az cosmosdb sql database create \
                --resource-group "$RESOURCE_GROUP" \
                --account-name "$COSMOS_NAME" \
                --name "$DB_NAME" \
                --throughput "$THROUGHPUT" \
                --output none
            echo -e "${GREEN}    ✓ Created database: $DB_NAME${NC}"
        fi
    done
else
    echo -e "\n${YELLOW}[7/9] Skipping Cosmos DB (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 8. Create Function App
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.function_app.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[8/9] Creating Function App...${NC}"

    RUNTIME=$(jq -r '.resources.function_app.runtime' "$CONFIG_FILE")
    RUNTIME_VERSION=$(jq -r '.resources.function_app.runtime_version' "$CONFIG_FILE")

    # Create App Service Plan (if needed)
    PLAN_NAME="${PROJECT_NAME}-${ENVIRONMENT}-plan"

    if ! az functionapp plan show -g "$RESOURCE_GROUP" -n "$PLAN_NAME" &>/dev/null; then
        az functionapp plan create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$PLAN_NAME" \
            --location "$LOCATION" \
            --sku EP1 \
            --is-linux true \
            --output none
        echo -e "${GREEN}  ✓ Created App Service Plan: $PLAN_NAME${NC}"
    fi

    if az functionapp show -g "$RESOURCE_GROUP" -n "$FUNCTION_APP" &>/dev/null; then
        echo -e "${GREEN}  ✓ Function App already exists${NC}"
    else
        az functionapp create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$FUNCTION_APP" \
            --storage-account "$STORAGE_ACCOUNT" \
            --plan "$PLAN_NAME" \
            --runtime "$RUNTIME" \
            --runtime-version "$RUNTIME_VERSION" \
            --functions-version 4 \
            --os-type Linux \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created Function App: $FUNCTION_APP${NC}"
    fi
else
    echo -e "\n${YELLOW}[8/9] Skipping Function App (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# 9. Create ML Workspace
#-------------------------------------------------------------------------------
if [ "$(jq -r '.resources.ml_workspace.enabled' "$CONFIG_FILE")" == "true" ]; then
    echo -e "\n${YELLOW}[9/9] Creating ML Workspace...${NC}"

    if az ml workspace show -g "$RESOURCE_GROUP" -n "$ML_WORKSPACE" &>/dev/null; then
        echo -e "${GREEN}  ✓ ML Workspace already exists${NC}"
    else
        # ML workspace needs Application Insights
        APP_INSIGHTS="${PROJECT_NAME}-${ENVIRONMENT}-insights"

        az monitor app-insights component create \
            --resource-group "$RESOURCE_GROUP" \
            --app "$APP_INSIGHTS" \
            --location "$LOCATION" \
            --kind web \
            --application-type web \
            --output none 2>/dev/null || true

        az ml workspace create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$ML_WORKSPACE" \
            --location "$LOCATION" \
            --storage-account "$STORAGE_ACCOUNT" \
            --key-vault "$KEY_VAULT" \
            --application-insights "$APP_INSIGHTS" \
            --tags $TAGS \
            --output none
        echo -e "${GREEN}  ✓ Created ML Workspace: $ML_WORKSPACE${NC}"
    fi
else
    echo -e "\n${YELLOW}[9/9] Skipping ML Workspace (disabled)${NC}"
fi

#-------------------------------------------------------------------------------
# Generate Output
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Resource Creation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

OUTPUT_FILE="./created_resources_$(date +%Y%m%d_%H%M%S).json"
cat > "$OUTPUT_FILE" << EOF
{
  "created_at": "$(date -Iseconds)",
  "project_name": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "location": "$LOCATION",
  "resources": {
    "resource_group": "$RESOURCE_GROUP",
    "storage_account": "$STORAGE_ACCOUNT",
    "key_vault": "$KEY_VAULT",
    "openai": "$OPENAI_NAME",
    "ai_search": "$SEARCH_NAME",
    "cosmos_db": "$COSMOS_NAME",
    "function_app": "$FUNCTION_APP",
    "ml_workspace": "$ML_WORKSPACE",
    "vnet": "$VNET_NAME"
  }
}
EOF

echo -e "Resource details saved to: ${BLUE}$OUTPUT_FILE${NC}"
