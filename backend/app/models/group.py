# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\models\group.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (
        Index("ix_groups_created_by_type", "created_by", "type"),
        Index("ix_groups_discovery", "is_discoverable", "category", "created_at"),
        Index("ix_groups_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(30), index=True)
    organization_name: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_discoverable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False, index=True)
    announcement_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    onboarding_steps: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    growth_goal: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="groups_created")
    posts = relationship("GroupPost", back_populates="group", cascade="all, delete-orphan")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
