# Secure Coding Standard — Master Table

> **Tech Lead / Principal Engineer Reference | OWASP + NIST + CMMI L3 Aligned**
>
> Enforceable rules that prevent known vulnerabilities—especially in AI systems.

---

## Master Control Table

| # | Security Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|---------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Security Requirements** | Make security explicit | Define security NFRs | CIA + abuse cases defined | Security NFR section |
| 2 | **Threat Modeling Linkage** | Build from known threats | Map code areas to threat model | STRIDE/OWASP coverage | Threat→control map |
| 3 | **Authentication (AuthN)** | Prevent account takeover | Use standard auth (OIDC/OAuth2) | No custom auth | Auth design + config |
| 4 | **Authorization (AuthZ)** | Enforce least privilege | RBAC/ABAC + policy checks | Deny by default | Access control policy |
| 5 | **Secrets Management** | Prevent credential leaks | Use Vault/KMS + env injection | No secrets in repo | Secrets scan reports |
| 6 | **Input Validation** | Stop injection attacks | Validate at boundaries | Allow-list validation | Validation rules |
| 7 | **Output Encoding** | Prevent XSS/injection | Encode outputs by context | No raw HTML injection | Encoding guidelines |
| 8 | **Injection Protection** | Prevent SQL/Command/Template injection | Use parameterized APIs | No string-concat SQL/commands | SAST evidence |
| 9 | **Deserialization Safety** | Prevent RCE | Avoid unsafe deserialization | No pickle/untrusted deserialize | Code scan results |
| 10 | **Error Handling** | Avoid info leaks | Standard error responses | No stack traces to clients | Error contract |
| 11 | **Logging & PII Redaction** | Prevent data exposure | Structured logs + redaction | No PII/PHI in logs | Log policy + tests |
| 12 | **Cryptography Standard** | Prevent weak crypto | Use approved libs only | No custom crypto | Crypto policy |
| 13 | **Transport Security** | Protect data in transit | TLS everywhere | Enforce HTTPS/mTLS internally | TLS config |
| 14 | **Data at Rest Protection** | Protect stored data | Encryption at rest | Key rotation | Storage encryption proof |
| 15 | **Dependency Management (SCA)** | Reduce supply-chain risk | Pin + scan dependencies | No critical CVEs | SCA reports |
| 16 | **Secure Defaults** | Prevent misconfig | Secure config baseline | Default deny, secure headers | Config baseline |
| 17 | **Rate Limiting & Abuse Prevention** | Prevent DoS & cost spikes | Apply quotas/throttles | Per-user/per-tenant limits | Rate limit policy |
| 18 | **File/Upload Handling** | Prevent malware attacks | Validate size/type | Virus scan if needed | Upload policy |
| 19 | **SSRF Protection** | Stop internal probing | Block internal IP ranges | Allow-list outbound calls | SSRF controls |
| 20 | **Concurrency & Race Conditions** | Prevent subtle security bugs | Use safe primitives | No shared mutable globals | Review checklist |
| 21 | **CI Security Gates** | Make security real | SAST/SCA/secret scan | Block merges on critical/high | CI logs |
| 22 | **Security Testing (DAST)** | Catch runtime issues | Scan staging env | Risk-based requirement | DAST reports |
| 23 | **Secure Code Review Checklist** | Ensure consistent review | Review against checklist | Security sign-off for high risk | PR review logs |
| 24 | **Vulnerability Response** | Fix quickly | Triage → patch → verify | SLAs by severity | Vuln tickets |
| 25 | **Exception / Waiver Process** | Controlled risk acceptance | Waiver with expiry | No permanent waivers | Waiver register |

---

## GenAI / RAG Secure Coding Addendum

| Area | Mandatory Rules |
|------|-----------------|
| **Prompt Injection Defense** | Never trust user input; isolate system instructions; treat retrieved text as untrusted |
| **RAG Data Leakage** | Enforce doc-level ACLs at retrieval time; redact sensitive content before prompt |
| **Tool/Agent Safety** | Explicit allow-list of tools/actions; require human approval for high-impact actions |
| **Output Handling** | Treat model output as untrusted; sanitize before rendering or executing |
| **Model & Prompt Versioning** | Every request logs model/prompt version (no content) for auditability |
| **Rate Limits / Cost Controls** | Token caps, per-tenant quotas, abuse detection |

---

## Python-Specific Secure Coding Rules

| Rule | Rationale |
|------|-----------|
| Never use `eval()` / `exec()` on untrusted input | Code injection |
| Avoid unsafe deserialization (e.g., `pickle`) for untrusted data | RCE risk |
| Use parameterized DB queries (ORM or prepared statements) | SQL injection |
| Use `subprocess.run([...], shell=False)` and validate args | Command injection |
| Centralize input validation with schemas (e.g., Pydantic) | Consistent validation |

---

## OWASP Top 10 Coverage

| OWASP Risk | Control |
|------------|---------|
| A01: Broken Access Control | AuthZ checks, default deny |
| A02: Cryptographic Failures | Approved crypto, TLS |
| A03: Injection | Parameterized queries, input validation |
| A04: Insecure Design | Threat modeling |
| A05: Security Misconfiguration | Secure defaults, IaC scans |
| A06: Vulnerable Components | SCA, dependency pinning |
| A07: Auth Failures | Standard auth, MFA |
| A08: Software Integrity | Signed artifacts, SCA |
| A09: Logging Failures | Structured logging, no PII |
| A10: SSRF | Allow-list outbound, block internal |

---

## Security Review Checklist

```markdown
Input Handling:
- [ ] All user input validated
- [ ] Allow-list validation used
- [ ] File uploads restricted

Authentication:
- [ ] Standard auth (OIDC/OAuth2)
- [ ] No hardcoded credentials
- [ ] Session management secure

Authorization:
- [ ] Default deny
- [ ] RBAC/ABAC enforced
- [ ] Privilege escalation prevented

Data Protection:
- [ ] PII identified and protected
- [ ] Encryption at rest/transit
- [ ] No sensitive data in logs

Dependencies:
- [ ] Dependencies pinned
- [ ] No critical CVEs
- [ ] SBOM generated
```

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Secrets in `.env` committed "just for testing" | Credential exposure |
| No rate limiting | GenAI cost explosions + DoS |
| Treating retrieved docs as trusted in RAG | Data leakage |
| Logging sensitive payloads "for debugging" | PII exposure |
| Security gates run but don't block merges | Vulnerabilities ship |

---

## Executive Summary

> **Secure coding is a set of enforceable rules that prevent known vulnerabilities by controlling inputs, secrets, dependencies, and privileged actions—especially in AI systems.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Security Standard |
| Applicable To | All code |
| Framework Alignment | OWASP, NIST, CMMI L3, ISO 42001 |
