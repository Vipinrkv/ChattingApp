import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.moderation_schema import (
    ReportCreateRequest,
    ReportResponse,
)
from app.services.moderation_service import ModerationError, ModerationService

router = APIRouter(
    tags=["moderation"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    try:
        report = await ModerationService.create_report(
            session,
            str(current_user.id),
            payload.target_type.value,
            payload.target_id,
            payload.reason,
            payload.details,
            [e.dict() for e in payload.evidence],
        )
        return report
    except ModerationError as exc:
        raise BadRequestError(str(exc), code="moderation_report_invalid") from exc


@router.get("/reports", response_model=list[ReportResponse])
async def list_my_reports(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportResponse]:
    reports = await ModerationService.list_reports(session, reporter_id=str(current_user.id))
    return reports
