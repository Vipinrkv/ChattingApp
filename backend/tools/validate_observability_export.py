"""Validate hosted observability wiring for a deployed ChattingApp backend."""
from __future__ import annotations

import argparse
import os
import sys

import httpx


def _get_json(client: httpx.Client, path: str) -> dict:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def validate(args: argparse.Namespace) -> None:
    required_env = {
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        "OTEL_SERVICE_NAME": os.getenv("OTEL_SERVICE_NAME"),
    }
    missing = [key for key, value in required_env.items() if not value]
    if missing and not args.allow_missing_env:
        raise RuntimeError(f"Missing hosted trace env vars: {', '.join(missing)}")

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=args.timeout) as client:
        health = _get_json(client, "/health/details")
        if health.get("status") not in {"ok", "degraded"}:
            raise AssertionError(f"Unexpected health payload: {health}")

        performance = _get_json(client, "/performance")
        if "http_requests_total" not in performance:
            raise AssertionError(f"Performance summary missing counters: {performance}")

        metrics = client.get("/metrics")
        metrics.raise_for_status()
        body = metrics.text
        for metric in ("chattingapp_http_requests_total", "chattingapp_websocket_connections_total"):
            if metric not in body:
                raise AssertionError(f"Prometheus metric {metric} not exposed")

        if args.send_sentry_test:
            response = client.get("/__force_sentry_validation__")
            if response.status_code < 500:
                raise AssertionError("Sentry validation endpoint should return a server error when enabled")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate hosted OpenTelemetry/Sentry observability exports.")
    parser.add_argument("--base-url", required=True, help="Hosted backend URL, for example https://api.example.com")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--allow-missing-env", action="store_true", help="Allow local smoke checks without hosted OTEL env vars")
    parser.add_argument("--send-sentry-test", action="store_true", help="Reserved for environments with a deliberate error-test endpoint")
    return parser.parse_args()


def main() -> int:
    try:
        validate(parse_args())
    except Exception as exc:
        print(f"observability validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("observability validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
