from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from app.models.post import Post, PostVisibility
from app.models.friend import FriendRequest, FriendRequestStatus
from app.models.follower import Follower
from app.models.block import Block
import logging

logger = logging.getLogger(__name__)


class PrivacyEngine:
    @staticmethod
    async def can_view_post(
        session: AsyncSession, viewer_id: str, post: Post
    ) -> bool:
        """
        Determine if a user can view a post.
        
        Rules:
        - Blocked users cannot view
        - Own posts always visible
        - PUBLIC posts visible to all non-blocked
        - FRIENDS posts visible to friends
        - FOLLOWERS posts visible to followers
        - CUSTOM posts visible to allowed users
        """
        # Check if viewer is blocked
        blocked_result = await session.execute(
            select(Block).where(
                and_(
                    Block.blocker_id == post.user_id,
                    Block.blocked_user_id == viewer_id,
                )
            )
        )
        if blocked_result.scalars().first():
            return False

        # Own posts
        if post.user_id == viewer_id:
            return True

        # Check visibility
        if post.visibility == PostVisibility.PUBLIC:
            return True

        if post.visibility == PostVisibility.FRIENDS:
            friends_result = await session.execute(
                select(FriendRequest).where(
                    and_(
                        FriendRequest.status == FriendRequestStatus.ACCEPTED,
                        or_(
                            and_(
                                FriendRequest.requester_id == post.user_id,
                                FriendRequest.addressee_id == viewer_id,
                            ),
                            and_(
                                FriendRequest.requester_id == viewer_id,
                                FriendRequest.addressee_id == post.user_id,
                            ),
                        ),
                    )
                )
            )
            return friends_result.scalars().first() is not None

        if post.visibility == PostVisibility.FOLLOWERS:
            following_result = await session.execute(
                select(Follower).where(
                    and_(
                        Follower.following_id == post.user_id,
                        Follower.follower_id == viewer_id,
                    )
                )
            )
            return following_result.scalars().first() is not None

        if post.visibility == PostVisibility.CUSTOM:
            # CUSTOM posts not visible by default in this implementation
            return False

        return False

    @staticmethod
    async def can_chat(
        session: AsyncSession, user_id: str, target_user_id: str
    ) -> bool:
        """Check if users can chat (not blocked)"""
        blocked_result = await session.execute(
            select(Block).where(
                or_(
                    and_(
                        Block.blocker_id == user_id,
                        Block.blocked_user_id == target_user_id,
                    ),
                    and_(
                        Block.blocker_id == target_user_id,
                        Block.blocked_user_id == user_id,
                    ),
                )
            )
        )
        return blocked_result.scalars().first() is None
