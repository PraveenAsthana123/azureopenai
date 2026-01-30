# Tech Stack & Azure Services Reference

> **Complete Technology Stack and Service Inventory for Azure OpenAI Enterprise Platform**

---

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Azure Services Inventory](#azure-services-inventory)
3. [Historical Database Design](#historical-database-design)
4. [Job Schedules](#job-schedules)
5. [PII Detection Libraries](#pii-detection-libraries)

---

## Technology Stack

### Core Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **LLM** | Azure OpenAI (GPT-4o) | 2024-08-06 | Answer generation, complex reasoning |
| **LLM (Light)** | Azure OpenAI (GPT-4o-mini) | 2024-07-18 | Query rewriting, summarization |
| **Embeddings** | text-embedding-3-large | 2024-01-25 | Vector embeddings (3072 dimensions) |
| **Search** | Azure AI Search | 2024-07-01 | Hybrid search (vector + BM25 + semantic) |
| **OCR/Parse** | Azure Document Intelligence | 4.0 | PDF, image, form extraction |
| **Container Orchestration** | AKS (Kubernetes) | 1.29+ | Microservices hosting |
| **Serverless** | Azure Functions | 4.x (Python 3.11) | Event-driven processing |
| **API Gateway** | Azure API Management | v2 | Rate limiting, JWT validation, routing |
| **Cache** | Azure Cache for Redis | 6.x | Query/retrieval/embedding cache |
| **Database** | Cosmos DB (NoSQL API) | Latest | Conversations, sessions, audit |
| **Object Storage** | Azure Data Lake Gen2 | Latest | Documents, embeddings, logs |
| **Secrets** | Azure Key Vault | Premium | Secrets, keys, certificates |
| **Identity** | Microsoft Entra ID | Latest | SSO, MFA, Conditional Access |
| **IaC** | Terraform | 1.6+ | Infrastructure as Code |
| **CI/CD** | GitHub Actions | Latest | Build, test, deploy pipelines |
| **Monitoring** | Application Insights | Latest | APM, distributed tracing |
| **Logging** | Azure Log Analytics | Latest | Centralized log aggregation |
| **Container Registry** | Azure Container Registry | Premium | Docker image storage |

### Application Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Backend API** | Python | 3.11 | Core application logic |
| **Web Framework** | FastAPI | 0.104+ | REST API endpoints |
| **AI SDK** | LangChain | 0.1+ | LLM orchestration framework |
| **Azure SDK** | azure-identity | 1.15+ | Managed Identity auth |
| **OpenAI SDK** | openai (Python) | 1.12+ | Azure OpenAI integration |
| **Search SDK** | azure-search-documents | 11.4+ | AI Search integration |
| **Cosmos SDK** | azure-cosmos | 4.5+ | Cosmos DB operations |
| **PII Detection** | Presidio | 2.2+ | PII recognition and anonymization |
| **Content Safety** | azure-ai-contentsafety | 1.0+ | Content moderation |
| **Testing** | pytest | 7.x | Unit and integration testing |
| **Linting** | ruff | 0.1+ | Code quality |
| **Containerization** | Docker | 24+ | Application packaging |
| **Helm** | Helm | 3.x | Kubernetes package management |

### Frontend Stack (B2C/B2E)

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Chat UI** | React | 18+ | Customer/employee chat interface |
| **Bot Framework** | Copilot Studio | Latest | Teams integration (B2E) |
| **Auth (B2C)** | Entra External ID | Latest | Customer authentication |
| **Auth (B2E)** | Entra ID | Latest | Employee SSO |

---

## Azure Services Inventory

### AI & Cognitive Services

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 1 | **Azure OpenAI** | S0 | GPT-4o, GPT-4o-mini, Embeddings | Pay-per-token | Private Endpoint |
| 2 | **Azure AI Search** | Basic (dev) / Standard S1 (prod) | Hybrid vector + keyword search | Per search unit | Private Endpoint |
| 3 | **Azure Document Intelligence** | S0 | OCR, layout analysis, form extraction | Per page processed | Private Endpoint |
| 4 | **Azure Content Safety** | S0 | Content moderation (hate, violence, etc.) | Per API call | Private Endpoint |

### Compute

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 5 | **Azure Kubernetes Service (AKS)** | Standard (Private) | API services, RAG pipeline | Per node-hour | Private Cluster |
| 6 | **Azure Functions** | Elastic Premium EP1 (prod) / Consumption (dev) | Event-driven ingestion, scheduled jobs | Per execution + duration | VNet Integrated |
| 7 | **Azure Container Registry** | Premium (prod) / Basic (dev) | Docker image storage | Per storage + build | Private Endpoint |

### Data & Storage

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 8 | **Azure Data Lake Gen2** | StorageV2 (Hot/Cool/Archive) | Documents, embeddings, audit logs | Per GB + transactions | Private Endpoint |
| 9 | **Azure Cosmos DB** | Serverless (dev) / Autoscale (prod) | Conversations, sessions, metadata | Per RU/s + storage | Private Endpoint |
| 10 | **Azure Cache for Redis** | Basic C1 (dev) / Premium P1 (prod) | Query cache, retrieval cache | Per instance | Private Endpoint |

### Networking

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 11 | **Virtual Network** | Standard | Network isolation (10.0.0.0/16) | Free (included) | — |
| 12 | **Network Security Groups** | Standard | Subnet-level firewall rules | Free (included) | — |
| 13 | **Private DNS Zones** | Standard | Private endpoint name resolution | Per zone + queries | — |
| 14 | **Azure Bastion** | Standard (prod only) | Secure VM access (no public IP) | Per hour | Dedicated subnet |
| 15 | **Application Gateway + WAF** | WAF_v2 | Web application firewall, SSL termination | Per hour + capacity | Dedicated subnet |
| 16 | **Azure DDoS Protection** | Standard (prod) / Basic (all) | DDoS mitigation | Per month (Standard) | — |
| 17 | **Azure API Management** | Developer (dev) / Standard (prod) | API gateway, rate limiting, JWT validation | Per unit | VNet Integrated |

### Security & Identity

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 18 | **Azure Key Vault** | Standard (dev) / Premium (prod) | Secrets, keys, certificates | Per operation | Private Endpoint |
| 19 | **Microsoft Entra ID** | P2 (prod) / P1 (dev) | SSO, MFA, Conditional Access, PIM | Per user/month | Cloud |
| 20 | **Microsoft Defender for Cloud** | Standard | Security posture, vulnerability scanning | Per resource | Cloud |

### Monitoring & Observability

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 21 | **Application Insights** | Standard | APM, distributed tracing, custom metrics | Per GB ingested | Cloud |
| 22 | **Log Analytics Workspace** | Per-GB | Centralized log aggregation, KQL queries | Per GB ingested | Cloud |
| 23 | **Azure Monitor** | Standard | Alerts, dashboards, action groups | Per alert rule | Cloud |
| 24 | **Microsoft Sentinel** | Pay-per-GB (prod only) | SIEM, threat detection | Per GB analyzed | Cloud |

### Governance & Compliance

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 25 | **Azure Policy** | Built-in | Enforce security and compliance rules | Free | Cloud |
| 26 | **Azure Resource Manager** | Standard | Resource tagging, RBAC | Free | Cloud |
| 27 | **Azure Cost Management** | Standard | Budget alerts, cost analysis | Free | Cloud |

### DevOps & Automation

| # | Service | SKU | Purpose | Cost Tier | Network |
|---|---------|-----|---------|-----------|---------|
| 28 | **GitHub Actions** | Enterprise | CI/CD pipelines | Per minute | Cloud |
| 29 | **Terraform Cloud** | Free / Team | State management, plan/apply | Per workspace | Cloud |

---

## Historical Database Design

### Cosmos DB — Container Design

| Container | Partition Key | RU/s (Prod) | TTL | Purpose |
|-----------|---------------|-------------|-----|---------|
| `conversations` | `/userId` | Autoscale 400–4000 | 90 days | Chat history |
| `sessions` | `/sessionId` | Autoscale 400–2000 | 24 hours | Active sessions |
| `evaluations` | `/evaluationId` | 400 (fixed) | None | Eval results |
| `feedback` | `/queryId` | 400 (fixed) | None | User feedback |
| `audit-events` | `/tenantId` | Autoscale 400–4000 | 7 years | Audit trail |
| `tenant-config` | `/tenantId` | 400 (fixed) | None | Tenant settings |
| `model-metrics` | `/modelId` | 400 (fixed) | 365 days | Model performance |

### Conversations Schema

```json
{
  "id": "conv-uuid-001",
  "userId": "user@company.com",
  "tenantId": "tenant-001",
  "sessionId": "session-uuid",
  "startedAt": "2025-01-15T10:00:00Z",
  "lastActiveAt": "2025-01-15T10:30:00Z",
  "messageCount": 5,
  "messages": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "What is the AML policy?",
      "timestamp": "2025-01-15T10:00:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "Based on the AML policy document...",
      "citations": [{"docId": "doc123", "page": 5, "score": 0.94}],
      "confidence": 0.92,
      "model": "gpt-4o",
      "tokensUsed": {"input": 1200, "output": 450},
      "latencyMs": 2340,
      "timestamp": "2025-01-15T10:00:03Z"
    }
  ],
  "metadata": {
    "department": "Compliance",
    "intent": "procedural",
    "feedbackScore": 5
  },
  "ttl": 7776000
}
```

### Audit Events Schema

```json
{
  "id": "audit-uuid-001",
  "tenantId": "tenant-001",
  "eventType": "query",
  "userId": "user@company.com",
  "timestamp": "2025-01-15T10:00:00Z",
  "details": {
    "queryHash": "sha256:abc123...",
    "documentsAccessed": ["doc123", "doc456"],
    "model": "gpt-4o",
    "tokensUsed": 1650,
    "responseGenerated": true,
    "confidenceScore": 0.92,
    "contentFilterTriggered": false,
    "piiDetected": false
  },
  "clientInfo": {
    "ipHash": "sha256:def456...",
    "userAgent": "Teams/1.6",
    "channel": "B2E"
  },
  "ttl": 220752000
}
```

### Indexing Policies

```json
{
  "indexingPolicy": {
    "automatic": true,
    "indexingMode": "consistent",
    "includedPaths": [
      {"path": "/userId/?"},
      {"path": "/tenantId/?"},
      {"path": "/eventType/?"},
      {"path": "/timestamp/?"}
    ],
    "excludedPaths": [
      {"path": "/messages/*"},
      {"path": "/details/*"}
    ],
    "compositeIndexes": [
      [
        {"path": "/tenantId", "order": "ascending"},
        {"path": "/timestamp", "order": "descending"}
      ]
    ]
  }
}
```

---

## Job Schedules

### Scheduled Jobs

| Job | Schedule | Runtime | Trigger | Purpose |
|-----|----------|---------|---------|---------|
| **Index Refresh** | Every 15 min | Azure Function (Timer) | Cron: `0 */15 * * * *` | Re-index new/changed documents |
| **Cache Invalidation** | Every 5 min | Azure Function (Timer) | Cron: `0 */5 * * * *` | Clear stale cache entries |
| **Embedding Refresh** | Daily 2:00 AM | Azure Function (Durable) | Cron: `0 0 2 * * *` | Regenerate embeddings for updated docs |
| **Evaluation Pipeline** | Daily 6:00 AM | AKS CronJob | Cron: `0 6 * * *` | Run automated eval on golden dataset |
| **Cleanup: Expired Sessions** | Hourly | Azure Function (Timer) | Cron: `0 0 * * * *` | Delete expired session data |
| **Cleanup: Old Conversations** | Daily 3:00 AM | Azure Function (Timer) | Cron: `0 0 3 * * *` | Enforce TTL on conversations |
| **Backup: Cosmos DB** | Every 4 hours | Azure (built-in) | Continuous backup | Point-in-time restore capability |
| **Backup: AI Search Index** | Daily 1:00 AM | Azure Function (Durable) | Cron: `0 0 1 * * *` | Export index to Data Lake |
| **Security Scan** | Daily 4:00 AM | GitHub Actions | Cron: `0 4 * * *` | Container image + dependency scan |
| **Cost Report** | Weekly Monday 8:00 AM | Azure Function (Timer) | Cron: `0 0 8 * * 1` | Generate and email cost report |
| **Access Review Reminder** | Monthly 1st | Azure Function (Timer) | Cron: `0 0 9 1 * *` | Remind managers to review access |
| **Certificate Renewal Check** | Weekly | Azure Function (Timer) | Cron: `0 0 10 * * 0` | Alert on expiring certificates |
| **Log Archival** | Daily 5:00 AM | Azure Function (Timer) | Cron: `0 0 5 * * *` | Move old logs to cool/archive storage |
| **Drift Detection** | Weekly Sunday 6:00 AM | AKS CronJob | Cron: `0 6 * * 0` | Detect data/model drift |

### Job Monitoring

| Job | SLA | Alert If | Escalation |
|-----|-----|----------|------------|
| Index Refresh | < 5 min | Duration > 10 min or failure | DevOps team |
| Evaluation Pipeline | < 30 min | Metrics below threshold | AI team |
| Backup | < 15 min | Failure | DevOps team (P1) |
| Security Scan | < 20 min | Critical vulnerability found | Security team (P0) |

---

## PII Detection Libraries

### Detection Stack

| Library | Purpose | Capabilities | Integration |
|---------|---------|-------------|-------------|
| **Microsoft Presidio** | Primary PII engine | Named entity recognition, pattern matching, context-aware | Python library in RAG pipeline |
| **Azure Content Safety** | Content moderation | Hate, sexual, violence, self-harm detection | Azure API call |
| **spaCy NER** | Named entity extraction | Person, org, location, date extraction | Presidio backend |
| **Custom Regex Patterns** | Domain-specific PII | SSN, credit card, employee ID, account numbers | Presidio custom recognizer |

### Presidio Configuration

```python
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# Initialize with spaCy NER model
analyzer = AnalyzerEngine()

# Custom recognizers for domain-specific PII
ssn_recognizer = PatternRecognizer(
    supported_entity="US_SSN",
    patterns=[
        Pattern("SSN", r"\b\d{3}-\d{2}-\d{4}\b", 0.85),
        Pattern("SSN_NO_DASH", r"\b\d{9}\b", 0.5)
    ]
)

employee_id_recognizer = PatternRecognizer(
    supported_entity="EMPLOYEE_ID",
    patterns=[
        Pattern("EMP_ID", r"\bEMP-\d{6}\b", 0.95),
        Pattern("EMP_ID_ALT", r"\b[A-Z]{2}\d{6}\b", 0.6)
    ]
)

account_recognizer = PatternRecognizer(
    supported_entity="ACCOUNT_NUMBER",
    patterns=[
        Pattern("ACCT", r"\b\d{10,12}\b", 0.4),
        Pattern("ACCT_DASH", r"\b\d{3}-\d{7}\b", 0.7)
    ]
)
```

### PII Entity Types

| Entity | Detection Method | Confidence | Action |
|--------|-----------------|-----------|--------|
| **Person Name** | spaCy NER | 0.85+ | Mask: `[PERSON]` |
| **Email** | Regex + context | 0.95+ | Mask: `j***@company.com` |
| **Phone** | Regex + context | 0.90+ | Mask: `***-***-1234` |
| **SSN** | Regex | 0.85+ | Mask: `***-**-****` |
| **Credit Card** | Regex + Luhn check | 0.95+ | Mask: `****-****-****-1234` |
| **Employee ID** | Custom regex | 0.95+ | Mask: `EMP-******` |
| **Account Number** | Custom regex + context | 0.70+ | Mask: `**********` |
| **Address** | spaCy NER | 0.75+ | Mask: `[ADDRESS]` |
| **Date of Birth** | Regex + context | 0.80+ | Mask: `[DOB]` |
| **IP Address** | Regex | 0.90+ | Mask: `***.***.***.***` |
| **Passport** | Regex + context | 0.80+ | Mask: `[PASSPORT]` |
| **Medical Record** | Custom regex | 0.85+ | Mask: `[MRN]` |

### PII Detection Pipeline

```
Input Text
    │
    ▼
┌──────────────────┐
│ 1. Regex Scan    │  Fast pattern matching (SSN, CC, phone)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. spaCy NER     │  Named entity recognition (names, orgs)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Presidio      │  Context-aware analysis (combines regex + NER)
│    Analyzer      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Custom Rules  │  Domain-specific patterns (employee ID, etc.)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Presidio      │  Apply masking/redaction per entity type
│    Anonymizer    │
└──────────────────┘
         │
         ▼
    Cleaned Text
```

### Content Safety Configuration

```yaml
Azure Content Safety:
  Endpoint: Private Endpoint
  Authentication: Managed Identity

  Text Analysis:
    Categories:
      - Hate: Block at severity >= 2 (Medium)
      - Sexual: Block at severity >= 2 (Medium)
      - Violence: Block at severity >= 2 (Medium)
      - SelfHarm: Block at severity >= 2 (Medium)

  Custom Blocklists:
    - competitor-names
    - internal-project-codenames
    - restricted-topics

  Integration Points:
    - Pre-LLM: Scan user input
    - Post-LLM: Scan model output
    - Ingestion: Scan documents before indexing
```

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal |
| Owner | Platform Team |
| Review | Quarterly |
| Related | [Architecture Guide](../architecture/ARCHITECTURE-GUIDE.md), [Security Compliance](../security/SECURITY-COMPLIANCE.md) |
