# Access Control / RBAC Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 + ISO 42001 + NIST 800-53 Aligned**
>
> Least-privilege by design, zero-trust aligned, and audit-ready.

---

## Master Control Table

| # | Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Scope & Asset Coverage** | Eliminate blind spots | Identify all protected resources | Apps, APIs, data, AI tools, infra | Access scope inventory |
| 2 | **Identity Source of Truth** | Prevent identity sprawl | Central IdP integration | SSO via OIDC/SAML only | IdP config |
| 3 | **Authentication (AuthN)** | Verify user/service identity | MFA + strong auth | MFA mandatory for privileged | Auth policy |
| 4 | **Authorization Model** | Enforce consistent decisions | Choose RBAC/ABAC | Default deny | AuthZ design |
| 5 | **Role Definition** | Reduce complexity | Define standard roles | No ad-hoc roles | Role catalog |
| 6 | **Role Granularity** | Avoid over-privilege | Separate read/write/admin | Least privilege | Role matrix |
| 7 | **Permission Mapping** | Make access explicit | Map roles → permissions | No implicit access | Permission matrix |
| 8 | **Service-to-Service Access** | Secure internal calls | Managed identities / mTLS | No shared secrets | Service identity config |
| 9 | **Environment Segregation** | Reduce blast radius | Separate roles per env | Prod ≠ non-prod access | Env access map |
| 10 | **Multi-Tenant Isolation** | Prevent cross-tenant leaks | Tenant-aware authZ | Tenant_id enforced | Tenant tests |
| 11 | **Privileged Access Management (PAM)** | Control high-risk access | Just-in-time (JIT) access | Time-bound elevation | PAM logs |
| 12 | **API Authorization** | Protect interfaces | Scope-based access | Token scopes enforced | OpenAPI security |
| 13 | **Data Access Control** | Protect sensitive data | Row/column-level security | PII minimized | Data access policy |
| 14 | **AI / Tool Access Control** | Prevent AI abuse | Allow-list tools/actions | Human-in-loop for high risk | AI access policy |
| 15 | **Secrets & Key Access** | Prevent credential misuse | Vault-based access | Role-scoped secrets | Vault audit logs |
| 16 | **Change Management** | Prevent access drift | Approved role changes | No direct grants | Change records |
| 17 | **Access Reviews (Recertification)** | Remove stale access | Periodic reviews | Quarterly minimum | Review reports |
| 18 | **Logging & Audit Trails** | Enable forensics | Log all access decisions | Immutable logs | Audit trails |
| 19 | **Monitoring & Alerting** | Detect abuse early | Alert on anomalies | Real-time alerts | SIEM rules |
| 20 | **Break-Glass Access** | Ensure recovery | Controlled emergency access | Logged & reviewed | Break-glass SOP |
| 21 | **Revocation & Offboarding** | Prevent orphan access | Automated de-provisioning | Immediate revocation | Offboarding logs |
| 22 | **Third-Party / Vendor Access** | Reduce external risk | Least-privilege + expiry | Time-boxed access | Vendor access register |
| 23 | **Testing & Validation** | Prevent misconfig | AuthZ tests | Deny tests mandatory | Test results |
| 24 | **Exception / Risk Acceptance** | Controlled deviation | Time-bound waivers | No permanent exceptions | Waiver register |
| 25 | **Governance & Ownership** | Sustain discipline | Assign role owners | RACI defined | RACI matrix |

---

## RBAC Design Rules (Non-Negotiable)

| Rule | Rationale |
|------|-----------|
| Default deny | Access is granted explicitly |
| Least privilege | Minimum permissions required |
| Separation of duties | Dev ≠ Deploy ≠ Admin |
| No shared accounts | Ever |
| Time-bound elevation | For privileged roles |
| All decisions logged | Allow + Deny |

---

## Typical Role Model

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Viewer** | Read-only access | Dashboards, reports |
| **User** | Standard operations | Day-to-day work |
| **Operator** | Operational actions | Restart, scale |
| **Admin** | Configuration changes | Settings, config |
| **Security Admin** | IAM & security settings | Access management |
| **Auditor** | Read access to logs & configs | Compliance review |

---

## AI / GenAI-Specific Access Controls

| Control | Description |
|---------|-------------|
| Separate roles for prompt edit, model deploy, evaluation, cost admin | Role granularity |
| Tool/agent access explicitly allow-listed | Prevent unauthorized actions |
| Human approval for actions affecting data, money, or users | HITL enforcement |
| Per-tenant quotas tied to roles | Cost control |
| Access to RAG sources enforced at retrieval time | Data isolation |

---

## Environment Access Matrix

| Role | Dev | Staging | Prod |
|------|-----|---------|------|
| Developer | Full | Read | None |
| DevOps | Full | Full | Deploy only |
| SRE | Read | Read | Operate |
| Admin | Full | Full | JIT only |
| Auditor | Read | Read | Read |

---

## Access Review Process

```
Quarterly Review Cycle
        ↓
Role Owner generates access report
        ↓
Manager reviews & certifies
        ↓
Stale access revoked
        ↓
Exceptions documented (time-bound)
        ↓
Audit evidence retained
```

---

## Break-Glass Procedure

| Step | Action |
|------|--------|
| 1 | Declare emergency (incident ticket) |
| 2 | Request break-glass access |
| 3 | Receive time-bound credentials |
| 4 | Perform emergency actions |
| 5 | Actions logged automatically |
| 6 | Post-incident review required |
| 7 | Access auto-revoked after window |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Too many roles | No one understands access |
| Shared service accounts | No accountability |
| Permanent admin access | Over-privilege |
| No recertification | Stale access accumulates |
| AI tools with unrestricted permissions | Data leakage, abuse |

---

## Key Metrics (KPIs)

| Metric | Target |
|--------|--------|
| % users with MFA enabled | 100% |
| Orphan account count | 0 |
| Access review completion rate | 100% |
| JIT elevation usage | > 90% for admin |
| Break-glass events per quarter | < 5 |

---

## Executive Summary

> **Access Control defines who can do what, where, and for how long—using least privilege, explicit roles, and continuous verification.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Security Standard |
| Applicable To | All systems and users |
| Framework Alignment | CMMI L3, ISO 42001, NIST 800-53, OWASP, MITRE |
