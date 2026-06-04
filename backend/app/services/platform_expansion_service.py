from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_expansion import (
    CallSession,
    CommunityChannel,
    CreatorMonetizationProfile,
    LiveStream,
    MarketplaceListing,
    PlatformEvent,
    ScreenShareSession,
    SubscriptionPlan,
    UserSubscription,
)


class PlatformExpansionService:
    @staticmethod
    async def summary(session: AsyncSession) -> dict[str, object]:
        async def count(model, *criteria) -> int:
            stmt = select(func.count(model.id))
            if criteria:
                stmt = stmt.where(*criteria)
            return int(await session.scalar(stmt) or 0)

        return {
            "live_streams": await count(LiveStream),
            "active_calls": await count(CallSession, CallSession.status.in_(["waiting", "active"])),
            "screen_shares": await count(ScreenShareSession, ScreenShareSession.status == "active"),
            "monetized_creators": await count(CreatorMonetizationProfile),
            "marketplace_listings": await count(MarketplaceListing, MarketplaceListing.status == "active"),
            "subscription_plans": await count(SubscriptionPlan, SubscriptionPlan.is_active.is_(True)),
            "platform_events": await count(PlatformEvent),
            "community_channels": await count(CommunityChannel, CommunityChannel.is_active.is_(True)),
            "generated_at": datetime.utcnow(),
        }

    @staticmethod
    async def create_live_stream(session: AsyncSession, host_id: uuid.UUID, **payload) -> LiveStream:
        stream = LiveStream(host_id=host_id, stream_key=f"ls_{uuid.uuid4().hex}", **payload)
        session.add(stream)
        await session.commit()
        await session.refresh(stream)
        return stream

    @staticmethod
    async def set_live_stream_status(session: AsyncSession, stream_id: uuid.UUID, status: str) -> LiveStream:
        stream = await session.scalar(select(LiveStream).where(LiveStream.id == stream_id))
        if not stream:
            raise ValueError("Live stream not found")
        stream.status = status
        if status == "live":
            stream.started_at = stream.started_at or datetime.utcnow()
            stream.playback_url = stream.playback_url or f"/streams/{stream.id}/playback.m3u8"
        if status == "ended":
            stream.ended_at = datetime.utcnow()
        await session.commit()
        await session.refresh(stream)
        return stream

    @staticmethod
    async def create_call_session(session: AsyncSession, creator_id: uuid.UUID, **payload) -> CallSession:
        call = CallSession(creator_id=creator_id, status="active", started_at=datetime.utcnow(), **payload)
        session.add(call)
        await session.commit()
        await session.refresh(call)
        return call

    @staticmethod
    async def end_call_session(session: AsyncSession, call_id: uuid.UUID, quality_score: int | None = None) -> CallSession:
        call = await session.scalar(select(CallSession).where(CallSession.id == call_id))
        if not call:
            raise ValueError("Call session not found")
        call.status = "ended"
        call.ended_at = datetime.utcnow()
        call.quality_score = quality_score
        await session.commit()
        await session.refresh(call)
        return call

    @staticmethod
    async def start_screen_share(session: AsyncSession, call_session_id: uuid.UUID, presenter_id: uuid.UUID) -> ScreenShareSession:
        share = ScreenShareSession(call_session_id=call_session_id, presenter_id=presenter_id)
        session.add(share)
        await session.commit()
        await session.refresh(share)
        return share

    @staticmethod
    async def upsert_monetization_profile(
        session: AsyncSession,
        user_id: uuid.UUID,
        payout_provider: str | None = None,
        revenue_share_bps: int = 7000,
    ) -> CreatorMonetizationProfile:
        profile = await session.scalar(select(CreatorMonetizationProfile).where(CreatorMonetizationProfile.user_id == user_id))
        if profile:
            profile.payout_provider = payout_provider
            profile.revenue_share_bps = revenue_share_bps
        else:
            profile = CreatorMonetizationProfile(
                user_id=user_id,
                payout_provider=payout_provider,
                revenue_share_bps=revenue_share_bps,
            )
            session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    @staticmethod
    async def create_marketplace_listing(session: AsyncSession, seller_id: uuid.UUID, **payload) -> MarketplaceListing:
        metadata = payload.pop("metadata", {})
        listing = MarketplaceListing(seller_id=seller_id, metadata_json=metadata, **payload)
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
        return listing

    @staticmethod
    async def create_subscription_plan(session: AsyncSession, **payload) -> SubscriptionPlan:
        plan = SubscriptionPlan(**payload)
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan

    @staticmethod
    async def subscribe_user(session: AsyncSession, user_id: uuid.UUID, plan_id: uuid.UUID) -> UserSubscription:
        subscription = UserSubscription(user_id=user_id, plan_id=plan_id)
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription

    @staticmethod
    async def create_event(session: AsyncSession, host_id: uuid.UUID, **payload) -> PlatformEvent:
        event = PlatformEvent(host_id=host_id, **payload)
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    @staticmethod
    async def create_channel(session: AsyncSession, owner_id: uuid.UUID, **payload) -> CommunityChannel:
        channel = CommunityChannel(owner_id=owner_id, **payload)
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel
