# Project 10: Code Review & DevOps Copilot

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=flat&logo=openai&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-Python_3.11-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-Integrated-0078D4?style=flat&logo=azuredevops&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-API-181717?style=flat&logo=github&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade AI-powered platform that automates code review, pull request summarization, incident root cause analysis (RCA), and deployment risk scoring. The system integrates with Azure DevOps and GitHub APIs to analyze code changes in real time, leveraging Azure OpenAI GPT-4o for intelligent review comments, PR summaries, and incident correlation. Azure AI Search indexes historical incidents, past reviews, and runbook knowledge to provide context-aware recommendations. The platform supports both synchronous HTTP-based review requests and asynchronous Service Bus-driven batch processing for large PRs, with all review decisions logged to Cosmos DB for audit and analytics.

---

## Architecture

```
Interfaces (DevOps Portal, Teams Bot, VS Code Extension)
        |
   Azure Front Door (WAF + CDN + SSL)
        |
   +--------+--------+
   |        |        |
  APIM    Static   Azure
  Gateway  Web App  SignalR
  (Auth,   (Dash-   (Real-time
   Rate    board)   Notifications)
   Limit)
        |
   Private VNet (10.0.0.0/16)
        |
   Azure Functions (Copilot Engine)
   +--------+--------+--------+--------+
   |        |        |        |        |
 Code     PR      RCA      Risk    Webhook
 Reviewer Summary Analyzer Scorer  Processor
   |        |        |        |
   +--------+--------+--------+
   |        |        |
Azure     Azure    Azure
OpenAI    AI Search DevOps API
(GPT-4o)  (Vector   + GitHub API
           Index)
        |
   +--------+--------+
   |        |        |
 Cosmos   Blob    Redis
 DB       Storage  Cache
 (Reviews, (Diffs,  (PR Cache,
  RCA,     Logs)    Rate State)
  Risk)
        |
   Webhook Ingestion Pipeline
   (DevOps Webhooks + GitHub Webhooks + Azure Monitor Alerts)
        |
   Service Bus Queue (Event Routing)
        |
   Async Processing Functions
   (Code Review, PR Summary, Incident RCA)
        |
   Observability (App Insights + Log Analytics + Prompt Flow Tracing)
```

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure OpenAI (GPT-4o) | Code review, PR summarization, RCA generation, risk analysis |
| Azure OpenAI (ada-002) | Vector embeddings for code diffs and incident knowledge |
| Azure AI Search | Semantic + vector search over historical incidents, code patterns, runbooks |
| Azure DevOps API | Repository access, PR diffs, pipeline webhooks, work item creation |
| GitHub API | Repository access, PR diffs, webhook ingestion |
| Azure Cosmos DB | Review records, RCA reports, risk assessments, incident data (serverless) |
| Azure Blob Storage | Code diffs, deployment logs, artifacts (encrypted at rest) |
| Azure Cache for Redis | PR diff cache, review result cache, rate limiting state (P1 Premium) |
| Azure Service Bus | Event-driven webhook routing with dead-letter queues (3 queues) |
| Azure Key Vault | API keys, PATs (GitHub/DevOps), connection strings (automated rotation) |
| Azure SignalR | Real-time review status and alert streaming |
| Application Insights | APM, distributed tracing, Prompt Flow tracing |
| Log Analytics | Centralized logging for review decisions and AI suggestions |

---

## Prerequisites

- **Azure Subscription** with the following resources:
  - Azure OpenAI Service (GPT-4o and text-embedding-ada-002 deployments)
  - Azure AI Search (S1 tier with 3 replicas)
  - Azure Cosmos DB (serverless)
  - Azure Service Bus (Standard tier)
  - Azure Cache for Redis (P1 Premium)
- **Azure DevOps Organization** with PAT for API access (stored in Key Vault)
- **GitHub** organization/repository with PAT for API access (stored in Key Vault)
- **Python 3.11+**
- **Azure Functions Core Tools v4**
- **Azure CLI** (authenticated)

---

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-10-code-review-copilot

# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://<openai-resource>.openai.azure.com/"
export COSMOS_ENDPOINT="https://<cosmos-account>.documents.azure.com:443/"
export KEY_VAULT_URL="https://<keyvault-name>.vault.azure.net/"
export DEVOPS_ORG_URL="https://dev.azure.com/<organization>"
export GITHUB_API_URL="https://api.github.com"
export SERVICE_BUS_CONNECTION="<service-bus-connection-string>"
```

### 2. Install dependencies

```bash
cd src
pip install -r requirements.txt
```

### 3. Run locally

```bash
func start
```

### 4. Configure webhooks

```bash
# Azure DevOps: Configure service hook for PR created/updated events
# GitHub: Configure webhook for pull_request events
# Point webhooks to: https://<function-app>.azurewebsites.net/api/webhook
```

### 5. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -var-file="env/dev.tfvars"
terraform apply -var-file="env/dev.tfvars"
```

### 6. Deploy function app

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

---

## Testing

```bash
# Run unit tests
cd tests
python -m pytest -v

# Run tests with coverage
python -m pytest --cov=src --cov-report=html -v
```

---

## Cross-Cutting Concerns

### Security

- **Authentication**: Entra ID OAuth2/OIDC with conditional access for dashboard SSO; MFA enforcement
- **Authorization**: Repository-level access control aligned with Azure DevOps/GitHub permissions; PIM for just-in-time admin access
- **RBAC**: Fine-grained roles for developers, tech leads, SREs, and engineering managers
- **Managed Identity**: System-assigned managed identity for all Azure service-to-service authentication -- zero credentials in code
- **Network Isolation**: Dedicated VNet with Application, Data, and Integration subnets; all PaaS services via Private Link; NSG least-privilege rules
- **PAT Security**: GitHub and Azure DevOps PATs stored in Key Vault with automated rotation
- **Prompt Injection Guard**: Input validation prevents prompt injection attacks via malicious code comments

### Encryption

- **Data at Rest**: AES-256 encryption for Cosmos DB, Blob Storage, and Redis; CMK via Key Vault for sensitive data
- **Data in Transit**: TLS 1.2+ enforced on all endpoints; HTTPS-only for all API communications
- **Code Content Protection**: Code diffs encrypted at rest; never persisted in plain text
- **PAT Rotation**: Automated Personal Access Token rotation for DevOps and GitHub integrations
- **Secret Detection**: Pre-commit hooks and pipeline scanning for secrets and PII in code

### Monitoring

- **Application Insights**: APM for Azure Functions with custom metrics for review latency, finding counts, risk score distributions, and token usage
- **Log Analytics**: Centralized logging for review decisions, AI suggestions, and webhook processing
- **Alerts**: Configured for Service Bus dead-letter queue depth, high error rates, OpenAI latency spikes, and Redis cache miss ratios
- **Prompt Flow Tracing**: End-to-end tracing of GPT-4o prompt chains for code review, RCA, and risk scoring
- **Dashboards**: Azure Monitor dashboards for review throughput, mean review time, and finding severity distribution

### Visualization

- **DevOps Dashboard**: React/Next.js unified dashboard for review status, RCA reports, and deployment risk
- **VS Code Extension**: In-editor code review suggestions via TypeScript VS Code API
- **Teams Integration**: Bot Framework integration for incident alerts, RCA notifications, and review summaries

### Tracking

- **Request Tracing**: Application Insights distributed tracing with correlation IDs across webhook ingestion, code analysis, and comment posting
- **Correlation IDs**: MD5-hashed `review_id`, `summary_id`, `rca_id`, and `assessment_id` generated per request for end-to-end traceability
- **Audit Logs**: All review records persisted to Cosmos DB `reviews` container with review type, timestamp, request data, and AI-generated result
- **DevOps Audit**: Code review decisions and AI suggestions logged for compliance and retrospective analysis

### Accuracy

- **Code Review Quality**: GPT-4o analyzes for security vulnerabilities, logic errors, null pointer risks, resource leaks, race conditions, SQL injection, XSS, hardcoded secrets, and complexity issues
- **Quality Score**: Each review produces a 1-10 quality score across the entire diff
- **Risk Scoring**: Deployment risk scored 0.0-1.0 with clear thresholds (High > 0.7, Medium > 0.4, Low)
- **Finding Severity**: Findings categorized as critical, high, medium, low, or info across bug, security, performance, style, and maintainability types
- **Historical Pattern Matching**: AI Search vector index enables matching current code patterns against historically problematic diffs

### Explainability

- **Structured Findings**: Each code review finding includes `type`, `severity`, `file`, `line`, `description`, and `suggestion` for actionable context
- **PR Summary Breakdown**: PR summaries include `change_overview`, `key_changes` grouped by category, `risk_areas`, `breaking_changes`, and `estimated_review_time_minutes`
- **RCA Reports**: Incident analysis produces `root_cause` with confidence level, `contributing_factors`, chronological `timeline`, and `prevention_recommendations`
- **Risk Factor Decomposition**: Deployment risk includes individual `risk_factors` with per-factor scores and specific `mitigation_strategies`
- **Go/No-Go Recommendation**: Deployment risk assessment produces clear `go`, `go_with_caution`, or `no_go` recommendation

### Responsibility

- **Content Filtering**: Azure OpenAI content filtering prevents misuse of the code review and analysis capabilities
- **IP Protection**: Proprietary source code never sent to external AI services without explicit approval
- **SAST/DAST Integration**: Static and dynamic application security testing integrated into the review pipeline
- **OSS License Compliance**: Automated open-source license compatibility checking (GPL, MIT, Apache, etc.)
- **AI Ethics**: AI review suggestions evaluated for bias and security implications per organizational policy
- **Human-in-the-Loop**: AI reviews are suggestions; human reviewers make final approval decisions

### Interpretability

- **Metric Transparency**: Reviews include `metrics` (additions, deletions, files_changed) alongside findings for context
- **Comment Formatting**: Review comments prefixed with severity tags ([CRITICAL], [HIGH], [MEDIUM], [LOW], [INFO]) for rapid triage
- **Confidence Levels**: RCA reports include confidence level for root cause determination; risk assessments include overall confidence score
- **Token Usage**: Every API response includes `usage` metrics (prompt/completion/total tokens) for cost and performance tracking

### Portability

- **Infrastructure as Code**: Terraform modules in `infra/` for complete environment provisioning (dev/staging/production)
- **Containerization**: Azure Functions can be containerized; webhook processor supports Node.js 20 runtime
- **Multi-Platform**: Supports both Azure DevOps and GitHub via abstracted API integration layer
- **Event-Driven Architecture**: Service Bus decoupling enables swapping message brokers (RabbitMQ, Kafka) with minimal code changes
- **Environment Configuration**: All endpoints, thresholds, and API URLs externalized via environment variables and Config class

---

## Project Structure

```
project-10-code-review-copilot/
|-- docs/
|   +-- ARCHITECTURE.md
|-- infra/
|   +-- main.tf
|-- src/
|   +-- function_app.py
|-- tests/
+-- README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/review-code` | AI code review analyzing diff for bugs, security, performance, and style |
| POST | `/api/summarize-pr` | Generate structured PR summary with risk areas and review recommendations |
| POST | `/api/incident-rca` | Root cause analysis from incident data and application logs |
| POST | `/api/deployment-risk` | Deployment risk assessment with go/no-go recommendation |
| GET | `/api/health` | Health check endpoint |
| -- | `AsyncPRReviewProcessor` | Service Bus trigger: async PR review for large diffs with callback |

---

## License

This project is licensed under the MIT License.
