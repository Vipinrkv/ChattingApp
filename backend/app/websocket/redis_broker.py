#backend/app/websocket/redis_broker.py
import asyncio
import json
import uuid
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis, from_url
from redis.asyncio.client import PubSub
import logging

logger = logging.getLogger(__name__)

from app.core.config import settings

RedisCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class RedisBroker:
    def __init__(self) -> None:
        self.instance_id = uuid.uuid4().hex
        self.enabled = False
        self.redis: Redis | None = None
        self.pubsub: PubSub | None = None
        self.listener_task: asyncio.Task | None = None
        self.callbacks: list[RedisCallback] = []

    async def initialize(self) -> None:
        if self.enabled:
            return
        if not settings.REDIS_URL:
            return

        self.redis = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        )
        try:
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            await self.pubsub.psubscribe("chat:user:*", "group:*")
            self.listener_task = asyncio.create_task(self._listen_loop())
            self.enabled = True
        except Exception as exc:
            logger.warning("Redis broker unavailable: %s", exc)
            await self.shutdown()

    async def shutdown(self) -> None:
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None

        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None

        if self.redis:
            await self.redis.aclose()
            self.redis = None

        self.enabled = False

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        if not self.redis:
            return
        try:
            await self.redis.publish(channel, json.dumps(payload))
        except Exception as exc:
            logger.exception("Redis publish failed: %s", exc)

    def _presence_key(self, user_id: uuid.UUID) -> str:
        return f"ws:user:{user_id}:count"

    async def increment_presence(self, user_id: uuid.UUID) -> int:
        if not self.redis:
            return 0
        try:
            key = self._presence_key(user_id)
            count = await self.redis.incr(key)
            await self.redis.expire(key, 60)
            return int(count)
        except Exception as exc:
            logger.exception("Redis presence increment failed: %s", exc)
            return 0

    async def decrement_presence(self, user_id: uuid.UUID) -> int:
        if not self.redis:
            return 0
        try:
            key = self._presence_key(user_id)
            count = await self.redis.decr(key)
            if count <= 0:
                await self.redis.delete(key)
                return 0
            await self.redis.expire(key, 60)
            return int(count)
        except Exception as exc:
            logger.exception("Redis presence decrement failed: %s", exc)
            return 0

    async def get_presence_count(self, user_id: uuid.UUID) -> int:
        if not self.redis:
            return 0
        try:
            key = self._presence_key(user_id)
            value = await self.redis.get(key)
            return int(value) if value and str(value).isdigit() else 0
        except Exception as exc:
            logger.exception("Redis presence count lookup failed: %s", exc)
            return 0

    async def _listen_loop(self) -> None:
        assert self.pubsub is not None
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    continue

                if message["type"] != "message":
                    continue

                channel = message["channel"]
                payload = json.loads(message["data"])
                for callback in list(self.callbacks):
                    await callback(channel, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Redis listener error: %s", exc)
                await asyncio.sleep(1)

    def register_callback(self, callback: RedisCallback) -> None:
        self.callbacks.append(callback)


redis_broker = RedisBroker()
