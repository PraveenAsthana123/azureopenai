"""
Agentic Workflow Orchestrator with Tool Registry

Implements:
- Planning + tool execution on top of RAG
- Grounded actions with citations
- Enterprise-safe guardrails (approval gates, scopes, audit)
- Integration with Azure ecosystem tools
- Observable and controllable execution
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from enum import Enum
import asyncio
import json
import hashlib
from datetime import datetime
from abc import ABC, abstractmethod

from openai import AsyncAzureOpenAI


class ToolCategory(Enum):
    """Risk category for tools."""
    READ_ONLY = "read_only"  # Low risk - search, fetch
    WRITE = "write"  # High risk - create, update, delete
    EXECUTE = "execute"  # Very high risk - run workflows


class ApprovalRequirement(Enum):
    """When approval is required."""
    NEVER = "never"
    ALWAYS = "always"
    CONDITIONAL = "conditional"


class ActionStatus(Enum):
    """Status of an action."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolConstraint:
    """Constraints on tool usage."""
    allowed_values: dict[str, list[str]] = field(default_factory=dict)
    max_items: int | None = None
    max_bytes: int | None = None
    required_clearance: str | None = None
    allowed_tenants: list[str] | None = None


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    description: str
    category: ToolCategory
    approval: ApprovalRequirement
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    constraints: ToolConstraint | None = None
    handler: Callable[..., Awaitable[Any]] | None = None


@dataclass
class UserContext:
    """Security context for the current user."""
    user_id: str
    tenant_id: str
    groups: list[str] = field(default_factory=list)
    clearance_level: str = "public"
    department: str | None = None


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: str
    action: str  # "retrieve", "call_tool", "analyze", "respond"
    tool_name: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    justification_citations: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    status: ActionStatus = ActionStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class ExecutionPlan:
    """A plan for executing a user request."""
    plan_id: str
    goal: str
    steps: list[PlanStep]
    requires_approval: bool = False
    approval_reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExecutionResult:
    """Result of plan execution."""
    plan_id: str
    status: str
    answer: str | None
    citations: list[dict[str, Any]]
    actions_taken: list[dict[str, Any]]
    execution_time_ms: float
    cost_estimate_usd: float
    audit_log: list[dict[str, Any]]


class ToolRegistry:
    """
    Registry of available tools.

    Tools are categorized by risk level and have associated constraints.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default set of tools."""
        # Read-only tools
        self.register(ToolDefinition(
            name="search_documents",
            description="Search indexed documents using hybrid retrieval",
            category=ToolCategory.READ_ONLY,
            approval=ApprovalRequirement.NEVER,
            input_schema={
                "query": {"type": "string", "description": "Search query"},
                "filters": {"type": "object", "description": "Optional filters"},
                "top_k": {"type": "integer", "default": 10},
            },
            output_schema={
                "chunks": {"type": "array", "items": {"type": "object"}},
                "total_count": {"type": "integer"},
            },
        ))

        self.register(ToolDefinition(
            name="get_document_metadata",
            description="Get metadata for a specific document",
            category=ToolCategory.READ_ONLY,
            approval=ApprovalRequirement.NEVER,
            input_schema={
                "doc_id": {"type": "string", "description": "Document ID"},
            },
            output_schema={
                "metadata": {"type": "object"},
            },
        ))

        self.register(ToolDefinition(
            name="get_user_profile",
            description="Get user profile from Microsoft Graph",
            category=ToolCategory.READ_ONLY,
            approval=ApprovalRequirement.NEVER,
            input_schema={
                "user_id": {"type": "string", "description": "User ID or email"},
            },
            output_schema={
                "user": {"type": "object"},
            },
        ))

        self.register(ToolDefinition(
            name="list_key_vault_keys",
            description="List keys in Azure Key Vault",
            category=ToolCategory.READ_ONLY,
            approval=ApprovalRequirement.NEVER,
            input_schema={
                "vault_name": {"type": "string"},
                "include_versions": {"type": "boolean", "default": False},
            },
            output_schema={
                "keys": {"type": "array"},
            },
            constraints=ToolConstraint(
                required_clearance="internal",
            ),
        ))

        # Write tools (require approval)
        self.register(ToolDefinition(
            name="create_sharepoint_document",
            description="Create a document in SharePoint library",
            category=ToolCategory.WRITE,
            approval=ApprovalRequirement.ALWAYS,
            input_schema={
                "library_id": {"type": "string"},
                "title": {"type": "string"},
                "content_md": {"type": "string"},
            },
            output_schema={
                "document_id": {"type": "string"},
                "web_url": {"type": "string"},
            },
            constraints=ToolConstraint(
                allowed_values={"library_id": ["policies-reports", "team-docs"]},
                max_bytes=200000,
            ),
        ))

        self.register(ToolDefinition(
            name="create_ticket",
            description="Create a support ticket in ServiceNow/Jira",
            category=ToolCategory.WRITE,
            approval=ApprovalRequirement.CONDITIONAL,
            input_schema={
                "system": {"type": "string", "enum": ["servicenow", "jira"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "assignee": {"type": "string", "nullable": True},
            },
            output_schema={
                "ticket_id": {"type": "string"},
                "url": {"type": "string"},
            },
        ))

        self.register(ToolDefinition(
            name="send_email",
            description="Send email notification",
            category=ToolCategory.WRITE,
            approval=ApprovalRequirement.ALWAYS,
            input_schema={
                "to": {"type": "array", "items": {"type": "string"}},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            output_schema={
                "message_id": {"type": "string"},
            },
            constraints=ToolConstraint(
                max_items=10,  # Max 10 recipients
            ),
        ))

        # Execute tools (high risk)
        self.register(ToolDefinition(
            name="trigger_workflow",
            description="Trigger a Logic App workflow",
            category=ToolCategory.EXECUTE,
            approval=ApprovalRequirement.ALWAYS,
            input_schema={
                "workflow_name": {"type": "string"},
                "parameters": {"type": "object"},
            },
            output_schema={
                "run_id": {"type": "string"},
                "status": {"type": "string"},
            },
            constraints=ToolConstraint(
                allowed_values={"workflow_name": ["compliance-check", "report-generator"]},
            ),
        ))

    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolDefinition]:
        """List available tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_tools_for_llm(self) -> list[dict]:
        """Get tool definitions in OpenAI function calling format."""
        tools = []
        for tool in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.input_schema,
                        "required": [k for k, v in tool.input_schema.items()
                                    if not v.get("nullable", False) and "default" not in v],
                    },
                },
            })
        return tools


class Guardrails:
    """
    Safety guardrails for agent actions.

    Enforces:
    - Permission checks
    - Constraint validation
    - Prompt injection defense
    - Audit logging
    """

    # Patterns that might indicate prompt injection
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "disregard all prior",
        "forget everything",
        "new system prompt",
        "you are now",
        "pretend you are",
        "act as if",
        "override your instructions",
    ]

    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry

    def check_permissions(
        self,
        tool: ToolDefinition,
        user_context: UserContext,
    ) -> tuple[bool, str | None]:
        """Check if user has permission to use tool."""
        constraints = tool.constraints

        if not constraints:
            return True, None

        # Check clearance level
        if constraints.required_clearance:
            clearance_order = ["public", "internal", "confidential", "restricted"]
            user_level = clearance_order.index(user_context.clearance_level)
            required_level = clearance_order.index(constraints.required_clearance)

            if user_level < required_level:
                return False, f"Requires {constraints.required_clearance} clearance"

        # Check tenant
        if constraints.allowed_tenants:
            if user_context.tenant_id not in constraints.allowed_tenants:
                return False, "Tenant not authorized for this tool"

        return True, None

    def validate_inputs(
        self,
        tool: ToolDefinition,
        inputs: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Validate tool inputs against constraints."""
        constraints = tool.constraints

        if not constraints:
            return True, None

        # Check allowed values
        for field, allowed in constraints.allowed_values.items():
            if field in inputs and inputs[field] not in allowed:
                return False, f"Invalid value for {field}. Allowed: {allowed}"

        # Check max items
        if constraints.max_items:
            for field, value in inputs.items():
                if isinstance(value, list) and len(value) > constraints.max_items:
                    return False, f"Too many items in {field}. Max: {constraints.max_items}"

        # Check max bytes
        if constraints.max_bytes:
            total_bytes = len(json.dumps(inputs).encode())
            if total_bytes > constraints.max_bytes:
                return False, f"Input too large. Max: {constraints.max_bytes} bytes"

        return True, None

    def check_injection(self, text: str) -> tuple[bool, str | None]:
        """Check for prompt injection attempts."""
        text_lower = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            if pattern in text_lower:
                return False, f"Potential prompt injection detected: '{pattern}'"

        return True, None

    def requires_approval(
        self,
        tool: ToolDefinition,
        inputs: dict[str, Any],
        user_context: UserContext,
    ) -> tuple[bool, str | None]:
        """Determine if action requires user approval."""
        if tool.approval == ApprovalRequirement.ALWAYS:
            return True, f"Tool '{tool.name}' always requires approval"

        if tool.approval == ApprovalRequirement.CONDITIONAL:
            # Conditional logic based on inputs or context
            if tool.category == ToolCategory.WRITE:
                return True, f"Write action '{tool.name}' requires approval"

            # High priority tickets need approval
            if tool.name == "create_ticket" and inputs.get("priority") in ["high", "critical"]:
                return True, "High priority tickets require approval"

        return False, None


class Planner:
    """
    Creates execution plans from user requests.

    Uses LLM to decompose requests into steps and select appropriate tools.
    """

    PLANNING_PROMPT = """You are a planning agent that creates execution plans to fulfill user requests.

Available tools:
{tools_description}

User request: {request}

Retrieved context (from RAG):
{context}

Create a plan to fulfill this request. The plan should:
1. Use retrieval results when available
2. Call tools only when necessary
3. Cite evidence for each action
4. Keep the plan minimal and focused

Output a JSON plan:
{{
  "goal": "concise statement of the goal",
  "direct_answer_possible": true/false,
  "steps": [
    {{
      "step_id": "unique_id",
      "action": "retrieve|call_tool|analyze|respond",
      "tool_name": "tool name if action is call_tool",
      "inputs": {{}},
      "justification_citations": ["chunk_id1", "chunk_id2"],
      "depends_on": ["step_id of dependency"]
    }}
  ]
}}

If the request can be answered directly from context, set direct_answer_possible to true
and include a single "respond" step."""

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        tool_registry: ToolRegistry,
        model: str = "gpt-4o",
    ):
        self.client = openai_client
        self.registry = tool_registry
        self.model = model

    async def create_plan(
        self,
        request: str,
        context: list[dict[str, Any]],  # Retrieved chunks
        user_context: UserContext,
    ) -> ExecutionPlan:
        """Create an execution plan for a user request."""
        # Format tools for prompt
        tools = self.registry.list_tools()
        tools_desc = "\n".join([
            f"- {t.name}: {t.description} (category: {t.category.value})"
            for t in tools
        ])

        # Format context
        context_str = "\n\n".join([
            f"[{c.get('id', 'unknown')}] {c.get('content', '')[:500]}"
            for c in context[:10]
        ])

        prompt = self.PLANNING_PROMPT.format(
            tools_description=tools_desc,
            request=request,
            context=context_str if context else "No context available.",
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        plan_data = json.loads(response.choices[0].message.content)

        # Build plan steps
        steps = []
        for step_data in plan_data.get("steps", []):
            steps.append(PlanStep(
                step_id=step_data.get("step_id", f"step_{len(steps)}"),
                action=step_data.get("action", "respond"),
                tool_name=step_data.get("tool_name"),
                inputs=step_data.get("inputs", {}),
                justification_citations=step_data.get("justification_citations", []),
                depends_on=step_data.get("depends_on", []),
            ))

        plan_id = hashlib.sha256(
            f"{request}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        return ExecutionPlan(
            plan_id=plan_id,
            goal=plan_data.get("goal", request),
            steps=steps,
        )


class Executor:
    """
    Executes plans with guardrails and audit logging.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        tool_registry: ToolRegistry,
        guardrails: Guardrails,
        retriever: Any = None,  # HybridRetriever
    ):
        self.client = openai_client
        self.registry = tool_registry
        self.guardrails = guardrails
        self.retriever = retriever
        self.audit_log: list[dict[str, Any]] = []

    async def execute(
        self,
        plan: ExecutionPlan,
        user_context: UserContext,
        approval_callback: Callable[[PlanStep], Awaitable[bool]] | None = None,
    ) -> ExecutionResult:
        """
        Execute a plan.

        Args:
            plan: The execution plan
            user_context: Security context
            approval_callback: Optional callback for approval steps

        Returns:
            ExecutionResult with answer and audit trail
        """
        start_time = datetime.utcnow()
        self.audit_log = []
        actions_taken = []
        citations = []
        final_answer = None

        # Check for approval requirements
        for step in plan.steps:
            if step.tool_name:
                tool = self.registry.get(step.tool_name)
                if tool:
                    needs_approval, reason = self.guardrails.requires_approval(
                        tool, step.inputs, user_context
                    )
                    if needs_approval:
                        plan.requires_approval = True
                        plan.approval_reason = reason

        # If approval required, request it
        if plan.requires_approval and approval_callback:
            approved = await self._request_approval(plan, approval_callback)
            if not approved:
                return ExecutionResult(
                    plan_id=plan.plan_id,
                    status="rejected",
                    answer="Plan was rejected by user.",
                    citations=[],
                    actions_taken=[],
                    execution_time_ms=0,
                    cost_estimate_usd=0,
                    audit_log=self.audit_log,
                )

        # Execute steps in order
        step_results = {}

        for step in plan.steps:
            # Check dependencies
            for dep_id in step.depends_on:
                if dep_id not in step_results:
                    step.status = ActionStatus.FAILED
                    step.error = f"Dependency {dep_id} not completed"
                    continue

            try:
                step.status = ActionStatus.EXECUTING
                self._log_action("step_start", step)

                if step.action == "retrieve":
                    result = await self._execute_retrieve(step, user_context)

                elif step.action == "call_tool":
                    result = await self._execute_tool(step, user_context)
                    actions_taken.append({
                        "tool": step.tool_name,
                        "inputs": step.inputs,
                        "result": result,
                    })

                elif step.action == "analyze":
                    result = await self._execute_analyze(step, step_results)

                elif step.action == "respond":
                    result = await self._execute_respond(step, step_results, user_context)
                    final_answer = result.get("answer")
                    citations = result.get("citations", [])

                else:
                    result = {"error": f"Unknown action: {step.action}"}

                step.result = result
                step.status = ActionStatus.COMPLETED
                step_results[step.step_id] = result

                self._log_action("step_complete", step, result)

            except Exception as e:
                step.status = ActionStatus.FAILED
                step.error = str(e)
                self._log_action("step_failed", step, error=str(e))

        # Calculate timing
        end_time = datetime.utcnow()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return ExecutionResult(
            plan_id=plan.plan_id,
            status="completed" if final_answer else "failed",
            answer=final_answer,
            citations=citations,
            actions_taken=actions_taken,
            execution_time_ms=execution_time_ms,
            cost_estimate_usd=self._estimate_cost(),
            audit_log=self.audit_log,
        )

    async def _request_approval(
        self,
        plan: ExecutionPlan,
        callback: Callable[[PlanStep], Awaitable[bool]],
    ) -> bool:
        """Request approval for steps that need it."""
        for step in plan.steps:
            if step.tool_name:
                tool = self.registry.get(step.tool_name)
                if tool and tool.approval != ApprovalRequirement.NEVER:
                    approved = await callback(step)
                    if not approved:
                        self._log_action("approval_rejected", step)
                        return False
                    self._log_action("approval_granted", step)

        return True

    async def _execute_retrieve(
        self,
        step: PlanStep,
        user_context: UserContext,
    ) -> dict[str, Any]:
        """Execute a retrieval step."""
        if not self.retriever:
            return {"chunks": [], "error": "No retriever configured"}

        query = step.inputs.get("query", "")
        result = await self.retriever.retrieve(query, user_context)

        return {
            "chunks": [
                {"id": c.id, "content": c.content[:500], "score": c.final_score}
                for c in result.chunks
            ],
            "total": len(result.chunks),
        }

    async def _execute_tool(
        self,
        step: PlanStep,
        user_context: UserContext,
    ) -> dict[str, Any]:
        """Execute a tool call."""
        tool = self.registry.get(step.tool_name)
        if not tool:
            return {"error": f"Tool not found: {step.tool_name}"}

        # Check permissions
        allowed, reason = self.guardrails.check_permissions(tool, user_context)
        if not allowed:
            return {"error": f"Permission denied: {reason}"}

        # Validate inputs
        valid, reason = self.guardrails.validate_inputs(tool, step.inputs)
        if not valid:
            return {"error": f"Invalid inputs: {reason}"}

        # Check for injection in inputs
        for value in step.inputs.values():
            if isinstance(value, str):
                safe, reason = self.guardrails.check_injection(value)
                if not safe:
                    return {"error": f"Security check failed: {reason}"}

        # Execute tool
        if tool.handler:
            return await tool.handler(**step.inputs)
        else:
            # Placeholder for unimplemented tools
            return {"status": "mock", "message": f"Tool {tool.name} executed (mock)"}

    async def _execute_analyze(
        self,
        step: PlanStep,
        previous_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an analysis step."""
        # Gather inputs from previous steps
        analysis_input = step.inputs.get("data", {})
        for dep_id in step.depends_on:
            if dep_id in previous_results:
                analysis_input[dep_id] = previous_results[dep_id]

        # Use LLM for analysis
        prompt = f"""Analyze the following data and provide insights:

Data:
{json.dumps(analysis_input, indent=2)}

Analysis task: {step.inputs.get('task', 'Summarize the key findings')}

Provide a concise analysis."""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        return {"analysis": response.choices[0].message.content}

    async def _execute_respond(
        self,
        step: PlanStep,
        previous_results: dict[str, Any],
        user_context: UserContext,
    ) -> dict[str, Any]:
        """Generate final response with citations."""
        # Gather all context
        context_parts = []
        citations = []

        for step_id, result in previous_results.items():
            if "chunks" in result:
                for chunk in result["chunks"]:
                    context_parts.append(f"[{chunk['id']}]: {chunk['content']}")
                    citations.append({
                        "chunk_id": chunk["id"],
                        "step_id": step_id,
                    })
            elif "analysis" in result:
                context_parts.append(f"Analysis: {result['analysis']}")

        prompt = f"""Based on the following information, provide a grounded answer.

Context:
{chr(10).join(context_parts)}

User request: {step.inputs.get('original_request', '')}

Rules:
1. Only use information from the provided context
2. Cite sources using [chunk_id] format
3. If uncertain, say so
4. Be concise and professional

Provide your answer:"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        return {
            "answer": response.choices[0].message.content,
            "citations": citations,
        }

    def _log_action(
        self,
        action_type: str,
        step: PlanStep,
        result: Any = None,
        error: str | None = None,
    ):
        """Log an action for audit."""
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type,
            "step_id": step.step_id,
            "tool_name": step.tool_name,
            "inputs": step.inputs,
            "justification_citations": step.justification_citations,
            "result": result,
            "error": error,
        })

    def _estimate_cost(self) -> float:
        """Estimate cost of execution."""
        # Placeholder - would calculate based on token usage and tool calls
        return 0.01 * len(self.audit_log)


class AgentOrchestrator:
    """
    Main entry point for agentic workflows.

    Combines retrieval, planning, and execution into a unified interface.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        retriever: Any,  # HybridRetriever
        tool_registry: ToolRegistry | None = None,
    ):
        self.client = openai_client
        self.retriever = retriever

        self.registry = tool_registry or ToolRegistry()
        self.guardrails = Guardrails(self.registry)
        self.planner = Planner(openai_client, self.registry)
        self.executor = Executor(openai_client, self.registry, self.guardrails, retriever)

    async def process_request(
        self,
        request: str,
        user_context: UserContext,
        approval_callback: Callable[[PlanStep], Awaitable[bool]] | None = None,
    ) -> ExecutionResult:
        """
        Process a user request end-to-end.

        Args:
            request: User's natural language request
            user_context: Security context
            approval_callback: Optional callback for approval steps

        Returns:
            ExecutionResult with answer and audit trail
        """
        # Step 1: Retrieve relevant context
        retrieval_result = await self.retriever.retrieve(request, user_context)

        context = [
            {
                "id": c.id,
                "content": c.content,
                "doc_id": c.doc_id,
                "chunk_type": c.chunk_type,
            }
            for c in retrieval_result.chunks
        ]

        # Step 2: Create execution plan
        plan = await self.planner.create_plan(request, context, user_context)

        # Add original request to respond step
        for step in plan.steps:
            if step.action == "respond":
                step.inputs["original_request"] = request

        # Step 3: Execute plan
        result = await self.executor.execute(plan, user_context, approval_callback)

        return result
