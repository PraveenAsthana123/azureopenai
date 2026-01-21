#!/bin/bash
#===============================================================================
# Azure AI Foundry (AI Studio) Discovery Script
# Discovers AI Foundry hubs, projects, connections, and deployments
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

OUTPUT_DIR="${1:-./ai_foundry_discovery}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Azure AI Foundry Discovery Tool${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo -e "\n${YELLOW}Subscription: $SUBSCRIPTION_NAME${NC}"

#-------------------------------------------------------------------------------
# 1. Discover AI Foundry Hubs (Azure AI Hub)
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/8] Discovering AI Foundry Hubs...${NC}"

# AI Hubs are of type "Microsoft.MachineLearningServices/workspaces" with kind "Hub"
az resource list \
    --resource-type "Microsoft.MachineLearningServices/workspaces" \
    --query "[?kind=='Hub']" \
    --output json > "$OUTPUT_DIR/01_ai_hubs.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/01_ai_hubs.json"

HUB_COUNT=$(jq '. | length' "$OUTPUT_DIR/01_ai_hubs.json")
echo -e "${GREEN}  ✓ Found $HUB_COUNT AI Foundry Hubs${NC}"

if [ "$HUB_COUNT" -gt 0 ]; then
    echo -e "  Hubs discovered:"
    jq -r '.[] | "    - \(.name) (\(.location))"' "$OUTPUT_DIR/01_ai_hubs.json"
fi

#-------------------------------------------------------------------------------
# 2. Discover AI Foundry Projects
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/8] Discovering AI Foundry Projects...${NC}"

# AI Projects are of type "Microsoft.MachineLearningServices/workspaces" with kind "Project"
az resource list \
    --resource-type "Microsoft.MachineLearningServices/workspaces" \
    --query "[?kind=='Project']" \
    --output json > "$OUTPUT_DIR/02_ai_projects.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/02_ai_projects.json"

PROJECT_COUNT=$(jq '. | length' "$OUTPUT_DIR/02_ai_projects.json")
echo -e "${GREEN}  ✓ Found $PROJECT_COUNT AI Foundry Projects${NC}"

if [ "$PROJECT_COUNT" -gt 0 ]; then
    echo -e "  Projects discovered:"
    jq -r '.[] | "    - \(.name) (\(.resourceGroup))"' "$OUTPUT_DIR/02_ai_projects.json"
fi

#-------------------------------------------------------------------------------
# 3. Discover Azure OpenAI Services
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/8] Discovering Azure OpenAI Services...${NC}"

az cognitiveservices account list \
    --query "[?kind=='OpenAI']" \
    --output json > "$OUTPUT_DIR/03_openai_services.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/03_openai_services.json"

OPENAI_COUNT=$(jq '. | length' "$OUTPUT_DIR/03_openai_services.json")
echo -e "${GREEN}  ✓ Found $OPENAI_COUNT Azure OpenAI Services${NC}"

# Get deployments for each OpenAI service
echo "[]" > "$OUTPUT_DIR/03_openai_deployments.json"
if [ "$OPENAI_COUNT" -gt 0 ]; then
    echo -e "  Discovering model deployments..."

    jq -c '.[]' "$OUTPUT_DIR/03_openai_services.json" | while read -r service; do
        RG=$(echo "$service" | jq -r '.resourceGroup')
        NAME=$(echo "$service" | jq -r '.name')

        echo -e "    Checking $NAME..."
        DEPLOYMENTS=$(az cognitiveservices account deployment list -g "$RG" -n "$NAME" --output json 2>/dev/null || echo "[]")

        # Append to deployments file
        echo "$DEPLOYMENTS" | jq --arg name "$NAME" --arg rg "$RG" \
            '. | map(. + {openai_account: $name, resource_group: $rg})' >> "$OUTPUT_DIR/03_openai_deployments_temp.json"
    done

    # Merge all deployments
    if [ -f "$OUTPUT_DIR/03_openai_deployments_temp.json" ]; then
        jq -s 'add // []' "$OUTPUT_DIR/03_openai_deployments_temp.json" > "$OUTPUT_DIR/03_openai_deployments.json"
        rm -f "$OUTPUT_DIR/03_openai_deployments_temp.json"
    fi

    DEPLOY_COUNT=$(jq '. | length' "$OUTPUT_DIR/03_openai_deployments.json")
    echo -e "${GREEN}  ✓ Found $DEPLOY_COUNT model deployments${NC}"
fi

#-------------------------------------------------------------------------------
# 4. Discover Cognitive Services (AI Services)
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/8] Discovering Cognitive Services...${NC}"

az cognitiveservices account list \
    --output json > "$OUTPUT_DIR/04_cognitive_services.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/04_cognitive_services.json"

COG_COUNT=$(jq '. | length' "$OUTPUT_DIR/04_cognitive_services.json")
echo -e "${GREEN}  ✓ Found $COG_COUNT Cognitive Services accounts${NC}"

# Group by kind
echo -e "  Services by type:"
jq -r 'group_by(.kind) | .[] | "    - \(.[0].kind): \(. | length)"' "$OUTPUT_DIR/04_cognitive_services.json" 2>/dev/null || true

#-------------------------------------------------------------------------------
# 5. Discover AI Search Services
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/8] Discovering AI Search Services...${NC}"

az search service list \
    --output json > "$OUTPUT_DIR/05_ai_search.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/05_ai_search.json"

SEARCH_COUNT=$(jq '. | length' "$OUTPUT_DIR/05_ai_search.json")
echo -e "${GREEN}  ✓ Found $SEARCH_COUNT AI Search Services${NC}"

# Get indexes for each search service
echo "[]" > "$OUTPUT_DIR/05_ai_search_indexes.json"
if [ "$SEARCH_COUNT" -gt 0 ]; then
    echo -e "  Discovering search indexes..."

    jq -c '.[]' "$OUTPUT_DIR/05_ai_search.json" | while read -r service; do
        RG=$(echo "$service" | jq -r '.resourceGroup // empty')
        NAME=$(echo "$service" | jq -r '.name')

        if [ -n "$RG" ]; then
            # Get admin key to list indexes
            ADMIN_KEY=$(az search admin-key show -g "$RG" --service-name "$NAME" --query primaryKey -o tsv 2>/dev/null || echo "")

            if [ -n "$ADMIN_KEY" ]; then
                ENDPOINT="https://${NAME}.search.windows.net"
                INDEXES=$(curl -s -H "api-key: $ADMIN_KEY" "${ENDPOINT}/indexes?api-version=2023-11-01" 2>/dev/null | jq '.value // []')
                echo "$INDEXES" | jq --arg name "$NAME" \
                    '. | map(. + {search_service: $name})' >> "$OUTPUT_DIR/05_ai_search_indexes_temp.json"
            fi
        fi
    done

    if [ -f "$OUTPUT_DIR/05_ai_search_indexes_temp.json" ]; then
        jq -s 'add // []' "$OUTPUT_DIR/05_ai_search_indexes_temp.json" > "$OUTPUT_DIR/05_ai_search_indexes.json"
        rm -f "$OUTPUT_DIR/05_ai_search_indexes_temp.json"
    fi

    INDEX_COUNT=$(jq '. | length' "$OUTPUT_DIR/05_ai_search_indexes.json")
    echo -e "${GREEN}  ✓ Found $INDEX_COUNT search indexes${NC}"
fi

#-------------------------------------------------------------------------------
# 6. Discover Document Intelligence
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[6/8] Discovering Document Intelligence...${NC}"

az cognitiveservices account list \
    --query "[?kind=='FormRecognizer']" \
    --output json > "$OUTPUT_DIR/06_document_intelligence.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/06_document_intelligence.json"

DOC_COUNT=$(jq '. | length' "$OUTPUT_DIR/06_document_intelligence.json")
echo -e "${GREEN}  ✓ Found $DOC_COUNT Document Intelligence accounts${NC}"

#-------------------------------------------------------------------------------
# 7. Discover ML Workspaces (Traditional)
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[7/8] Discovering ML Workspaces...${NC}"

# Traditional ML workspaces have kind "Default" or no kind
az resource list \
    --resource-type "Microsoft.MachineLearningServices/workspaces" \
    --query "[?kind=='Default' || kind==null]" \
    --output json > "$OUTPUT_DIR/07_ml_workspaces.json" 2>/dev/null || echo "[]" > "$OUTPUT_DIR/07_ml_workspaces.json"

ML_COUNT=$(jq '. | length' "$OUTPUT_DIR/07_ml_workspaces.json")
echo -e "${GREEN}  ✓ Found $ML_COUNT ML Workspaces${NC}"

#-------------------------------------------------------------------------------
# 8. Discover AI Services Connections
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}[8/8] Discovering AI Service Connections...${NC}"

# For each hub/project, try to get connections
echo "[]" > "$OUTPUT_DIR/08_ai_connections.json"

if [ "$HUB_COUNT" -gt 0 ] || [ "$PROJECT_COUNT" -gt 0 ]; then
    # Combine hubs and projects
    jq -s 'add' "$OUTPUT_DIR/01_ai_hubs.json" "$OUTPUT_DIR/02_ai_projects.json" > "$OUTPUT_DIR/temp_workspaces.json"

    jq -c '.[]' "$OUTPUT_DIR/temp_workspaces.json" | while read -r workspace; do
        RG=$(echo "$workspace" | jq -r '.resourceGroup')
        NAME=$(echo "$workspace" | jq -r '.name')

        echo -e "    Checking connections for $NAME..."
        CONNECTIONS=$(az ml connection list -g "$RG" -w "$NAME" --output json 2>/dev/null || echo "[]")

        if [ "$CONNECTIONS" != "[]" ]; then
            echo "$CONNECTIONS" | jq --arg ws "$NAME" \
                '. | map(. + {workspace: $ws})' >> "$OUTPUT_DIR/08_ai_connections_temp.json"
        fi
    done

    rm -f "$OUTPUT_DIR/temp_workspaces.json"

    if [ -f "$OUTPUT_DIR/08_ai_connections_temp.json" ]; then
        jq -s 'add // []' "$OUTPUT_DIR/08_ai_connections_temp.json" > "$OUTPUT_DIR/08_ai_connections.json"
        rm -f "$OUTPUT_DIR/08_ai_connections_temp.json"
    fi

    CONN_COUNT=$(jq '. | length' "$OUTPUT_DIR/08_ai_connections.json")
    echo -e "${GREEN}  ✓ Found $CONN_COUNT AI connections${NC}"
fi

#-------------------------------------------------------------------------------
# Generate Terraform Variables for AI Foundry
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}Generating Terraform Variables...${NC}"

cat > "$OUTPUT_DIR/ai_foundry.tfvars" << EOF
# Azure AI Foundry Terraform Variables
# Auto-generated: $TIMESTAMP
# Subscription: $SUBSCRIPTION_NAME

subscription_id = "$SUBSCRIPTION_ID"

# AI Foundry Hubs
# Found: $HUB_COUNT hubs
EOF

if [ "$HUB_COUNT" -gt 0 ]; then
    echo -e "\n# Existing AI Hubs:" >> "$OUTPUT_DIR/ai_foundry.tfvars"
    jq -r '.[] | "# - \(.name) in \(.resourceGroup) (\(.location))"' "$OUTPUT_DIR/01_ai_hubs.json" >> "$OUTPUT_DIR/ai_foundry.tfvars"
fi

cat >> "$OUTPUT_DIR/ai_foundry.tfvars" << EOF

# AI Foundry Projects
# Found: $PROJECT_COUNT projects
EOF

if [ "$PROJECT_COUNT" -gt 0 ]; then
    echo -e "\n# Existing AI Projects:" >> "$OUTPUT_DIR/ai_foundry.tfvars"
    jq -r '.[] | "# - \(.name) in \(.resourceGroup)"' "$OUTPUT_DIR/02_ai_projects.json" >> "$OUTPUT_DIR/ai_foundry.tfvars"
fi

cat >> "$OUTPUT_DIR/ai_foundry.tfvars" << EOF

# Azure OpenAI Services
# Found: $OPENAI_COUNT services
EOF

if [ "$OPENAI_COUNT" -gt 0 ]; then
    echo -e "\n# Existing OpenAI Services:" >> "$OUTPUT_DIR/ai_foundry.tfvars"
    jq -r '.[] | "# - \(.name) (\(.sku.name)) in \(.location)"' "$OUTPUT_DIR/03_openai_services.json" >> "$OUTPUT_DIR/ai_foundry.tfvars"

    echo -e "\n# OpenAI Deployments:" >> "$OUTPUT_DIR/ai_foundry.tfvars"
    jq -r '.[] | "# - \(.name): \(.properties.model.name) v\(.properties.model.version // "latest") (capacity: \(.sku.capacity // "N/A"))"' "$OUTPUT_DIR/03_openai_deployments.json" >> "$OUTPUT_DIR/ai_foundry.tfvars" 2>/dev/null || true
fi

cat >> "$OUTPUT_DIR/ai_foundry.tfvars" << EOF

# AI Search Services
# Found: $SEARCH_COUNT services
EOF

if [ "$SEARCH_COUNT" -gt 0 ]; then
    echo -e "\n# Existing AI Search Services:" >> "$OUTPUT_DIR/ai_foundry.tfvars"
    jq -r '.[] | "# - \(.name) (\(.sku.name)) in \(.location // "N/A")"' "$OUTPUT_DIR/05_ai_search.json" >> "$OUTPUT_DIR/ai_foundry.tfvars"
fi

echo -e "${GREEN}  ✓ Generated ai_foundry.tfvars${NC}"

#-------------------------------------------------------------------------------
# Generate Summary Report
#-------------------------------------------------------------------------------
cat > "$OUTPUT_DIR/AI_FOUNDRY_SUMMARY.md" << EOF
# Azure AI Foundry Discovery Summary

**Generated:** $TIMESTAMP
**Subscription:** $SUBSCRIPTION_NAME
**Subscription ID:** $SUBSCRIPTION_ID

## Resource Counts

| Resource Type | Count |
|---------------|-------|
| AI Foundry Hubs | $HUB_COUNT |
| AI Foundry Projects | $PROJECT_COUNT |
| Azure OpenAI Services | $OPENAI_COUNT |
| Cognitive Services | $COG_COUNT |
| AI Search Services | $SEARCH_COUNT |
| Document Intelligence | $DOC_COUNT |
| ML Workspaces | $ML_COUNT |

## Files Generated

- \`01_ai_hubs.json\` - AI Foundry Hub resources
- \`02_ai_projects.json\` - AI Foundry Project resources
- \`03_openai_services.json\` - Azure OpenAI accounts
- \`03_openai_deployments.json\` - OpenAI model deployments
- \`04_cognitive_services.json\` - All Cognitive Services
- \`05_ai_search.json\` - AI Search services
- \`05_ai_search_indexes.json\` - Search indexes
- \`06_document_intelligence.json\` - Document Intelligence
- \`07_ml_workspaces.json\` - Traditional ML Workspaces
- \`08_ai_connections.json\` - AI service connections
- \`ai_foundry.tfvars\` - Terraform variables

## Next Steps

1. Review discovered resources
2. Use \`ai_foundry.tfvars\` as reference for Terraform configuration
3. Check connections and deployments for completeness
4. Plan any additional resources needed

## AI Foundry Architecture Reference

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                    AI FOUNDRY STRUCTURE                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              AI Foundry Hub                      │    │
│  │  - Shared resources (Storage, Key Vault)        │    │
│  │  - Connections to AI services                   │    │
│  │  - Compute resources                            │    │
│  │                                                  │    │
│  │  ┌─────────────────┐  ┌─────────────────────┐   │    │
│  │  │  AI Project 1   │  │    AI Project 2     │   │    │
│  │  │  - Experiments  │  │  - Experiments      │   │    │
│  │  │  - Deployments  │  │  - Deployments      │   │    │
│  │  │  - Data         │  │  - Data             │   │    │
│  │  └─────────────────┘  └─────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Connected Services:                                     │
│  ├── Azure OpenAI                                        │
│  ├── AI Search                                           │
│  ├── Document Intelligence                               │
│  └── Content Safety                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
\`\`\`
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  AI Foundry Discovery Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Output directory: ${BLUE}$OUTPUT_DIR${NC}"
echo -e "Summary: ${BLUE}$OUTPUT_DIR/AI_FOUNDRY_SUMMARY.md${NC}"
