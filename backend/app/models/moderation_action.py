from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    moderator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    action_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
