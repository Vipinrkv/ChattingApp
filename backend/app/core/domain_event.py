from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, List
import uuid


DomainEventHandler = Callable[["DomainEvent"], Coroutine[Any, Any, None]]

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    name: str
    aggregate_id: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NotificationCreatedEvent(DomainEvent):
    pass


class DomainEventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, List[DomainEventHandler]] = {}

    def register(self, event_name: str, handler: DomainEventHandler) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    async def dispatch(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.name, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.exception("Domain event handler failed: %s", exc)

        # Event bus publish (at-least-once semantics; consumers should be idempotent)
        try:
            from app.core.event_bus import event_bus

            await event_bus.publish(event.name, event.to_dict())
        except Exception as exc:
            logger.warning("Event bus publish failed for %s: %s", event.name, exc)



domain_event_dispatcher = DomainEventDispatcher()
