#!/bin/bash
# =============================================================================
# Terraform Testing Script
# =============================================================================
# Tests Terraform configuration without deploying resources

set -e

ENVIRONMENT=${1:-prod}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../environments/$ENVIRONMENT"

echo "=============================================="
echo "Terraform Testing Suite"
echo "=============================================="
echo "Environment: $ENVIRONMENT"
echo "=============================================="

cd "$TERRAFORM_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# =============================================================================
# Test 1: Terraform Version
# =============================================================================
echo ""
echo "Test 1: Terraform Version"
echo "----------------------------"
TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
REQUIRED_VERSION="1.5.0"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$TERRAFORM_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    pass "Terraform version $TERRAFORM_VERSION >= $REQUIRED_VERSION"
else
    fail "Terraform version $TERRAFORM_VERSION < $REQUIRED_VERSION"
fi

# =============================================================================
# Test 2: Configuration Validation
# =============================================================================
echo ""
echo "Test 2: Configuration Validation"
echo "-----------------------------------"

terraform init -backend=false > /dev/null 2>&1 || fail "Terraform init failed"

if terraform validate > /dev/null 2>&1; then
    pass "Terraform configuration is valid"
else
    fail "Terraform configuration is invalid"
    terraform validate
fi

# =============================================================================
# Test 3: Formatting Check
# =============================================================================
echo ""
echo "Test 3: Formatting Check"
echo "-------------------------"

if terraform fmt -check -recursive > /dev/null 2>&1; then
    pass "All files are properly formatted"
else
    warn "Some files need formatting. Run: terraform fmt -recursive"
    terraform fmt -check -recursive
fi

# =============================================================================
# Test 4: Provider Requirements
# =============================================================================
echo ""
echo "Test 4: Provider Requirements"
echo "-------------------------------"

PROVIDERS=$(terraform providers | grep -E "provider\[" | wc -l)
if [ "$PROVIDERS" -gt 0 ]; then
    pass "Found $PROVIDERS provider(s)"
    terraform providers
else
    fail "No providers configured"
fi

# =============================================================================
# Test 5: Module Dependencies
# =============================================================================
echo ""
echo "Test 5: Module Dependencies"
echo "----------------------------"

# Check if modules directory exists
MODULE_DIR="$SCRIPT_DIR/../modules"
if [ -d "$MODULE_DIR" ]; then
    MODULE_COUNT=$(find "$MODULE_DIR" -maxdepth 1 -type d | wc -l)
    pass "Found $((MODULE_COUNT - 1)) module(s)"
else
    fail "Modules directory not found"
fi

# Validate each module
for module_dir in "$MODULE_DIR"/*; do
    if [ -d "$module_dir" ]; then
        module_name=$(basename "$module_dir")
        cd "$module_dir"

        if terraform init -backend=false > /dev/null 2>&1 && terraform validate > /dev/null 2>&1; then
            pass "  $module_name: valid"
        else
            fail "  $module_name: invalid"
        fi

        cd "$TERRAFORM_DIR"
    fi
done

# =============================================================================
# Test 6: Variables Check
# =============================================================================
echo ""
echo "Test 6: Variables Check"
echo "------------------------"

if [ -f "terraform.tfvars" ]; then
    pass "terraform.tfvars exists"

    # Check for required variables
    REQUIRED_VARS=("project_name" "environment" "location")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}\s*=" terraform.tfvars; then
            pass "  $var is configured"
        else
            warn "  $var is not configured"
        fi
    done
else
    warn "terraform.tfvars not found (will use defaults)"
fi

# =============================================================================
# Test 7: Backend Configuration
# =============================================================================
echo ""
echo "Test 7: Backend Configuration"
echo "-------------------------------"

if grep -q "backend \"azurerm\"" main.tf; then
    pass "Azure backend is configured"

    # Extract backend config
    BACKEND_RG=$(grep -A10 "backend \"azurerm\"" main.tf | grep "resource_group_name" | awk -F'"' '{print $2}')
    BACKEND_SA=$(grep -A10 "backend \"azurerm\"" main.tf | grep "storage_account_name" | awk -F'"' '{print $2}')

    if [ -n "$BACKEND_RG" ] && [ -n "$BACKEND_SA" ]; then
        pass "  Resource Group: $BACKEND_RG"
        pass "  Storage Account: $BACKEND_SA"
    fi
else
    warn "No backend configuration found (using local state)"
fi

# =============================================================================
# Test 8: Security Check
# =============================================================================
echo ""
echo "Test 8: Security Check"
echo "-----------------------"

# Check for hardcoded secrets
SECURITY_ISSUES=0

if grep -r "password\s*=\s*\"" . --include="*.tf" --exclude-dir=".terraform" > /dev/null 2>&1; then
    warn "Potential hardcoded password found"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

if grep -r "api_key\s*=\s*\"" . --include="*.tf" --exclude-dir=".terraform" | grep -v "null" > /dev/null 2>&1; then
    warn "Potential hardcoded API key found"
    SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
fi

if [ $SECURITY_ISSUES -eq 0 ]; then
    pass "No obvious security issues found"
else
    warn "Found $SECURITY_ISSUES potential security issue(s)"
fi

# =============================================================================
# Test 9: Resource Naming
# =============================================================================
echo ""
echo "Test 9: Resource Naming"
echo "------------------------"

# Check naming conventions
if grep -r "name\s*=\s*\"\${.*-.*-.*}\"" . --include="*.tf" --exclude-dir=".terraform" > /dev/null 2>&1; then
    pass "Using consistent naming convention"
else
    warn "Inconsistent naming convention detected"
fi

# =============================================================================
# Test 10: Documentation
# =============================================================================
echo ""
echo "Test 10: Documentation"
echo "-----------------------"

DOC_COUNT=0

if [ -f "README.md" ]; then
    pass "README.md exists"
    DOC_COUNT=$((DOC_COUNT + 1))
fi

if [ -f "terraform.tfvars.example" ]; then
    pass "terraform.tfvars.example exists"
    DOC_COUNT=$((DOC_COUNT + 1))
fi

if [ $DOC_COUNT -lt 2 ]; then
    warn "Missing some documentation files"
fi

# =============================================================================
# Test 11: Dry Run (Plan without apply)
# =============================================================================
echo ""
echo "Test 11: Dry Run Plan"
echo "----------------------"

# Check if Azure CLI is available
if command -v az &> /dev/null; then
    if az account show &> /dev/null 2>&1; then
        echo "Running terraform plan (dry run)..."

        terraform init > /dev/null 2>&1

        if terraform plan -detailed-exitcode > /tmp/terraform_plan.log 2>&1; then
            pass "Terraform plan succeeded (no changes)"
        elif [ $? -eq 2 ]; then
            pass "Terraform plan succeeded (with changes)"
            echo ""
            echo "Preview of changes:"
            tail -20 /tmp/terraform_plan.log
        else
            fail "Terraform plan failed"
            cat /tmp/terraform_plan.log
        fi
    else
        warn "Not logged in to Azure (skipping plan test)"
    fi
else
    warn "Azure CLI not found (skipping plan test)"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo "All critical tests passed!"
echo ""
echo "Next steps:"
echo "  1. Review any warnings above"
echo "  2. Run: ./deploy.sh $ENVIRONMENT plan"
echo "  3. Review the plan carefully"
echo "  4. Run: ./deploy.sh $ENVIRONMENT apply"
echo "=============================================="
