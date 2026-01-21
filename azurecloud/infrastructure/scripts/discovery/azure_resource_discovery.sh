#!/bin/bash
#===============================================================================
# Azure Resource Discovery Script
# Discovers existing Azure resources and generates Terraform variable files
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output file
OUTPUT_DIR="${1:-./discovered_resources}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Azure Resource Discovery Tool${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

#-------------------------------------------------------------------------------
# 1. Subscription & Tenant Information
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/10] Discovering Subscription & Tenant Info...${NC}"

SUBSCRIPTION_INFO=$(az account show --output json)
SUBSCRIPTION_ID=$(echo $SUBSCRIPTION_INFO | jq -r '.id')
SUBSCRIPTION_NAME=$(echo $SUBSCRIPTION_INFO | jq -r '.name')
TENANT_ID=$(echo $SUBSCRIPTION_INFO | jq -r '.tenantId')

cat > "$OUTPUT_DIR/01_subscription_info.json" << EOF
{
  "subscription_id": "$SUBSCRIPTION_ID",
  "subscription_name": "$SUBSCRIPTION_NAME",
  "tenant_id": "$TENANT_ID",
  "discovered_at": "$TIMESTAMP"
}
EOF

echo -e "${GREEN}  ✓ Subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)${NC}"

#-------------------------------------------------------------------------------
# 2. Resource Groups
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/10] Discovering Resource Groups...${NC}"

az group list --output json > "$OUTPUT_DIR/02_resource_groups.json"
RG_COUNT=$(jq '. | length' "$OUTPUT_DIR/02_resource_groups.json")
echo -e "${GREEN}  ✓ Found $RG_COUNT resource groups${NC}"

#-------------------------------------------------------------------------------
# 3. Azure OpenAI Resources
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/10] Discovering Azure OpenAI Resources...${NC}"

az cognitiveservices account list --query "[?kind=='OpenAI']" --output json > "$OUTPUT_DIR/03_openai_resources.json"
OPENAI_COUNT=$(jq '. | length' "$OUTPUT_DIR/03_openai_resources.json")
echo -e "${GREEN}  ✓ Found $OPENAI_COUNT Azure OpenAI resources${NC}"

# Get deployments for each OpenAI resource
echo "[]" > "$OUTPUT_DIR/03_openai_deployments.json"
for rg in $(jq -r '.[].resourceGroup' "$OUTPUT_DIR/03_openai_resources.json" 2>/dev/null); do
    for name in $(jq -r ".[] | select(.resourceGroup==\"$rg\") | .name" "$OUTPUT_DIR/03_openai_resources.json" 2>/dev/null); do
        echo -e "  Checking deployments for $name..."
        az cognitiveservices account deployment list -g "$rg" -n "$name" --output json 2>/dev/null >> "$OUTPUT_DIR/03_openai_deployments.json" || true
    done
done

#-------------------------------------------------------------------------------
# 4. AI Search Resources
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/10] Discovering AI Search Resources...${NC}"

az search service list --output json > "$OUTPUT_DIR/04_ai_search.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/04_ai_search.json"
SEARCH_COUNT=$(jq '. | length' "$OUTPUT_DIR/04_ai_search.json")
echo -e "${GREEN}  ✓ Found $SEARCH_COUNT AI Search services${NC}"

#-------------------------------------------------------------------------------
# 5. Storage Accounts
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/10] Discovering Storage Accounts...${NC}"

az storage account list --output json > "$OUTPUT_DIR/05_storage_accounts.json"
STORAGE_COUNT=$(jq '. | length' "$OUTPUT_DIR/05_storage_accounts.json")
echo -e "${GREEN}  ✓ Found $STORAGE_COUNT storage accounts${NC}"

#-------------------------------------------------------------------------------
# 6. Azure ML Workspaces
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[6/10] Discovering Azure ML Workspaces...${NC}"

az ml workspace list --output json > "$OUTPUT_DIR/06_ml_workspaces.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/06_ml_workspaces.json"
ML_COUNT=$(jq '. | length' "$OUTPUT_DIR/06_ml_workspaces.json")
echo -e "${GREEN}  ✓ Found $ML_COUNT ML workspaces${NC}"

#-------------------------------------------------------------------------------
# 7. Key Vaults
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[7/10] Discovering Key Vaults...${NC}"

az keyvault list --output json > "$OUTPUT_DIR/07_key_vaults.json"
KV_COUNT=$(jq '. | length' "$OUTPUT_DIR/07_key_vaults.json")
echo -e "${GREEN}  ✓ Found $KV_COUNT Key Vaults${NC}"

#-------------------------------------------------------------------------------
# 8. Virtual Networks
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[8/10] Discovering Virtual Networks...${NC}"

az network vnet list --output json > "$OUTPUT_DIR/08_vnets.json"
VNET_COUNT=$(jq '. | length' "$OUTPUT_DIR/08_vnets.json")
echo -e "${GREEN}  ✓ Found $VNET_COUNT Virtual Networks${NC}"

#-------------------------------------------------------------------------------
# 9. Function Apps
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[9/10] Discovering Function Apps...${NC}"

az functionapp list --output json > "$OUTPUT_DIR/09_function_apps.json"
FUNC_COUNT=$(jq '. | length' "$OUTPUT_DIR/09_function_apps.json")
echo -e "${GREEN}  ✓ Found $FUNC_COUNT Function Apps${NC}"

#-------------------------------------------------------------------------------
# 10. Cosmos DB Accounts
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[10/10] Discovering Cosmos DB Accounts...${NC}"

az cosmosdb list --output json > "$OUTPUT_DIR/10_cosmosdb.json"
COSMOS_COUNT=$(jq '. | length' "$OUTPUT_DIR/10_cosmosdb.json")
echo -e "${GREEN}  ✓ Found $COSMOS_COUNT Cosmos DB accounts${NC}"

#-------------------------------------------------------------------------------
# Generate Terraform Variables File
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}Generating Terraform Variables...${NC}"

cat > "$OUTPUT_DIR/terraform.tfvars" << EOF
# Auto-generated Terraform Variables
# Generated: $TIMESTAMP
# Subscription: $SUBSCRIPTION_NAME

subscription_id = "$SUBSCRIPTION_ID"
tenant_id       = "$TENANT_ID"

# Resource counts discovered:
# - Resource Groups: $RG_COUNT
# - Azure OpenAI: $OPENAI_COUNT
# - AI Search: $SEARCH_COUNT
# - Storage Accounts: $STORAGE_COUNT
# - ML Workspaces: $ML_COUNT
# - Key Vaults: $KV_COUNT
# - VNets: $VNET_COUNT
# - Function Apps: $FUNC_COUNT
# - Cosmos DB: $COSMOS_COUNT

# Existing resources (uncomment and modify as needed):
EOF

# Add existing OpenAI resources
if [ "$OPENAI_COUNT" -gt 0 ]; then
    echo -e "\n# Existing Azure OpenAI Resources:" >> "$OUTPUT_DIR/terraform.tfvars"
    jq -r '.[] | "# - \(.name) in \(.resourceGroup) (\(.location))"' "$OUTPUT_DIR/03_openai_resources.json" >> "$OUTPUT_DIR/terraform.tfvars"
fi

# Add existing resource groups
echo -e "\n# Existing Resource Groups:" >> "$OUTPUT_DIR/terraform.tfvars"
jq -r '.[] | "# - \(.name) (\(.location))"' "$OUTPUT_DIR/02_resource_groups.json" >> "$OUTPUT_DIR/terraform.tfvars"

echo -e "${GREEN}  ✓ Generated terraform.tfvars${NC}"

#-------------------------------------------------------------------------------
# Generate Summary Report
#-------------------------------------------------------------------------------
cat > "$OUTPUT_DIR/DISCOVERY_SUMMARY.md" << EOF
# Azure Resource Discovery Summary

**Generated:** $TIMESTAMP
**Subscription:** $SUBSCRIPTION_NAME
**Subscription ID:** $SUBSCRIPTION_ID
**Tenant ID:** $TENANT_ID

## Resource Counts

| Resource Type | Count |
|---------------|-------|
| Resource Groups | $RG_COUNT |
| Azure OpenAI | $OPENAI_COUNT |
| AI Search | $SEARCH_COUNT |
| Storage Accounts | $STORAGE_COUNT |
| ML Workspaces | $ML_COUNT |
| Key Vaults | $KV_COUNT |
| Virtual Networks | $VNET_COUNT |
| Function Apps | $FUNC_COUNT |
| Cosmos DB | $COSMOS_COUNT |

## Files Generated

- \`01_subscription_info.json\` - Subscription details
- \`02_resource_groups.json\` - All resource groups
- \`03_openai_resources.json\` - Azure OpenAI accounts
- \`03_openai_deployments.json\` - OpenAI model deployments
- \`04_ai_search.json\` - AI Search services
- \`05_storage_accounts.json\` - Storage accounts
- \`06_ml_workspaces.json\` - ML workspaces
- \`07_key_vaults.json\` - Key Vaults
- \`08_vnets.json\` - Virtual Networks
- \`09_function_apps.json\` - Function Apps
- \`10_cosmosdb.json\` - Cosmos DB accounts
- \`terraform.tfvars\` - Generated Terraform variables

## Next Steps

1. Review discovered resources
2. Copy \`terraform.tfvars\` to your Terraform project
3. Modify variables as needed for your deployment
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Discovery Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Output directory: ${BLUE}$OUTPUT_DIR${NC}"
echo -e "Summary: ${BLUE}$OUTPUT_DIR/DISCOVERY_SUMMARY.md${NC}"
