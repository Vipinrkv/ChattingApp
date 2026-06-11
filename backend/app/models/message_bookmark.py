"""Message bookmark model"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class MessageBookmark(Base):
    __tablename__ = "message_bookmarks"
    __table_args__ = (
        Index("ix_message_bookmarks_user_id", "user_id"),
        Index("ix_message_bookmarks_message_id", "message_id"),
        Index("ix_message_bookmarks_created_at", "created_at"),
        UniqueConstraint("user_id", "message_id", name="uq_bookmark_user_message"),
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
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    bookmark_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
