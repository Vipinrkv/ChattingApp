from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep, require_role
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.analytics_schema import AnalyticsEventCreate, AnalyticsSummary, LocalSyncMetricsExport, ScalingStatus
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])
require_analytics_admin = require_role("admin", "moderator")


@router.post("/events", status_code=201)
async def track_event(
    payload: AnalyticsEventCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    event = await AnalyticsService.track_event(
        session,
        user_id=current_user.id,
        event_name=payload.event_name,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        metadata=payload.metadata,
    )
    return {"id": str(event.id), "status": "tracked"}


@router.post("/sync-metrics", status_code=201)
async def export_sync_metrics(
    payload: LocalSyncMetricsExport,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    event = await AnalyticsService.track_event(
        session,
        user_id=current_user.id,
        event_name="local_first.sync_metrics_exported",
        entity_type="local_first_metrics",
        entity_id=str(current_user.id),
        metadata={**payload.dict(exclude={"generated_at"}), "generated_at": payload.generated_at.isoformat()},
    )
    return {"id": str(event.id), "status": "tracked"}


@router.get("/admin/summary", response_model=AnalyticsSummary, dependencies=[Depends(require_analytics_admin)])
async def analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return await AnalyticsService.summary(session, days=days)


@router.get("/admin/scaling", response_model=ScalingStatus, dependencies=[Depends(require_analytics_admin)])
async def scaling_status() -> dict[str, object]:
    return await AnalyticsService.scaling_status()
