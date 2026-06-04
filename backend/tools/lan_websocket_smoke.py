#!/usr/bin/env python
"""LAN/WebSocket smoke test for a running ChattingApp backend.

The full smoke requires two valid Firebase ID tokens so it can exercise the
same auth path as real LAN clients. CI can run ``--ci-guard`` without a live
backend to catch syntax/config regressions and keep the manual fallback docs
discoverable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

import requests
import websockets


DEFAULT_TIMEOUT_SECONDS = 20
CI_GUARD_DOC_TERMS = (
    "SMOKE_BASE_URL",
    "SMOKE_USER_A_TOKEN",
    "SMOKE_USER_B_TOKEN",
    "Manual fallback",
    "health/details",
    "direct chat",
    "group",
    "offline recovery",
    "Media upload",
)
CI_GUARD_SCRIPT_TERMS = (
    "/health",
    "/health/details",
    "/api/v1/users/register",
    "/api/v1/users/me",
    "/api/v1/posts/create",
    "/api/v1/posts/feed/",
    "/api/v1/chat/",
    "/messages/media",
    "/api/v1/groups",
    "/ws/chat/",
    "/ws/groups/",
    '"sync"',
    '"message"',
    '"group_message"',
)


@dataclass
class SmokeUser:
    label: str
    token: str
    username: str
    email: str
    id: str | None = None


class SmokeFailure(AssertionError):
    pass


class SmokeClient:
    def __init__(self, base_url: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def api_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def ws_url(self, path: str, params: dict[str, str]) -> str:
        parsed = urlparse(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        query = urlencode(params)
        return urlunparse((scheme, parsed.netloc, path, "", query, ""))

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        expected: tuple[int, ...] = (200,),
        **kwargs: Any,
    ) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = self.session.request(
            method,
            self.api_url(path),
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )
        if response.status_code not in expected:
            body = response.text[:500]
            raise SmokeFailure(f"{method} {path} returned {response.status_code}; expected {expected}; body={body}")
        if response.status_code == 204:
            return None
        try:
            payload = response.json()
        except ValueError as exc:
            raise SmokeFailure(f"{method} {path} did not return JSON: {response.text[:200]}") from exc
        return unwrap(payload)


def unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("success") is True and "data" in payload:
        return payload["data"]
    return payload


def require(value: Any, message: str) -> Any:
    if not value:
        raise SmokeFailure(message)
    return value


def assert_contains_message(messages: Any, text: str, label: str) -> None:
    if not isinstance(messages, list):
        raise SmokeFailure(f"{label} did not return a message list: {messages!r}")
    if not any(str(item.get("content", "")) == text for item in messages if isinstance(item, dict)):
        raise SmokeFailure(f"{label} did not include expected message content: {text!r}")


def register_or_get_user(client: SmokeClient, user: SmokeUser) -> SmokeUser:
    payload = {"username": user.username, "email": user.email, "bio": "LAN smoke test user"}
    result = client.request(
        "POST",
        "/api/v1/users/register",
        token=user.token,
        json=payload,
        expected=(201, 409),
    )
    if isinstance(result, dict) and result.get("id"):
        user.id = str(result["id"])
        return user

    result = client.request("GET", "/api/v1/users/me", token=user.token)
    user.id = str(require(result.get("id"), f"{user.label} /me response did not include id"))
    return user


async def receive_until(ws: Any, expected_type: str, timeout: int, content: str | None = None) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        payload = json.loads(raw)
        if payload.get("type") != expected_type:
            continue
        if content is None:
            return payload
        data = payload.get("data") or {}
        if isinstance(data, dict) and data.get("content") == content:
            return payload
        messages = data.get("messages") if isinstance(data, dict) else None
        if isinstance(messages, list) and any(item.get("content") == content for item in messages if isinstance(item, dict)):
            return payload
    raise SmokeFailure(f"Timed out waiting for WebSocket event {expected_type!r} content={content!r}")


async def smoke_direct_chat(client: SmokeClient, user_a: SmokeUser, user_b: SmokeUser, stamp: str) -> None:
    require(user_a.id and user_b.id, "direct chat needs both user ids")
    ws_b = client.ws_url(
        f"/ws/chat/{user_a.id}",
        {"token": user_b.token, "device_id": f"smoke-b-{stamp}"},
    )
    direct_text = f"smoke-direct-{stamp}"
    async with websockets.connect(ws_b, open_timeout=client.timeout) as receiver:
        await receiver.send(json.dumps({"type": "ping"}))
        await receive_until(receiver, "pong", client.timeout)
        client.request(
            "POST",
            f"/api/v1/chat/{user_b.id}/messages",
            token=user_a.token,
            json={"content": direct_text},
        )
        await receive_until(receiver, "message", client.timeout, direct_text)

    reconnect_ws = client.ws_url(
        f"/ws/chat/{user_a.id}",
        {
            "token": user_b.token,
            "device_id": f"smoke-b-reconnect-{stamp}",
            "sync_since": "1970-01-01T00:00:00+00:00",
        },
    )
    async with websockets.connect(reconnect_ws, open_timeout=client.timeout) as receiver:
        await receiver.send(json.dumps({"type": "sync", "since": "1970-01-01T00:00:00+00:00"}))
        sync_payload = await receive_until(receiver, "sync", client.timeout, direct_text)
        assert_contains_message(sync_payload.get("data", {}).get("messages"), direct_text, "direct reconnect sync")

    offline_text = f"smoke-direct-offline-{stamp}"
    offline_since = datetime.now(timezone.utc).isoformat()
    client.request(
        "POST",
        f"/api/v1/chat/{user_b.id}/messages",
        token=user_a.token,
        json={"content": offline_text},
    )
    offline_ws = client.ws_url(
        f"/ws/chat/{user_a.id}",
        {
            "token": user_b.token,
            "device_id": f"smoke-b-offline-{stamp}",
            "sync_since": offline_since,
        },
    )
    async with websockets.connect(offline_ws, open_timeout=client.timeout) as receiver:
        await receiver.send(json.dumps({"type": "sync", "since": offline_since}))
        sync_payload = await receive_until(receiver, "sync", client.timeout, offline_text)
        assert_contains_message(sync_payload.get("data", {}).get("messages"), offline_text, "direct offline recovery")


async def smoke_group_chat(client: SmokeClient, user_a: SmokeUser, user_b: SmokeUser, stamp: str) -> str:
    require(user_a.id and user_b.id, "group chat needs both user ids")
    group = client.request(
        "POST",
        "/api/v1/groups",
        token=user_a.token,
        json={
            "name": f"Smoke Group {stamp}",
            "description": "LAN smoke test group",
            "type": "public",
            "category": "Smoke",
            "tags": ["smoke", "lan"],
        },
        expected=(201,),
    )
    group_id = str(require(group.get("id"), "group create response did not include id"))
    client.request("POST", f"/api/v1/groups/{group_id}/join", token=user_b.token)

    group_ws = client.ws_url(
        f"/ws/groups/{group_id}",
        {"token": user_b.token, "device_id": f"smoke-group-b-{stamp}"},
    )
    group_text = f"smoke-group-{stamp}"
    async with websockets.connect(group_ws, open_timeout=client.timeout) as receiver:
        await receiver.send(json.dumps({"type": "ping"}))
        await receive_until(receiver, "pong", client.timeout)
        client.request(
            "POST",
            f"/api/v1/groups/{group_id}/messages",
            token=user_a.token,
            json={"content": group_text},
        )
        await receive_until(receiver, "group_message", client.timeout, group_text)

    offline_text = f"smoke-group-offline-{stamp}"
    offline_since = datetime.now(timezone.utc).isoformat()
    client.request(
        "POST",
        f"/api/v1/groups/{group_id}/messages",
        token=user_a.token,
        json={"content": offline_text},
    )
    reconnect_ws = client.ws_url(
        f"/ws/groups/{group_id}",
        {
            "token": user_b.token,
            "device_id": f"smoke-group-reconnect-{stamp}",
            "sync_since": offline_since,
        },
    )
    async with websockets.connect(reconnect_ws, open_timeout=client.timeout) as receiver:
        await receiver.send(json.dumps({"type": "sync", "since": offline_since}))
        sync_payload = await receive_until(receiver, "sync", client.timeout, offline_text)
        assert_contains_message(sync_payload.get("data", {}).get("messages"), offline_text, "group offline recovery")
    return group_id


def smoke_upload(client: SmokeClient, user_a: SmokeUser, user_b: SmokeUser, stamp: str) -> None:
    require(user_b.id, "upload smoke needs user B id")
    files = {"file": (f"smoke-{stamp}.txt", BytesIO(b"chattingapp smoke upload\n"), "text/plain")}
    data = {"caption": f"smoke-upload-{stamp}"}
    result = client.request(
        "POST",
        f"/api/v1/chat/{user_b.id}/messages/media",
        token=user_a.token,
        files=files,
        data=data,
    )
    require(result.get("media_url"), "media upload response did not include media_url")


def smoke_feed(client: SmokeClient, user: SmokeUser, stamp: str) -> None:
    require(user.id, "feed smoke needs user id")
    text = f"smoke-feed-{stamp}"
    post = client.request(
        "POST",
        "/api/v1/posts/create",
        token=user.token,
        json={"content": text, "visibility": "public"},
        expected=(201,),
    )
    require(post.get("id"), "post create response did not include id")
    feed = client.request("GET", f"/api/v1/posts/feed/{user.id}", token=user.token)
    items = require(feed.get("feed"), "feed response did not include feed")
    if not any(isinstance(item, dict) and item.get("content") == text for item in items):
        raise SmokeFailure("new smoke post was not present in personalized feed")


def run_ci_guard(repo_root: Path) -> None:
    docs_path = repo_root / "docs" / "LAN_WEBSOCKET_SMOKE.md"
    if not docs_path.is_file():
        raise SmokeFailure("docs/LAN_WEBSOCKET_SMOKE.md is missing")
    docs = docs_path.read_text(encoding="utf-8")
    missing = [term for term in CI_GUARD_DOC_TERMS if term not in docs]
    if missing:
        raise SmokeFailure(f"smoke docs are missing required terms: {', '.join(missing)}")

    script = Path(__file__).read_text(encoding="utf-8")
    missing = [term for term in CI_GUARD_SCRIPT_TERMS if term not in script]
    if missing:
        raise SmokeFailure(f"smoke script is missing required coverage terms: {', '.join(missing)}")

    print("CI guard passed: smoke script coverage contract and fallback docs are present.")


async def run_full_smoke(args: argparse.Namespace) -> None:
    token_a = os.getenv("SMOKE_USER_A_TOKEN")
    token_b = os.getenv("SMOKE_USER_B_TOKEN")
    if not token_a or not token_b:
        raise SmokeFailure("SMOKE_USER_A_TOKEN and SMOKE_USER_B_TOKEN are required for full smoke")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    user_a = SmokeUser(
        "user A",
        token_a,
        os.getenv("SMOKE_USER_A_USERNAME", f"smoke_a_{stamp}"),
        os.getenv("SMOKE_USER_A_EMAIL", f"smoke-a-{stamp}@example.test"),
    )
    user_b = SmokeUser(
        "user B",
        token_b,
        os.getenv("SMOKE_USER_B_USERNAME", f"smoke_b_{stamp}"),
        os.getenv("SMOKE_USER_B_EMAIL", f"smoke-b-{stamp}@example.test"),
    )
    client = SmokeClient(args.base_url, args.timeout)

    health = client.request("GET", "/health")
    if health.get("status") != "ok":
        raise SmokeFailure(f"/health was not ok: {health!r}")
    details = client.request("GET", "/health/details")
    if details.get("status") not in {"ok", "degraded"}:
        raise SmokeFailure(f"/health/details status was unexpected: {details!r}")

    register_or_get_user(client, user_a)
    register_or_get_user(client, user_b)
    smoke_feed(client, user_a, stamp)
    await smoke_direct_chat(client, user_a, user_b, stamp)
    await smoke_group_chat(client, user_a, user_b, stamp)
    smoke_upload(client, user_a, user_b, stamp)

    print("Full LAN/WebSocket smoke passed.")
    print(f"Base URL: {client.base_url}")
    print(f"Users: {user_a.id}, {user_b.id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ChattingApp LAN/WebSocket smoke checks.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000"),
        help="Backend origin to test, for example http://192.168.1.25:8000.",
    )
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SMOKE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    parser.add_argument("--ci-guard", action="store_true", help="Validate smoke script/docs without a live backend.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    try:
        if args.ci_guard:
            run_ci_guard(repo_root)
        else:
            asyncio.run(run_full_smoke(args))
    except SmokeFailure as exc:
        print(f"Smoke failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Smoke crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
