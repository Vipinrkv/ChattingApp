# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\websocket\chat_socket.py
import tracemalloc
import uuid
import logging
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
from app.services.chat_service import ChatError, get_conversation_since, send_message, serialize_message
from app.services.moderation_service import ModerationError, ModerationService
from app.services.user_service import UserService
from app.websocket.redis_broker import redis_broker

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[tuple[uuid.UUID, uuid.UUID], dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self.user_connection_count: dict[uuid.UUID, int] = defaultdict(int)
        self.device_connection_count: dict[tuple[uuid.UUID, str], int] = defaultdict(int)

    async def connect(
        self,
        user_id: uuid.UUID,
        peer_id: uuid.UUID,
        websocket: WebSocket,
        device_id: str,
    ) -> None:
        await websocket.accept()
        key = (user_id, peer_id)
        self.active_connections[key][device_id].add(websocket)
        self.user_connection_count[user_id] += 1
        self.device_connection_count[(user_id, device_id)] += 1

        WEBSOCKET_CONNECTIONS.labels(channel="chat").inc()
        WEBSOCKET_ACTIVE_CONNECTIONS.labels(channel="chat").inc()
        WEBSOCKET_DEVICE_CONNECTIONS.labels(channel="chat").set(
            sum(1 for (uid, _), count in self.device_connection_count.items() if uid == user_id)
        )
        WEBSOCKET_ROOM_COUNT.labels(channel="chat").set(len(self.active_connections))
        self._update_memory_metric()

    def disconnect(
        self,
        user_id: uuid.UUID,
        peer_id: uuid.UUID,
        websocket: WebSocket,
        device_id: str,
    ) -> bool:
        key = (user_id, peer_id)
        device_map = self.active_connections.get(key)
        if not device_map:
            return False

        sockets = device_map.get(device_id)
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                device_map.pop(device_id, None)

        if not device_map:
            self.active_connections.pop(key, None)

        self.user_connection_count[user_id] -= 1
        self.device_connection_count[(user_id, device_id)] -= 1
        if self.device_connection_count[(user_id, device_id)] <= 0:
            self.device_connection_count.pop((user_id, device_id), None)

        WEBSOCKET_DISCONNECTS.labels(channel="chat", reason="normal").inc()
        WEBSOCKET_ACTIVE_CONNECTIONS.labels(channel="chat").dec()
        WEBSOCKET_DEVICE_CONNECTIONS.labels(channel="chat").set(
            sum(1 for (uid, _), count in self.device_connection_count.items() if uid == user_id)
        )
        WEBSOCKET_ROOM_COUNT.labels(channel="chat").set(len(self.active_connections))
        self._update_memory_metric()

        if self.user_connection_count[user_id] <= 0:
            self.user_connection_count.pop(user_id, None)
            return True

        return False

    async def _send_local(
        self,
        user_id: uuid.UUID,
        payload: dict,
        exclude_device_id: Optional[str] = None,
    ) -> None:
        disconnected: list[tuple[tuple[uuid.UUID, uuid.UUID], str, WebSocket]] = []

        for key, device_map in self.active_connections.items():
            if key[0] != user_id:
                continue

            for device_id, sockets in device_map.items():
                if device_id == exclude_device_id:
                    continue

                for websocket in list(sockets):
                    try:
                        clean_payload = dict(payload)
                        clean_payload.pop("_source_instance_id", None)
                        clean_payload.pop("_source_device_id", None)

                        await websocket.send_json(clean_payload)
                    except Exception:
                        disconnected.append((key, device_id, websocket))

        for key, device_id, websocket in disconnected:
            self.disconnect(key[0], key[1], websocket, device_id)

    async def send_to_user(
        self,
        user_id: uuid.UUID,
        payload: dict,
        exclude_device_id: Optional[str] = None,
    ) -> None:
        payload_with_origin = {
            **payload,
            "_source_instance_id": redis_broker.instance_id,
        }
        if exclude_device_id:
            payload_with_origin["_source_device_id"] = exclude_device_id

        await self._send_local(user_id, payload_with_origin, exclude_device_id=exclude_device_id)
        if redis_broker.enabled:
            await redis_broker.publish(f"chat:user:{user_id}", payload_with_origin)

    async def register_connection(self, user_id: uuid.UUID) -> int:
        if redis_broker.enabled:
            return await redis_broker.increment_presence(user_id)
        return self.user_connection_count.get(user_id, 0)

    async def unregister_connection(self, user_id: uuid.UUID) -> int:
        if redis_broker.enabled:
            return await redis_broker.decrement_presence(user_id)
        return self.user_connection_count.get(user_id, 0)

    def parse_timestamp(self, timestamp: str | None) -> Optional[datetime]:
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _update_memory_metric(self) -> None:
        try:
            WEBSOCKET_MEMORY_USAGE_BYTES.set(tracemalloc.get_traced_memory()[1])
        except Exception:
            pass


manager = ChatConnectionManager()


async def _handle_chat_pubsub(channel: str, payload: dict) -> None:
    if payload.get("_source_instance_id") == redis_broker.instance_id:
        return

    prefix = "chat:user:"
    if not channel.startswith(prefix):
        return

    try:
        user_id = uuid.UUID(channel[len(prefix):])
    except ValueError:
        return

    await manager._send_local(
        user_id,
        payload,
        exclude_device_id=payload.get("_source_device_id"),
    )


redis_broker.register_callback(_handle_chat_pubsub)


async def _send_ws_error(websocket: WebSocket, message: str, code: str) -> None:
    await websocket.send_json({"type": "error", "error": message, "code": code})


def _extract_websocket_token(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if token:
        return token

    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()

    protocol = websocket.headers.get("sec-websocket-protocol", "")
    for part in protocol.split(","):
        value = part.strip()
        if value.lower().startswith("bearer."):
            return value.split(".", 1)[1]
    return None


async def _authenticate_websocket(token: str | None) -> uuid.UUID | None:
    if not token:
        logger.warning("websocket_auth_failed", extra={"reason": "missing_token"})
        return None

    initialize_firebase_app()
    try:
        decoded_token = auth.verify_id_token(token)
    except Exception as exc:
        logger.warning(
            "websocket_auth_failed",
            extra={"reason": "invalid_firebase_token", "exception_type": type(exc).__name__, "exception_message": str(exc)},
        )
        return None

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        logger.warning("websocket_auth_failed", extra={"reason": "missing_firebase_uid"})
        return None

    async with AsyncSessionLocal() as session:
        user = await UserService.get_user_by_firebase_uid(session, firebase_uid)
        if not user:
            logger.warning("websocket_auth_failed", extra={"reason": "user_not_found", "firebase_uid": firebase_uid})
            return None
        return user.id


async def _resolve_user_identifier(identifier: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(identifier)
    except ValueError:
        pass

    async with AsyncSessionLocal() as session:
        user = await UserService.get_user_by_firebase_uid(session, identifier)
        return user.id if user else None


@router.websocket("/ws/chat/{peer_id}")
async def chat_websocket(websocket: WebSocket, peer_id: str) -> None:
    user_id = await _authenticate_websocket(_extract_websocket_token(websocket))
    if user_id is None:
        logger.warning("websocket_rejected", extra={"path": websocket.url.path, "peer_id": peer_id, "reason": "auth_failed"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    peer_uuid = await _resolve_user_identifier(peer_id)
    if peer_uuid is None:
        logger.warning("websocket_rejected", extra={"path": websocket.url.path, "user_id": str(user_id), "peer_id": peer_id, "reason": "peer_not_found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    device_id = websocket.query_params.get("device_id") or uuid.uuid4().hex
    sync_since = manager.parse_timestamp(websocket.query_params.get("sync_since"))

    await manager.connect(user_id, peer_uuid, websocket, device_id)
    first_connection = await manager.register_connection(user_id)

    if first_connection == 1:
        await manager.send_to_user(peer_uuid, {
            "type": "presence",
            "data": {
                "user_id": str(user_id),
                "status": "online",
            },
        })

    if sync_since:
        WEBSOCKET_RECONCILIATION_REQUESTS.labels(channel="chat").inc()
        async with AsyncSessionLocal() as session:
            messages = await get_conversation_since(session, user_id, peer_uuid, since=sync_since)
        if messages:
            await websocket.send_json({"type": "sync", "data": {"messages": messages}})

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = str(payload.get("type", "message"))
            WEBSOCKET_MESSAGES.labels(channel="chat", event_type=event_type).inc()
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if event_type == "typing":
                await manager.send_to_user(peer_uuid, {
                    "type": "typing",
                    "data": {
                        "user_id": str(user_id),
                    },
                }, exclude_device_id=device_id)
                continue

            if event_type == "message_read":
                message_id = str(payload.get("message_id", ""))
                if message_id:
                    await manager.send_to_user(peer_uuid, {
                        "type": "read_receipt",
                        "data": {
                            "message_id": message_id,
                            "reader_id": str(user_id),
                        },
                    }, exclude_device_id=device_id)
                    continue
                await _send_ws_error(websocket, "message_id is required for read receipts", "chat_read_receipt_invalid")
                continue

            if event_type == "sync":
                since = manager.parse_timestamp(str(payload.get("since", "")))
                WEBSOCKET_RECONCILIATION_REQUESTS.labels(channel="chat").inc()
                async with AsyncSessionLocal() as session:
                    messages = await get_conversation_since(session, user_id, peer_uuid, since=since)
                await websocket.send_json({"type": "sync", "data": {"messages": messages}})
                continue

            if event_type != "message":
                await _send_ws_error(websocket, "Unsupported event type", "chat_event_unsupported")
                continue

            content = str(payload.get("content", "")).strip()
            if not content:
                await _send_ws_error(websocket, "Message content is required", "chat_message_content_required")
                continue

            async with AsyncSessionLocal() as session:
                try:
                    user = await ModerationService.validate_user_can_send(session, str(user_id))
                    message = await send_message(session, user_id, peer_uuid, content)
                    response = serialize_message(message)
                except ModerationError as exc:
                    await _send_ws_error(websocket, str(exc), "chat_moderation_rejected")
                    continue
                except ChatError as exc:
                    await _send_ws_error(websocket, str(exc), "chat_message_rejected")
                    continue

            await manager.send_to_user(user_id, {"type": "message", "data": response}, exclude_device_id=device_id)

            if not user.is_shadow_banned:
                await manager.send_to_user(peer_uuid, {"type": "message", "data": response})
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", extra={"user_id": str(user_id), "peer_id": str(peer_uuid), "device_id": device_id})
        manager.disconnect(user_id, peer_uuid, websocket, device_id)
        global_connections = await manager.unregister_connection(user_id)
        if global_connections == 0:
            await manager.send_to_user(peer_uuid, {
                "type": "presence",
                "data": {
                    "user_id": str(user_id),
                    "status": "offline",
                },
            })
    except Exception as exc:
        logger.exception(
            "websocket_runtime_error",
            extra={"user_id": str(user_id), "peer_id": str(peer_uuid), "device_id": device_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
        )
        WEBSOCKET_ERRORS.labels(channel="chat", stage="runtime").inc()
        capture_exception(exc)
        manager.disconnect(user_id, peer_uuid, websocket, device_id)
        global_connections = await manager.unregister_connection(user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
        if global_connections == 0:
            await manager.send_to_user(peer_uuid, {
                "type": "presence",
                "data": {
                    "user_id": str(user_id),
                    "status": "offline",
                },
            })
