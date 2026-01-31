"""
GenAI Agentic Automation Platform - Unit Tests
==============================================
Comprehensive tests for the multi-agent orchestrator
with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock all Azure SDK modules before importing
sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["openai"] = MagicMock()

import agent_orchestrator


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_user_context():
    """Sample user context for agent interactions."""
    return {
        "name": "John Doe",
        "email": "john.doe@company.com",
        "department": "Engineering",
        "manager": "jane.manager@company.com"
    }


@pytest.fixture
def mock_http_request():
    """Factory for creating mock HTTP requests."""
    def _make_request(body: dict = None, method: str = "POST"):
        req = MagicMock()
        req.method = method
        req.route_params = {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


# ==============================================================================
# Test Tool Registry
# ==============================================================================

class TestToolRegistry:
    """Tests for tool registration and discovery."""

    def test_tools_registered(self):
        """Test that all expected tools are registered."""
        expected_tools = [
            "submit_leave_request",
            "get_pto_balance",
            "lookup_hr_policy",
            "reset_password",
            "unlock_account",
            "create_it_ticket",
            "check_account_status",
            "submit_expense",
            "check_expense_status"
        ]
        for tool_name in expected_tools:
            assert tool_name in agent_orchestrator.TOOL_REGISTRY, f"{tool_name} not registered"

    def test_tool_categories(self):
        """Test tools have correct categories."""
        hr_tools = [t for t in agent_orchestrator.TOOL_REGISTRY.values()
                     if t.category == agent_orchestrator.ToolCategory.HR]
        it_tools = [t for t in agent_orchestrator.TOOL_REGISTRY.values()
                     if t.category == agent_orchestrator.ToolCategory.IT]
        finance_tools = [t for t in agent_orchestrator.TOOL_REGISTRY.values()
                          if t.category == agent_orchestrator.ToolCategory.FINANCE]

        assert len(hr_tools) == 3
        assert len(it_tools) == 4
        assert len(finance_tools) == 2

    def test_expense_requires_approval(self):
        """Test that expense submission requires approval."""
        expense_tool = agent_orchestrator.TOOL_REGISTRY.get("submit_expense")
        assert expense_tool is not None
        assert expense_tool.requires_approval is True


# ==============================================================================
# Test Tool Executor
# ==============================================================================

class TestToolExecutor:
    """Tests for tool execution."""

    def test_submit_leave_request(self, sample_user_context):
        """Test leave request submission."""
        params = {
            "start_date": "2024-02-01",
            "end_date": "2024-02-05",
            "leave_type": "vacation",
            "reason": "Family trip"
        }

        result = agent_orchestrator.ToolExecutor.execute(
            "submit_leave_request", params, sample_user_context
        )

        assert result["success"] is True
        assert "request_id" in result
        assert result["status"] == "pending_approval"

    def test_get_pto_balance(self, sample_user_context):
        """Test PTO balance retrieval."""
        result = agent_orchestrator.ToolExecutor.execute(
            "get_pto_balance", {}, sample_user_context
        )

        assert "vacation_days" in result
        assert "available_vacation" in result
        assert result["vacation_days"] == 15

    def test_reset_password(self, sample_user_context):
        """Test password reset."""
        params = {"user_email": "john.doe@company.com", "method": "email"}

        result = agent_orchestrator.ToolExecutor.execute(
            "reset_password", params, sample_user_context
        )

        assert result["success"] is True
        assert "john.doe@company.com" in result["message"]

    def test_create_it_ticket(self, sample_user_context):
        """Test IT ticket creation."""
        params = {
            "category": "software",
            "description": "VS Code keeps crashing",
            "priority": "high"
        }

        result = agent_orchestrator.ToolExecutor.execute(
            "create_it_ticket", params, sample_user_context
        )

        assert result["success"] is True
        assert "ticket_id" in result
        assert result["status"] == "open"

    def test_submit_expense(self, sample_user_context):
        """Test expense submission."""
        params = {
            "amount": 250.00,
            "category": "travel",
            "description": "Flight to client meeting"
        }

        result = agent_orchestrator.ToolExecutor.execute(
            "submit_expense", params, sample_user_context
        )

        assert result["success"] is True
        assert result["amount"] == 250.00

    def test_unknown_tool(self, sample_user_context):
        """Test executing unknown tool returns error."""
        result = agent_orchestrator.ToolExecutor.execute(
            "nonexistent_tool", {}, sample_user_context
        )

        assert "error" in result

    def test_lookup_hr_policy(self, sample_user_context):
        """Test HR policy lookup."""
        params = {"topic": "leave"}

        result = agent_orchestrator.ToolExecutor.execute(
            "lookup_hr_policy", params, sample_user_context
        )

        assert "policy" in result
        assert "PTO" in result["policy"]

    def test_check_account_status(self, sample_user_context):
        """Test account status check."""
        params = {"user_email": "john.doe@company.com"}

        result = agent_orchestrator.ToolExecutor.execute(
            "check_account_status", params, sample_user_context
        )

        assert result["status"] == "active"
        assert result["mfa_enabled"] is True


# ==============================================================================
# Test Agent Orchestrator
# ==============================================================================

class TestAgentOrchestrator:
    """Tests for the agent orchestrator."""

    def test_orchestrator_init(self, sample_user_context):
        """Test orchestrator initialization."""
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)

        assert orchestrator.user_context == sample_user_context
        assert orchestrator.conversation_history == []
        assert orchestrator.tool_results == []

    def test_get_tools_for_openai(self, sample_user_context):
        """Test conversion of tools to OpenAI function format."""
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        tools = orchestrator._get_tools_for_openai()

        assert len(tools) == len(agent_orchestrator.TOOL_REGISTRY)
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_system_prompt_includes_context(self, sample_user_context):
        """Test system prompt includes user context."""
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        prompt = orchestrator._get_system_prompt()

        assert "John Doe" in prompt
        assert "john.doe@company.com" in prompt
        assert "Engineering" in prompt


# ==============================================================================
# Test HTTP Endpoints
# ==============================================================================

class TestEndpoints:
    """Tests for HTTP endpoints."""

    def test_chat_missing_message(self, mock_http_request):
        """Test agent/chat returns 400 when message is missing."""
        req = mock_http_request(body={"user_context": {"email": "test@co.com"}})

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            agent_orchestrator.agent_chat(req)
        )

        call_args = agent_orchestrator.func.HttpResponse.call_args
        assert call_args[1]["status_code"] == 400

    def test_list_tools_endpoint(self, mock_http_request):
        """Test agent/tools endpoint returns tool list."""
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            agent_orchestrator.list_tools(req)
        )

        call_args = agent_orchestrator.func.HttpResponse.call_args
        body = json.loads(call_args[0][0])
        assert "tools" in body
        assert len(body["tools"]) == 9

    def test_health_endpoint(self, mock_http_request):
        """Test health returns healthy status."""
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            agent_orchestrator.health(req)
        )

        call_args = agent_orchestrator.func.HttpResponse.call_args
        body = json.loads(call_args[0][0])
        assert body["status"] == "healthy"
        assert body["service"] == "agent-orchestrator"


# ==============================================================================
# Test Config
# ==============================================================================

class TestConfig:
    """Tests for configuration defaults."""

    def test_config_defaults(self):
        """Test Config has correct default values."""
        assert agent_orchestrator.Config.GPT_MODEL == "gpt-4o"
        assert agent_orchestrator.Config.MAX_ITERATIONS == 10

    def test_config_env_vars(self):
        """Test environment variable attributes."""
        for attr in ["AZURE_OPENAI_ENDPOINT", "COSMOS_ENDPOINT"]:
            value = getattr(agent_orchestrator.Config, attr)
            assert value is None or isinstance(value, str)


# ==============================================================================
# Test ToolCategory Enum
# ==============================================================================

class TestToolCategory:
    """Tests for tool category enum."""

    def test_categories_exist(self):
        """Test all expected categories exist."""
        assert agent_orchestrator.ToolCategory.HR.value == "hr"
        assert agent_orchestrator.ToolCategory.IT.value == "it"
        assert agent_orchestrator.ToolCategory.FINANCE.value == "finance"
        assert agent_orchestrator.ToolCategory.GENERAL.value == "general"


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
