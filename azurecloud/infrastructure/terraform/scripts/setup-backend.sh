#!/bin/bash
# =============================================================================
# Terraform Backend Setup Script
# =============================================================================
# Creates Azure Storage Account for Terraform state management
# Run this ONCE before first terraform init

set -e

# Configuration
ENVIRONMENT=${1:-prod}
LOCATION=${2:-eastus2}
RESOURCE_GROUP="terraform-state-rg"
STORAGE_ACCOUNT="tfstate${ENVIRONMENT}$(openssl rand -hex 4)"
CONTAINER_NAME="tfstate"

echo "=============================================="
echo "Terraform Backend Setup"
echo "=============================================="
echo "Environment: $ENVIRONMENT"
echo "Location: $LOCATION"
echo "Resource Group: $RESOURCE_GROUP"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "=============================================="

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "ERROR: Azure CLI not found"
    exit 1
fi

# Check login
az account show &> /dev/null || {
    echo "Please login to Azure..."
    az login
}

echo ""
echo "Logged in as: $(az account show --query user.name -o tsv)"
echo "Subscription: $(az account show --query name -o tsv)"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Create resource group
echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags Purpose="Terraform State" Environment="$ENVIRONMENT"

# Create storage account
echo "Creating storage account..."
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku "Standard_LRS" \
    --kind "StorageV2" \
    --https-only true \
    --min-tls-version "TLS1_2" \
    --allow-blob-public-access false \
    --tags Purpose="Terraform State" Environment="$ENVIRONMENT"

# Enable versioning for state recovery
echo "Enabling blob versioning..."
az storage account blob-service-properties update \
    --account-name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --enable-versioning true

# Create container
echo "Creating container..."
az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode login

# Enable soft delete
echo "Enabling soft delete..."
az storage account blob-service-properties update \
    --account-name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --enable-delete-retention true \
    --delete-retention-days 30

# Get storage account key
ACCOUNT_KEY=$(az storage account keys list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "$STORAGE_ACCOUNT" \
    --query '[0].value' -o tsv)

echo ""
echo "=============================================="
echo "Backend Setup Complete!"
echo "=============================================="
echo ""
echo "Update your Terraform backend configuration:"
echo ""
echo "terraform {"
echo "  backend \"azurerm\" {"
echo "    resource_group_name  = \"$RESOURCE_GROUP\""
echo "    storage_account_name = \"$STORAGE_ACCOUNT\""
echo "    container_name       = \"$CONTAINER_NAME\""
echo "    key                  = \"${ENVIRONMENT}.terraform.tfstate\""
echo "  }"
echo "}"
echo ""
echo "Or use environment variables:"
echo ""
echo "export ARM_ACCESS_KEY=\"$ACCOUNT_KEY\""
echo ""
echo "Then run: terraform init"
echo ""
