import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.post_comment import PostComment
from app.models.post import Post
from app.services.notification_service import NotificationService
from app.services.feed_event_chain_service import FeedEventChainService


class PostCommentService:
    @staticmethod
    async def create_comment(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
        content: str,
    ) -> PostComment:
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id
        comment = PostComment(
            post_id=post_uuid,
            user_id=user_id,
            content=content,
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)

        # Notify post owner (best-effort)
        try:
            post = await session.get(Post, post_uuid)
            if post and str(post.user_id) != str(user_id):
                await NotificationService.create_notification(
                    session,
                    user_id=str(post.user_id),
                    type="post_comment",
                    text=content,
                    actor_id=str(user_id),
                    data={"post_id": post_id, "comment_id": str(comment.id)},
                )
        except Exception:
            pass

        # Log event in FeedEventChain
        await FeedEventChainService.log_event(
            session,
            event_type="comment_created",
            event_id=comment.id,
            user_id=user_id,
            payload={"post_id": str(post_uuid), "content": content},
        )
        await session.commit()

        return comment

    @staticmethod
    async def list_comments(
        session: AsyncSession,
        post_id: str,
        limit: int,
    ) -> list[PostComment]:
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id
        result = await session.execute(
            select(PostComment)
            .where(PostComment.post_id == post_uuid)
            .order_by(desc(PostComment.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
