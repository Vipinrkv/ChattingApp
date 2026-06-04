from datetime import datetime
from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    event_name: str = Field(min_length=1, max_length=80)
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, object] = Field(default_factory=dict)


class AnalyticsSummary(BaseModel):
    active_users: int
    total_events: int
    engagement_events: int
    creator_events: int
    revenue_events: int
    moderation_events: int
    retained_users: int
    heatmap: list[dict[str, object]]
    top_events: list[dict[str, object]]
    generated_at: datetime


class ScalingStatus(BaseModel):
    task_queue_backend: str
    event_bus_backend: str
    redis_enabled: bool
    kafka_configured: bool
    read_replica_configured: bool
    failover_configured: bool
    api_replica_strategy: str
    worker_strategy: str


class LocalSyncMetricsExport(BaseModel):
    queue_depth: int = Field(ge=0)
    failed_sync_count: int = Field(ge=0)
    restore_count: int = Field(ge=0)
    cache_size_bytes: int = Field(ge=0)
    generated_at: datetime
