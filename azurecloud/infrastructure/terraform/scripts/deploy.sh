#!/bin/bash
# =============================================================================
# Terraform Deployment Script
# =============================================================================
# Deploys RAG Platform infrastructure using Terraform
#
# Usage:
#   ./deploy.sh [environment] [action]
#   ./deploy.sh prod plan
#   ./deploy.sh prod apply
#   ./deploy.sh dev destroy

set -e

# Configuration
ENVIRONMENT=${1:-prod}
ACTION=${2:-plan}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../environments/$ENVIRONMENT"

echo "=============================================="
echo "RAG Platform Terraform Deployment"
echo "=============================================="
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo "Directory: $TERRAFORM_DIR"
echo "=============================================="

# Validate environment
if [[ ! -d "$TERRAFORM_DIR" ]]; then
    echo "ERROR: Environment directory not found: $TERRAFORM_DIR"
    echo "Available environments:"
    ls -1 "$SCRIPT_DIR/../environments/"
    exit 1
fi

# Check prerequisites
command -v terraform &> /dev/null || {
    echo "ERROR: Terraform not found. Install from https://terraform.io"
    exit 1
}

command -v az &> /dev/null || {
    echo "ERROR: Azure CLI not found"
    exit 1
}

# Check Azure login
az account show &> /dev/null || {
    echo "Please login to Azure..."
    az login
}

echo ""
echo "Azure Account: $(az account show --query name -o tsv)"
echo "Subscription ID: $(az account show --query id -o tsv)"
echo ""

# Change to environment directory
cd "$TERRAFORM_DIR"

# Check for tfvars
if [[ ! -f "terraform.tfvars" ]]; then
    echo "WARNING: terraform.tfvars not found"
    echo "Copy terraform.tfvars.example to terraform.tfvars and configure"

    if [[ -f "terraform.tfvars.example" ]]; then
        read -p "Copy example file now? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp terraform.tfvars.example terraform.tfvars
            echo "Created terraform.tfvars - please edit and re-run"
            exit 0
        fi
    fi
fi

# Terraform commands
case $ACTION in
    init)
        echo "Initializing Terraform..."
        terraform init -upgrade
        ;;

    validate)
        echo "Validating configuration..."
        terraform init -upgrade
        terraform validate
        terraform fmt -check -recursive
        ;;

    plan)
        echo "Planning deployment..."
        terraform init -upgrade
        terraform plan -out=tfplan
        echo ""
        echo "Review the plan above."
        echo "To apply: ./deploy.sh $ENVIRONMENT apply"
        ;;

    apply)
        echo "Applying deployment..."

        if [[ -f "tfplan" ]]; then
            terraform apply tfplan
            rm -f tfplan
        else
            echo "No plan file found. Running plan first..."
            terraform plan -out=tfplan

            read -p "Apply this plan? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                terraform apply tfplan
                rm -f tfplan
            else
                echo "Cancelled."
                exit 0
            fi
        fi
        ;;

    destroy)
        echo "WARNING: This will destroy all resources!"
        echo ""
        terraform plan -destroy
        echo ""
        read -p "Are you sure you want to destroy? Type 'yes' to confirm: " CONFIRM
        if [[ "$CONFIRM" == "yes" ]]; then
            terraform destroy -auto-approve
        else
            echo "Cancelled."
            exit 0
        fi
        ;;

    output)
        echo "Terraform outputs:"
        terraform output
        ;;

    state)
        echo "Terraform state:"
        terraform state list
        ;;

    refresh)
        echo "Refreshing state..."
        terraform refresh
        ;;

    *)
        echo "Unknown action: $ACTION"
        echo ""
        echo "Available actions:"
        echo "  init     - Initialize Terraform"
        echo "  validate - Validate configuration"
        echo "  plan     - Plan deployment"
        echo "  apply    - Apply deployment"
        echo "  destroy  - Destroy all resources"
        echo "  output   - Show outputs"
        echo "  state    - List state resources"
        echo "  refresh  - Refresh state"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Done!"
echo "=============================================="
