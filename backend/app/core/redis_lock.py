from __future__ import annotations
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.core.redis_cache import redis_cache

logger = logging.getLogger(__name__)

UNLOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLockError(Exception):
    pass


class RedisLock:
    def __init__(self) -> None:
        self.redis: Redis | None = None

    async def _ensure_redis(self) -> Redis:
        if redis_cache.enabled and redis_cache.redis is not None:
            return redis_cache.redis

        if self.redis is None:
            self.redis = from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            )
        return self.redis

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.close()
            self.redis = None

    async def acquire(
        self,
        key: str,
        ttl_seconds: int = 300,
        retry_delay: float = 0.25,
        max_attempts: int = 20,
    ) -> str:
        redis = await self._ensure_redis()
        token = uuid.uuid4().hex
        attempt = 0
        while attempt < max_attempts:
            try:
                locked = await redis.set(key, token, nx=True, ex=ttl_seconds)
                if locked:
                    return token
            except Exception as exc:  # pragma: no cover
                logger.exception("Redis lock acquisition failed on attempt %s: %s", attempt + 1, exc)
                raise RedisLockError("Failed to acquire Redis lock") from exc

            attempt += 1
            await asyncio.sleep(retry_delay)

        raise RedisLockError(
            f"Unable to acquire Redis lock for key '{key}' after {max_attempts} attempts"
        )

    async def release(self, key: str, token: str) -> bool:
        redis = await self._ensure_redis()
        try:
            released = await redis.eval(UNLOCK_SCRIPT, 1, key, token)
            return bool(released)
        except Exception as exc:  # pragma: no cover
            logger.exception("Redis lock release failed for key %s: %s", key, exc)
            raise RedisLockError("Failed to release Redis lock") from exc

    @asynccontextmanager
    async def lock(
        self,
        key: str,
        ttl_seconds: int = 300,
        retry_delay: float = 0.25,
        max_attempts: int = 20,
    ) -> AsyncIterator[str]:
        token = await self.acquire(key, ttl_seconds=ttl_seconds, retry_delay=retry_delay, max_attempts=max_attempts)
        try:
            yield token
        finally:
            try:
                await self.release(key, token)
            except RedisLockError:
                logger.warning("Failed to release Redis lock for key %s", key)


redis_lock = RedisLock()
