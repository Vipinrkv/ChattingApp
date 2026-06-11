"""Chat backup model for backup/export functionality"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Enum as SQLEnum, BigInteger, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class BackupStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatBackup(Base):
    __tablename__ = "chat_backups"
    __table_args__ = (
        Index("ix_chat_backups_user_id", "user_id"),
        Index("ix_chat_backups_backup_status", "backup_status"),
        Index("ix_chat_backups_created_at", "created_at"),
        Index("ix_chat_backups_user_status", "user_id", "backup_status"),
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
    )
    backup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    backup_status: Mapped[BackupStatus] = mapped_column(
        SQLEnum(BackupStatus, name="backupstatus", values_callable=lambda enum: [item.value for item in enum]),
        default=BackupStatus.PENDING,
        nullable=False,
    )
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="json", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
