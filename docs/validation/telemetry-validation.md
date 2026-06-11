# Telemetry Validation & System Observability

This document details the telemetry verification plan, metrics collection endpoints, logging specifications, and alerting limits for the ChattingApp ecosystem.

## Observability Stack Architecture

ChattingApp uses a standardized open-source monitoring stack to ensure backend instances, databases, and connection pools remain healthy:

```
[ Backend Replicas ] ----(Prometheus `/metrics`)----> [ Prometheus Server ]
        |                                                   |
 (Structured JSON Logs)                               (Data Source)
        |                                                   v
 [ Vector / Promtail ] ---> [ Grafana Loki ] <--- [ Grafana Dashboard ]
```

1. **Metrics Collection**: All backend instances expose a `/metrics` Prometheus-compatible endpoint.
2. **Log Aggregation**: Application logs are formatted as structured JSON for easy querying in Loki/Elastic.
3. **Dashboards**: Grafana aggregates Prometheus metrics and Loki logs into operational viewboards.

## Core Metrics Checklist

The Prometheus exporter gathers the following indicators:

| Metric Name | Type | Description | Target / SLA |
|---|---|---|---|
| `http_requests_total` | Counter | Total HTTP requests categorized by code and method. | 2xx/3xx > 99.5% |
| `http_request_duration_seconds` | Histogram | Request latency duration. | p95 < 200ms |
| `websocket_active_connections` | Gauge | Active real-time WebSocket client sessions. | Monitor scaling |
| `redis_connected_clients` | Gauge | Number of active connections to the Redis cluster. | < Redis maxlimit |
| `db_connection_pool_busy` | Gauge | Count of database connections currently active. | < Max pool size |

## Structured Logging Protocol

Backend logs must be outputted to `stdout` in structured JSON format when running in production:

```json
{
  "timestamp": "2026-06-11T12:30:45.123Z",
  "level": "INFO",
  "module": "app.services.media_service",
  "message": "Voice note transcoding completed successfully",
  "duration_ms": 145,
  "meta": {
    "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "content_type": "audio/webm",
    "size_bytes": 102400
  }
}
```

## Alerting Thresholds

The following alerts are configured inside Prometheus:
* **High HTTP Errors**: Triggered when `http_requests_total{status=~"5.."}` > 2% of total requests for 5 minutes.
* **Database Connection Exhaustion**: Triggered when `db_connection_pool_busy` > 90% of pool capacity for 2 minutes.
* **WebSocket Disconnection Spike**: Triggered if `websocket_active_connections` drops by > 40% in a 1-minute window (indicates network partition or proxy failure).
