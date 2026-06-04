# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\group_service.py
import secrets
import uuid
from datetime import datetime

from sqlalchemy import String, and_, cast, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_value, encrypt_value
from app.models.group import Group
from app.models.group_event import GroupEvent
from app.models.group_member import GroupMember
from app.models.group_message import GroupMessage
from app.models.user import User
from app.schemas.group_schema import DEFAULT_GROUP_TEMPLATES
from app.services.block_service import are_blocked, user_exists
from app.services.moderation_service import ModerationError, ModerationService
from app.services.notification_service import NotificationService


class GroupError(Exception):
    pass


ALIAS_ADJECTIVES = ["Quiet", "Blue", "Silver", "Hidden", "Bright", "Calm"]
ALIAS_NOUNS = ["Member", "Voice", "Signal", "Guest", "Node", "Spark"]
ADMIN_ROLES = {"admin", "owner", "moderator"}


def _generate_alias() -> str:
    return (
        f"{secrets.choice(ALIAS_ADJECTIVES)} "
        f"{secrets.choice(ALIAS_NOUNS)} {secrets.randbelow(9000) + 1000}"
    )


async def _get_group(session: AsyncSession, group_id: uuid.UUID) -> Group:
    result = await session.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise GroupError("Group not found")
    return group


async def _get_active_member(
    session: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GroupMember | None:
    result = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def _require_group_admin(
    session: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GroupMember:
    member = await _get_active_member(session, group_id, user_id)
    if not member or member.role not in ADMIN_ROLES:
        raise GroupError("Only group admins can manage this feature")
    return member


def _clean_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    cleaned: list[str] = []
    for tag in tags:
        normalized = tag.strip().lower()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized[:40])
    return cleaned[:8]


def _apply_template_defaults(template_key: str | None, payload: dict) -> dict:
    if not template_key:
        return payload
    template = DEFAULT_GROUP_TEMPLATES.get(template_key)
    if not template:
        raise GroupError("Unknown group template")
    merged = {**template, **{key: value for key, value in payload.items() if value not in (None, "", [])}}
    merged["template_key"] = template_key
    return merged


async def _group_counts(session: AsyncSession, group_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    counts = {group_id: {"member_count": 0, "message_count": 0, "event_count": 0} for group_id in group_ids}
    if not group_ids:
        return counts

    member_rows = await session.execute(
        select(GroupMember.group_id, func.count())
        .where(GroupMember.group_id.in_(group_ids), GroupMember.status == "active")
        .group_by(GroupMember.group_id)
    )
    for group_id, count in member_rows.all():
        counts[group_id]["member_count"] = count

    message_rows = await session.execute(
        select(GroupMessage.group_id, func.count())
        .where(GroupMessage.group_id.in_(group_ids))
        .group_by(GroupMessage.group_id)
    )
    for group_id, count in message_rows.all():
        counts[group_id]["message_count"] = count

    event_rows = await session.execute(
        select(GroupEvent.group_id, func.count())
        .where(GroupEvent.group_id.in_(group_ids))
        .group_by(GroupEvent.group_id)
    )
    for group_id, count in event_rows.all():
        counts[group_id]["event_count"] = count

    return counts


def _discovery_score(group: Group, counts: dict[str, int]) -> float:
    score = counts["member_count"] * 1.5 + counts["message_count"] * 0.4 + counts["event_count"] * 4
    if group.is_verified:
        score += 25
    if group.welcome_message:
        score += 5
    if group.tags:
        score += min(len(group.tags) * 2, 10)
    return round(score, 2)


def _serialize_group_list_item(
    group: Group,
    membership_map: dict[uuid.UUID, GroupMember],
    counts: dict[uuid.UUID, dict[str, int]],
) -> dict:
    group_counts = counts.get(group.id, {"member_count": 0, "message_count": 0, "event_count": 0})
    membership = membership_map.get(group.id)
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "type": group.type,
        "organization_name": group.organization_name,
        "category": group.category,
        "tags": group.tags or [],
        "is_discoverable": group.is_discoverable,
        "is_verified": group.is_verified,
        "verification_status": group.verification_status,
        "announcement_only": group.announcement_only,
        "template_key": group.template_key,
        "onboarding_steps": group.onboarding_steps or [],
        "welcome_message": group.welcome_message,
        "growth_goal": group.growth_goal,
        "created_by": group.created_by,
        "created_at": group.created_at,
        "is_member": bool(membership and membership.status == "active"),
        "membership_status": membership.status if membership else None,
        **group_counts,
        "discovery_score": _discovery_score(group, group_counts),
    }


async def is_group_member(
    session: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> bool:
    """Check if a user is an active member of a group."""
    member = await _get_active_member(session, group_id, user_id)
    return member is not None


async def create_group(
    session: AsyncSession,
    creator_id: uuid.UUID,
    name: str,
    description: str | None,
    group_type: str,
    organization_name: str | None,
    category: str | None = None,
    tags: list[str] | None = None,
    is_discoverable: bool = True,
    announcement_only: bool = False,
    template_key: str | None = None,
    onboarding_steps: list[dict] | None = None,
    welcome_message: str | None = None,
    growth_goal: int = 100,
) -> Group:
    payload = _apply_template_defaults(
        template_key,
        {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags,
            "onboarding_steps": onboarding_steps,
            "welcome_message": welcome_message,
            "growth_goal": growth_goal,
        },
    )
    name = payload["name"]
    description = payload.get("description")
    category = payload.get("category")
    tags = payload.get("tags")
    onboarding_steps = payload.get("onboarding_steps")
    welcome_message = payload.get("welcome_message")
    growth_goal = payload.get("growth_goal", growth_goal)
    template_key = payload.get("template_key")

    if group_type == "organization" and not organization_name:
        raise GroupError("Organization groups require organization_name")

    group = Group(
        name=name,
        description=description,
        type=group_type,
        organization_name=organization_name,
        category=category,
        tags=_clean_tags(tags),
        is_discoverable=is_discoverable,
        announcement_only=announcement_only,
        template_key=template_key,
        onboarding_steps=onboarding_steps or [],
        welcome_message=welcome_message,
        growth_goal=growth_goal,
        created_by=creator_id,
    )
    session.add(group)
    await session.flush()

    session.add(
        GroupMember(
            user_id=creator_id,
            group_id=group.id,
            role="admin",
            status="active",
            alias=_generate_alias() if group_type == "anonymous" else None,
        )
    )
    await session.commit()
    await session.refresh(group)
    return group


async def join_group(
    session: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> GroupMember:
    group = await _get_group(session, group_id)

    result = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()

    if membership and membership.status == "active":
        return membership

    if group.type == "private" and not membership:
        raise GroupError("Private groups require an invite")

    if membership:
        membership.status = "active"
        membership.alias = membership.alias or (
            _generate_alias() if group.type == "anonymous" else None
        )
    else:
        membership = GroupMember(
            user_id=user_id,
            group_id=group_id,
            role="member",
            status="active",
            alias=_generate_alias() if group.type == "anonymous" else None,
        )
        session.add(membership)

    await session.commit()
    await session.refresh(membership)
    return membership


async def leave_group(
    session: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> None:
    await session.execute(
        delete(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    await session.commit()


async def invite_user(
    session: AsyncSession,
    inviter_id: uuid.UUID,
    group_id: uuid.UUID,
    invited_user_id: uuid.UUID,
) -> GroupMember:
    if inviter_id == invited_user_id:
        raise GroupError("Cannot invite yourself")
    if not await user_exists(session, invited_user_id):
        raise GroupError("Invited user not found")
    if await are_blocked(session, inviter_id, invited_user_id):
        raise GroupError("Invite is not allowed")

    group = await _get_group(session, group_id)
    inviter = await _get_active_member(session, group_id, inviter_id)
    if not inviter:
        raise GroupError("Only group members can invite users")

    result = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == invited_user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        return membership

    membership = GroupMember(
        user_id=invited_user_id,
        group_id=group_id,
        role="member",
        status="invited" if group.type == "private" else "active",
        alias=_generate_alias() if group.type == "anonymous" else None,
        invited_by=inviter_id,
    )
    session.add(membership)
    await session.commit()
    await session.refresh(membership)
    # Best-effort notification to invited user
    try:
        await NotificationService.create_notification(
            session,
            user_id=str(invited_user_id),
            type="group_invite",
            text=f"You were invited to {group.name}",
            actor_id=str(inviter_id),
            data={"group_id": str(group.id)},
        )
    except Exception:
        pass
    return membership


async def list_members(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
) -> list[dict]:
    group = await _get_group(session, group_id)
    requester = await _get_active_member(session, group_id, requester_id)
    if not requester:
        raise GroupError("Only group members can list members")

    result = await session.execute(
        select(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.status == "active")
        .order_by(GroupMember.joined_at.asc())
    )
    members = result.scalars().all()
    if group.type == "anonymous":
        return [
            {
                "user_id": None,
                "group_id": member.group_id,
                "role": member.role,
                "status": member.status,
                "alias": member.alias,
                "joined_at": member.joined_at,
            }
            for member in members
        ]

    return [
        {
            "user_id": member.user_id,
            "group_id": member.group_id,
            "role": member.role,
            "status": member.status,
            "alias": member.alias,
            "joined_at": member.joined_at,
        }
        for member in members
    ]


async def list_groups(session: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    membership_result = await session.execute(
        select(GroupMember).where(GroupMember.user_id == user_id)
    )
    memberships = membership_result.scalars().all()
    membership_map = {member.group_id: member for member in memberships}

    result = await session.execute(
        select(Group).where(
            or_(
                and_(Group.is_discoverable == True, Group.type != "private"),
                Group.id.in_(list(membership_map.keys())),
            )
        )
    )
    groups = result.scalars().all()
    counts = await _group_counts(session, [group.id for group in groups])

    groups.sort(
        key=lambda group: (_discovery_score(group, counts[group.id]), group.created_at),
        reverse=True,
    )

    return [_serialize_group_list_item(group, membership_map, counts) for group in groups]


async def search_groups(
    session: AsyncSession,
    user_id: uuid.UUID,
    query_text: str,
    limit: int = 20,
) -> list[dict]:
    membership_result = await session.execute(
        select(GroupMember).where(GroupMember.user_id == user_id)
    )
    memberships = membership_result.scalars().all()
    membership_map = {member.group_id: member for member in memberships}

    stmt = select(Group).where(
        and_(
            or_(
                and_(Group.is_discoverable == True, Group.type != "private"),
                Group.id.in_(list(membership_map.keys())),
            ),
            or_(
                Group.name.ilike(f"%{query_text}%"),
                Group.description.ilike(f"%{query_text}%"),
                Group.organization_name.ilike(f"%{query_text}%"),
                Group.category.ilike(f"%{query_text}%"),
                cast(Group.tags, String).ilike(f"%{query_text}%"),
            ),
        )
    ).limit(limit)

    result = await session.execute(stmt)
    groups = result.scalars().all()
    counts = await _group_counts(session, [group.id for group in groups])

    groups.sort(
        key=lambda group: (_discovery_score(group, counts[group.id]), group.created_at),
        reverse=True,
    )

    return [_serialize_group_list_item(group, membership_map, counts) for group in groups]


async def send_group_message(
    session: AsyncSession,
    sender_id: uuid.UUID,
    group_id: uuid.UUID,
    content: str,
) -> GroupMessage:
    group = await _get_group(session, group_id)
    member = await _get_active_member(session, group_id, sender_id)
    if not member:
        raise GroupError("Only group members can send messages")
    if group.announcement_only and member.role not in ADMIN_ROLES:
        raise GroupError("Only group admins can post in announcement channels")

    await ModerationService.validate_user_can_send(session, str(sender_id))
    await ModerationService.validate_text_content(content)
    await ModerationService.enforce_message_rate_limit(session, str(sender_id))

    ai_result = await ModerationService.validate_content_with_ai(
        session,
        content_id=str(uuid.uuid4()),
        content_type="group_message",
        content_text=content,
    )
    if ai_result.get("should_auto_moderate"):
        await ModerationService.apply_ai_auto_moderation(
            session,
            str(sender_id),
            ai_result.get("content_id"),
            ai_analysis=ai_result,
        )
        raise GroupError("Group message blocked by AI moderation policy")

    message = GroupMessage(
        sender_id=sender_id,
        group_id=group_id,
        content=encrypt_value(content),
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def serialize_group_message(
    session: AsyncSession,
    message: GroupMessage,
) -> dict:
    group = await _get_group(session, message.group_id)
    sender_alias = None
    sender_id = message.sender_id
    if group.type == "anonymous":
        member = await _get_active_member(session, message.group_id, message.sender_id)
        sender_alias = member.alias if member else None
        sender_id = None

    return {
        "id": message.id,
        "sender_id": sender_id,
        "sender_alias": sender_alias,
        "group_id": message.group_id,
        "content": decrypt_value(message.content),
        "timestamp": message.timestamp,
    }


async def get_group_messages(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
    limit: int = 50,
) -> list[dict]:
    if not await _get_active_member(session, group_id, requester_id):
        raise GroupError("Only group members can read messages")

    result = await session.execute(
        select(GroupMessage)
        .where(GroupMessage.group_id == group_id)
        .order_by(GroupMessage.timestamp.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    filtered_messages = await ModerationService.filter_shadowbanned_messages(
        session,
        messages,
        str(requester_id),
        viewer_is_admin=False,
    )
    return [await serialize_group_message(session, message) for message in filtered_messages]


async def get_group_messages_since(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    if not await _get_active_member(session, group_id, requester_id):
        raise GroupError("Only group members can read messages")

    query = select(GroupMessage).where(GroupMessage.group_id == group_id)
    if since:
        query = query.where(GroupMessage.timestamp > since)
    query = query.order_by(GroupMessage.timestamp.asc()).limit(limit)
    result = await session.execute(query)
    messages = list(result.scalars().all())
    filtered_messages = await ModerationService.filter_shadowbanned_messages(
        session,
        messages,
        str(requester_id),
        viewer_is_admin=False,
    )
    return [await serialize_group_message(session, message) for message in filtered_messages]


def list_group_templates() -> list[dict]:
    return [{"key": key, **template} for key, template in DEFAULT_GROUP_TEMPLATES.items()]


async def update_group_settings(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
    **settings: object,
) -> Group:
    group = await _get_group(session, group_id)
    await _require_group_admin(session, group_id, requester_id)

    for field in (
        "category",
        "is_discoverable",
        "announcement_only",
        "onboarding_steps",
        "welcome_message",
        "growth_goal",
    ):
        if settings.get(field) is not None:
            setattr(group, field, settings[field])
    if settings.get("tags") is not None:
        group.tags = _clean_tags(settings["tags"])

    await session.commit()
    await session.refresh(group)
    return group


async def request_group_verification(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
) -> Group:
    group = await _get_group(session, group_id)
    await _require_group_admin(session, group_id, requester_id)
    group.verification_status = "pending"
    await session.commit()
    await session.refresh(group)
    return group


async def create_group_event(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
    title: str,
    description: str | None,
    starts_at: datetime,
    ends_at: datetime | None,
    location: str | None,
    is_online: bool,
) -> GroupEvent:
    await _get_group(session, group_id)
    await _require_group_admin(session, group_id, requester_id)
    event = GroupEvent(
        group_id=group_id,
        host_id=requester_id,
        title=title,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        location=location,
        is_online=is_online,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_group_events(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
) -> list[GroupEvent]:
    group = await _get_group(session, group_id)
    if group.type == "private" and not await _get_active_member(session, group_id, requester_id):
        raise GroupError("Only group members can view private group events")
    result = await session.execute(
        select(GroupEvent)
        .where(GroupEvent.group_id == group_id)
        .order_by(GroupEvent.starts_at.asc())
        .limit(100)
    )
    return list(result.scalars().all())


async def get_group_analytics(
    session: AsyncSession,
    requester_id: uuid.UUID,
    group_id: uuid.UUID,
) -> dict:
    group = await _get_group(session, group_id)
    await _require_group_admin(session, group_id, requester_id)
    counts = (await _group_counts(session, [group_id]))[group_id]

    invited_count_result = await session.execute(
        select(func.count()).select_from(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.status == "invited",
        )
    )
    invited_count = invited_count_result.scalar_one()
    days_active = max((datetime.utcnow().date() - group.created_at.date()).days + 1, 1)
    member_count = counts["member_count"]
    message_count = counts["message_count"]
    event_count = counts["event_count"]
    onboarding_steps = len(group.onboarding_steps or [])

    return {
        "group_id": group.id,
        "member_count": member_count,
        "invited_count": invited_count,
        "message_count": message_count,
        "event_count": event_count,
        "days_active": days_active,
        "growth_goal": group.growth_goal,
        "growth_percent": round(min((member_count / max(group.growth_goal, 1)) * 100, 100), 2),
        "discovery_score": _discovery_score(group, counts),
        "engagement_rate": round(message_count / max(member_count, 1), 2),
        "onboarding_completion_estimate": round(min((onboarding_steps / 2) * 100, 100), 2),
    }
