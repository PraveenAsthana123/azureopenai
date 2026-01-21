#!/bin/bash
# Setup Azure AI Search Index

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
ENVIRONMENT="dev"
RESOURCE_GROUP=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -e, --environment    Environment (dev, staging, prod). Default: dev"
            echo "  -g, --resource-group Azure resource group name"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Setting up Azure AI Search Index"
print_status "Environment: $ENVIRONMENT"

# Get resource group from Terraform if not specified
if [[ -z "$RESOURCE_GROUP" ]]; then
    cd "$PROJECT_ROOT/infrastructure/terraform"
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
fi

if [[ -z "$RESOURCE_GROUP" ]]; then
    print_error "Resource group not found. Please specify with -g option."
    exit 1
fi

print_status "Resource Group: $RESOURCE_GROUP"

# Get search service details
SEARCH_SERVICE_NAME=$(az search service list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
SEARCH_ADMIN_KEY=$(az search admin-key show --resource-group "$RESOURCE_GROUP" --service-name "$SEARCH_SERVICE_NAME" --query "primaryKey" -o tsv)

if [[ -z "$SEARCH_SERVICE_NAME" ]]; then
    print_error "Search service not found in resource group $RESOURCE_GROUP"
    exit 1
fi

print_status "Search Service: $SEARCH_SERVICE_NAME"

# Create index
INDEX_FILE="$PROJECT_ROOT/configs/search-indexes/documents-index.json"
SEARCH_ENDPOINT="https://${SEARCH_SERVICE_NAME}.search.windows.net"

print_status "Creating search index..."

# Check if index exists
INDEX_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "api-key: $SEARCH_ADMIN_KEY" \
    -H "Content-Type: application/json" \
    "${SEARCH_ENDPOINT}/indexes/documents-index?api-version=2024-07-01")

if [[ "$INDEX_EXISTS" == "200" ]]; then
    print_warning "Index already exists. Updating..."
    HTTP_METHOD="PUT"
    URL="${SEARCH_ENDPOINT}/indexes/documents-index?api-version=2024-07-01"
else
    print_status "Creating new index..."
    HTTP_METHOD="POST"
    URL="${SEARCH_ENDPOINT}/indexes?api-version=2024-07-01"
fi

# Create or update index
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X "$HTTP_METHOD" \
    -H "api-key: $SEARCH_ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d @"$INDEX_FILE" \
    "$URL")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "201" ]]; then
    print_status "Index created/updated successfully!"
else
    print_error "Failed to create index. HTTP Code: $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

# Create skillset for document enrichment (optional)
print_status "Creating skillset for document enrichment..."

SKILLSET_JSON=$(cat << 'EOF'
{
  "name": "document-skillset",
  "description": "Skillset for document processing",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "text-split",
      "description": "Split text into chunks",
      "context": "/document",
      "textSplitMode": "pages",
      "maximumPageLength": 2000,
      "pageOverlapLength": 500,
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "textItems",
          "targetName": "chunks"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
      "name": "key-phrase-extraction",
      "description": "Extract key phrases",
      "context": "/document/chunks/*",
      "inputs": [
        {
          "name": "text",
          "source": "/document/chunks/*"
        }
      ],
      "outputs": [
        {
          "name": "keyPhrases",
          "targetName": "keyPhrases"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
      "name": "language-detection",
      "description": "Detect language",
      "context": "/document",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "languageCode",
          "targetName": "language"
        }
      ]
    }
  ]
}
EOF
)

curl -s -X PUT \
    -H "api-key: $SEARCH_ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d "$SKILLSET_JSON" \
    "${SEARCH_ENDPOINT}/skillsets/document-skillset?api-version=2024-07-01" > /dev/null

print_status "Skillset created/updated!"

print_status "Search index setup complete!"
echo ""
echo "Index Details:"
echo "  Name: documents-index"
echo "  Endpoint: $SEARCH_ENDPOINT"
echo "  Service: $SEARCH_SERVICE_NAME"
