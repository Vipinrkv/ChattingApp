import json
import logging
from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self) -> None:
        self.redis: Redis | None = None
        self.enabled = False

    async def initialize(self) -> None:
        if self.enabled or not settings.REDIS_URL:
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
            self.enabled = True
        except Exception as exc:
            logger.warning("Redis cache unavailable: %s", exc)
            self.enabled = False
            if self.redis:
                await self.redis.close()
                self.redis = None

    async def shutdown(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None
        self.enabled = False

    async def get(self, key: str) -> str | None:
        if not self.redis:
            return None
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if not self.redis:
            return
        await self.redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        if not self.redis:
            return
        await self.redis.delete(key)

    async def increment(self, key: str, ex: int | None = None) -> int:
        if not self.redis:
            return 0
        value = await self.redis.incr(key)
        if ex is not None:
            await self.redis.expire(key, ex)
        return int(value)

    async def get_json(self, key: str) -> dict | list | None:
        raw = await self.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: dict | list, ex: int | None = None) -> None:
        await self.set(key, json.dumps(value, default=str), ex=ex)


redis_cache = RedisCache()
