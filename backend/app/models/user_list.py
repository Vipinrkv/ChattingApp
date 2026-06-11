import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.connection import Base


class UserList(Base):
    __tablename__ = "user_lists"
    __table_args__ = (
        Index("ix_user_lists_owner_id", "owner_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(250), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("UserListMember", back_populates="user_list", cascade="all, delete-orphan")


class UserListMember(Base):
    __tablename__ = "user_list_members"

    list_id = Column(UUID(as_uuid=True), ForeignKey("user_lists.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user_list = relationship("UserList", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
