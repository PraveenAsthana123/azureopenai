#!/bin/bash
# Deploy application to Azure VMs via Bastion

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
RESOURCE_GROUP=""
VM_NAME=""
DEPLOY_FRONTEND=true
DEPLOY_BACKEND=true

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
        -v|--vm-name)
            VM_NAME="$2"
            shift 2
            ;;
        --frontend-only)
            DEPLOY_BACKEND=false
            shift
            ;;
        --backend-only)
            DEPLOY_FRONTEND=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -e, --environment    Environment (dev, staging, prod). Default: dev"
            echo "  -g, --resource-group Azure resource group name"
            echo "  -v, --vm-name        Specific VM name to deploy to"
            echo "  --frontend-only      Only deploy frontend"
            echo "  --backend-only       Only deploy backend services"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_header "VM Deployment"
print_status "Environment: $ENVIRONMENT"

# Get Terraform outputs if resource group not specified
if [[ -z "$RESOURCE_GROUP" ]]; then
    cd "$PROJECT_ROOT/infrastructure/terraform"
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
fi

print_status "Resource Group: $RESOURCE_GROUP"

# Get VM list
if [[ -z "$VM_NAME" ]]; then
    print_status "Getting VM list..."
    VM_LIST=$(az vm list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv)
else
    VM_LIST="$VM_NAME"
fi

# Create deployment package
create_deployment_package() {
    print_status "Creating deployment package..."

    DEPLOY_DIR="$PROJECT_ROOT/.deploy"
    rm -rf "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"

    if [[ "$DEPLOY_FRONTEND" == true ]]; then
        # Build frontend
        print_status "Building frontend..."
        cd "$PROJECT_ROOT/frontend"
        if [[ -f "package.json" ]]; then
            npm install
            npm run build
            cp -r dist "$DEPLOY_DIR/frontend"
        fi
    fi

    if [[ "$DEPLOY_BACKEND" == true ]]; then
        # Package backend shared components
        print_status "Packaging backend..."
        cp -r "$PROJECT_ROOT/backend/shared" "$DEPLOY_DIR/backend"
    fi

    # Create deployment script for VM
    cat > "$DEPLOY_DIR/install.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

APP_DIR="/opt/genai-copilot"

echo "Installing application..."

# Stop nginx if running
sudo systemctl stop nginx 2>/dev/null || true

# Copy frontend
if [[ -d "/tmp/deploy/frontend" ]]; then
    sudo rm -rf "$APP_DIR/frontend"
    sudo cp -r /tmp/deploy/frontend "$APP_DIR/"
    sudo chown -R www-data:www-data "$APP_DIR/frontend"
fi

# Copy backend
if [[ -d "/tmp/deploy/backend" ]]; then
    sudo rm -rf "$APP_DIR/backend"
    sudo cp -r /tmp/deploy/backend "$APP_DIR/"

    # Setup Python environment
    cd "$APP_DIR/backend"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt 2>/dev/null || true
    deactivate
fi

# Configure nginx
sudo tee /etc/nginx/sites-available/genai-copilot << 'NGINX_CONFIG'
server {
    listen 80;
    server_name _;

    root /opt/genai-copilot/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:7071;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX_CONFIG

sudo ln -sf /etc/nginx/sites-available/genai-copilot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

echo "Installation complete!"
INSTALL_SCRIPT

    chmod +x "$DEPLOY_DIR/install.sh"

    # Create tarball
    cd "$DEPLOY_DIR"
    tar -czf deploy.tar.gz *

    print_status "Deployment package created: $DEPLOY_DIR/deploy.tar.gz"
}

# Deploy to a single VM via Bastion
deploy_to_vm() {
    local vm_name=$1

    print_status "Deploying to VM: $vm_name"

    # Get VM resource ID
    VM_ID=$(az vm show --resource-group "$RESOURCE_GROUP" --name "$vm_name" --query "id" -o tsv)

    # Get Bastion name
    BASTION_NAME=$(az network bastion list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)

    if [[ -z "$BASTION_NAME" ]]; then
        print_warning "No Bastion host found. Using direct SSH (requires public IP or VPN)."

        # Get private IP
        PRIVATE_IP=$(az vm show --resource-group "$RESOURCE_GROUP" --name "$vm_name" -d --query "privateIps" -o tsv)

        print_status "VM Private IP: $PRIVATE_IP"
        print_warning "Please ensure you have VPN or network connectivity to the VM."

        # Instructions for manual deployment
        echo ""
        echo "Manual deployment steps:"
        echo "1. Copy deploy.tar.gz to VM: scp $PROJECT_ROOT/.deploy/deploy.tar.gz azureadmin@$PRIVATE_IP:/tmp/"
        echo "2. SSH to VM: ssh azureadmin@$PRIVATE_IP"
        echo "3. Extract and run: cd /tmp && tar -xzf deploy.tar.gz && sudo ./install.sh"
    else
        print_status "Using Bastion: $BASTION_NAME"

        # Upload via Bastion tunnel
        print_status "Creating Bastion tunnel..."

        # Start tunnel in background
        az network bastion tunnel \
            --name "$BASTION_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --target-resource-id "$VM_ID" \
            --resource-port 22 \
            --port 50022 &

        TUNNEL_PID=$!
        sleep 5

        # Copy files through tunnel
        print_status "Copying deployment package..."
        scp -P 50022 -o StrictHostKeyChecking=no "$PROJECT_ROOT/.deploy/deploy.tar.gz" azureadmin@localhost:/tmp/

        # Run installation
        print_status "Running installation script..."
        ssh -p 50022 -o StrictHostKeyChecking=no azureadmin@localhost "cd /tmp && tar -xzf deploy.tar.gz && sudo ./install.sh"

        # Clean up tunnel
        kill $TUNNEL_PID 2>/dev/null || true

        print_status "Deployment to $vm_name complete!"
    fi
}

# Main deployment flow
create_deployment_package

for vm in $VM_LIST; do
    deploy_to_vm "$vm"
done

print_header "VM Deployment Complete"
print_status "Application deployed to all VMs"
