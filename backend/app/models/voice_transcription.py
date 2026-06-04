"""Voice transcription model for voice message processing"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class VoiceTranscription(Base):
    __tablename__ = "voice_transcriptions"
    __table_args__ = (
        Index("ix_voice_transcriptions_message_id", "message_id"),
        Index("ix_voice_transcriptions_is_processed", "is_processed"),
        Index("ix_voice_transcriptions_created_at", "created_at"),
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
    audio_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    transcribed_text: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    source_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    processing_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
