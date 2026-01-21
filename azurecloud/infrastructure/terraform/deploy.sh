#!/bin/bash
# GenAI Copilot Platform - Deployment Script
# Usage: ./deploy.sh [deploy|destroy|plan|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_azure_login() {
    print_status "Checking Azure login status..."
    if ! az account show &>/dev/null; then
        print_error "Not logged into Azure. Please run: az login"
        exit 1
    fi
    SUBSCRIPTION=$(az account show --query name -o tsv)
    print_status "Using subscription: $SUBSCRIPTION"
}

terraform_init() {
    print_status "Initializing Terraform..."
    terraform init -backend-config=backend.tfvars
}

case "${1:-help}" in
    deploy)
        print_status "=== DEPLOYING GENAI COPILOT PLATFORM ==="
        check_azure_login
        terraform_init

        print_status "Running Terraform plan..."
        terraform plan -out=tfplan

        print_warning "Review the plan above. Estimated monthly cost: ~\$400-420"
        read -p "Do you want to proceed with deployment? (yes/no): " confirm

        if [ "$confirm" == "yes" ]; then
            print_status "Applying Terraform configuration..."
            terraform apply tfplan
            rm -f tfplan
            print_status "=== DEPLOYMENT COMPLETE ==="
            terraform output
        else
            print_warning "Deployment cancelled."
            rm -f tfplan
        fi
        ;;

    destroy)
        print_status "=== DESTROYING GENAI COPILOT PLATFORM ==="
        check_azure_login
        terraform_init

        print_warning "This will DESTROY all resources and stop billing."
        print_warning "Your Terraform files will be preserved for future deployment."
        read -p "Are you sure you want to destroy all resources? (yes/no): " confirm

        if [ "$confirm" == "yes" ]; then
            print_status "Destroying all resources..."
            terraform destroy -auto-approve
            print_status "=== DESTRUCTION COMPLETE ==="
            print_status "All resources have been deleted. No more charges will occur."
            print_status "Run './deploy.sh deploy' to recreate the infrastructure."
        else
            print_warning "Destruction cancelled."
        fi
        ;;

    plan)
        print_status "=== TERRAFORM PLAN ==="
        check_azure_login
        terraform_init
        terraform plan
        ;;

    status)
        print_status "=== INFRASTRUCTURE STATUS ==="
        check_azure_login

        echo ""
        print_status "Deployed Resources:"
        az resource list --resource-group rg-genai-copilot-dev-wus2 \
            --query "[].{Name:name, Type:type}" -o table 2>/dev/null || \
            print_warning "Resource group not found. Infrastructure may not be deployed."

        echo ""
        print_status "Terraform State:"
        terraform show -no-color 2>/dev/null | head -20 || \
            print_warning "No Terraform state found."
        ;;

    output)
        print_status "=== TERRAFORM OUTPUTS ==="
        terraform output
        ;;

    help|*)
        echo "GenAI Copilot Platform - Infrastructure Management"
        echo ""
        echo "Usage: ./deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy all infrastructure (creates resources, starts billing)"
        echo "  destroy  - Destroy all infrastructure (stops billing)"
        echo "  plan     - Show what would be created/destroyed"
        echo "  status   - Show current infrastructure status"
        echo "  output   - Show Terraform outputs (endpoints, names, etc.)"
        echo "  help     - Show this help message"
        echo ""
        echo "Estimated Monthly Cost: ~\$400-420 (when deployed)"
        echo ""
        echo "Quick Start:"
        echo "  1. Deploy:  ./deploy.sh deploy"
        echo "  2. Destroy: ./deploy.sh destroy"
        ;;
esac
