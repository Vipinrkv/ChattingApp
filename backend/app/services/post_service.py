import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from app.models.post import Post, PostVisibility
from app.schemas.post_schema import PostCreate, PostUpdate
from app.services.moderation_service import ModerationService
from app.services.feed_event_chain_service import FeedEventChainService

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

        quoted_post_uuid = uuid.UUID(post_data.quoted_post_id) if post_data.quoted_post_id else None

        post = Post(
            user_id=uuid.UUID(str(user_id)),
            content=post_data.content,
            visibility=post_data.visibility,
            quoted_post_id=quoted_post_uuid,
        )
        session.add(post)
        await session.flush()

        # Log event in FeedEventChain
        await FeedEventChainService.log_event(
            session,
            event_type="post_created",
            event_id=post.id,
            user_id=uuid.UUID(str(user_id)),
            payload={
                "content": post.content,
                "visibility": str(post.visibility),
                "quoted_post_id": str(post.quoted_post_id) if post.quoted_post_id else None,
            },
        )

        # Commit event log
        await session.commit()
        
        # Load relationship
        stmt = select(Post).options(selectinload(Post.quoted_post)).where(Post.id == post.id)
        res = await session.execute(stmt)
        return res.scalar_one()

    @staticmethod
    async def get_post(session: AsyncSession, post_id: str) -> Post:
        """Get post by ID"""
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id
        stmt = select(Post).options(selectinload(Post.quoted_post)).where(Post.id == post_uuid)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def update_post(
        session: AsyncSession, post_id: str, post_data: PostUpdate
    ) -> Post:
        """Update post"""
        post = await PostService.get_post(session, post_id)
        if not post:
            return None

        if post_data.content:
            post.content = post_data.content
        if post_data.visibility:
            post.visibility = post_data.visibility

        await session.flush()

        # Log event in FeedEventChain
        await FeedEventChainService.log_event(
            session,
            event_type="post_updated",
            event_id=post.id,
            user_id=post.user_id,
            payload={
                "content": post.content,
                "visibility": str(post.visibility),
            },
        )
        await session.commit()
        return post

    @staticmethod
    async def delete_post(session: AsyncSession, post_id: str) -> bool:
        """Delete post"""
        post = await PostService.get_post(session, post_id)
        if post:
            post_id_val = post.id
            user_id_val = post.user_id
            await session.delete(post)
            await session.flush()

            # Log event in FeedEventChain
            await FeedEventChainService.log_event(
                session,
                event_type="post_deleted",
                event_id=post_id_val,
                user_id=user_id_val,
                payload={},
            )
            await session.commit()
            return True
        return False

    @staticmethod
    async def get_user_posts(
        session: AsyncSession, user_id: str, skip: int = 0, limit: int = 10
    ):
        """Get user's posts"""
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.quoted_post))
            .where(Post.user_id == user_uuid)
            .order_by(desc(Post.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
