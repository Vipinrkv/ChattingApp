import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_name_created_at", "event_name", "created_at"),
        Index("ix_analytics_events_user_created_at", "user_id", "created_at"),
        Index("ix_analytics_events_entity", "entity_type", "entity_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_name = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(String(120), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
