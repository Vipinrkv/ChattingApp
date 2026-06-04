import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep, require_role
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.enterprise_feature_schema import (
    AuditReviewCreate,
    EnterpriseRoleCreate,
    EnterpriseSummary,
    RevenueLedgerEntryCreate,
    SupportTicketCreate,
)
from app.services.enterprise_feature_service import EnterpriseFeatureService

router = APIRouter(tags=["enterprise"])
require_enterprise_admin = require_role("admin", "moderator")


class ReportingSnapshotCreate(BaseModel):
    report_key: str = Field(min_length=1, max_length=120)
    filters: dict[str, object] = Field(default_factory=dict)
    payload: dict[str, object] = Field(default_factory=dict)


@router.get("/summary", response_model=EnterpriseSummary, dependencies=[Depends(require_enterprise_admin)])
async def enterprise_summary(session: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    return await EnterpriseFeatureService.summary(session)


@router.post("/roles", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_enterprise_admin)])
async def assign_enterprise_role(
    payload: EnterpriseRoleCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    role = await EnterpriseFeatureService.assign_role(session, **payload.model_dump())
    return {"id": str(role.id), "role": role.role_name}


@router.post("/audit-reviews", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_enterprise_admin)])
async def create_audit_review(
    payload: AuditReviewCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    review = await EnterpriseFeatureService.create_audit_review(session, current_user.id, **payload.model_dump())
    return {"id": str(review.id), "status": review.status}


@router.post("/audit-reviews/{review_id}/resolve", dependencies=[Depends(require_enterprise_admin)])
async def resolve_audit_review(
    review_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    try:
        review = await EnterpriseFeatureService.resolve_audit_review(session, review_id)
        return {"id": str(review.id), "status": review.status}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/support-tickets", status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    ticket = await EnterpriseFeatureService.create_support_ticket(session, current_user.id, **payload.model_dump())
    return {"id": str(ticket.id), "status": ticket.status}


@router.post("/revenue", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_enterprise_admin)])
async def add_revenue_entry(
    payload: RevenueLedgerEntryCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    entry = await EnterpriseFeatureService.add_revenue_entry(session, **payload.model_dump())
    return {"id": str(entry.id), "status": entry.status}


@router.post("/reporting-snapshots", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_enterprise_admin)])
async def create_reporting_snapshot(
    payload: ReportingSnapshotCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    snapshot = await EnterpriseFeatureService.create_reporting_snapshot(
        session,
        report_key=payload.report_key,
        filters=payload.filters,
        payload=payload.payload,
        generated_by=current_user.id,
    )
    return {"id": str(snapshot.id), "report_key": snapshot.report_key}
