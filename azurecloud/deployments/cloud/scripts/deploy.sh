#!/bin/bash
# =============================================================================
# RAG Platform Cloud Deployment Script
# =============================================================================
# Usage: ./deploy.sh <environment> [resource_group] [location]
# Example: ./deploy.sh prod rg-rag-prod eastus2

set -e

# =============================================================================
# Configuration
# =============================================================================

ENVIRONMENT=${1:-prod}
RESOURCE_GROUP=${2:-rg-rag-$ENVIRONMENT}
LOCATION=${3:-eastus2}
BASE_NAME="rag"

echo "=============================================="
echo "RAG Platform Cloud Deployment"
echo "=============================================="
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "=============================================="

# =============================================================================
# Pre-flight Checks
# =============================================================================

echo "Checking prerequisites..."

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "ERROR: Azure CLI not found. Install from https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check Azure Functions Core Tools
if ! command -v func &> /dev/null; then
    echo "WARNING: Azure Functions Core Tools not found. Install for local testing."
fi

# Check login status
az account show &> /dev/null || {
    echo "Not logged in to Azure. Running 'az login'..."
    az login
}

echo "Logged in as: $(az account show --query user.name -o tsv)"
echo "Subscription: $(az account show --query name -o tsv)"

# Confirm deployment
read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# =============================================================================
# Create Resource Group
# =============================================================================

echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags Environment="$ENVIRONMENT" Application="RAG Platform"

# =============================================================================
# Deploy Infrastructure
# =============================================================================

echo "Deploying infrastructure (this may take 10-15 minutes)..."

DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infrastructure/main.bicep \
    --parameters environment="$ENVIRONMENT" \
    --parameters baseName="$BASE_NAME" \
    --parameters enablePrivateEndpoints=true \
    --query properties.outputs -o json)

# Extract outputs
FUNCTION_APP_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.functionAppName.value')
FUNCTION_APP_URL=$(echo $DEPLOYMENT_OUTPUT | jq -r '.functionAppUrl.value')
OPENAI_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.openaiEndpoint.value')
SEARCH_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.searchEndpoint.value')
COSMOS_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.cosmosEndpoint.value')
STORAGE_ACCOUNT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.storageAccountName.value')
APP_INSIGHTS_CS=$(echo $DEPLOYMENT_OUTPUT | jq -r '.appInsightsConnectionString.value')

echo "Infrastructure deployed successfully!"
echo "Function App: $FUNCTION_APP_NAME"
echo "Function URL: $FUNCTION_APP_URL"

# =============================================================================
# Create Azure Search Index
# =============================================================================

echo "Creating Azure Search index..."

# Get search admin key
SEARCH_KEY=$(az search admin-key show \
    --resource-group "$RESOURCE_GROUP" \
    --service-name "search-$BASE_NAME-$ENVIRONMENT-*" \
    --query primaryKey -o tsv 2>/dev/null || echo "")

if [ -n "$SEARCH_KEY" ]; then
    # Create index using REST API
    SEARCH_SERVICE=$(az search service list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)

    curl -X PUT "https://$SEARCH_SERVICE.search.windows.net/indexes/rag-multimodal-index?api-version=2023-11-01" \
        -H "Content-Type: application/json" \
        -H "api-key: $SEARCH_KEY" \
        -d @infrastructure/search-index.json 2>/dev/null || echo "Index creation via REST failed, may need manual setup"
fi

# =============================================================================
# Deploy Azure Functions
# =============================================================================

echo "Deploying Azure Functions..."

cd src/functions

# Install dependencies
pip install -r requirements.txt -q

# Publish to Azure
func azure functionapp publish "$FUNCTION_APP_NAME" --python

cd ../..

echo "Functions deployed successfully!"

# =============================================================================
# Verify Deployment
# =============================================================================

echo "Verifying deployment..."

# Wait for function to warm up
sleep 10

# Health check
HEALTH_STATUS=$(curl -s "$FUNCTION_APP_URL/api/health" | jq -r '.status' 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo "✅ Health check passed!"
else
    echo "⚠️ Health check returned: $HEALTH_STATUS"
    echo "Some services may still be initializing..."
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo ""
echo "Resources Created:"
echo "  - Function App: $FUNCTION_APP_NAME"
echo "  - Azure OpenAI: $(echo $OPENAI_ENDPOINT | sed 's/https:\/\///' | sed 's/\/.*//')"
echo "  - Azure Search: $(echo $SEARCH_ENDPOINT | sed 's/https:\/\///' | sed 's/\/.*//')"
echo "  - Cosmos DB: $(echo $COSMOS_ENDPOINT | sed 's/https:\/\///' | sed 's/:443\/.*//')"
echo "  - Storage: $STORAGE_ACCOUNT"
echo ""
echo "API Endpoints:"
echo "  - Chat: $FUNCTION_APP_URL/api/chat"
echo "  - Ingest: $FUNCTION_APP_URL/api/ingest"
echo "  - Health: $FUNCTION_APP_URL/api/health"
echo ""
echo "Next Steps:"
echo "  1. Configure Entra ID authentication (optional)"
echo "  2. Set up custom domain (optional)"
echo "  3. Configure alerts in Azure Monitor"
echo "  4. Test the API with sample documents"
echo ""
echo "Test the API:"
echo "  curl -X POST $FUNCTION_APP_URL/api/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"question\": \"Hello, how are you?\", \"user_id\": \"test\"}'"
echo ""
