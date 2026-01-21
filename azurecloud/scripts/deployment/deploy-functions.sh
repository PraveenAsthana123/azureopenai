#!/bin/bash
# Deploy Azure Functions from desktop to Azure Cloud

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FUNCTIONS_DIR="$PROJECT_ROOT/backend/azure-functions"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}"; }

# Default values
ENVIRONMENT="dev"
FUNCTION_APP=""
RESOURCE_GROUP=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -f|--function)
            FUNCTION_APP="$2"
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
            echo "  -e, --environment     Environment (dev, staging, prod). Default: dev"
            echo "  -f, --function        Specific function app to deploy (api-gateway, orchestrator, ingestion, rag-processor)"
            echo "  -g, --resource-group  Azure resource group name"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_header "Azure Functions Deployment"
print_status "Environment: $ENVIRONMENT"

# Get Terraform outputs if resource group not specified
if [[ -z "$RESOURCE_GROUP" ]]; then
    cd "$PROJECT_ROOT/infrastructure/terraform"
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")

    if [[ -z "$RESOURCE_GROUP" ]]; then
        print_error "Could not get resource group from Terraform. Please specify with -g option."
        exit 1
    fi
fi

print_status "Resource Group: $RESOURCE_GROUP"

# Function to deploy a single function app
deploy_function() {
    local func_name=$1
    local func_dir=$2
    local azure_name=$3

    print_status "Deploying $func_name..."

    cd "$func_dir"

    # Create virtual environment and install dependencies
    if [[ -f "requirements.txt" ]]; then
        print_status "Installing Python dependencies..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt -q
        deactivate
    fi

    # Deploy using Azure Functions Core Tools
    print_status "Publishing to Azure..."
    func azure functionapp publish "$azure_name" --python

    print_status "$func_name deployed successfully!"
}

# Get function app names from Terraform
get_function_names() {
    cd "$PROJECT_ROOT/infrastructure/terraform"

    API_GATEWAY_NAME=$(terraform output -json function_app_names 2>/dev/null | jq -r '.api_gateway' || echo "")
    ORCHESTRATOR_NAME=$(terraform output -json function_app_names 2>/dev/null | jq -r '.orchestrator' || echo "")
    INGESTION_NAME=$(terraform output -json function_app_names 2>/dev/null | jq -r '.ingestion' || echo "")
    RAG_PROCESSOR_NAME=$(terraform output -json function_app_names 2>/dev/null | jq -r '.rag_processor' || echo "")
}

# Deploy all or specific function
get_function_names

if [[ -n "$FUNCTION_APP" ]]; then
    case $FUNCTION_APP in
        api-gateway)
            deploy_function "API Gateway" "$FUNCTIONS_DIR/api-gateway" "$API_GATEWAY_NAME"
            ;;
        orchestrator)
            deploy_function "Orchestrator" "$FUNCTIONS_DIR/orchestrator" "$ORCHESTRATOR_NAME"
            ;;
        ingestion)
            deploy_function "Ingestion Pipeline" "$FUNCTIONS_DIR/ingestion" "$INGESTION_NAME"
            ;;
        rag-processor)
            deploy_function "RAG Processor" "$FUNCTIONS_DIR/rag-processor" "$RAG_PROCESSOR_NAME"
            ;;
        *)
            print_error "Unknown function app: $FUNCTION_APP"
            exit 1
            ;;
    esac
else
    # Deploy all functions
    print_status "Deploying all function apps..."

    deploy_function "API Gateway" "$FUNCTIONS_DIR/api-gateway" "$API_GATEWAY_NAME"
    deploy_function "Orchestrator" "$FUNCTIONS_DIR/orchestrator" "$ORCHESTRATOR_NAME"
    deploy_function "Ingestion Pipeline" "$FUNCTIONS_DIR/ingestion" "$INGESTION_NAME"
    deploy_function "RAG Processor" "$FUNCTIONS_DIR/rag-processor" "$RAG_PROCESSOR_NAME"
fi

print_header "Deployment Complete"

# Show function URLs
print_status "Function App URLs:"
echo "  API Gateway:    https://$API_GATEWAY_NAME.azurewebsites.net"
echo "  Orchestrator:   https://$ORCHESTRATOR_NAME.azurewebsites.net"
echo "  Ingestion:      https://$INGESTION_NAME.azurewebsites.net"
echo "  RAG Processor:  https://$RAG_PROCESSOR_NAME.azurewebsites.net"
