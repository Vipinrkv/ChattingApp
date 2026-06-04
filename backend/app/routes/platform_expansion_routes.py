import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep, require_role
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.platform_expansion_schema import (
    CallSessionCreate,
    CommunityChannelCreate,
    LiveStreamCreate,
    LiveStreamResponse,
    MarketplaceListingCreate,
    PlatformEventCreate,
    PlatformExpansionSummary,
    SubscriptionPlanCreate,
)
from app.services.platform_expansion_service import PlatformExpansionService

router = APIRouter(tags=["platform-expansion"])
require_platform_admin = require_role("admin", "moderator")


class MonetizationProfileUpsert(BaseModel):
    payout_provider: str | None = Field(default=None, max_length=50)
    revenue_share_bps: int = Field(default=7000, ge=0, le=10000)


class CallQualityUpdate(BaseModel):
    quality_score: int | None = Field(default=None, ge=0, le=100)


class SubscribeRequest(BaseModel):
    plan_id: uuid.UUID


@router.get("/summary", response_model=PlatformExpansionSummary, dependencies=[Depends(require_platform_admin)])
async def platform_summary(session: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    return await PlatformExpansionService.summary(session)


@router.post("/live-streams", response_model=LiveStreamResponse, status_code=status.HTTP_201_CREATED)
async def create_live_stream(
    payload: LiveStreamCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await PlatformExpansionService.create_live_stream(session, current_user.id, **payload.model_dump())


@router.post("/live-streams/{stream_id}/start", response_model=LiveStreamResponse)
async def start_live_stream(
    stream_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await PlatformExpansionService.set_live_stream_status(session, stream_id, "live")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/live-streams/{stream_id}/end", response_model=LiveStreamResponse)
async def end_live_stream(
    stream_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await PlatformExpansionService.set_live_stream_status(session, stream_id, "ended")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/calls", status_code=status.HTTP_201_CREATED)
async def create_call_session(
    payload: CallSessionCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    call = await PlatformExpansionService.create_call_session(session, current_user.id, **payload.model_dump())
    return {"id": str(call.id), "status": call.status}


@router.post("/calls/{call_id}/end")
async def end_call_session(
    call_id: uuid.UUID,
    payload: CallQualityUpdate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    try:
        call = await PlatformExpansionService.end_call_session(session, call_id, payload.quality_score)
        return {"id": str(call.id), "status": call.status}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/calls/{call_id}/screen-share", status_code=status.HTTP_201_CREATED)
async def start_screen_share(
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    share = await PlatformExpansionService.start_screen_share(session, call_id, current_user.id)
    return {"id": str(share.id), "status": share.status}


@router.post("/monetization/profile", status_code=status.HTTP_201_CREATED)
async def upsert_monetization_profile(
    payload: MonetizationProfileUpsert,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    profile = await PlatformExpansionService.upsert_monetization_profile(session, current_user.id, **payload.model_dump())
    return {"id": str(profile.id), "status": profile.payout_status}


@router.post("/marketplace/listings", status_code=status.HTTP_201_CREATED)
async def create_marketplace_listing(
    payload: MarketplaceListingCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    listing = await PlatformExpansionService.create_marketplace_listing(session, current_user.id, **payload.model_dump())
    return {"id": str(listing.id), "status": listing.status}


@router.post("/subscriptions/plans", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_platform_admin)])
async def create_subscription_plan(
    payload: SubscriptionPlanCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    plan = await PlatformExpansionService.create_subscription_plan(session, **payload.model_dump())
    return {"id": str(plan.id), "status": "active" if plan.is_active else "inactive"}


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def subscribe_current_user(
    payload: SubscribeRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    subscription = await PlatformExpansionService.subscribe_user(session, current_user.id, payload.plan_id)
    return {"id": str(subscription.id), "status": subscription.status}


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_platform_event(
    payload: PlatformEventCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    event = await PlatformExpansionService.create_event(session, current_user.id, **payload.model_dump())
    return {"id": str(event.id), "status": "scheduled"}


@router.post("/channels", status_code=status.HTTP_201_CREATED)
async def create_community_channel(
    payload: CommunityChannelCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    channel = await PlatformExpansionService.create_channel(session, current_user.id, **payload.model_dump())
    return {"id": str(channel.id), "status": "active" if channel.is_active else "inactive"}
