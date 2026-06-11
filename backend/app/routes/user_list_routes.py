import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, NotFoundError, ForbiddenError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.user_list_schema import UserListCreate, UserListResponse, UserListMemberAdd
from app.schemas.post_schema import PostResponse
from app.services.user_list_service import UserListService
from app.core.pagination import parse_cursor

router = APIRouter(
    prefix="/api/v1/social/lists",
    tags=["social"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.post("", response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
async def create_user_list(
    payload: UserListCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> UserListResponse:
    return await UserListService.create_list(session, current_user.id, payload.name, payload.description)


@router.get("", response_model=list[UserListResponse])
async def list_user_lists(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserListResponse]:
    return await UserListService.get_lists(session, current_user.id)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_list(
    list_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    success = await UserListService.delete_list(session, current_user.id, list_id)
    if not success:
        raise NotFoundError("User list not found", code="list_not_found")


@router.post("/{list_id}/members", status_code=status.HTTP_201_CREATED)
async def add_list_member(
    list_id: uuid.UUID,
    payload: UserListMemberAdd,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        await UserListService.add_to_list(session, current_user.id, list_id, payload.user_id)
        return {"status": "ok"}
    except PermissionError as exc:
        raise ForbiddenError(str(exc), code="list_access_denied") from exc


@router.delete("/{list_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_list_member(
    list_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    success = await UserListService.remove_from_list(session, current_user.id, list_id, user_id)
    if not success:
        raise NotFoundError("List member or list not found", code="list_member_not_found")


@router.get("/{list_id}/posts", response_model=list[PostResponse])
async def get_list_posts(
    list_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[PostResponse]:
    before = None
    if cursor:
        try:
            before = parse_cursor(cursor)
        except ValueError as exc:
            raise BadRequestError("Invalid cursor format", code="invalid_cursor") from exc

    try:
        posts = await UserListService.get_list_posts(session, current_user.id, list_id, before, limit)
        return posts
    except PermissionError as exc:
        raise ForbiddenError(str(exc), code="list_access_denied") from exc
