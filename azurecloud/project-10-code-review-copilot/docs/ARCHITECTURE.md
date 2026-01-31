# Project 10: Code Review & DevOps Copilot

## Executive Summary

An enterprise-grade AI-powered platform that automates code review, pull request summarization, incident root cause analysis (RCA), and deployment risk scoring. The system integrates with Azure DevOps and GitHub APIs to analyze code changes in real time, leveraging Azure OpenAI GPT-4o for intelligent review comments, PR summaries, and incident correlation. Azure AI Search indexes historical incidents, past reviews, and runbook knowledge to provide context-aware recommendations and deployment risk assessments via a unified DevOps dashboard.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        CODE REVIEW & DEVOPS COPILOT PLATFORM                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DevOps Portal  │     │  Teams Bot      │     │  VS Code        │
│  (React/Next.js)│     │  (Bot Service)  │     │  Extension      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Azure Front Door      │
                    │   (WAF + CDN + SSL)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   APIM Gateway  │   │  Static Web App │   │  Azure SignalR  │
│  (Rate Limit,   │   │  (Dashboard UI) │   │  (Real-time     │
│   Auth, Cache)  │   │                 │   │   Notifications)│
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
         │  ┌──────────────────────────────────────────────────────────────┐
         │  │                 PRIVATE VNET (10.0.0.0/16)                   │
         │  │  ┌────────────────────────────────────────────────────────┐  │
         │  │  │            Application Subnet (10.0.1.0/24)           │  │
         ▼  │  │                                                        │  │
┌───────────┴──┴───┐                                                    │  │
│ Azure Functions  │◄───────────────────────────────────────────────┐   │  │
│ (Copilot Engine) │                                                │   │  │
│                  │    ┌──────────────────┐   ┌─────────────────┐  │   │  │
│ - Code Reviewer  │    │  Azure OpenAI    │   │  Azure DevOps   │  │   │  │
│ - PR Summarizer  │◄───┤  (GPT-4o)       │   │  API            │  │   │  │
│ - RCA Analyzer   │    │  Private Link    │   │  (Repos/PRs/    │  │   │  │
│ - Risk Scorer    │    └──────────────────┘   │   Pipelines)    │  │   │  │
│ - Incident Mgr   │                           └─────────────────┘  │   │  │
└────────┬─────────┘    ┌──────────────────┐   ┌─────────────────┐  │   │  │
         │              │  GitHub API      │   │  Service Bus    │  │   │  │
         ├─────────────►│  (Repos/PRs/     │   │  (Event Queue)  │  │   │  │
         │              │   Webhooks)      │   │  Private Link   │  │   │  │
         │              └──────────────────┘   └────────┬────────┘  │   │  │
         │                                              │           │   │  │
         │              ┌──────────────────┐            │           │   │  │
         ├─────────────►│  Azure AI Search │◄───────────┘           │   │  │
         │              │  (Vector Index)  │                        │   │  │
         │              │  - Incident KB   │                        │   │  │
         │              │  - Code Patterns │                        │   │  │
         │              │  - Runbooks      │                        │   │  │
         │              └────────┬─────────┘                        │   │  │
         │                       │                                  │   │  │
         │  ┌────────────────────┼──────────────────────────────┐   │   │  │
         │  │            Data Subnet (10.0.2.0/24)              │   │   │  │
         │  │                    │                               │   │   │  │
         │  │    ┌───────────────┼───────────────┐              │   │   │  │
         │  │    │               │               │              │   │   │  │
         │  │    ▼               ▼               ▼              │   │   │  │
         │  │ ┌──────┐     ┌──────────┐    ┌───────┐           │   │   │  │
         │  │ │ Blob │     │ Cosmos DB│    │ Redis │           │   │   │  │
         │  │ │Store │     │(Reviews, │    │ Cache │           │   │   │  │
         │  │ │(Logs,│     │ Incidents│    │(PR &  │           │   │   │  │
         │  │ │ Diffs│     │ RCA Data)│    │ Query │           │   │   │  │
         │  │ │ Repo)│     │          │    │ Cache)│           │   │   │  │
         │  │ └──────┘     └──────────┘    └───────┘           │   │   │  │
         │  └───────────────────────────────────────────────────┘   │   │  │
         │                                                          │   │  │
         │  ┌───────────────────────────────────────────────────┐   │   │  │
         │  │       Integration Subnet (10.0.3.0/24)            │   │   │  │
         │  │                                                    │   │   │  │
         │  │  ┌─────────────┐   ┌──────────────┐              │   │   │  │
         │  │  │  Key Vault  │   │  Managed     │              │   │   │  │
         │  │  │  (Secrets,  │   │  Identity    │              │   │   │  │
         │  │  │   PATs)     │   │  (Auth)      │              │   │   │  │
         │  │  └─────────────┘   └──────────────┘              │   │   │  │
         │  └───────────────────────────────────────────────────┘   │   │  │
         └─────────────────────────────────────────────────────────┘   │  │
                                                                       │  │
┌──────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                  WEBHOOK INGESTION PIPELINE                      │   │
│   │                                                                  │   │
│   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │   │
│   │  │ Azure DevOps │   │ GitHub       │   │ Azure Monitor        │  │   │
│   │  │ Webhooks     │   │ Webhooks     │   │ (Incident Alerts)    │  │   │
│   │  │ (PR/Build)   │   │ (PR/Push)    │   │                      │  │   │
│   │  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘  │   │
│   │         │                  │                       │              │   │
│   │         └──────────────────┼───────────────────────┘              │   │
│   │                            ▼                                      │   │
│   │                 ┌─────────────────────┐                           │   │
│   │                 │  Service Bus Queue  │                           │   │
│   │                 │  (Event Routing)    │                           │   │
│   │                 └──────────┬──────────┘                           │   │
│   │                            │                                      │   │
│   │          ┌─────────────────┼─────────────────┐                    │   │
│   │          ▼                 ▼                  ▼                    │   │
│   │   ┌────────────┐   ┌────────────┐    ┌──────────────┐            │   │
│   │   │ Code Review│   │ PR Summary │    │ Incident     │            │   │
│   │   │ Function   │   │ Function   │    │ RCA Function │            │   │
│   │   └────────────┘   └────────────┘    └──────────────┘            │   │
│   │          │                 │                  │                    │   │
│   │          └─────────────────┼──────────────────┘                   │   │
│   │                            ▼                                      │   │
│   │                 ┌─────────────────────┐                           │   │
│   │                 │ Cosmos DB + AI      │                           │   │
│   │                 │ Search Indexing     │                           │   │
│   │                 └─────────────────────┘                           │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                               │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐              │
│  │ App Insights│  │Log Analytics│  │ Azure Monitor       │              │
│  │ (APM)       │  │ (Logs)      │  │ (Metrics/Alerts)    │              │
│  └─────────────┘  └─────────────┘  └─────────────────────┘              │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐              │
│  │ Prompt Flow │  │ Cost Mgmt  │  │ Defender for Cloud  │              │
│  │ Tracing     │  │ Dashboard   │  │ (Security)          │              │
│  └─────────────┘  └─────────────┘  └─────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CODE REVIEW FLOW                                     │
└─────────────────────────────────────────────────────────────────────────┘

    PR Created / Updated                                  Review Posted
         │                                                     ▲
         ▼                                                     │
┌───────────────┐                                     ┌───────────────┐
│ 1. Webhook    │                                     │ 8. Post       │
│ (DevOps/GH)   │                                     │ Review to PR  │
└───────┬───────┘                                     └───────┬───────┘
        │                                                      │
        ▼                                                      │
┌───────────────┐                                     ┌───────────────┐
│ 2. Service Bus│                                     │ 7. Format     │
│ Queue         │                                     │ Comments      │
└───────┬───────┘                                     └───────┬───────┘
        │                                                      │
        ▼                                                      │
┌───────────────┐                                     ┌───────────────┐
│ 3. Fetch Diff │─────────────────────────────────────│ 6. GPT-4o     │
│ & File Context│                                     │ Code Review   │
└───────┬───────┘                                     └───────┬───────┘
        │                                                      │
        ▼                                                      │
┌───────────────┐     ┌───────────────┐              ┌───────────────┐
│ 4. Embed Code │────►│ 5. Search     │─────────────►│ Past Reviews  │
│ Diff Chunks   │     │ Similar       │              │ & Patterns    │
│ (ada-002)     │     │ Patterns      │              │ Retrieved     │
└───────────────┘     └───────────────┘              └───────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                   INCIDENT RCA FLOW                                      │
└─────────────────────────────────────────────────────────────────────────┘

    Incident Alert Fired
         │
         ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Azure      │────►│ 2. Service Bus│────►│ 3. RCA        │
│ Monitor Alert │     │ Queue         │     │ Function      │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                          ┌──────────────────────────┼──────────────────┐
                          │                          │                  │
                          ▼                          ▼                  ▼
                   ┌────────────┐          ┌────────────────┐  ┌─────────────┐
                   │ 4a. Fetch  │          │ 4b. Search     │  │ 4c. Fetch   │
                   │ Recent     │          │ Past Incidents │  │ Deployment  │
                   │ Deployments│          │ (AI Search)    │  │ Logs        │
                   └─────┬──────┘          └───────┬────────┘  └──────┬──────┘
                         │                         │                  │
                         └─────────────────────────┼──────────────────┘
                                                   │
                                                   ▼
                                           ┌───────────────┐
                                           │ 5. Correlate  │
                                           │ & Analyze     │
                                           │ (GPT-4o)      │
                                           └───────┬───────┘
                                                   │
                                                   ▼
                                           ┌───────────────┐
                                           │ 6. Generate   │
                                           │ RCA Report    │
                                           │ & Remediation │
                                           └───────┬───────┘
                                                   │
                                     ┌─────────────┼─────────────┐
                                     ▼             ▼             ▼
                              ┌──────────┐  ┌──────────┐  ┌──────────┐
                              │ Cosmos DB│  │ Teams    │  │ DevOps   │
                              │ (Store)  │  │ Notify   │  │ Work Item│
                              └──────────┘  └──────────┘  └──────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                DEPLOYMENT RISK SCORING FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

    Deployment Triggered
         │
         ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 1. Pipeline   │────►│ 2. Gather     │────►│ 3. Risk       │
│ Webhook       │     │ Change Set    │     │ Scoring       │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
                         ┌───────────────────────────┤
                         ▼                           ▼
                  ┌─────────────┐            ┌─────────────────┐
                  │ 4. GPT-4o   │            │ 5. Historical   │
                  │ Analyze     │            │ Failure Match   │
                  │ Complexity  │            │ (AI Search)     │
                  └──────┬──────┘            └────────┬────────┘
                         │                            │
                         └────────────┬───────────────┘
                                      ▼
                              ┌───────────────┐
                              │ 6. Risk Score │
                              │ (Low/Med/High)│
                              │ + Gate/Notify │
                              └───────────────┘
```

---

## Component Details

### 1. Frontend Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| DevOps Dashboard | React + Next.js + TypeScript | Unified review, RCA, and risk dashboard |
| VS Code Extension | TypeScript (VS Code API) | In-editor code review suggestions |
| Teams Integration | Bot Framework | Incident alerts and RCA notifications |

### 2. API Gateway Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Front Door | WAF Policy, SSL termination | Global load balancing, DDoS protection |
| APIM | OAuth2/JWT, Rate limits (100 RPM) | API management, authentication, caching |
| Azure SignalR | Serverless mode | Real-time review status and alert streaming |

### 3. Application Layer

| Component | Runtime | Purpose |
|-----------|---------|---------|
| Code Review Engine | Azure Functions (Python 3.11) | AI-driven code review comment generation |
| PR Summarizer | Azure Functions (Python 3.11) | Automated pull request summary creation |
| RCA Analyzer | Azure Functions (Python 3.11) | Incident correlation and root cause analysis |
| Risk Scorer | Azure Functions (Python 3.11) | Deployment risk assessment and gate control |
| Webhook Processor | Azure Functions (Node.js 20) | Azure DevOps and GitHub webhook ingestion |

### 4. AI/ML Layer

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| Azure OpenAI | GPT-4o (gpt-4o-2024-08-06) | Code review, RCA generation, risk analysis |
| Azure OpenAI | text-embedding-ada-002 | Vector embeddings for code diffs and incidents |
| Azure AI Search | Semantic ranker + vector index | Historical incident and code pattern retrieval |
| Prompt Library | Custom prompt templates | Specialized prompts for review, RCA, and risk |

### 5. Data Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Azure Cosmos DB | Serverless, multi-partition | Reviews, incidents, RCA reports, risk scores |
| Azure Blob Storage | Hot tier, versioning enabled | Code diffs, deployment logs, artifacts |
| Azure AI Search | S1 tier, 3 replicas | Vector index for incidents, reviews, runbooks |
| Azure Redis Cache | P1 Premium, 6GB | PR diff cache, review result cache, rate state |
| Azure Service Bus | Standard tier, 3 queues | Event-driven webhook routing and processing |

### 6. Security Layer

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| Key Vault | RBAC, soft delete, purge protect | API keys, PATs, connection strings |
| Private Link | All PaaS services | Network isolation for data plane traffic |
| Managed Identity | System-assigned | Zero-credential service-to-service auth |
| Entra ID | OAuth2/OIDC, Conditional Access | User authentication, SSO for dashboard |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PERIMETER SECURITY                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Azure Front │  │ WAF Policy  │  │ DDoS        │  │ Geo-filtering   │  │
│ │ Door        │  │ (OWASP 3.2) │  │ Protection  │  │ (Allowed Regions│  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: IDENTITY & ACCESS                                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Entra ID    │  │ Conditional │  │ MFA         │  │ PIM (Just-in-   │  │
│ │ (SSO)       │  │ Access      │  │ Enforcement │  │ time access)    │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: NETWORK SECURITY                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ VNET        │  │ NSG Rules   │  │ Private     │  │ Service         │  │
│ │ Isolation   │  │ (Least Priv)│  │ Endpoints   │  │ Endpoints       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DATA SECURITY                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Encryption  │  │ Key Vault   │  │ PAT Rotation│  │ Code Content    │  │
│ │ at Rest/    │  │ (CMK)       │  │ (Automated) │  │ Redaction       │  │
│ │ Transit     │  │             │  │             │  │ (PII/Secrets)   │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION SECURITY                                            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Managed     │  │ RBAC        │  │ API         │  │ Content         │  │
│ │ Identity    │  │ (Fine-grain)│  │ Throttling  │  │ Filtering       │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: MONITORING & COMPLIANCE                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│ │ Defender    │  │ Sentinel    │  │ Audit Logs  │  │ Compliance      │  │
│ │ for Cloud   │  │ (SIEM)      │  │ (Activity)  │  │ Manager         │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```yaml
# Multi-Environment Deployment Strategy

environments:
  development:
    subscription: dev-subscription
    resource_group: rg-code-review-copilot-dev
    location: eastus
    sku_tier: basic
    features:
      - code_review
      - pr_summary

  staging:
    subscription: staging-subscription
    resource_group: rg-code-review-copilot-stg
    location: eastus
    sku_tier: standard
    features:
      - code_review
      - pr_summary
      - incident_rca
      - deployment_risk

  production:
    subscription: prod-subscription
    resource_group: rg-code-review-copilot-prod
    location: eastus
    secondary_location: westus2  # DR
    sku_tier: premium
    features:
      - code_review
      - pr_summary
      - incident_rca
      - deployment_risk
      - risk_gate_enforcement

deployment_strategy:
  type: blue-green
  rollback_enabled: true
  canary_percentage: 10
  health_check_path: /health
  webhook_validation: true

ci_cd_pipeline:
  source: Azure DevOps Pipelines
  stages:
    - build_and_test
    - security_scan
    - deploy_staging
    - integration_tests
    - deploy_production
  approval_gates:
    production: manual + risk_score_check
```

---

## Cost Estimation (Production)

| Service | SKU | Monthly Cost (USD) |
|---------|-----|-------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$3,000-7,000 |
| Azure AI Search | S1 (3 replicas) | ~$750 |
| Azure Functions | Premium EP1 (x2) | ~$400 |
| Cosmos DB | Serverless | ~$150 |
| Blob Storage | Hot (500GB) | ~$12 |
| Key Vault | Standard | ~$5 |
| APIM | Standard | ~$150 |
| Redis Cache | P1 Premium | ~$250 |
| Service Bus | Standard | ~$10 |
| Application Insights | Pay-as-you-go | ~$100 |
| Log Analytics | Pay-as-you-go | ~$75 |
| Azure Monitor | Alerts + Metrics | ~$30 |
| Front Door | Standard | ~$35 |
| SignalR Service | Standard (1 unit) | ~$50 |
| **Total Estimated** | | **~$5,000-9,000** |

---

## Interview Talking Points

### Architecture Decisions

1. **Why event-driven webhook processing with Service Bus?**
   - Decouples webhook ingestion from AI processing to handle burst traffic
   - Dead-letter queues ensure no PR or incident event is lost
   - Separate queues for code review, PR summary, and RCA allow independent scaling
   - At-least-once delivery guarantees reliable processing

2. **Why Azure AI Search for historical context?**
   - Semantic search over past incidents surfaces similar root causes instantly
   - Vector embeddings on code diffs enable pattern matching for recurring bugs
   - Hybrid search combines keyword matching (error codes) with semantic understanding
   - Indexed runbooks provide automated remediation suggestions

3. **Why GPT-4o over fine-tuned models for code review?**
   - GPT-4o has strong zero-shot code understanding across all languages
   - RAG approach with historical reviews provides org-specific context without retraining
   - Prompt engineering with few-shot examples customizes review style per team
   - Lower operational overhead compared to maintaining fine-tuned model versions

4. **How does deployment risk scoring work?**
   - Analyzes change set size, file complexity, and blast radius of modified services
   - Correlates with historical deployment failures from AI Search index
   - Factors in time-of-day, day-of-week, and change freeze windows
   - Outputs a Low/Medium/High score that can gate production deployments

5. **Security Considerations**
   - All services behind Private Link with no public endpoints exposed
   - Managed Identity eliminates credential management for service-to-service auth
   - PATs for Azure DevOps and GitHub stored in Key Vault with automated rotation
   - Code content is never persisted in plain text; diffs are encrypted at rest
   - Content filtering in Azure OpenAI prevents prompt injection in code comments

### Scalability Considerations

- Service Bus partitioned queues handle webhook burst traffic (1000+ events/minute)
- Azure Functions Premium plan for VNET integration and zero cold starts
- Redis Cache reduces redundant AI Search and OpenAI API calls for duplicate PRs
- Cosmos DB auto-scaling with partition keys on repository ID for even distribution
- AI Search replicas scale read throughput for concurrent pattern lookups
- Async processing model allows the system to queue reviews during peak hours

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Internal Engineering Tools)
- **Visibility:** Internal (Engineering) — software development teams and engineering leadership
- **Project Score:** 8.0 / 10 (Elevated)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Network Isolation | Dedicated VNet, NSG rules, no public endpoints |
| Network | Private Link | OpenAI, DevOps, Storage via private endpoints |
| Identity | Managed Identity | Zero-secret architecture for all services |
| Identity | RBAC | Repository-level access control aligned with DevOps |
| Data | SAST/DAST Integration | Static and dynamic application security testing |
| Data | Secrets Detection | Pre-commit hooks and pipeline scanning for secrets |
| Data | Source Code Protection | Encryption at rest for all code repositories |
| Data | Key Vault | API keys, service credentials, signing certificates |
| Application | Prompt Injection Guard | Input validation to prevent prompt injection in reviews |
| Application | OSS License Scanner | Automated open-source license compatibility checking |
| Monitoring | DevOps Audit | Code review decisions and AI suggestions logged |
| Monitoring | Sentinel | Security event monitoring for development environment |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| SDLC Governance | Enforced | Secure development lifecycle policies and gates |
| OSS License Compliance | Automated | License compatibility checking (GPL, MIT, Apache, etc.) |
| Code Quality Standards | Defined | Automated enforcement of coding standards and patterns |
| IP Protection | Enforced | Proprietary code never sent to external AI without approval |
| Change Management | ITIL-aligned | Change advisory board integration for critical repos |
| AI Ethics | Policy-based | AI suggestions reviewed for bias and security implications |

### Regulatory Applicability
- **SOC 2 Type II:** Development environment security controls
- **ISO 27001:** Information security for development assets
- **OWASP SAMM:** Software Assurance Maturity Model alignment
- **NIST SSDF:** Secure Software Development Framework
- **Export Controls:** Encryption and controlled technology in code
