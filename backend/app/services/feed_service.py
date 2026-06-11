from datetime import datetime
import re
import uuid
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_, and_, func
from sqlalchemy.orm import selectinload
from app.core.pagination import apply_tuple_cursor_filter, decode_cursor, encode_cursor
from app.core.redis_cache import redis_cache
from app.core.config import settings
from app.models.post import Post, PostVisibility
from app.models.friend import FriendRequest, FriendRequestStatus
from app.models.follower import Follower
from app.models.block import Block
from app.models.post_like import PostLike
from app.models.post_repost import PostRepost
from app.models.post_comment import PostComment
from app.services.user_feed_control_service import UserFeedControlService

import logging

logger = logging.getLogger(__name__)


class FeedService:
    @staticmethod
    async def _load_relationships(session: AsyncSession, user_id: str) -> dict[str, list[str]]:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cache_key = f"user:relations:{user_uuid}"
        if redis_cache.enabled:
            cached = await redis_cache.get_json(cache_key)
            if cached:
                return cached

        friends_result = await session.execute(
            select(FriendRequest.requester_id, FriendRequest.addressee_id)
            .where(FriendRequest.status == FriendRequestStatus.ACCEPTED)
            .where(
                or_(
                    FriendRequest.requester_id == user_uuid,
                    FriendRequest.addressee_id == user_uuid,
                )
            )
        )
        friends = [
            str(friend_id)
            for pair in friends_result.all()
            for friend_id in pair
            if friend_id != user_uuid
        ]

        following_result = await session.execute(
            select(Follower.following_id).where(Follower.follower_id == user_uuid)
        )
        following = [str(item) for item in following_result.scalars().all()]

        blocked_result = await session.execute(
            select(Block.blocked_user_id).where(Block.blocker_id == user_uuid)
        )
        blocked = [str(item) for item in blocked_result.scalars().all()]

        payload = {
            "friends": friends,
            "following": following,
            "blocked": blocked,
        }
        if redis_cache.enabled:
            await redis_cache.set_json(cache_key, payload, ex=settings.CACHE_TTL_SECONDS)

        return payload

    @staticmethod
    def _visible_post_filter(user_id: str, friends: list[str], following: list[str], blocked: list[str]):
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        friends_uuids = [uuid.UUID(f) if isinstance(f, str) else f for f in friends]
        following_uuids = [uuid.UUID(f) if isinstance(f, str) else f for f in following]
        blocked_uuids = [uuid.UUID(b) if isinstance(b, str) else b for b in blocked]

        return and_(
            or_(
                Post.user_id == user_uuid,
                and_(
                    Post.user_id.in_(friends_uuids),
                    Post.visibility.in_([PostVisibility.FRIENDS, PostVisibility.PUBLIC]),
                ),
                and_(
                    Post.user_id.in_(following_uuids),
                    Post.visibility.in_([PostVisibility.FOLLOWERS, PostVisibility.PUBLIC]),
                ),
                Post.visibility == PostVisibility.PUBLIC,
            ),
            ~Post.user_id.in_(blocked_uuids),
        )

    @staticmethod
    def extract_hashtags(content: str) -> list[str]:
        return [tag.lower() for tag in re.findall(r"#([a-z0-9_]+)", content or "", re.IGNORECASE)]

    @staticmethod
    async def _build_interest_profile(session: AsyncSession, user_id: str) -> dict[str, float]:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        return_values = {}
        topic_counter = Counter()

        recent_own_posts = await session.execute(
            select(Post).where(Post.user_id == user_uuid).order_by(desc(Post.created_at)).limit(50)
        )
        for post in recent_own_posts.scalars().all():
            topic_counter.update(FeedService.extract_hashtags(post.content))

        liked_posts = await session.execute(
            select(Post)
            .join(PostLike, PostLike.post_id == Post.id)
            .where(PostLike.user_id == user_uuid)
            .order_by(desc(Post.created_at))
            .limit(50)
        )
        for post in liked_posts.scalars().all():
            topic_counter.update(FeedService.extract_hashtags(post.content))

        for tag, count in topic_counter.items():
            return_values[tag] = min(1.0 + count * 0.5, 6.0)

        return return_values

    @staticmethod
    def _score_post(
        post: Post,
        likes: int = 0,
        reposts: int = 0,
        comments: int = 0,
        interest_weights: dict[str, float] | None = None,
    ) -> float:
        age_hours = max((datetime.utcnow() - post.created_at).total_seconds() / 3600.0, 0.0)
        recency_factor = max(0.15, 1.0 - min(age_hours / 168.0, 0.85))
        engagement_score = likes * 1.2 + reposts * 1.5 + comments * 1.0
        topic_boost = 0.0

        if interest_weights:
            for tag in FeedService.extract_hashtags(post.content):
                topic_boost += interest_weights.get(tag, 0.0)

        topic_factor = 1.0 + min(topic_boost / 4.0, 1.0)
        return engagement_score * recency_factor * topic_factor + max(0.01, 1.0 / (1.0 + age_hours))

    @staticmethod
    def _apply_feed_controls_filter(query, control):
        # 1. Filter muted words
        if control.muted_words:
            for word in control.muted_words:
                normalized = word.strip().lower()
                if normalized:
                    query = query.where(~Post.content.ilike(f"%{normalized}%"))

        # 2. Filter sensitive content if hidden
        if control.sensitive_content_hidden:
            sensitive_tags = ["#nsfw", "#sensitive", "#18+", "#adult", "#nudity"]
            for tag in sensitive_tags:
                query = query.where(~Post.content.ilike(f"%{tag}%"))

        return query

    @staticmethod
    async def get_feed(
        session: AsyncSession,
        user_id: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        """Get user's personalized feed with controls and durable cursor pagination"""
        relations = await FeedService._load_relationships(session, user_id)
        friends = relations["friends"]
        following = relations["following"]
        blocked = relations["blocked"]

        # Fetch Feed Settings
        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))

        query = (
            select(
                Post,
                func.count(PostLike.id).label("like_count"),
                func.count(PostRepost.id).label("repost_count"),
                func.count(PostComment.id).label("comment_count"),
            )
            .options(selectinload(Post.quoted_post))
            .outerjoin(PostLike, PostLike.post_id == Post.id)
            .outerjoin(PostRepost, PostRepost.post_id == Post.id)
            .outerjoin(PostComment, PostComment.post_id == Post.id)
            .where(FeedService._visible_post_filter(user_id, friends, following, blocked))
            .group_by(Post.id)
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)

        if control.ranking_mode == "chronological":
            query = query.order_by(desc(Post.created_at), desc(Post.id))
            if skip:
                query = query.offset(skip)
            query = query.limit(limit)
            result = await session.execute(query)
            return [row[0] for row in result.all()]

        # Engagement ranking mode (hybrid database/in-memory ranking)
        interest_weights = await FeedService._build_interest_profile(session, user_id)
        query = query.order_by(desc(Post.created_at), desc(Post.id))
        query = query.limit(limit * 2)
        if skip:
            query = query.offset(skip)

        result = await session.execute(query)
        rows = result.all()
        scored = sorted(
            rows,
            key=lambda row: FeedService._score_post(
                row[0],
                likes=row.like_count or 0,
                reposts=row.repost_count or 0,
                comments=row.comment_count or 0,
                interest_weights=interest_weights,
            ),
            reverse=True,
        )
        return [row[0] for row in scored][:limit]

    @staticmethod
    async def search_feed(
        session: AsyncSession,
        user_id: str,
        search_term: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        friends = relations["friends"]
        following = relations["following"]
        blocked = relations["blocked"]

        # Load controls
        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))

        query = (
            select(Post)
            .options(selectinload(Post.quoted_post))
            .where(
                and_(
                    FeedService._visible_post_filter(user_id, friends, following, blocked),
                    Post.content.ilike(f"%{search_term}%"),
                )
            )
            .order_by(desc(Post.created_at), desc(Post.id))
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)
        if skip:
            query = query.offset(skip)
        query = query.limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_trending_feed(
        session: AsyncSession,
        user_id: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        friends = relations["friends"]
        following = relations["following"]
        blocked = relations["blocked"]

        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))

        like_count = func.count(PostLike.id)
        repost_count = func.count(PostRepost.id)
        comment_count = func.count(PostComment.id)
        score = like_count + repost_count + comment_count

        query = (
            select(Post)
            .options(selectinload(Post.quoted_post))
            .outerjoin(PostLike, PostLike.post_id == Post.id)
            .outerjoin(PostRepost, PostRepost.post_id == Post.id)
            .outerjoin(PostComment, PostComment.post_id == Post.id)
            .where(FeedService._visible_post_filter(user_id, friends, following, blocked))
            .group_by(Post.id)
            .order_by(desc(score), desc(Post.created_at), desc(Post.id))
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)
        if skip:
            query = query.offset(skip)
        query = query.limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_recommendations(
        session: AsyncSession,
        user_id: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        blocked = relations["blocked"]
        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))
        interest_weights = await FeedService._build_interest_profile(session, user_id)

        query = (
            select(
                Post,
                func.count(PostLike.id).label("like_count"),
                func.count(PostRepost.id).label("repost_count"),
                func.count(PostComment.id).label("comment_count"),
            )
            .options(selectinload(Post.quoted_post))
            .outerjoin(PostLike, PostLike.post_id == Post.id)
            .outerjoin(PostRepost, PostRepost.post_id == Post.id)
            .outerjoin(PostComment, PostComment.post_id == Post.id)
            .where(
                and_(
                    Post.visibility == PostVisibility.PUBLIC,
                    ~Post.user_id.in_(blocked),
                    Post.user_id != user_id,
                )
            )
            .group_by(Post.id)
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)
        query = query.order_by(desc(Post.created_at), desc(Post.id))

        if skip:
            query = query.offset(skip)
        query = query.limit(limit * 2)

        rows = (await session.execute(query)).all()
        scored = sorted(
            rows,
            key=lambda row: FeedService._score_post(
                row[0],
                likes=row.like_count or 0,
                reposts=row.repost_count or 0,
                comments=row.comment_count or 0,
                interest_weights=interest_weights,
            ),
            reverse=True,
        )
        return [row[0] for row in scored][:limit]

    @staticmethod
    async def get_explore_feed(
        session: AsyncSession,
        user_id: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        blocked = relations["blocked"]
        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))
        interest_weights = await FeedService._build_interest_profile(session, user_id)

        query = (
            select(
                Post,
                func.count(PostLike.id).label("like_count"),
                func.count(PostRepost.id).label("repost_count"),
                func.count(PostComment.id).label("comment_count"),
            )
            .options(selectinload(Post.quoted_post))
            .outerjoin(PostLike, PostLike.post_id == Post.id)
            .outerjoin(PostRepost, PostRepost.post_id == Post.id)
            .outerjoin(PostComment, PostComment.post_id == Post.id)
            .where(
                and_(
                    Post.visibility == PostVisibility.PUBLIC,
                    ~Post.user_id.in_(blocked),
                    Post.user_id != user_id,
                )
            )
            .group_by(Post.id)
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)
        query = query.order_by(desc(Post.created_at), desc(Post.id))

        if skip:
            query = query.offset(skip)
        query = query.limit(limit * 3)

        rows = (await session.execute(query)).all()
        scored = sorted(
            rows,
            key=lambda row: FeedService._score_post(
                row[0],
                likes=row.like_count or 0,
                reposts=row.repost_count or 0,
                comments=row.comment_count or 0,
                interest_weights=interest_weights,
            ) + (0.2 * len(FeedService.extract_hashtags(row[0].content))),
            reverse=True,
        )
        return [row[0] for row in scored][:limit]

    @staticmethod
    async def get_feed_analytics(
        session: AsyncSession,
        user_id: str,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        blocked = relations["blocked"]

        feed_posts = (
            await session.execute(
                select(Post).where(FeedService._visible_post_filter(user_id, relations["friends"], relations["following"], blocked))
            )
        ).scalars().all()

        hashtag_counts: dict[str, int] = {}
        for post in feed_posts:
            for tag in FeedService.extract_hashtags(post.content):
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1

        top_hashtags = sorted(hashtag_counts.items(), key=lambda item: item[1], reverse=True)[:8]
        total_feed_posts = len(feed_posts)
        total_user_posts = await session.scalar(
            select(func.count(Post.id)).where(Post.user_id == user_id)
        )

        return {
            "feed_post_count": total_feed_posts,
            "user_post_count": total_user_posts or 0,
            "top_hashtags": [tag for tag, _ in top_hashtags],
            "interest_graph": {tag: count for tag, count in top_hashtags},
        }

    @staticmethod
    async def get_posts_by_hashtag(
        session: AsyncSession,
        tag: str,
        user_id: str,
        cursor: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        relations = await FeedService._load_relationships(session, user_id)
        friends = relations["friends"]
        following = relations["following"]
        blocked = relations["blocked"]

        control = await UserFeedControlService.get_controls(session, uuid.UUID(user_id))

        query = (
            select(Post)
            .options(selectinload(Post.quoted_post))
            .where(
                and_(
                    FeedService._visible_post_filter(user_id, friends, following, blocked),
                    Post.content.ilike(f"%#{tag.lower()}%"),
                )
            )
            .order_by(desc(Post.created_at), desc(Post.id))
        )

        query = FeedService._apply_feed_controls_filter(query, control)
        query = apply_tuple_cursor_filter(query, Post.created_at, Post.id, cursor)
        if skip:
            query = query.offset(skip)
        query = query.limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_global_trends(session: AsyncSession, limit: int = 10) -> list[dict]:
        """Improved Trends System: dynamically aggregate top hashtags from public posts in the last 24 hours."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(Post.content).where(
            Post.visibility == PostVisibility.PUBLIC,
            Post.created_at >= cutoff
        )
        res = await session.execute(stmt)
        contents = res.scalars().all()

        hashtag_counts = Counter()
        for content in contents:
            hashtag_counts.update(FeedService.extract_hashtags(content))

        top_trends = hashtag_counts.most_common(limit)
        return [{"hashtag": tag, "count": count} for tag, count in top_trends]
