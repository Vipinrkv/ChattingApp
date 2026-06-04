from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise_feature import (
    AuditReview,
    EnterpriseRole,
    ReportingSnapshot,
    RevenueLedgerEntry,
    SupportTicket,
)
from app.models.report import Report


class EnterpriseFeatureService:
    @staticmethod
    async def summary(session: AsyncSession) -> dict[str, object]:
        async def count(model, *criteria) -> int:
            stmt = select(func.count(model.id))
            if criteria:
                stmt = stmt.where(*criteria)
            return int(await session.scalar(stmt) or 0)

        revenue = await session.scalar(
            select(func.coalesce(func.sum(RevenueLedgerEntry.amount), 0)).where(RevenueLedgerEntry.status == "booked")
        )
        return {
            "roles": await count(EnterpriseRole),
            "open_audit_reviews": await count(AuditReview, AuditReview.status == "open"),
            "open_support_tickets": await count(SupportTicket, SupportTicket.status == "open"),
            "booked_revenue": float(revenue or 0),
            "reporting_snapshots": await count(ReportingSnapshot),
            "moderation_queue": await count(Report, Report.status.in_(["pending", "open"])),
            "generated_at": datetime.utcnow(),
        }

    @staticmethod
    async def assign_role(session: AsyncSession, **payload) -> EnterpriseRole:
        role = EnterpriseRole(**payload)
        session.add(role)
        await session.commit()
        await session.refresh(role)
        return role

    @staticmethod
    async def create_audit_review(session: AsyncSession, actor_id: uuid.UUID | None, **payload) -> AuditReview:
        metadata = payload.pop("metadata", {})
        review = AuditReview(actor_id=actor_id, metadata_json=metadata, **payload)
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review

    @staticmethod
    async def resolve_audit_review(session: AsyncSession, review_id: uuid.UUID) -> AuditReview:
        review = await session.scalar(select(AuditReview).where(AuditReview.id == review_id))
        if not review:
            raise ValueError("Audit review not found")
        review.status = "reviewed"
        review.reviewed_at = datetime.utcnow()
        await session.commit()
        await session.refresh(review)
        return review

    @staticmethod
    async def create_support_ticket(session: AsyncSession, requester_id: uuid.UUID | None, **payload) -> SupportTicket:
        ticket = SupportTicket(requester_id=requester_id, **payload)
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket

    @staticmethod
    async def add_revenue_entry(session: AsyncSession, **payload) -> RevenueLedgerEntry:
        metadata = payload.pop("metadata", {})
        entry = RevenueLedgerEntry(metadata_json=metadata, **payload)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry

    @staticmethod
    async def create_reporting_snapshot(
        session: AsyncSession,
        report_key: str,
        filters: dict[str, object],
        payload: dict[str, object],
        generated_by: uuid.UUID | None,
    ) -> ReportingSnapshot:
        snapshot = ReportingSnapshot(
            report_key=report_key,
            filters=filters,
            payload=payload,
            generated_by=generated_by,
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return snapshot
