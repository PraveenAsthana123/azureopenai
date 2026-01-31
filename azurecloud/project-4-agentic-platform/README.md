# GenAI Agentic Workflow Automation Platform

![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoftazure&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-00A4EF?style=flat&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-0062AD?style=flat&logo=azurefunctions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise AI agent platform that enables autonomous multi-step task execution using Azure OpenAI GPT-4o function calling capabilities. The platform allows AI agents to interact with enterprise systems (HR, IT, Finance) through natural language requests -- performing workflows like leave submissions, password resets, IT ticket creation, account management, and expense reporting. The agent orchestrator follows the ReAct (Reason + Act) pattern with a maximum of 10 iterations per request and includes human-in-the-loop approval gates for sensitive actions.

## Architecture

```
User Interfaces (Teams / Slack / Web Portal / Mobile)
        |
   APIM Gateway (OAuth2/JWT, Rate Limiting)
        |
   Agent Orchestrator (Azure Functions)
        |
   GPT-4o with Function Calling
   (Intent Analysis -> Execution Plan -> Tool Loop)
        |
   +----+----+----+
   |         |         |
HR Agent   IT Agent   Finance Agent
   |         |         |
   +---------+---------+
   |
   Tool Execution Layer
   |    |    |    |
 Workday  ServiceNow  Graph API  Custom APIs
   |
   +----+----+
   |         |
Cosmos DB  Key Vault
(State/    (Secrets)
 Audit)
```

### Agent Tools (9 Functions)

| Category | Tool | Description |
|----------|------|-------------|
| **HR** | `submit_leave_request` | Submit PTO/leave request with date range and type |
| **HR** | `get_pto_balance` | Retrieve current vacation, sick, and personal day balances |
| **HR** | `lookup_hr_policy` | Search HR policies by topic and keywords |
| **IT** | `reset_password` | Reset password and send reset link via email or SMS |
| **IT** | `unlock_account` | Unlock a locked user account |
| **IT** | `create_it_ticket` | Create IT support ticket with category and priority |
| **IT** | `check_account_status` | Check if account is active, locked, or disabled |
| **Finance** | `submit_expense` | Submit expense report (requires approval) |
| **Finance** | `check_expense_status` | Check status of submitted expense reports |

## Azure Services Used

| Service | SKU / Tier | Purpose |
|---------|-----------|---------|
| Azure OpenAI | GPT-4o with function calling | Agent reasoning, tool selection, response generation |
| Azure Cosmos DB | Serverless | Workflow state, chat history, audit logs, user preferences |
| Azure Key Vault | Standard | Tool credentials, API keys, connection strings |
| Azure Functions | Premium EP1 (Python 3.11) | Agent orchestrator, API endpoints |
| Azure APIM | Standard | API gateway with OAuth2 auth and rate limiting |
| Azure Entra ID | P1 | User authentication with SSO and MFA |
| Application Insights | Pay-as-you-go | Telemetry, tracing, custom metrics |

## Prerequisites

- Azure subscription with Contributor access
- Azure CLI >= 2.50
- Terraform >= 1.5
- Python 3.11+
- Azure OpenAI resource with GPT-4o deployment (function calling enabled)

## Quick Start

### 1. Clone and configure

```bash
cd azurecloud/project-4-agentic-platform

# Copy environment template
cp .env.example .env
# Edit .env with your Azure resource endpoints
```

### 2. Deploy infrastructure

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Install dependencies and run locally

```bash
cd ../src
pip install -r requirements.txt

func start
```

### 4. Send an agent request

```bash
curl -X POST http://localhost:7071/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to take next Friday off for a doctor appointment",
    "user_context": {
      "email": "john.doe@company.com",
      "name": "John Doe",
      "department": "Engineering",
      "manager": "jane.smith@company.com"
    }
  }'
```

## Testing

```bash
# Run unit tests
cd tests
python -m pytest test_agent_orchestrator.py -v

# Run comprehensive integration tests
python -m pytest test_comprehensive.py -v

# Run all tests with coverage
python -m pytest --cov=src --cov-report=term-missing
```

## Cross-Cutting Concerns

### Security

- **Authentication**: Azure Entra ID with corporate SSO and MFA enforcement for all users
- **Authorization**: Function-level authorization per tool -- agents can only execute tools the user has permissions for; tool execution validated against Entra ID roles
- **Managed Identity**: System-assigned managed identity for all service-to-service auth; zero stored credentials
- **Network Isolation**: All backend services (Cosmos DB, Key Vault, OpenAI) accessed via Private Link endpoints
- **Approval Gates**: Human-in-the-loop approval required for high-risk actions (financial transactions, HR changes, admin operations)
- **Action Scoping**: Tools scoped to least-privilege -- read-only tools separated from write/mutating tools
- **Rate Limiting**: Per-user action limits and token budgets to prevent abuse

### Encryption

- **Data at Rest**: AES-256 encryption on Cosmos DB (workflow state, chat history, audit logs) and Key Vault
- **Data in Transit**: TLS 1.2+ enforced on all endpoints and inter-service communication
- **Key Management**: Azure Key Vault with RBAC for tool credentials, API keys, and connection strings

### Monitoring

- **Application Insights**: Full telemetry for agent execution -- tool invocations, iteration counts, latency per step
- **Log Analytics**: Centralized logs for all agent actions with structured query support
- **Alerts**: Alerts on max-iteration hits, tool execution failures, approval queue depth, and abnormal usage patterns
- **Custom Metrics**: Per-tool success rates, average iterations per request, and token consumption tracked

### Visualization

- **Azure Monitor Workbooks**: Operational dashboards for agent activity, tool usage distribution, and execution patterns
- **Power BI**: Executive dashboards for automation ROI -- requests handled, time saved, and escalation rates

### Tracking

- **Full Audit Trail**: Every agent action, tool invocation, parameter, and result logged to Cosmos DB with timestamps
- **Immutable Logs**: Tamper-proof audit logs for compliance -- all tool executions recorded with user context and decision reasoning
- **Correlation IDs**: Session-level correlation from user request through every tool execution iteration

### Accuracy

- **ReAct Pattern**: Reason + Act loop ensures the agent reasons about each step before acting, enabling self-correction
- **Max Iterations**: Capped at 10 iterations to prevent runaway execution; graceful fallback with user notification
- **Tool Validation**: Tool parameters validated against schema before execution; required parameters enforced
- **Confirmation Flow**: Agent confirms understanding with user before executing multi-step plans

### Explainability

- **Execution Trace**: Full conversation history including THOUGHT, ACTION, and OBSERVATION for each iteration returned in the response
- **Tool Results**: Every tool execution result is visible in the response payload with arguments and outcomes
- **Plan Transparency**: Agent explains its multi-step execution plan to the user before taking action
- **Iteration Count**: Response includes iteration count for debugging and performance analysis

### Responsibility

- **Human-in-the-Loop**: Sensitive actions (expense submission, HR changes) flagged with `requires_approval: true` and routed for human approval
- **Escalation Paths**: Agent escalates to human support when uncertain or when max iterations are reached
- **User Confirmation**: Irreversible actions require explicit user confirmation before execution
- **Content Filtering**: Azure OpenAI content filters applied to all agent responses

### Interpretability

- **Tool Registry**: All available tools documented with name, description, category, and parameter schema; exposed via GET /api/agent/tools
- **Decision Reasoning**: GPT-4o provides reasoning for tool selection and execution order
- **Category Tagging**: Each tool tagged with category (HR, IT, Finance) for clear organizational mapping
- **Parameter Transparency**: Tool arguments and results fully visible in the response for audit

### Portability

- **Infrastructure as Code**: All resources defined in Terraform with environment-specific configurations
- **Modular Tool Registry**: Tools registered via decorator pattern -- add or remove tools without code changes to the orchestrator
- **SDK Abstraction**: OpenAI Python SDK with Azure configuration; tool definitions follow OpenAI function calling schema for portability
- **Containerization**: Azure Functions compatible with Docker for local development and alternative hosting

## Project Structure

```
project-4-agentic-platform/
|-- docs/
|   +-- ARCHITECTURE.md             # Detailed architecture documentation
|-- infra/
|   +-- main.tf                     # Terraform infrastructure definitions
|-- src/
|   +-- agent_orchestrator.py       # Agent orchestrator with 9 tools, ReAct loop,
|                                   #   tool registry, and HTTP endpoints
|-- tests/
|   |-- test_agent_orchestrator.py  # Unit tests for agent and tools
|   +-- test_comprehensive.py       # Integration and end-to-end tests
+-- README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agent/chat` | Submit a natural language request to the agent orchestrator |
| `GET` | `/api/agent/tools` | List all registered agent tools with descriptions and categories |
| `GET` | `/api/health` | Health check -- returns service status |

### POST /api/agent/chat

**Request:**
```json
{
  "message": "I'm locked out of my laptop and need to submit my expense report by EOD",
  "user_context": {
    "email": "john.doe@company.com",
    "name": "John Doe",
    "department": "Engineering",
    "manager": "jane.smith@company.com"
  },
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "I've unlocked your account and sent a password reset link to your email. Once you're back in, I've prepared an expense report draft. Would you like me to walk you through the submission?",
  "tools_executed": [
    {
      "tool": "check_account_status",
      "arguments": {"user_email": "john.doe@company.com"},
      "result": {"status": "locked", "mfa_enabled": true},
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "tool": "unlock_account",
      "arguments": {"user_email": "john.doe@company.com"},
      "result": {"success": true, "message": "Account unlocked"},
      "timestamp": "2024-01-15T10:30:01Z"
    },
    {
      "tool": "reset_password",
      "arguments": {"user_email": "john.doe@company.com", "method": "email"},
      "result": {"success": true, "expires_in": "24 hours"},
      "timestamp": "2024-01-15T10:30:02Z"
    }
  ],
  "requires_action": false,
  "iterations": 4
}
```

### GET /api/agent/tools

**Response:**
```json
{
  "tools": [
    {"name": "submit_leave_request", "description": "Submit a leave/PTO request", "category": "hr", "requires_approval": false},
    {"name": "submit_expense", "description": "Submit an expense report", "category": "finance", "requires_approval": true}
  ]
}
```

## License

This project is licensed under the MIT License.
