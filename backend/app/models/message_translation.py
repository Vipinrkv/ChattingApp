"""Message translation cache model"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Index, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class MessageTranslation(Base):
    __tablename__ = "message_translations"
    __table_args__ = (
        Index("ix_message_translations_message_id", "message_id"),
        UniqueConstraint("message_id", "target_language", name="uq_translation_message_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_content: Mapped[str] = mapped_column(String(4096), nullable=False)
    is_auto_translated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
