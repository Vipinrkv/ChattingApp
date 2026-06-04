# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\block_service.py
import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.follower import Follower
from app.models.friend import FriendRequest
from app.models.user import User
from app.core.redis_cache import redis_cache


async def _invalidate_user_relations(user_id: uuid.UUID) -> None:
    if redis_cache.enabled:
        await redis_cache.delete(f"user:relations:{user_id}")


class UserNotFoundError(Exception):
    pass


class CannotBlockSelfError(Exception):
    pass


async def user_exists(session: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await session.execute(select(User.id).where(User.id == user_id))
    return result.scalar_one_or_none() is not None


async def are_blocked(
    session: AsyncSession,
    user_a_id: uuid.UUID,
    user_b_id: uuid.UUID,
) -> bool:
    result = await session.execute(
        select(Block).where(
            or_(
                (Block.blocker_id == user_a_id) & (Block.blocked_user_id == user_b_id),
                (Block.blocker_id == user_b_id) & (Block.blocked_user_id == user_a_id),
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def list_blocked_users(session: AsyncSession, blocker_id: uuid.UUID) -> list[User]:
    result = await session.execute(
        select(User)
        .join(Block, Block.blocked_user_id == User.id)
        .where(Block.blocker_id == blocker_id)
        .order_by(Block.created_at.desc())
    )
    return list(result.scalars().all())


async def block_user(
    session: AsyncSession,
    blocker_id: uuid.UUID,
    blocked_id: uuid.UUID,
) -> Block:
    if blocker_id == blocked_id:
        raise CannotBlockSelfError("Cannot block yourself")
    if not await user_exists(session, blocked_id):
        raise UserNotFoundError("User not found")

    existing = await session.execute(
        select(Block).where(
            Block.blocker_id == blocker_id,
            Block.blocked_user_id == blocked_id,
        )
    )
    block = existing.scalar_one_or_none()
    if block:
        return block

    block = Block(blocker_id=blocker_id, blocked_user_id=blocked_id)
    session.add(block)

    await session.execute(
        delete(FriendRequest).where(
            or_(
                (FriendRequest.requester_id == blocker_id)
                & (FriendRequest.addressee_id == blocked_id),
                (FriendRequest.requester_id == blocked_id)
                & (FriendRequest.addressee_id == blocker_id),
            )
        )
    )
    await session.execute(
        delete(Follower).where(
            or_(
                (Follower.follower_id == blocker_id)
                & (Follower.following_id == blocked_id),
                (Follower.follower_id == blocked_id)
                & (Follower.following_id == blocker_id),
            )
        )
    )
    await session.commit()
    await _invalidate_user_relations(blocker_id)
    await _invalidate_user_relations(blocked_id)
    return block


async def unblock_user(
    session: AsyncSession,
    blocker_id: uuid.UUID,
    blocked_id: uuid.UUID,
) -> None:
    await session.execute(
        delete(Block).where(
            Block.blocker_id == blocker_id,
            Block.blocked_user_id == blocked_id,
        )
    )
    await session.commit()
    await _invalidate_user_relations(blocker_id)
    await _invalidate_user_relations(blocked_id)
