# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\group_routes.py
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, ForbiddenError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.group_schema import (
    GroupAnalyticsResponse,
    GroupCreateRequest,
    GroupEventCreateRequest,
    GroupEventResponse,
    GroupInviteRequest,
    GroupListResponse,
    GroupMemberResponse,
    GroupMessageCreateRequest,
    GroupMessageResponse,
    GroupResponse,
    GroupSettingsRequest,
    GroupTemplateResponse,
    GroupMemberRoleUpdateRequest,
)
from app.services.group_service import (
    GroupError,
    create_group,
    create_group_event,
    get_group_analytics,
    get_group_messages,
    invite_user,
    join_group,
    leave_group,
    list_group_events,
    list_groups,
    list_members,
    list_group_templates,
    request_group_verification,
    search_groups,
    send_group_message,
    serialize_group_message,
    update_group_settings,
    assign_group_member_role,
)

router = APIRouter(
    tags=["groups"],
    dependencies=[Depends(get_current_user_dep)],
)


def _group_bad_request(exc: Exception, code: str = "group_request_invalid") -> BadRequestError:
    return BadRequestError(str(exc), code=code)


def _group_forbidden(exc: Exception, code: str = "group_forbidden") -> ForbiddenError:
    return ForbiddenError(str(exc), code=code)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_new_group(
    payload: GroupCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    current_user_id = current_user.id
    try:
        return await create_group(
            session,
            current_user_id,
            payload.name,
            payload.description,
            payload.type,
            payload.organization_name,
            payload.category,
            payload.tags,
            payload.is_discoverable,
            payload.announcement_only,
            payload.template_key,
            payload.onboarding_steps,
            payload.welcome_message,
            payload.growth_goal,
        )
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_create_invalid") from exc


@router.post("/{group_id}/join", response_model=GroupMemberResponse)
async def join_existing_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupMemberResponse:
    current_user_id = current_user.id
    try:
        return await join_group(session, current_user_id, group_id)
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_join_invalid") from exc


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_existing_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    current_user_id = current_user.id
    await leave_group(session, current_user_id, group_id)


@router.post("/{group_id}/invite", response_model=GroupMemberResponse)
async def invite_group_user(
    group_id: uuid.UUID,
    payload: GroupInviteRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupMemberResponse:
    current_user_id = current_user.id
    try:
        return await invite_user(session, current_user_id, group_id, payload.user_id)
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_invite_invalid") from exc


@router.get("", response_model=list[GroupListResponse])
async def list_available_groups(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await list_groups(session, current_user.id)


@router.get("/templates", response_model=list[GroupTemplateResponse])
async def get_group_templates() -> list[dict]:
    return list_group_templates()


@router.get("/search", response_model=list[GroupListResponse])
async def search_groups_endpoint(
    q: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await search_groups(session, current_user.id, q, limit=50)


@router.patch("/{group_id}/settings", response_model=GroupResponse)
async def update_group_feature_settings(
    group_id: uuid.UUID,
    payload: GroupSettingsRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    try:
        return await update_group_settings(
            session,
            current_user.id,
            group_id,
            **payload.dict(exclude_unset=True),
        )
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_settings_invalid") from exc


@router.post("/{group_id}/verify", response_model=GroupResponse)
async def request_verification(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    try:
        return await request_group_verification(session, current_user.id, group_id)
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_verification_invalid") from exc


@router.get("/{group_id}/analytics", response_model=GroupAnalyticsResponse)
async def get_group_growth_analytics(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        return await get_group_analytics(session, current_user.id, group_id)
    except GroupError as exc:
        raise _group_forbidden(exc, code="group_analytics_forbidden") from exc


@router.post("/{group_id}/events", response_model=GroupEventResponse, status_code=status.HTTP_201_CREATED)
async def schedule_group_event(
    group_id: uuid.UUID,
    payload: GroupEventCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupEventResponse:
    try:
        return await create_group_event(
            session,
            current_user.id,
            group_id,
            payload.title,
            payload.description,
            payload.starts_at,
            payload.ends_at,
            payload.location,
            payload.is_online,
        )
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_event_invalid") from exc


@router.get("/{group_id}/events", response_model=list[GroupEventResponse])
async def list_events_for_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[GroupEventResponse]:
    try:
        return await list_group_events(session, current_user.id, group_id)
    except GroupError as exc:
        raise _group_forbidden(exc, code="group_events_forbidden") from exc


@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
async def get_group_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    current_user_id = current_user.id
    try:
        return await list_members(session, current_user_id, group_id)
    except GroupError as exc:
        raise _group_forbidden(exc, code="group_members_forbidden") from exc


@router.post("/{group_id}/messages", response_model=GroupMessageResponse)
async def create_group_message(
    group_id: uuid.UUID,
    payload: GroupMessageCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        message = await send_group_message(session, current_user_id, group_id, payload.content)
        return await serialize_group_message(session, message)
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_message_rejected") from exc


@router.get("/{group_id}/messages", response_model=list[GroupMessageResponse])
async def list_group_messages(
    group_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    current_user_id = current_user.id
    try:
        return await get_group_messages(session, current_user_id, group_id, limit)
    except GroupError as exc:
        raise _group_forbidden(exc, code="group_messages_forbidden") from exc


@router.patch("/{group_id}/members/{user_id}/role", response_model=GroupMemberResponse)
async def update_member_role(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: GroupMemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> GroupMemberResponse:
    try:
        return await assign_group_member_role(
            session,
            current_user.id,
            group_id,
            user_id,
            payload.role,
        )
    except GroupError as exc:
        raise _group_bad_request(exc, code="group_member_role_invalid") from exc
