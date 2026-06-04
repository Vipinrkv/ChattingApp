from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app.models.post import Post, PostVisibility
from app.schemas.post_schema import PostCreate, PostUpdate
from app.services.moderation_service import ModerationService
import logging

logger = logging.getLogger(__name__)


class PostService:
    @staticmethod
    async def create_post(
        session: AsyncSession, user_id: str, post_data: PostCreate
    ) -> Post:
        """Create a new post"""
        await ModerationService.validate_text_content(post_data.content)

        ai_result = await ModerationService.validate_content_with_ai(
            session,
            content_id=str(uuid.uuid4()),
            content_type="post",
            content_text=post_data.content,
        )
        if ai_result.get("should_auto_moderate"):
            await ModerationService.apply_ai_auto_moderation(
                session,
                user_id,
                ai_result.get("content_id"),
                ai_analysis=ai_result,
            )
            raise Exception("Post blocked by AI moderation policy")

        post = Post(
            user_id=user_id,
            content=post_data.content,
            visibility=post_data.visibility,
        )
        session.add(post)
        await session.flush()
        return post

    @staticmethod
    async def get_post(session: AsyncSession, post_id: str) -> Post:
        """Get post by ID"""
        return await session.get(Post, post_id)

    @staticmethod
    async def update_post(
        session: AsyncSession, post_id: str, post_data: PostUpdate
    ) -> Post:
        """Update post"""
        post = await session.get(Post, post_id)
        if not post:
            return None

        if post_data.content:
            post.content = post_data.content
        if post_data.visibility:
            post.visibility = post_data.visibility

        await session.flush()
        return post

    @staticmethod
    async def delete_post(session: AsyncSession, post_id: str) -> bool:
        """Delete post"""
        post = await session.get(Post, post_id)
        if post:
            await session.delete(post)
            await session.flush()
            return True
        return False

    @staticmethod
    async def get_user_posts(
        session: AsyncSession, user_id: str, skip: int = 0, limit: int = 10
    ):
        """Get user's posts"""
        result = await session.execute(
            select(Post)
            .where(Post.user_id == user_id)
            .order_by(desc(Post.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
