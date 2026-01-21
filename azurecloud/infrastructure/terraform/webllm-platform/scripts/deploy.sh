#!/bin/bash
#===============================================================================
# WebLLM Platform - Full Deployment Script
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="/mnt/deepa/AzureopenAI/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create log directory
mkdir -p "$LOG_DIR"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"
}

#-------------------------------------------------------------------------------
# Prerequisites Check
#-------------------------------------------------------------------------------
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        error "Azure CLI is not installed. Please install it first."
    fi
    az_version=$(az version --query '"azure-cli"' -o tsv)
    info "Azure CLI version: $az_version"

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Please install it first."
    fi
    tf_version=$(terraform version -json | jq -r '.terraform_version')
    info "Terraform version: $tf_version"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        warn "kubectl is not installed. K8s deployment will be skipped."
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        warn "Docker is not installed. Container builds will be skipped."
    fi

    # Check Azure login
    if ! az account show &> /dev/null; then
        error "Not logged in to Azure. Please run 'az login' first."
    fi
    account=$(az account show --query name -o tsv)
    info "Azure subscription: $account"

    log "Prerequisites check completed"
}

#-------------------------------------------------------------------------------
# Terraform Deployment
#-------------------------------------------------------------------------------
deploy_infrastructure() {
    log "Deploying infrastructure with Terraform..."

    cd "$PROJECT_ROOT"

    # Initialize Terraform
    log "Initializing Terraform..."
    terraform init -input=false 2>&1 | tee -a "$LOG_DIR/terraform-$TIMESTAMP.log"

    # Validate configuration
    log "Validating Terraform configuration..."
    terraform validate 2>&1 | tee -a "$LOG_DIR/terraform-$TIMESTAMP.log"

    # Plan deployment
    log "Creating Terraform plan..."
    terraform plan -out=tfplan -input=false 2>&1 | tee -a "$LOG_DIR/terraform-$TIMESTAMP.log"

    # Apply (with confirmation)
    if [ "$AUTO_APPROVE" == "true" ]; then
        log "Applying Terraform plan (auto-approved)..."
        terraform apply -input=false tfplan 2>&1 | tee -a "$LOG_DIR/terraform-$TIMESTAMP.log"
    else
        log "Applying Terraform plan..."
        terraform apply tfplan 2>&1 | tee -a "$LOG_DIR/terraform-$TIMESTAMP.log"
    fi

    # Save outputs
    log "Saving Terraform outputs..."
    terraform output -json > "$LOG_DIR/terraform-outputs-$TIMESTAMP.json"

    log "Infrastructure deployment completed"
}

#-------------------------------------------------------------------------------
# Get Terraform Outputs
#-------------------------------------------------------------------------------
get_terraform_outputs() {
    cd "$PROJECT_ROOT"

    ACR_NAME=$(terraform output -raw acr_login_server 2>/dev/null || echo "")
    AKS_NAME=$(terraform output -raw aks_cluster_name 2>/dev/null || echo "")
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
}

#-------------------------------------------------------------------------------
# Build and Push Docker Images
#-------------------------------------------------------------------------------
build_and_push_images() {
    log "Building and pushing Docker images..."

    get_terraform_outputs

    if [ -z "$ACR_NAME" ]; then
        warn "ACR name not found. Skipping image build."
        return
    fi

    # Login to ACR
    log "Logging in to ACR: $ACR_NAME"
    az acr login --name "${ACR_NAME%%.*}"

    # Build and push backend image
    log "Building backend image..."
    docker build -t "$ACR_NAME/ucp-backend:latest" "$PROJECT_ROOT/backend"
    docker push "$ACR_NAME/ucp-backend:latest"

    # Build and push frontend image
    log "Building frontend image..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    npm run build
    docker build -t "$ACR_NAME/ucp-frontend:latest" .
    docker push "$ACR_NAME/ucp-frontend:latest"

    log "Docker images built and pushed"
}

#-------------------------------------------------------------------------------
# Deploy to Kubernetes
#-------------------------------------------------------------------------------
deploy_kubernetes() {
    log "Deploying to Kubernetes..."

    get_terraform_outputs

    if [ -z "$AKS_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        warn "AKS cluster info not found. Skipping K8s deployment."
        return
    fi

    # Get AKS credentials
    log "Getting AKS credentials..."
    az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_NAME" --overwrite-existing

    # Deploy MLC LLM
    log "Deploying MLC LLM manifests..."
    kubectl apply -f "$PROJECT_ROOT/k8s/mlc-llm/"

    # Deploy WebLLM Router
    log "Deploying WebLLM Router..."
    kubectl apply -f "$PROJECT_ROOT/k8s/webllm-router/"

    # Wait for deployments
    log "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/webllm-router -n webllm-router || true

    log "Kubernetes deployment completed"
}

#-------------------------------------------------------------------------------
# Verify Deployment
#-------------------------------------------------------------------------------
verify_deployment() {
    log "Verifying deployment..."

    get_terraform_outputs

    # Check Terraform resources
    log "Checking Azure resources..."
    az resource list --resource-group "$RESOURCE_GROUP" --output table 2>&1 | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"

    # Check Kubernetes pods
    if command -v kubectl &> /dev/null; then
        log "Checking Kubernetes pods..."
        kubectl get pods -A 2>&1 | tee -a "$LOG_DIR/deploy-$TIMESTAMP.log"
    fi

    log "Deployment verification completed"
}

#-------------------------------------------------------------------------------
# Print Summary
#-------------------------------------------------------------------------------
print_summary() {
    log "========================================"
    log "DEPLOYMENT SUMMARY"
    log "========================================"

    get_terraform_outputs

    echo ""
    info "Resource Group: $RESOURCE_GROUP"
    info "ACR: $ACR_NAME"
    info "AKS Cluster: $AKS_NAME"
    echo ""
    info "Logs saved to: $LOG_DIR"
    info "Terraform outputs: $LOG_DIR/terraform-outputs-$TIMESTAMP.json"
    echo ""

    log "Deployment completed successfully!"
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------
main() {
    echo "========================================"
    echo "WebLLM Platform Deployment"
    echo "========================================"
    echo ""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-approve)
                AUTO_APPROVE="true"
                shift
                ;;
            --skip-infra)
                SKIP_INFRA="true"
                shift
                ;;
            --skip-build)
                SKIP_BUILD="true"
                shift
                ;;
            --skip-k8s)
                SKIP_K8S="true"
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    check_prerequisites

    if [ "$SKIP_INFRA" != "true" ]; then
        deploy_infrastructure
    fi

    if [ "$SKIP_BUILD" != "true" ]; then
        build_and_push_images
    fi

    if [ "$SKIP_K8S" != "true" ]; then
        deploy_kubernetes
    fi

    verify_deployment
    print_summary
}

main "$@"
