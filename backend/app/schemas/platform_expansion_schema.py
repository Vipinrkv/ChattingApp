from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LiveStreamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    scheduled_at: datetime | None = None


class LiveStreamResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: str | None
    status: str
    playback_url: str | None
    scheduled_at: datetime | None
    viewer_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CallSessionCreate(BaseModel):
    room_id: str = Field(min_length=1, max_length=120)
    call_type: str = "video"
    participant_ids: list[str] = Field(default_factory=list)


class MarketplaceListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    category: str | None = None
    price_amount: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    metadata: dict[str, object] = Field(default_factory=dict)


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    plan_type: str = "creator"
    price_amount: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    interval: str = "monthly"
    features: list[str] = Field(default_factory=list)


class PlatformEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    event_type: str = "community"
    access_level: str = "public"


class CommunityChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    visibility: str = "public"
    channel_type: str = "discussion"


class PlatformExpansionSummary(BaseModel):
    live_streams: int
    active_calls: int
    screen_shares: int
    monetized_creators: int
    marketplace_listings: int
    subscription_plans: int
    platform_events: int
    community_channels: int
    generated_at: datetime
