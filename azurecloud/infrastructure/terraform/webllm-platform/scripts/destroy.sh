#!/bin/bash
#===============================================================================
# WebLLM Platform - Destroy Script
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${RED}========================================"
echo "WARNING: This will destroy all resources!"
echo "========================================${NC}"
echo ""

read -p "Are you sure you want to destroy all resources? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

cd "$PROJECT_ROOT"

echo -e "${YELLOW}Destroying Kubernetes resources...${NC}"
kubectl delete -f k8s/webllm-router/ --ignore-not-found || true
kubectl delete -f k8s/mlc-llm/ --ignore-not-found || true

echo -e "${YELLOW}Destroying Terraform resources...${NC}"
terraform destroy -auto-approve

echo -e "${GREEN}All resources destroyed.${NC}"
