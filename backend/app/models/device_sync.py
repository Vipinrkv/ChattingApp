"""Device sync model for cross-device synchronization"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"


class DeviceSync(Base):
    __tablename__ = "device_syncs"
    __table_args__ = (
        Index("ix_device_syncs_user_id", "user_id"),
        Index("ix_device_syncs_device_id", "device_id"),
        Index("ix_device_syncs_message_id", "message_id"),
        Index("ix_device_syncs_sync_status", "sync_status"),
        Index("ix_device_syncs_user_status", "user_id", "sync_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, name="syncstatus", values_callable=lambda enum: [item.value for item in enum]),
        default=SyncStatus.PENDING,
        nullable=False,
        index=True,
    )
    last_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
