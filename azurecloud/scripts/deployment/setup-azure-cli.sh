#!/bin/bash
# Setup Azure CLI and authenticate from desktop to Azure Cloud

set -e

echo "=========================================="
echo "Azure CLI Setup and Configuration"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
check_azure_cli() {
    if command -v az &> /dev/null; then
        print_status "Azure CLI is already installed"
        az --version | head -n 1
    else
        print_status "Installing Azure CLI..."
        curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    fi
}

# Check if Terraform is installed
check_terraform() {
    if command -v terraform &> /dev/null; then
        print_status "Terraform is already installed"
        terraform --version | head -n 1
    else
        print_status "Installing Terraform..."
        sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
        wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt-get update && sudo apt-get install -y terraform
    fi
}

# Check if Azure Functions Core Tools is installed
check_func_tools() {
    if command -v func &> /dev/null; then
        print_status "Azure Functions Core Tools is already installed"
        func --version
    else
        print_status "Installing Azure Functions Core Tools..."
        curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
        sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
        sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
        sudo apt-get update
        sudo apt-get install -y azure-functions-core-tools-4
    fi
}

# Check Node.js
check_nodejs() {
    if command -v node &> /dev/null; then
        print_status "Node.js is already installed"
        node --version
    else
        print_status "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
}

# Check Python
check_python() {
    if command -v python3 &> /dev/null; then
        print_status "Python is already installed"
        python3 --version
    else
        print_status "Installing Python..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    fi
}

# Login to Azure
azure_login() {
    print_status "Logging into Azure..."
    echo ""
    echo "Choose login method:"
    echo "1) Interactive browser login (recommended)"
    echo "2) Device code login"
    echo "3) Service Principal login"
    read -p "Enter choice [1-3]: " choice

    case $choice in
        1)
            az login
            ;;
        2)
            az login --use-device-code
            ;;
        3)
            read -p "Enter App ID (Client ID): " client_id
            read -sp "Enter Client Secret: " client_secret
            echo ""
            read -p "Enter Tenant ID: " tenant_id
            az login --service-principal -u "$client_id" -p "$client_secret" --tenant "$tenant_id"
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Set subscription
set_subscription() {
    print_status "Available subscriptions:"
    az account list --output table

    echo ""
    read -p "Enter subscription ID to use: " sub_id
    az account set --subscription "$sub_id"
    print_status "Subscription set to: $sub_id"
}

# Create Terraform backend storage
create_tf_backend() {
    read -p "Create Terraform backend storage? (y/n): " create_backend
    if [[ "$create_backend" == "y" ]]; then
        read -p "Enter resource group name for Terraform state [tfstate-rg]: " tf_rg
        tf_rg=${tf_rg:-tfstate-rg}

        read -p "Enter storage account name (must be globally unique): " tf_storage
        read -p "Enter location [eastus2]: " tf_location
        tf_location=${tf_location:-eastus2}

        print_status "Creating Terraform backend storage..."

        # Create resource group
        az group create --name "$tf_rg" --location "$tf_location"

        # Create storage account
        az storage account create \
            --name "$tf_storage" \
            --resource-group "$tf_rg" \
            --location "$tf_location" \
            --sku Standard_LRS \
            --encryption-services blob

        # Create container
        az storage container create \
            --name tfstate \
            --account-name "$tf_storage"

        print_status "Terraform backend created successfully!"
        echo ""
        echo "Add these values to your backend configuration:"
        echo "  resource_group_name  = \"$tf_rg\""
        echo "  storage_account_name = \"$tf_storage\""
        echo "  container_name       = \"tfstate\""
        echo "  key                  = \"genai-copilot.tfstate\""
    fi
}

# Install Azure DevOps extension
install_azdo_extension() {
    print_status "Installing Azure DevOps CLI extension..."
    az extension add --name azure-devops --allow-preview true 2>/dev/null || true
}

# Main setup flow
main() {
    echo "This script will setup your development environment for Azure GenAI Copilot"
    echo ""

    # Install prerequisites
    print_status "Checking prerequisites..."
    check_azure_cli
    check_terraform
    check_func_tools
    check_nodejs
    check_python

    echo ""
    print_status "All prerequisites installed!"
    echo ""

    # Azure login
    azure_login

    # Set subscription
    set_subscription

    # Install extensions
    install_azdo_extension

    # Create Terraform backend
    create_tf_backend

    echo ""
    print_status "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. cd infrastructure/terraform"
    echo "2. terraform init -backend-config=environments/dev/backend.tfvars"
    echo "3. terraform plan -var-file=environments/dev/terraform.tfvars"
    echo "4. terraform apply -var-file=environments/dev/terraform.tfvars"
}

main "$@"
