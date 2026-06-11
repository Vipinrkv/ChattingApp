from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.pagination import parse_cursor
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.post_schema import (
    PostCreate,
    PostUpdate,
    PostResponse,
    GroupPostCreate,
    GroupPostResponse,
)
from app.services.group_feed_service import GroupFeedService
from app.services.post_service import PostService
from app.services.feed_service import FeedService
from app.utils.privacy import PrivacyEngine

from app.services.post_like_service import PostLikeService
from app.services.post_comment_service import PostCommentService
from app.services.post_repost_service import PostRepostService


router = APIRouter(
    tags=["posts"],
    dependencies=[Depends(get_current_user_dep)],
)


class PostCommentCreate(BaseModel):
    content: str


def _invalid_feed_cursor(exc: Exception) -> BadRequestError:
    return BadRequestError(
        "Invalid cursor format; expected ISO8601 timestamp",
        code="feed_cursor_invalid",
    )


def _forbid_feed(message: str) -> ForbiddenError:
    return ForbiddenError(message, code="feed_forbidden")


@router.post("/create", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    post = await PostService.create_post(session, current_user.id, post_data)
    return post


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    post = await PostService.get_post(session, post_id)
    if not post or str(post.user_id) != str(current_user.id):
        raise ForbiddenError(
            "Cannot update post that does not belong to you",
            code="post_forbidden",
        )

    updated_post = await PostService.update_post(session, post_id, post_data)
    if not updated_post:
        raise NotFoundError("Post not found", code="post_not_found")
    return updated_post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    post = await PostService.get_post(session, post_id)
    if not post or str(post.user_id) != str(current_user.id):
        raise ForbiddenError(
            "Cannot delete post that does not belong to you",
            code="post_forbidden",
        )

    success = await PostService.delete_post(session, post_id)
    if not success:
        raise NotFoundError("Post not found", code="post_not_found")


@router.get("/search")
async def search_feed_posts(
    q: str = Query(min_length=1, max_length=100),
    cursor: str | None = Query(
        default=None,
        description="Optional ISO8601 timestamp cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    before = None
    if cursor:
        try:
            before = parse_cursor(cursor)
        except ValueError as exc:
            raise _invalid_feed_cursor(exc) from exc

    feed = await FeedService.search_feed(session, str(current_user.id), q, before, skip, limit)
    return {"feed": feed}


@router.get("/user/{user_id}")
async def get_user_posts(
    user_id: str,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    posts = await PostService.get_user_posts(session, user_id, skip, limit)
    visible_posts = [
        post
        for post in posts
        if await PrivacyEngine.can_view_post(session, str(current_user.id), post)
    ]
    return {"posts": visible_posts}


@router.get("/trends")
async def get_global_trends(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
):
    return await FeedService.get_global_trends(session, limit)


@router.get("/feed/{user_id}")
async def get_user_feed(
    user_id: str,
    cursor: str | None = Query(
        default=None,
        description="Optional base64 or ISO8601 cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot read another user's personalized feed")

    feed = await FeedService.get_feed(session, user_id, cursor, skip, limit)
    from app.core.pagination import encode_cursor
    next_cursor = encode_cursor(feed[-1].created_at, feed[-1].id) if len(feed) > 0 else None
    return {"feed": feed, "next_cursor": next_cursor}


@router.get("/trending/{user_id}")
async def get_user_trending_feed(
    user_id: str,
    cursor: str | None = Query(
        default=None,
        description="Optional base64 or ISO8601 cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot read another user's personalized trending feed")

    feed = await FeedService.get_trending_feed(session, user_id, cursor, skip, limit)
    from app.core.pagination import encode_cursor
    next_cursor = encode_cursor(feed[-1].created_at, feed[-1].id) if len(feed) > 0 else None
    return {"feed": feed, "next_cursor": next_cursor}


@router.get("/recommendations/{user_id}")
async def get_user_recommendations(
    user_id: str,
    cursor: str | None = Query(
        default=None,
        description="Optional base64 or ISO8601 cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot read another user's recommendations")

    feed = await FeedService.get_recommendations(session, user_id, cursor, skip, limit)
    from app.core.pagination import encode_cursor
    next_cursor = encode_cursor(feed[-1].created_at, feed[-1].id) if len(feed) > 0 else None
    return {"feed": feed, "next_cursor": next_cursor}


@router.get("/explore/{user_id}")
async def get_user_explore_feed(
    user_id: str,
    cursor: str | None = Query(
        default=None,
        description="Optional base64 or ISO8601 cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot read another user's explore feed")

    feed = await FeedService.get_explore_feed(session, user_id, cursor, skip, limit)
    from app.core.pagination import encode_cursor
    next_cursor = encode_cursor(feed[-1].created_at, feed[-1].id) if len(feed) > 0 else None
    return {"feed": feed, "next_cursor": next_cursor}


@router.get("/analytics/{user_id}")
async def get_user_feed_analytics(
    user_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot read another user's feed analytics")

    analytics = await FeedService.get_feed_analytics(session, user_id)
    return analytics


@router.get("/hashtag/{tag}")
async def get_posts_by_hashtag(
    tag: str,
    user_id: str = Query(..., description="Current user ID"),
    cursor: str | None = Query(
        default=None,
        description="Optional base64 or ISO8601 cursor for pagination",
    ),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    if str(current_user.id) != str(user_id):
        raise _forbid_feed("Cannot query hashtags for another user")

    feed = await FeedService.get_posts_by_hashtag(session, tag, user_id, cursor, skip, limit)
    from app.core.pagination import encode_cursor
    next_cursor = encode_cursor(feed[-1].created_at, feed[-1].id) if len(feed) > 0 else None
    return {"feed": feed, "next_cursor": next_cursor}


@router.post("/group/{group_id}/create", response_model=GroupPostResponse, status_code=status.HTTP_201_CREATED)
async def create_group_post(
    group_id: str,
    post_data: GroupPostCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    post = await GroupFeedService.create_group_post(
        session, group_id, current_user.id, post_data.content
    )
    return post


@router.get("/group/{group_id}/feed")
async def get_group_feed(
    group_id: str,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        feed = await GroupFeedService.get_group_feed(
            session, group_id, str(current_user.id), skip, limit
        )
    except PermissionError as exc:
        raise ForbiddenError(str(exc), code="group_feed_forbidden") from exc

    return {"feed": feed}


@router.delete("/group/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    success = await GroupFeedService.delete_group_post(session, post_id)
    if not success:
        raise NotFoundError("Post not found", code="post_not_found")


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    post = await PostService.get_post(session, post_id)
    if not post:
        raise NotFoundError("Post not found", code="post_not_found")

    if not await PrivacyEngine.can_view_post(session, str(current_user.id), post):
        raise ForbiddenError("Post is not visible to you", code="post_forbidden")

    return post


# Like endpoints
@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        payload = await PostLikeService.toggle_like(session, post_id, current_user.id)
        return payload
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_like_invalid") from exc


@router.delete("/{post_id}/like")
async def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        payload = await PostLikeService.toggle_like(session, post_id, current_user.id)
        if payload.get("liked") is True:
            payload = await PostLikeService.toggle_like(session, post_id, current_user.id)
        return payload
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_like_invalid") from exc


@router.get("/{post_id}/likes")
async def get_post_likes(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        likes = await PostLikeService.get_like_count(session, post_id)
        liked = await PostLikeService.get_user_like_state(session, post_id, current_user.id)
        return {"post_id": str(post_id), "likes": likes, "liked": liked}
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_like_invalid") from exc


# Comment endpoints
@router.post("/{post_id}/comments")
async def create_comment(
    post_id: str,
    payload: PostCommentCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        comment = await PostCommentService.create_comment(
            session=session,
            post_id=post_id,
            user_id=current_user.id,
            content=payload.content,
        )
        return {
            "id": str(comment.id),
            "post_id": str(comment.post_id),
            "user_id": str(comment.user_id),
            "content": comment.content,
            "created_at": comment.created_at,
        }
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_comment_invalid") from exc


@router.get("/{post_id}/comments")
async def list_comments(
    post_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        comments = await PostCommentService.list_comments(session, post_id, limit)
        return [
            {
                "id": str(c.id),
                "post_id": str(c.post_id),
                "user_id": str(c.user_id),
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in comments
        ]
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_comment_invalid") from exc


# Repost endpoints
@router.get("/{post_id}/reposts")
async def get_post_reposts(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        reposts = await PostRepostService.get_repost_count(session, post_id)
        reposted = await PostRepostService.get_user_repost_state(session, post_id, current_user.id)
        return {"post_id": str(post_id), "reposts": reposts, "reposted": reposted}
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_repost_invalid") from exc


@router.post("/{post_id}/repost")
async def repost_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        payload = await PostRepostService.toggle_repost(session, post_id, current_user.id)
        return payload
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_repost_invalid") from exc


@router.delete("/{post_id}/repost")
async def unrepost_post(
    post_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        payload = await PostRepostService.toggle_repost(session, post_id, current_user.id)
        if payload.get("reposted") is True:
            payload = await PostRepostService.toggle_repost(session, post_id, current_user.id)
        return payload
    except Exception as exc:
        raise BadRequestError(str(exc), code="post_repost_invalid") from exc
