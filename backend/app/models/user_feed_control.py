import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base


class UserFeedControl(Base):
    __tablename__ = "user_feed_controls"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    muted_words = Column(JSON, default=list, nullable=False)
    ranking_mode = Column(String(30), default="engagement", nullable=False)
    sensitive_content_hidden = Column(Boolean, default=True, nullable=False)
    data_saver_enabled = Column(Boolean, default=False, nullable=False)
