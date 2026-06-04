import uuid
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post_repost import PostRepost
from app.models.post import Post
from app.services.notification_service import NotificationService


class PostRepostService:
    @staticmethod
    async def get_repost_count(session: AsyncSession, post_id: str) -> int:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(
            select(func.count(PostRepost.id)).where(PostRepost.post_id == post_uuid)
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    async def get_user_repost_state(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
    ) -> bool:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(
            select(PostRepost.id).where(
                PostRepost.post_id == post_uuid,
                PostRepost.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def toggle_repost(
        session: AsyncSession,
        post_id: str,
        user_id: uuid.UUID,
    ) -> dict:
        post_uuid = uuid.UUID(post_id)

        existing_result = await session.execute(
            select(PostRepost.id).where(
                PostRepost.post_id == post_uuid,
                PostRepost.user_id == user_id,
            )
        )
        existing_id = existing_result.scalar_one_or_none()

        if existing_id is not None:
            await session.execute(delete(PostRepost).where(PostRepost.id == existing_id))
            await session.commit()
        else:
            session.add(PostRepost(post_id=post_uuid, user_id=user_id))
            await session.commit()
            # Notify post owner (best-effort)
            try:
                post = await session.get(Post, post_uuid)
                if post and str(post.user_id) != str(user_id):
                    await NotificationService.create_notification(
                        session,
                        user_id=str(post.user_id),
                        type="post_repost",
                        text=None,
                        actor_id=str(user_id),
                        data={"post_id": post_id},
                    )
            except Exception:
                pass

        count = await PostRepostService.get_repost_count(session, post_id)
        reposted = await PostRepostService.get_user_repost_state(session, post_id, user_id)

        return {"post_id": post_id, "reposts": count, "reposted": reposted}
