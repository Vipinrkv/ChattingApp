import uuid
from datetime import datetime
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_list import UserList, UserListMember
from app.models.post import Post
from app.services.feed_service import FeedService


class UserListService:
    @staticmethod
    async def create_list(
        session: AsyncSession,
        owner_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> UserList:
        user_list = UserList(
            owner_id=owner_id,
            name=name,
            description=description,
        )
        session.add(user_list)
        await session.commit()
        await session.refresh(user_list)
        return user_list

    @staticmethod
    async def delete_list(
        session: AsyncSession,
        owner_id: uuid.UUID,
        list_id: uuid.UUID,
    ) -> bool:
        stmt = select(UserList).where(UserList.id == list_id, UserList.owner_id == owner_id)
        res = await session.execute(stmt)
        user_list = res.scalar_one_or_none()
        if not user_list:
            return False

        await session.delete(user_list)
        await session.commit()
        return True

    @staticmethod
    async def add_to_list(
        session: AsyncSession,
        owner_id: uuid.UUID,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserListMember:
        # Check if list belongs to owner
        list_stmt = select(UserList).where(UserList.id == list_id, UserList.owner_id == owner_id)
        list_res = await session.execute(list_stmt)
        if not list_res.scalar_one_or_none():
            raise PermissionError("User list not found or access denied")

        # Check if already a member
        member_stmt = select(UserListMember).where(
            UserListMember.list_id == list_id,
            UserListMember.user_id == user_id,
        )
        member_res = await session.execute(member_stmt)
        member = member_res.scalar_one_or_none()

        if not member:
            member = UserListMember(list_id=list_id, user_id=user_id)
            session.add(member)
            await session.commit()
            await session.refresh(member)
        return member

    @staticmethod
    async def remove_from_list(
        session: AsyncSession,
        owner_id: uuid.UUID,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        # Check if list belongs to owner
        list_stmt = select(UserList).where(UserList.id == list_id, UserList.owner_id == owner_id)
        list_res = await session.execute(list_stmt)
        if not list_res.scalar_one_or_none():
            return False

        stmt = delete(UserListMember).where(
            UserListMember.list_id == list_id,
            UserListMember.user_id == user_id,
        )
        await session.execute(stmt)
        await session.commit()
        return True

    @staticmethod
    async def get_lists(
        session: AsyncSession,
        owner_id: uuid.UUID,
    ) -> list[UserList]:
        stmt = select(UserList).where(UserList.owner_id == owner_id).order_by(UserList.created_at.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_list_posts(
        session: AsyncSession,
        owner_id: uuid.UUID,
        list_id: uuid.UUID,
        before: datetime | None = None,
        limit: int = 20,
    ) -> list[Post]:
        # Verify ownership
        list_stmt = select(UserList).where(UserList.id == list_id, UserList.owner_id == owner_id)
        list_res = await session.execute(list_stmt)
        if not list_res.scalar_one_or_none():
            raise PermissionError("Access denied")

        # Get list members
        members_stmt = select(UserListMember.user_id).where(UserListMember.list_id == list_id)
        members_res = await session.execute(members_stmt)
        member_ids = list(members_res.scalars().all())

        if not member_ids:
            return []

        # Get relationships for privacy filter
        relations = await FeedService._load_relationships(session, str(owner_id))
        friends = relations["friends"]
        following = relations["following"]
        blocked = relations["blocked"]

        # Build query
        query = (
            select(Post)
            .where(
                and_(
                    Post.user_id.in_(member_ids),
                    FeedService._visible_post_filter(str(owner_id), friends, following, blocked),
                )
            )
            .order_by(Post.created_at.desc())
        )

        if before:
            query = query.where(Post.created_at < before)
        query = query.limit(limit)

        res = await session.execute(query)
        return list(res.scalars().all())
