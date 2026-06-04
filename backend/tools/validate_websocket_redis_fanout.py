"""Validate WebSocket delivery across two backend replicas.

Run this after starting two backend replicas against the same Redis instance.
The validation connects user A to replica A and user B to replica B, verifies
direct message fanout, group message fanout, and reconnect sync recovery.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

import websockets


def _ws_url(base_url: str, route: str, resource_id: str, token: str, device_id: str, sync_since: str | None = None) -> str:
    base = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    url = f"{base}/ws/{route}/{resource_id}?token={token}&device_id={device_id}"
    if sync_since:
        url += f"&sync_since={sync_since}"
    return url


async def _wait_for_type(ws, event_type: str, timeout: float, content: str | None = None) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - asyncio.get_running_loop().time()))
        payload = json.loads(raw)
        if payload.get("type") != event_type:
            continue
        if content is None:
            return payload
        data = payload.get("data") or {}
        if isinstance(data, dict) and data.get("content") == content:
            return payload
        messages = data.get("messages") if isinstance(data, dict) else None
        if isinstance(messages, list) and any(item.get("content") == content for item in messages if isinstance(item, dict)):
            return payload
    raise TimeoutError(f"Timed out waiting for event type {event_type!r} content={content!r}")


async def _validate_direct(args: argparse.Namespace) -> str:
    marker = f"fanout-direct-{uuid.uuid4()}"
    url_a = _ws_url(args.replica_a, "chat", args.user_b_id, args.user_a_token, f"fanout-a-{uuid.uuid4().hex}")
    url_b = _ws_url(args.replica_b, "chat", args.user_a_id, args.user_b_token, f"fanout-b-{uuid.uuid4().hex}")

    async with websockets.connect(url_b, open_timeout=args.timeout) as receiver:
        async with websockets.connect(url_a, open_timeout=args.timeout) as sender:
            await sender.send(json.dumps({"type": "message", "content": marker}))
            await _wait_for_type(receiver, "message", args.timeout, marker)
    return marker


async def _validate_group(args: argparse.Namespace) -> str:
    marker = f"fanout-group-{uuid.uuid4()}"
    url_a = _ws_url(args.replica_a, "groups", args.group_id, args.user_a_token, f"fanout-group-a-{uuid.uuid4().hex}")
    url_b = _ws_url(args.replica_b, "groups", args.group_id, args.user_b_token, f"fanout-group-b-{uuid.uuid4().hex}")

    async with websockets.connect(url_b, open_timeout=args.timeout) as receiver:
        async with websockets.connect(url_a, open_timeout=args.timeout) as sender:
            await sender.send(json.dumps({"type": "message", "content": marker}))
            await _wait_for_type(receiver, "group_message", args.timeout, marker)
    return marker


async def _validate_reconnect(args: argparse.Namespace) -> tuple[str, str]:
    since = datetime.now(timezone.utc).isoformat()
    direct_marker = f"fanout-reconnect-direct-{uuid.uuid4()}"
    url_a = _ws_url(args.replica_a, "chat", args.user_b_id, args.user_a_token, f"fanout-reconnect-a-{uuid.uuid4().hex}")

    async with websockets.connect(url_a, open_timeout=args.timeout) as sender:
        await sender.send(json.dumps({"type": "message", "content": direct_marker}))

    url_b = _ws_url(
        args.replica_b,
        "chat",
        args.user_a_id,
        args.user_b_token,
        f"fanout-reconnect-b-{uuid.uuid4().hex}",
        sync_since=since,
    )
    async with websockets.connect(url_b, open_timeout=args.timeout) as receiver:
        await receiver.send(json.dumps({"type": "sync", "since": since}))
        await _wait_for_type(receiver, "sync", args.timeout, direct_marker)

    group_marker = f"fanout-reconnect-group-{uuid.uuid4()}"
    group_sender_url = _ws_url(args.replica_a, "groups", args.group_id, args.user_a_token, f"fanout-group-reconnect-a-{uuid.uuid4().hex}")
    async with websockets.connect(group_sender_url, open_timeout=args.timeout) as sender:
        await sender.send(json.dumps({"type": "message", "content": group_marker}))

    group_receiver_url = _ws_url(
        args.replica_b,
        "groups",
        args.group_id,
        args.user_b_token,
        f"fanout-group-reconnect-b-{uuid.uuid4().hex}",
        sync_since=since,
    )
    async with websockets.connect(group_receiver_url, open_timeout=args.timeout) as receiver:
        await receiver.send(json.dumps({"type": "sync", "since": since}))
        await _wait_for_type(receiver, "sync", args.timeout, group_marker)

    return direct_marker, group_marker


async def validate(args: argparse.Namespace) -> None:
    direct_marker = await _validate_direct(args)
    group_marker = await _validate_group(args)
    reconnect_direct_marker, reconnect_group_marker = await _validate_reconnect(args)
    print(json.dumps({
        "status": "passed",
        "replica_a_user": args.user_a_id,
        "replica_b_user": args.user_b_id,
        "group_id": args.group_id,
        "direct_message_marker": direct_marker,
        "group_message_marker": group_marker,
        "direct_reconnect_marker": reconnect_direct_marker,
        "group_reconnect_marker": reconnect_group_marker,
    }, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate two-replica WebSocket Redis fanout.")
    parser.add_argument("--replica-a", required=True, help="Base URL for backend replica A, for example http://127.0.0.1:8001")
    parser.add_argument("--replica-b", required=True, help="Base URL for backend replica B, for example http://127.0.0.1:8002")
    parser.add_argument("--user-a-id", required=True, help="Database UUID for user A")
    parser.add_argument("--user-b-id", required=True, help="Database UUID for user B")
    parser.add_argument("--group-id", required=True, help="Group UUID where both validation users are members")
    parser.add_argument("--user-a-token", required=True, help="Firebase ID token for user A")
    parser.add_argument("--user-b-token", required=True, help="Firebase ID token for user B")
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(validate(args))
    except Exception as exc:
        print(f"fanout validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("fanout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
