import logging
import time
import tracemalloc
from typing import Callable

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import StatusCode
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger("app.observability")

REQUEST_COUNT = Counter(
    "chattingapp_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "chattingapp_http_request_latency_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)
APP_EXCEPTIONS = Counter(
    "chattingapp_app_exceptions_total",
    "Total unhandled application exceptions",
    ["exception_type", "endpoint"],
)
DB_QUERY_COUNT = Counter(
    "chattingapp_db_queries_total",
    "Total database queries executed",
)
DB_QUERY_LATENCY = Histogram(
    "chattingapp_db_query_latency_seconds",
    "Database query execution latency",
)
DB_QUERY_ERRORS = Counter(
    "chattingapp_db_query_errors_total",
    "Total database query failures",
)
WEBSOCKET_CONNECTIONS = Counter(
    "chattingapp_websocket_connections_total",
    "WebSocket connections established",
    ["channel"],
)
WEBSOCKET_DISCONNECTS = Counter(
    "chattingapp_websocket_disconnects_total",
    "WebSocket connections disconnected",
    ["channel", "reason"],
)
WEBSOCKET_MESSAGES = Counter(
    "chattingapp_websocket_messages_total",
    "WebSocket messages processed",
    ["channel", "event_type"],
)
WEBSOCKET_ERRORS = Counter(
    "chattingapp_websocket_errors_total",
    "WebSocket errors encountered",
    ["channel", "stage"],
)
WEBSOCKET_ACTIVE_CONNECTIONS = Gauge(
    "chattingapp_websocket_active_connections",
    "Currently active WebSocket connections",
    ["channel"],
)
WEBSOCKET_ROOM_COUNT = Gauge(
    "chattingapp_websocket_room_count",
    "Active WebSocket rooms or conversation channels",
    ["channel"],
)
WEBSOCKET_DEVICE_CONNECTIONS = Gauge(
    "chattingapp_websocket_device_connections",
    "Active WebSocket device connection groups",
    ["channel"],
)
WEBSOCKET_MEMORY_USAGE_BYTES = Gauge(
    "chattingapp_websocket_memory_usage_bytes",
    "Approximate memory usage for WebSocket runtime state",
)
WEBSOCKET_RECONCILIATION_REQUESTS = Counter(
    "chattingapp_websocket_reconciliation_requests_total",
    "Offline reconciliation requests received",
    ["channel"],
)

_tracer_provider_initialized = False


def _configure_tracing() -> None:
    global _tracer_provider_initialized
    if _tracer_provider_initialized:
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "deployment.environment": settings.APP_ENV,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = None

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    elif settings.DEBUG and settings.ENABLE_TRACE_LOGGING:
        exporter = ConsoleSpanExporter()

    if exporter is not None:
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer_provider_initialized = True
        logger.info("OpenTelemetry tracing initialized. exporter=%s", type(exporter).__name__)
    else:
        logger.info("OpenTelemetry tracing not initialized; set OTEL_EXPORTER_OTLP_ENDPOINT or enable DEBUG trace logging.")


def _sample_gauge_value(gauge: Gauge) -> float:
    total = 0.0
    for metric in gauge.collect():
        for sample in metric.samples:
            if sample.name == gauge._name:
                total += float(sample.value)
    return total


def initialize_observability(app=None):
    _configure_tracing()
    if not tracemalloc.is_tracing():
        tracemalloc.start()
        logger.info("tracemalloc started for realtime websocket memory profiling")

    if settings.SENTRY_DSN:
        sentry_init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                LoggingIntegration(event_level=None, level=logging.INFO),
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
        )
        if app is not None:
            app.add_middleware(SentryAsgiMiddleware)
        logger.info("Sentry initialized for environment %s", settings.APP_ENV)


def capture_exception(exc: Exception) -> None:
    APP_EXCEPTIONS.labels(exception_type=type(exc).__name__, endpoint="unknown").inc()
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except Exception:
            logger.warning("Failed to capture exception to Sentry.")


class OpenTelemetryTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        _configure_tracing()
        tracer = trace.get_tracer(__name__)
        endpoint = request.url.path
        with tracer.start_as_current_span(f"HTTP {request.method} {endpoint}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.target", endpoint)
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        request_latency = time.time() - start_time

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            http_status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(request_latency)

        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _sum_counter(counter: Counter) -> int:
    total = 0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += sample.value
    return int(total)


def _histogram_average(histogram: Histogram) -> float:
    total = 0.0
    count = 0
    for metric in histogram.collect():
        for sample in metric.samples:
            if sample.name.endswith("_sum"):
                total += sample.value
            elif sample.name.endswith("_count"):
                count += sample.value
    return float(total / count * 1000) if count else 0.0


def performance_summary() -> dict[str, object]:
    return {
        "http_requests_total": _sum_counter(REQUEST_COUNT),
        "average_request_latency_ms": _histogram_average(REQUEST_LATENCY),
        "db_queries_total": _sum_counter(DB_QUERY_COUNT),
        "average_db_query_latency_ms": _histogram_average(DB_QUERY_LATENCY),
        "db_query_errors_total": _sum_counter(DB_QUERY_ERRORS),
        "websocket_connections_total": _sum_counter(WEBSOCKET_CONNECTIONS),
        "websocket_disconnects_total": _sum_counter(WEBSOCKET_DISCONNECTS),
        "websocket_messages_total": _sum_counter(WEBSOCKET_MESSAGES),
        "websocket_reconciliation_requests_total": _sum_counter(WEBSOCKET_RECONCILIATION_REQUESTS),
        "websocket_errors_total": _sum_counter(WEBSOCKET_ERRORS),
        "websocket_active_connection_rooms": _sample_gauge_value(WEBSOCKET_ROOM_COUNT),
        "websocket_device_connection_groups": _sample_gauge_value(WEBSOCKET_DEVICE_CONNECTIONS),
        "websocket_memory_usage_bytes": _sample_gauge_value(WEBSOCKET_MEMORY_USAGE_BYTES),
    }
