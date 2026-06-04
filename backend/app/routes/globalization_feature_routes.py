from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep, require_role
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.globalization_feature_schema import (
    GlobalizationSummary,
    LocalePreferenceUpdate,
    LocalizationStringUpsert,
    RegionalPolicyCreate,
    RegionRecommendationCreate,
    TimezoneScheduleCreate,
)
from app.services.globalization_feature_service import GlobalizationFeatureService

router = APIRouter(tags=["globalization"])
require_global_admin = require_role("admin", "moderator")


class InternationalModerationCreate(BaseModel):
    target_type: str = Field(min_length=1, max_length=80)
    target_id: str = Field(min_length=1, max_length=120)
    region_code: str = Field(min_length=1, max_length=16)
    locale: str | None = Field(default=None, max_length=16)
    reason: str = Field(min_length=1, max_length=180)


@router.get("/summary", response_model=GlobalizationSummary, dependencies=[Depends(require_global_admin)])
async def globalization_summary(session: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    return await GlobalizationFeatureService.summary(session)


@router.put("/me/locale")
async def update_my_locale(
    payload: LocalePreferenceUpdate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | None]:
    preference = await GlobalizationFeatureService.upsert_locale_preference(session, current_user.id, **payload.model_dump())
    return {"locale": preference.locale, "timezone": preference.timezone, "region_code": preference.region_code}


@router.post("/localization", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_global_admin)])
async def upsert_localization_string(
    payload: LocalizationStringUpsert,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    row = await GlobalizationFeatureService.upsert_localization_string(session, **payload.model_dump())
    return {"id": str(row.id), "locale": row.locale, "message_key": row.message_key}


@router.post("/regional-policies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_global_admin)])
async def create_regional_policy(
    payload: RegionalPolicyCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    policy = await GlobalizationFeatureService.create_policy(session, **payload.model_dump())
    return {"id": str(policy.id), "region_code": policy.region_code}


@router.post("/moderation-queue", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_global_admin)])
async def enqueue_international_moderation(
    payload: InternationalModerationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    item = await GlobalizationFeatureService.enqueue_moderation(session, **payload.model_dump())
    return {"id": str(item.id), "status": item.status}


@router.post("/schedules", status_code=status.HTTP_201_CREATED)
async def schedule_timezone_item(
    payload: TimezoneScheduleCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    item = await GlobalizationFeatureService.schedule_item(session, current_user.id, **payload.model_dump())
    return {"id": str(item.id), "status": item.status}


@router.post("/recommendations", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_global_admin)])
async def create_region_recommendation(
    payload: RegionRecommendationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    recommendation = await GlobalizationFeatureService.create_recommendation(session, **payload.model_dump())
    return {"id": str(recommendation.id), "region_code": recommendation.region_code}
