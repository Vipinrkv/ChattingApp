from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, not_, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friend import FriendRequest, FriendRequestStatus
from app.models.follower import Follower
from app.models.social_feature import CloseFriend, Poll, ShortVideo, Story, VerificationRequest
from app.models.user import User
from app.services.friend_service import are_friends, list_friends


class SocialFeatureService:
    @staticmethod
    async def suggested_users(session: AsyncSession, user_id: uuid.UUID, limit: int = 10) -> list[dict[str, object]]:
        friends = await list_friends(session, user_id)
        friend_ids = {friend.id for friend in friends}
        excluded = friend_ids | {user_id}
        followed_rows = await session.execute(select(Follower.following_id).where(Follower.follower_id == user_id))
        excluded.update(followed_rows.scalars().all())

        result = await session.execute(
            select(User)
            .where(User.is_active.is_(True), not_(User.id.in_(excluded)) if excluded else true())
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        suggestions = []
        for user in result.scalars().all():
            score = 1.0
            reason = "active new member"
            mutual_count = await SocialFeatureService.mutual_friend_count(session, user_id, user.id)
            if mutual_count:
                score += mutual_count * 2
                reason = f"{mutual_count} mutual friend{'s' if mutual_count != 1 else ''}"
            suggestions.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "score": score,
                    "reason": reason,
                    "is_verified": bool(getattr(user, "is_verified", False)),
                }
            )
        return sorted(suggestions, key=lambda item: item["score"], reverse=True)

    @staticmethod
    async def mutual_friend_count(session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> int:
        mutuals = await SocialFeatureService.mutual_friends(session, user_a, user_b)
        return len(mutuals)

    @staticmethod
    async def mutual_friends(session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> list[User]:
        friends_a = {friend.id for friend in await list_friends(session, user_a)}
        friends_b = {friend.id for friend in await list_friends(session, user_b)}
        mutual_ids = friends_a & friends_b
        if not mutual_ids:
            return []
        result = await session.execute(select(User).where(User.id.in_(mutual_ids)))
        return list(result.scalars().all())

    @staticmethod
    async def add_close_friend(session: AsyncSession, owner_id: uuid.UUID, friend_id: uuid.UUID) -> CloseFriend:
        if owner_id == friend_id:
            raise ValueError("Cannot add yourself as a close friend")
        if not await are_friends(session, owner_id, friend_id):
            raise ValueError("Close friends must already be friends")
        existing = await session.scalar(
            select(CloseFriend).where(CloseFriend.owner_id == owner_id, CloseFriend.friend_id == friend_id)
        )
        if existing:
            return existing
        close_friend = CloseFriend(owner_id=owner_id, friend_id=friend_id)
        session.add(close_friend)
        await session.commit()
        await session.refresh(close_friend)
        return close_friend

    @staticmethod
    async def remove_close_friend(session: AsyncSession, owner_id: uuid.UUID, friend_id: uuid.UUID) -> None:
        row = await session.scalar(select(CloseFriend).where(CloseFriend.owner_id == owner_id, CloseFriend.friend_id == friend_id))
        if row:
            await session.delete(row)
            await session.commit()

    @staticmethod
    async def create_poll(session: AsyncSession, owner_id: uuid.UUID, question: str, options: list[str], expires_at=None) -> Poll:
        normalized = [option.strip() for option in options if option.strip()]
        if len(set(normalized)) < 2:
            raise ValueError("Poll requires at least two unique options")
        poll = Poll(owner_id=owner_id, question=question, options=normalized, votes={}, expires_at=expires_at)
        session.add(poll)
        await session.commit()
        await session.refresh(poll)
        return poll

    @staticmethod
    async def vote_poll(session: AsyncSession, poll_id: uuid.UUID, user_id: uuid.UUID, option: str) -> Poll:
        poll = await session.scalar(select(Poll).where(Poll.id == poll_id))
        if not poll:
            raise ValueError("Poll not found")
        if option not in poll.options:
            raise ValueError("Invalid poll option")
        if poll.expires_at and poll.expires_at < datetime.utcnow():
            raise ValueError("Poll has expired")
        votes = dict(poll.votes or {})
        previous = votes.get(str(user_id))
        if previous:
            counts = {key: 0 for key in poll.options}
            for selected in votes.values():
                counts[selected] = counts.get(selected, 0) + 1
        votes[str(user_id)] = option
        poll.votes = votes
        await session.commit()
        await session.refresh(poll)
        return poll

    @staticmethod
    def poll_counts(poll: Poll) -> dict[str, int]:
        counts = {option: 0 for option in poll.options}
        for selected in (poll.votes or {}).values():
            counts[selected] = counts.get(selected, 0) + 1
        return counts

    @staticmethod
    async def create_story(session: AsyncSession, owner_id: uuid.UUID, media_url: str, caption: str | None, audience: str) -> Story:
        story = Story(
            owner_id=owner_id,
            media_url=media_url,
            caption=caption,
            audience=audience,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story

    @staticmethod
    async def stories(session: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[Story]:
        friend_ids = {friend.id for friend in await list_friends(session, user_id)}
        close_rows = await session.execute(select(CloseFriend.owner_id).where(CloseFriend.friend_id == user_id))
        close_owner_ids = set(close_rows.scalars().all())
        visible_owner_ids = friend_ids | close_owner_ids | {user_id}
        result = await session.execute(
            select(Story)
            .where(
                Story.expires_at >= datetime.utcnow(),
                or_(
                    Story.owner_id == user_id,
                    and_(Story.audience == "public"),
                    and_(Story.audience == "friends", Story.owner_id.in_(visible_owner_ids)),
                    and_(Story.audience == "close_friends", Story.owner_id.in_(close_owner_ids)),
                ),
            )
            .order_by(Story.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_short_video(session: AsyncSession, owner_id: uuid.UUID, **kwargs) -> ShortVideo:
        video = ShortVideo(owner_id=owner_id, **kwargs)
        session.add(video)
        await session.commit()
        await session.refresh(video)
        return video

    @staticmethod
    async def reels(session: AsyncSession, limit: int = 30) -> list[ShortVideo]:
        result = await session.execute(select(ShortVideo).order_by(ShortVideo.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def request_verification(session: AsyncSession, user_id: uuid.UUID, reason: str | None, evidence: dict[str, object]) -> VerificationRequest:
        request = VerificationRequest(user_id=user_id, reason=reason, evidence=evidence)
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request
