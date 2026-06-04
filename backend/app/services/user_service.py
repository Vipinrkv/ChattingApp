# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\user_service.py
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_value, encrypt_value
from app.core.service_response import ServiceResult, error_result, success_result
from app.core.transaction import run_transaction
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserAlreadyExistsError(Exception):
    pass


class UsernameAlreadyTakenError(Exception):
    pass


class UserService:
    @staticmethod
    async def get_user_by_firebase_uid(session: AsyncSession, firebase_uid: str) -> User | None:
        result = await session.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        user = result.scalar_one_or_none()
        if user and user.phone:
            user.phone = decrypt_value(user.phone)
        return user

    @staticmethod
    async def create_user_if_not_exists(
        session: AsyncSession,
        firebase_uid: str,
        payload,
    ) -> ServiceResult[User]:
        existing_user = await UserService.get_user_by_firebase_uid(session, firebase_uid)
        if existing_user:
            return success_result(existing_user)

        username_result = await session.execute(
            select(User.id).where(User.username == payload.username)
        )
        if username_result.scalar_one_or_none():
            return error_result("Username already taken", code="username_conflict")

        user = User(
            firebase_uid=firebase_uid,
            phone=encrypt_value(payload.phone),
            username=payload.username,
            email=payload.email,
            bio=payload.bio,
        )

        try:
            session.add(user)
            await session.flush()
            await session.refresh(user)
            result = user
        except IntegrityError as exc:
            return error_result("User already exists", code="user_exists", details=str(exc))

        if result.phone:
            result.phone = decrypt_value(result.phone)
        return success_result(result)

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user and user.phone:
            user.phone = decrypt_value(user.phone)
        return user

    @staticmethod
    async def create_user(session: AsyncSession, firebase_uid: str, user_data: UserCreate) -> User:
        # Check if username exists
        existing = await UserService.get_user_by_username(session, user_data.username)
        if existing:
            raise UsernameAlreadyTakenError("Username already taken")

        user = User(
            firebase_uid=firebase_uid,
            phone=encrypt_value(user_data.phone) if user_data.phone else None,
            username=user_data.username,
            email=user_data.email,
            bio=user_data.bio,
        )
        async def persist_user() -> User:
            session.add(user)
            await session.refresh(user)
            return user

        result = await run_transaction(session, persist_user)
        if result.phone:
            result.phone = decrypt_value(result.phone)
        return result

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user and user.phone:
            user.phone = decrypt_value(user.phone)
        return user

    @staticmethod
    async def get_all_users(session: AsyncSession, exclude_id: str | None = None) -> list[User]:
        query = select(User)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)

        result = await session.execute(query)
        users = result.scalars().all()
        for user in users:
            if user.phone:
                user.phone = decrypt_value(user.phone)
        return users

    @staticmethod
    async def search_users(
        session: AsyncSession,
        query_text: str,
        exclude_id: str | None = None,
        limit: int = 20,
    ) -> list[User]:
        stmt = select(User).where(
            or_(
                User.username.ilike(f"%{query_text}%"),
                User.email.ilike(f"%{query_text}%"),
                User.bio.ilike(f"%{query_text}%"),
            )
        )

        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)

        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        users = result.scalars().all()
        for user in users:
            if user.phone:
                user.phone = decrypt_value(user.phone)
        return users

    @staticmethod
    async def update_user(session: AsyncSession, user_id: str, user_data: UserUpdate) -> User | None:
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return None

        if user_data.username:
            existing = await UserService.get_user_by_username(session, user_data.username)
            if existing and existing.id != user.id:
                raise UsernameAlreadyTakenError("Username already taken")
            user.username = user_data.username

        if user_data.phone is not None:
            user.phone = encrypt_value(user_data.phone)
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.bio is not None:
            user.bio = user_data.bio

        async def persist_user() -> User:
            await session.refresh(user)
            return user

        result = await run_transaction(session, persist_user)
        if result.phone:
            result.phone = decrypt_value(result.phone)
        return result
