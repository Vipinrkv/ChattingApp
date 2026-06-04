import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class LiveStream(Base):
    __tablename__ = "live_streams"
    __table_args__ = (Index("ix_live_streams_host_status", "host_id", "status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="scheduled", nullable=False, index=True)
    stream_key = Column(String(120), nullable=True)
    playback_url = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    viewer_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CallSession(Base):
    __tablename__ = "call_sessions"
    __table_args__ = (Index("ix_call_sessions_creator_status", "creator_id", "status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(String(120), nullable=False, index=True)
    call_type = Column(String(20), default="video", nullable=False)
    status = Column(String(30), default="waiting", nullable=False, index=True)
    participant_ids = Column(JSON, default=list, nullable=False)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    quality_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ScreenShareSession(Base):
    __tablename__ = "screen_share_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_session_id = Column(UUID(as_uuid=True), ForeignKey("call_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    presenter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="active", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)


class CreatorMonetizationProfile(Base):
    __tablename__ = "creator_monetization_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    payout_status = Column(String(30), default="pending", nullable=False)
    payout_provider = Column(String(50), nullable=True)
    revenue_share_bps = Column(Integer, default=7000, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (Index("ix_marketplace_listings_status_category", "status", "category"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(80), nullable=True)
    price_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(30), default="active", nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    plan_type = Column(String(40), default="creator", nullable=False, index=True)
    price_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    interval = Column(String(20), default="monthly", nullable=False)
    features = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (Index("ix_user_subscriptions_user_status", "user_id", "status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="active", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    renews_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)


class PlatformEvent(Base):
    __tablename__ = "platform_events"
    __table_args__ = (Index("ix_platform_events_host_start", "host_id", "starts_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime, nullable=True)
    event_type = Column(String(50), default="community", nullable=False)
    access_level = Column(String(40), default="public", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityChannel(Base):
    __tablename__ = "community_channels"
    __table_args__ = (Index("ix_community_channels_visibility", "visibility", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(String(30), default="public", nullable=False)
    channel_type = Column(String(40), default="discussion", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
