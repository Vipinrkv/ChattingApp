from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis, from_url
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    from_url = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

try:
    import aiokafka  # type: ignore[import]
    from aiokafka import AIOKafkaProducer
    _KAFKA_AVAILABLE = True
except ImportError:  # pragma: no cover
    AIOKafkaProducer = None  # type: ignore[assignment]
    _KAFKA_AVAILABLE = False


class EventBus:
    backend_name = "in-memory"

    async def initialize(self) -> None:
        return

    async def shutdown(self) -> None:
        return

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    backend_name = "in-memory"

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        logger.debug("InMemoryEventBus.publish %s %s", topic, payload)


class RedisEventBus(EventBus):
    backend_name = "redis"

    def __init__(self, redis_url: str, topic_prefix: str) -> None:
        self.redis_url = redis_url
        self.topic_prefix = topic_prefix
        self.redis: Redis | None = None

    async def initialize(self) -> None:
        if not _REDIS_AVAILABLE:
            raise RuntimeError("redis package is required for RedisEventBus")

        self.redis = from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        )
        await self.redis.ping()

    async def shutdown(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.redis:
            logger.warning("RedisEventBus.publish skipped because Redis is unavailable")
            return
        channel = f"{self.topic_prefix}:{topic}"
        await self.redis.publish(channel, json.dumps(payload, default=str))


class KafkaEventBus(EventBus):
    backend_name = "kafka"

    def __init__(self, bootstrap_servers: str, topic_prefix: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = None

    async def initialize(self) -> None:
        if not _KAFKA_AVAILABLE:
            raise RuntimeError("aiokafka package is required for KafkaEventBus")

        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()

    async def shutdown(self) -> None:
        if self.producer:
            await self.producer.stop()
            self.producer = None

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.producer:
            logger.warning("KafkaEventBus.publish skipped because Kafka producer is not initialized")
            return
        channel = f"{self.topic_prefix}.{topic}"
        await self.producer.send_and_wait(channel, json.dumps(payload, default=str).encode("utf-8"))


def build_event_bus() -> EventBus:
    if settings.KAFKA_BOOTSTRAP_SERVERS:
        if _KAFKA_AVAILABLE:
            return KafkaEventBus(settings.KAFKA_BOOTSTRAP_SERVERS, settings.EVENT_BUS_TOPIC_PREFIX)
        logger.warning("KAFKA_BOOTSTRAP_SERVERS configured but aiokafka is not installed. Falling back to Redis or in-memory event bus.")

    if settings.REDIS_URL and _REDIS_AVAILABLE:
        return RedisEventBus(settings.REDIS_URL, settings.EVENT_BUS_TOPIC_PREFIX)

    return InMemoryEventBus()


event_bus = build_event_bus()
