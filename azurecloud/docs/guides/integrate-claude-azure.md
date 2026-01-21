# Integrating Claude with Azure

This guide covers three ways to use Claude (Anthropic's AI) with your Azure deployment.

## Overview

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Direct Anthropic API** | Quick setup, development | Simple, latest models | Data leaves Azure |
| **Azure AI Foundry** | Enterprise, compliance | Data stays in Azure | Limited regions |
| **Hybrid Setup** | Best of both worlds | Flexibility | More configuration |

---

## Method 1: Direct Anthropic API

**Time: 5 minutes**

### Step 1: Get API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Click **Settings** → **API Keys**
4. Click **Create Key**
5. Save the key (starts with `sk-ant-`)

### Step 2: Configure

```bash
cd deployments/desktop
cp .env.example .env
```

Edit `.env`:
```bash
# Use Claude as LLM provider
RAG_LLM_PROVIDER=anthropic
RAG_ANTHROPIC__API_KEY=sk-ant-api03-xxxxxxxxxxxx
RAG_ANTHROPIC__MODEL=claude-sonnet-4-20250514

# Embeddings (Claude doesn't have embeddings, use Ollama locally)
RAG_VECTOR_DB_PROVIDER=chromadb
RAG_OLLAMA__EMBEDDING_MODEL=nomic-embed-text
```

### Step 3: Run

```bash
# Start Ollama for embeddings
ollama serve &
ollama pull nomic-embed-text

# Start the API
python -m uvicorn src.api.main:app --reload
```

### Step 4: Test

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Azure?", "user_id": "test"}'
```

---

## Method 2: Azure AI Foundry (Claude in Azure)

**Time: 30 minutes**

### Prerequisites

- Azure subscription with AI services access
- Claude available in your region (check Azure documentation)
- Azure CLI installed

### Step 1: Check Availability

```bash
# Login to Azure
az login

# Install ML extension
az extension add -n ml

# Check if Claude is available
az ml model list --registry-name azureml \
  --query "[?contains(name, 'Claude')]" -o table
```

### Step 2: Deploy with Terraform (Recommended)

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Create terraform.tfvars
cat > terraform.tfvars << EOF
project_name        = "rag"
environment         = "prod"
location            = "eastus"
resource_group_name = "rg-rag-prod"

# Enable Claude deployment
deploy_claude       = true
claude_model_id     = "azureml://registries/azureml/models/Anthropic-Claude-3-5-Sonnet/versions/1"
EOF

# Plan and apply
terraform plan -target=module.ai_foundry
terraform apply -target=module.ai_foundry
```

### Step 3: Alternative - Azure Portal

1. Go to https://ml.azure.com
2. Select your workspace
3. Click **Model catalog** in left menu
4. Search for "Claude" or "Anthropic"
5. Select **Claude 3.5 Sonnet** (or available version)
6. Click **Deploy** → **Serverless API**
7. Accept marketplace terms
8. Note the endpoint URL and key

### Step 4: Get Credentials

**From Terraform outputs:**
```bash
terraform output claude_endpoint_id
terraform output key_vault_uri

# Get endpoint key from Key Vault
az keyvault secret show \
  --vault-name $(terraform output -raw key_vault_name) \
  --name claude-endpoint-uri \
  --query value -o tsv
```

**From Azure CLI:**
```bash
# Get endpoint URL
az ml serverless-endpoint show \
  --name claude-sonnet-endpoint \
  --resource-group rg-rag-prod \
  --workspace-name rag-prod-ai-hub \
  --query "properties.inferenceEndpoint.uri" -o tsv

# Get API key
az ml serverless-endpoint get-credentials \
  --name claude-sonnet-endpoint \
  --resource-group rg-rag-prod \
  --workspace-name rag-prod-ai-hub \
  --query "primaryKey" -o tsv
```

### Step 5: Configure

```bash
# In .env
AZURE_AI_CLAUDE_ENDPOINT=https://your-endpoint.inference.ai.azure.com
AZURE_AI_CLAUDE_KEY=your-api-key

# For embeddings, use Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-key
```

### Step 6: Use in Code

```python
from src.services.hybrid_llm_service import AzureAIFoundryClaudeService

service = AzureAIFoundryClaudeService(
    endpoint="https://your-endpoint.inference.ai.azure.com",
    api_key="your-api-key",
    azure_openai_endpoint="https://your-openai.openai.azure.com/",
    azure_openai_key="your-openai-key"
)

response = await service.chat([
    {"role": "user", "content": "Hello Claude!"}
])
```

---

## Method 3: Hybrid Setup (Claude + Azure Embeddings)

**Best for production** - Claude quality + Azure embeddings

### Configuration

```bash
# .env file

# Claude for chat (high quality reasoning)
RAG_LLM_PROVIDER=anthropic
RAG_ANTHROPIC__API_KEY=sk-ant-api03-xxxxxxxxxxxx
RAG_ANTHROPIC__MODEL=claude-sonnet-4-20250514
RAG_ANTHROPIC__EMBEDDING_PROVIDER=azure_openai

# Azure OpenAI for embeddings (fast, scalable)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
RAG_AZURE_OPENAI__ENDPOINT=${AZURE_OPENAI_ENDPOINT}
RAG_AZURE_OPENAI__API_KEY=${AZURE_OPENAI_API_KEY}
RAG_AZURE_OPENAI__EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Vector DB (can be local or Azure)
RAG_VECTOR_DB_PROVIDER=chromadb  # or azure_search
```

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Hybrid LLM Service                      │
│  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │   Claude (Chat)     │  │  Azure OpenAI (Embed)   │  │
│  │   - Reasoning       │  │  - text-embedding-3     │  │
│  │   - Responses       │  │  - Fast & scalable      │  │
│  └─────────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────────────┐
│  Anthropic API  │          │     Azure OpenAI        │
│  (us/eu)        │          │  (your Azure region)    │
└─────────────────┘          └─────────────────────────┘
```

### Code Example

```python
from src.services.hybrid_llm_service import HybridClaudeService

# Create hybrid service
service = HybridClaudeService(
    # Claude for chat
    anthropic_api_key="sk-ant-xxx",
    claude_model="claude-sonnet-4-20250514",

    # Azure OpenAI for embeddings
    embedding_provider="azure_openai",
    azure_endpoint="https://your-openai.openai.azure.com/",
    azure_api_key="your-key",
    azure_embedding_deployment="text-embedding-3-large"
)

# Chat uses Claude
response = await service.chat([
    {"role": "user", "content": "Explain quantum computing"}
])

# Embeddings use Azure OpenAI
embeddings = await service.embed("quantum computing basics")
```

---

## Comparison

### Latency

| Provider | Chat Latency | Embedding Latency |
|----------|--------------|-------------------|
| Claude (Direct) | 1-3s | N/A |
| Azure AI Foundry | 1-3s | N/A |
| Azure OpenAI | 0.5-2s | 0.1-0.3s |
| Ollama (Local) | 2-10s | 0.5-1s |

### Cost (Approximate)

| Provider | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|----------------------|------------------------|
| Claude Sonnet | $3.00 | $15.00 |
| GPT-4o-mini | $0.15 | $0.60 |
| Azure Embeddings | $0.13 | N/A |

### Recommendations

| Use Case | Recommended Setup |
|----------|-------------------|
| Development | Claude Direct + Ollama embeddings |
| Production | Claude Direct + Azure OpenAI embeddings |
| Enterprise/Compliance | Azure AI Foundry Claude + Azure OpenAI |
| Fully Local | Ollama (no Claude) |

---

## Troubleshooting

### "API key invalid"

```bash
# Verify Anthropic key format
echo $ANTHROPIC_API_KEY | grep "sk-ant-"

# Test the key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

### "Claude not available in region"

Check Azure AI Foundry model availability:
- US regions: Usually available
- EU regions: Check compliance requirements
- Other regions: May require different approach

### "Embeddings failed"

Claude doesn't have embeddings. Ensure you have a separate embedding provider configured:

```bash
# Check embedding provider
echo $RAG_ANTHROPIC__EMBEDDING_PROVIDER

# Should be one of: azure_openai, openai, ollama
```

---

## Security Considerations

1. **API Keys**: Store in Azure Key Vault or environment variables
2. **Network**: Use private endpoints for Azure services
3. **Data Residency**: Azure AI Foundry keeps data in Azure region
4. **Compliance**: Check Anthropic's data policies for direct API use

```bash
# Store key in Azure Key Vault
az keyvault secret set \
  --vault-name your-keyvault \
  --name AnthropicApiKey \
  --value "sk-ant-xxx"
```
