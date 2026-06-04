from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LocalePreferenceUpdate(BaseModel):
    locale: str = Field(default="en-US", max_length=16)
    timezone: str = Field(default="UTC", max_length=80)
    region_code: str | None = Field(default=None, max_length=16)


class LocalizationStringUpsert(BaseModel):
    locale: str = Field(max_length=16)
    message_key: str = Field(min_length=1, max_length=180)
    message_value: str = Field(min_length=1)
    namespace: str = Field(default="app", max_length=80)


class RegionalPolicyCreate(BaseModel):
    region_code: str = Field(max_length=16)
    policy_key: str = Field(min_length=1, max_length=120)
    policy_value: dict[str, object] = Field(default_factory=dict)


class TimezoneScheduleCreate(BaseModel):
    item_type: str = Field(min_length=1, max_length=80)
    payload: dict[str, object] = Field(default_factory=dict)
    timezone: str = Field(default="UTC", max_length=80)
    scheduled_for_utc: datetime


class RegionRecommendationCreate(BaseModel):
    region_code: str = Field(max_length=16)
    target_type: str = Field(max_length=80)
    target_id: str = Field(max_length=120)
    score: float = Field(ge=0)
    reason: str | None = Field(default=None, max_length=180)
    metadata: dict[str, object] = Field(default_factory=dict)


class GlobalizationSummary(BaseModel):
    locales: int
    localized_strings: int
    regional_policies: int
    international_moderation_items: int
    scheduled_items: int
    regional_recommendations: int
    generated_at: datetime
