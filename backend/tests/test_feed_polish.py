import asyncio
from datetime import datetime, timedelta
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.post import Post, PostVisibility
from app.services.feed_service import FeedService
from app.services.feed_event_chain_service import FeedEventChainService
from app.services.user_feed_control_service import UserFeedControlService
from app.services.user_list_service import UserListService
from app.core.pagination import encode_cursor


async def create_test_user(session: AsyncSession, user_id):
    user = User(
        id=user_id,
        firebase_uid=f"test-{user_id.hex}",
        username=f"user_{user_id.hex[:12]}",
        email=f"user_{user_id.hex[:12]}@example.test",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_feed_event_chain_hashing(session: AsyncSession):
    user_id = uuid.uuid4()
    await create_test_user(session, user_id)

    # Log two events
    event1 = await FeedEventChainService.log_event(
        session,
        event_type="post_created",
        event_id=uuid.uuid4(),
        user_id=user_id,
        payload={"text": "hello"},
    )
    
    event2 = await FeedEventChainService.log_event(
        session,
        event_type="post_liked",
        event_id=uuid.uuid4(),
        user_id=user_id,
        payload={"like": True},
    )

    # The second event must have the hash of the first event as previous_hash
    assert event2.previous_hash == event1.hash

    # Verify the entire chain
    is_valid = await FeedEventChainService.verify_chain(session)
    assert is_valid is True


@pytest.mark.asyncio
async def test_durable_cursor_pagination(session: AsyncSession):
    user_id = uuid.uuid4()
    await create_test_user(session, user_id)

    # Create posts with slightly different creation times
    base_time = datetime.utcnow() - timedelta(days=1)
    posts = []
    for i in range(5):
        post = Post(
            id=uuid.uuid4(),
            user_id=user_id,
            content=f"Post number {i}",
            visibility=PostVisibility.PUBLIC,
            created_at=base_time + timedelta(minutes=i),
        )
        session.add(post)
        posts.append(post)
    await session.commit()

    # Get page 1 (limit 2)
    feed_page1 = await FeedService.get_feed(session, str(user_id), limit=2)
    assert len(feed_page1) == 2
    # Since they are ordered by desc(created_at), feed_page1 should have posts 4 and 3
    assert feed_page1[0].content == "Post number 4"
    assert feed_page1[1].content == "Post number 3"

    # Advance using cursor
    cursor = encode_cursor(feed_page1[-1].created_at, feed_page1[-1].id)
    feed_page2 = await FeedService.get_feed(session, str(user_id), cursor=cursor, limit=2)
    assert len(feed_page2) == 2
    assert feed_page2[0].content == "Post number 2"
    assert feed_page2[1].content == "Post number 1"


@pytest.mark.asyncio
async def test_user_feed_controls_muting(session: AsyncSession):
    user_id = uuid.uuid4()
    await create_test_user(session, user_id)

    # Add posts with muted and non-muted words
    post1 = Post(
        id=uuid.uuid4(),
        user_id=user_id,
        content="This is a lovely day with cats #happy",
        visibility=PostVisibility.PUBLIC,
        created_at=datetime.utcnow(),
    )
    post2 = Post(
        id=uuid.uuid4(),
        user_id=user_id,
        content="This is a post about spam stuff #spam",
        visibility=PostVisibility.PUBLIC,
        created_at=datetime.utcnow() - timedelta(minutes=1),
    )
    session.add(post1)
    session.add(post2)
    await session.commit()

    # Verify initially both are visible
    feed = await FeedService.get_feed(session, str(user_id))
    feed_ids = [p.id for p in feed]
    assert post1.id in feed_ids
    assert post2.id in feed_ids

    # Update feed controls to mute 'spam'
    from app.schemas.user_feed_control_schema import UserFeedControlUpdate
    await UserFeedControlService.update_controls(
        session,
        user_id,
        UserFeedControlUpdate(
            muted_words=["spam"],
            sensitive_content_hidden=False,
        ),
    )

    # Get feed again and confirm spam post is filtered out
    filtered_feed = await FeedService.get_feed(session, str(user_id))
    filtered_ids = [p.id for p in filtered_feed]
    assert post1.id in filtered_ids
    assert post2.id not in filtered_ids


@pytest.mark.asyncio
async def test_user_lists_management(session: AsyncSession):
    user_id = uuid.uuid4()
    member_id = uuid.uuid4()
    await create_test_user(session, user_id)
    await create_test_user(session, member_id)

    # Create list
    user_list = await UserListService.create_list(
        session,
        owner_id=user_id,
        name="Close Friends",
        description="A list of my closest peers",
    )
    assert user_list.name == "Close Friends"

    # Add member to list
    member = await UserListService.add_to_list(session, user_id, user_list.id, member_id)
    assert member is not None

    # Retrieve lists for user
    lists = await UserListService.get_lists(session, user_id)
    assert len(lists) == 1
    assert lists[0].name == "Close Friends"

    # Create post by list member
    post = Post(
        id=uuid.uuid4(),
        user_id=member_id,
        content="Exclusive content for lists",
        visibility=PostVisibility.PUBLIC,
        created_at=datetime.utcnow(),
    )
    session.add(post)
    await session.commit()

    # Get posts from this custom list
    list_posts = await UserListService.get_list_posts(session, user_id, user_list.id)
    assert len(list_posts) == 1
    assert list_posts[0].content == "Exclusive content for lists"

    # Remove from list
    removed = await UserListService.remove_from_list(session, user_id, user_list.id, member_id)
    assert removed is True

    # Delete list
    deleted = await UserListService.delete_list(session, user_id, user_list.id)
    assert deleted is True
