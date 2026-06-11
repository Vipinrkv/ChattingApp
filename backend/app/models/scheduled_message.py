"""Scheduled message model"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class ScheduledMessageStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"
    __table_args__ = (
        Index("ix_scheduled_messages_sender_id", "sender_id"),
        Index("ix_scheduled_messages_receiver_id", "receiver_id"),
        Index("ix_scheduled_messages_scheduled_for", "scheduled_for"),
        Index("ix_scheduled_messages_status", "status"),
        Index("ix_scheduled_messages_scheduled_for_status", "scheduled_for", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(4096), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[ScheduledMessageStatus] = mapped_column(
        SQLEnum(ScheduledMessageStatus, name="messagestatus", values_callable=lambda enum: [item.value for item in enum]),
        default=ScheduledMessageStatus.SCHEDULED,
        nullable=False,
    )
    media_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
