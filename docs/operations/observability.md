# Observability and Monitoring

This document describes the observability setup for ChattingApp backend, including Prometheus metrics, Sentry error tracking, and OpenTelemetry distributed tracing.

## Overview

The backend integrates three observability systems:

- **Prometheus**: Real-time HTTP request metrics, database query metrics, and WebSocket activity
- **Sentry**: Error tracking, exception reporting, and performance monitoring
- **OpenTelemetry**: Distributed tracing for request flows and service interactions

## Prometheus Metrics

### Available Endpoints

- `/metrics` — Prometheus-formatted metrics (JSON conversion available)
- `/performance` — Summary of HTTP and DB performance metrics
- `/health` — Liveness/readiness check

### Metric Categories

#### HTTP Request Metrics

- `chattingapp_http_requests_total` — Counter by method, endpoint, and status
- `chattingapp_http_request_latency_seconds` — Histogram of request duration

#### Database Metrics

- `chattingapp_db_queries_total` — Counter of all DB queries
- `chattingapp_db_query_latency_seconds` — Histogram of query duration
- `chattingapp_db_query_errors_total` — Counter of failed queries

#### WebSocket Metrics

- `chattingapp_websocket_connections_total` — Total WS connections established
- `chattingapp_websocket_disconnects_total` — Total WS disconnects
- `chattingapp_websocket_messages_total` — Messages processed by event type
- `chattingapp_websocket_errors_total` — WS errors by stage
- `chattingapp_websocket_active_connections` — Current active WS connections

#### Application Metrics

- `chattingapp_app_exceptions_total` — Unhandled exceptions by type

### Scraping Prometheus Metrics

Example Prometheus job configuration:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "chattingapp"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
```

## Sentry Error Tracking

Sentry captures unhandled exceptions, logs, and performance data for all environments.

### Configuration

Set the following environment variables:

```bash
export SENTRY_DSN="https://<key>@<sentry-domain>.ingest.sentry.io/<project>"
export SENTRY_TRACES_SAMPLE_RATE="0.1"  # Default 10% of transactions
export APP_ENV="production"  # or staging/development
```

### Sentry Integrations

The backend includes:

- **Logging Integration**: Captures `INFO` level and above
- **SQLAlchemy Integration**: Tracks database errors and slow queries
- **ASGI Middleware**: Captures all HTTP exceptions and performance data

### Exception Handling

All unhandled exceptions are automatically captured via the generic exception handler in `app/main.py`.

To manually capture an exception:

```python
from app.core.observability import capture_exception

try:
    # dangerous operation
except Exception as exc:
    capture_exception(exc)  # Sentry will receive it if DSN is configured
```

### Performance Monitoring

When `SENTRY_TRACES_SAMPLE_RATE > 0`, Sentry traces every Nth transaction for performance analysis.

## OpenTelemetry Tracing

OpenTelemetry provides distributed tracing across services.

### Configuration

Set the following environment variables:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"  # OTLP HTTP receiver
export OTEL_SERVICE_NAME="chattingapp-backend"
export ENABLE_TRACE_LOGGING="true"  # Console logging in development
```

### Trace Data

Each HTTP request generates a span with:

- HTTP method and target path
- HTTP status code
- Request start/end timestamps

### Development Tracing (Console)

In development mode with `DEBUG=true` and `ENABLE_TRACE_LOGGING=true`, OpenTelemetry traces are logged to console (via `ConsoleSpanExporter`).

### Production Tracing (OTLP)

In production, configure `OTEL_EXPORTER_OTLP_ENDPOINT` to send traces to an OpenTelemetry collector:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector.monitoring:4318"
```

Example `otel-collector` docker-compose entry:

```yaml
otel-collector:
  image: otel/opentelemetry-collector-contrib:0.80.0
  ports:
    - "4318:4318" # OTLP HTTP receiver
  volumes:
    - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
  command:
    - "--config=/etc/otel-collector-config.yaml"
```

## Health Check Endpoint

The `/health` endpoint returns `{"status": "ok"}` and should be used for:

- Kubernetes liveness/readiness probes
- Load balancer health checks
- Docker health checks

Example Kubernetes probe:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Production Environment Variables

Create a `.env.production` file with:

```bash
# Observability
SENTRY_DSN="https://<key>@<sentry-domain>.ingest.sentry.io/<project>"
SENTRY_TRACES_SAMPLE_RATE=0.05  # 5% of transactions in production
OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector.monitoring:4318"
OTEL_SERVICE_NAME="chattingapp-backend"
ENABLE_TRACE_LOGGING=false  # Disable console logging in production

# Logging
LOG_LEVEL="INFO"

# App
APP_ENV="production"
DEBUG=false

# Database
DB_POOL_SIZE=25  # Increase pool size for production
DB_MAX_OVERFLOW=5
```

## Monitoring and Alerting

### Grafana Dashboards

Create Grafana dashboards connected to Prometheus with panels for:

1. **Request Rate** — `rate(chattingapp_http_requests_total[5m])`
2. **P95 Latency** — `histogram_quantile(0.95, chattingapp_http_request_latency_seconds_bucket)`
3. **Error Rate** — `rate(chattingapp_http_requests_total{http_status=~"5.."}[5m])`
4. **DB Query Latency** — `histogram_quantile(0.95, chattingapp_db_query_latency_seconds_bucket)`
5. **Active WebSocket Connections** — `chattingapp_websocket_active_connections`
6. **WebSocket memory usage** — `chattingapp_websocket_memory_usage_bytes`

For local development, Grafana is provisioned under `docker-compose.yml` on port **3001**, and Alertmanager is available on port **9093**.

### Alert Rules

Example Prometheus alert rules (alert.rules.yml):

```yaml
groups:
  - name: chattingapp
    rules:
      - alert: HighErrorRate
        expr: rate(chattingapp_http_requests_total{http_status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected (5xx errors > 5%)"

      - alert: HighLatency
        expr: histogram_quantile(0.95, chattingapp_http_request_latency_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency exceeds 1 second"

      - alert: DatabaseQueryErrors
        expr: rate(chattingapp_db_query_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database query errors detected"
```

## Troubleshooting

### No metrics appearing

- Verify `/metrics` endpoint responds: `curl http://localhost:8000/metrics`
- Check `ENABLE_QUERY_PROFILING=true` to enable slow query logging
- Review logs for `"QueryLogger"` entries

### Sentry not receiving errors

- Verify `SENTRY_DSN` is set and valid
- Check Sentry project settings for SDK version compatibility
- Review backend logs for `"Sentry"` initialization messages

### OpenTelemetry traces not exported

- Verify `OTEL_EXPORTER_OTLP_ENDPOINT` is reachable from the backend container
- Check collector logs: `docker logs otel-collector`
- In development, set `ENABLE_TRACE_LOGGING=true` to see console traces

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
