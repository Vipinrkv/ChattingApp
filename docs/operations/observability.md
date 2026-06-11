# Observability & Monitoring Platform

This document details the self-hosted monitoring, alerting, and telemetry collection systems for ChattingApp.

---

## 1. Observability Topology

We use a fully open-source, zero-cost observability stack:

- **Instrumentation**: OpenTelemetry (OTel) python SDK logs API execution routes, query timings, and WebSocket errors.
- **Metrics Storage**: Prometheus scrapes application metrics from the backend endpoint.
- **Visualization**: Grafana queries Prometheus to render real-time health dashboards.

```
+------------------+     OTel Metrics     +------------------+
| FastAPI Replicas | -------------------> | Prometheus Engine |
+------------------+                      +------------------+
                                                   |
                                                   v
+------------------+                      +------------------+
| Operations Staff | <------------------- | Grafana Console  |
+------------------+    Slack Alerts      +------------------+
```

---

## 2. Telemetry & Metrics Scrape Config

Prometheus scrapes the backend metrics at regular intervals. The metrics endpoint is served at `/metrics` by the `prometheus_client` integration:

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'chattingapp-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

---

## 3. Core Operational Metrics

We export and track the following metrics to determine system health:

- `chattingapp_http_requests_total`: Counter for HTTP status codes (2xx, 3xx, 4xx, 5xx) to monitor error rates.
- `chattingapp_websocket_connections_active`: Gauge tracking the current active WebSocket connections per backend replica.
- `chattingapp_db_query_duration_seconds`: Histogram tracking database query execution times.
- `chattingapp_redis_cache_hits_total` / `misses_total`: Counters to check cache efficiency.

---

## 4. Alerting Thresholds

Alerts are configured within Prometheus Alertmanager to notify operations staff (e.g. via Discord webhooks or Slack):

1. **High HTTP Error Rate**: Trigger alert if HTTP 5xx error rate exceeds 2% of total traffic over a 5-minute window.
2. **WebSocket Connection Drop**: Trigger alert if active WebSocket connections drop by more than 50% within a 1-minute window (indicates network partition or proxy issues).
3. **Database Latency**: Trigger alert if 95th percentile query duration (`p95`) exceeds 2.5 seconds.
