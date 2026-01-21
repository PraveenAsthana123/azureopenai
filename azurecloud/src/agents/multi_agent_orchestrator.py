"""
Multi-Agent Orchestrator for Enterprise RAG Platform (Phase 11).

Implements a sophisticated multi-agent system with:
- Coordinator agent for task planning and delegation
- Specialized agents (Retriever, Table Analyst, Vision, Compliance)
- Agent communication protocols
- Conflict resolution and result synthesis
- Human-in-the-loop checkpoints
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from collections import defaultdict

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of specialized agents."""
    COORDINATOR = "coordinator"
    RETRIEVER = "retriever"
    TABLE_ANALYST = "table_analyst"
    VISION = "vision"
    COMPLIANCE = "compliance"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"


class TaskStatus(str, Enum):
    """Status of agent tasks."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Types of inter-agent messages."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    QUERY = "query"
    RESPONSE = "response"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"
    CHECKPOINT = "checkpoint"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"


@dataclass
class AgentMessage:
    """Message exchanged between agents."""
    id: str
    sender: str
    recipient: str
    message_type: MessageType
    content: dict
    timestamp: datetime
    correlation_id: str
    requires_response: bool = False
    priority: int = 5  # 1-10, higher is more urgent

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
            "priority": self.priority
        }


@dataclass
class AgentTask:
    """Task assigned to an agent."""
    id: str
    task_type: str
    description: str
    assigned_to: str
    status: TaskStatus
    created_at: datetime
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retries: int = 0
    max_retries: int = 3
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "dependencies": self.dependencies,
            "timeout_seconds": self.timeout_seconds,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "error": self.error
        }


@dataclass
class WorkflowPlan:
    """Plan for executing a multi-agent workflow."""
    id: str
    query: str
    tenant_id: str
    user_id: str
    tasks: list[AgentTask]
    execution_order: list[list[str]]  # Groups of parallel task IDs
    created_at: datetime
    status: str = "pending"
    checkpoints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "tasks": [t.to_dict() for t in self.tasks],
            "execution_order": self.execution_order,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "checkpoints": self.checkpoints
        }


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        openai_client: AsyncAzureOpenAI,
        model: str = "gpt-4o"
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.openai_client = openai_client
        self.model = model
        self.capabilities: list[str] = []
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @abstractmethod
    async def process_task(self, task: AgentTask) -> dict:
        """Process an assigned task."""
        pass

    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        """Check if agent can handle a task type."""
        pass

    async def receive_message(self, message: AgentMessage) -> None:
        """Receive a message from another agent."""
        await self._message_queue.put(message)

    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: dict,
        correlation_id: str,
        requires_response: bool = False
    ) -> AgentMessage:
        """Create a message to send to another agent."""
        return AgentMessage(
            id=self._generate_message_id(),
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            requires_response=requires_response
        )

    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        data = f"{self.agent_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class CoordinatorAgent(BaseAgent):
    """
    Coordinator agent that plans and delegates tasks.
    Acts as the central orchestrator for multi-agent workflows.
    """

    def __init__(self, openai_client: AsyncAzureOpenAI, model: str = "gpt-4o"):
        super().__init__(
            agent_id="coordinator",
            agent_type=AgentType.COORDINATOR,
            openai_client=openai_client,
            model=model
        )
        self.capabilities = ["planning", "delegation", "synthesis", "conflict_resolution"]
        self._registered_agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self._registered_agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.agent_type.value})")

    async def create_plan(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        context: dict = None
    ) -> WorkflowPlan:
        """Create an execution plan for a query."""
        plan_id = hashlib.sha256(
            f"{query}:{tenant_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        # Use LLM to decompose query into tasks
        task_plan = await self._decompose_query(query, context or {})

        tasks = []
        task_id_map = {}

        for i, task_def in enumerate(task_plan["tasks"]):
            task_id = f"{plan_id}-{i}"
            task_id_map[task_def.get("name", f"task_{i}")] = task_id

            # Find appropriate agent
            agent_id = self._find_agent_for_task(task_def["type"])

            task = AgentTask(
                id=task_id,
                task_type=task_def["type"],
                description=task_def["description"],
                assigned_to=agent_id,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                input_data=task_def.get("input", {}),
                dependencies=[
                    task_id_map.get(dep, dep)
                    for dep in task_def.get("dependencies", [])
                ]
            )
            tasks.append(task)

        # Determine execution order (parallel groups)
        execution_order = self._determine_execution_order(tasks)

        plan = WorkflowPlan(
            id=plan_id,
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            tasks=tasks,
            execution_order=execution_order,
            created_at=datetime.utcnow(),
            checkpoints=task_plan.get("checkpoints", [])
        )

        logger.info(f"Created plan {plan_id} with {len(tasks)} tasks")
        return plan

    async def _decompose_query(self, query: str, context: dict) -> dict:
        """Use LLM to decompose query into tasks."""
        available_agents = [
            {"id": a.agent_id, "type": a.agent_type.value, "capabilities": a.capabilities}
            for a in self._registered_agents.values()
        ]

        prompt = f"""Decompose this user query into tasks for a multi-agent system.

Available agents:
{json.dumps(available_agents, indent=2)}

User query: {query}

Additional context:
{json.dumps(context, indent=2)}

Return a JSON plan:
{{
    "tasks": [
        {{
            "name": "task_name",
            "type": "retrieval|table_analysis|vision_analysis|compliance_check|synthesis",
            "description": "what this task does",
            "input": {{}},
            "dependencies": ["list of task names this depends on"]
        }}
    ],
    "checkpoints": ["task names requiring human approval"],
    "reasoning": "why this decomposition"
}}

Rules:
1. Start with retrieval tasks to gather context
2. Use specialized agents for specific content types
3. Always end with synthesis to combine results
4. Add compliance check for sensitive queries
5. Mark high-risk tasks as checkpoints"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def _find_agent_for_task(self, task_type: str) -> str:
        """Find the best agent for a task type."""
        type_to_agent = {
            "retrieval": "retriever",
            "table_analysis": "table_analyst",
            "vision_analysis": "vision",
            "compliance_check": "compliance",
            "synthesis": "synthesizer",
            "validation": "validator"
        }

        agent_id = type_to_agent.get(task_type, "retriever")

        if agent_id not in self._registered_agents:
            # Fallback to retriever
            return "retriever"

        return agent_id

    def _determine_execution_order(self, tasks: list[AgentTask]) -> list[list[str]]:
        """Determine parallel execution groups based on dependencies."""
        task_map = {t.id: t for t in tasks}
        completed = set()
        order = []

        while len(completed) < len(tasks):
            # Find tasks whose dependencies are all completed
            ready = []
            for task in tasks:
                if task.id in completed:
                    continue
                deps_met = all(d in completed for d in task.dependencies)
                if deps_met:
                    ready.append(task.id)

            if not ready:
                # Circular dependency or error
                remaining = [t.id for t in tasks if t.id not in completed]
                order.append(remaining)
                break

            order.append(ready)
            completed.update(ready)

        return order

    async def process_task(self, task: AgentTask) -> dict:
        """Coordinator processes planning/synthesis tasks."""
        if task.task_type == "synthesis":
            return await self._synthesize_results(task)
        return {"status": "unsupported_task_type"}

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["planning", "synthesis", "conflict_resolution"]

    async def _synthesize_results(self, task: AgentTask) -> dict:
        """Synthesize results from multiple agents."""
        results = task.input_data.get("agent_results", [])

        prompt = f"""Synthesize these results from multiple agents into a coherent response.

Query: {task.input_data.get('original_query', '')}

Agent Results:
{json.dumps(results, indent=2)}

Create a unified response that:
1. Combines relevant information from all sources
2. Resolves any conflicts between agents
3. Cites sources appropriately
4. Highlights areas of uncertainty

Return JSON:
{{
    "response": "synthesized response",
    "sources": ["list of source citations"],
    "confidence": 0.0-1.0,
    "conflicts_resolved": ["list of conflicts and resolutions"],
    "limitations": ["areas of uncertainty or missing info"]
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)


class RetrieverAgent(BaseAgent):
    """Agent specialized in document retrieval."""

    def __init__(self, openai_client: AsyncAzureOpenAI, search_endpoint: str):
        super().__init__(
            agent_id="retriever",
            agent_type=AgentType.RETRIEVER,
            openai_client=openai_client,
            model="gpt-4o-mini"
        )
        self.search_endpoint = search_endpoint
        self.capabilities = ["semantic_search", "keyword_search", "hybrid_search", "filtering"]

    async def process_task(self, task: AgentTask) -> dict:
        """Execute retrieval task."""
        query = task.input_data.get("query", "")
        filters = task.input_data.get("filters", {})
        top_k = task.input_data.get("top_k", 10)

        # This would integrate with the hybrid retriever
        # Simulated response for demonstration
        results = await self._execute_search(query, filters, top_k)

        return {
            "status": "success",
            "documents": results,
            "query": query,
            "result_count": len(results)
        }

    async def _execute_search(
        self,
        query: str,
        filters: dict,
        top_k: int
    ) -> list[dict]:
        """Execute hybrid search."""
        # Integration point with HybridRetriever
        # Returns mock data for demonstration
        return [
            {
                "id": f"doc_{i}",
                "content": f"Sample content for query: {query}",
                "score": 0.9 - (i * 0.1),
                "metadata": {"source": f"document_{i}.pdf"}
            }
            for i in range(min(top_k, 5))
        ]

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["retrieval", "search", "document_lookup"]


class TableAnalystAgent(BaseAgent):
    """Agent specialized in table and structured data analysis."""

    def __init__(self, openai_client: AsyncAzureOpenAI):
        super().__init__(
            agent_id="table_analyst",
            agent_type=AgentType.TABLE_ANALYST,
            openai_client=openai_client,
            model="gpt-4o"
        )
        self.capabilities = ["table_extraction", "data_aggregation", "trend_analysis", "comparison"]

    async def process_task(self, task: AgentTask) -> dict:
        """Analyze table data."""
        tables = task.input_data.get("tables", [])
        question = task.input_data.get("question", "")

        if not tables:
            return {"status": "no_tables", "answer": None}

        analysis = await self._analyze_tables(tables, question)
        return {
            "status": "success",
            "analysis": analysis,
            "tables_analyzed": len(tables)
        }

    async def _analyze_tables(self, tables: list[dict], question: str) -> dict:
        """Use LLM to analyze table data."""
        tables_text = "\n\n".join([
            f"Table {i+1}:\n{json.dumps(t, indent=2)}"
            for i, t in enumerate(tables[:5])
        ])

        prompt = f"""Analyze these tables to answer the question.

Tables:
{tables_text}

Question: {question}

Provide:
1. Direct answer to the question
2. Supporting data points
3. Any calculations performed
4. Confidence level

Return JSON:
{{
    "answer": "answer to the question",
    "supporting_data": [{{}}],
    "calculations": "any calculations",
    "confidence": 0.0-1.0,
    "reasoning": "how you arrived at the answer"
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["table_analysis", "data_analysis", "aggregation"]


class VisionAgent(BaseAgent):
    """Agent specialized in image and diagram analysis."""

    def __init__(self, openai_client: AsyncAzureOpenAI):
        super().__init__(
            agent_id="vision",
            agent_type=AgentType.VISION,
            openai_client=openai_client,
            model="gpt-4o"
        )
        self.capabilities = ["image_analysis", "diagram_interpretation", "chart_reading", "ocr"]

    async def process_task(self, task: AgentTask) -> dict:
        """Analyze visual content."""
        images = task.input_data.get("images", [])
        question = task.input_data.get("question", "")

        if not images:
            return {"status": "no_images", "analysis": None}

        results = []
        for image in images[:5]:  # Limit to 5 images
            analysis = await self._analyze_image(image, question)
            results.append(analysis)

        return {
            "status": "success",
            "analyses": results,
            "images_processed": len(results)
        }

    async def _analyze_image(self, image: dict, question: str) -> dict:
        """Analyze a single image using vision model."""
        image_url = image.get("url") or image.get("base64")

        if not image_url:
            return {"error": "no_image_data"}

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this image to answer: {question}\n\nProvide structured analysis including key elements, data points, and relevance to the question."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=1000
            )

            return {
                "image_id": image.get("id", "unknown"),
                "analysis": response.choices[0].message.content,
                "status": "success"
            }
        except Exception as e:
            return {
                "image_id": image.get("id", "unknown"),
                "error": str(e),
                "status": "failed"
            }

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["vision_analysis", "image_analysis", "diagram_interpretation"]


class ComplianceAgent(BaseAgent):
    """Agent specialized in compliance and policy checking."""

    def __init__(self, openai_client: AsyncAzureOpenAI, policy_engine):
        super().__init__(
            agent_id="compliance",
            agent_type=AgentType.COMPLIANCE,
            openai_client=openai_client,
            model="gpt-4o-mini"
        )
        self.policy_engine = policy_engine
        self.capabilities = ["pii_detection", "policy_check", "access_validation", "audit"]

    async def process_task(self, task: AgentTask) -> dict:
        """Check compliance of content or action."""
        content = task.input_data.get("content", "")
        action = task.input_data.get("action", "read")
        context = task.input_data.get("context", {})

        # Run compliance checks
        checks = await self._run_compliance_checks(content, action, context)

        return {
            "status": "success",
            "compliant": all(c["passed"] for c in checks),
            "checks": checks,
            "recommendations": [c["recommendation"] for c in checks if not c["passed"]]
        }

    async def _run_compliance_checks(
        self,
        content: str,
        action: str,
        context: dict
    ) -> list[dict]:
        """Run various compliance checks."""
        checks = []

        # PII check
        pii_result = await self._check_pii(content)
        checks.append({
            "name": "pii_check",
            "passed": not pii_result["contains_pii"],
            "details": pii_result,
            "recommendation": "Redact PII before sharing" if pii_result["contains_pii"] else None
        })

        # Policy check (if policy engine available)
        if self.policy_engine:
            policy_result = await self._check_policies(action, context)
            checks.append({
                "name": "policy_check",
                "passed": policy_result["allowed"],
                "details": policy_result,
                "recommendation": policy_result.get("recommendation")
            })

        # Sensitivity check
        sensitivity = await self._assess_sensitivity(content)
        checks.append({
            "name": "sensitivity_check",
            "passed": sensitivity["level"] != "restricted",
            "details": sensitivity,
            "recommendation": sensitivity.get("recommendation")
        })

        return checks

    async def _check_pii(self, content: str) -> dict:
        """Check for PII in content."""
        prompt = f"""Analyze this content for PII (Personally Identifiable Information).

Content:
{content[:2000]}

Return JSON:
{{
    "contains_pii": true/false,
    "pii_types": ["list of PII types found"],
    "locations": ["approximate locations in text"],
    "risk_level": "none|low|medium|high"
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    async def _check_policies(self, action: str, context: dict) -> dict:
        """Check action against policies."""
        # Integration with PolicyEngine
        return {"allowed": True, "policies_checked": 0}

    async def _assess_sensitivity(self, content: str) -> dict:
        """Assess content sensitivity level."""
        prompt = f"""Assess the sensitivity level of this content.

Content:
{content[:1000]}

Return JSON:
{{
    "level": "public|internal|confidential|restricted",
    "factors": ["factors affecting sensitivity"],
    "recommendation": "handling recommendation if sensitive"
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["compliance_check", "pii_detection", "policy_validation"]


class SynthesizerAgent(BaseAgent):
    """Agent specialized in synthesizing information from multiple sources."""

    def __init__(self, openai_client: AsyncAzureOpenAI):
        super().__init__(
            agent_id="synthesizer",
            agent_type=AgentType.SYNTHESIZER,
            openai_client=openai_client,
            model="gpt-4o"
        )
        self.capabilities = ["synthesis", "summarization", "conflict_resolution", "citation"]

    async def process_task(self, task: AgentTask) -> dict:
        """Synthesize information from multiple sources."""
        sources = task.input_data.get("sources", [])
        query = task.input_data.get("query", "")
        format_type = task.input_data.get("format", "comprehensive")

        synthesis = await self._synthesize(sources, query, format_type)

        return {
            "status": "success",
            "synthesis": synthesis,
            "source_count": len(sources)
        }

    async def _synthesize(
        self,
        sources: list[dict],
        query: str,
        format_type: str
    ) -> dict:
        """Synthesize information from sources."""
        sources_text = "\n\n".join([
            f"Source {i+1} ({s.get('agent', 'unknown')}):\n{json.dumps(s.get('content', s), indent=2)}"
            for i, s in enumerate(sources)
        ])

        prompt = f"""Synthesize information from multiple sources to answer the query.

Query: {query}

Sources:
{sources_text}

Format: {format_type}

Create a response that:
1. Directly answers the query
2. Integrates information from all relevant sources
3. Notes any conflicts and how they were resolved
4. Includes proper citations
5. Acknowledges limitations or gaps

Return JSON:
{{
    "answer": "comprehensive answer",
    "key_points": ["main points"],
    "citations": [{{"source_id": "id", "claim": "what it supports"}}],
    "conflicts": [{{"topic": "", "resolution": ""}}],
    "confidence": 0.0-1.0,
    "limitations": ["gaps or uncertainties"]
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def can_handle(self, task_type: str) -> bool:
        return task_type in ["synthesis", "summarization", "response_generation"]


class MessageBus:
    """Message bus for inter-agent communication."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._message_log: list[AgentMessage] = []
        self._pending_responses: dict[str, asyncio.Future] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent with the message bus."""
        self._agents[agent.agent_id] = agent

    async def send(self, message: AgentMessage) -> None:
        """Send a message to an agent."""
        self._message_log.append(message)

        recipient = self._agents.get(message.recipient)
        if recipient:
            await recipient.receive_message(message)

        if message.requires_response:
            future = asyncio.Future()
            self._pending_responses[message.id] = future

    async def broadcast(
        self,
        sender: str,
        message_type: MessageType,
        content: dict,
        correlation_id: str
    ) -> None:
        """Broadcast message to all agents."""
        for agent_id in self._agents:
            if agent_id != sender:
                message = AgentMessage(
                    id=hashlib.sha256(f"{sender}:{agent_id}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16],
                    sender=sender,
                    recipient=agent_id,
                    message_type=message_type,
                    content=content,
                    timestamp=datetime.utcnow(),
                    correlation_id=correlation_id
                )
                await self.send(message)

    def get_message_log(self, correlation_id: str = None) -> list[AgentMessage]:
        """Get message log, optionally filtered by correlation ID."""
        if correlation_id:
            return [m for m in self._message_log if m.correlation_id == correlation_id]
        return self._message_log


class MultiAgentOrchestrator:
    """
    Main orchestrator for multi-agent workflows.
    Coordinates planning, execution, and synthesis across agents.
    """

    def __init__(
        self,
        cosmos_endpoint: str,
        openai_endpoint: str,
        openai_api_key: str,
        search_endpoint: str,
        openai_api_version: str = "2024-02-15-preview"
    ):
        self.cosmos_endpoint = cosmos_endpoint
        self.openai_endpoint = openai_endpoint
        self.openai_api_key = openai_api_key
        self.search_endpoint = search_endpoint
        self.openai_api_version = openai_api_version

        self._cosmos_client: Optional[CosmosClient] = None
        self._openai_client: Optional[AsyncAzureOpenAI] = None

        self.coordinator: Optional[CoordinatorAgent] = None
        self.message_bus: Optional[MessageBus] = None
        self._agents: dict[str, BaseAgent] = {}

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the orchestrator and all agents."""
        if self._initialized:
            return

        credential = DefaultAzureCredential()
        self._cosmos_client = CosmosClient(self.cosmos_endpoint, credential=credential)
        self._openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_api_key,
            api_version=self.openai_api_version
        )

        # Initialize message bus
        self.message_bus = MessageBus()

        # Initialize coordinator
        self.coordinator = CoordinatorAgent(self._openai_client)
        self.message_bus.register(self.coordinator)

        # Initialize specialized agents
        retriever = RetrieverAgent(self._openai_client, self.search_endpoint)
        table_analyst = TableAnalystAgent(self._openai_client)
        vision = VisionAgent(self._openai_client)
        compliance = ComplianceAgent(self._openai_client, None)  # Policy engine injected later
        synthesizer = SynthesizerAgent(self._openai_client)

        # Register all agents
        for agent in [retriever, table_analyst, vision, compliance, synthesizer]:
            self._agents[agent.agent_id] = agent
            self.coordinator.register_agent(agent)
            self.message_bus.register(agent)

        self._initialized = True
        logger.info("Multi-agent orchestrator initialized")

    async def execute_query(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        context: dict = None,
        require_approval: bool = False
    ) -> dict:
        """Execute a query using the multi-agent system."""
        if not self._initialized:
            await self.initialize()

        # Create execution plan
        plan = await self.coordinator.create_plan(query, tenant_id, user_id, context)

        # Execute plan
        result = await self._execute_plan(plan, require_approval)

        return {
            "plan_id": plan.id,
            "query": query,
            "result": result,
            "tasks_executed": len(plan.tasks),
            "execution_order": plan.execution_order
        }

    async def _execute_plan(
        self,
        plan: WorkflowPlan,
        require_approval: bool
    ) -> dict:
        """Execute a workflow plan."""
        task_results: dict[str, dict] = {}
        plan.status = "running"

        for task_group in plan.execution_order:
            # Execute tasks in parallel within each group
            group_tasks = [
                t for t in plan.tasks if t.id in task_group
            ]

            # Check for checkpoints requiring approval
            checkpoint_tasks = [t for t in group_tasks if t.id in plan.checkpoints]
            if checkpoint_tasks and require_approval:
                # Wait for approval (in production, this would be async)
                logger.info(f"Checkpoint reached: {[t.id for t in checkpoint_tasks]}")

            # Execute group in parallel
            results = await asyncio.gather(*[
                self._execute_task(task, task_results)
                for task in group_tasks
            ], return_exceptions=True)

            # Collect results
            for task, result in zip(group_tasks, results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    task_results[task.id] = {"error": str(result)}
                else:
                    task.status = TaskStatus.COMPLETED
                    task.output_data = result
                    task_results[task.id] = result

        plan.status = "completed"

        # Synthesize final result
        synthesis_task = AgentTask(
            id=f"{plan.id}-synthesis",
            task_type="synthesis",
            description="Synthesize all agent results",
            assigned_to="synthesizer",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            input_data={
                "query": plan.query,
                "sources": [
                    {"task_id": tid, "content": result, "agent": self._get_task_agent(plan, tid)}
                    for tid, result in task_results.items()
                ]
            }
        )

        final_result = await self._execute_task(synthesis_task, task_results)

        return {
            "synthesis": final_result,
            "task_results": task_results
        }

    async def _execute_task(
        self,
        task: AgentTask,
        prior_results: dict[str, dict]
    ) -> dict:
        """Execute a single task."""
        agent = self._agents.get(task.assigned_to)
        if not agent:
            return {"error": f"Agent not found: {task.assigned_to}"}

        # Inject dependencies into task input
        for dep_id in task.dependencies:
            if dep_id in prior_results:
                task.input_data[f"dep_{dep_id}"] = prior_results[dep_id]

        task.status = TaskStatus.RUNNING

        try:
            result = await asyncio.wait_for(
                agent.process_task(task),
                timeout=task.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            return {"error": "Task timed out", "timeout_seconds": task.timeout_seconds}
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            return {"error": str(e)}

    def _get_task_agent(self, plan: WorkflowPlan, task_id: str) -> str:
        """Get the agent ID for a task."""
        for task in plan.tasks:
            if task.id == task_id:
                return task.assigned_to
        return "unknown"

    async def close(self) -> None:
        """Close connections."""
        if self._cosmos_client:
            await self._cosmos_client.close()
        if self._openai_client:
            await self._openai_client.close()


# Example usage
async def main():
    """Example usage of multi-agent orchestrator."""
    orchestrator = MultiAgentOrchestrator(
        cosmos_endpoint="https://your-cosmos.documents.azure.com:443/",
        openai_endpoint="https://your-openai.openai.azure.com/",
        openai_api_key="your-api-key",
        search_endpoint="https://your-search.search.windows.net"
    )

    await orchestrator.initialize()

    # Execute a complex query
    result = await orchestrator.execute_query(
        query="Compare Q3 and Q4 sales figures from the financial report and summarize key trends",
        tenant_id="tenant-123",
        user_id="user-456",
        context={"document_types": ["financial_report", "sales_data"]}
    )

    print(f"Plan ID: {result['plan_id']}")
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Synthesis: {json.dumps(result['result']['synthesis'], indent=2)}")

    await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
