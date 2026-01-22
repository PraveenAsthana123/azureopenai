# CI/CD Pipeline Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Ready**
>
> Ensures pipelines are secure, repeatable, observable, and governed.

---

## Master Control Table

| # | Pipeline Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|--------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Pipeline Architecture** | Ensure scalability | Define pipeline patterns | Multi-stage, environment-aware | Pipeline architecture doc |
| 2 | **Source Control Integration** | Enable traceability | Trigger on PR/merge | Branch protection enforced | SCM config |
| 3 | **Branch Strategy** | Control flow | GitFlow / Trunk-based | Protected main branch | Branch policy |
| 4 | **Build Stage** | Create artifacts | Compile, lint, build | Reproducible builds | Build logs |
| 5 | **Artifact Management** | Enable reuse | Store in registry | Immutable artifacts | Artifact registry |
| 6 | **Versioning Strategy** | Enable traceability | Semantic versioning | Auto-versioning | Version manifest |
| 7 | **Unit Test Stage** | Catch bugs early | Run tests on every build | Coverage thresholds | Test reports |
| 8 | **Static Analysis (SAST)** | Find code issues | Scan code for vulns | Block on critical/high | SAST reports |
| 9 | **Dependency Scan (SCA)** | Reduce supply chain risk | Scan dependencies | No critical CVEs | SCA reports |
| 10 | **Secret Scanning** | Prevent credential leaks | Scan for secrets | Block on detection | Secret scan logs |
| 11 | **Container Scanning** | Secure images | Scan container images | No critical vulns | Container scan reports |
| 12 | **Integration Test Stage** | Validate interactions | Run integration tests | Environment isolation | Integration reports |
| 13 | **Performance Test Stage** | Prevent regressions | Run perf tests | Threshold enforcement | Perf reports |
| 14 | **Staging Deployment** | Validate before prod | Deploy to staging | Automated deployment | Deployment logs |
| 15 | **Smoke Tests** | Validate deployment | Run post-deploy checks | Must pass | Smoke test results |
| 16 | **Approval Gates** | Control promotion | Manual/auto gates | Required for prod | Approval records |
| 17 | **Production Deployment** | Release safely | Deploy with strategy | Canary/Blue-Green | Prod deploy logs |
| 18 | **Rollback Automation** | Enable recovery | Auto-rollback on failure | Tested rollback | Rollback logs |
| 19 | **Pipeline Security** | Protect CI/CD | Secure pipeline configs | Least privilege | Security config |
| 20 | **Environment Variables** | Manage config | Externalize config | No secrets in code | Env config |
| 21 | **Caching Strategy** | Optimize speed | Cache dependencies | Cache invalidation | Cache config |
| 22 | **Parallelization** | Reduce time | Run stages in parallel | Resource limits | Pipeline metrics |
| 23 | **Notifications** | Keep teams informed | Notify on status | Failure alerts | Notification config |
| 24 | **Audit & Logging** | Enable compliance | Log all actions | Immutable logs | Audit trail |
| 25 | **Pipeline Metrics** | Improve process | Track DORA metrics | Dashboard required | Metrics dashboard |

---

## Pipeline Stages

| Stage | Purpose | Quality Gate |
|-------|---------|--------------|
| **Source** | Code checkout | Branch protection |
| **Build** | Compile & package | Build success |
| **Test** | Unit tests | Coverage > threshold |
| **Scan** | Security analysis | No critical findings |
| **Package** | Create artifact | Artifact signed |
| **Deploy-Dev** | Development deploy | Health checks pass |
| **Deploy-Staging** | Pre-prod validation | Smoke tests pass |
| **Approve** | Gate control | Required approvals |
| **Deploy-Prod** | Production release | Canary success |

---

## AI / GenAI Pipeline Add-Ons

| Requirement | Implementation |
|-------------|----------------|
| Model validation in pipeline | Eval suite execution |
| Prompt testing automation | Prompt regression tests |
| RAG index validation | Index quality checks |
| Token cost estimation | Cost analysis step |
| Bias/safety checks | AI safety scans |
| Model/prompt versioning | Version tagging |

---

## Security Gates (Non-Negotiable)

| Gate | Threshold | Action on Fail |
|------|-----------|----------------|
| SAST findings | No critical/high | Block merge |
| SCA vulnerabilities | No critical CVEs | Block merge |
| Secret detection | Any secret found | Block merge |
| Container vulnerabilities | No critical | Block deploy |
| Unit test coverage | > 80% | Block merge |
| Integration tests | All pass | Block deploy |

---

## DORA Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Deployment Frequency** | How often code deploys | Daily+ |
| **Lead Time** | Commit to production | < 1 day |
| **Change Failure Rate** | Deploys causing failures | < 15% |
| **MTTR** | Mean time to recover | < 1 hour |

---

## Pipeline Configuration Example

```yaml
# Azure DevOps Pipeline Structure
stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - task: Build
          - task: UnitTests
          - task: CodeCoverage

  - stage: SecurityScan
    jobs:
      - job: SAST
      - job: SCA
      - job: SecretScan

  - stage: DeployStaging
    dependsOn: SecurityScan
    condition: succeeded()

  - stage: IntegrationTests
    dependsOn: DeployStaging

  - stage: DeployProd
    dependsOn: IntegrationTests
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
```

---

## Branch Protection Rules

| Rule | Requirement |
|------|-------------|
| Require PR reviews | Minimum 2 approvers |
| Require status checks | All CI checks pass |
| Require signed commits | GPG signing enabled |
| No force push | Prevent history rewrite |
| No direct commits | All changes via PR |

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Security scans run but don't block | Vulnerabilities ship |
| No artifact immutability | Environment drift |
| Manual production deploys | Human error, inconsistency |
| No rollback automation | Slow recovery |
| Pipeline secrets in code | Credential exposure |

---

## Pipeline Checklist

```markdown
Pipeline Setup:
- [ ] Multi-stage pipeline defined
- [ ] Branch protection enabled
- [ ] Security scans integrated
- [ ] Artifact versioning configured
- [ ] Environment isolation verified

Quality Gates:
- [ ] Unit test coverage threshold set
- [ ] SAST blocking enabled
- [ ] SCA blocking enabled
- [ ] Secret scanning enabled
- [ ] Approval gates configured

Deployment:
- [ ] Staging deployment automated
- [ ] Smoke tests configured
- [ ] Production deployment strategy defined
- [ ] Rollback automation tested
- [ ] Notifications configured
```

---

## Executive Summary

> **A CI/CD Pipeline Standard ensures every code change flows through consistent, secure, and observable automation—enabling fast, safe, and reliable delivery.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All pipelines |
| Framework Alignment | CMMI L3, ISO 42001, DORA |
