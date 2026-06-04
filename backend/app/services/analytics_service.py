from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.event_bus import event_bus
from app.core.task_queue import task_queue
from app.models.analytics_event import AnalyticsEvent
from app.models.moderation_action import ModerationAction
from app.models.post import Post
from app.models.report import Report
from app.models.user import User


class AnalyticsService:
    @staticmethod
    async def track_event(
        session: AsyncSession,
        *,
        user_id: UUID | None,
        event_name: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            user_id=user_id,
            event_name=event_name,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        await event_bus.publish(
            "analytics.event.created",
            {
                "event_id": str(event.id),
                "event_name": event.event_name,
                "user_id": str(event.user_id) if event.user_id else None,
            },
        )
        return event

    @staticmethod
    async def summary(session: AsyncSession, days: int = 30) -> dict[str, object]:
        since = datetime.utcnow() - timedelta(days=days)

        async def scalar(stmt, default=0):
            value = await session.scalar(stmt)
            return value if value is not None else default

        total_events = await scalar(select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.created_at >= since))
        active_users = await scalar(
            select(func.count(distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.user_id.is_not(None),
            )
        )
        retained_users = await scalar(
            select(func.count(distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.event_name.in_(["session.started", "message.sent", "post.created"]),
            )
        )
        engagement_events = await scalar(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.event_name.in_(["message.sent", "post.created", "post.liked", "poll.voted", "story.viewed"]),
            )
        )
        creator_events = await scalar(
            select(func.count(Post.id)).where(Post.created_at >= since)
        )
        revenue_events = await scalar(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.event_name.like("revenue.%"),
            )
        )
        moderation_events = await scalar(
            select(func.count(Report.id)).where(Report.created_at >= since)
        )
        moderation_actions = await scalar(
            select(func.count(ModerationAction.id)).where(ModerationAction.created_at >= since)
        )

        top_rows = await session.execute(
            select(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id).label("count"))
            .where(AnalyticsEvent.created_at >= since)
            .group_by(AnalyticsEvent.event_name)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(8)
        )
        heatmap_rows = await session.execute(
            select(func.extract("hour", AnalyticsEvent.created_at).label("hour"), func.count(AnalyticsEvent.id).label("count"))
            .where(AnalyticsEvent.created_at >= since)
            .group_by("hour")
            .order_by("hour")
        )
        return {
            "active_users": int(active_users),
            "total_events": int(total_events),
            "engagement_events": int(engagement_events),
            "creator_events": int(creator_events),
            "revenue_events": int(revenue_events),
            "moderation_events": int(moderation_events) + int(moderation_actions),
            "retained_users": int(retained_users),
            "heatmap": [{"hour": int(row.hour), "count": int(row.count)} for row in heatmap_rows],
            "top_events": [{"event_name": row.event_name, "count": int(row.count)} for row in top_rows],
            "generated_at": datetime.utcnow(),
        }

    @staticmethod
    async def scaling_status() -> dict[str, object]:
        return {
            "task_queue_backend": settings.TASK_QUEUE_BACKEND,
            "event_bus_backend": event_bus.backend_name,
            "redis_enabled": bool(getattr(task_queue, "redis", None)),
            "kafka_configured": bool(settings.KAFKA_BOOTSTRAP_SERVERS),
            "read_replica_configured": bool(settings.READ_REPLICA_DATABASE_URL),
            "failover_configured": bool(settings.DB_FAILOVER_URL),
            "api_replica_strategy": "stateless FastAPI replicas behind a load balancer with Redis-backed realtime fanout",
            "worker_strategy": "run dedicated queue workers for notifications, analytics, moderation, media, and event consumers",
        }
