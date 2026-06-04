from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification_preference import NotificationPreference
import uuid


class NotificationPrefService:
    @staticmethod
    async def get_preferences(session: AsyncSession, user_id: str) -> dict:
        pref = await session.get(NotificationPreference, uuid.UUID(str(user_id)))
        if not pref:
            return {}
        return pref.preferences or {}

    @staticmethod
    async def set_preferences(session: AsyncSession, user_id: str, prefs: dict) -> dict:
        uid = uuid.UUID(str(user_id))
        pref = await session.get(NotificationPreference, uid)
        if not pref:
            pref = NotificationPreference(user_id=uid, preferences=prefs)
            session.add(pref)
        else:
            pref.preferences = prefs
        await session.commit()
        await session.refresh(pref)
        return pref.preferences
