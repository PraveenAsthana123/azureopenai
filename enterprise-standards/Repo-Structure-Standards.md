# Repo Structure & Standards — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | Audit-Ready**

---

## Master Control Table

| # | Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Repo Type** | Avoid confusion | Classify repo | Service / Library / Monorepo / Infra | Repo classification record |
| 2 | **Golden Path Template** | Consistency & speed | Use standard scaffold | New repos must start from template | Template repo link |
| 3 | **Top-Level Layout** | Predictability | Standard folders | Common folders required | Repo tree |
| 4 | **Code Location** | Clean boundaries | Keep code under src/ | No "random" code in root | Structure check |
| 5 | **Tests Location** | Discoverability | Separate tests | tests/ mirrors src/ | Test layout |
| 6 | **Docs Location** | Knowledge retention | Central docs | docs/ required | Docs index |
| 7 | **Scripts & Tools** | Automation | Standard scripts folder | scripts/ for ops/dev | Script inventory |
| 8 | **Configuration** | Prevent misconfig | Central config folder | No env-specific logic in code | Config rules |
| 9 | **Environment Files** | Prevent secret leaks | Use .env.example only | .env never committed | Gitignore rules |
| 10 | **Dependency Management** | Reproducible builds | Pin dependencies | Lockfiles mandatory | lockfile |
| 11 | **Code Quality Gates** | Enforce standards | Pre-commit + CI | Lint/format required | CI logs |
| 12 | **Branching Standard** | Traceability | Standard branching model | No direct main commits | Git policy |
| 13 | **Commit Standard** | Clean history | Conventional commits | Required for releases | Commit lint logs |
| 14 | **PR Template** | Better reviews | PR template required | Links to ticket + tests | .github/PULL_REQUEST_TEMPLATE.md |
| 15 | **Issue Templates** | Better intake | Standard issue forms | Bug/feature templates | .github/ISSUE_TEMPLATE/ |
| 16 | **CODEOWNERS** | Clear ownership | Define owners | Required for approvals | CODEOWNERS file |
| 17 | **ADR Storage** | Preserve decisions | Store ADRs in repo | Versioned ADRs | docs/adr/ |
| 18 | **API Specs Storage** | Contract-first | Store OpenAPI/AsyncAPI | Spec is source of truth | docs/api/ |
| 19 | **Data Contracts Storage** | Prevent breaking changes | Store schemas/contracts | Versioned schemas | contracts/ |
| 20 | **Secrets Handling** | Prevent leaks | Vault references only | No secrets in repo | Secret scan reports |
| 21 | **Security Controls** | Reduce risk | Security scans in CI | Block critical issues | Scan reports |
| 22 | **Build & Release** | Reproducible releases | Build once deploy many | Semantic versioning | Release tags |
| 23 | **Observability Artifacts** | Operability | Keep telemetry docs | Dashboard/alert definitions | docs/observability/ |
| 24 | **Runbooks/Playbooks** | On-call readiness | Store runbooks near code | Must be updated with changes | docs/runbooks/ |
| 25 | **Change & Incident Records** | Audit trail | Link to incident/change | Traceability | Links in docs/ |
| 26 | **License & Compliance** | Legal safety | Include license & notices | OSS compliance | LICENSE/NOTICE |
| 27 | **Repo Health Automation** | Prevent drift | Automated checks | Fails on structure violations | Repo lint config |
| 28 | **Exception/Waiver Process** | Controlled flexibility | Time-bound waivers | No permanent waivers | Waiver log |

---

## Recommended Default Repo Tree

```
repo/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── CODEOWNERS
│
├── src/
│   └── <service_or_package>/
│       ├── __init__.py
│       ├── config/
│       ├── domain/
│       ├── adapters/
│       ├── api/
│       ├── jobs/
│       └── utils/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── api/              # OpenAPI / AsyncAPI
│   ├── data/             # ERD + contracts explanation
│   ├── observability/    # dashboards, alerts, SLOs
│   ├── runbooks/
│   └── security/
│
├── contracts/
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── asyncapi.yaml
│   └── data/
│       ├── schemas/
│       └── contracts/
│
├── infra/
│   ├── terraform/
│   ├── k8s/
│   ├── helm/
│   └── pipelines/
│
├── scripts/
│   ├── dev/
│   ├── ci/
│   └── ops/
│
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .gitignore
├── .editorconfig
├── pyproject.toml (or package.json)
├── ruff.toml / .pylintrc
├── mypy.ini
├── pytest.ini
│
└── security/
    └── threat-model.md
```

---

## Non-Negotiable Rules

| Rule | Rationale |
|------|-----------|
| No secrets in repo (ever) | Prevents credential exposure |
| Contract-first specs live in repo and are versioned | Single source of truth |
| CI enforces lint/test/security gates | Quality enforcement |
| Docs close to code (runbooks, ADRs, threat model) | Knowledge retention |
| CODEOWNERS required for protected files | Clear accountability |

---

## Common Repo Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| "docs in Confluence only" | Becomes stale, loses context |
| No CODEOWNERS | Nobody accountable for changes |
| No contracts | Integration breaks silently |
| No runbooks | Incidents become chaos |
| Infra scattered | Deployments drift |

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All repositories |
| Framework Alignment | CMMI L3, ISO 42001 |
