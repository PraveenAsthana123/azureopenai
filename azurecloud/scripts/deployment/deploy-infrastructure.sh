#!/bin/bash
# Deploy Azure infrastructure using Terraform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"

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
ACTION="plan"
AUTO_APPROVE=""
VM_PASSWORD=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        --auto-approve)
            AUTO_APPROVE="-auto-approve"
            shift
            ;;
        -p|--password)
            VM_PASSWORD="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -e, --environment    Environment (dev, staging, prod). Default: dev"
            echo "  -a, --action         Action (init, plan, apply, destroy). Default: plan"
            echo "  --auto-approve       Skip approval prompt for apply/destroy"
            echo "  -p, --password       VM admin password"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(init|plan|apply|destroy|output)$ ]]; then
    print_error "Invalid action: $ACTION. Must be init, plan, apply, destroy, or output."
    exit 1
fi

print_header "Azure Infrastructure Deployment"
print_status "Environment: $ENVIRONMENT"
print_status "Action: $ACTION"
print_status "Terraform Dir: $TERRAFORM_DIR"

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Check if tfvars file exists
TFVARS_FILE="environments/$ENVIRONMENT/terraform.tfvars"
if [[ ! -f "$TFVARS_FILE" ]]; then
    print_error "tfvars file not found: $TFVARS_FILE"
    exit 1
fi

# Get VM password if not provided and action requires it
if [[ -z "$VM_PASSWORD" && ("$ACTION" == "apply" || "$ACTION" == "plan") ]]; then
    read -sp "Enter VM admin password: " VM_PASSWORD
    echo ""
fi

# Terraform init
terraform_init() {
    print_status "Initializing Terraform..."

    # Check for backend config
    BACKEND_CONFIG="environments/$ENVIRONMENT/backend.tfvars"
    if [[ -f "$BACKEND_CONFIG" ]]; then
        terraform init -backend-config="$BACKEND_CONFIG" -reconfigure
    else
        terraform init -reconfigure
    fi
}

# Terraform plan
terraform_plan() {
    print_status "Creating Terraform plan..."
    terraform plan \
        -var-file="$TFVARS_FILE" \
        -var="vm_admin_password=$VM_PASSWORD" \
        -out="tfplan-$ENVIRONMENT"
}

# Terraform apply
terraform_apply() {
    print_status "Applying Terraform configuration..."

    if [[ -f "tfplan-$ENVIRONMENT" ]]; then
        terraform apply $AUTO_APPROVE "tfplan-$ENVIRONMENT"
    else
        terraform apply \
            -var-file="$TFVARS_FILE" \
            -var="vm_admin_password=$VM_PASSWORD" \
            $AUTO_APPROVE
    fi
}

# Terraform destroy
terraform_destroy() {
    print_warning "This will DESTROY all infrastructure in $ENVIRONMENT!"

    if [[ -z "$AUTO_APPROVE" ]]; then
        read -p "Are you sure? Type 'destroy' to confirm: " confirm
        if [[ "$confirm" != "destroy" ]]; then
            print_status "Destroy cancelled."
            exit 0
        fi
    fi

    print_status "Destroying infrastructure..."
    terraform destroy \
        -var-file="$TFVARS_FILE" \
        -var="vm_admin_password=${VM_PASSWORD:-dummy}" \
        $AUTO_APPROVE
}

# Terraform output
terraform_output() {
    print_status "Terraform outputs:"
    terraform output
}

# Execute action
case $ACTION in
    init)
        terraform_init
        ;;
    plan)
        terraform_init
        terraform_plan
        ;;
    apply)
        terraform_init
        terraform_plan
        terraform_apply
        ;;
    destroy)
        terraform_init
        terraform_destroy
        ;;
    output)
        terraform_output
        ;;
esac

print_status "Done!"

# Show next steps
if [[ "$ACTION" == "apply" ]]; then
    echo ""
    print_header "Next Steps"
    echo "1. Deploy Function Apps:"
    echo "   ./scripts/deployment/deploy-functions.sh -e $ENVIRONMENT"
    echo ""
    echo "2. Deploy Frontend to VMs:"
    echo "   ./scripts/deployment/deploy-to-vm.sh -e $ENVIRONMENT"
    echo ""
    echo "3. Configure AI Search Index:"
    echo "   ./scripts/deployment/setup-search-index.sh -e $ENVIRONMENT"
fi
