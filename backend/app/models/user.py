# backend/app/models/user.py
from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_shadow_banned", "is_shadow_banned"),
        Index("ix_users_is_muted", "is_muted"),
        Index("ix_users_is_suspended", "is_suspended"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, unique=True, nullable=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    bio = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_badge = Column(String, nullable=True)
    is_shadow_banned = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    muted_until = Column(DateTime, nullable=True)
    is_suspended = Column(Boolean, default=False)
    suspended_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    sent_requests = relationship(
        "FriendRequest",
        foreign_keys="FriendRequest.requester_id",
        back_populates="requester",
        cascade="all, delete-orphan",
    )
    received_requests = relationship(
        "FriendRequest",
        foreign_keys="FriendRequest.addressee_id",
        back_populates="addressee",
        cascade="all, delete-orphan",
    )
    followers = relationship(
        "Follower",
        foreign_keys="Follower.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
    )
    following = relationship(
        "Follower",
        foreign_keys="Follower.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_messages = relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan",
    )
    blocks = relationship(
        "Block",
        foreign_keys="Block.blocker_id",
        back_populates="blocker",
        cascade="all, delete-orphan",
    )
    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    groups_created = relationship(
        "Group",
        foreign_keys="Group.created_by",
        back_populates="creator",
        cascade="all, delete-orphan",
    )
    group_memberships = relationship(
        "GroupMember",
        foreign_keys="GroupMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
