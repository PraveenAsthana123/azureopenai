# Multi-Region Disaster Recovery AI Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-00A67E?logo=openai&logoColor=white)
![Front Door](https://img.shields.io/badge/Azure%20Front%20Door-Global%20LB-blue)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-Multi--Region-purple)
![Terraform](https://img.shields.io/badge/Terraform-IaC-623CE4?logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

A multi-region disaster recovery architecture for enterprise AI/ML platforms ensuring high availability across Azure regions (East US primary, West US 2 secondary). The platform provides automated failover orchestrated by Azure Monitor and Automation Runbooks, geo-replicated data across Cosmos DB (active-active), RA-GRS Blob Storage, and geo-replicated Redis Cache. Azure OpenAI GPT-4o generates automated DR status reports with executive summaries, timelines, impact assessments, and recovery recommendations after every failover event. The architecture targets an overall RTO of less than 5 minutes and RPO of less than 1 minute.

## Architecture

```
                   Global Layer
                   +------------------+
                   | Azure Front Door |
                   | (WAF, SSL, CDN,  |
                   |  Health Probes)  |
                   +--------+---------+
                            |
                   +--------+---------+
                   | Traffic Manager  |
                   | (Priority/       |
                   |  Performance)    |
                   +--------+---------+
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
  PRIMARY REGION (East US)         SECONDARY REGION (West US 2)
  Priority: 1                      Priority: 2
  +-------------------------+      +-------------------------+
  | Compute:                |      | Compute (Standby):      |
  | AKS, Functions,         |      | AKS, Functions,         |
  | App Service, Containers |      | App Service, Containers |
  +-------------------------+      +-------------------------+
  | AI Services:            |      | AI Services (Failover): |
  | Azure OpenAI (GPT-4o)  |<---->| Azure OpenAI (GPT-4o)  |
  | AI Search (Primary)    |<---->| AI Search (Secondary)  |
  | Azure ML Endpoint      |<---->| Azure ML Endpoint      |
  +-------------------------+      +-------------------------+
  | Data Layer:             |      | Data Layer:             |
  | Cosmos DB (Multi-Write) |<---->| Cosmos DB (Multi-Write)|
  | Storage (RA-GRS)       |----->| Storage (Read Only)    |
  | Redis (Geo-Replicated) |<---->| Redis (Geo-Replicated) |
  +-------------------------+      +-------------------------+

                   DR Orchestration
                   +---------------------------+
                   | Azure Monitor (Health)    |
                   | Automation (Runbooks)     |
                   | Azure OpenAI (DR Reports) |
                   +---------------------------+
```

## Azure Services Used

| Service | DR Strategy | Purpose |
|---------|-------------|---------|
| Azure Front Door | Active-Active | Global load balancing with WAF, SSL, health probes |
| Azure Traffic Manager | Priority Routing | Regional failover with performance-based routing |
| Azure Cosmos DB | Multi-Region Write | Zero-RPO active-active database replication |
| Azure Blob Storage (RA-GRS) | Async Replication | Geo-redundant storage with read-only secondary |
| Azure AI Search | Geo-Replicas | Index replication for search availability |
| Azure OpenAI (GPT-4o) | Multi-Region Deploy | Stateless AI service with multi-region deployment |
| Azure ML Endpoints | Multi-Region Deploy | Same model version deployed across regions |
| Azure Redis Cache | Geo-Replication | Active geo-replication for cache HA |
| Azure Monitor | N/A | Health monitoring, alerting, diagnostics |
| Azure Automation | N/A | Failover and failback runbooks |
| AKS | Multi-Region | Container orchestration with cross-region standby |
| Azure Functions Premium | Multi-Region | Serverless compute with warm standby |
| Azure Key Vault | Per-Region | Per-region key vaults with geo-replication |

## Prerequisites

- Azure Subscription with Contributor access across two regions
- Azure OpenAI resource deployed in both East US and West US 2
- Cosmos DB account with multi-region writes enabled
- Azure Front Door Premium tier
- Terraform >= 1.5
- Azure CLI >= 2.50
- Azure Automation account
- Azure Monitor with Log Analytics workspace

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd azurecloud/project-14-multi-region-dr

# Configure Terraform variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your subscription, regions, and resource naming
```

### 2. Deploy Infrastructure

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Verify Multi-Region Setup

```bash
# Check Front Door health
az network front-door probe list --resource-group <rg-name> --name <fd-name>

# Verify Cosmos DB regions
az cosmosdb show --name <cosmos-name> --resource-group <rg-name> \
  --query "readLocations[].locationName"

# Check Traffic Manager endpoints
az network traffic-manager endpoint list \
  --profile-name <tm-name> --resource-group <rg-name>
```

### 4. Run DR Drill

```bash
# Trigger failover simulation via Automation Runbook
az automation runbook start --name "DR-Failover-Drill" \
  --resource-group <rg-name> --automation-account-name <account-name>
```

## Testing

```bash
cd tests

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -v -k "test_failover"       # Failover automation tests
pytest -v -k "test_replication"    # Data replication validation tests
pytest -v -k "test_health"         # Health probe and monitoring tests
pytest -v -k "test_dr_report"      # GenAI DR report generation tests
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID with consistent role assignments replicated across both regions
- **Authorization**: RBAC policies synchronized across primary and secondary regions
- **RBAC**: Tier-based failover approval: automated for Tier-1, approval-based for lower tiers
- **Managed Identity**: Zero-secret architecture replicated across regions for all services
- **Network Isolation**: Multi-region peered VNets with geo-redundant NSG rules; all services via Private Link in each region; geo-fencing restricts traffic to approved geographies

### Encryption

- **Data at Rest**: AES-256 encryption for all data stores in both regions; geo-redundant storage (GRS/GZRS) maintains encryption at secondary
- **Data in Transit**: TLS 1.3 enforced for cross-region data replication and all service communications
- **Key Management**: Per-region Azure Key Vault instances with geo-replication; failover key rotation procedures

### Monitoring

- **Application Insights**: Cross-region APM with unified monitoring across primary and secondary deployments
- **Log Analytics**: Centralized logging aggregating both regions for unified observability
- **Alerts**: Azure Monitor health probes with 3-consecutive-failure trigger; alerts for service degradation, replication lag, and failover events
- **Dashboards**: Unified operations dashboard showing regional health status, replication sync status, RTO/RPO metrics, and failover history

### Visualization

- **Grafana / Azure Monitor Dashboards**: Multi-region health status visualization with real-time replication lag indicators
- **DR Status Reports**: GenAI-generated markdown reports with executive summary, timeline, service status, data integrity assessment, impact analysis, and recovery recommendations
- **Cost Management**: Regional cost comparison dashboards for DR infrastructure optimization

### Tracking

- **Request Tracing**: Cross-region correlation IDs maintained through Front Door, Traffic Manager, and backend services
- **Failover Audit Trail**: Every failover event logged with trigger time, reason, actions taken, and duration in Log Analytics
- **DR Runbook Audit**: Automation runbook executions tracked with start/end times, step results, and outcomes
- **Replication Monitoring**: Continuous tracking of Cosmos DB sync status, Blob Storage replication lag, and Redis geo-replication health

### Accuracy

- **Health Probes**: Front Door and Traffic Manager health probes at 30-second intervals; 3 consecutive failures trigger failover evaluation
- **RPO/RTO Targets**: Cosmos DB RPO 0 (active-active), Blob Storage RPO < 15 min, Redis RPO < 1 sec; overall RTO < 5 minutes
- **DR Drills**: Quarterly failover drills with documented results; Azure Chaos Studio for chaos engineering validation
- **Failover Success Rate**: Target 99.9% automated failover success rate

### Explainability

- GenAI DR reports include 7 structured sections: executive summary, timeline of events, service status, data integrity assessment, impact analysis, recommended next steps, and estimated recovery timeline
- Failover sequences are documented step-by-step: Traffic Manager update, Cosmos DB promotion, DNS TTL update, compute warmup, AI Search verification, ML endpoint testing, Redis enable, monitoring update
- Replication strategy table clearly states RPO, RTO, and replication method for each service

### Responsibility

- **Automated vs Manual Failover**: Critical severity triggers automatic failover; lower severity requires human approval
- **Data Sovereignty**: Regional data residency maintained during failover; geo-fencing prevents data from crossing approved boundaries
- **Cost Optimization**: Secondary compute scaled down until failover to minimize costs; consumption-based services preferred
- **Post-Mortem**: ITIL-aligned major incident process with mandatory post-mortem requirements for every failover event

### Interpretability

- DR metrics dashboard provides real-time visibility into RTO, RPO, mean time to detect (< 30s), and mean time to recover (< 5 min)
- Service status table shows replication strategy, current sync state, and health for each component
- GenAI reports translate technical failover data into plain-English executive summaries

### Portability

- **Infrastructure as Code**: Full Terraform configuration with multi-region resources (main.tf, variables.tf, output.tf, terraform.tfvars)
- **Containerization**: AKS workloads containerized for consistent deployment across regions
- **Multi-Cloud Considerations**: DR patterns (active-active, active-passive, geo-replication) applicable to AWS/GCP equivalents
- **CI/CD**: Azure DevOps pipelines for synchronized multi-region deployments with health verification gates

## Project Structure

```
project-14-multi-region-dr/
|-- docs/
|   |-- ARCHITECTURE.md
|-- infra/
|-- src/
|-- tests/
|-- main.tf
|-- variables.tf
|-- output.tf
|-- terraform.tfvars
|-- README.md
```

## API Reference

| Component | Endpoint / Runbook | Description |
|-----------|-------------------|-------------|
| Front Door | Global endpoint | WAF-protected global load balancer with auto-failover |
| Traffic Manager | Priority routing | Regional endpoint failover based on health probes |
| Automation | `DR-Failover-Drill` | Automated failover simulation runbook |
| Automation | `DR-Failover-Execute` | Production failover execution runbook |
| Automation | `DR-Failback-Execute` | Failback to primary region runbook |
| Azure OpenAI | DR Report Generator | GPT-4o generates post-failover status reports |
| Azure Monitor | Health Probes | Continuous health monitoring with alert rules |

## License

This project is licensed under the MIT License.
