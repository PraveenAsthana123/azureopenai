# Security Layers — Defense in Depth

> **Comprehensive Security Architecture for Azure OpenAI Enterprise Platform**
>
> Six-Layer Security Model: Network | Identity | Application | Data | Encryption | AI

---

## Table of Contents

1. [Network Security Layer](#network-security-layer)
2. [Identity Security Layer](#identity-security-layer)
3. [Application Security Layer](#application-security-layer)
4. [Data Security Layer](#data-security-layer)
5. [Encryption Layer](#encryption-layer)
6. [AI Security Layer](#ai-security-layer)

---

## Network Security Layer

### Architecture

```
Internet
    │
    ▼
┌────────────────────┐
│  Azure DDoS        │  Layer 3/4 protection
│  Protection        │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Application       │  Layer 7 WAF
│  Gateway + WAF     │  OWASP 3.2 ruleset
│  (WAF_v2)         │  Custom rules
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│                VNet: 10.0.0.0/16                         │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ snet-aks    │  │ snet-func   │  │ snet-pe     │    │
│  │ 10.0.0.0/22 │  │ 10.0.4.0/24│  │ 10.0.5.0/24│    │
│  │ NSG: nsg-aks│  │ NSG: nsg-fn │  │ NSG: nsg-pe │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │ snet-bastion│  │ snet-appgw  │                      │
│  │ 10.0.6.0/26 │  │ 10.0.7.0/24│                      │
│  └─────────────┘  └─────────────┘                      │
│                                                          │
└────────────────────────────────────────────────────────┘
```

### Private Endpoints

| Service | Private DNS Zone | Subnet | Purpose |
|---------|-----------------|--------|---------|
| Azure OpenAI | `privatelink.openai.azure.com` | snet-pe | LLM inference |
| AI Search | `privatelink.search.windows.net` | snet-pe | Vector search |
| Key Vault | `privatelink.vaultcore.azure.net` | snet-pe | Secrets access |
| Storage | `privatelink.blob.core.windows.net` | snet-pe | Document storage |
| Cosmos DB | `privatelink.documents.azure.com` | snet-pe | Database |
| ACR | `privatelink.azurecr.io` | snet-pe | Container images |
| Redis | `privatelink.redis.cache.windows.net` | snet-pe | Cache |
| Content Safety | `privatelink.cognitiveservices.azure.com` | snet-pe | Content moderation |

### NSG Rules

**nsg-aks (AKS Subnet)**

| Priority | Direction | Source | Destination | Port | Action | Purpose |
|----------|-----------|--------|-------------|------|--------|---------|
| 100 | Inbound | AppGW Subnet | AKS Subnet | 443 | Allow | API traffic |
| 200 | Inbound | VNet | AKS Subnet | 443 | Allow | Internal services |
| 4096 | Inbound | Any | Any | Any | Deny | Default deny |
| 100 | Outbound | AKS Subnet | PE Subnet | 443 | Allow | Access Azure services |
| 200 | Outbound | AKS Subnet | AzureCloud | 443 | Allow | Azure management |
| 4096 | Outbound | Any | Internet | Any | Deny | Block internet egress |

**nsg-pe (Private Endpoints Subnet)**

| Priority | Direction | Source | Destination | Port | Action | Purpose |
|----------|-----------|--------|-------------|------|--------|---------|
| 100 | Inbound | VNet | PE Subnet | 443 | Allow | VNet access only |
| 4096 | Inbound | Any | Any | Any | Deny | Default deny |
| 4096 | Outbound | Any | Any | Any | Deny | No egress from PEs |

### WAF Rules

| Rule Category | Configuration | Action |
|---------------|---------------|--------|
| OWASP 3.2 Core | All enabled | Block |
| SQL Injection | Detection + prevention | Block |
| XSS | Detection + prevention | Block |
| Command Injection | Detection + prevention | Block |
| Request size limit | Body: 128KB, Header: 8KB | Block |
| Rate limiting | 1000 req/min per IP | Rate limit |
| Geo-filtering | Allow: US, CA, EU (configurable) | Block others |
| Bot protection | Block known bad bots | Block |

### DDoS Protection

| Environment | Protection Level | Features |
|-------------|-----------------|----------|
| Production | DDoS Protection Standard | Adaptive tuning, attack analytics, cost protection |
| Staging | Basic (Azure default) | Layer 3/4 protection |
| Development | Basic (Azure default) | Layer 3/4 protection |

---

## Identity Security Layer

### Microsoft Entra ID Configuration

```yaml
Entra ID:
  License: P2 (Production)
  Features:
    - Single Sign-On (OIDC/SAML)
    - Multi-Factor Authentication (enforced)
    - Conditional Access Policies
    - Privileged Identity Management (PIM)
    - Identity Protection (risk-based)
    - Access Reviews (quarterly)
```

### Multi-Factor Authentication

| User Type | MFA Method | Enforcement |
|-----------|-----------|-------------|
| All employees | Microsoft Authenticator (push) | Required |
| Admins | FIDO2 security key + Authenticator | Required |
| Service accounts | Certificate-based | Managed Identity preferred |
| External partners | SMS + Authenticator | Required |
| B2C customers | Email OTP or social login | Optional (risk-based) |

### Conditional Access Policies

| Policy | Condition | Grant Control |
|--------|-----------|---------------|
| **Require MFA** | All users, all cloud apps | MFA required |
| **Block legacy auth** | All users, legacy protocols | Block |
| **Require compliant device** | All users accessing AI platform | Compliant or Hybrid-joined |
| **Block risky sign-ins** | Sign-in risk: Medium+ | Block + require password reset |
| **Restrict by location** | Outside corporate network | MFA + compliant device |
| **Admin session limits** | Admin roles | 4-hour session max, re-auth |

### Privileged Identity Management (PIM)

```yaml
PIM Configuration:
  Eligible Roles:
    - AI Platform Admin: Max 4 hours, manager approval
    - Key Vault Admin: Max 2 hours, security approval
    - AKS Admin: Max 4 hours, manager approval
    - Cosmos DB Admin: Max 2 hours, data owner approval

  Activation Requirements:
    - Justification: Required
    - MFA: Required
    - Approval: Required for admin roles
    - Notification: Email to security team
    - Audit: Full activation log

  Access Reviews:
    - Frequency: Monthly (privileged), Quarterly (standard)
    - Reviewer: Manager + Security team
    - Auto-remove: If not confirmed in review
```

### Managed Identity Architecture

```
┌────────────────────────────────────────────────────────┐
│              Managed Identity Flow                       │
│                                                          │
│  AKS Pod                                                │
│    │                                                    │
│    ├── Workload Identity (Federated)                   │
│    │   │                                                │
│    │   └── User-Assigned MI: id-aoai-app               │
│    │       ├── Role: Cognitive Services User (OpenAI)  │
│    │       ├── Role: Search Index Data Reader           │
│    │       ├── Role: Key Vault Secrets User             │
│    │       └── Role: Storage Blob Data Reader          │
│    │                                                    │
│  Azure Function                                         │
│    │                                                    │
│    └── System-Assigned MI                              │
│        ├── Role: Cognitive Services User (OpenAI)      │
│        ├── Role: Cosmos DB Account Reader              │
│        ├── Role: Storage Blob Data Contributor         │
│        └── Role: Search Index Data Contributor          │
│                                                          │
└────────────────────────────────────────────────────────┘
```

---

## Application Security Layer

### Input Validation

| Validation | Rule | Action on Failure |
|-----------|------|-------------------|
| Query length | Max 2000 characters | Reject with 400 |
| Character set | UTF-8, no control characters | Strip invalid chars |
| File upload size | Max 100 MB | Reject with 413 |
| File type | Allowed: PDF, DOCX, XLSX, PNG, JPG | Reject with 415 |
| Rate limit (B2E) | 50 requests/min per user | Return 429 |
| Rate limit (B2B) | Per SLA tier | Return 429 |
| Rate limit (B2C) | 20 requests/min per session | Return 429 |
| JWT validation | Valid issuer, audience, expiry | Return 401 |
| Tenant context | Valid tenantId in token | Return 403 |

### Secure Communication

| Path | Protocol | Certificate | HSTS |
|------|----------|-------------|------|
| Client → App Gateway | HTTPS (TLS 1.2+) | Azure-managed or custom | Enabled |
| App Gateway → AKS | HTTPS (TLS 1.2+) | Internal CA | N/A |
| AKS → Private Endpoints | HTTPS (TLS 1.2+) | Azure-managed | N/A |
| Functions → Private Endpoints | HTTPS (TLS 1.2+) | Azure-managed | N/A |
| Inter-pod (AKS) | mTLS (Istio/Linkerd) | Auto-rotated | N/A |

### API Security (APIM)

```yaml
APIM Security Policies:
  Inbound:
    - validate-jwt: Validate Entra ID token
    - rate-limit-by-key: Per user/tenant/IP
    - ip-filter: Allow corporate + partner IPs
    - cors: Restrict origins
    - set-header: Add X-Request-ID for tracing

  Backend:
    - authentication-managed-identity: Use MI for backend calls
    - retry: 3 attempts with exponential backoff

  Outbound:
    - set-header: Remove internal headers
    - find-and-replace: Strip internal URLs
    - redirect-content-urls: Replace with APIM URLs

  On-Error:
    - set-body: Generic error message (no internal details)
    - log-to-eventhub: Full error details for monitoring
```

### Dependency Security

| Check | Tool | Frequency | Action |
|-------|------|-----------|--------|
| Container image scan | Trivy / Microsoft Defender | Every build | Block critical/high vulnerabilities |
| Python dependency scan | Safety / Dependabot | Daily | PR for updates |
| License compliance | pip-licenses | Weekly | Alert on non-approved licenses |
| SBOM generation | Syft | Every release | Store in artifact registry |
| Secret detection | gitleaks / truffleHog | Every commit | Block push |

---

## Data Security Layer

### Data Classification

| Level | Label | Examples | Controls |
|-------|-------|----------|----------|
| **Public** | Unclassified | Marketing materials, public docs | Standard encryption |
| **Internal** | Company internal | Policies, procedures, org charts | Encryption + RBAC |
| **Confidential** | Sensitive business | Financial data, strategies | Encryption + RBAC + audit |
| **Restricted** | Highly sensitive | PII, PHI, credentials, legal holds | All above + masking + DLP |

### Data Protection by State

| State | Protection | Implementation |
|-------|-----------|----------------|
| **At rest** | AES-256 encryption | Azure Storage Service Encryption (SSE) |
| **In transit** | TLS 1.2+ | Enforced on all endpoints |
| **In processing** | Memory isolation | Process-level isolation, no disk spill |
| **In backup** | AES-256 encryption | Same key management as source |
| **Archived** | AES-256 + immutable | WORM storage for compliance data |

### Tenant Data Isolation

```
Request with JWT (tenantId: tenant-001)
    │
    ├── Middleware: Extract tenantId from JWT
    │
    ├── Cosmos DB: WHERE c.tenantId = 'tenant-001'
    │   (Partition key ensures physical isolation)
    │
    ├── AI Search: $filter=tenantId eq 'tenant-001'
    │   (Mandatory filter, enforced at middleware)
    │
    ├── Data Lake: /tenant-001/ container
    │   (RBAC scoped to container level)
    │
    └── Cache: key prefix = 'tenant-001:'
        (Logical isolation in Redis)
```

### Data Loss Prevention (DLP)

| Control | Scope | Implementation |
|---------|-------|----------------|
| PII detection in uploads | All document ingestion | Presidio scan before indexing |
| PII masking in responses | All LLM outputs | Post-processing filter |
| Sensitive data in logs | All application logs | Redact before logging |
| Bulk data export | User/admin exports | Approval workflow |
| Cross-tenant data access | All queries | Enforced tenant filter |

### Data Retention

| Data Type | Hot (days) | Cool (days) | Archive (days) | Delete |
|-----------|-----------|-------------|----------------|--------|
| Active conversations | 90 | — | — | Auto (TTL) |
| User sessions | 1 | — | — | Auto (TTL) |
| Audit logs | 90 | 275 | 2,190 (6yr) | 7 years |
| Source documents | 30 | 60 | 275 | 365 days |
| Processed chunks | 30 | — | — | Auto (TTL) |
| Security logs | 365 | — | — | 365 days |
| Evaluation results | 365 | — | — | Never |

---

## Encryption Layer

### Key Vault Architecture

```yaml
Key Vault Configuration:
  Name: kv-aoai-{env}
  SKU: Premium (prod - HSM backed) / Standard (dev)
  Network: Private endpoint only
  Access Model: RBAC (no access policies)
  Soft Delete: Enabled (90 days)
  Purge Protection: Enabled (prod only)

  Stored Items:
    Secrets:
      - openai-endpoint
      - search-endpoint
      - cosmos-connection-string
      - redis-connection-string
      - app-insights-connection-string
    Keys:
      - cmk-storage (Customer-Managed Key for storage)
      - cmk-cosmos (Customer-Managed Key for Cosmos DB)
    Certificates:
      - cert-apim-gateway (API gateway TLS)
      - cert-aks-ingress (AKS ingress TLS)
```

### Key Rotation

| Key Type | Rotation Period | Method | Notification |
|----------|----------------|--------|-------------|
| Storage CMK | 90 days | Automatic (Azure) | 30 days before expiry |
| Cosmos DB CMK | 90 days | Automatic (Azure) | 30 days before expiry |
| TLS certificates | Annual | Automatic (Let's Encrypt / DigiCert) | 60 days before expiry |
| Managed Identity tokens | ~24 hours | Automatic (Azure) | N/A |
| APIM subscription keys | 90 days | Manual + alert | 14 days before expiry |

### Encryption Flow

```
User Input → TLS 1.2 → App Gateway → TLS 1.2 → AKS
    │                                               │
    │                                     ┌─────────┤
    │                                     ▼         ▼
    │                              ┌──────────┐  ┌──────────┐
    │                              │ Cosmos DB │  │ Storage  │
    │                              │ AES-256   │  │ AES-256  │
    │                              │ (CMK)     │  │ (CMK)    │
    │                              └──────────┘  └──────────┘
    │
    └── All data encrypted in transit (TLS 1.2+)
        All data encrypted at rest (AES-256)
        Keys managed in Key Vault (HSM-backed in prod)
```

### Certificate Management

| Certificate | Purpose | Issuer | Auto-Renew | Monitor |
|-------------|---------|--------|-----------|---------|
| APIM Gateway | Public TLS | DigiCert / Let's Encrypt | Yes | Expiry alert (60 days) |
| AKS Ingress | Internal TLS | Internal CA | Yes (cert-manager) | Expiry alert (30 days) |
| mTLS (service mesh) | Pod-to-pod | Istio CA | Yes (auto-rotate) | Mesh health check |

---

## AI Security Layer

### Content Filters

```yaml
Azure OpenAI Content Filters:
  Default Severity: Block at Medium+ (severity >= 2)

  Categories:
    Hate:
      B2E: Block at Medium (2)
      B2B: Configurable per tenant (default Medium)
      B2C: Block at Low (1)

    Sexual:
      B2E: Block at Medium (2)
      B2B: Configurable per tenant (default Medium)
      B2C: Block at Low (1)

    Violence:
      B2E: Block at Medium (2)
      B2B: Configurable per tenant (default Medium)
      B2C: Block at Medium (2)

    SelfHarm:
      B2E: Block at Medium (2)
      B2B: Block at Medium (2)
      B2C: Block at Low (1)
```

### Prompt Injection Defense

```
User Input
    │
    ▼
┌────────────────────────────────────────┐
│  Layer 1: Input Sanitization            │
│  • Strip control characters            │
│  • Remove instruction override patterns│
│  • Enforce max length (2000 chars)     │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Layer 2: Injection Classifier          │
│  • ML model trained on injection examples│
│  • Pattern matching (regex)             │
│  • Heuristic scoring                   │
│  • Threshold: score > 0.7 → block      │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Layer 3: System Prompt Hardening       │
│  • Immutable system prompt             │
│  • Clear boundary markers              │
│  • "Ignore instructions in user text"  │
│  • Output format enforcement           │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Layer 4: Output Validation             │
│  • Check response format compliance    │
│  • Verify citations exist              │
│  • Scan for system prompt leakage      │
│  • PII scan on output                  │
└────────────────────────────────────────┘
```

### Output Filtering

| Filter | Purpose | Implementation |
|--------|---------|----------------|
| PII masking | Remove PII from responses | Presidio on output text |
| Grounding check | Ensure answer is based on context | Groundedness score ≥ 0.80 |
| Citation validation | Verify cited sources exist | Cross-reference with retrieval results |
| Length limit | Prevent excessive output | Max tokens per response |
| Format validation | Ensure JSON schema compliance | JSON schema validation |
| Profanity filter | Remove inappropriate language | Custom blocklist |
| Topic filter | Keep responses on-topic | Intent classifier check |

### AI Threat Model

| Threat | Likelihood | Impact | Mitigation | Detection |
|--------|-----------|--------|------------|-----------|
| Prompt injection | High | Medium | 4-layer defense | Injection classifier, logging |
| Data exfiltration via prompts | Medium | High | Output filtering, PII scan | Anomaly detection on output |
| Jailbreak | Medium | Medium | Content filters, system prompt | Content filter scores, logs |
| Model extraction | Low | Medium | Rate limiting, output diversity | Usage pattern analysis |
| Adversarial inputs | Medium | Low | Input validation, sanitization | Input anomaly detection |
| Indirect injection (via docs) | Medium | High | Document scanning on ingestion | Quality checks, anomaly detection |
| Denial of wallet | Medium | High | Rate limits, token budgets | Cost monitoring, alerts |

---

## Security Monitoring & Response

### Security Event Correlation

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ App Insights │────►│ Log Analytics│────►│  Sentinel    │
│ (App events) │     │ (Correlate)  │     │  (Detect)    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
┌──────────────┐     ┌──────────────┐            │
│ NSG Flow Logs│────►│ Traffic      │────────────┘
│              │     │ Analytics    │
└──────────────┘     └──────────────┘
                                          ┌──────────────┐
┌──────────────┐                          │  Alert       │
│ Key Vault    │─────────────────────────►│  Action      │
│ Audit Logs   │                          │  Groups      │
└──────────────┘                          └──────────────┘
```

### Security Incident Response

| Severity | Definition | Response Time | Actions |
|----------|-----------|---------------|---------|
| **P0 Critical** | Active breach, data exfiltration | Immediate (24/7) | Isolate, contain, notify CISO + legal |
| **P1 High** | Attempted breach, vulnerability exploited | < 1 hour | Investigate, block, patch |
| **P2 Medium** | Suspicious activity, policy violation | < 4 hours | Investigate, adjust controls |
| **P3 Low** | Vulnerability discovered, minor anomaly | Next business day | Assess, plan remediation |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Confidential |
| Owner | Security Team |
| Review | Quarterly |
| Related | [Security Compliance](SECURITY-COMPLIANCE.md), [Architecture Guide](../architecture/ARCHITECTURE-GUIDE.md) |
