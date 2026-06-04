# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\models\friend.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class FriendRequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class FriendRequest(Base):
    __tablename__ = "friends"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    addressee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SQLEnum(FriendRequestStatus),
        default=FriendRequestStatus.PENDING,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    requester = relationship(
        "User",
        foreign_keys=[requester_id],
        back_populates="sent_requests",
    )
    addressee = relationship(
        "User",
        foreign_keys=[addressee_id],
        back_populates="received_requests",
    )
