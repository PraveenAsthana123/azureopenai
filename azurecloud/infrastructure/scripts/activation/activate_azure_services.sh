#!/bin/bash
#===============================================================================
# Azure Service Activation Script
# Registers resource providers and enables required Azure services
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Azure Service Activation Tool${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure. Run 'az login' first.${NC}"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo -e "\n${YELLOW}Subscription: $SUBSCRIPTION_NAME${NC}"
echo -e "${YELLOW}Subscription ID: $SUBSCRIPTION_ID${NC}"

#-------------------------------------------------------------------------------
# Resource Providers for AI/ML Platform
#-------------------------------------------------------------------------------
REQUIRED_PROVIDERS=(
    # Core Infrastructure
    "Microsoft.Resources"
    "Microsoft.Storage"
    "Microsoft.Network"
    "Microsoft.Compute"
    "Microsoft.ManagedIdentity"
    "Microsoft.Authorization"

    # AI/ML Services
    "Microsoft.CognitiveServices"          # Azure OpenAI, AI Services
    "Microsoft.MachineLearningServices"    # Azure ML, AI Foundry
    "Microsoft.Search"                     # AI Search

    # Data Services
    "Microsoft.DocumentDB"                 # Cosmos DB
    "Microsoft.Sql"                        # Azure SQL
    "Microsoft.Synapse"                    # Synapse Analytics
    "Microsoft.DataFactory"                # Data Factory
    "Microsoft.EventHub"                   # Event Hubs
    "Microsoft.StreamAnalytics"            # Stream Analytics

    # Compute Services
    "Microsoft.Web"                        # App Service, Functions
    "Microsoft.ContainerRegistry"          # ACR
    "Microsoft.ContainerService"           # AKS
    "Microsoft.ContainerInstance"          # Container Instances

    # Integration & Messaging
    "Microsoft.Logic"                      # Logic Apps
    "Microsoft.ServiceBus"                 # Service Bus
    "Microsoft.EventGrid"                  # Event Grid
    "Microsoft.SignalRService"             # SignalR
    "Microsoft.ApiManagement"              # APIM

    # Security & Identity
    "Microsoft.KeyVault"                   # Key Vault
    "Microsoft.AAD"                        # Azure Active Directory
    "Microsoft.Security"                   # Security Center

    # Monitoring & Management
    "Microsoft.Insights"                   # Application Insights, Monitor
    "Microsoft.OperationalInsights"        # Log Analytics
    "Microsoft.AlertsManagement"           # Alerts
    "Microsoft.Dashboard"                  # Managed Grafana

    # IoT (for IoT projects)
    "Microsoft.Devices"                    # IoT Hub
    "Microsoft.IoTCentral"                 # IoT Central

    # Additional AI Services
    "Microsoft.BotService"                 # Bot Service
    "Microsoft.Purview"                    # Data Governance
)

#-------------------------------------------------------------------------------
# Check and Register Providers
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}Checking Resource Provider Registration...${NC}"
echo -e "Total providers to check: ${#REQUIRED_PROVIDERS[@]}"
echo ""

REGISTERED=0
REGISTERING=0
FAILED=0

for provider in "${REQUIRED_PROVIDERS[@]}"; do
    STATUS=$(az provider show -n "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "NotFound")

    case "$STATUS" in
        "Registered")
            echo -e "${GREEN}  ✓ $provider${NC}"
            ((REGISTERED++))
            ;;
        "Registering")
            echo -e "${YELLOW}  ⟳ $provider (registering...)${NC}"
            ((REGISTERING++))
            ;;
        "NotRegistered"|"Unregistered")
            echo -e "${YELLOW}  → Registering $provider...${NC}"
            if az provider register -n "$provider" --wait 2>/dev/null; then
                echo -e "${GREEN}    ✓ Registered $provider${NC}"
                ((REGISTERED++))
            else
                echo -e "${RED}    ✗ Failed to register $provider${NC}"
                ((FAILED++))
            fi
            ;;
        *)
            echo -e "${RED}  ✗ $provider (Status: $STATUS)${NC}"
            ((FAILED++))
            ;;
    esac
done

echo ""
echo -e "${GREEN}Registered: $REGISTERED${NC}"
echo -e "${YELLOW}Registering: $REGISTERING${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

#-------------------------------------------------------------------------------
# Check Feature Flags
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}Checking Feature Flags...${NC}"

# Important feature flags for AI services
FEATURES=(
    "Microsoft.CognitiveServices/AIServicesLegacy"
    "Microsoft.MachineLearningServices/WorkspaceAllowLLM"
)

for feature in "${FEATURES[@]}"; do
    IFS='/' read -r namespace feature_name <<< "$feature"
    STATUS=$(az feature show --namespace "$namespace" --name "$feature_name" --query "properties.state" -o tsv 2>/dev/null || echo "NotFound")

    case "$STATUS" in
        "Registered")
            echo -e "${GREEN}  ✓ $feature${NC}"
            ;;
        "NotRegistered"|"Unregistered")
            echo -e "${YELLOW}  → Requesting $feature...${NC}"
            az feature register --namespace "$namespace" --name "$feature_name" 2>/dev/null || true
            ;;
        *)
            echo -e "${YELLOW}  ? $feature (Status: $STATUS)${NC}"
            ;;
    esac
done

#-------------------------------------------------------------------------------
# List Available Locations for AI Services
#-------------------------------------------------------------------------------
echo -e "\n${YELLOW}Available Locations for Key AI Services:${NC}"

echo -e "\n  ${BLUE}Azure OpenAI:${NC}"
az cognitiveservices account list-skus --kind OpenAI --query "[].locations[]" -o tsv 2>/dev/null | sort -u | head -10 | while read loc; do
    echo -e "    - $loc"
done

echo -e "\n  ${BLUE}AI Search:${NC}"
az provider show -n Microsoft.Search --query "resourceTypes[?resourceType=='searchServices'].locations[]" -o tsv 2>/dev/null | head -10 | while read loc; do
    echo -e "    - $loc"
done

#-------------------------------------------------------------------------------
# Generate Activation Report
#-------------------------------------------------------------------------------
REPORT_FILE="./activation_report_$(date +%Y%m%d_%H%M%S).md"

cat > "$REPORT_FILE" << EOF
# Azure Service Activation Report

**Generated:** $(date -Iseconds)
**Subscription:** $SUBSCRIPTION_NAME
**Subscription ID:** $SUBSCRIPTION_ID

## Registration Summary

| Status | Count |
|--------|-------|
| Registered | $REGISTERED |
| Registering | $REGISTERING |
| Failed | $FAILED |

## Resource Providers

EOF

for provider in "${REQUIRED_PROVIDERS[@]}"; do
    STATUS=$(az provider show -n "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "Unknown")
    echo "- \`$provider\`: $STATUS" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" << EOF

## Next Steps

1. Wait for any "Registering" providers to complete
2. For failed providers, check subscription permissions
3. Some providers may require specific subscription types (Enterprise, Pay-as-you-go)

## Quota Recommendations

For AI/ML workloads, consider requesting quota increases for:

| Resource | Recommended Quota |
|----------|------------------|
| Azure OpenAI GPT-4o TPM | 100K+ |
| Azure OpenAI Embeddings TPM | 500K+ |
| Azure ML Compute (CPU) | 100 cores |
| Azure ML Compute (GPU) | 10 GPUs |

Use: \`az quota create\` or Azure Portal to request increases.
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Service Activation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Report saved to: ${BLUE}$REPORT_FILE${NC}"
