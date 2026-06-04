import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class LocalizationString(Base):
    __tablename__ = "localization_strings"
    __table_args__ = (Index("ix_localization_strings_locale_key", "locale", "message_key", unique=True),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locale = Column(String(16), nullable=False, index=True)
    message_key = Column(String(180), nullable=False)
    message_value = Column(Text, nullable=False)
    namespace = Column(String(80), default="app", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserLocalePreference(Base):
    __tablename__ = "user_locale_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    locale = Column(String(16), default="en-US", nullable=False)
    timezone = Column(String(80), default="UTC", nullable=False)
    region_code = Column(String(16), nullable=True, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RegionalContentPolicy(Base):
    __tablename__ = "regional_content_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String(16), nullable=False, index=True)
    policy_key = Column(String(120), nullable=False)
    policy_value = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class InternationalModerationQueue(Base):
    __tablename__ = "international_moderation_queue"
    __table_args__ = (Index("ix_international_moderation_region_status", "region_code", "status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(String(80), nullable=False)
    target_id = Column(String(120), nullable=False)
    region_code = Column(String(16), nullable=False)
    locale = Column(String(16), nullable=True)
    reason = Column(String(180), nullable=False)
    status = Column(String(30), default="open", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TimezoneScheduledItem(Base):
    __tablename__ = "timezone_scheduled_items"
    __table_args__ = (Index("ix_timezone_scheduled_items_due", "status", "scheduled_for_utc"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(80), nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    timezone = Column(String(80), default="UTC", nullable=False)
    scheduled_for_utc = Column(DateTime, nullable=False)
    status = Column(String(30), default="scheduled", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RegionRecommendation(Base):
    __tablename__ = "region_recommendations"
    __table_args__ = (Index("ix_region_recommendations_region_score", "region_code", "score"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String(16), nullable=False)
    target_type = Column(String(80), nullable=False)
    target_id = Column(String(120), nullable=False)
    score = Column(Numeric(8, 4), nullable=False)
    reason = Column(String(180), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
