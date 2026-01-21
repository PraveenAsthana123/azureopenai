"""
Telemetry and Monitoring Module for Enterprise Copilot
Provides structured logging, metrics, and tracing using Azure Application Insights.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.trace import Span, Status, StatusCode


class MetricName(str, Enum):
    """Standard metric names for the platform."""
    # Latency metrics
    EMBEDDING_LATENCY = "embedding_latency"
    SEARCH_LATENCY = "search_latency"
    RERANKING_LATENCY = "reranking_latency"
    LLM_LATENCY = "llm_latency"
    TOTAL_RAG_LATENCY = "total_rag_latency"

    # Cache metrics
    CACHE_HIT_RATE = "cache_hit_rate"
    CACHE_SIZE = "cache_size"

    # Quality metrics
    RETRIEVAL_RELEVANCE = "retrieval_relevance"
    RETRIEVAL_NDCG = "retrieval_ndcg"
    GROUNDEDNESS_SCORE = "groundedness_score"
    HALLUCINATION_SCORE = "hallucination_score"
    RELEVANCE_SCORE = "relevance_score"

    # Volume metrics
    DOCUMENTS_INGESTED = "documents_ingested"
    CHUNKS_CREATED = "chunks_created"
    QUERIES_PROCESSED = "queries_processed"

    # Resource metrics
    TOKENS_USED = "tokens_used"
    SEARCH_RU_CONSUMED = "search_ru_consumed"


class EventName(str, Enum):
    """Standard event names for custom events."""
    USER_QUERY = "user_query"
    USER_FEEDBACK = "user_feedback"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    DOCUMENT_UPLOADED = "document_uploaded"
    CACHE_EVICTION = "cache_eviction"
    RATE_LIMIT_HIT = "rate_limit_hit"
    PII_DETECTED = "pii_detected"


class OperationName(str, Enum):
    """Standard operation names for tracing."""
    RAG_QUERY = "rag_query"
    INTENT_CLASSIFICATION = "intent_classification"
    QUERY_REWRITE = "query_rewrite"
    EMBEDDING_GENERATION = "embedding_generation"
    VECTOR_SEARCH = "vector_search"
    SEMANTIC_RERANKING = "semantic_reranking"
    LLM_GENERATION = "llm_generation"
    CACHE_LOOKUP = "cache_lookup"
    INGESTION_ORCHESTRATOR = "ingestion_orchestrator"
    DOCUMENT_PARSING = "document_parsing"
    DOCUMENT_CHUNKING = "document_chunking"
    INDEX_UPDATE = "index_update"
    RBAC_FILTER = "rbac_filter"
    PII_DETECTION = "pii_detection"


@dataclass
class TelemetryConfig:
    """Configuration for telemetry setup."""
    connection_string: str
    service_name: str = "enterprise-copilot"
    service_version: str = "1.0.0"
    environment: str = "production"
    enable_live_metrics: bool = True
    sampling_ratio: float = 1.0  # 1.0 = 100% sampling
    custom_dimensions: dict = field(default_factory=dict)


class TelemetryClient:
    """
    Centralized telemetry client for the Enterprise Copilot platform.
    Provides metrics, traces, and structured logging.
    """

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self._setup_azure_monitor()
        self._setup_metrics()
        self._setup_tracer()
        self.logger = logging.getLogger("copilot.telemetry")

    def _setup_azure_monitor(self):
        """Configure Azure Monitor OpenTelemetry."""
        configure_azure_monitor(
            connection_string=self.config.connection_string,
            enable_live_metrics=self.config.enable_live_metrics,
        )

    def _setup_metrics(self):
        """Setup OpenTelemetry metrics."""
        self.meter = metrics.get_meter(
            self.config.service_name,
            self.config.service_version,
        )

        # Latency histograms (in milliseconds)
        self._latency_histograms: dict[str, Histogram] = {}
        for metric in [
            MetricName.EMBEDDING_LATENCY,
            MetricName.SEARCH_LATENCY,
            MetricName.RERANKING_LATENCY,
            MetricName.LLM_LATENCY,
            MetricName.TOTAL_RAG_LATENCY,
        ]:
            self._latency_histograms[metric.value] = self.meter.create_histogram(
                name=metric.value,
                description=f"Latency for {metric.value}",
                unit="ms",
            )

        # Counters
        self._counters: dict[str, Counter] = {}
        for metric in [
            MetricName.DOCUMENTS_INGESTED,
            MetricName.CHUNKS_CREATED,
            MetricName.QUERIES_PROCESSED,
            MetricName.TOKENS_USED,
        ]:
            self._counters[metric.value] = self.meter.create_counter(
                name=metric.value,
                description=f"Counter for {metric.value}",
            )

        # Gauges (using UpDownCounter for gauge-like behavior)
        self._gauges = {
            MetricName.CACHE_HIT_RATE.value: self.meter.create_histogram(
                name=MetricName.CACHE_HIT_RATE.value,
                description="Cache hit rate percentage",
                unit="%",
            ),
            MetricName.CACHE_SIZE.value: self.meter.create_histogram(
                name=MetricName.CACHE_SIZE.value,
                description="Cache size in items",
            ),
        }

        # Quality metrics (0-1 scores)
        for metric in [
            MetricName.RETRIEVAL_RELEVANCE,
            MetricName.RETRIEVAL_NDCG,
            MetricName.GROUNDEDNESS_SCORE,
            MetricName.HALLUCINATION_SCORE,
            MetricName.RELEVANCE_SCORE,
        ]:
            self._gauges[metric.value] = self.meter.create_histogram(
                name=metric.value,
                description=f"Quality score for {metric.value}",
            )

    def _setup_tracer(self):
        """Setup OpenTelemetry tracer."""
        self.tracer = trace.get_tracer(
            self.config.service_name,
            self.config.service_version,
        )

    def _get_base_attributes(self) -> dict:
        """Get base attributes for all telemetry."""
        return {
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "environment": self.config.environment,
            **self.config.custom_dimensions,
        }

    # =========================================================================
    # METRICS
    # =========================================================================

    def record_latency(
        self,
        metric: MetricName,
        latency_ms: float,
        attributes: dict | None = None,
    ):
        """Record a latency measurement."""
        attrs = {**self._get_base_attributes(), **(attributes or {})}
        if metric.value in self._latency_histograms:
            self._latency_histograms[metric.value].record(latency_ms, attrs)

    def increment_counter(
        self,
        metric: MetricName,
        value: int = 1,
        attributes: dict | None = None,
    ):
        """Increment a counter metric."""
        attrs = {**self._get_base_attributes(), **(attributes or {})}
        if metric.value in self._counters:
            self._counters[metric.value].add(value, attrs)

    def record_gauge(
        self,
        metric: MetricName,
        value: float,
        attributes: dict | None = None,
    ):
        """Record a gauge metric value."""
        attrs = {**self._get_base_attributes(), **(attributes or {})}
        if metric.value in self._gauges:
            self._gauges[metric.value].record(value, attrs)

    def record_quality_score(
        self,
        metric: MetricName,
        score: float,
        attributes: dict | None = None,
    ):
        """Record a quality score (0-1 range)."""
        if not 0 <= score <= 1:
            self.logger.warning(f"Quality score {score} outside 0-1 range for {metric}")
        self.record_gauge(metric, score, attributes)

    # =========================================================================
    # TRACING
    # =========================================================================

    @contextmanager
    def start_span(
        self,
        operation: OperationName,
        attributes: dict | None = None,
    ):
        """Context manager for creating a traced span."""
        attrs = {**self._get_base_attributes(), **(attributes or {})}
        with self.tracer.start_as_current_span(operation.value, attributes=attrs) as span:
            start_time = time.time()
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)

    def trace_operation(
        self,
        operation: OperationName,
        attributes: dict | None = None,
    ):
        """Decorator for tracing a function."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.start_span(operation, attributes) as span:
                    result = await func(*args, **kwargs)
                    return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.start_span(operation, attributes) as span:
                    result = func(*args, **kwargs)
                    return result

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator

    def add_span_attributes(self, attributes: dict):
        """Add attributes to the current span."""
        span = trace.get_current_span()
        if span:
            for key, value in attributes.items():
                span.set_attribute(key, value)

    def add_span_event(self, name: str, attributes: dict | None = None):
        """Add an event to the current span."""
        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes or {})

    # =========================================================================
    # CUSTOM EVENTS
    # =========================================================================

    def track_event(
        self,
        event: EventName,
        properties: dict | None = None,
    ):
        """Track a custom event."""
        props = {**self._get_base_attributes(), **(properties or {})}
        span = trace.get_current_span()
        if span:
            span.add_event(event.value, props)
        self.logger.info(f"Event: {event.value}", extra={"custom_dimensions": props})

    def track_user_query(
        self,
        user_id: str,
        query: str,
        intent: str | None = None,
        cache_hit: bool = False,
        latency_ms: float | None = None,
    ):
        """Track a user query event."""
        self.track_event(
            EventName.USER_QUERY,
            {
                "user_id": user_id,
                "query_length": len(query),
                "intent": intent or "unknown",
                "cache_hit": cache_hit,
                "latency_ms": latency_ms,
            },
        )
        self.increment_counter(MetricName.QUERIES_PROCESSED)

    def track_user_feedback(
        self,
        user_id: str,
        query_id: str,
        rating: int,
        feedback_type: str = "thumbs",
        comment: str | None = None,
    ):
        """Track user feedback on a response."""
        self.track_event(
            EventName.USER_FEEDBACK,
            {
                "user_id": user_id,
                "query_id": query_id,
                "rating": rating,
                "feedback_type": feedback_type,
                "has_comment": comment is not None,
            },
        )

    # =========================================================================
    # RAG-SPECIFIC TELEMETRY
    # =========================================================================

    def record_rag_pipeline_metrics(
        self,
        embedding_latency_ms: float,
        search_latency_ms: float,
        llm_latency_ms: float,
        total_latency_ms: float,
        documents_retrieved: int,
        cache_hit: bool,
        attributes: dict | None = None,
    ):
        """Record comprehensive RAG pipeline metrics."""
        attrs = attributes or {}

        self.record_latency(MetricName.EMBEDDING_LATENCY, embedding_latency_ms, attrs)
        self.record_latency(MetricName.SEARCH_LATENCY, search_latency_ms, attrs)
        self.record_latency(MetricName.LLM_LATENCY, llm_latency_ms, attrs)
        self.record_latency(MetricName.TOTAL_RAG_LATENCY, total_latency_ms, attrs)

        self.add_span_attributes({
            "embedding_latency_ms": embedding_latency_ms,
            "search_latency_ms": search_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "total_latency_ms": total_latency_ms,
            "documents_retrieved": documents_retrieved,
            "cache_hit": cache_hit,
        })

    def record_retrieval_quality(
        self,
        relevance_scores: list[float],
        ndcg: float | None = None,
        mrr: float | None = None,
    ):
        """Record retrieval quality metrics."""
        if relevance_scores:
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
            self.record_quality_score(MetricName.RETRIEVAL_RELEVANCE, avg_relevance)

        if ndcg is not None:
            self.record_quality_score(MetricName.RETRIEVAL_NDCG, ndcg)

        self.add_span_attributes({
            "retrieval_relevance": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
            "retrieval_ndcg": ndcg,
            "retrieval_mrr": mrr,
        })

    def record_generation_quality(
        self,
        groundedness: float,
        hallucination_score: float,
        relevance: float,
    ):
        """Record response generation quality metrics."""
        self.record_quality_score(MetricName.GROUNDEDNESS_SCORE, groundedness)
        self.record_quality_score(MetricName.HALLUCINATION_SCORE, hallucination_score)
        self.record_quality_score(MetricName.RELEVANCE_SCORE, relevance)

        self.add_span_attributes({
            "groundedness_score": groundedness,
            "hallucination_score": hallucination_score,
            "relevance_score": relevance,
        })

    def record_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ):
        """Record token usage for cost tracking."""
        total_tokens = prompt_tokens + completion_tokens
        self.increment_counter(
            MetricName.TOKENS_USED,
            total_tokens,
            {"model": model, "token_type": "total"},
        )
        self.add_span_attributes({
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model": model,
        })

    # =========================================================================
    # INGESTION TELEMETRY
    # =========================================================================

    def record_ingestion_metrics(
        self,
        source: str,
        documents_processed: int,
        chunks_created: int,
        processing_time_ms: float,
        failed_documents: int = 0,
    ):
        """Record document ingestion metrics."""
        self.increment_counter(
            MetricName.DOCUMENTS_INGESTED,
            documents_processed,
            {"source": source},
        )
        self.increment_counter(
            MetricName.CHUNKS_CREATED,
            chunks_created,
            {"source": source},
        )
        self.add_span_attributes({
            "source": source,
            "documents_processed": documents_processed,
            "chunks_created": chunks_created,
            "failed_documents": failed_documents,
            "processing_time_ms": processing_time_ms,
        })

    # =========================================================================
    # SECURITY TELEMETRY
    # =========================================================================

    def track_access_denied(
        self,
        user_id: str,
        resource: str,
        reason: str,
    ):
        """Track access denied events for security monitoring."""
        self.logger.warning(
            f"Access denied: user={user_id}, resource={resource}, reason={reason}",
            extra={
                "custom_dimensions": {
                    "user_id": user_id,
                    "resource_requested": resource,
                    "denial_reason": reason,
                }
            },
        )
        self.add_span_event("access_denied", {
            "user_id": user_id,
            "resource": resource,
            "reason": reason,
        })

    def track_pii_detection(
        self,
        pii_detected: bool,
        pii_types: list[str],
        action_taken: str,
    ):
        """Track PII detection events."""
        self.track_event(
            EventName.PII_DETECTED,
            {
                "pii_detected": pii_detected,
                "pii_types": ",".join(pii_types),
                "action_taken": action_taken,
            },
        )


# =============================================================================
# HELPER DECORATORS
# =============================================================================

def timed_operation(
    telemetry: TelemetryClient,
    metric: MetricName,
    operation: OperationName | None = None,
):
    """
    Decorator that records operation latency and optionally creates a span.

    Usage:
        @timed_operation(telemetry, MetricName.LLM_LATENCY, OperationName.LLM_GENERATION)
        async def generate_response(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                if operation:
                    with telemetry.start_span(operation):
                        result = await func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)
                return result
            finally:
                latency_ms = (time.time() - start) * 1000
                telemetry.record_latency(metric, latency_ms)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                if operation:
                    with telemetry.start_span(operation):
                        result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            finally:
                latency_ms = (time.time() - start) * 1000
                telemetry.record_latency(metric, latency_ms)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_telemetry_instance: TelemetryClient | None = None


def get_telemetry() -> TelemetryClient:
    """Get the global telemetry client instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        raise RuntimeError("Telemetry not initialized. Call init_telemetry() first.")
    return _telemetry_instance


def init_telemetry(config: TelemetryConfig) -> TelemetryClient:
    """Initialize the global telemetry client."""
    global _telemetry_instance
    _telemetry_instance = TelemetryClient(config)
    return _telemetry_instance
