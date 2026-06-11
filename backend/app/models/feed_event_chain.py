import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base


class FeedEventChain(Base):
    __tablename__ = "feed_event_chain"
    __table_args__ = (
        Index("ix_feed_event_chain_timestamp", "timestamp"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    previous_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=False, index=True)
