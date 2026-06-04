import logging
from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.cqrs import command_bus
from app.core.domain_event import NotificationCreatedEvent, domain_event_dispatcher

from app.core.repository import NotificationRepository

from app.core.service_response import ServiceResult, success_result, error_result

from app.core.transaction import run_transaction
from app.models.notification import Notification
import uuid

logger = logging.getLogger(__name__)


@dataclass
class CreateNotificationCommand:
    session: AsyncSession
    user_id: str
    type: str
    text: str | None = None
    actor_id: str | None = None
    data: dict | None = None


async def _handle_create_notification_command(command: CreateNotificationCommand) -> ServiceResult[Notification]:
    repository = NotificationRepository(command.session)
    notif = Notification(
        user_id=uuid.UUID(str(command.user_id)),
        actor_id=uuid.UUID(str(command.actor_id)) if command.actor_id else None,
        type=command.type,
        text=command.text,
        data=command.data or {},
    )

    async def persist() -> Notification:
        await repository.add(notif)
        return notif

    try:
        result = await run_transaction(command.session, persist)
    except Exception as exc:
        return error_result("Failed to create notification", details=str(exc))

    event = NotificationCreatedEvent(
        name="notification.created",
        aggregate_id=str(result.id),
        payload={
            "id": str(result.id),
            "user_id": str(result.user_id),
            "actor_id": str(result.actor_id) if result.actor_id else None,
            "type": result.type,
            "text": result.text,
            "data": result.data or {},
            "is_read": bool(result.is_read),
            "timestamp": result.timestamp.isoformat() if result.timestamp is not None else None,
        },
    )

    await domain_event_dispatcher.dispatch(event)
    return success_result(result)


command_bus.register(CreateNotificationCommand, _handle_create_notification_command)


class NotificationService:

    @staticmethod
    async def create_notification(
        session: AsyncSession,
        user_id: str,
        type: str,
        text: str | None = None,
        actor_id: str | None = None,
        data: dict | None = None,
    ) -> ServiceResult[Notification]:
        # CQRS + Domain Event entrypoint: persist via CreateNotificationCommand,
        # then let domain events and subscribers handle delivery.
        cmd = CreateNotificationCommand(
            session=session,
            user_id=user_id,
            type=type,
            text=text,
            actor_id=actor_id,
            data=data,
        )
        return await command_bus.execute(cmd)


    @staticmethod
    async def _deliver_notification(user_id: str, notif_dict: dict) -> None:
        try:
            from app.websocket.redis_broker import redis_broker

            if notif_dict and redis_broker.enabled:
                payload = {
                    "type": "notification",
                    "data": notif_dict,
                    "_source_instance_id": redis_broker.instance_id,
                }
                await redis_broker.publish(f"chat:user:{user_id}", payload)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Failed to publish notification to Redis broker")

        try:
            from app.websocket.chat_socket import manager as ws_manager

            if notif_dict:
                await ws_manager.send_to_user(user_id, {"type": "notification", "data": notif_dict})
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Failed to send notification via WebSocket manager")

    @staticmethod
    async def list_notifications(session: AsyncSession, user_id: str, limit: int = 50, offset: int = 0) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == uuid.UUID(str(user_id))).order_by(Notification.timestamp.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def unread_count(session: AsyncSession, user_id: str) -> int:
        stmt = select(Notification).where(Notification.user_id == uuid.UUID(str(user_id))).where(Notification.is_read == False)
        result = await session.execute(stmt)
        return len(result.scalars().all())

    @staticmethod
    async def mark_as_read(session: AsyncSession, notification_id: str) -> bool:
        stmt = update(Notification).where(Notification.id == uuid.UUID(str(notification_id))).values(is_read=True)
        try:
            await session.execute(stmt)
            return True
        except Exception:
            return False
