"""Tests for advanced group features."""
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.group_service import (
    create_group,
    search_groups,
    create_group_event,
    request_group_verification,
    GroupError,
)


async def create_test_user(session: AsyncSession, user_id):
    user = User(
        id=user_id,
        firebase_uid=f"test-{user_id}",
        username=f"user_{user_id.hex[:12]}",
        email=f"user_{user_id.hex[:12]}@example.test",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_create_discoverable_group_with_template(session: AsyncSession):
    creator_id = uuid4()
    await create_test_user(session, creator_id)
    group = await create_group(
        session,
        creator_id,
        name='Study Circle',
        description='A useful cohort',
        group_type='public',
        organization_name=None,
        category='Education',
        tags=['study', 'resources'],
        is_discoverable=True,
        announcement_only=False,
        template_key='study-circle',
        onboarding_steps=None,
        welcome_message=None,
        growth_goal=50,
    )

    assert group.is_discoverable is True
    assert group.template_key == 'study-circle'
    assert group.category == 'Education'
    assert set(group.tags) >= {'study', 'resources'}
    assert group.growth_goal == 50


@pytest.mark.asyncio
async def test_search_groups_returns_ranked_results(session: AsyncSession):
    creator_id = uuid4()
    await create_test_user(session, creator_id)
    await create_group(
        session,
        creator_id,
        name='Local Events Hub',
        description='Community events',
        group_type='public',
        organization_name=None,
        category='Events',
        tags=['events', 'meetups'],
        is_discoverable=True,
        announcement_only=False,
        template_key='local-events',
        onboarding_steps=None,
        welcome_message=None,
        growth_goal=120,
    )
    results = await search_groups(session, creator_id, 'events', limit=10)
    assert len(results) >= 1
    assert any(
        (group.get('category') and 'events' in str(group.get('category')).lower())
        or ('events' in [t.lower() for t in group.get('tags', [])])
        for group in results
    )


@pytest.mark.asyncio
async def test_group_event_scheduling_requires_admin(session: AsyncSession):
    creator_id = uuid4()
    await create_test_user(session, creator_id)
    group = await create_group(
        session,
        creator_id,
        name='Announcements Test',
        description='Testing event scheduling',
        group_type='public',
        organization_name=None,
        category='Community',
        tags=['announcements'],
        is_discoverable=True,
        announcement_only=False,
        template_key=None,
        onboarding_steps=None,
        welcome_message=None,
        growth_goal=100,
    )

    with pytest.raises(GroupError):
        await create_group_event(
            session,
            uuid4(),
            group.id,
            title='Community meeting',
            description='A test event',
            starts_at=datetime.utcnow(),
            ends_at=None,
            location='Online',
            is_online=True,
        )


@pytest.mark.asyncio
async def test_group_verification_request_updates_status(session: AsyncSession):
    creator_id = uuid4()
    await create_test_user(session, creator_id)
    group = await create_group(
        session,
        creator_id,
        name='Verified Community',
        description='Request verification',
        group_type='public',
        organization_name=None,
        category='Community',
        tags=['verified'],
        is_discoverable=True,
        announcement_only=False,
        template_key=None,
        onboarding_steps=None,
        welcome_message=None,
        growth_goal=200,
    )

    updated_group = await request_group_verification(session, creator_id, group.id)
    assert updated_group.verification_status == 'pending'
