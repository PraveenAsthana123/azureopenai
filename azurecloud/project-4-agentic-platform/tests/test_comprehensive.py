"""
GenAI Agentic Automation Platform - Comprehensive Tests
======================================================
3-tier testing: Positive, Negative, and Functional tests
for multi-agent orchestrator with mocked Azure services.
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

sys.modules["azure.functions"] = MagicMock()
sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.cosmos"] = MagicMock()
sys.modules["openai"] = MagicMock()

import agent_orchestrator


@pytest.fixture
def sample_user_context():
    return {"name": "John Doe", "email": "john.doe@company.com", "department": "Engineering", "manager": "jane.manager@company.com"}


@pytest.fixture
def sample_user_context_finance():
    return {"name": "Alice Finance", "email": "alice.finance@company.com", "department": "Finance", "manager": "bob.cfo@company.com"}


@pytest.fixture
def mock_http_request():
    def _make_request(body=None, method="POST"):
        req = MagicMock()
        req.method = method
        req.route_params = {}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON body")
        return req
    return _make_request


class TestPositive_ToolExecution:
    def test_submit_leave_all_params(self, sample_user_context):
        params = {"start_date": "2024-03-01", "end_date": "2024-03-05", "leave_type": "vacation", "reason": "Spring break"}
        result = agent_orchestrator.ToolExecutor.execute("submit_leave_request", params, sample_user_context)
        assert result["success"] is True
        assert "request_id" in result
        assert result["status"] == "pending_approval"

    def test_get_pto_balance_returns_all_fields(self, sample_user_context):
        result = agent_orchestrator.ToolExecutor.execute("get_pto_balance", {}, sample_user_context)
        assert "vacation_days" in result
        assert "available_vacation" in result
        assert result["vacation_days"] == 15

    def test_create_it_ticket_high_priority(self, sample_user_context):
        params = {"category": "hardware", "description": "Laptop screen flickering", "priority": "high"}
        result = agent_orchestrator.ToolExecutor.execute("create_it_ticket", params, sample_user_context)
        assert result["success"] is True
        assert "ticket_id" in result
        assert result["status"] == "open"

    def test_unlock_account(self, sample_user_context):
        result = agent_orchestrator.ToolExecutor.execute("unlock_account", {"user_email": "john.doe@company.com"}, sample_user_context)
        assert result["success"] is True

    def test_check_expense_status(self, sample_user_context):
        result = agent_orchestrator.ToolExecutor.execute("check_expense_status", {"expense_id": "exp-12345"}, sample_user_context)
        assert "status" in result

    def test_submit_expense_with_approval(self, sample_user_context):
        params = {"amount": 150.00, "category": "office_supplies", "description": "Monitor stand"}
        result = agent_orchestrator.ToolExecutor.execute("submit_expense", params, sample_user_context)
        assert result["success"] is True
        assert result["amount"] == 150.00


class TestPositive_Orchestrator:
    def test_orchestrator_init_preserves_context(self, sample_user_context):
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        assert orchestrator.user_context["name"] == "John Doe"
        assert orchestrator.conversation_history == []
        assert orchestrator.tool_results == []

    def test_tools_for_openai_format(self, sample_user_context):
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        tools = orchestrator._get_tools_for_openai()
        assert len(tools) == len(agent_orchestrator.TOOL_REGISTRY)
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]

    def test_system_prompt_includes_all_context(self, sample_user_context):
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        prompt = orchestrator._get_system_prompt()
        assert "John Doe" in prompt
        assert "john.doe@company.com" in prompt
        assert "Engineering" in prompt


class TestNegative_ToolExecution:
    def test_unknown_tool_returns_error(self, sample_user_context):
        result = agent_orchestrator.ToolExecutor.execute("nonexistent_tool", {}, sample_user_context)
        assert "error" in result

    def test_submit_expense_large_amount(self, sample_user_context):
        params = {"amount": 999999.99, "category": "travel", "description": "Very expensive trip"}
        result = agent_orchestrator.ToolExecutor.execute("submit_expense", params, sample_user_context)
        assert result["success"] is True
        assert result["amount"] == 999999.99


class TestNegative_Endpoints:
    def test_chat_missing_message_returns_400(self, mock_http_request):
        req = mock_http_request(body={"user_context": {"email": "test@co.com"}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(agent_orchestrator.agent_chat(req))
        assert agent_orchestrator.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_chat_missing_user_context(self, mock_http_request):
        req = mock_http_request(body={"message": "I need help"})
        import asyncio
        asyncio.get_event_loop().run_until_complete(agent_orchestrator.agent_chat(req))
        assert agent_orchestrator.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_chat_malformed_json(self, mock_http_request):
        req = mock_http_request(body=None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(agent_orchestrator.agent_chat(req))
        assert agent_orchestrator.func.HttpResponse.call_args[1]["status_code"] == 400

    def test_chat_empty_message(self, mock_http_request):
        req = mock_http_request(body={"message": "", "user_context": {"name": "Test", "email": "test@co.com"}})
        import asyncio
        asyncio.get_event_loop().run_until_complete(agent_orchestrator.agent_chat(req))
        assert agent_orchestrator.func.HttpResponse.call_args[1]["status_code"] == 400


class TestFunctional_AgentPipeline:
    def test_tool_registry_completeness(self):
        registry = agent_orchestrator.TOOL_REGISTRY
        hr_tools = [t for t in registry.values() if t.category == agent_orchestrator.ToolCategory.HR]
        it_tools = [t for t in registry.values() if t.category == agent_orchestrator.ToolCategory.IT]
        finance_tools = [t for t in registry.values() if t.category == agent_orchestrator.ToolCategory.FINANCE]
        assert len(hr_tools) == 3
        assert len(it_tools) == 4
        assert len(finance_tools) == 2
        assert len(registry) == 9

    def test_hr_workflow_pto_then_leave(self, sample_user_context):
        pto = agent_orchestrator.ToolExecutor.execute("get_pto_balance", {}, sample_user_context)
        assert pto["vacation_days"] == 15
        leave = agent_orchestrator.ToolExecutor.execute("submit_leave_request", {"start_date": "2024-03-01", "end_date": "2024-03-03", "leave_type": "vacation", "reason": "Personal"}, sample_user_context)
        assert leave["success"] is True

    def test_it_workflow_status_then_ticket(self, sample_user_context):
        status = agent_orchestrator.ToolExecutor.execute("check_account_status", {"user_email": "john.doe@company.com"}, sample_user_context)
        assert status["status"] == "active"
        ticket = agent_orchestrator.ToolExecutor.execute("create_it_ticket", {"category": "software", "description": "App crashes", "priority": "medium"}, sample_user_context)
        assert ticket["success"] is True

    def test_orchestrator_creates_valid_openai_tools(self, sample_user_context):
        orchestrator = agent_orchestrator.AgentOrchestrator(sample_user_context)
        tools = orchestrator._get_tools_for_openai()
        tool_names = [t["function"]["name"] for t in tools]
        for name in ["submit_leave_request", "get_pto_balance", "lookup_hr_policy", "reset_password", "unlock_account", "create_it_ticket", "check_account_status", "submit_expense", "check_expense_status"]:
            assert name in tool_names

    def test_expense_tool_requires_approval(self):
        expense_tool = agent_orchestrator.TOOL_REGISTRY.get("submit_expense")
        assert expense_tool is not None
        assert expense_tool.requires_approval is True

    def test_list_tools_returns_all(self, mock_http_request):
        req = mock_http_request(body=None, method="GET")
        req.get_json.side_effect = None
        import asyncio
        asyncio.get_event_loop().run_until_complete(agent_orchestrator.list_tools(req))
        body = json.loads(agent_orchestrator.func.HttpResponse.call_args[0][0])
        assert len(body["tools"]) == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
