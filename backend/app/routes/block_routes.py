# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\block_routes.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.models.user import User
from app.services.block_service import (
    CannotBlockSelfError,
    UserNotFoundError,
    block_user,
    list_blocked_users,
    unblock_user,
)
from app.schemas.user import UserResponse

router = APIRouter(
    tags=["blocks"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.get("", response_model=list[UserResponse])
async def list_blocks(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await list_blocked_users(session, current_user.id)


@router.post("/{blocked_id}", status_code=status.HTTP_201_CREATED)
async def block(
    blocked_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        block_row = await block_user(session, current_user_id, blocked_id)
        return {
            "blocker_id": block_row.blocker_id,
            "blocked_user_id": block_row.blocked_user_id,
            "created_at": block_row.created_at,
        }
    except CannotBlockSelfError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{blocked_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock(
    blocked_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    current_user_id = current_user.id
    await unblock_user(session, current_user_id, blocked_id)
