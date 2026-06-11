# Database Report

This report documents the schema audit, indexing strategy, and database performance optimizations implemented for the ChattingApp platform.

---

## 1. Relational Schema Summary

The database uses PostgreSQL as its primary transactional database. The schema is organized into logical functional areas:

- **Identity & Sessions**: `User`, `Session`, `LoginHistory`, `MFA`, `DeviceSync`
- **Social Graph**: `Follower`, `FriendRequest`
- **Content Feed**: `Post`, `PostLike`, `PostRepost`, `PostComment`, `UserFeedControl`, `UserList`
- **Real-time Messaging**: `Message`, `MessageBookmark`, `MessageTranslation`, `ScheduledMessage`, `VoiceTranscription`
- **Group Communication**: `Group`, `GroupMember`, `GroupMessage`, `GroupPost`, `GroupEvent`
- **Moderation & Auditing**: `Report`, `ReportEvidence`, `ModerationAction`, `FeedEventChain`

---

## 2. Alembic Migration Strategy

- **Single-Head Constraint**: All migrations are sequenced strictly under a single timeline. The current head is `0013_feed_polish_and_social_features`.
- **Validation**: Every database modification is backed by a corresponding Alembic migration file, preventing structural drift between environment branches.

---

## 3. Database Optimizations & Indexing

To support sub-second query latency under high load, the following optimizations are applied:

### A. Critical Indexes
- **Feed Queries**: Compound index on `(user_id, created_at DESC)` for the `posts` table.
- **Messaging Queries**: Compound index on `(sender_id, receiver_id, created_at DESC)` for the `messages` table.
- **Social Queries**: Unique index on `(follower_id, following_id)` for the `followers` table.
- **Muting & Filters**: Index on `(user_id)` for `user_feed_controls`.

### B. Stable Query Execution
- Avoided `N+1` query bugs by using SQLAlchemy `selectinload` and `joinedload` on relationships (e.g., loading post authors and quoted posts in `FeedService.get_feed`).
- Paginated feed queries using cursor-based pagination (`apply_tuple_cursor_filter`), avoiding performance degradation associated with large offset queries.

---

## 4. Integrity and Event-Chaining

- **Referential Integrity**: Cascading deletes are explicitly declared on foreign key definitions (e.g., deleting a post cascades deletes to its likes, comments, and reposts).
- **Tamper-Evident Event Logging**: Moderation events are serialized into the `feed_event_chains` table. Each record contains a SHA-256 hash calculated from its own content combined with the hash of the preceding record, ensuring event chain integrity.
