import uuid
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post_like import PostLike
from app.models.post import Post
from app.services.notification_service import NotificationService
from app.services.feed_event_chain_service import FeedEventChainService


class PostLikeError(Exception):
    pass


class PostLikeService:
    @staticmethod
    async def get_like_count(session: AsyncSession, post_id: str) -> int:
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id
        result = await session.execute(
            select(func.count(PostLike.id)).where(PostLike.post_id == post_uuid)
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    async def get_user_like_state(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
    ) -> bool:
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id
        result = await session.execute(
            select(PostLike.id).where(
                PostLike.post_id == post_uuid,
                PostLike.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def toggle_like(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
    ) -> dict:
        post_uuid = uuid.UUID(post_id) if isinstance(post_id, str) else post_id

        # Check existing like
        existing_result = await session.execute(
            select(PostLike.id).where(
                PostLike.post_id == post_uuid,
                PostLike.user_id == user_id,
            )
        )
        existing_id = existing_result.scalar_one_or_none()

        action = "like"
        if existing_id is not None:
            # Unlike
            action = "unlike"
            await session.execute(delete(PostLike).where(PostLike.id == existing_id))
            await session.commit()
        else:
            # Like
            session.add(PostLike(post_id=post_uuid, user_id=user_id))
            await session.commit()
            # Notify post owner (best-effort)
            try:
                post = await session.get(Post, post_uuid)
                if post and str(post.user_id) != str(user_id):
                    await NotificationService.create_notification(
                        session,
                        user_id=str(post.user_id),
                        type="post_like",
                        text=None,
                        actor_id=str(user_id),
                        data={"post_id": post_id},
                    )
            except Exception:
                pass

        # Log event in FeedEventChain
        await FeedEventChainService.log_event(
            session,
            event_type="like_toggled",
            event_id=post_uuid,
            user_id=user_id,
            payload={"action": action},
        )
        await session.commit()

        count = await PostLikeService.get_like_count(session, post_id)
        liked = await PostLikeService.get_user_like_state(session, post_id, user_id)

        return {"post_id": str(post_id), "likes": count, "liked": liked}
