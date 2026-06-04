"""AI smart replies model for suggested replies"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class AISmartReply(Base):
    __tablename__ = "ai_smart_replies"
    __table_args__ = (
        Index("ix_ai_smart_replies_message_id", "message_id"),
        Index("ix_ai_smart_replies_user_id", "user_id"),
        Index("ix_ai_smart_replies_created_at", "created_at"),
        Index("ix_ai_smart_replies_message_confidence", "message_id", "confidence_score"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reply_text: Mapped[str] = mapped_column(String(4096), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    was_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
