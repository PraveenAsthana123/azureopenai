# Secrets & Key Management Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 + NIST + ISO 42001 Aligned**
>
> Ensures credentials are never stored, shared, logged, or trusted longer than necessary.

---

## Master Control Table

| # | Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Scope & Definition** | Eliminate ambiguity | Define what is a secret | API keys, tokens, certs, passwords | Secrets taxonomy |
| 2 | **Approved Secret Stores** | Centralize protection | Use managed vaults only | No local or custom stores | Vault/KMS inventory |
| 3 | **Secret Classification** | Apply correct controls | Classify by sensitivity | High/Med/Low | Classification matrix |
| 4 | **Creation & Provisioning** | Prevent weak secrets | Generate via secure tools | No manual secrets | Provisioning logs |
| 5 | **Key Management (KMS)** | Secure encryption keys | Use managed KMS/HSM | No hard-coded keys | KMS config |
| 6 | **Encryption Standards** | Prevent data compromise | Approved algorithms only | AES-256, RSA-2048+, ECC | Crypto policy |
| 7 | **Access Control (IAM)** | Enforce least privilege | RBAC/ABAC on secrets | No shared credentials | IAM policy |
| 8 | **Secret Injection** | Prevent leaks in code | Inject at runtime | No secrets in code/config | Runtime config |
| 9 | **Environment Separation** | Prevent cross-env leaks | Separate secrets per env | Dev/Test/Prod isolated | Env secret map |
| 10 | **Rotation Policy** | Limit blast radius | Automatic rotation | Rotation intervals defined | Rotation schedule |
| 11 | **Certificate Management** | Prevent cert expiry outages | Automate issuance/renewal | No manual certs | Cert lifecycle docs |
| 12 | **CI/CD Secret Handling** | Secure pipelines | Use pipeline secret stores | No secrets in logs | CI config |
| 13 | **Logging & Redaction** | Prevent exposure | Mask secrets everywhere | No plaintext secrets logged | Redaction rules |
| 14 | **Secrets in Containers** | Secure runtime | Use secrets mounts | No secrets baked in images | Container configs |
| 15 | **Secrets in IaC** | Prevent repo leaks | Reference secrets, don't store | No plaintext in IaC | IaC scan results |
| 16 | **Third-Party & Vendor Keys** | Reduce external risk | Isolate & monitor keys | Separate per vendor | Vendor key registry |
| 17 | **AI/GenAI Secrets** | Control AI access & cost | Secure LLM/API keys | Per-tenant quotas | AI key registry |
| 18 | **Revocation & Incident Response** | Fast containment | Immediate revoke on breach | Tested revocation | IR runbooks |
| 19 | **Monitoring & Alerting** | Detect misuse | Alert on access anomalies | Real-time alerts | SIEM rules |
| 20 | **Backup & Recovery** | Ensure availability | Secure backup of keys | Access-controlled backups | Backup records |
| 21 | **Compliance & Auditability** | Prove control | Log all secret access | Immutable audit logs | Audit trails |
| 22 | **Testing & Validation** | Prevent misconfig | Validate secret access | Fail fast on missing secrets | Test results |
| 23 | **Exception / Waiver Process** | Controlled risk | Time-bound waivers only | No permanent waivers | Waiver register |
| 24 | **Ownership & RACI** | Prevent orphaned secrets | Assign owners | Ownership mandatory | RACI matrix |
| 25 | **Periodic Review** | Reduce secret sprawl | Quarterly secret review | Unused secrets removed | Review reports |

---

## Non-Negotiable Rules (Hard Gates)

| Rule | Enforcement |
|------|-------------|
| No secrets in source code, configs, or IaC | Pre-commit hooks, CI scans |
| No shared credentials | RBAC enforcement |
| No manual secret rotation | Automated rotation |
| No secrets logged (ever) | Redaction rules |
| Secrets injected at runtime only | Runtime validation |
| Automatic rotation + audit logging | Vault configuration |

---

## AI / GenAI-Specific Add-Ons

| Requirement | Implementation |
|-------------|----------------|
| Separate API keys per environment & tenant | Key scoping |
| Token usage & cost quotas enforced | Rate limiting |
| Key scope limited to required models/endpoints | Least privilege |
| Immediate revocation on abuse detection | Automated response |
| Prompt/model version logged (not secret content) | Audit logging |

---

## Secret Classification Matrix

| Classification | Examples | Rotation | Access |
|----------------|----------|----------|--------|
| **High** | Prod DB passwords, signing keys | 30 days | Restricted |
| **Medium** | API keys, service tokens | 90 days | Role-based |
| **Low** | Dev/test credentials | 180 days | Team-based |

---

## Rotation Schedule

| Secret Type | Rotation Interval | Method |
|-------------|-------------------|--------|
| Database passwords | 30 days | Automated |
| API keys | 90 days | Automated |
| Certificates | 90 days before expiry | Automated |
| Service account keys | 90 days | Automated |
| Encryption keys | Annual | Key versioning |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| `.env` files committed "temporarily" | Credential exposure |
| Secrets passed via CLI args | Leak in process list |
| One API key shared across all services | Blast radius |
| No rotation → long-lived credentials | Extended exposure |
| CI logs leaking secrets | Public exposure |

---

## Secret Injection Patterns

### Good Pattern (Runtime Injection)
```yaml
# Kubernetes
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password

# Azure Functions
@Microsoft.KeyVault(SecretUri=https://kv.vault.azure.net/secrets/db-password)
```

### Bad Pattern (Hard-coded)
```python
# NEVER DO THIS
DB_PASSWORD = "supersecret123"
```

---

## Executive Summary

> **Secrets & Key Management is about ensuring credentials are never stored, shared, logged, or trusted longer than necessary—while remaining auditable and automatable.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Security Standard |
| Applicable To | All systems |
| Framework Alignment | CMMI L3, NIST, ISO 42001 |
