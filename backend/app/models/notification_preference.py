from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base
import uuid


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preferences = Column(JSON, nullable=False, default={})
