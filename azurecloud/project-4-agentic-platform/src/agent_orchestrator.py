"""
GenAI Agentic Automation Platform - Agent Orchestrator
========================================================
Multi-agent system with Azure OpenAI function calling
"""

import azure.functions as func
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    GPT_MODEL = "gpt-4o"
    MAX_ITERATIONS = 10


# ==============================================================================
# Tool Definitions
# ==============================================================================

class ToolCategory(Enum):
    HR = "hr"
    IT = "it"
    FINANCE = "finance"
    GENERAL = "general"


@dataclass
class Tool:
    """Represents an agent tool/function."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    required_params: List[str]
    handler: Optional[Callable] = None
    requires_approval: bool = False


# Tool Registry
TOOL_REGISTRY: Dict[str, Tool] = {}


def register_tool(tool: Tool):
    """Register a tool in the registry."""
    TOOL_REGISTRY[tool.name] = tool
    return tool


# ==============================================================================
# HR Tools
# ==============================================================================

@register_tool
def submit_leave_request_tool():
    return Tool(
        name="submit_leave_request",
        description="Submit a leave/PTO request for the employee. Use this when user wants to take time off.",
        category=ToolCategory.HR,
        parameters={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "leave_type": {
                    "type": "string",
                    "enum": ["vacation", "sick", "personal", "bereavement"],
                    "description": "Type of leave"
                },
                "reason": {"type": "string", "description": "Reason for leave"}
            },
            "required": ["start_date", "end_date", "leave_type"]
        },
        required_params=["start_date", "end_date", "leave_type"]
    )


@register_tool
def get_pto_balance_tool():
    return Tool(
        name="get_pto_balance",
        description="Get the user's current PTO/vacation balance",
        category=ToolCategory.HR,
        parameters={
            "type": "object",
            "properties": {
                "user_email": {"type": "string", "description": "User email (optional, defaults to current user)"}
            }
        },
        required_params=[]
    )


@register_tool
def lookup_hr_policy_tool():
    return Tool(
        name="lookup_hr_policy",
        description="Look up HR policies and procedures",
        category=ToolCategory.HR,
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Policy topic to look up"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords to search"}
            },
            "required": ["topic"]
        },
        required_params=["topic"]
    )


# ==============================================================================
# IT Tools
# ==============================================================================

@register_tool
def reset_password_tool():
    return Tool(
        name="reset_password",
        description="Reset user's password and send reset link via email",
        category=ToolCategory.IT,
        parameters={
            "type": "object",
            "properties": {
                "user_email": {"type": "string", "description": "User's email address"},
                "method": {
                    "type": "string",
                    "enum": ["email", "sms"],
                    "description": "Delivery method for reset link"
                }
            },
            "required": ["user_email"]
        },
        required_params=["user_email"]
    )


@register_tool
def unlock_account_tool():
    return Tool(
        name="unlock_account",
        description="Unlock a locked user account",
        category=ToolCategory.IT,
        parameters={
            "type": "object",
            "properties": {
                "user_email": {"type": "string", "description": "User's email address"}
            },
            "required": ["user_email"]
        },
        required_params=["user_email"]
    )


@register_tool
def create_it_ticket_tool():
    return Tool(
        name="create_it_ticket",
        description="Create an IT support ticket",
        category=ToolCategory.IT,
        parameters={
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
                "description": {"type": "string", "description": "Issue description"},
                "affected_system": {"type": "string", "description": "System affected"}
            },
            "required": ["category", "description"]
        },
        required_params=["category", "description"]
    )


@register_tool
def check_account_status_tool():
    return Tool(
        name="check_account_status",
        description="Check user account status (locked, active, disabled)",
        category=ToolCategory.IT,
        parameters={
            "type": "object",
            "properties": {
                "user_email": {"type": "string", "description": "User's email address"}
            },
            "required": ["user_email"]
        },
        required_params=["user_email"]
    )


# ==============================================================================
# Finance Tools
# ==============================================================================

@register_tool
def submit_expense_tool():
    return Tool(
        name="submit_expense",
        description="Submit an expense report for reimbursement",
        category=ToolCategory.FINANCE,
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Expense amount"},
                "currency": {"type": "string", "default": "USD"},
                "category": {
                    "type": "string",
                    "enum": ["travel", "meals", "supplies", "software", "other"]
                },
                "description": {"type": "string", "description": "Expense description"},
                "receipt_url": {"type": "string", "description": "URL to receipt image"}
            },
            "required": ["amount", "category", "description"]
        },
        required_params=["amount", "category", "description"],
        requires_approval=True
    )


@register_tool
def check_expense_status_tool():
    return Tool(
        name="check_expense_status",
        description="Check status of submitted expense reports",
        category=ToolCategory.FINANCE,
        parameters={
            "type": "object",
            "properties": {
                "expense_id": {"type": "string", "description": "Expense report ID (optional)"}
            }
        },
        required_params=[]
    )


# Initialize tools
submit_leave_request_tool()
get_pto_balance_tool()
lookup_hr_policy_tool()
reset_password_tool()
unlock_account_tool()
create_it_ticket_tool()
check_account_status_tool()
submit_expense_tool()
check_expense_status_tool()


# ==============================================================================
# Tool Executors (Simulated - Replace with actual integrations)
# ==============================================================================

class ToolExecutor:
    """Executes tools and returns results."""

    @staticmethod
    def execute(tool_name: str, parameters: Dict[str, Any], user_context: Dict) -> Dict:
        """Execute a tool with given parameters."""
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")

        # Simulated responses - replace with actual API calls
        executors = {
            "submit_leave_request": ToolExecutor._submit_leave,
            "get_pto_balance": ToolExecutor._get_pto_balance,
            "lookup_hr_policy": ToolExecutor._lookup_policy,
            "reset_password": ToolExecutor._reset_password,
            "unlock_account": ToolExecutor._unlock_account,
            "create_it_ticket": ToolExecutor._create_ticket,
            "check_account_status": ToolExecutor._check_account,
            "submit_expense": ToolExecutor._submit_expense,
            "check_expense_status": ToolExecutor._check_expense
        }

        executor = executors.get(tool_name)
        if executor:
            return executor(parameters, user_context)

        return {"error": f"Unknown tool: {tool_name}"}

    @staticmethod
    def _submit_leave(params: Dict, ctx: Dict) -> Dict:
        # In production: Call Workday/HR system API
        return {
            "success": True,
            "request_id": "LR-2024-001234",
            "status": "pending_approval",
            "message": f"Leave request submitted for {params['start_date']} to {params['end_date']}",
            "approver": "manager@company.com"
        }

    @staticmethod
    def _get_pto_balance(params: Dict, ctx: Dict) -> Dict:
        return {
            "vacation_days": 15,
            "sick_days": 10,
            "personal_days": 3,
            "used_vacation": 5,
            "available_vacation": 10
        }

    @staticmethod
    def _lookup_policy(params: Dict, ctx: Dict) -> Dict:
        topic = params.get("topic", "").lower()
        policies = {
            "leave": "Employees accrue 1.25 days of PTO per month. Maximum carryover is 5 days.",
            "remote": "Remote work allowed up to 3 days per week with manager approval.",
            "expense": "Expenses over $500 require VP approval. Receipts required for all claims."
        }
        return {"topic": topic, "policy": policies.get(topic, "Policy not found")}

    @staticmethod
    def _reset_password(params: Dict, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message": f"Password reset link sent to {params['user_email']}",
            "expires_in": "24 hours"
        }

    @staticmethod
    def _unlock_account(params: Dict, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message": f"Account {params['user_email']} has been unlocked",
            "previous_status": "locked"
        }

    @staticmethod
    def _create_ticket(params: Dict, ctx: Dict) -> Dict:
        return {
            "success": True,
            "ticket_id": "INC-2024-005678",
            "status": "open",
            "priority": params.get("priority", "medium"),
            "assigned_to": "IT Support Queue"
        }

    @staticmethod
    def _check_account(params: Dict, ctx: Dict) -> Dict:
        return {
            "user_email": params["user_email"],
            "status": "active",
            "last_login": "2024-01-15T09:30:00Z",
            "mfa_enabled": True
        }

    @staticmethod
    def _submit_expense(params: Dict, ctx: Dict) -> Dict:
        return {
            "success": True,
            "expense_id": "EXP-2024-003456",
            "status": "pending_approval",
            "amount": params["amount"],
            "approver": "finance@company.com"
        }

    @staticmethod
    def _check_expense(params: Dict, ctx: Dict) -> Dict:
        return {
            "expenses": [
                {"id": "EXP-2024-003456", "amount": 250.00, "status": "approved"},
                {"id": "EXP-2024-003123", "amount": 75.50, "status": "pending"}
            ]
        }


# ==============================================================================
# Agent Orchestrator
# ==============================================================================

class AgentOrchestrator:
    """Orchestrates multi-agent task execution using GPT-4o function calling."""

    def __init__(self, user_context: Dict):
        self.user_context = user_context
        self.credential = DefaultAzureCredential()
        self.openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=lambda: self.credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-06-01"
        )
        self.conversation_history: List[Dict] = []
        self.tool_results: List[Dict] = []

    def _get_tools_for_openai(self) -> List[Dict]:
        """Convert tool registry to OpenAI function format."""
        tools = []
        for name, tool in TOOL_REGISTRY.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return tools

    def _get_system_prompt(self) -> str:
        """Build system prompt with user context."""
        return f"""You are an enterprise AI assistant that helps employees with HR, IT, and Finance tasks.

USER CONTEXT:
- Name: {self.user_context.get('name', 'Employee')}
- Email: {self.user_context.get('email', 'user@company.com')}
- Department: {self.user_context.get('department', 'Unknown')}
- Manager: {self.user_context.get('manager', 'Unknown')}

CAPABILITIES:
- HR: Submit leave requests, check PTO balance, lookup HR policies
- IT: Reset passwords, unlock accounts, create IT tickets
- Finance: Submit expenses, check expense status

GUIDELINES:
1. Always confirm understanding before taking actions
2. For multi-step tasks, explain your plan first
3. If information is missing, ask the user
4. Be concise but helpful in responses
5. If a tool fails, explain the issue and suggest alternatives
6. For sensitive actions (password reset, expense submission), confirm with user first

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""

    async def process_request(self, user_message: str) -> Dict:
        """
        Process user request through the agent loop.

        Returns:
            {
                "response": str,
                "tools_executed": List[Dict],
                "requires_action": bool
            }
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        iteration = 0
        while iteration < Config.MAX_ITERATIONS:
            iteration += 1

            # Call OpenAI with function calling
            response = self.openai_client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    *self.conversation_history
                ],
                tools=self._get_tools_for_openai(),
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.3
            )

            message = response.choices[0].message

            # Check if model wants to call tools
            if message.tool_calls:
                # Add assistant message with tool calls
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Executing tool: {tool_name}")

                    # Execute the tool
                    result = ToolExecutor.execute(tool_name, tool_args, self.user_context)

                    # Store result
                    self.tool_results.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    # Add tool result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

            else:
                # Model is done with tools, return response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content
                })

                return {
                    "response": message.content,
                    "tools_executed": self.tool_results,
                    "requires_action": False,
                    "iterations": iteration
                }

        # Max iterations reached
        return {
            "response": "I apologize, but I wasn't able to complete all the tasks. Please try again or contact support.",
            "tools_executed": self.tool_results,
            "requires_action": True,
            "iterations": iteration
        }


# ==============================================================================
# Azure Functions HTTP Endpoints
# ==============================================================================

@app.route(route="agent/chat", methods=["POST"])
async def agent_chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main chat endpoint for agent interactions.

    Request:
    {
        "message": "I need to take Friday off",
        "user_context": {
            "email": "john.doe@company.com",
            "name": "John Doe",
            "department": "Engineering"
        },
        "session_id": "optional-session-id"
    }
    """
    try:
        body = req.get_json()
        message = body.get("message")
        user_context = body.get("user_context", {})

        if not message:
            return func.HttpResponse(
                json.dumps({"error": "message is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Create orchestrator and process
        orchestrator = AgentOrchestrator(user_context)
        result = await orchestrator.process_request(message)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="agent/tools", methods=["GET"])
async def list_tools(req: func.HttpRequest) -> func.HttpResponse:
    """List all available agent tools."""
    tools = []
    for name, tool in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": tool.description,
            "category": tool.category.value,
            "requires_approval": tool.requires_approval
        })

    return func.HttpResponse(
        json.dumps({"tools": tools}),
        mimetype="application/json"
    )


@app.route(route="health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "agent-orchestrator"}),
        mimetype="application/json"
    )
