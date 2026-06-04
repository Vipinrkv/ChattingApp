# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\friend_service.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friend import FriendRequest, FriendRequestStatus
from app.models.user import User
from app.services.block_service import are_blocked, user_exists
from app.services.notification_service import NotificationService
from app.core.redis_cache import redis_cache


async def _invalidate_user_relations(user_id: uuid.UUID) -> None:
    if redis_cache.enabled:
        await redis_cache.delete(f"user:relations:{user_id}")


class FriendRequestError(Exception):
    pass


async def send_friend_request(
    session: AsyncSession,
    requester_id: uuid.UUID,
    addressee_id: uuid.UUID,
) -> FriendRequest:
    if requester_id == addressee_id:
        raise FriendRequestError("Cannot send a friend request to yourself")
    if not await user_exists(session, addressee_id):
        raise FriendRequestError("User not found")
    if await are_blocked(session, requester_id, addressee_id):
        raise FriendRequestError("Friend request is not allowed")

    existing = await session.execute(
        select(FriendRequest).where(
            or_(
                (FriendRequest.requester_id == requester_id)
                & (FriendRequest.addressee_id == addressee_id),
                (FriendRequest.requester_id == addressee_id)
                & (FriendRequest.addressee_id == requester_id),
            )
        )
    )
    friend_request = existing.scalar_one_or_none()
    if friend_request:
        if (
            friend_request.status == FriendRequestStatus.DECLINED
            and friend_request.requester_id == requester_id
        ):
            friend_request.status = FriendRequestStatus.PENDING
            friend_request.responded_at = None
            await session.commit()
            await session.refresh(friend_request)
        return friend_request

    friend_request = FriendRequest(
        requester_id=requester_id,
        addressee_id=addressee_id,
        status=FriendRequestStatus.PENDING,
    )
    session.add(friend_request)
    await session.commit()
    await session.refresh(friend_request)
    # Notify the addressee about the friend request (best-effort)
    try:
        await NotificationService.create_notification(
            session,
            user_id=str(addressee_id),
            type="friend_request",
            text=None,
            actor_id=str(requester_id),
            data={"request_id": str(friend_request.id)},
        )
    except Exception:
        pass
    return friend_request


async def respond_to_friend_request(
    session: AsyncSession,
    current_user_id: uuid.UUID,
    request_id: uuid.UUID,
    action: str,
) -> FriendRequest:
    result = await session.execute(
        select(FriendRequest).where(FriendRequest.id == request_id)
    )
    friend_request = result.scalar_one_or_none()
    if not friend_request:
        raise FriendRequestError("Friend request not found")
    if friend_request.addressee_id != current_user_id:
        raise FriendRequestError("Only the recipient can respond")
    if friend_request.status != "pending":
        raise FriendRequestError("Friend request has already been handled")
    if await are_blocked(session, friend_request.requester_id, friend_request.addressee_id):
        raise FriendRequestError("Friend request is not allowed")

    friend_request.status = (
        FriendRequestStatus.ACCEPTED
        if action == "accept"
        else FriendRequestStatus.DECLINED
    )
    friend_request.responded_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(friend_request)
    if friend_request.status == FriendRequestStatus.ACCEPTED:
        await _invalidate_user_relations(friend_request.requester_id)
        await _invalidate_user_relations(friend_request.addressee_id)
    # Notify the requester about the response (best-effort)
    try:
        await NotificationService.create_notification(
            session,
            user_id=str(friend_request.requester_id),
            type=("friend_request_accepted" if friend_request.status == FriendRequestStatus.ACCEPTED else "friend_request_declined"),
            text=None,
            actor_id=str(friend_request.addressee_id),
            data={"request_id": str(friend_request.id)},
        )
    except Exception:
        pass
    return friend_request


async def list_friends(session: AsyncSession, user_id: uuid.UUID) -> list[User]:
    result = await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == FriendRequestStatus.ACCEPTED,
            or_(
                FriendRequest.requester_id == user_id,
                FriendRequest.addressee_id == user_id,
            ),
        )
    )
    friend_rows = result.scalars().all()
    friend_ids = [
        row.addressee_id if row.requester_id == user_id else row.requester_id
        for row in friend_rows
    ]
    if not friend_ids:
        return []

    users_result = await session.execute(select(User).where(User.id.in_(friend_ids)))
    friends = users_result.scalars().all()
    return [
        friend
        for friend in friends
        if not await are_blocked(session, user_id, friend.id)
    ]


async def list_pending_friend_requests(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[FriendRequest]:
    result = await session.execute(
        select(FriendRequest)
        .where(
            FriendRequest.addressee_id == user_id,
            FriendRequest.status == FriendRequestStatus.PENDING,
        )
        .order_by(FriendRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def are_friends(
    session: AsyncSession,
    user_a_id: uuid.UUID,
    user_b_id: uuid.UUID,
) -> bool:
    if await are_blocked(session, user_a_id, user_b_id):
        return False
    result = await session.execute(
        select(FriendRequest.id).where(
            FriendRequest.status == FriendRequestStatus.ACCEPTED,
            or_(
                (FriendRequest.requester_id == user_a_id)
                & (FriendRequest.addressee_id == user_b_id),
                (FriendRequest.requester_id == user_b_id)
                & (FriendRequest.addressee_id == user_a_id),
            ),
        )
    )
    return result.scalar_one_or_none() is not None
