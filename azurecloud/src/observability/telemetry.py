"""
OpenTelemetry Instrumentation for Enterprise RAG Platform.

Provides end-to-end tracing for:
- Azure Functions
- Azure OpenAI calls
- Azure AI Search queries
- Cosmos DB operations
- Custom RAG pipeline spans
"""

import os
import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


@dataclass
class TelemetryConfig:
    """Configuration for telemetry setup."""
    service_name: str = "rag-platform"
    service_version: str = "1.0.0"
    environment: str = "development"
    app_insights_connection_string: Optional[str] = None
    otlp_endpoint: Optional[str] = None
    enable_console_export: bool = False
    sample_rate: float = 1.0


class TelemetryManager:
    """
    Manages OpenTelemetry instrumentation for the RAG platform.
    Provides tracers, meters, and convenience methods for instrumentation.
    """

    _instance: Optional["TelemetryManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if TelemetryManager._initialized:
            return
        self._tracer: Optional[trace.Tracer] = None
        self._meter: Optional[metrics.Meter] = None
        self._config: Optional[TelemetryConfig] = None

    def initialize(self, config: TelemetryConfig) -> None:
        """Initialize telemetry with configuration."""
        if TelemetryManager._initialized:
            return

        self._config = config

        # Setup trace provider
        trace_provider = TracerProvider(
            resource=self._create_resource()
        )

        # Add Azure Monitor exporter if connection string provided
        if config.app_insights_connection_string:
            try:
                from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
                azure_exporter = AzureMonitorTraceExporter(
                    connection_string=config.app_insights_connection_string
                )
                trace_provider.add_span_processor(BatchSpanProcessor(azure_exporter))
            except ImportError:
                logger.warning("Azure Monitor exporter not available")

        # Add OTLP exporter if endpoint provided
        if config.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
            trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(trace_provider)
        self._tracer = trace.get_tracer(
            config.service_name,
            config.service_version
        )

        # Setup metrics
        metric_readers = []
        if config.app_insights_connection_string:
            try:
                from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter
                azure_metric_exporter = AzureMonitorMetricExporter(
                    connection_string=config.app_insights_connection_string
                )
                metric_readers.append(
                    PeriodicExportingMetricReader(azure_metric_exporter, export_interval_millis=60000)
                )
            except ImportError:
                pass

        meter_provider = MeterProvider(metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter(config.service_name, config.service_version)

        # Auto-instrument HTTP requests
        RequestsInstrumentor().instrument()

        TelemetryManager._initialized = True
        logger.info(f"Telemetry initialized for {config.service_name}")

    def _create_resource(self):
        """Create OpenTelemetry resource with service info."""
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        return Resource.create({
            SERVICE_NAME: self._config.service_name,
            SERVICE_VERSION: self._config.service_version,
            "deployment.environment": self._config.environment
        })

    @property
    def tracer(self) -> trace.Tracer:
        """Get the tracer instance."""
        if self._tracer is None:
            raise RuntimeError("Telemetry not initialized. Call initialize() first.")
        return self._tracer

    @property
    def meter(self) -> metrics.Meter:
        """Get the meter instance."""
        if self._meter is None:
            raise RuntimeError("Telemetry not initialized. Call initialize() first.")
        return self._meter


# Global telemetry manager instance
telemetry = TelemetryManager()


class RAGMetrics:
    """Pre-defined metrics for RAG platform monitoring."""

    def __init__(self):
        meter = telemetry.meter

        # Counters
        self.query_count = meter.create_counter(
            "rag.query.count",
            description="Total number of RAG queries",
            unit="1"
        )
        self.retrieval_count = meter.create_counter(
            "rag.retrieval.count",
            description="Total retrieval operations",
            unit="1"
        )
        self.llm_call_count = meter.create_counter(
            "rag.llm.call_count",
            description="Total LLM calls",
            unit="1"
        )
        self.safety_violation_count = meter.create_counter(
            "rag.safety.violations",
            description="Safety filter violations",
            unit="1"
        )

        # Histograms
        self.query_latency = meter.create_histogram(
            "rag.query.latency",
            description="End-to-end query latency",
            unit="ms"
        )
        self.retrieval_latency = meter.create_histogram(
            "rag.retrieval.latency",
            description="Search retrieval latency",
            unit="ms"
        )
        self.llm_latency = meter.create_histogram(
            "rag.llm.latency",
            description="LLM generation latency",
            unit="ms"
        )
        self.rerank_latency = meter.create_histogram(
            "rag.rerank.latency",
            description="Reranking latency",
            unit="ms"
        )

        # Gauges (using UpDownCounter)
        self.active_sessions = meter.create_up_down_counter(
            "rag.sessions.active",
            description="Active chat sessions",
            unit="1"
        )

        # Token usage
        self.token_usage = meter.create_histogram(
            "rag.llm.tokens",
            description="Token usage per request",
            unit="tokens"
        )


def traced(
    span_name: str = None,
    attributes: dict = None,
    record_exception: bool = True
):
    """
    Decorator to trace a function with OpenTelemetry.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Static attributes to add to span
        record_exception: Whether to record exceptions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = span_name or func.__name__
            with telemetry.tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", duration_ms)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = span_name or func.__name__
            with telemetry.tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", duration_ms)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: dict = None
):
    """
    Context manager for tracing operations.

    Usage:
        with trace_operation("search_documents", {"query": query}) as span:
            results = search(query)
            span.set_attribute("result_count", len(results))
    """
    with telemetry.tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        start_time = time.time()
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)


class SearchTelemetry:
    """Telemetry helpers for Azure AI Search operations."""

    @staticmethod
    def trace_hybrid_search(
        query: str,
        user_id: str,
        tenant_id: str,
        filters: dict = None
    ):
        """Create a span for hybrid search."""
        return trace_operation(
            "hybrid_search",
            {
                "search.query": query[:100],  # Truncate for safety
                "search.user_id": user_id,
                "search.tenant_id": tenant_id,
                "search.has_filters": bool(filters)
            }
        )

    @staticmethod
    def record_search_results(span, results: list, latency_ms: float):
        """Record search results on span."""
        span.set_attribute("search.result_count", len(results))
        span.set_attribute("search.latency_ms", latency_ms)
        if results:
            span.set_attribute("search.top_score", results[0].get("@search.score", 0))


class LLMTelemetry:
    """Telemetry helpers for LLM operations."""

    @staticmethod
    def trace_completion(
        model: str,
        prompt_tokens: int = 0,
        max_tokens: int = 0
    ):
        """Create a span for LLM completion."""
        return trace_operation(
            "llm_completion",
            {
                "llm.model": model,
                "llm.prompt_tokens_estimate": prompt_tokens,
                "llm.max_tokens": max_tokens
            }
        )

    @staticmethod
    def record_completion(
        span,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        finish_reason: str = "stop"
    ):
        """Record LLM completion results on span."""
        span.set_attribute("llm.prompt_tokens", prompt_tokens)
        span.set_attribute("llm.completion_tokens", completion_tokens)
        span.set_attribute("llm.total_tokens", prompt_tokens + completion_tokens)
        span.set_attribute("llm.latency_ms", latency_ms)
        span.set_attribute("llm.finish_reason", finish_reason)

        # Estimate cost (GPT-4o pricing as example)
        input_cost = (prompt_tokens / 1_000_000) * 2.50
        output_cost = (completion_tokens / 1_000_000) * 10.00
        span.set_attribute("llm.estimated_cost_usd", round(input_cost + output_cost, 6))


class CosmosTelemetry:
    """Telemetry helpers for Cosmos DB operations."""

    @staticmethod
    def trace_query(operation: str, container: str):
        """Create a span for Cosmos DB query."""
        return trace_operation(
            f"cosmos_{operation}",
            {
                "cosmos.operation": operation,
                "cosmos.container": container
            }
        )

    @staticmethod
    def record_query(span, ru_charge: float, item_count: int, latency_ms: float):
        """Record Cosmos DB query results."""
        span.set_attribute("cosmos.ru_charge", ru_charge)
        span.set_attribute("cosmos.item_count", item_count)
        span.set_attribute("cosmos.latency_ms", latency_ms)


def log_rag_event(
    event_name: str,
    user_id: str,
    session_id: str,
    tenant_id: str,
    **attributes
):
    """
    Log a structured RAG event with all required audit fields.

    Args:
        event_name: Name of the event (e.g., "query_completed")
        user_id: User identifier
        session_id: Session identifier
        tenant_id: Tenant identifier
        **attributes: Additional event attributes
    """
    span = trace.get_current_span()

    # Core audit fields
    span.add_event(
        event_name,
        {
            "user_id": user_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            **{k: str(v) if not isinstance(v, (str, int, float, bool)) else v
               for k, v in attributes.items()}
        }
    )


def initialize_telemetry():
    """Initialize telemetry from environment variables."""
    config = TelemetryConfig(
        service_name=os.getenv("SERVICE_NAME", "rag-platform"),
        service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        app_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        sample_rate=float(os.getenv("OTEL_SAMPLE_RATE", "1.0"))
    )
    telemetry.initialize(config)
    return telemetry


# Example usage
if __name__ == "__main__":
    import asyncio

    # Initialize
    initialize_telemetry()
    rag_metrics = RAGMetrics()

    @traced("example_query")
    async def example_rag_query(query: str, user_id: str):
        with SearchTelemetry.trace_hybrid_search(query, user_id, "tenant-1") as span:
            # Simulate search
            await asyncio.sleep(0.1)
            SearchTelemetry.record_search_results(span, [{"id": "1"}], 100)

        with LLMTelemetry.trace_completion("gpt-4o", 500, 1000) as span:
            # Simulate LLM call
            await asyncio.sleep(0.2)
            LLMTelemetry.record_completion(span, 500, 200, 200, "stop")

        # Record metrics
        rag_metrics.query_count.add(1, {"tenant": "tenant-1"})
        rag_metrics.query_latency.record(300, {"tenant": "tenant-1"})

        return "Example response"

    asyncio.run(example_rag_query("test query", "user-123"))
