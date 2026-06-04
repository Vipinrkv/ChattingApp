import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.post_comment import PostComment
from app.models.post import Post
from app.services.notification_service import NotificationService


class PostCommentService:
    @staticmethod
    async def create_comment(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
        content: str,
    ) -> PostComment:
        comment = PostComment(
            post_id=uuid.UUID(post_id),
            user_id=user_id,
            content=content,
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        # Notify post owner (best-effort)
        try:
            post = await session.get(Post, uuid.UUID(post_id))
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
        return comment

    @staticmethod
    async def list_comments(
        session: AsyncSession,
        post_id: str,
        limit: int,
    ) -> list[PostComment]:
        result = await session.execute(
            select(PostComment)
            .where(PostComment.post_id == uuid.UUID(post_id))
            .order_by(desc(PostComment.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
