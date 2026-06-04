#backend/app/core/auth.py
from fastapi import Depends, HTTPException, Request, status
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import get_firebase_uid
from app.database.connection import get_db_session
from app.services.user_service import UserService
from app.models.user import User


async def get_current_user(
    request: Request,
    firebase_uid: str = Depends(get_firebase_uid),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Reusable dependency that resolves the authenticated user."""
    user = await UserService.get_user_by_firebase_uid(session, firebase_uid)
    if not user:
        logging.getLogger(__name__).warning("Authenticated UID not found in DB: %s", firebase_uid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user profile not found",
        )
    request.state.user_id = str(user.id)
    return user


def require_role(*allowed_roles: str):
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logging.getLogger(__name__).warning(
                "User %s attempted action without required role. Required=%s, actual=%s",
                getattr(current_user, 'id', None),
                allowed_roles,
                current_user.role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return role_dependency


require_admin = require_role("admin")
require_moderator = require_role("admin", "moderator")
