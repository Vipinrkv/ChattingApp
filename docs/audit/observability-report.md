# Observability Report

This report outlines the self-hosted Prometheus, Grafana, and OpenTelemetry observability platform.

---

## 1. Metrics & Logs Collector
- **OTel Exporter**: Exports metrics and spans to a central OpenTelemetry collector.
- **Prometheus Scrapes**: Collects system indicators from the `/metrics` endpoint including active sockets counts, query timings, HTTP error rates, and cache hits.

---

## 2. Alerts Configuration
- **API Outages**: Trigger alerts if HTTP 5xx errors exceed 2% of total traffic.
- **WebSocket Connection Drops**: Trigger alerts if socket connections drop by >50% within a 1-minute window.
- **Latencies**: Trigger alerts if database query latency exceeds 2.5 seconds.
