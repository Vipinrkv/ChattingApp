# backend/app/models/follower.py
from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


class Follower(Base):
    __tablename__ = "followers"
    __table_args__ = (
        Index("ix_followers_follower_following", "follower_id", "following_id"),
        Index("ix_followers_following_follower", "following_id", "follower_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    following_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    follower = relationship(
        "User",
        foreign_keys=[follower_id],
        back_populates="following",
    )
    following = relationship(
        "User",
        foreign_keys=[following_id],
        back_populates="followers",
    )
