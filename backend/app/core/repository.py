from __future__ import annotations

import uuid
from typing import Any, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

T = TypeVar("T")


class Repository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self.session = session
        self.model = model

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: str | UUID) -> Optional[T]:
        raw_id = uuid.UUID(str(entity_id))
        statement = select(self.model).where(self.model.id == raw_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list(self, limit: int = 100, offset: int = 0, order_by: Any | None = None) -> List[T]:
        statement = select(self.model)
        if order_by is not None:
            statement = statement.order_by(order_by)
        statement = statement.limit(limit).offset(offset)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def update_by_id(self, entity_id: str | UUID, values: dict[str, Any]) -> int:
        raw_id = uuid.UUID(str(entity_id))
        statement = update(self.model).where(self.model.id == raw_id).values(**values)
        result = await self.session.execute(statement)
        return result.rowcount

    async def delete_by_id(self, entity_id: str | UUID) -> int:
        raw_id = uuid.UUID(str(entity_id))
        statement = delete(self.model).where(self.model.id == raw_id)
        result = await self.session.execute(statement)
        return result.rowcount


class NotificationRepository(Repository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def list_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == uuid.UUID(str(user_id)))
            .order_by(Notification.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def unread_count(self, user_id: str) -> int:
        statement = (
            select(Notification)
            .where(Notification.user_id == uuid.UUID(str(user_id)))
            .where(Notification.is_read == False)
        )
        result = await self.session.execute(statement)
        return len(result.scalars().all())
