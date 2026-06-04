from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep, require_role
from app.core.errors import BadRequestError, NotFoundError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.moderation_schema import (
    ReportResponse,
    ReportResolutionRequest,
)
from app.services.moderation_service import ModerationError, ModerationService

require_moderator = require_role("admin", "moderator")

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_moderator)],
)


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    status: Optional[str] = Query(default=None),
    target_type: Optional[str] = Query(default=None),
    reporter_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportResponse]:
    return await ModerationService.list_reports(
        session,
        status=status,
        target_type=target_type,
        reporter_id=reporter_id,
        limit=limit,
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    report = await ModerationService.get_report(session, report_id)
    if not report:
        raise NotFoundError("Report not found", code="moderation_report_not_found")
    return report


@router.post("/reports/{report_id}/resolve", response_model=ReportResponse)
async def resolve_report(
    report_id: str,
    payload: ReportResolutionRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    try:
        if payload.action_type:
            await ModerationService.apply_action(
                session,
                str(current_user.id),
                report_id,
                payload.action_type.value,
                payload.reason,
                payload.duration_minutes,
                payload.metadata,
            )
            report = await ModerationService.get_report(session, report_id)
        else:
            report = await ModerationService.resolve_report(
                session,
                report_id,
                str(current_user.id),
                reason=payload.comment or payload.reason,
            )
        if not report:
            raise ModerationError("Report not found")
        return report
    except ModerationError as exc:
        if "not found" in str(exc).lower():
            raise NotFoundError(str(exc), code="moderation_report_not_found") from exc
        raise BadRequestError(str(exc), code="moderation_resolution_invalid") from exc
