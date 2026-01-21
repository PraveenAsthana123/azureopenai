"""
Online Evaluation and Drift Monitoring for Enterprise RAG Platform.

Implements continuous evaluation in production:
- Daily batch evaluation of logged queries
- Drift detection (retrieval score, query patterns, quality)
- User feedback correlation
- Automated alerting on quality regression

Integrates with Azure AI Foundry for managed evaluation.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.evaluation import evaluate
from azure.ai.evaluation.evaluators import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    ResponseCompletenessEvaluator,
)

logger = logging.getLogger(__name__)


@dataclass
class OnlineEvalConfig:
    """Configuration for online evaluation."""
    cosmos_uri: str = os.getenv("COSMOS_URI", "")
    cosmos_db: str = os.getenv("COSMOS_DB", "rag_platform")
    eval_buffer_container: str = "eval_buffer"
    project_connection_string: str = os.getenv("FOUNDRY_PROJECT_CONNECTION_STRING", "")
    evaluation_hours: int = 24  # Evaluate last N hours
    sample_size: int = 100  # Max samples per evaluation
    groundedness_threshold: float = 0.8
    relevance_threshold: float = 0.7
    drift_alert_threshold: float = 0.15  # 15% drift triggers alert


@dataclass
class EvalBufferItem:
    """A logged RAG request for evaluation."""
    id: str
    timestamp: str
    user_id: str
    tenant_id: str
    session_id: str
    question: str
    transformed_query: str
    answer: str
    retrieved_chunks: list[dict]
    citations: list[dict]
    latency_ms: dict
    safety_flags: dict
    user_feedback: Optional[dict] = None


@dataclass
class DriftSignal:
    """A drift detection signal."""
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    is_regression: bool
    timestamp: str


@dataclass
class OnlineEvalSummary:
    """Summary of online evaluation run."""
    run_id: str
    timestamp: str
    period_start: str
    period_end: str
    samples_evaluated: int
    groundedness_avg: float
    relevance_avg: float
    completeness_avg: float
    overall_avg: float
    pass_rate: float
    drift_signals: list[DriftSignal]
    alerts: list[str]


class EvalBufferClient:
    """Client for reading evaluation buffer from Cosmos DB."""

    def __init__(self, config: OnlineEvalConfig):
        self.config = config
        self._client = None
        self._container = None

    async def _get_container(self):
        """Get Cosmos DB container."""
        if self._container:
            return self._container

        credential = DefaultAzureCredential()
        self._client = CosmosClient(self.config.cosmos_uri, credential=credential)
        database = self._client.get_database_client(self.config.cosmos_db)
        self._container = database.get_container_client(self.config.eval_buffer_container)
        return self._container

    async def read_eval_buffer(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> list[EvalBufferItem]:
        """
        Read recent logged queries for evaluation.

        Args:
            hours: Number of hours to look back
            limit: Maximum samples to return

        Returns:
            List of EvalBufferItem objects
        """
        container = await self._get_container()

        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        query = """
            SELECT TOP @limit *
            FROM c
            WHERE c.timestamp > @cutoff
            ORDER BY c.timestamp DESC
        """

        parameters = [
            {"name": "@limit", "value": limit},
            {"name": "@cutoff", "value": cutoff}
        ]

        items = container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )

        results = []
        async for item in items:
            results.append(EvalBufferItem(
                id=item.get("id"),
                timestamp=item.get("timestamp"),
                user_id=item.get("user_id"),
                tenant_id=item.get("tenant_id"),
                session_id=item.get("session_id"),
                question=item.get("question"),
                transformed_query=item.get("transformed_query", ""),
                answer=item.get("answer"),
                retrieved_chunks=item.get("retrieved_chunks", []),
                citations=item.get("citations", []),
                latency_ms=item.get("latency_ms", {}),
                safety_flags=item.get("safety_flags", {}),
                user_feedback=item.get("user_feedback")
            ))

        return results

    async def get_baseline_metrics(self, days: int = 7) -> dict:
        """Get baseline metrics from last N days."""
        container = await self._get_container()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = """
            SELECT
                AVG(c.eval_results.groundedness) as groundedness_avg,
                AVG(c.eval_results.relevance) as relevance_avg,
                AVG(c.retrieval_top_score) as retrieval_score_avg,
                COUNT(1) as sample_count
            FROM c
            WHERE c.timestamp > @cutoff
              AND IS_DEFINED(c.eval_results)
        """

        parameters = [{"name": "@cutoff", "value": cutoff}]

        items = container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )

        async for item in items:
            return {
                "groundedness_avg": item.get("groundedness_avg", 0.8),
                "relevance_avg": item.get("relevance_avg", 0.8),
                "retrieval_score_avg": item.get("retrieval_score_avg", 0.7),
                "sample_count": item.get("sample_count", 0)
            }

        # Default baseline
        return {
            "groundedness_avg": 0.8,
            "relevance_avg": 0.8,
            "retrieval_score_avg": 0.7,
            "sample_count": 0
        }


class DriftDetector:
    """Detects drift in RAG quality metrics."""

    def __init__(self, config: OnlineEvalConfig):
        self.config = config

    def detect_drift(
        self,
        baseline: dict,
        current: dict
    ) -> list[DriftSignal]:
        """
        Compare current metrics against baseline.

        Args:
            baseline: Baseline metrics from historical data
            current: Current evaluation metrics

        Returns:
            List of drift signals
        """
        signals = []
        threshold = self.config.drift_alert_threshold

        metrics_to_check = [
            ("groundedness_avg", "Groundedness"),
            ("relevance_avg", "Relevance"),
            ("retrieval_score_avg", "Retrieval Score"),
        ]

        for metric_key, metric_name in metrics_to_check:
            baseline_val = baseline.get(metric_key, 0)
            current_val = current.get(metric_key, 0)

            if baseline_val == 0:
                continue

            change = (current_val - baseline_val) / baseline_val
            is_regression = change < -threshold

            signals.append(DriftSignal(
                metric_name=metric_name,
                baseline_value=round(baseline_val, 4),
                current_value=round(current_val, 4),
                change_percent=round(change * 100, 2),
                is_regression=is_regression,
                timestamp=datetime.utcnow().isoformat()
            ))

        return signals


class OnlineEvaluator:
    """
    Runs online evaluation using Azure AI Foundry evaluators.
    """

    def __init__(self, config: OnlineEvalConfig):
        self.config = config
        self.buffer_client = EvalBufferClient(config)
        self.drift_detector = DriftDetector(config)

    async def _prepare_eval_target(self, item: EvalBufferItem) -> dict:
        """Prepare item for Foundry evaluation."""
        context = "\n\n".join([
            c.get("content", "") for c in item.retrieved_chunks
        ])

        return {
            "inputs": {"question": item.question},
            "outputs": {"response": item.answer},
            "context": context,
            "query": item.transformed_query or item.question
        }

    async def run_evaluation(self) -> OnlineEvalSummary:
        """
        Run online evaluation batch.

        Returns:
            OnlineEvalSummary with results and drift signals
        """
        import uuid

        run_id = str(uuid.uuid4())[:8]
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(hours=self.config.evaluation_hours)

        # Get samples from buffer
        samples = await self.buffer_client.read_eval_buffer(
            hours=self.config.evaluation_hours,
            limit=self.config.sample_size
        )

        if not samples:
            logger.warning("No samples found in evaluation buffer")
            return self._empty_summary(run_id, period_start, period_end)

        # Get baseline for drift detection
        baseline = await self.buffer_client.get_baseline_metrics(days=7)

        # Initialize Foundry evaluators
        credential = DefaultAzureCredential()
        project = AIProjectClient.from_connection_string(
            credential,
            self.config.project_connection_string
        )

        evaluators = {
            "groundedness": GroundednessEvaluator(project=project),
            "relevance": RelevanceEvaluator(project=project),
            "completeness": ResponseCompletenessEvaluator(project=project),
        }

        # Run evaluation
        results = []
        for sample in samples:
            try:
                target = await self._prepare_eval_target(sample)

                # Run each evaluator
                scores = {}
                for name, evaluator in evaluators.items():
                    result = await evaluator.evaluate(
                        query=target["inputs"]["question"],
                        response=target["outputs"]["response"],
                        context=target["context"]
                    )
                    scores[name] = result.get("score", 0)

                results.append(scores)

            except Exception as e:
                logger.error(f"Failed to evaluate sample {sample.id}: {e}")
                continue

        if not results:
            return self._empty_summary(run_id, period_start, period_end)

        # Calculate aggregates
        n = len(results)
        groundedness_avg = sum(r.get("groundedness", 0) for r in results) / n
        relevance_avg = sum(r.get("relevance", 0) for r in results) / n
        completeness_avg = sum(r.get("completeness", 0) for r in results) / n
        overall_avg = (groundedness_avg + relevance_avg + completeness_avg) / 3

        # Calculate pass rate
        pass_count = sum(
            1 for r in results
            if r.get("groundedness", 0) >= self.config.groundedness_threshold
            and r.get("relevance", 0) >= self.config.relevance_threshold
        )
        pass_rate = pass_count / n

        # Current metrics for drift detection
        current = {
            "groundedness_avg": groundedness_avg,
            "relevance_avg": relevance_avg,
            "retrieval_score_avg": self._calc_retrieval_avg(samples)
        }

        # Detect drift
        drift_signals = self.drift_detector.detect_drift(baseline, current)

        # Generate alerts
        alerts = self._generate_alerts(
            groundedness_avg, relevance_avg, pass_rate, drift_signals
        )

        return OnlineEvalSummary(
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            samples_evaluated=n,
            groundedness_avg=round(groundedness_avg, 4),
            relevance_avg=round(relevance_avg, 4),
            completeness_avg=round(completeness_avg, 4),
            overall_avg=round(overall_avg, 4),
            pass_rate=round(pass_rate, 4),
            drift_signals=drift_signals,
            alerts=alerts
        )

    def _calc_retrieval_avg(self, samples: list[EvalBufferItem]) -> float:
        """Calculate average retrieval score from samples."""
        scores = []
        for sample in samples:
            if sample.retrieved_chunks:
                top_score = sample.retrieved_chunks[0].get("score", 0)
                scores.append(top_score)
        return sum(scores) / len(scores) if scores else 0

    def _generate_alerts(
        self,
        groundedness: float,
        relevance: float,
        pass_rate: float,
        drift_signals: list[DriftSignal]
    ) -> list[str]:
        """Generate alert messages based on metrics."""
        alerts = []

        if groundedness < self.config.groundedness_threshold:
            alerts.append(
                f"ALERT: Groundedness ({groundedness:.2%}) below threshold "
                f"({self.config.groundedness_threshold:.2%})"
            )

        if relevance < self.config.relevance_threshold:
            alerts.append(
                f"ALERT: Relevance ({relevance:.2%}) below threshold "
                f"({self.config.relevance_threshold:.2%})"
            )

        if pass_rate < 0.8:
            alerts.append(f"ALERT: Pass rate ({pass_rate:.2%}) below 80%")

        for signal in drift_signals:
            if signal.is_regression:
                alerts.append(
                    f"ALERT: {signal.metric_name} regression detected "
                    f"({signal.change_percent:+.1f}%)"
                )

        return alerts

    def _empty_summary(
        self,
        run_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> OnlineEvalSummary:
        """Return empty summary when no samples available."""
        return OnlineEvalSummary(
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            samples_evaluated=0,
            groundedness_avg=0,
            relevance_avg=0,
            completeness_avg=0,
            overall_avg=0,
            pass_rate=0,
            drift_signals=[],
            alerts=["WARNING: No samples found in evaluation buffer"]
        )


class FeedbackCorrelator:
    """Correlates user feedback with quality metrics."""

    def __init__(self, config: OnlineEvalConfig):
        self.buffer_client = EvalBufferClient(config)

    async def analyze_feedback(self, hours: int = 24) -> dict:
        """
        Analyze correlation between user feedback and quality.

        Returns:
            Analysis of feedback patterns
        """
        samples = await self.buffer_client.read_eval_buffer(hours=hours, limit=500)

        positive = []
        negative = []

        for sample in samples:
            if sample.user_feedback:
                rating = sample.user_feedback.get("rating")
                if rating == "up":
                    positive.append(sample)
                elif rating == "down":
                    negative.append(sample)

        # Calculate average scores for each group
        positive_scores = self._calc_avg_scores(positive)
        negative_scores = self._calc_avg_scores(negative)

        # Analyze negative feedback reasons
        negative_reasons = defaultdict(int)
        for sample in negative:
            reason = sample.user_feedback.get("reason", "unspecified")
            negative_reasons[reason] += 1

        return {
            "period_hours": hours,
            "total_feedback": len(positive) + len(negative),
            "positive_count": len(positive),
            "negative_count": len(negative),
            "satisfaction_rate": len(positive) / (len(positive) + len(negative))
                if (positive or negative) else 0,
            "positive_avg_scores": positive_scores,
            "negative_avg_scores": negative_scores,
            "negative_reasons": dict(negative_reasons)
        }

    def _calc_avg_scores(self, samples: list[EvalBufferItem]) -> dict:
        """Calculate average scores for a group of samples."""
        if not samples:
            return {}

        # This would use stored eval results
        # Simplified for example
        return {
            "count": len(samples),
            "avg_latency_ms": sum(
                s.latency_ms.get("total", 0) for s in samples
            ) / len(samples)
        }


# Azure Function Timer Trigger for daily evaluation
async def run_daily_evaluation():
    """
    Entry point for daily online evaluation job.
    Can be triggered by Azure Functions Timer or Logic Apps.
    """
    config = OnlineEvalConfig()
    evaluator = OnlineEvaluator(config)

    logger.info("Starting daily online evaluation...")
    summary = await evaluator.run_evaluation()

    # Log results
    logger.info(f"Evaluation complete: {summary.samples_evaluated} samples")
    logger.info(f"Groundedness: {summary.groundedness_avg:.2%}")
    logger.info(f"Relevance: {summary.relevance_avg:.2%}")
    logger.info(f"Pass rate: {summary.pass_rate:.2%}")

    for alert in summary.alerts:
        logger.warning(alert)

    # Save summary (to Cosmos, App Insights, etc.)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_daily_evaluation())
