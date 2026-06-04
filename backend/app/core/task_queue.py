import asyncio
import inspect
import json
import logging
from typing import Any, Awaitable, Callable

from app.core.config import settings

try:
    from redis.asyncio import Redis, from_url
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    from_url = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

try:
    from celery import Celery  # type: ignore[import]
    _CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover
    Celery = None  # type: ignore[assignment]
    _CELERY_AVAILABLE = False

try:
    from rq import Queue  # type: ignore[import]
    _RQ_AVAILABLE = True
except ImportError:  # pragma: no cover
    Queue = None  # type: ignore[assignment]
    _RQ_AVAILABLE = False

logger = logging.getLogger(__name__)

TaskCallable = Callable[..., Awaitable[Any]]


class BackgroundTaskQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[TaskCallable, tuple[Any, ...], dict[str, Any]]] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None
        self.enabled = False
        self.redis: Redis | None = None
        self.distributed_task_registry: dict[str, TaskCallable] = {}
        self.celery_app = None
        self.rq_queue = None

    async def initialize(self) -> None:
        if self.enabled:
            return

        if settings.TASK_QUEUE_BACKEND == "redis" and _REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis = from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                    socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                )
                await self.redis.ping()
                self.worker_task = asyncio.create_task(self._redis_worker_loop())
                self.enabled = True
                return
            except Exception as exc:
                logger.warning("Redis distributed task queue unavailable: %s", exc)
                self.redis = None

        if settings.TASK_QUEUE_BACKEND == "celery" and _CELERY_AVAILABLE and settings.REDIS_URL:
            try:
                self.celery_app = Celery("chattingapp", broker=settings.REDIS_URL)
                self.enabled = True
                return
            except Exception as exc:
                logger.warning("Celery task queue initialization failed: %s", exc)
                self.celery_app = None

        if settings.TASK_QUEUE_BACKEND == "rq" and _RQ_AVAILABLE and _REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis = from_url(
                    settings.REDIS_URL,
                    decode_responses=False,
                    socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                    socket_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                )
                await self.redis.ping()
                self.rq_queue = Queue(settings.RQ_QUEUE_NAME, connection=self.redis)
                self.enabled = True
                return
            except Exception as exc:
                logger.warning("RQ task queue initialization failed: %s", exc)
                self.redis = None
                self.rq_queue = None

        self.worker_task = asyncio.create_task(self._worker_loop())
        self.enabled = True

    async def shutdown(self) -> None:
        if not self.enabled:
            return
        try:
            await self.queue.join()
        except Exception:
            pass
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass
            self.redis = None
        self.enabled = False

    async def register_distributed_task(self, name: str, task: TaskCallable) -> None:
        self.distributed_task_registry[name] = task

    async def schedule_distributed(self, task_name: str, *args: Any, **kwargs: Any) -> None:
        if settings.TASK_QUEUE_BACKEND == "redis" and self.redis:
            payload = {"task_name": task_name, "args": args, "kwargs": kwargs}
            await self.redis.rpush(settings.TASK_QUEUE_REDIS_KEY, json.dumps(payload, default=str))
            return

        if settings.TASK_QUEUE_BACKEND == "celery" and _CELERY_AVAILABLE and self.celery_app:
            self.celery_app.send_task(task_name, args=args, kwargs=kwargs)
            return

        if settings.TASK_QUEUE_BACKEND == "rq" and _RQ_AVAILABLE and self.rq_queue:
            self.rq_queue.enqueue_call(
                func="app.workers.tasks.run_distributed_task",
                args=(task_name, *args),
                kwargs=kwargs,
            )
            return

        raise RuntimeError("Distributed task queue is not configured or supported in this environment")

    async def schedule(self, task: TaskCallable, *args: Any, **kwargs: Any) -> None:
        if not self.enabled:
            raise RuntimeError("Background task queue is not initialized")
        await self.queue.put((task, args, kwargs))

    async def _worker_loop(self) -> None:
        while True:
            task_fn, args, kwargs = await self.queue.get()
            try:
                result = task_fn(*args, **kwargs)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.exception("Background task failed: %s", exc)
            finally:
                self.queue.task_done()

    async def _redis_worker_loop(self) -> None:
        if not self.redis:
            return
        while True:
            try:
                payload = await self.redis.blpop(settings.TASK_QUEUE_REDIS_KEY, timeout=5)
                if not payload:
                    continue
                _, raw = payload
                task_payload = json.loads(raw)
                task_name = task_payload.get("task_name")
                args = task_payload.get("args", [])
                kwargs = task_payload.get("kwargs", {})
                task = self.distributed_task_registry.get(task_name)
                if task:
                    result = task(*args, **kwargs)
                    if inspect.isawaitable(result):
                        await result
                else:
                    logger.warning("Distributed task %s is not registered", task_name)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Redis distributed task worker failed: %s", exc)


task_queue = BackgroundTaskQueue()
