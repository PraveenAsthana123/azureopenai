#!/usr/bin/env bash
###############################################################################
# Bootstrap Script for Enterprise Copilot Setup VM
#
# Installs:
#   - Azure CLI
#   - Terraform (latest)
#   - jq, git, python3, pip
#   - kubectl, helm (optional)
#   - Docker (optional)
#
# Usage:
#   curl -sSL <url>/bootstrap-vm.sh | bash
#   # or
#   chmod +x bootstrap-vm.sh && ./bootstrap-vm.sh
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Versions
TERRAFORM_VERSION="${TERRAFORM_VERSION:-1.9.8}"

###############################################################################
# Helper Functions
###############################################################################

print_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_installed() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 $(command -v $1)"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

###############################################################################
# Main Installation
###############################################################################

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Enterprise Copilot - VM Bootstrap Script                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Update package lists
print_step "Updating system packages"
sudo apt-get update -qq

# Install basic tools
print_step "Installing basic tools (jq, curl, unzip, git, ca-certificates)"
sudo apt-get install -y -qq \
    jq \
    curl \
    wget \
    unzip \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https

print_success "Basic tools installed"

###############################################################################
# Azure CLI
###############################################################################

print_step "Installing Azure CLI"

if command -v az &> /dev/null; then
    print_warning "Azure CLI already installed: $(az --version | head -1)"
else
    # Install Azure CLI
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

    print_success "Azure CLI installed: $(az --version | head -1)"
fi

###############################################################################
# Terraform
###############################################################################

print_step "Installing Terraform ${TERRAFORM_VERSION}"

if command -v terraform &> /dev/null; then
    CURRENT_TF=$(terraform --version | head -1)
    print_warning "Terraform already installed: $CURRENT_TF"
    read -rp "Reinstall/upgrade? (y/n): " REINSTALL_TF
    if [[ "$REINSTALL_TF" != "y" ]]; then
        SKIP_TF=true
    fi
fi

if [[ "${SKIP_TF:-false}" != "true" ]]; then
    # Download and install Terraform
    cd /tmp
    curl -LO "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
    unzip -o "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
    sudo mv terraform /usr/local/bin/
    rm "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
    cd -

    print_success "Terraform installed: $(terraform --version | head -1)"
fi

###############################################################################
# Python 3 & pip
###############################################################################

print_step "Installing Python 3 and pip"

sudo apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv

print_success "Python installed: $(python3 --version)"

# Install useful Python packages
pip3 install --quiet --user \
    azure-identity \
    azure-mgmt-resource \
    pyyaml \
    requests

print_success "Python packages installed"

###############################################################################
# Optional: kubectl
###############################################################################

print_step "Installing kubectl (optional)"

read -rp "Install kubectl? (y/n): " INSTALL_KUBECTL

if [[ "$INSTALL_KUBECTL" == "y" ]]; then
    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl

    print_success "kubectl installed: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
else
    echo "Skipping kubectl installation"
fi

###############################################################################
# Optional: Helm
###############################################################################

print_step "Installing Helm (optional)"

read -rp "Install Helm? (y/n): " INSTALL_HELM

if [[ "$INSTALL_HELM" == "y" ]]; then
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

    print_success "Helm installed: $(helm version --short)"
else
    echo "Skipping Helm installation"
fi

###############################################################################
# Optional: Docker
###############################################################################

print_step "Installing Docker (optional)"

read -rp "Install Docker? (y/n): " INSTALL_DOCKER

if [[ "$INSTALL_DOCKER" == "y" ]]; then
    # Add Docker's official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # Add the repository to Apt sources
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    sudo usermod -aG docker "$USER"

    print_success "Docker installed: $(docker --version)"
    print_warning "Log out and back in for docker group permissions to take effect"
else
    echo "Skipping Docker installation"
fi

###############################################################################
# Azure CLI Extensions
###############################################################################

print_step "Installing Azure CLI extensions"

# Install useful extensions
az extension add --name account --only-show-errors 2>/dev/null || true
az extension add --name ai-examples --only-show-errors 2>/dev/null || true
az extension add --name application-insights --only-show-errors 2>/dev/null || true
az extension add --name containerapp --only-show-errors 2>/dev/null || true
az extension add --name aks-preview --only-show-errors 2>/dev/null || true

print_success "Azure CLI extensions installed"

###############################################################################
# Shell Configuration
###############################################################################

print_step "Configuring shell environment"

# Add useful aliases and configurations
cat >> ~/.bashrc << 'EOF'

# Enterprise Copilot aliases
alias tf='terraform'
alias tfi='terraform init'
alias tfp='terraform plan'
alias tfa='terraform apply'
alias tfd='terraform destroy'
alias tfv='terraform validate'
alias tff='terraform fmt -recursive'

# Azure aliases
alias azl='az login'
alias azs='az account show'
alias azsl='az account list -o table'
alias azrg='az group list -o table'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

# Color prompt with git branch
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}
export PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[33m\]$(parse_git_branch)\[\033[00m\]\$ '

# Azure CLI completion
source /etc/bash_completion.d/azure-cli 2>/dev/null || true

# Terraform completion
complete -C /usr/local/bin/terraform terraform tf
EOF

print_success "Shell configuration updated"

###############################################################################
# Download Enterprise Copilot Scripts
###############################################################################

print_step "Setting up Enterprise Copilot scripts directory"

mkdir -p ~/enterprise-copilot
cd ~/enterprise-copilot

# Create a placeholder for the input collector script
cat > collect-inputs.sh << 'SCRIPT'
#!/usr/bin/env bash
echo "Download the full collect-terraform-inputs.sh script from your repository"
echo "or copy it from infrastructure/scripts/collect-terraform-inputs.sh"
SCRIPT
chmod +x collect-inputs.sh

print_success "Scripts directory created at ~/enterprise-copilot"

###############################################################################
# Verification
###############################################################################

print_step "Verifying installations"

echo ""
echo "Installed tools:"
check_installed az || true
check_installed terraform || true
check_installed python3 || true
check_installed pip3 || true
check_installed jq || true
check_installed git || true
check_installed kubectl || true
check_installed helm || true
check_installed docker || true

###############################################################################
# Summary
###############################################################################

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Bootstrap Complete!                                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

cat << EOF

${CYAN}NEXT STEPS${NC}

1. Reload your shell configuration:
   ${GREEN}source ~/.bashrc${NC}

2. Login to Azure (if not using managed identity):
   ${GREEN}az login${NC}

   Or with device code (for remote/headless):
   ${GREEN}az login --use-device-code${NC}

3. Set your subscription:
   ${GREEN}az account list -o table${NC}
   ${GREEN}az account set --subscription "YOUR_SUBSCRIPTION_ID"${NC}

4. Navigate to scripts directory:
   ${GREEN}cd ~/enterprise-copilot${NC}

5. Copy and run the input collector:
   ${GREEN}# Copy collect-terraform-inputs.sh to this VM${NC}
   ${GREEN}chmod +x collect-terraform-inputs.sh${NC}
   ${GREEN}./collect-terraform-inputs.sh${NC}

${CYAN}USEFUL COMMANDS${NC}

  Terraform shortcuts:
    ${GREEN}tf${NC}   = terraform
    ${GREEN}tfi${NC}  = terraform init
    ${GREEN}tfp${NC}  = terraform plan
    ${GREEN}tfa${NC}  = terraform apply

  Azure shortcuts:
    ${GREEN}azl${NC}  = az login
    ${GREEN}azs${NC}  = az account show
    ${GREEN}azrg${NC} = az group list -o table

EOF
