"""
Governance Policy Engine

Implements automated policy enforcement for:
- Data security (tenant isolation, PII rules, content types)
- Operational policies (SLA targets, error budgets, throttling)
- Model safety (hallucination thresholds, citation coverage)
- Action safety (tool usage, approval requirements)

All rule triggers and actions are logged for compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from enum import Enum
import asyncio
import json
import re
from datetime import datetime
from abc import ABC, abstractmethod


class PolicyScope(Enum):
    """Where policies are enforced."""
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    AGENT_PLANNING = "agent_planning"
    TOOL_EXECUTION = "tool_execution"
    ANSWER_GENERATION = "answer_generation"
    ALL = "all"


class PolicyAction(Enum):
    """Actions to take when policy triggers."""
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"
    WARN = "warn"
    LOG_ONLY = "log_only"
    REQUIRE_APPROVAL = "require_approval"
    DEGRADE = "degrade"
    ESCALATE = "escalate"


class PolicySeverity(Enum):
    """Severity of policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PolicyRule:
    """A single governance policy rule."""
    rule_id: str
    name: str
    description: str
    scope: PolicyScope
    condition: str  # Expression to evaluate
    action: PolicyAction
    severity: PolicySeverity
    owner_group: str
    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PolicyContext:
    """Context for policy evaluation."""
    scope: PolicyScope
    tenant_id: str
    user_id: str
    request_id: str
    data: dict[str, Any]  # Context-specific data
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    rule_id: str
    triggered: bool
    action: PolicyAction
    severity: PolicySeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None


@dataclass
class PolicyEvaluationResult:
    """Aggregate result of all policy evaluations."""
    request_id: str
    scope: PolicyScope
    results: list[PolicyResult]
    overall_action: PolicyAction
    blocked: bool
    warnings: list[str]
    evaluation_time_ms: float


class ConditionEvaluator:
    """
    Evaluates policy conditions safely.

    Supports expressions like:
    - "chunk.contains_pii == true"
    - "response.citation_count < 1"
    - "cost.tokens_used > 10000"
    - "user.clearance_level not in ['restricted', 'confidential']"
    """

    # Safe operators
    OPERATORS = {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b,
        'contains': lambda a, b: b in a if isinstance(a, (str, list)) else False,
        'matches': lambda a, b: bool(re.search(b, a)) if isinstance(a, str) else False,
    }

    def evaluate(self, condition: str, context: PolicyContext) -> bool:
        """Evaluate a condition expression against context."""
        try:
            # Parse condition
            parsed = self._parse_condition(condition)
            if not parsed:
                return False

            left_value = self._resolve_value(parsed['left'], context)
            right_value = self._resolve_value(parsed['right'], context)
            operator = parsed['operator']

            if operator not in self.OPERATORS:
                return False

            return self.OPERATORS[operator](left_value, right_value)

        except Exception:
            return False

    def _parse_condition(self, condition: str) -> dict | None:
        """Parse a condition string into components."""
        # Handle 'not in' first
        if ' not in ' in condition:
            parts = condition.split(' not in ', 1)
            return {'left': parts[0].strip(), 'operator': 'not in', 'right': parts[1].strip()}

        # Then other operators
        for op in ['==', '!=', '>=', '<=', '>', '<', ' in ', ' contains ', ' matches ']:
            if op in condition:
                parts = condition.split(op, 1)
                return {
                    'left': parts[0].strip(),
                    'operator': op.strip(),
                    'right': parts[1].strip()
                }

        return None

    def _resolve_value(self, expr: str, context: PolicyContext) -> Any:
        """Resolve an expression to its value from context."""
        expr = expr.strip()

        # Handle literals
        if expr.lower() == 'true':
            return True
        if expr.lower() == 'false':
            return False
        if expr.startswith('"') or expr.startswith("'"):
            return expr[1:-1]
        if expr.startswith('[') and expr.endswith(']'):
            # Parse list literal
            items = expr[1:-1].split(',')
            return [i.strip().strip('"\'') for i in items]
        try:
            return int(expr)
        except ValueError:
            pass
        try:
            return float(expr)
        except ValueError:
            pass

        # Resolve from context.data using dot notation
        parts = expr.split('.')
        value = context.data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


class PolicyStore:
    """
    Stores and manages governance policies.
    """

    # Default enterprise policies
    DEFAULT_POLICIES = [
        # Data Security Policies
        PolicyRule(
            rule_id="pii_redaction_required",
            name="PII Redaction Required",
            description="Redact PII from chunks before indexing",
            scope=PolicyScope.INGESTION,
            condition="chunk.contains_pii == true",
            action=PolicyAction.REDACT,
            severity=PolicySeverity.ERROR,
            owner_group="Security",
        ),
        PolicyRule(
            rule_id="tenant_isolation",
            name="Tenant Isolation",
            description="Ensure no cross-tenant data access",
            scope=PolicyScope.RETRIEVAL,
            condition="chunk.tenant_id != user.tenant_id",
            action=PolicyAction.DENY,
            severity=PolicySeverity.CRITICAL,
            owner_group="Security",
        ),
        PolicyRule(
            rule_id="sensitivity_clearance",
            name="Sensitivity Clearance Check",
            description="Block access to docs above user clearance",
            scope=PolicyScope.RETRIEVAL,
            condition="chunk.sensitivity not in user.allowed_sensitivities",
            action=PolicyAction.DENY,
            severity=PolicySeverity.ERROR,
            owner_group="Security",
        ),

        # Model Safety Policies
        PolicyRule(
            rule_id="citation_required",
            name="Citation Required",
            description="All claims must have citations",
            scope=PolicyScope.ANSWER_GENERATION,
            condition="response.citation_count < 1",
            action=PolicyAction.DENY,
            severity=PolicySeverity.ERROR,
            owner_group="AI Platform",
            parameters={"min_citations": 1},
        ),
        PolicyRule(
            rule_id="groundedness_threshold",
            name="Groundedness Threshold",
            description="Block responses with low groundedness",
            scope=PolicyScope.ANSWER_GENERATION,
            condition="response.groundedness_score < 0.8",
            action=PolicyAction.DENY,
            severity=PolicySeverity.ERROR,
            owner_group="AI Platform",
            parameters={"threshold": 0.8},
        ),
        PolicyRule(
            rule_id="hallucination_detection",
            name="Hallucination Detection",
            description="Flag potential hallucinations",
            scope=PolicyScope.ANSWER_GENERATION,
            condition="response.hallucination_risk == high",
            action=PolicyAction.ESCALATE,
            severity=PolicySeverity.WARNING,
            owner_group="AI Platform",
        ),

        # Operational Policies
        PolicyRule(
            rule_id="cost_limit_per_query",
            name="Cost Limit Per Query",
            description="Limit tokens per single query",
            scope=PolicyScope.ANSWER_GENERATION,
            condition="cost.tokens_used > 50000",
            action=PolicyAction.DEGRADE,
            severity=PolicySeverity.WARNING,
            owner_group="Platform Ops",
            parameters={"max_tokens": 50000},
        ),
        PolicyRule(
            rule_id="tenant_daily_budget",
            name="Tenant Daily Budget",
            description="Enforce daily spending limits",
            scope=PolicyScope.ALL,
            condition="tenant.daily_spend > tenant.daily_budget",
            action=PolicyAction.DEGRADE,
            severity=PolicySeverity.WARNING,
            owner_group="Finance",
        ),

        # Action Safety Policies
        PolicyRule(
            rule_id="write_tool_approval",
            name="Write Tool Approval Required",
            description="Require approval for write operations",
            scope=PolicyScope.TOOL_EXECUTION,
            condition="tool.category == write",
            action=PolicyAction.REQUIRE_APPROVAL,
            severity=PolicySeverity.WARNING,
            owner_group="Security",
        ),
        PolicyRule(
            rule_id="external_api_restriction",
            name="External API Restriction",
            description="Block calls to non-approved APIs",
            scope=PolicyScope.TOOL_EXECUTION,
            condition="tool.endpoint not in approved_endpoints",
            action=PolicyAction.DENY,
            severity=PolicySeverity.ERROR,
            owner_group="Security",
        ),
    ]

    def __init__(self, cosmos_client: Any = None):
        self.cosmos_client = cosmos_client
        self._policies: dict[str, PolicyRule] = {}
        self._load_default_policies()

    def _load_default_policies(self):
        """Load default enterprise policies."""
        for policy in self.DEFAULT_POLICIES:
            self._policies[policy.rule_id] = policy

    def get_policies_for_scope(self, scope: PolicyScope) -> list[PolicyRule]:
        """Get all enabled policies for a scope."""
        return [
            p for p in self._policies.values()
            if p.enabled and (p.scope == scope or p.scope == PolicyScope.ALL)
        ]

    def add_policy(self, policy: PolicyRule):
        """Add or update a policy."""
        policy.updated_at = datetime.utcnow().isoformat()
        self._policies[policy.rule_id] = policy

    def disable_policy(self, rule_id: str):
        """Disable a policy."""
        if rule_id in self._policies:
            self._policies[rule_id].enabled = False

    def get_policy(self, rule_id: str) -> PolicyRule | None:
        """Get a specific policy."""
        return self._policies.get(rule_id)


class PolicyEngine:
    """
    Main policy engine that evaluates and enforces governance rules.
    """

    def __init__(
        self,
        policy_store: PolicyStore,
        audit_logger: Any = None,  # ComplianceAuditLogger
    ):
        self.store = policy_store
        self.evaluator = ConditionEvaluator()
        self.audit_logger = audit_logger

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyEvaluationResult:
        """
        Evaluate all applicable policies for a context.

        Returns aggregate result with overall action.
        """
        start_time = datetime.utcnow()

        # Get applicable policies
        policies = self.store.get_policies_for_scope(context.scope)

        results = []
        warnings = []
        blocked = False
        overall_action = PolicyAction.ALLOW

        for policy in policies:
            result = self._evaluate_policy(policy, context)
            results.append(result)

            if result.triggered:
                # Log the trigger
                if self.audit_logger:
                    await self.audit_logger.log_policy_trigger(
                        policy=policy,
                        context=context,
                        result=result,
                    )

                # Determine overall action (most restrictive wins)
                if result.action == PolicyAction.DENY:
                    blocked = True
                    overall_action = PolicyAction.DENY
                elif result.action == PolicyAction.REQUIRE_APPROVAL and not blocked:
                    overall_action = PolicyAction.REQUIRE_APPROVAL
                elif result.action == PolicyAction.ESCALATE:
                    warnings.append(f"[{policy.name}] {result.message}")
                elif result.action == PolicyAction.WARN:
                    warnings.append(f"[{policy.name}] {result.message}")

        end_time = datetime.utcnow()
        evaluation_time_ms = (end_time - start_time).total_seconds() * 1000

        return PolicyEvaluationResult(
            request_id=context.request_id,
            scope=context.scope,
            results=results,
            overall_action=overall_action,
            blocked=blocked,
            warnings=warnings,
            evaluation_time_ms=evaluation_time_ms,
        )

    def _evaluate_policy(
        self,
        policy: PolicyRule,
        context: PolicyContext,
    ) -> PolicyResult:
        """Evaluate a single policy."""
        triggered = self.evaluator.evaluate(policy.condition, context)

        if triggered:
            return PolicyResult(
                rule_id=policy.rule_id,
                triggered=True,
                action=policy.action,
                severity=policy.severity,
                message=f"Policy '{policy.name}' triggered: {policy.description}",
                details={
                    "condition": policy.condition,
                    "context_data": context.data,
                },
                remediation=self._get_remediation(policy),
            )

        return PolicyResult(
            rule_id=policy.rule_id,
            triggered=False,
            action=PolicyAction.ALLOW,
            severity=PolicySeverity.INFO,
            message="Policy not triggered",
        )

    def _get_remediation(self, policy: PolicyRule) -> str:
        """Get remediation guidance for a policy."""
        remediations = {
            "pii_redaction_required": "PII detected will be automatically redacted. Review the redacted content.",
            "tenant_isolation": "Access denied due to tenant isolation. Verify user has correct tenant assignment.",
            "sensitivity_clearance": "User clearance level insufficient. Request elevated access if needed.",
            "citation_required": "Add citations to support all claims in the response.",
            "groundedness_threshold": "Response lacks sufficient grounding. Retrieve more evidence.",
            "hallucination_detection": "Potential hallucination detected. Verify claims against sources.",
            "cost_limit_per_query": "Query exceeds cost limit. Response will be truncated or use smaller model.",
            "write_tool_approval": "Write operation requires user approval before execution.",
        }
        return remediations.get(policy.rule_id, "Contact platform team for guidance.")


class PolicyEnforcer:
    """
    Enforces policy decisions by taking appropriate actions.
    """

    def __init__(self, policy_engine: PolicyEngine):
        self.engine = policy_engine
        self._action_handlers: dict[PolicyAction, Callable] = {
            PolicyAction.ALLOW: self._handle_allow,
            PolicyAction.DENY: self._handle_deny,
            PolicyAction.REDACT: self._handle_redact,
            PolicyAction.WARN: self._handle_warn,
            PolicyAction.REQUIRE_APPROVAL: self._handle_require_approval,
            PolicyAction.DEGRADE: self._handle_degrade,
            PolicyAction.ESCALATE: self._handle_escalate,
        }

    async def enforce(
        self,
        context: PolicyContext,
        data: Any,
    ) -> tuple[Any, PolicyEvaluationResult]:
        """
        Evaluate policies and enforce the result.

        Returns modified data and evaluation result.
        """
        result = await self.engine.evaluate(context)

        # Apply actions for triggered policies
        modified_data = data
        for policy_result in result.results:
            if policy_result.triggered:
                handler = self._action_handlers.get(policy_result.action)
                if handler:
                    modified_data = await handler(modified_data, policy_result, context)

        return modified_data, result

    async def _handle_allow(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Allow action - pass through."""
        return data

    async def _handle_deny(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Deny action - raise exception or return error."""
        raise PolicyViolationError(result.message, result.rule_id)

    async def _handle_redact(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Redact sensitive information."""
        if isinstance(data, dict) and 'content' in data:
            data['content'] = self._redact_pii(data['content'])
            data['redacted'] = True
        return data

    async def _handle_warn(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Log warning but allow."""
        # Warning is logged by the engine, just pass through
        return data

    async def _handle_require_approval(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Mark data as requiring approval."""
        if isinstance(data, dict):
            data['requires_approval'] = True
            data['approval_reason'] = result.message
        return data

    async def _handle_degrade(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Degrade service quality."""
        if isinstance(data, dict):
            data['degraded'] = True
            data['degradation_reason'] = result.message
        return data

    async def _handle_escalate(self, data: Any, result: PolicyResult, context: PolicyContext) -> Any:
        """Escalate for review."""
        if isinstance(data, dict):
            data['escalated'] = True
            data['escalation_reason'] = result.message
        return data

    def _redact_pii(self, text: str) -> str:
        """Redact common PII patterns."""
        import re

        patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '<<SSN_REDACTED>>'),  # SSN
            (r'\b\d{16}\b', '<<CARD_REDACTED>>'),  # Credit card
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<<EMAIL_REDACTED>>'),  # Email
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '<<PHONE_REDACTED>>'),  # Phone
        ]

        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        return result


class PolicyViolationError(Exception):
    """Exception raised when a policy is violated."""

    def __init__(self, message: str, rule_id: str):
        self.message = message
        self.rule_id = rule_id
        super().__init__(message)


class ComplianceAuditLogger:
    """
    Logs all policy-related events for compliance.
    """

    def __init__(self, cosmos_client: Any = None):
        self.cosmos_client = cosmos_client

    async def log_policy_trigger(
        self,
        policy: PolicyRule,
        context: PolicyContext,
        result: PolicyResult,
    ):
        """Log a policy trigger event."""
        event = {
            "event_type": "policy_trigger",
            "timestamp": datetime.utcnow().isoformat(),
            "rule_id": policy.rule_id,
            "rule_name": policy.name,
            "scope": context.scope.value,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "action_taken": result.action.value,
            "severity": result.severity.value,
            "message": result.message,
            "details": result.details,
        }

        # Store in Cosmos DB if available
        if self.cosmos_client:
            # Implementation would store to Cosmos
            pass

        # Also log to App Insights / stdout
        print(f"[POLICY] {event}")

    async def log_policy_evaluation(
        self,
        result: PolicyEvaluationResult,
    ):
        """Log overall policy evaluation."""
        event = {
            "event_type": "policy_evaluation",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": result.request_id,
            "scope": result.scope.value,
            "overall_action": result.overall_action.value,
            "blocked": result.blocked,
            "warnings_count": len(result.warnings),
            "evaluation_time_ms": result.evaluation_time_ms,
            "triggered_rules": [
                r.rule_id for r in result.results if r.triggered
            ],
        }

        if self.cosmos_client:
            pass

        print(f"[POLICY_EVAL] {event}")
