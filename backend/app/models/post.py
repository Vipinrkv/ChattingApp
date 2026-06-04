from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class PostVisibility(str, enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    FOLLOWERS = "followers"
    CUSTOM = "custom"


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_user_created_at", "user_id", "created_at"),
        Index("ix_posts_visibility_created_at", "visibility", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    visibility = Column(SQLEnum(PostVisibility), default=PostVisibility.PUBLIC)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    user = relationship("User", back_populates="posts")
