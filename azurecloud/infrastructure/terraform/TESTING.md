# Terraform Testing Guide

Complete guide for testing Terraform configuration before deploying to Azure.

## Quick Test

```bash
cd infrastructure/terraform/scripts
chmod +x test-terraform.sh
./test-terraform.sh prod
```

## Testing Levels

### Level 1: Syntax & Validation (Local, No Azure)

These tests run locally without Azure credentials:

```bash
cd environments/prod

# 1. Check Terraform version
terraform version

# 2. Format check
terraform fmt -check -recursive

# 3. Initialize (without backend)
terraform init -backend=false

# 4. Validate configuration
terraform validate

# 5. Check for issues
terraform fmt -check -recursive -diff
```

**Expected:** All commands should succeed with no errors.

### Level 2: Static Analysis (Local)

```bash
# 1. Check for security issues with tfsec
docker run --rm -v $(pwd):/src aquasec/tfsec /src

# 2. Check for best practices with checkov
pip install checkov
checkov -d .

# 3. Check costs with infracost
infracost breakdown --path .
```

### Level 3: Plan Test (Azure Required)

Tests configuration against Azure without making changes:

```bash
# 1. Login to Azure
az login

# 2. Set subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# 3. Initialize with backend
terraform init

# 4. Run plan
terraform plan -out=tfplan

# 5. Review plan
terraform show tfplan

# 6. Clean up
rm tfplan
```

**Expected:** Plan succeeds showing resources to be created.

### Level 4: Module Testing

Test individual modules independently:

```bash
cd modules/ai-foundry

# Initialize and validate
terraform init -backend=false
terraform validate

# Test with example values
terraform plan -var="project_name=test" \
               -var="environment=dev" \
               -var="location=eastus" \
               -var="resource_group_name=test-rg"
```

## Automated Test Script

The `test-terraform.sh` script runs 11 automated tests:

| Test | Description | Requirement |
|------|-------------|-------------|
| 1. Version | Terraform >= 1.5.0 | Local |
| 2. Validation | Configuration valid | Local |
| 3. Formatting | Code formatted | Local |
| 4. Providers | Providers configured | Local |
| 5. Modules | All modules valid | Local |
| 6. Variables | Required vars set | Local |
| 7. Backend | Backend configured | Local |
| 8. Security | No hardcoded secrets | Local |
| 9. Naming | Consistent naming | Local |
| 10. Documentation | Docs present | Local |
| 11. Plan | Dry run succeeds | Azure |

### Run All Tests

```bash
./scripts/test-terraform.sh prod
```

### Run Specific Test Type

```bash
# Just validation
cd environments/prod
terraform init -backend=false
terraform validate

# Just formatting
terraform fmt -check -recursive

# Just plan
az login
terraform init
terraform plan
```

## Test Checklist

Before deploying to production:

- [ ] All tests in `test-terraform.sh` pass
- [ ] `terraform fmt -check` has no changes
- [ ] `terraform validate` succeeds
- [ ] `terraform plan` succeeds
- [ ] Plan reviewed and understood
- [ ] No hardcoded secrets in `.tf` files
- [ ] `terraform.tfvars` configured (not checked in)
- [ ] Backend storage account exists
- [ ] Azure credentials valid
- [ ] Correct subscription selected
- [ ] Resource naming follows convention
- [ ] Cost estimate reviewed
- [ ] Team reviewed changes

## Testing in Different Environments

### Dev Environment

```bash
# Test dev environment
./scripts/test-terraform.sh dev

# Deploy to dev first
./scripts/deploy.sh dev apply
```

### Staging Environment

```bash
# Test staging
./scripts/test-terraform.sh staging

# Deploy to staging
./scripts/deploy.sh staging apply
```

### Production Environment

```bash
# ALWAYS test dev/staging first!

# Test prod
./scripts/test-terraform.sh prod

# Review plan carefully
./scripts/deploy.sh prod plan

# Get approval
# [ ] Manager approval
# [ ] Security review
# [ ] Cost approval

# Deploy
./scripts/deploy.sh prod apply
```

## Common Test Failures

### "terraform: command not found"

```bash
# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### "Error: Backend initialization required"

```bash
# Setup backend first
./scripts/setup-backend.sh prod
```

### "Error: Invalid provider configuration"

```bash
# Reinitialize
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### "Error: variables.tf not found"

```bash
# Wrong directory
cd environments/prod
terraform init
```

### "Error: terraform.tfvars required"

```bash
# Copy example
cp terraform.tfvars.example terraform.tfvars
# Edit with your values
nano terraform.tfvars
```

## CI/CD Testing

For automated testing in GitHub Actions / Azure DevOps:

```yaml
# .github/workflows/terraform-test.yml
name: Terraform Test

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0

      - name: Terraform Format
        run: terraform fmt -check -recursive
        working-directory: infrastructure/terraform

      - name: Terraform Init
        run: terraform init -backend=false
        working-directory: infrastructure/terraform/environments/dev

      - name: Terraform Validate
        run: terraform validate
        working-directory: infrastructure/terraform/environments/dev

      - name: Run Test Suite
        run: ./scripts/test-terraform.sh dev
        working-directory: infrastructure/terraform
```

## Cost Testing

Estimate costs before deploying:

### Using Azure Pricing Calculator

1. List resources from plan:
   ```bash
   terraform plan -out=tfplan
   terraform show -json tfplan | jq '.resource_changes[].address'
   ```

2. Enter each resource in: https://azure.microsoft.com/pricing/calculator/

### Using Infracost

```bash
# Install
brew install infracost
# or
curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh

# Login
infracost auth login

# Check costs
cd environments/prod
infracost breakdown --path .

# Compare changes
infracost diff --path .
```

## Security Testing

### Check for Secrets

```bash
# Scan for secrets
git secrets --scan -r .

# Or use gitleaks
docker run -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" -v
```

### Check Security Best Practices

```bash
# tfsec
docker run --rm -v $(pwd):/src aquasec/tfsec /src

# Checkov
pip install checkov
checkov -d . --framework terraform
```

## Performance Testing

Test Terraform performance:

```bash
# Time the plan
time terraform plan

# Profile
TF_LOG=TRACE terraform plan 2> trace.log
```

## Cleanup After Testing

```bash
# Remove test artifacts
rm -rf .terraform .terraform.lock.hcl tfplan terraform.tfstate*

# Keep
# - *.tf files
# - terraform.tfvars (gitignored)
# - terraform.tfvars.example
```

## Test Documentation

Test that your documentation is complete:

- [ ] README.md exists and up to date
- [ ] All modules documented
- [ ] Variables documented (description)
- [ ] Outputs documented
- [ ] Examples provided
- [ ] Architecture diagram included
- [ ] Cost estimates included
