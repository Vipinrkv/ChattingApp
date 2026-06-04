from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_
from app.models.group_post import GroupPost
from app.models.group_member import GroupMember
from app.services.moderation_service import ModerationService
import logging

logger = logging.getLogger(__name__)


class GroupFeedService:
    @staticmethod
    async def create_group_post(
        session: AsyncSession, group_id: str, user_id: str, content: str
    ) -> GroupPost:
        """Create a post in group"""
        membership_query = await session.execute(
            select(GroupMember).where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                )
            )
        )
        membership = membership_query.scalar_one_or_none()
        if not membership:
            raise PermissionError("User must be a group member to create a post")

        await ModerationService.validate_text_content(content)
        post = GroupPost(
            group_id=group_id,
            user_id=user_id,
            content=content,
        )
        session.add(post)
        await session.flush()
        return post

    @staticmethod
    async def get_group_feed(
        session: AsyncSession,
        group_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ):
        """Get group feed (only visible to members)"""
        membership_query = await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.status == "active",
            )
        )
        membership = membership_query.scalar_one_or_none()
        if not membership:
            raise PermissionError("Only group members can view this feed")

        result = await session.execute(
            select(GroupPost)
            .where(GroupPost.group_id == group_id)
            .order_by(desc(GroupPost.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def delete_group_post(
        session: AsyncSession, post_id: str
    ) -> bool:
        """Delete a group post"""
        post = await session.get(GroupPost, post_id)
        if post:
            await session.delete(post)
            await session.flush()
            return True
        return False
