# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\websocket\group_socket.py
import tracemalloc
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from firebase_admin import auth

from app.core.firebase import initialize_firebase_app
from app.core.observability import (
    WEBSOCKET_ACTIVE_CONNECTIONS,
    WEBSOCKET_CONNECTIONS,
    WEBSOCKET_DISCONNECTS,
    WEBSOCKET_ERRORS,
    WEBSOCKET_MESSAGES,
    WEBSOCKET_ROOM_COUNT,
    WEBSOCKET_DEVICE_CONNECTIONS,
    WEBSOCKET_MEMORY_USAGE_BYTES,
    WEBSOCKET_RECONCILIATION_REQUESTS,
    capture_exception,
)
from app.database.connection import AsyncSessionLocal
from app.services.group_service import (
    GroupError,
    get_group_messages_since,
    is_group_member,
    send_group_message,
    serialize_group_message,
)
from app.services.moderation_service import ModerationError, ModerationService
from app.services.user_service import UserService
from app.websocket.redis_broker import redis_broker

router = APIRouter()


class GroupConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[uuid.UUID, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self.device_connection_count: dict[tuple[uuid.UUID, str], int] = defaultdict(int)

    async def connect(self, group_id: uuid.UUID, websocket: WebSocket, device_id: str) -> None:
        await websocket.accept()
        self.active_connections[group_id][device_id].add(websocket)
        self.device_connection_count[(group_id, device_id)] += 1
        WEBSOCKET_CONNECTIONS.labels(channel="group").inc()
        WEBSOCKET_ACTIVE_CONNECTIONS.labels(channel="group").inc()
        WEBSOCKET_DEVICE_CONNECTIONS.labels(channel="group").set(
            sum(1 for (gid, _), count in self.device_connection_count.items() if gid == group_id)
        )
        WEBSOCKET_ROOM_COUNT.labels(channel="group").set(len(self.active_connections))
        self._update_memory_metric()

    def disconnect(self, group_id: uuid.UUID, websocket: WebSocket, device_id: str) -> None:
        device_map = self.active_connections.get(group_id)
        if not device_map:
            return

        sockets = device_map.get(device_id)
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                device_map.pop(device_id, None)

        if not device_map:
            self.active_connections.pop(group_id, None)

        self.device_connection_count[(group_id, device_id)] -= 1
        if self.device_connection_count[(group_id, device_id)] <= 0:
            self.device_connection_count.pop((group_id, device_id), None)

        WEBSOCKET_DISCONNECTS.labels(channel="group", reason="normal").inc()
        WEBSOCKET_ACTIVE_CONNECTIONS.labels(channel="group").dec()
        WEBSOCKET_DEVICE_CONNECTIONS.labels(channel="group").set(
            sum(1 for (gid, _), count in self.device_connection_count.items() if gid == group_id)
        )
        WEBSOCKET_ROOM_COUNT.labels(channel="group").set(len(self.active_connections))
        self._update_memory_metric()

    async def _broadcast_local(
        self,
        group_id: uuid.UUID,
        payload: dict,
        exclude_device_id: Optional[str] = None,
    ) -> None:
        disconnected: list[tuple[str, WebSocket]] = []
        for device_id, sockets in self.active_connections.get(group_id, {}).items():
            if device_id == exclude_device_id:
                continue
            for websocket in list(sockets):
                try:
                    clean_payload = dict(payload)
                    clean_payload.pop("_source_instance_id", None)
                    clean_payload.pop("_source_device_id", None)

                    await websocket.send_json(clean_payload)
                except Exception:
                    disconnected.append((device_id, websocket))

        for device_id, websocket in disconnected:
            self.disconnect(group_id, websocket, device_id)

    async def broadcast(
        self,
        group_id: uuid.UUID,
        payload: dict,
        exclude_device_id: Optional[str] = None,
    ) -> None:
        payload_with_origin = {
            **payload,
            "_source_instance_id": redis_broker.instance_id,
        }
        if exclude_device_id:
            payload_with_origin["_source_device_id"] = exclude_device_id

        await self._broadcast_local(group_id, payload_with_origin, exclude_device_id=exclude_device_id)
        if redis_broker.enabled:
            await redis_broker.publish(f"group:{group_id}", payload_with_origin)

    def _update_memory_metric(self) -> None:
        try:
            WEBSOCKET_MEMORY_USAGE_BYTES.set(tracemalloc.get_traced_memory()[1])
        except Exception:
            pass

    def parse_timestamp(self, timestamp: str | None) -> Optional[datetime]:
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None


manager = GroupConnectionManager()


async def _handle_group_pubsub(channel: str, payload: dict) -> None:
    if payload.get("_source_instance_id") == redis_broker.instance_id:
        return

    prefix = "group:"
    if not channel.startswith(prefix):
        return

    try:
        group_id = uuid.UUID(channel[len(prefix):])
    except ValueError:
        return

    await manager._broadcast_local(group_id, payload)


redis_broker.register_callback(_handle_group_pubsub)


async def _send_ws_error(websocket: WebSocket, message: str, code: str) -> None:
    await websocket.send_json({"type": "error", "error": message, "code": code})


async def _authenticate_websocket(token: str | None) -> uuid.UUID | None:
    if not token:
        return None

    initialize_firebase_app()
    try:
        decoded_token = auth.verify_id_token(token)
    except Exception as exc:
        return None

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        return None

    async with AsyncSessionLocal() as session:
        user = await UserService.get_user_by_firebase_uid(session, firebase_uid)
        return user.id if user else None


@router.websocket("/ws/groups/{group_id}")
async def group_chat_websocket(websocket: WebSocket, group_id: uuid.UUID) -> None:
    user_id = await _authenticate_websocket(websocket.query_params.get("token"))
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as session:
        allowed = await is_group_member(session, user_id, group_id)

    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    device_id = websocket.query_params.get("device_id") or uuid.uuid4().hex
    sync_since = manager.parse_timestamp(websocket.query_params.get("sync_since"))

    await manager.connect(group_id, websocket, device_id)

    if sync_since:
        WEBSOCKET_RECONCILIATION_REQUESTS.labels(channel="group").inc()
        async with AsyncSessionLocal() as session:
            messages = await get_group_messages_since(session, user_id, group_id, since=sync_since)
        if messages:
            await websocket.send_json({"type": "sync", "data": {"messages": messages}})

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = str(payload.get("type", "message"))
            WEBSOCKET_MESSAGES.labels(channel="group", event_type=event_type).inc()
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if event_type == "typing":
                await manager.broadcast(
                    group_id,
                    {
                        "type": "typing",
                        "data": {"user_id": str(user_id)},
                    },
                    exclude_device_id=device_id,
                )
                continue

            if event_type == "sync":
                since = manager.parse_timestamp(str(payload.get("since", "")))
                WEBSOCKET_RECONCILIATION_REQUESTS.labels(channel="group").inc()
                async with AsyncSessionLocal() as session:
                    messages = await get_group_messages_since(session, user_id, group_id, since=since)
                await websocket.send_json({"type": "sync", "data": {"messages": messages}})
                continue

            if event_type != "message":
                await _send_ws_error(websocket, "Unsupported event type", "group_event_unsupported")
                continue

            content = str(payload.get("content", "")).strip()
            if not content:
                await _send_ws_error(websocket, "Message content is required", "group_message_content_required")
                continue

            async with AsyncSessionLocal() as session:
                try:
                    user = await ModerationService.validate_user_can_send(session, str(user_id))
                    message = await send_group_message(session, user_id, group_id, content)
                    response = await serialize_group_message(session, message)
                except ModerationError as exc:
                    await _send_ws_error(websocket, str(exc), "group_moderation_rejected")
                    continue
                except GroupError as exc:
                    await _send_ws_error(websocket, str(exc), "group_message_rejected")
                    continue

            await websocket.send_json({"type": "group_message", "data": response})
            if not user.is_shadow_banned:
                await manager.broadcast(
                    group_id,
                    {"type": "group_message", "data": response},
                    exclude_device_id=device_id,
                )
    except WebSocketDisconnect:
        manager.disconnect(group_id, websocket, device_id)
    except Exception as exc:
        WEBSOCKET_ERRORS.labels(channel="group", stage="runtime").inc()
        capture_exception(exc)
        manager.disconnect(group_id, websocket, device_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
