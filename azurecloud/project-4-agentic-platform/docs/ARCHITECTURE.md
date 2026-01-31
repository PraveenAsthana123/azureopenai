# Project 4: GenAI Agentic Workflow Automation Platform

## Executive Summary

An enterprise AI agent platform that enables autonomous multi-step task execution using Azure OpenAI's function calling capabilities. The platform allows AI agents to interact with enterprise systems (HR, IT, Finance) to perform complex workflows like password resets, leave approvals, ticket creation, and data retrieval - all triggered through natural language requests.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    GENAI AGENTIC AUTOMATION PLATFORM                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                         │
│                                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ Microsoft Teams│  │ Slack Bot      │  │ Web Portal     │  │ Mobile App       │   │
│  │ Bot            │  │                │  │ (React)        │  │ (React Native)   │   │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └────────┬─────────┘   │
│          │                   │                   │                    │             │
└──────────┼───────────────────┼───────────────────┼────────────────────┼─────────────┘
           │                   │                   │                    │
           └───────────────────┴───────────────────┴────────────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │      Azure API Gateway      │
                         │      (APIM)                 │
                         │                             │
                         │  - OAuth2/JWT Auth          │
                         │  - Rate Limiting            │
                         │  - Request Validation       │
                         └──────────────┬──────────────┘
                                        │
┌───────────────────────────────────────┼───────────────────────────────────────────┐
│                    AGENT ORCHESTRATION LAYER                                       │
│                                        │                                           │
│                         ┌──────────────▼──────────────┐                           │
│                         │    AGENT ORCHESTRATOR       │                           │
│                         │    (Azure Functions)        │                           │
│                         │                             │                           │
│                         │  ┌───────────────────────┐  │                           │
│                         │  │ Intent Classification │  │                           │
│                         │  │ (What does user want?)│  │                           │
│                         │  └───────────┬───────────┘  │                           │
│                         │              │              │                           │
│                         │  ┌───────────▼───────────┐  │                           │
│                         │  │ Agent Selection       │  │                           │
│                         │  │ (Which agent handles?)│  │                           │
│                         │  └───────────┬───────────┘  │                           │
│                         │              │              │                           │
│                         │  ┌───────────▼───────────┐  │                           │
│                         │  │ Execution Planning    │  │                           │
│                         │  │ (Multi-step plan)     │  │                           │
│                         │  └───────────┬───────────┘  │                           │
│                         │              │              │                           │
│                         │  ┌───────────▼───────────┐  │                           │
│                         │  │ Tool Execution Loop   │  │                           │
│                         │  │ (Function calling)    │  │                           │
│                         │  └───────────────────────┘  │                           │
│                         └──────────────┬──────────────┘                           │
│                                        │                                           │
│         ┌──────────────────────────────┼──────────────────────────────┐           │
│         │                              │                              │           │
│         ▼                              ▼                              ▼           │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐        │
│  │   HR AGENT      │        │   IT AGENT      │        │  FINANCE AGENT  │        │
│  │                 │        │                 │        │                 │        │
│  │ Tools:          │        │ Tools:          │        │ Tools:          │        │
│  │ - Leave request │        │ - Password reset│        │ - Expense submit│        │
│  │ - PTO balance   │        │ - Ticket create │        │ - Budget query  │        │
│  │ - Policy lookup │        │ - Access request│        │ - Invoice status│        │
│  │ - Org chart     │        │ - Asset lookup  │        │ - PO approval   │        │
│  └────────┬────────┘        └────────┬────────┘        └────────┬────────┘        │
│           │                          │                          │                 │
└───────────┼──────────────────────────┼──────────────────────────┼─────────────────┘
            │                          │                          │
┌───────────┼──────────────────────────┼──────────────────────────┼─────────────────┐
│           │      AZURE OPENAI (GPT-4o with Function Calling)    │                 │
│           │                          │                          │                 │
│   ┌───────▼──────────────────────────▼──────────────────────────▼───────┐         │
│   │                                                                      │         │
│   │   System Prompt: "You are an enterprise assistant with access to    │         │
│   │   the following tools..."                                            │         │
│   │                                                                      │         │
│   │   Tools: [                                                           │         │
│   │     {name: "submit_leave_request", parameters: {...}},              │         │
│   │     {name: "reset_password", parameters: {...}},                    │         │
│   │     {name: "create_ticket", parameters: {...}},                     │         │
│   │     ...                                                              │         │
│   │   ]                                                                  │         │
│   │                                                                      │         │
│   │   User: "I need to take next Friday off for a doctor's appointment" │         │
│   │                                                                      │         │
│   │   Assistant: <function_call name="submit_leave_request">            │         │
│   │              {"date": "2024-01-19", "type": "sick", "hours": 8}     │         │
│   │              </function_call>                                        │         │
│   └──────────────────────────────────────────────────────────────────────┘         │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         TOOL EXECUTION LAYER                                         │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                     Durable Functions (Workflow Engine)                       │   │
│  │                                                                               │   │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │   │
│  │   │ Sub-orch 1  │──►│ Sub-orch 2  │──►│ Sub-orch 3  │──►│ Human Task  │     │   │
│  │   │ (Validate)  │   │ (Execute)   │   │ (Notify)    │   │ (Approval)  │     │   │
│  │   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Logic Apps   │  │ Power        │  │ Azure        │  │ Custom APIs            │   │
│  │ (Low-code)   │  │ Automate     │  │ Functions    │  │ (REST endpoints)       │   │
│  │              │  │              │  │              │  │                        │   │
│  │ - Approvals  │  │ - Email      │  │ - Complex    │  │ - Legacy system        │   │
│  │ - SharePoint │  │ - Teams msg  │  │   logic      │  │   integration          │   │
│  │ - D365       │  │ - Adaptive   │  │ - Data       │  │ - Third-party          │   │
│  │              │  │   cards      │  │   transform  │  │   APIs                 │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ENTERPRISE INTEGRATIONS                                      │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Microsoft    │  │ ServiceNow   │  │ Workday      │  │ SAP          │             │
│  │ Graph API    │  │              │  │              │  │              │             │
│  │              │  │ - Tickets    │  │ - HR data    │  │ - Finance    │             │
│  │ - Users      │  │ - Incidents  │  │ - Leave      │  │ - Procurement│             │
│  │ - Calendar   │  │ - Assets     │  │ - Benefits   │  │ - Inventory  │             │
│  │ - Email      │  │ - Change     │  │ - Time       │  │              │             │
│  │ - Teams      │  │              │  │              │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Azure AD /   │  │ Jira         │  │ Salesforce   │  │ Custom       │             │
│  │ Entra ID     │  │              │  │              │  │ Databases    │             │
│  │              │  │ - Issues     │  │ - Cases      │  │              │             │
│  │ - Identity   │  │ - Projects   │  │ - Accounts   │  │ - SQL/Cosmos │             │
│  │ - Roles      │  │ - Sprints    │  │ - Contacts   │  │ - Legacy     │             │
│  │ - Groups     │  │              │  │              │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         STATE & OBSERVABILITY                                        │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────┐   │
│  │ Cosmos DB        │  │ Redis Cache      │  │ Azure Monitor                    │   │
│  │                  │  │                  │  │                                  │   │
│  │ - Workflow state │  │ - Session cache  │  │ - Application Insights          │   │
│  │ - Chat history   │  │ - Rate limiting  │  │ - Log Analytics                  │   │
│  │ - Audit logs     │  │ - Tool results   │  │ - Custom metrics                 │   │
│  │ - User prefs     │  │                  │  │ - Alerts                         │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC EXECUTION LOOP (ReAct Pattern)                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

User Request: "I'm locked out of my laptop and need to submit my expense report by EOD"

     ┌────────────────────────────────────────────────────────────────────────────┐
     │                         STEP 1: INTENT ANALYSIS                            │
     │                                                                            │
     │   GPT-4o Analysis:                                                         │
     │   - Intent 1: Password/Access issue → IT Agent                            │
     │   - Intent 2: Expense submission → Finance Agent                          │
     │   - Urgency: High (EOD deadline)                                          │
     │   - Order: Must resolve access before expense submission                   │
     └────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
     ┌────────────────────────────────────────────────────────────────────────────┐
     │                         STEP 2: EXECUTION PLAN                             │
     │                                                                            │
     │   Plan:                                                                    │
     │   1. [IT] Check user's account status                                     │
     │   2. [IT] Reset password / Unlock account                                 │
     │   3. [IT] Send password reset link                                        │
     │   4. [Finance] Get expense report template                                │
     │   5. [Finance] Pre-fill known details                                     │
     │   6. [Human] User completes expense details                               │
     │   7. [Finance] Submit expense report                                      │
     └────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
     ┌────────────────────────────────────────────────────────────────────────────┐
     │                      STEP 3: TOOL EXECUTION (Loop)                         │
     │                                                                            │
     │   Iteration 1:                                                             │
     │   ┌─────────────────────────────────────────────────────────────────────┐ │
     │   │ THOUGHT: Need to check account status first                         │ │
     │   │ ACTION: check_account_status(user="john.doe@company.com")          │ │
     │   │ OBSERVATION: {"status": "locked", "reason": "too_many_attempts"}   │ │
     │   └─────────────────────────────────────────────────────────────────────┘ │
     │                                                                            │
     │   Iteration 2:                                                             │
     │   ┌─────────────────────────────────────────────────────────────────────┐ │
     │   │ THOUGHT: Account is locked, need to unlock                          │ │
     │   │ ACTION: unlock_account(user="john.doe@company.com")                │ │
     │   │ OBSERVATION: {"success": true, "message": "Account unlocked"}      │ │
     │   └─────────────────────────────────────────────────────────────────────┘ │
     │                                                                            │
     │   Iteration 3:                                                             │
     │   ┌─────────────────────────────────────────────────────────────────────┐ │
     │   │ THOUGHT: Need to send password reset                                │ │
     │   │ ACTION: send_password_reset(user="john.doe@company.com")           │ │
     │   │ OBSERVATION: {"sent": true, "email": "john.doe@company.com"}       │ │
     │   └─────────────────────────────────────────────────────────────────────┘ │
     │                                                                            │
     │   ... continues with expense workflow ...                                  │
     └────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
     ┌────────────────────────────────────────────────────────────────────────────┐
     │                         STEP 4: RESPONSE                                   │
     │                                                                            │
     │   "I've unlocked your account and sent a password reset link to your     │
     │    email. Once you're back in, I've prepared an expense report draft.    │
     │    Just add the receipt images and amounts, then I'll submit it for you. │
     │    Would you like me to walk you through the expense submission?"        │
     └────────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Definition Schema

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "submit_leave_request",
        "description": "Submit a leave/PTO request for the employee",
        "parameters": {
          "type": "object",
          "properties": {
            "start_date": {
              "type": "string",
              "description": "Start date in YYYY-MM-DD format"
            },
            "end_date": {
              "type": "string",
              "description": "End date in YYYY-MM-DD format"
            },
            "leave_type": {
              "type": "string",
              "enum": ["vacation", "sick", "personal", "bereavement"],
              "description": "Type of leave"
            },
            "reason": {
              "type": "string",
              "description": "Reason for the leave request"
            }
          },
          "required": ["start_date", "end_date", "leave_type"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "reset_password",
        "description": "Reset user's password and send reset link",
        "parameters": {
          "type": "object",
          "properties": {
            "user_email": {
              "type": "string",
              "description": "User's email address"
            },
            "method": {
              "type": "string",
              "enum": ["email", "sms", "authenticator"],
              "description": "Password reset delivery method"
            }
          },
          "required": ["user_email"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_it_ticket",
        "description": "Create an IT support ticket in ServiceNow",
        "parameters": {
          "type": "object",
          "properties": {
            "category": {
              "type": "string",
              "enum": ["hardware", "software", "network", "access", "other"]
            },
            "priority": {
              "type": "string",
              "enum": ["low", "medium", "high", "critical"]
            },
            "description": {
              "type": "string",
              "description": "Detailed description of the issue"
            },
            "affected_system": {
              "type": "string",
              "description": "System or application affected"
            }
          },
          "required": ["category", "description"]
        }
      }
    }
  ]
}
```

---

## Azure Services Mapping

| Layer | Service | Purpose |
|-------|---------|---------|
| **Frontend** | Bot Framework | Teams/Slack integration |
| **API** | APIM | Gateway, auth, rate limiting |
| **Orchestration** | Azure Functions | Agent orchestrator |
| **AI** | Azure OpenAI | GPT-4o with function calling |
| **Workflows** | Durable Functions | Multi-step workflows |
| **Workflows** | Logic Apps | Low-code integrations |
| **Integration** | Graph API | Microsoft 365 services |
| **State** | Cosmos DB | Workflow state, history |
| **Cache** | Redis | Session, rate limiting |
| **Security** | Key Vault | Secrets, API keys |
| **Identity** | Entra ID | User authentication |
| **Monitoring** | App Insights | Telemetry, tracing |

---

## Security Considerations

### 1. Permission Boundaries
- Agents can only access tools user has permissions for
- Tool execution validated against user's Entra ID roles
- Approval workflows for sensitive actions

### 2. Audit Trail
- All tool executions logged to Cosmos DB
- Immutable audit log for compliance
- Real-time alerts for suspicious patterns

### 3. Rate Limiting
- Per-user rate limits on agent requests
- Token budget per session
- Cost controls on OpenAI API usage

---

## Interview Talking Points

### Architecture Decisions

1. **Why Function Calling over Fine-tuning?**
   - More flexible - add/remove tools without retraining
   - Better control over what actions agent can take
   - Easier to maintain and debug
   - Built-in parameter validation

2. **Why Durable Functions for Workflows?**
   - Built-in state management
   - Handles long-running processes (approvals)
   - Automatic retry and checkpointing
   - Fan-out/fan-in for parallel tool execution

3. **ReAct Pattern Benefits**
   - Reasoning trace for debugging
   - Self-correcting behavior
   - Better handling of multi-step tasks
   - More predictable than pure LLM responses

4. **Human-in-the-Loop Design**
   - Approval workflows for sensitive actions
   - Escalation paths when agent is uncertain
   - User confirmation before irreversible actions

## Business Domain, Security, Governance & Compliance

### Business Domain
- **Classification:** B2E (Business-to-Employee)
- **Visibility:** Internal — enterprise workflow automation for employees
- **Project Score:** 8.5 / 10 (Elevated)

### Security Controls
| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | Private Link | All backend services via private endpoints |
| Identity | Managed Identity | System-assigned MI; no stored credentials |
| Identity | RBAC | Function-level authorization per tool/action |
| Identity | Entra ID | Corporate SSO with MFA enforcement |
| Data | Key Vault | Tool credentials, API keys, connection strings |
| Data | Encryption | AES-256 at rest, TLS 1.2 in transit |
| Application | Approval Gates | Human-in-the-loop for high-risk actions (financial, HR, admin) |
| Application | Action Scoping | Tools scoped to least-privilege (read vs write) |
| Application | Rate Limiting | Per-user action limits to prevent abuse |
| Monitoring | Full Audit Trail | Every agent action, tool invocation, and decision logged |

### Governance & Compliance
| Area | Policy | Details |
|------|--------|---------|
| Workflow Audit | Complete | All multi-step workflows logged with decision reasoning |
| Human-in-the-Loop | Mandatory | Actions above threshold require human approval |
| Action Logging | Immutable | Tamper-proof logs of all tool executions |
| Change Management | ITSM integrated | Workflow changes tracked via ServiceNow/Jira |
| Tool Governance | Registry | Approved tool catalog with version control |

### Regulatory Applicability
- **SOC 2 Type II:** Workflow audit trail and access controls
- **SOX (if financial actions):** Approval gates for financial transactions
- **ISO 27001:** Information security management for automated workflows
