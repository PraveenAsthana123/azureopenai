#!/usr/bin/env bash
###############################################################################
# Create Azure Primitive VM for Enterprise Copilot Setup
#
# This script creates an Ubuntu VM with:
#   - Managed Identity (for Azure access)
#   - Public IP (for SSH access)
#   - NSG with SSH allowed
#   - Optional: VNet integration
#
# Usage:
#   ./create-primitive-vm.sh [simple|enterprise]
#
#   simple     - Quick VM with minimal networking
#   enterprise - Full VNet, NSG, managed identity setup
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

###############################################################################
# Configuration - MODIFY THESE
###############################################################################

# Resource naming
RG="${RG:-rg-ecp-primitive-dev}"
LOCATION="${LOCATION:-eastus2}"
VM_NAME="${VM_NAME:-ecp-setup-vm}"
ADMIN_USER="${ADMIN_USER:-azureuser}"
VM_SIZE="${VM_SIZE:-Standard_B2s}"

# Networking (enterprise mode)
VNET_NAME="${VNET_NAME:-vnet-ecp-setup}"
VNET_CIDR="${VNET_CIDR:-10.50.0.0/16}"
SUBNET_NAME="${SUBNET_NAME:-subnet-setup}"
SUBNET_CIDR="${SUBNET_CIDR:-10.50.1.0/24}"
NSG_NAME="${NSG_NAME:-nsg-ecp-setup}"
PIP_NAME="${PIP_NAME:-pip-ecp-setup}"
NIC_NAME="${NIC_NAME:-nic-ecp-setup}"

# Tags
TAGS="project=enterprise-copilot owner=setup-script purpose=terraform-deployment"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${GREEN}[$1/$TOTAL_STEPS]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

###############################################################################
# Pre-flight Checks
###############################################################################

MODE="${1:-simple}"

if [[ "$MODE" != "simple" && "$MODE" != "enterprise" ]]; then
    echo "Usage: $0 [simple|enterprise]"
    echo ""
    echo "  simple     - Quick VM with minimal networking (default)"
    echo "  enterprise - Full VNet, NSG, managed identity setup"
    exit 1
fi

print_header "Enterprise Copilot - Primitive VM Setup ($MODE mode)"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Install: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
fi

# Check login
echo "Checking Azure login..."
if ! az account show &>/dev/null; then
    print_warning "Not logged in. Starting Azure login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "Using subscription: ${CYAN}$SUBSCRIPTION${NC}"
echo ""

###############################################################################
# Simple Mode - Quick VM
###############################################################################

if [[ "$MODE" == "simple" ]]; then
    TOTAL_STEPS=3

    print_step 1 "Creating resource group: $RG"
    az group create \
        --name "$RG" \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    print_step 2 "Creating Ubuntu VM with managed identity..."
    az vm create \
        --resource-group "$RG" \
        --name "$VM_NAME" \
        --image Ubuntu2204 \
        --size "$VM_SIZE" \
        --admin-username "$ADMIN_USER" \
        --generate-ssh-keys \
        --public-ip-sku Standard \
        --assign-identity \
        --tags $TAGS \
        --output table

    print_step 3 "Opening SSH port..."
    az vm open-port \
        --resource-group "$RG" \
        --name "$VM_NAME" \
        --port 22 \
        --output none

    PUBLIC_IP=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)

###############################################################################
# Enterprise Mode - Full Network Setup
###############################################################################

else
    TOTAL_STEPS=7

    print_step 1 "Creating resource group: $RG"
    az group create \
        --name "$RG" \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    print_step 2 "Creating VNet and Subnet..."
    az network vnet create \
        --resource-group "$RG" \
        --name "$VNET_NAME" \
        --address-prefix "$VNET_CIDR" \
        --subnet-name "$SUBNET_NAME" \
        --subnet-prefix "$SUBNET_CIDR" \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    print_step 3 "Creating Network Security Group with SSH rule..."
    az network nsg create \
        --resource-group "$RG" \
        --name "$NSG_NAME" \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    az network nsg rule create \
        --resource-group "$RG" \
        --nsg-name "$NSG_NAME" \
        --name "Allow-SSH" \
        --priority 1000 \
        --access Allow \
        --direction Inbound \
        --protocol Tcp \
        --source-address-prefixes "*" \
        --source-port-ranges "*" \
        --destination-address-prefixes "*" \
        --destination-port-ranges 22 \
        --output none

    print_step 4 "Creating Public IP..."
    az network public-ip create \
        --resource-group "$RG" \
        --name "$PIP_NAME" \
        --sku Standard \
        --allocation-method Static \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    print_step 5 "Creating Network Interface..."
    az network nic create \
        --resource-group "$RG" \
        --name "$NIC_NAME" \
        --vnet-name "$VNET_NAME" \
        --subnet "$SUBNET_NAME" \
        --network-security-group "$NSG_NAME" \
        --public-ip-address "$PIP_NAME" \
        --location "$LOCATION" \
        --tags $TAGS \
        --output none

    print_step 6 "Creating Ubuntu VM with Managed Identity..."
    az vm create \
        --resource-group "$RG" \
        --name "$VM_NAME" \
        --nics "$NIC_NAME" \
        --image Ubuntu2204 \
        --size "$VM_SIZE" \
        --admin-username "$ADMIN_USER" \
        --generate-ssh-keys \
        --assign-identity \
        --location "$LOCATION" \
        --tags $TAGS \
        --output table

    print_step 7 "Assigning Contributor role to VM identity..."
    IDENTITY_ID=$(az vm show -g "$RG" -n "$VM_NAME" --query identity.principalId -o tsv)
    SUB_ID=$(az account show --query id -o tsv)

    az role assignment create \
        --assignee "$IDENTITY_ID" \
        --role "Contributor" \
        --scope "/subscriptions/$SUB_ID" \
        --output none || print_warning "Could not assign Contributor role (may need Owner permissions)"

    PUBLIC_IP=$(az network public-ip show -g "$RG" -n "$PIP_NAME" --query ipAddress -o tsv)
fi

###############################################################################
# Output Summary
###############################################################################

print_header "VM Created Successfully"

cat << EOF

${GREEN}CONNECTION DETAILS${NC}
  Resource Group : $RG
  VM Name        : $VM_NAME
  Public IP      : $PUBLIC_IP
  Username       : $ADMIN_USER

${GREEN}SSH COMMAND${NC}
  ${CYAN}ssh $ADMIN_USER@$PUBLIC_IP${NC}

${GREEN}NEXT STEPS${NC}
  1. SSH into the VM:
     ${CYAN}ssh $ADMIN_USER@$PUBLIC_IP${NC}

  2. Run the bootstrap script to install tools:
     ${CYAN}curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/infrastructure/scripts/bootstrap-vm.sh | bash${NC}

     Or copy and run manually:
     ${CYAN}scp bootstrap-vm.sh $ADMIN_USER@$PUBLIC_IP:~/${NC}
     ${CYAN}ssh $ADMIN_USER@$PUBLIC_IP 'chmod +x bootstrap-vm.sh && ./bootstrap-vm.sh'${NC}

  3. Run the input collector script:
     ${CYAN}./collect-terraform-inputs.sh${NC}

${GREEN}CLEANUP${NC}
  To delete all resources:
  ${CYAN}az group delete --name $RG --yes --no-wait${NC}

EOF

# Save connection info to file
cat > "vm-connection-info.txt" << EOF
# Enterprise Copilot Setup VM Connection Info
# Generated: $(date)

RESOURCE_GROUP=$RG
VM_NAME=$VM_NAME
PUBLIC_IP=$PUBLIC_IP
USERNAME=$ADMIN_USER
SSH_COMMAND="ssh $ADMIN_USER@$PUBLIC_IP"
EOF

print_success "Connection info saved to vm-connection-info.txt"
