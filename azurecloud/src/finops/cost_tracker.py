"""
FinOps Cost Tracking Module for Enterprise RAG Platform.

Implements comprehensive cost tracking and optimization:
- Token usage tracking for Azure OpenAI
- Search query cost estimation
- Cosmos DB RU tracking
- Cost attribution by tenant/user
- Budget alerts and forecasting
- Cost optimization recommendations
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CostCategory(str, Enum):
    """Categories of costs in RAG platform."""
    LLM_INPUT = "llm_input"
    LLM_OUTPUT = "llm_output"
    EMBEDDING = "embedding"
    SEARCH = "search"
    COSMOS_RU = "cosmos_ru"
    STORAGE = "storage"
    FUNCTION_EXECUTION = "function_execution"
    NETWORKING = "networking"


class CostTier(str, Enum):
    """Pricing tiers."""
    STANDARD = "standard"
    PREMIUM = "premium"
    RESERVED = "reserved"


@dataclass
class CostEvent:
    """A single cost event."""
    timestamp: datetime
    category: CostCategory
    quantity: float
    unit: str
    unit_price: float
    total_cost: float
    tenant_id: str
    user_id: str
    model: str = ""
    operation: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_cost": self.total_cost,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "model": self.model,
            "operation": self.operation,
            "metadata": self.metadata
        }


@dataclass
class CostSummary:
    """Summary of costs for a period."""
    period_start: datetime
    period_end: datetime
    total_cost: float
    by_category: dict[str, float]
    by_tenant: dict[str, float]
    by_model: dict[str, float]
    event_count: int
    top_users: list[tuple[str, float]]


class PricingModel:
    """
    Azure pricing model for RAG components.
    Prices as of 2024 - update as needed.
    """

    # Azure OpenAI pricing (per 1M tokens)
    LLM_PRICING = {
        "gpt-4o": {
            "input": 2.50,   # $2.50 per 1M input tokens
            "output": 10.00  # $10.00 per 1M output tokens
        },
        "gpt-4o-mini": {
            "input": 0.15,   # $0.15 per 1M input tokens
            "output": 0.60   # $0.60 per 1M output tokens
        },
        "gpt-4": {
            "input": 30.00,
            "output": 60.00
        },
        "gpt-35-turbo": {
            "input": 0.50,
            "output": 1.50
        }
    }

    # Embedding pricing (per 1M tokens)
    EMBEDDING_PRICING = {
        "text-embedding-3-large": 0.13,
        "text-embedding-3-small": 0.02,
        "text-embedding-ada-002": 0.10
    }

    # Azure AI Search pricing (per 1000 operations)
    SEARCH_PRICING = {
        "basic": 0.00,      # Included in basic tier
        "standard_s1": 0.0008,
        "standard_s2": 0.0008,
        "standard_s3": 0.0008
    }

    # Cosmos DB pricing (per 100 RU)
    COSMOS_PRICING = {
        "serverless": 0.25,  # per million RU
        "provisioned": 0.008  # per 100 RU/s per hour
    }

    # Storage pricing (per GB per month)
    STORAGE_PRICING = {
        "hot": 0.0184,
        "cool": 0.01,
        "archive": 0.00099
    }

    # Function pricing (per million executions)
    FUNCTION_PRICING = {
        "consumption": 0.20,
        "premium": 0.0  # Included in plan cost
    }

    @classmethod
    def get_llm_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate LLM cost."""
        if model not in cls.LLM_PRICING:
            model = "gpt-4o-mini"  # Default

        prices = cls.LLM_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]
        return round(input_cost + output_cost, 6)

    @classmethod
    def get_embedding_cost(cls, model: str, tokens: int) -> float:
        """Calculate embedding cost."""
        price = cls.EMBEDDING_PRICING.get(model, 0.13)
        return round((tokens / 1_000_000) * price, 6)

    @classmethod
    def get_search_cost(cls, tier: str, operations: int) -> float:
        """Calculate search cost."""
        price = cls.SEARCH_PRICING.get(tier, 0.0008)
        return round((operations / 1000) * price, 6)

    @classmethod
    def get_cosmos_cost(cls, tier: str, ru: float) -> float:
        """Calculate Cosmos DB cost."""
        if tier == "serverless":
            return round((ru / 1_000_000) * cls.COSMOS_PRICING["serverless"], 6)
        return round((ru / 100) * cls.COSMOS_PRICING["provisioned"] / 3600, 6)


class CostTracker:
    """
    Main cost tracking service.
    Tracks all cost events and provides aggregations.
    """

    def __init__(self, cosmos_client=None, database_name: str = "rag_platform"):
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self._events: list[CostEvent] = []
        self._hourly_cache: dict[str, dict] = {}

    def track_llm_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tenant_id: str,
        user_id: str,
        operation: str = "completion"
    ) -> CostEvent:
        """Track LLM token usage."""
        cost = PricingModel.get_llm_cost(model, input_tokens, output_tokens)

        event = CostEvent(
            timestamp=datetime.utcnow(),
            category=CostCategory.LLM_INPUT if input_tokens > output_tokens else CostCategory.LLM_OUTPUT,
            quantity=input_tokens + output_tokens,
            unit="tokens",
            unit_price=cost / (input_tokens + output_tokens) if (input_tokens + output_tokens) > 0 else 0,
            total_cost=cost,
            tenant_id=tenant_id,
            user_id=user_id,
            model=model,
            operation=operation,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        )

        self._events.append(event)
        self._update_cache(event)
        return event

    def track_embedding_usage(
        self,
        model: str,
        tokens: int,
        tenant_id: str,
        user_id: str,
        batch_size: int = 1
    ) -> CostEvent:
        """Track embedding generation."""
        cost = PricingModel.get_embedding_cost(model, tokens)

        event = CostEvent(
            timestamp=datetime.utcnow(),
            category=CostCategory.EMBEDDING,
            quantity=tokens,
            unit="tokens",
            unit_price=cost / tokens if tokens > 0 else 0,
            total_cost=cost,
            tenant_id=tenant_id,
            user_id=user_id,
            model=model,
            operation="embedding",
            metadata={"batch_size": batch_size}
        )

        self._events.append(event)
        self._update_cache(event)
        return event

    def track_search_usage(
        self,
        operation_count: int,
        tenant_id: str,
        user_id: str,
        search_tier: str = "standard_s1",
        query_type: str = "hybrid"
    ) -> CostEvent:
        """Track search operations."""
        cost = PricingModel.get_search_cost(search_tier, operation_count)

        event = CostEvent(
            timestamp=datetime.utcnow(),
            category=CostCategory.SEARCH,
            quantity=operation_count,
            unit="operations",
            unit_price=cost / operation_count if operation_count > 0 else 0,
            total_cost=cost,
            tenant_id=tenant_id,
            user_id=user_id,
            model=search_tier,
            operation=query_type
        )

        self._events.append(event)
        self._update_cache(event)
        return event

    def track_cosmos_usage(
        self,
        ru_consumed: float,
        tenant_id: str,
        user_id: str,
        cosmos_tier: str = "serverless",
        operation: str = "query"
    ) -> CostEvent:
        """Track Cosmos DB RU consumption."""
        cost = PricingModel.get_cosmos_cost(cosmos_tier, ru_consumed)

        event = CostEvent(
            timestamp=datetime.utcnow(),
            category=CostCategory.COSMOS_RU,
            quantity=ru_consumed,
            unit="RU",
            unit_price=cost / ru_consumed if ru_consumed > 0 else 0,
            total_cost=cost,
            tenant_id=tenant_id,
            user_id=user_id,
            model=cosmos_tier,
            operation=operation
        )

        self._events.append(event)
        self._update_cache(event)
        return event

    def _update_cache(self, event: CostEvent):
        """Update hourly cache for fast aggregations."""
        hour_key = event.timestamp.strftime("%Y-%m-%d-%H")

        if hour_key not in self._hourly_cache:
            self._hourly_cache[hour_key] = {
                "total": 0,
                "by_category": defaultdict(float),
                "by_tenant": defaultdict(float),
                "by_model": defaultdict(float),
                "count": 0
            }

        cache = self._hourly_cache[hour_key]
        cache["total"] += event.total_cost
        cache["by_category"][event.category.value] += event.total_cost
        cache["by_tenant"][event.tenant_id] += event.total_cost
        cache["by_model"][event.model] += event.total_cost
        cache["count"] += 1

    def get_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        tenant_id: str = None
    ) -> CostSummary:
        """Get cost summary for a period."""
        filtered_events = [
            e for e in self._events
            if start_time <= e.timestamp <= end_time
            and (tenant_id is None or e.tenant_id == tenant_id)
        ]

        by_category = defaultdict(float)
        by_tenant = defaultdict(float)
        by_model = defaultdict(float)
        by_user = defaultdict(float)

        total_cost = 0
        for event in filtered_events:
            total_cost += event.total_cost
            by_category[event.category.value] += event.total_cost
            by_tenant[event.tenant_id] += event.total_cost
            by_model[event.model] += event.total_cost
            by_user[event.user_id] += event.total_cost

        # Top 10 users by cost
        top_users = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]

        return CostSummary(
            period_start=start_time,
            period_end=end_time,
            total_cost=round(total_cost, 4),
            by_category=dict(by_category),
            by_tenant=dict(by_tenant),
            by_model=dict(by_model),
            event_count=len(filtered_events),
            top_users=top_users
        )

    def get_tenant_usage(self, tenant_id: str, hours: int = 24) -> dict:
        """Get usage breakdown for a tenant."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        summary = self.get_summary(start_time, end_time, tenant_id)

        return {
            "tenant_id": tenant_id,
            "period_hours": hours,
            "total_cost_usd": summary.total_cost,
            "breakdown": summary.by_category,
            "model_usage": summary.by_model,
            "request_count": summary.event_count
        }


class BudgetManager:
    """
    Manages budgets and alerts for cost control.
    """

    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
        self._budgets: dict[str, dict] = {}
        self._alerts: list[dict] = []

    def set_budget(
        self,
        tenant_id: str,
        monthly_budget: float,
        alert_thresholds: list[float] = None
    ):
        """Set budget for a tenant."""
        self._budgets[tenant_id] = {
            "monthly_budget": monthly_budget,
            "alert_thresholds": alert_thresholds or [0.5, 0.75, 0.9, 1.0],
            "created_at": datetime.utcnow()
        }

    def check_budget(self, tenant_id: str) -> dict:
        """Check budget status for a tenant."""
        if tenant_id not in self._budgets:
            return {"status": "no_budget", "tenant_id": tenant_id}

        budget = self._budgets[tenant_id]
        monthly_budget = budget["monthly_budget"]

        # Get current month's usage
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        summary = self.cost_tracker.get_summary(month_start, now, tenant_id)
        current_spend = summary.total_cost
        utilization = current_spend / monthly_budget if monthly_budget > 0 else 0

        # Check thresholds
        alerts_triggered = []
        for threshold in budget["alert_thresholds"]:
            if utilization >= threshold:
                alerts_triggered.append(threshold)

        status = "ok"
        if utilization >= 1.0:
            status = "exceeded"
        elif utilization >= 0.9:
            status = "critical"
        elif utilization >= 0.75:
            status = "warning"

        return {
            "tenant_id": tenant_id,
            "status": status,
            "monthly_budget": monthly_budget,
            "current_spend": round(current_spend, 2),
            "utilization_percent": round(utilization * 100, 2),
            "remaining": round(monthly_budget - current_spend, 2),
            "alerts_triggered": alerts_triggered,
            "days_in_month": (now - month_start).days + 1
        }

    def forecast_month_end(self, tenant_id: str) -> dict:
        """Forecast month-end spend based on current usage."""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get current usage
        summary = self.cost_tracker.get_summary(month_start, now, tenant_id)
        current_spend = summary.total_cost

        # Calculate days
        days_elapsed = (now - month_start).days + 1
        days_in_month = 30  # Approximate

        # Linear forecast
        daily_rate = current_spend / days_elapsed if days_elapsed > 0 else 0
        projected_spend = daily_rate * days_in_month

        # Get budget
        budget = self._budgets.get(tenant_id, {})
        monthly_budget = budget.get("monthly_budget", 0)

        return {
            "tenant_id": tenant_id,
            "current_spend": round(current_spend, 2),
            "daily_rate": round(daily_rate, 2),
            "projected_month_end": round(projected_spend, 2),
            "monthly_budget": monthly_budget,
            "projected_variance": round(projected_spend - monthly_budget, 2) if monthly_budget > 0 else None,
            "forecast_date": now.isoformat()
        }


class CostOptimizer:
    """
    Provides cost optimization recommendations.
    """

    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker

    def analyze(self, tenant_id: str, days: int = 30) -> list[dict]:
        """Analyze usage and provide optimization recommendations."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        summary = self.cost_tracker.get_summary(start_time, end_time, tenant_id)
        recommendations = []

        # Analyze LLM usage
        llm_cost = summary.by_category.get("llm_input", 0) + summary.by_category.get("llm_output", 0)
        if llm_cost > summary.total_cost * 0.7:
            # Check if using expensive models
            if summary.by_model.get("gpt-4", 0) > llm_cost * 0.3:
                recommendations.append({
                    "category": "llm",
                    "priority": "high",
                    "title": "Switch to GPT-4o-mini for simple queries",
                    "description": "30%+ of LLM costs are from GPT-4. Consider using GPT-4o-mini for simpler queries.",
                    "potential_savings": round(summary.by_model.get("gpt-4", 0) * 0.95, 2),
                    "implementation": "Implement model routing based on query complexity"
                })

        # Analyze embedding usage
        embedding_cost = summary.by_category.get("embedding", 0)
        if embedding_cost > summary.total_cost * 0.15:
            recommendations.append({
                "category": "embedding",
                "priority": "medium",
                "title": "Batch embedding requests",
                "description": "High embedding costs detected. Batch requests to reduce overhead.",
                "potential_savings": round(embedding_cost * 0.2, 2),
                "implementation": "Use batch_size=32 for embedding requests"
            })

        # Analyze search usage
        search_cost = summary.by_category.get("search", 0)
        if search_cost > summary.total_cost * 0.25:
            recommendations.append({
                "category": "search",
                "priority": "medium",
                "title": "Implement query caching",
                "description": "Frequent search queries detected. Cache common queries.",
                "potential_savings": round(search_cost * 0.3, 2),
                "implementation": "Add Redis cache for top-k results with 30-minute TTL"
            })

        # General recommendations
        if summary.event_count > 10000:
            recommendations.append({
                "category": "general",
                "priority": "low",
                "title": "Review high-frequency users",
                "description": "High request volume detected. Review top users for optimization.",
                "potential_savings": None,
                "implementation": "Implement rate limiting and usage quotas"
            })

        return recommendations


class ChargebackService:
    """
    Service for cost allocation and chargeback to departments/tenants.
    """

    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
        self._department_mapping: dict[str, str] = {}

    def set_department_mapping(self, tenant_id: str, department: str):
        """Map tenant to department for chargeback."""
        self._department_mapping[tenant_id] = department

    def generate_chargeback_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Generate chargeback report for all departments."""
        summary = self.cost_tracker.get_summary(start_date, end_date)

        # Aggregate by department
        by_department = defaultdict(lambda: {
            "total": 0,
            "tenants": [],
            "breakdown": defaultdict(float)
        })

        for tenant_id, cost in summary.by_tenant.items():
            department = self._department_mapping.get(tenant_id, "Unassigned")
            by_department[department]["total"] += cost
            by_department[department]["tenants"].append({
                "tenant_id": tenant_id,
                "cost": round(cost, 2)
            })

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_cost": round(summary.total_cost, 2),
            "by_department": {
                dept: {
                    "total": round(data["total"], 2),
                    "tenant_count": len(data["tenants"]),
                    "tenants": data["tenants"]
                }
                for dept, data in by_department.items()
            },
            "generated_at": datetime.utcnow().isoformat()
        }


# Example usage
def main():
    """Example usage of cost tracking."""
    tracker = CostTracker()
    budget_manager = BudgetManager(tracker)
    optimizer = CostOptimizer(tracker)

    # Set budget
    budget_manager.set_budget("tenant-1", monthly_budget=1000.0)

    # Track some usage
    tracker.track_llm_usage(
        model="gpt-4o-mini",
        input_tokens=500,
        output_tokens=200,
        tenant_id="tenant-1",
        user_id="user@company.com"
    )

    tracker.track_embedding_usage(
        model="text-embedding-3-large",
        tokens=1000,
        tenant_id="tenant-1",
        user_id="user@company.com"
    )

    tracker.track_search_usage(
        operation_count=5,
        tenant_id="tenant-1",
        user_id="user@company.com"
    )

    # Check budget
    budget_status = budget_manager.check_budget("tenant-1")
    print(f"Budget Status: {budget_status}")

    # Get recommendations
    recommendations = optimizer.analyze("tenant-1", days=1)
    print(f"Recommendations: {recommendations}")


if __name__ == "__main__":
    main()
