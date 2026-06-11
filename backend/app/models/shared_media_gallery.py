"""Shared media gallery models"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Index, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class SharedMediaGallery(Base):
    __tablename__ = "shared_media_galleries"
    __table_args__ = (
        Index("ix_shared_media_galleries_conversation_id", "conversation_id"),
        Index("ix_shared_media_galleries_creator_id", "creator_id"),
        Index("ix_shared_media_galleries_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    media_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GalleryMediaItem(Base):
    __tablename__ = "gallery_media_items"
    __table_args__ = (
        Index("ix_gallery_media_items_gallery_id", "gallery_id"),
        Index("ix_gallery_media_items_message_id", "message_id"),
        Index("ix_gallery_media_items_added_at", "added_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    gallery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared_media_galleries.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    media_type: Mapped[str] = mapped_column(String(80), nullable=False)
    media_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
