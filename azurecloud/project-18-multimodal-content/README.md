# Project 18: Multi-Modal Content Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o%20%7C%20DALL--E%203-blue?style=flat)
![AI Vision](https://img.shields.io/badge/AI%20Vision-Image%20Analysis%204.0-green?style=flat)
![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-yellow?style=flat)
![Video Indexer](https://img.shields.io/badge/Video%20Indexer-Scene%20Detection-orange?style=flat)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade multi-modal content platform that enables brand teams, creative professionals, and accessibility engineers to analyze images, video, and audio assets using Azure AI Vision, Video Indexer, and Azure AI Speech, and to generate new content using Azure OpenAI GPT-4o and DALL-E 3. The platform powers brand content creation workflows, automated accessibility tagging (alt text, captions, transcripts), and GenAI-driven creative pipelines -- all governed by corporate brand guidelines and compliance policies.

## Architecture

```
Media Upload (Image/Video/Audio) --> APIM Auth --> Azure Functions (Content Orchestrator)
                                                       |
                            +--------------------------+--------------------------+
                            |                          |                          |
                       AI Vision               Video Indexer               AI Speech
                     (Objects, Tags,         (Scenes, OCR,              (Transcribe,
                      Faces, Text)            People, Transcripts)       Speaker ID)
                            |                          |                          |
                            +--------------------------+--------------------------+
                                                       |
                                    Enrich with Brand Guidelines (Cosmos DB)
                                                       |
                                    Index in AI Search (Tags, Embeddings)
                                                       |
                                    GPT-4o (Summarize + Generate Alt Text/Captions)
                                                       |
                                    Return Structured Analysis

Content Generation: Brief --> Brand Rules (Cosmos DB) --> DALL-E 3 / GPT-4o --> Brand Check --> CDN
```

**Key Components:**
- **Creative Studio** (React + Next.js) -- Multi-modal content creation workspace
- **Brand Portal** (React SPA) -- Brand asset management and approval workflows
- **Accessibility Dashboard** -- Accessibility audit, alt-text review, caption editing
- **Azure Functions** (Python 3.11) -- Content orchestration, media pipeline, brand compliance

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Multi-modal analysis, copy generation, summarization |
| Azure OpenAI (DALL-E 3) | Image generation from creative briefs |
| Azure AI Vision (Image Analysis 4.0) | Object detection, OCR, brand logo recognition |
| Azure Video Indexer | Scene detection, face identification, video transcription |
| Azure AI Speech | Speech-to-text, text-to-speech, audio transcription |
| Azure AI Search | Content discovery with vector embeddings and semantic ranking |
| Azure Cosmos DB | Metadata, brand rules, job state, user sessions |
| Azure Blob Storage | Media asset storage (images, video, audio) |
| Azure CDN | Low-latency media delivery for generated assets |
| Azure Media Services | Video encoding, adaptive bitrate, thumbnails |
| Azure Redis Cache | Result caching, rate limiting, job deduplication |
| Azure Key Vault | API keys, connection strings, certificates |
| Application Insights | APM, dependency tracking, content processing metrics |
| Log Analytics | Centralized logging for all media processing pipelines |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50.0
- Python >= 3.11
- Node.js >= 18 (for frontend)
- Terraform >= 1.5.0
- Azure Functions Core Tools >= 4.x
- Azure AI Vision resource provisioned
- Azure Video Indexer account

## Quick Start

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd azurecloud/project-18-multimodal-content

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### Environment Variables

```bash
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
VISION_ENDPOINT=https://<your-vision>.cognitiveservices.azure.com/
SPEECH_ENDPOINT=https://<your-speech>.cognitiveservices.azure.com/
COSMOS_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
KEY_VAULT_URL=https://<your-keyvault>.vault.azure.net/
STORAGE_ACCOUNT_URL=https://<your-storage>.blob.core.windows.net
STORAGE_CONNECTION=<storage-connection-string>
```

### Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Deploy Application

```bash
cd src
func azure functionapp publish <your-function-app-name>
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_function_app.py -v

# Run integration tests
python -m pytest test_integration.py -v

# Test health endpoint
curl https://<function-app>.azurewebsites.net/api/health
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID (OAuth2/OIDC) with Conditional Access and MFA enforcement for all users
- **Authorization**: Role-based content access with hierarchy: creator, reviewer, publisher; fine-grained RBAC per brand asset
- **Managed Identity**: System-assigned managed identity for zero-credential service-to-service authentication
- **Network Isolation**: Dedicated VNet with Application, Data, and Integration subnets; all PaaS services behind Private Link; CDN with WAF protection
- **Content Safety**: Azure AI Content Safety API for filtering inappropriate AI-generated content

### Encryption

- **Data at Rest**: AES-256 encryption for all media assets in Blob Storage and Cosmos DB; Customer-Managed Keys (CMK) via Key Vault
- **Data in Transit**: TLS 1.2+ enforced across all service communication; CDN configured with HTTPS-only delivery
- **Key Management**: Azure Key Vault with RBAC, soft delete, and purge protection; content encryption keys and DRM certificates managed centrally

### Monitoring

- **Application Insights**: APM with dependency tracking for AI Vision, Video Indexer, Speech, and OpenAI calls; custom metrics for media processing latency
- **Log Analytics**: Per-GB ingestion (~50GB/mo) with centralized logging for all content processing workflows
- **Alerts**: Azure Monitor alerts on content processing failures, DALL-E quota exhaustion, and brand compliance violations
- **Dashboards**: Content processing pipeline health, brand compliance rates, and accessibility coverage metrics

### Visualization

- **Creative Studio Dashboard**: Real-time content creation pipeline status with media preview
- **Content Safety Logs**: Dashboard tracking content moderation outcomes and flagged assets
- **Cost Management Dashboard**: Azure Cost Management for per-service cost tracking including DALL-E and AI Vision usage

### Tracking

- **Request Tracing**: Distributed tracing via Application Insights across all media processing stages (upload, analyze, index, generate)
- **Correlation IDs**: End-to-end correlation for every content request from upload through CDN delivery
- **Audit Logs**: All content creation, modification, and publication events logged with user context and timestamps
- **IP Tracking**: Source attribution and licensing compliance tracking for third-party content

### Accuracy

- **Model Evaluation**: AI Vision object detection accuracy benchmarked against labeled datasets; GPT-4o alt-text quality evaluated by accessibility auditors
- **Confidence Thresholds**: Image analysis tags include confidence scores; low-confidence results flagged for human review
- **Brand Compliance Validation**: Post-generation AI Vision validates output against brand asset library in AI Search

### Explainability

- Image analysis results include bounding boxes, confidence scores, and dense captions explaining what was detected and where
- Generated content includes the revised prompt from DALL-E 3, showing how the model interpreted the creative brief
- Accessibility tags reference WCAG criteria that informed the generated alt text and ARIA labels

### Responsibility

- **Content Safety**: Azure AI Content Safety filters all generated images and text for harmful, inappropriate, or biased content
- **AI Content Labeling**: AI-generated content labeled per emerging regulations (FTC Guidelines)
- **Watermarking**: Invisible watermarks applied to AI-generated content for provenance tracking
- **Brand Safety**: Automated brand guideline compliance checking prevents off-brand content from reaching publication

### Interpretability

- **Feature Decomposition**: AI Vision provides per-object confidence scores and bounding box coordinates
- **Decision Transparency**: Brand compliance engine shows which guidelines each generated asset was validated against
- **Accessibility Audit Trail**: Each accessibility tag includes the WCAG criteria it satisfies and the source analysis that produced it

### Portability

- **Containerization**: Azure Functions deployable as Docker containers; media processing pipeline runnable locally
- **Infrastructure as Code**: Full Terraform configuration in `infra/` for reproducible multi-environment deployments
- **Multi-Cloud Considerations**: OpenAI API is compatible with non-Azure OpenAI endpoints; media processing patterns transferable to AWS Rekognition or GCP Vision
- **Standards Compliance**: WCAG 2.1 AA accessibility output is platform-agnostic; content exportable to any CMS

## Project Structure

```
project-18-multimodal-content/
|-- docs/
|   |-- ARCHITECTURE.md          # Detailed architecture documentation
|-- infra/
|   |-- main.tf                  # Terraform infrastructure definitions
|-- src/
|   |-- function_app.py          # Azure Functions (analyze, generate, accessibility, brand)
|   |-- requirements.txt         # Python dependencies
|-- tests/
|   |-- test_function_app.py     # Unit and integration tests
|-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze-image` | Analyze image for tags, captions, objects, and OCR text |
| POST | `/api/generate-image` | Generate image using DALL-E 3 from text prompt |
| POST | `/api/analyze-video` | Analyze video for scenes, objects, themes, and tags |
| POST | `/api/accessibility-tag` | Generate WCAG-compliant accessibility metadata for content |
| POST | `/api/brand-content` | Create brand-aligned content from creative brief |
| GET | `/api/health` | Health check with capability listing |
| Blob Trigger | `MediaAssetProcessor` | Auto-process new media uploads (image/video/audio) |

## License

This project is licensed under the MIT License.
