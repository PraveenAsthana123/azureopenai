"""
Model Lifecycle Manager for Enterprise RAG Platform.

Implements model versioning, deployment, and evaluation:
- Model registry with version tracking
- Shadow evaluation before promotion
- Canary deployment with traffic splitting
- Automatic rollback on degradation
- A/B testing framework
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from collections import defaultdict

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types of models managed."""
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    CLASSIFIER = "classifier"


class DeploymentStage(str, Enum):
    """Deployment stages for models."""
    DEVELOPMENT = "development"
    SHADOW = "shadow"
    CANARY = "canary"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ROLLED_BACK = "rolled_back"


class EvaluationStatus(str, Enum):
    """Status of model evaluation."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ModelVersion:
    """Represents a model version in the registry."""
    model_id: str
    version: str
    model_type: ModelType
    endpoint: str
    deployment_name: str
    stage: DeploymentStage
    created_at: datetime
    created_by: str
    config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    parent_version: Optional[str] = None
    is_default: bool = False

    @property
    def full_id(self) -> str:
        return f"{self.model_id}:{self.version}"

    def to_dict(self) -> dict:
        return {
            "id": self.full_id,
            "model_id": self.model_id,
            "version": self.version,
            "model_type": self.model_type.value,
            "endpoint": self.endpoint,
            "deployment_name": self.deployment_name,
            "stage": self.stage.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "config": self.config,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "parent_version": self.parent_version,
            "is_default": self.is_default
        }


@dataclass
class EvaluationResult:
    """Results from model evaluation."""
    evaluation_id: str
    model_version: str
    baseline_version: str
    status: EvaluationStatus
    started_at: datetime
    completed_at: Optional[datetime]
    metrics: dict = field(default_factory=dict)
    sample_count: int = 0
    passed_thresholds: dict = field(default_factory=dict)
    failed_thresholds: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.evaluation_id,
            "model_version": self.model_version,
            "baseline_version": self.baseline_version,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": self.metrics,
            "sample_count": self.sample_count,
            "passed_thresholds": self.passed_thresholds,
            "failed_thresholds": self.failed_thresholds,
            "errors": self.errors
        }


@dataclass
class DeploymentConfig:
    """Configuration for model deployment."""
    traffic_percentage: float = 0.0
    max_traffic_percentage: float = 100.0
    ramp_up_minutes: int = 30
    evaluation_window_minutes: int = 60
    auto_rollback: bool = True
    rollback_thresholds: dict = field(default_factory=lambda: {
        "error_rate": 0.05,
        "latency_p99_ms": 10000,
        "quality_score_min": 0.7
    })


class ModelRegistry:
    """
    Registry for tracking model versions and their metadata.
    Stores model configurations, metrics, and deployment history.
    """

    def __init__(self, cosmos_client: CosmosClient, database_name: str):
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self._cache: dict[str, ModelVersion] = {}

    async def register_model(self, model: ModelVersion) -> None:
        """Register a new model version."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_registry")
            await container.upsert_item(model.to_dict())
            self._cache[model.full_id] = model
            logger.info(f"Registered model: {model.full_id}")
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise

    async def get_model(self, model_id: str, version: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        full_id = f"{model_id}:{version}"
        if full_id in self._cache:
            return self._cache[full_id]

        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_registry")
            item = await container.read_item(item=full_id, partition_key=model_id)
            model = self._dict_to_model(item)
            self._cache[full_id] = model
            return model
        except Exception:
            return None

    async def get_default_model(self, model_id: str) -> Optional[ModelVersion]:
        """Get the default (production) version of a model."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_registry")

            query = """
                SELECT * FROM c
                WHERE c.model_id = @model_id
                AND c.is_default = true
            """
            params = [{"name": "@model_id", "value": model_id}]

            async for item in container.query_items(query=query, parameters=params):
                return self._dict_to_model(item)
            return None
        except Exception as e:
            logger.error(f"Failed to get default model: {e}")
            return None

    async def get_models_by_stage(
        self,
        model_id: str,
        stage: DeploymentStage
    ) -> list[ModelVersion]:
        """Get all model versions in a specific stage."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_registry")

            query = """
                SELECT * FROM c
                WHERE c.model_id = @model_id
                AND c.stage = @stage
            """
            params = [
                {"name": "@model_id", "value": model_id},
                {"name": "@stage", "value": stage.value}
            ]

            models = []
            async for item in container.query_items(query=query, parameters=params):
                models.append(self._dict_to_model(item))
            return models
        except Exception as e:
            logger.error(f"Failed to get models by stage: {e}")
            return []

    async def update_stage(
        self,
        model_id: str,
        version: str,
        new_stage: DeploymentStage
    ) -> None:
        """Update the deployment stage of a model."""
        model = await self.get_model(model_id, version)
        if model:
            model.stage = new_stage
            await self.register_model(model)
            logger.info(f"Updated {model.full_id} to stage: {new_stage.value}")

    async def set_default(self, model_id: str, version: str) -> None:
        """Set a model version as the default."""
        # Clear existing default
        current_default = await self.get_default_model(model_id)
        if current_default:
            current_default.is_default = False
            await self.register_model(current_default)

        # Set new default
        model = await self.get_model(model_id, version)
        if model:
            model.is_default = True
            model.stage = DeploymentStage.PRODUCTION
            await self.register_model(model)
            logger.info(f"Set default model: {model.full_id}")

    async def update_metrics(
        self,
        model_id: str,
        version: str,
        metrics: dict
    ) -> None:
        """Update metrics for a model version."""
        model = await self.get_model(model_id, version)
        if model:
            model.metrics.update(metrics)
            model.metrics["last_updated"] = datetime.utcnow().isoformat()
            await self.register_model(model)

    def _dict_to_model(self, d: dict) -> ModelVersion:
        """Convert dict to ModelVersion."""
        return ModelVersion(
            model_id=d["model_id"],
            version=d["version"],
            model_type=ModelType(d["model_type"]),
            endpoint=d["endpoint"],
            deployment_name=d["deployment_name"],
            stage=DeploymentStage(d["stage"]),
            created_at=datetime.fromisoformat(d["created_at"]),
            created_by=d["created_by"],
            config=d.get("config", {}),
            metrics=d.get("metrics", {}),
            metadata=d.get("metadata", {}),
            parent_version=d.get("parent_version"),
            is_default=d.get("is_default", False)
        )


class ShadowEvaluator:
    """
    Runs shadow evaluation comparing new model to baseline.
    Evaluates on production traffic without affecting users.
    """

    def __init__(
        self,
        openai_client: AsyncAzureOpenAI,
        registry: ModelRegistry,
        cosmos_client: CosmosClient,
        database_name: str
    ):
        self.openai_client = openai_client
        self.registry = registry
        self.cosmos_client = cosmos_client
        self.database_name = database_name

        # Default evaluation thresholds
        self.thresholds = {
            "relevance_score": 0.8,
            "grounding_score": 0.75,
            "latency_p50_ms": 2000,
            "latency_p99_ms": 8000,
            "error_rate": 0.02,
            "cost_per_query": 0.05
        }

    async def start_evaluation(
        self,
        candidate_version: str,
        baseline_version: str,
        sample_queries: list[dict],
        custom_thresholds: dict = None
    ) -> EvaluationResult:
        """Start shadow evaluation of candidate against baseline."""
        eval_id = hashlib.sha256(
            f"{candidate_version}:{baseline_version}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        result = EvaluationResult(
            evaluation_id=eval_id,
            model_version=candidate_version,
            baseline_version=baseline_version,
            status=EvaluationStatus.RUNNING,
            started_at=datetime.utcnow(),
            completed_at=None,
            sample_count=len(sample_queries)
        )

        thresholds = {**self.thresholds, **(custom_thresholds or {})}

        try:
            # Run evaluation
            metrics = await self._run_comparison(
                candidate_version,
                baseline_version,
                sample_queries
            )
            result.metrics = metrics

            # Check thresholds
            for metric_name, threshold in thresholds.items():
                if metric_name in metrics:
                    actual = metrics[metric_name]
                    # Lower is better for latency/error/cost, higher for scores
                    if metric_name in ["latency_p50_ms", "latency_p99_ms", "error_rate", "cost_per_query"]:
                        passed = actual <= threshold
                    else:
                        passed = actual >= threshold

                    if passed:
                        result.passed_thresholds[metric_name] = {
                            "threshold": threshold,
                            "actual": actual
                        }
                    else:
                        result.failed_thresholds[metric_name] = {
                            "threshold": threshold,
                            "actual": actual
                        }

            # Determine overall status
            if result.failed_thresholds:
                result.status = EvaluationStatus.FAILED
            else:
                result.status = EvaluationStatus.PASSED

            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            logger.error(f"Evaluation failed: {e}")

        # Store result
        await self._store_result(result)

        return result

    async def _run_comparison(
        self,
        candidate_version: str,
        baseline_version: str,
        sample_queries: list[dict]
    ) -> dict:
        """Run comparison between candidate and baseline."""
        candidate_metrics = defaultdict(list)
        baseline_metrics = defaultdict(list)

        for query in sample_queries:
            # Run both models
            candidate_result = await self._run_query(candidate_version, query)
            baseline_result = await self._run_query(baseline_version, query)

            # Collect metrics
            for metric, value in candidate_result.items():
                candidate_metrics[metric].append(value)
            for metric, value in baseline_result.items():
                baseline_metrics[metric].append(value)

        # Aggregate metrics
        aggregated = {}
        for metric in candidate_metrics:
            values = candidate_metrics[metric]
            if metric.startswith("latency"):
                aggregated[f"{metric}_candidate"] = sorted(values)[int(len(values) * 0.5)]  # p50
                aggregated[f"{metric}_p99_candidate"] = sorted(values)[int(len(values) * 0.99)] if len(values) > 100 else max(values)
            else:
                aggregated[f"{metric}_candidate"] = sum(values) / len(values)

        for metric in baseline_metrics:
            values = baseline_metrics[metric]
            if metric.startswith("latency"):
                aggregated[f"{metric}_baseline"] = sorted(values)[int(len(values) * 0.5)]
            else:
                aggregated[f"{metric}_baseline"] = sum(values) / len(values)

        # Calculate comparison scores
        if "relevance_score_candidate" in aggregated and "relevance_score_baseline" in aggregated:
            aggregated["relevance_score"] = aggregated["relevance_score_candidate"]
            aggregated["relevance_delta"] = (
                aggregated["relevance_score_candidate"] - aggregated["relevance_score_baseline"]
            )

        return aggregated

    async def _run_query(self, model_version: str, query: dict) -> dict:
        """Run a single query and collect metrics."""
        model_id, version = model_version.rsplit(":", 1)
        model = await self.registry.get_model(model_id, version)

        if not model:
            return {"error": 1, "latency_ms": 0, "relevance_score": 0}

        start_time = datetime.utcnow()

        try:
            # This would be replaced with actual model invocation
            response = await self.openai_client.chat.completions.create(
                model=model.deployment_name,
                messages=[{"role": "user", "content": query.get("query", "")}],
                temperature=0,
                max_tokens=500
            )

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Evaluate response quality
            relevance_score = await self._evaluate_relevance(
                query.get("query", ""),
                response.choices[0].message.content,
                query.get("expected_answer", "")
            )

            return {
                "latency_ms": latency_ms,
                "relevance_score": relevance_score,
                "error": 0,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }

        except Exception as e:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Query failed: {e}")
            return {
                "latency_ms": latency_ms,
                "relevance_score": 0,
                "error": 1
            }

    async def _evaluate_relevance(
        self,
        query: str,
        response: str,
        expected: str
    ) -> float:
        """Evaluate relevance of response to query."""
        if not expected:
            return 0.8  # Default score when no expected answer

        prompt = f"""Rate the relevance of the response to the query on a scale of 0-1.

Query: {query}
Expected Answer: {expected}
Actual Response: {response}

Return only a number between 0 and 1."""

        try:
            result = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            score = float(result.choices[0].message.content.strip())
            return max(0, min(1, score))
        except Exception:
            return 0.5

    async def _store_result(self, result: EvaluationResult) -> None:
        """Store evaluation result in Cosmos DB."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("model_evaluations")
            await container.upsert_item(result.to_dict())
        except Exception as e:
            logger.error(f"Failed to store evaluation result: {e}")


class CanaryDeployer:
    """
    Manages canary deployments with gradual traffic shifting.
    Monitors health and triggers automatic rollback if needed.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        cosmos_client: CosmosClient,
        database_name: str
    ):
        self.registry = registry
        self.cosmos_client = cosmos_client
        self.database_name = database_name
        self._active_canaries: dict[str, dict] = {}

    async def start_canary(
        self,
        model_id: str,
        candidate_version: str,
        config: DeploymentConfig
    ) -> dict:
        """Start a canary deployment."""
        deployment_id = hashlib.sha256(
            f"{model_id}:{candidate_version}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        # Get current production model
        production = await self.registry.get_default_model(model_id)
        if not production:
            raise ValueError(f"No production model found for {model_id}")

        # Update candidate to canary stage
        await self.registry.update_stage(model_id, candidate_version, DeploymentStage.CANARY)

        canary_state = {
            "deployment_id": deployment_id,
            "model_id": model_id,
            "candidate_version": candidate_version,
            "production_version": production.version,
            "config": {
                "traffic_percentage": config.traffic_percentage,
                "max_traffic_percentage": config.max_traffic_percentage,
                "ramp_up_minutes": config.ramp_up_minutes,
                "auto_rollback": config.auto_rollback,
                "rollback_thresholds": config.rollback_thresholds
            },
            "started_at": datetime.utcnow().isoformat(),
            "current_traffic": config.traffic_percentage,
            "status": "running",
            "metrics_history": []
        }

        self._active_canaries[deployment_id] = canary_state
        await self._store_canary_state(canary_state)

        logger.info(
            f"Started canary deployment {deployment_id}: "
            f"{candidate_version} at {config.traffic_percentage}% traffic"
        )

        return canary_state

    async def update_traffic(
        self,
        deployment_id: str,
        new_percentage: float
    ) -> dict:
        """Update traffic percentage for canary."""
        if deployment_id not in self._active_canaries:
            canary_state = await self._load_canary_state(deployment_id)
            if not canary_state:
                raise ValueError(f"Canary deployment not found: {deployment_id}")
            self._active_canaries[deployment_id] = canary_state

        canary = self._active_canaries[deployment_id]
        max_traffic = canary["config"]["max_traffic_percentage"]

        if new_percentage > max_traffic:
            raise ValueError(f"Traffic {new_percentage}% exceeds max {max_traffic}%")

        canary["current_traffic"] = new_percentage
        canary["metrics_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "traffic_percentage": new_percentage,
            "action": "traffic_update"
        })

        await self._store_canary_state(canary)

        logger.info(f"Updated canary {deployment_id} traffic to {new_percentage}%")

        return canary

    async def check_health(self, deployment_id: str, metrics: dict) -> dict:
        """Check canary health and decide on action."""
        if deployment_id not in self._active_canaries:
            canary_state = await self._load_canary_state(deployment_id)
            if not canary_state:
                return {"action": "none", "reason": "deployment not found"}
            self._active_canaries[deployment_id] = canary_state

        canary = self._active_canaries[deployment_id]
        thresholds = canary["config"]["rollback_thresholds"]

        # Check rollback conditions
        violations = []
        for metric, threshold in thresholds.items():
            if metric in metrics:
                actual = metrics[metric]
                if metric in ["error_rate", "latency_p99_ms"]:
                    if actual > threshold:
                        violations.append({
                            "metric": metric,
                            "threshold": threshold,
                            "actual": actual
                        })
                else:  # quality scores - lower is worse
                    if actual < threshold:
                        violations.append({
                            "metric": metric,
                            "threshold": threshold,
                            "actual": actual
                        })

        # Record metrics
        canary["metrics_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "violations": violations
        })

        if violations and canary["config"]["auto_rollback"]:
            # Trigger rollback
            await self.rollback(deployment_id, f"Threshold violations: {violations}")
            return {
                "action": "rollback",
                "reason": "threshold_violations",
                "violations": violations
            }

        # Check if ready for promotion
        if self._is_ready_for_promotion(canary):
            return {
                "action": "promote",
                "reason": "evaluation_period_complete",
                "metrics": metrics
            }

        await self._store_canary_state(canary)

        return {
            "action": "continue",
            "current_traffic": canary["current_traffic"],
            "violations": violations
        }

    async def promote(self, deployment_id: str) -> dict:
        """Promote canary to production."""
        canary = self._active_canaries.get(deployment_id)
        if not canary:
            canary = await self._load_canary_state(deployment_id)
            if not canary:
                raise ValueError(f"Canary deployment not found: {deployment_id}")

        model_id = canary["model_id"]
        candidate_version = canary["candidate_version"]

        # Set as default
        await self.registry.set_default(model_id, candidate_version)

        # Deprecate old production
        old_version = canary["production_version"]
        await self.registry.update_stage(model_id, old_version, DeploymentStage.DEPRECATED)

        # Update canary state
        canary["status"] = "promoted"
        canary["completed_at"] = datetime.utcnow().isoformat()
        await self._store_canary_state(canary)

        if deployment_id in self._active_canaries:
            del self._active_canaries[deployment_id]

        logger.info(f"Promoted canary {deployment_id}: {candidate_version} is now production")

        return {
            "action": "promoted",
            "new_production": candidate_version,
            "old_production": old_version
        }

    async def rollback(self, deployment_id: str, reason: str) -> dict:
        """Rollback canary deployment."""
        canary = self._active_canaries.get(deployment_id)
        if not canary:
            canary = await self._load_canary_state(deployment_id)
            if not canary:
                raise ValueError(f"Canary deployment not found: {deployment_id}")

        model_id = canary["model_id"]
        candidate_version = canary["candidate_version"]

        # Mark candidate as rolled back
        await self.registry.update_stage(model_id, candidate_version, DeploymentStage.ROLLED_BACK)

        # Update canary state
        canary["status"] = "rolled_back"
        canary["rollback_reason"] = reason
        canary["completed_at"] = datetime.utcnow().isoformat()
        await self._store_canary_state(canary)

        if deployment_id in self._active_canaries:
            del self._active_canaries[deployment_id]

        logger.info(f"Rolled back canary {deployment_id}: {reason}")

        return {
            "action": "rolled_back",
            "candidate": candidate_version,
            "reason": reason
        }

    def _is_ready_for_promotion(self, canary: dict) -> bool:
        """Check if canary is ready for promotion."""
        started = datetime.fromisoformat(canary["started_at"])
        eval_minutes = canary["config"].get("evaluation_window_minutes", 60)
        elapsed = (datetime.utcnow() - started).total_seconds() / 60

        # Must complete evaluation window at max traffic
        if elapsed < eval_minutes:
            return False

        if canary["current_traffic"] < canary["config"]["max_traffic_percentage"]:
            return False

        # Check for recent violations
        recent_history = canary["metrics_history"][-10:]
        for entry in recent_history:
            if entry.get("violations"):
                return False

        return True

    async def _store_canary_state(self, state: dict) -> None:
        """Store canary state in Cosmos DB."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("canary_deployments")
            await container.upsert_item({
                "id": state["deployment_id"],
                "partitionKey": state["model_id"],
                **state
            })
        except Exception as e:
            logger.error(f"Failed to store canary state: {e}")

    async def _load_canary_state(self, deployment_id: str) -> Optional[dict]:
        """Load canary state from Cosmos DB."""
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("canary_deployments")

            query = "SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": deployment_id}]

            async for item in container.query_items(query=query, parameters=params):
                return item
            return None
        except Exception as e:
            logger.error(f"Failed to load canary state: {e}")
            return None


class TrafficRouter:
    """
    Routes traffic between model versions based on deployment configuration.
    Implements weighted routing for canary deployments.
    """

    def __init__(self, registry: ModelRegistry, canary_deployer: CanaryDeployer):
        self.registry = registry
        self.canary_deployer = canary_deployer
        self._routing_cache: dict[str, dict] = {}
        self._cache_ttl_seconds = 30
        self._cache_timestamps: dict[str, datetime] = {}

    async def get_model_for_request(
        self,
        model_id: str,
        tenant_id: str,
        request_id: str
    ) -> ModelVersion:
        """Get the appropriate model version for a request."""
        # Check cache
        cache_key = f"{model_id}:{tenant_id}"
        if self._is_cache_valid(cache_key):
            routing = self._routing_cache[cache_key]
        else:
            routing = await self._build_routing_config(model_id, tenant_id)
            self._routing_cache[cache_key] = routing
            self._cache_timestamps[cache_key] = datetime.utcnow()

        # Determine which model to use
        if routing.get("canary"):
            # Use request_id for consistent routing
            hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16) % 100
            if hash_value < routing["canary"]["traffic_percentage"]:
                return routing["canary"]["model"]

        return routing["production"]

    async def _build_routing_config(self, model_id: str, tenant_id: str) -> dict:
        """Build routing configuration for a model."""
        config = {}

        # Get production model
        production = await self.registry.get_default_model(model_id)
        if production:
            config["production"] = production

        # Check for active canary
        canary_models = await self.registry.get_models_by_stage(model_id, DeploymentStage.CANARY)
        if canary_models:
            canary = canary_models[0]
            # Load canary deployment config
            for dep_id, state in self.canary_deployer._active_canaries.items():
                if state["model_id"] == model_id and state["status"] == "running":
                    config["canary"] = {
                        "model": canary,
                        "traffic_percentage": state["current_traffic"],
                        "deployment_id": dep_id
                    }
                    break

        return config

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._routing_cache:
            return False
        if key not in self._cache_timestamps:
            return False
        elapsed = (datetime.utcnow() - self._cache_timestamps[key]).total_seconds()
        return elapsed < self._cache_ttl_seconds


class ModelLifecycleManager:
    """
    Main manager for model lifecycle operations.
    Coordinates registration, evaluation, deployment, and routing.
    """

    def __init__(
        self,
        cosmos_endpoint: str,
        openai_endpoint: str,
        openai_api_key: str,
        openai_api_version: str = "2024-02-15-preview"
    ):
        self.cosmos_endpoint = cosmos_endpoint
        self.openai_endpoint = openai_endpoint
        self.openai_api_key = openai_api_key
        self.openai_api_version = openai_api_version

        self._cosmos_client: Optional[CosmosClient] = None
        self._openai_client: Optional[AsyncAzureOpenAI] = None

        self.registry: Optional[ModelRegistry] = None
        self.evaluator: Optional[ShadowEvaluator] = None
        self.deployer: Optional[CanaryDeployer] = None
        self.router: Optional[TrafficRouter] = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize lifecycle manager components."""
        if self._initialized:
            return

        credential = DefaultAzureCredential()
        self._cosmos_client = CosmosClient(self.cosmos_endpoint, credential=credential)
        self._openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_api_key,
            api_version=self.openai_api_version
        )

        database_name = "rag_platform"
        self.registry = ModelRegistry(self._cosmos_client, database_name)
        self.evaluator = ShadowEvaluator(
            self._openai_client,
            self.registry,
            self._cosmos_client,
            database_name
        )
        self.deployer = CanaryDeployer(self.registry, self._cosmos_client, database_name)
        self.router = TrafficRouter(self.registry, self.deployer)

        self._initialized = True
        logger.info("Model lifecycle manager initialized")

    async def register_new_version(
        self,
        model_id: str,
        version: str,
        model_type: ModelType,
        endpoint: str,
        deployment_name: str,
        created_by: str,
        config: dict = None,
        metadata: dict = None
    ) -> ModelVersion:
        """Register a new model version."""
        if not self._initialized:
            await self.initialize()

        # Get current default to set as parent
        current_default = await self.registry.get_default_model(model_id)

        model = ModelVersion(
            model_id=model_id,
            version=version,
            model_type=model_type,
            endpoint=endpoint,
            deployment_name=deployment_name,
            stage=DeploymentStage.DEVELOPMENT,
            created_at=datetime.utcnow(),
            created_by=created_by,
            config=config or {},
            metadata=metadata or {},
            parent_version=current_default.version if current_default else None
        )

        await self.registry.register_model(model)
        return model

    async def evaluate_and_deploy(
        self,
        model_id: str,
        version: str,
        sample_queries: list[dict],
        deployment_config: DeploymentConfig = None
    ) -> dict:
        """Run full evaluation and deployment pipeline."""
        if not self._initialized:
            await self.initialize()

        config = deployment_config or DeploymentConfig()
        result = {"stages": []}

        # Get baseline
        baseline = await self.registry.get_default_model(model_id)
        if not baseline:
            raise ValueError(f"No baseline model for {model_id}")

        # Stage 1: Shadow evaluation
        logger.info(f"Starting shadow evaluation: {model_id}:{version}")
        await self.registry.update_stage(model_id, version, DeploymentStage.SHADOW)

        eval_result = await self.evaluator.start_evaluation(
            candidate_version=f"{model_id}:{version}",
            baseline_version=baseline.full_id,
            sample_queries=sample_queries
        )

        result["stages"].append({
            "stage": "shadow_evaluation",
            "status": eval_result.status.value,
            "metrics": eval_result.metrics
        })

        if eval_result.status != EvaluationStatus.PASSED:
            result["final_status"] = "failed_evaluation"
            await self.registry.update_stage(model_id, version, DeploymentStage.DEVELOPMENT)
            return result

        # Stage 2: Canary deployment
        logger.info(f"Starting canary deployment: {model_id}:{version}")
        canary = await self.deployer.start_canary(model_id, version, config)

        result["stages"].append({
            "stage": "canary_started",
            "deployment_id": canary["deployment_id"],
            "traffic_percentage": canary["current_traffic"]
        })

        result["final_status"] = "canary_running"
        result["canary_deployment_id"] = canary["deployment_id"]

        return result

    async def get_model(
        self,
        model_id: str,
        tenant_id: str,
        request_id: str
    ) -> ModelVersion:
        """Get model for a request with traffic routing."""
        if not self._initialized:
            await self.initialize()

        return await self.router.get_model_for_request(model_id, tenant_id, request_id)

    async def close(self) -> None:
        """Close connections."""
        if self._cosmos_client:
            await self._cosmos_client.close()
        if self._openai_client:
            await self._openai_client.close()


# Example usage
async def main():
    """Example usage of model lifecycle manager."""
    manager = ModelLifecycleManager(
        cosmos_endpoint="https://your-cosmos.documents.azure.com:443/",
        openai_endpoint="https://your-openai.openai.azure.com/",
        openai_api_key="your-api-key"
    )

    await manager.initialize()

    # Register new model version
    model = await manager.register_new_version(
        model_id="gpt-4o",
        version="2024-02-01",
        model_type=ModelType.LLM,
        endpoint="https://your-openai.openai.azure.com/",
        deployment_name="gpt-4o-2024-02-01",
        created_by="admin@contoso.com",
        config={"temperature": 0.7, "max_tokens": 4000}
    )

    print(f"Registered: {model.full_id}")

    # Run evaluation and deployment
    sample_queries = [
        {"query": "What is our refund policy?", "expected_answer": "30 day returns"},
        {"query": "How do I contact support?", "expected_answer": "support@contoso.com"}
    ]

    result = await manager.evaluate_and_deploy(
        model_id="gpt-4o",
        version="2024-02-01",
        sample_queries=sample_queries,
        deployment_config=DeploymentConfig(
            traffic_percentage=5,
            max_traffic_percentage=50,
            ramp_up_minutes=30
        )
    )

    print(f"Deployment result: {result['final_status']}")

    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
