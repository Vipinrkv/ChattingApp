from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.globalization_feature import (
    InternationalModerationQueue,
    LocalizationString,
    RegionalContentPolicy,
    RegionRecommendation,
    TimezoneScheduledItem,
    UserLocalePreference,
)


class GlobalizationFeatureService:
    @staticmethod
    async def summary(session: AsyncSession) -> dict[str, object]:
        async def count(model, *criteria) -> int:
            stmt = select(func.count(model.id))
            if criteria:
                stmt = stmt.where(*criteria)
            return int(await session.scalar(stmt) or 0)

        locales = await session.scalar(select(func.count(distinct(LocalizationString.locale))))
        return {
            "locales": int(locales or 0),
            "localized_strings": await count(LocalizationString),
            "regional_policies": await count(RegionalContentPolicy, RegionalContentPolicy.is_active.is_(True)),
            "international_moderation_items": await count(InternationalModerationQueue, InternationalModerationQueue.status == "open"),
            "scheduled_items": await count(TimezoneScheduledItem, TimezoneScheduledItem.status == "scheduled"),
            "regional_recommendations": await count(RegionRecommendation),
            "generated_at": datetime.utcnow(),
        }

    @staticmethod
    async def upsert_locale_preference(session: AsyncSession, user_id: uuid.UUID, **payload) -> UserLocalePreference:
        preference = await session.scalar(select(UserLocalePreference).where(UserLocalePreference.user_id == user_id))
        if preference:
            for key, value in payload.items():
                setattr(preference, key, value)
            preference.updated_at = datetime.utcnow()
        else:
            preference = UserLocalePreference(user_id=user_id, **payload)
            session.add(preference)
        await session.commit()
        await session.refresh(preference)
        return preference

    @staticmethod
    async def upsert_localization_string(session: AsyncSession, **payload) -> LocalizationString:
        row = await session.scalar(
            select(LocalizationString).where(
                LocalizationString.locale == payload["locale"],
                LocalizationString.message_key == payload["message_key"],
            )
        )
        if row:
            row.message_value = payload["message_value"]
            row.namespace = payload.get("namespace", row.namespace)
            row.updated_at = datetime.utcnow()
        else:
            row = LocalizationString(**payload)
            session.add(row)
        await session.commit()
        await session.refresh(row)
        return row

    @staticmethod
    async def create_policy(session: AsyncSession, **payload) -> RegionalContentPolicy:
        policy = RegionalContentPolicy(**payload)
        session.add(policy)
        await session.commit()
        await session.refresh(policy)
        return policy

    @staticmethod
    async def enqueue_moderation(
        session: AsyncSession,
        target_type: str,
        target_id: str,
        region_code: str,
        reason: str,
        locale: str | None = None,
    ) -> InternationalModerationQueue:
        item = InternationalModerationQueue(
            target_type=target_type,
            target_id=target_id,
            region_code=region_code,
            locale=locale,
            reason=reason,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def schedule_item(session: AsyncSession, owner_id: uuid.UUID, **payload) -> TimezoneScheduledItem:
        item = TimezoneScheduledItem(owner_id=owner_id, **payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def create_recommendation(session: AsyncSession, **payload) -> RegionRecommendation:
        metadata = payload.pop("metadata", {})
        recommendation = RegionRecommendation(metadata_json=metadata, **payload)
        session.add(recommendation)
        await session.commit()
        await session.refresh(recommendation)
        return recommendation
