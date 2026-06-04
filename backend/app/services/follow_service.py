# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\follow_service.py
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follower import Follower
from app.models.user import User
from app.services.block_service import are_blocked, user_exists
from app.services.notification_service import NotificationService
from app.core.redis_cache import redis_cache


async def _invalidate_user_relations(user_id: uuid.UUID) -> None:
    if redis_cache.enabled:
        await redis_cache.delete(f"user:relations:{user_id}")


class FollowError(Exception):
    pass


async def follow_user(
    session: AsyncSession,
    follower_id: uuid.UUID,
    following_id: uuid.UUID,
) -> Follower:
    if follower_id == following_id:
        raise FollowError("Cannot follow yourself")
    if not await user_exists(session, following_id):
        raise FollowError("User not found")
    if await are_blocked(session, follower_id, following_id):
        raise FollowError("Follow is not allowed")

    result = await session.execute(
        select(Follower).where(
            Follower.follower_id == follower_id,
            Follower.following_id == following_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    follower = Follower(follower_id=follower_id, following_id=following_id)
    session.add(follower)
    await session.commit()
    await session.refresh(follower)
    await _invalidate_user_relations(follower_id)
    await _invalidate_user_relations(following_id)
    # Notify the followed user (best-effort)
    try:
        await NotificationService.create_notification(
            session,
            user_id=str(following_id),
            type="follow",
            text=None,
            actor_id=str(follower_id),
            data={},
        )
    except Exception:
        pass
    return follower


async def unfollow_user(
    session: AsyncSession,
    follower_id: uuid.UUID,
    following_id: uuid.UUID,
) -> None:
    await session.execute(
        delete(Follower).where(
            Follower.follower_id == follower_id,
            Follower.following_id == following_id,
        )
    )
    await session.commit()
    await _invalidate_user_relations(follower_id)
    await _invalidate_user_relations(following_id)


async def list_following(session: AsyncSession, user_id: uuid.UUID) -> list[User]:
    result = await session.execute(
        select(User)
        .join(Follower, Follower.following_id == User.id)
        .where(Follower.follower_id == user_id)
    )
    users = result.scalars().all()
    return [user for user in users if not await are_blocked(session, user_id, user.id)]


async def list_followers(session: AsyncSession, user_id: uuid.UUID) -> list[User]:
    result = await session.execute(
        select(User)
        .join(Follower, Follower.follower_id == User.id)
        .where(Follower.following_id == user_id)
    )
    users = result.scalars().all()
    return [user for user in users if not await are_blocked(session, user_id, user.id)]


async def is_following(
    session: AsyncSession,
    follower_id: uuid.UUID,
    following_id: uuid.UUID,
) -> bool:
    if await are_blocked(session, follower_id, following_id):
        return False
    result = await session.execute(
        select(Follower).where(
            Follower.follower_id == follower_id,
            Follower.following_id == following_id,
        )
    )
    return result.scalar_one_or_none() is not None
