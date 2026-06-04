# Database And Backend Details

This file is the database/backend map for ChattingApp. It lists the database technology, tables, important columns, relationships, API files, service files, techniques, and where each piece is used.

## Backend Stack

| Area                               | Tool / Technique                                               | Main Files                                                                                                                                  |
| ---------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| API server                         | FastAPI ASGI app                                               | `backend/app/main.py`                                                                                                                       |
| Runtime server                     | Uvicorn                                                        | `backend/requirements.txt`, root `package.json` scripts                                                                                     |
| Database                           | PostgreSQL                                                     | `backend/app/core/config.py`, `backend/app/database/connection.py`                                                                          |
| DB driver                          | `asyncpg` through SQLAlchemy async engine                      | `backend/requirements.txt`, `backend/app/database/connection.py`                                                                            |
| ORM                                | SQLAlchemy 2.x async models and sessions                       | `backend/app/models/*`, `backend/app/database/connection.py`                                                                                |
| Migrations                         | Alembic                                                        | `backend/alembic.ini`, `backend/alembic/versions/0001_initial_schema.py`, `backend/alembic/versions/0006_add_message_archive_partitions.py` |
| Request/response validation        | Pydantic schemas                                               | `backend/app/schemas/*`                                                                                                                     |
| Auth provider                      | Firebase Admin SDK verifying Firebase ID tokens                | `backend/app/core/firebase.py`, `backend/app/core/auth.py`                                                                                  |
| Client auth transport              | `Authorization: Bearer <Firebase ID token>`                    | `frontend/src/lib/api.ts`, `backend/app/core/firebase.py`                                                                                   |
| Real time                          | FastAPI WebSocket endpoints                                    | `backend/app/websocket/chat_socket.py`, `backend/app/websocket/group_socket.py`                                                             |
| Cross-instance realtime fanout     | Optional Redis pub/sub                                         | `backend/app/websocket/redis_broker.py`                                                                                                     |
| Distributed lock coordination      | Redis-based lock helper for migration and backup orchestration | `backend/app/core/redis_lock.py`, `backend/tools/db_backup_and_migrate.py`                                                                  |
| Message encryption                 | Fernet encryption derived from `AES_KEY`                       | `backend/app/core/security.py`, `backend/app/services/chat_service.py`                                                                      |
| Media uploads                      | Multipart upload to backend local `uploads` folder             | `backend/app/services/media_service.py`, `backend/app/main.py`                                                                              |
| Static media serving               | FastAPI `StaticFiles` mounted at `/uploads`                    | `backend/app/main.py`                                                                                                                       |
| CORS / trusted host hardening      | FastAPI middleware                                             | `backend/app/main.py`, `backend/app/core/config.py`                                                                                         |
| Standard response/error formatting | Custom middleware and handlers                                 | `backend/app/core/middleware.py`, `backend/app/core/response.py`, `backend/app/core/errors.py`                                              |

## Database Connection

| Item                            | Detail                                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------ |
| Config source                   | `Settings.DATABASE_URL` in `backend/app/core/config.py`                                         |
| Default URL                     | `postgresql+asyncpg://user:password@localhost:5432/chat_platform`                               |
| Engine                          | `create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=20, max_overflow=0)`  |
| Session maker                   | `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`                       |
| Dependency                      | `get_db_session = get_db` yields one async session per request                                  |
| Startup behavior                | `init_db()` validates connectivity with `SELECT 1`; tables are not auto-created                 |
| Read replica support            | `READ_REPLICA_DATABASE_URL` can be configured for read-only session traffic via `get_read_db()` |
| Multi-region / failover support | `DB_FAILOVER_URL` and `DB_REGION` enable failover validation and deployment metadata            |
| Schema creation                 | Alembic migration `0001_initial_schema.py`                                                      |
| SSL mode                        | `DB_SSL_MODE=require                                                                            | verify-full | verify-ca`sets SQLAlchemy`connect_args["ssl"]` for secure Postgres connections |

Important files:

- `backend/app/core/config.py`: environment settings and validation.
- `backend/app/database/connection.py`: SQLAlchemy engine, session factory, model imports, DB dependency.
- `backend/alembic/versions/0001_initial_schema.py`: initial table creation.
- `backend/app/main.py`: calls `init_db()` during FastAPI lifespan startup.

## Tables

### `users`

Model: `backend/app/models/user.py`
Migration: `backend/alembic/versions/0001_initial_schema.py`

| Column         | Type / Rule                                             | Purpose                                             |
| -------------- | ------------------------------------------------------- | --------------------------------------------------- |
| `id`           | UUID primary key                                        | Internal user ID used by every backend relationship |
| `firebase_uid` | string, unique, indexed, required                       | Connects Firebase auth user to backend user         |
| `phone`        | string, unique, nullable, indexed                       | Optional phone identity/profile data                |
| `username`     | string, unique, indexed, required                       | Public display/discovery name                       |
| `email`        | string, unique nullable in model, nullable in migration | Optional email from Firebase/register form          |
| `bio`          | string nullable                                         | Chat list/profile description                       |
| `role`         | string default `user`, indexed                          | Role-based authorization hook                       |
| `is_active`    | boolean default true                                    | Account active flag                                 |
| `created_at`   | datetime                                                | Account creation time                               |
| `updated_at`   | datetime                                                | Profile update time                                 |

Used by:

- `backend/app/routes/user_routes.py`: register, current profile, list users, update user.
- `backend/app/services/user_service.py`: user lookup, creation, update.
- `backend/app/core/auth.py`: converts Firebase UID into DB user.
- `backend/app/websocket/chat_socket.py`: maps WebSocket token to DB user ID.
- `frontend/src/pages/Chat.tsx`: lists users for chat discovery through `GET /api/v1/users`.
- `frontend/src/pages/Feed.tsx`: gets current user ID through `GET /api/v1/users/me`.

### `friends`

Model: `backend/app/models/friend.py`

| Column         | Type / Rule                            | Purpose                       |
| -------------- | -------------------------------------- | ----------------------------- |
| `id`           | UUID primary key                       | Friend request ID             |
| `requester_id` | UUID FK `users.id`, indexed            | User who sent the request     |
| `addressee_id` | UUID FK `users.id`, indexed            | User who receives the request |
| `status`       | enum `pending`, `accepted`, `declined` | Request state                 |
| `created_at`   | datetime                               | Request creation time         |
| `responded_at` | datetime nullable                      | Accept/reject time            |

Used by:

- `backend/app/routes/friend_routes.py`
- `backend/app/services/friend_service.py`
- `backend/app/utils/privacy.py` for friends-only post visibility.

### `followers`

Model: `backend/app/models/follower.py`

| Column         | Type / Rule                 | Purpose             |
| -------------- | --------------------------- | ------------------- |
| `id`           | UUID primary key            | Follow row ID       |
| `follower_id`  | UUID FK `users.id`, indexed | User who follows    |
| `following_id` | UUID FK `users.id`, indexed | User being followed |
| `created_at`   | datetime                    | Follow time         |

Indexes:

- `ix_followers_follower_following`
- `ix_followers_following_follower`

Used by:

- `backend/app/routes/follow_routes.py`
- `backend/app/services/follow_service.py`
- `backend/app/utils/privacy.py` for followers-only post visibility.
- `backend/app/services/feed_service.py` for feed construction.

### `blocks`

Model: `backend/app/models/block.py`

| Column            | Type / Rule        | Purpose             |
| ----------------- | ------------------ | ------------------- |
| `id`              | UUID primary key   | Block row ID        |
| `blocker_id`      | UUID FK `users.id` | User who blocks     |
| `blocked_user_id` | UUID FK `users.id` | User who is blocked |
| `created_at`      | datetime           | Block time          |

Used by:

- `backend/app/routes/block_routes.py`
- `backend/app/services/block_service.py`
- `backend/app/services/chat_service.py`: prevents direct messages when users are blocked.
- `backend/app/services/follow_service.py` and `friend_service.py`: validates social actions.

### `messages`

Model: `backend/app/models/message.py`

| Column                | Type / Rule                              | Purpose                          |
| --------------------- | ---------------------------------------- | -------------------------------- |
| `id`                  | UUID primary key                         | Message ID                       |
| `sender_id`           | UUID FK `users.id`, indexed              | Sender                           |
| `receiver_id`         | UUID FK `users.id`, indexed              | Receiver                         |
| `content`             | string max 4096                          | Encrypted direct message content |
| `media_url`           | string max 2048 nullable                 | Uploaded attachment URL          |
| `media_type`          | string max 80 nullable                   | MIME type                        |
| `media_name`          | string max 255 nullable                  | Original/safe file name          |
| `media_size`          | int nullable                             | Uploaded byte size               |
| `reply_to_message_id` | UUID FK `messages.id`, nullable, indexed | Reply threading                  |
| `reactions`           | JSON default `{}`                        | Emoji -> user ID list            |
| `is_pinned`           | boolean default false                    | Pin state                        |
| `timestamp`           | timezone datetime, indexed               | Send time                        |
| `edited_at`           | timezone datetime nullable               | Edit time                        |
| `is_seen`             | boolean default false                    | Read status                      |

Indexes:

- `ix_messages_conversation(sender_id, receiver_id, timestamp)`
- `ix_messages_receiver_conversation(receiver_id, sender_id, timestamp)`

Used by:

- `backend/app/routes/chat_routes.py`: REST direct message API.
- `backend/app/services/chat_service.py`: create, list, search, edit, delete, seen, forward, pin, reactions.
- `backend/app/websocket/chat_socket.py`: realtime text messages, typing, read receipts, presence.
- `frontend/src/pages/Chat.tsx`: message history, search, send, media send, seen, edit, delete, pin, react, forward.
- `frontend/src/hooks/useWebSocket.ts` and `frontend/src/lib/websocket.ts`: realtime connection.

Encryption note: `chat_service.send_message()` stores `encrypt_value(content)` and `serialize_message()` returns `decrypt_value(message.content)`.

### `chat_settings`

Model: `backend/app/models/chat_settings.py`

| Column        | Type / Rule                 | Purpose                     |
| ------------- | --------------------------- | --------------------------- |
| `id`          | UUID primary key            | Settings row ID             |
| `user_id`     | UUID FK `users.id`, indexed | Owner of settings           |
| `peer_id`     | UUID FK `users.id`, indexed | Conversation peer           |
| `is_muted`    | boolean default false       | User-specific mute state    |
| `is_archived` | boolean default false       | User-specific archive state |
| `updated_at`  | timezone datetime           | Last update time            |

Constraints:

- unique pair: `user_id`, `peer_id`
- check: `user_id <> peer_id`

Used by:

- `backend/app/routes/chat_routes.py`
- `backend/app/services/chat_service.py`

Frontend note: there is currently no visible mute/archive UI in `Chat.tsx`.

### `posts`

Model: `backend/app/models/post.py`

| Column       | Type / Rule                                     | Purpose       |
| ------------ | ----------------------------------------------- | ------------- |
| `id`         | UUID primary key                                | Post ID       |
| `user_id`    | UUID FK `users.id`                              | Author        |
| `content`    | text required                                   | Post body     |
| `visibility` | enum `public`, `friends`, `followers`, `custom` | Privacy mode  |
| `created_at` | datetime                                        | Creation time |
| `updated_at` | datetime                                        | Update time   |

Indexes:

- `ix_posts_user_created_at`
- `ix_posts_visibility_created_at`

Used by:

- `backend/app/routes/post_routes.py`
- `backend/app/services/post_service.py`
- `backend/app/services/feed_service.py`
- `backend/app/utils/privacy.py`
- `frontend/src/pages/Feed.tsx`: reads feed, likes, reposts, comments.

### `post_likes`

Model: `backend/app/models/post_like.py`

| Column       | Type / Rule                       | Purpose     |
| ------------ | --------------------------------- | ----------- |
| `id`         | integer primary key autoincrement | Like row ID |
| `post_id`    | UUID FK `posts.id`, indexed       | Liked post  |
| `user_id`    | UUID FK `users.id`, indexed       | Liking user |
| `created_at` | timezone datetime                 | Like time   |

Constraint: unique pair `post_id`, `user_id`.

Used by:

- `backend/app/routes/post_routes.py`
- `backend/app/services/post_like_service.py`
- `frontend/src/pages/Feed.tsx`

### `post_comments`

Model: `backend/app/models/post_comment.py`

| Column       | Type / Rule                 | Purpose        |
| ------------ | --------------------------- | -------------- |
| `id`         | UUID primary key            | Comment ID     |
| `post_id`    | UUID FK `posts.id`, indexed | Parent post    |
| `user_id`    | UUID FK `users.id`, indexed | Comment author |
| `content`    | text required               | Comment body   |
| `created_at` | timezone datetime, indexed  | Comment time   |

Used by:

- `backend/app/routes/post_routes.py`
- `backend/app/services/post_comment_service.py`
- `frontend/src/pages/Feed.tsx`

### `post_reposts`

Model: `backend/app/models/post_repost.py`

| Column       | Type / Rule                 | Purpose        |
| ------------ | --------------------------- | -------------- |
| `id`         | UUID primary key            | Repost row ID  |
| `post_id`    | UUID FK `posts.id`, indexed | Reposted post  |
| `user_id`    | UUID FK `users.id`, indexed | Reposting user |
| `created_at` | timezone datetime, indexed  | Repost time    |

Constraint: unique pair `post_id`, `user_id`.

Used by:

- `backend/app/routes/post_routes.py`
- `backend/app/services/post_repost_service.py`
- `frontend/src/pages/Feed.tsx`

### `groups`

Model: `backend/app/models/group.py`

| Column              | Type / Rule                 | Purpose                                          |
| ------------------- | --------------------------- | ------------------------------------------------ |
| `id`                | UUID primary key            | Group ID                                         |
| `name`              | string max 120, indexed     | Group name                                       |
| `description`       | text nullable               | Group description                                |
| `type`              | string max 30, indexed      | `public`, `private`, `anonymous`, `organization` |
| `organization_name` | string max 160 nullable     | Organization label                               |
| `created_by`        | UUID FK `users.id`, indexed | Creator                                          |
| `created_at`        | timezone datetime           | Creation time                                    |

Indexes:

- `ix_groups_created_by_type`
- `ix_groups_created_at`

Used by:

- `backend/app/routes/group_routes.py`
- `backend/app/services/group_service.py`
- `backend/app/services/group_feed_service.py`
- `frontend/src/pages/Groups.tsx`

### `group_members`

Model: `backend/app/models/group_member.py`

| Column       | Type / Rule                             | Purpose                               |
| ------------ | --------------------------------------- | ------------------------------------- |
| `user_id`    | UUID FK `users.id`, primary key         | Member user                           |
| `group_id`   | UUID FK `groups.id`, primary key        | Group                                 |
| `role`       | string max 20 default `member`          | `owner`, `admin`, `member` style role |
| `status`     | string max 20 default `active`, indexed | Membership status                     |
| `alias`      | string max 80 nullable                  | Anonymous group alias                 |
| `invited_by` | UUID FK `users.id`, nullable            | Inviter                               |
| `joined_at`  | timezone datetime                       | Join time                             |

Constraint: unique pair `user_id`, `group_id`.

Used by:

- `backend/app/routes/group_routes.py`
- `backend/app/services/group_service.py`
- `backend/app/services/group_feed_service.py`

### `group_messages`

Model: `backend/app/models/group_message.py`

| Column      | Type / Rule                  | Purpose          |
| ----------- | ---------------------------- | ---------------- |
| `id`        | UUID primary key             | Group message ID |
| `sender_id` | UUID FK `users.id`, indexed  | Sender           |
| `group_id`  | UUID FK `groups.id`, indexed | Group            |
| `content`   | string max 4096              | Message text     |
| `timestamp` | timezone datetime, indexed   | Send time        |

Used by:

- `backend/app/routes/group_routes.py`: REST group message send/list.
- `backend/app/services/group_service.py`
- `backend/app/websocket/group_socket.py`: realtime group messaging.
- `frontend/src/pages/Groups.tsx`: sends and reloads group messages through REST.

### `group_posts`

Model: `backend/app/models/group_post.py`

| Column       | Type / Rule         | Purpose       |
| ------------ | ------------------- | ------------- |
| `id`         | UUID primary key    | Group post ID |
| `group_id`   | UUID FK `groups.id` | Group         |
| `user_id`    | UUID FK `users.id`  | Author        |
| `content`    | text required       | Post body     |
| `created_at` | datetime            | Creation time |
| `updated_at` | datetime            | Update time   |

Indexes:

- `ix_group_posts_group_created_at`
- `ix_group_posts_user_created_at`

Used by:

- `backend/app/routes/post_routes.py`
- `backend/app/services/group_feed_service.py`

Frontend note: no full group feed UI exists yet; `Groups.tsx` focuses on group creation and group messages.

## API Routers

`backend/app/main.py` mounts these routers:

| Mounted Prefix          | Router File                             | Purpose                                            |
| ----------------------- | --------------------------------------- | -------------------------------------------------- |
| `/api/v1/users`         | `backend/app/routes/user_routes.py`     | User registration, profile, discovery              |
| `/api/v1/friends`       | `backend/app/routes/friend_routes.py`   | Friend requests and accepted friends               |
| `/api/v1/follows`       | `backend/app/routes/follow_routes.py`   | Follow/unfollow and follower lists                 |
| `/api/v1/blocks`        | `backend/app/routes/block_routes.py`    | Block/unblock users                                |
| `/api/v1/chat`          | `backend/app/routes/chat_routes.py`     | Direct message REST operations                     |
| `/api/v1/groups`        | `backend/app/routes/group_routes.py`    | Group create/join/invite/messages                  |
| `/api/v1/posts`         | `backend/app/routes/post_routes.py`     | Posts, feed, group posts, likes, comments, reposts |
| `/ws/chat/{peer_id}`    | `backend/app/websocket/chat_socket.py`  | Direct chat realtime events                        |
| `/ws/groups/{group_id}` | `backend/app/websocket/group_socket.py` | Group chat realtime events                         |

Note: `backend/app/routes/chat_routes_new.py` exists as an older/alternate chat router, but `backend/app/main.py` imports and mounts `chat_routes.py`, not `chat_routes_new.py`.

## Endpoint Summary

All `/api/v1/*` endpoints require Firebase bearer auth unless explicitly health/root.

### Core

| Method | Path      | Backend               |
| ------ | --------- | --------------------- |
| `GET`  | `/health` | `backend/app/main.py` |
| `GET`  | `/`       | `backend/app/main.py` |

### Users

| Method | Path                      | Main Service                  |
| ------ | ------------------------- | ----------------------------- |
| `POST` | `/api/v1/users/register`  | `UserService.create_user`     |
| `GET`  | `/api/v1/users/me`        | `get_current_user` dependency |
| `PUT`  | `/api/v1/users/{user_id}` | `UserService.update_user`     |
| `GET`  | `/api/v1/users`           | `UserService.get_all_users`   |
| `GET`  | `/api/v1/users/{user_id}` | `UserService.get_user_by_id`  |

### Chat

| Method   | Path                                                     | Main Service                              |
| -------- | -------------------------------------------------------- | ----------------------------------------- |
| `POST`   | `/api/v1/chat/{receiver_id}/messages`                    | `send_message`                            |
| `POST`   | `/api/v1/chat/{receiver_id}/messages/media`              | `store_chat_upload`, `send_media_message` |
| `GET`    | `/api/v1/chat/{peer_id}/messages`                        | `get_conversation`                        |
| `GET`    | `/api/v1/chat/{peer_id}/messages/search`                 | `get_conversation`, in-memory filter      |
| `PATCH`  | `/api/v1/chat/{peer_id}/messages/{message_id}/seen`      | `mark_message_as_seen`                    |
| `DELETE` | `/api/v1/chat/{peer_id}/messages/{message_id}`           | `delete_message`                          |
| `PATCH`  | `/api/v1/chat/{peer_id}/messages/{message_id}`           | `update_message`                          |
| `POST`   | `/api/v1/chat/{peer_id}/messages/{message_id}/forward`   | `forward_message`                         |
| `PATCH`  | `/api/v1/chat/{peer_id}/messages/{message_id}/pin`       | `toggle_pin_message`                      |
| `PATCH`  | `/api/v1/chat/{peer_id}/messages/{message_id}/reactions` | `toggle_message_reaction`                 |
| `PATCH`  | `/api/v1/chat/{peer_id}/settings`                        | `update_chat_settings`                    |

### Posts And Feed

| Method   | Path                               | Main Service                                                |
| -------- | ---------------------------------- | ----------------------------------------------------------- |
| `POST`   | `/api/v1/posts/create`             | `PostService.create_post`                                   |
| `PUT`    | `/api/v1/posts/{post_id}`          | `PostService.update_post`                                   |
| `DELETE` | `/api/v1/posts/{post_id}`          | `PostService.delete_post`                                   |
| `GET`    | `/api/v1/posts/user/{user_id}`     | `PostService.get_user_posts`, `PrivacyEngine.can_view_post` |
| `GET`    | `/api/v1/posts/feed/{user_id}`     | `FeedService.get_feed`                                      |
| `GET`    | `/api/v1/posts/trending/{user_id}` | `FeedService.get_trending_feed`                             |
| `GET`    | `/api/v1/posts/{post_id}`          | `PostService.get_post`, `PrivacyEngine.can_view_post`       |
| `POST`   | `/api/v1/posts/{post_id}/like`     | `PostLikeService.toggle_like`                               |
| `DELETE` | `/api/v1/posts/{post_id}/like`     | `PostLikeService.toggle_like`                               |
| `GET`    | `/api/v1/posts/{post_id}/likes`    | like count and current user state                           |
| `POST`   | `/api/v1/posts/{post_id}/comments` | `PostCommentService.create_comment`                         |
| `GET`    | `/api/v1/posts/{post_id}/comments` | `PostCommentService.list_comments`                          |
| `GET`    | `/api/v1/posts/{post_id}/reposts`  | repost count and current user state                         |
| `POST`   | `/api/v1/posts/{post_id}/repost`   | `PostRepostService.toggle_repost`                           |
| `DELETE` | `/api/v1/posts/{post_id}/repost`   | `PostRepostService.toggle_repost`                           |

### Groups

| Method   | Path                                    | Main Service                         |
| -------- | --------------------------------------- | ------------------------------------ |
| `POST`   | `/api/v1/groups`                        | `create_group`                       |
| `POST`   | `/api/v1/groups/{group_id}/join`        | `join_group`                         |
| `POST`   | `/api/v1/groups/{group_id}/leave`       | `leave_group`                        |
| `POST`   | `/api/v1/groups/{group_id}/invite`      | `invite_user`                        |
| `GET`    | `/api/v1/groups/{group_id}/members`     | `list_members`                       |
| `POST`   | `/api/v1/groups/{group_id}/messages`    | `send_group_message`                 |
| `GET`    | `/api/v1/groups/{group_id}/messages`    | `get_group_messages`                 |
| `POST`   | `/api/v1/posts/group/{group_id}/create` | `GroupFeedService.create_group_post` |
| `GET`    | `/api/v1/posts/group/{group_id}/feed`   | `GroupFeedService.get_group_feed`    |
| `DELETE` | `/api/v1/posts/group/{post_id}`         | `GroupFeedService.delete_group_post` |

### Friends / Follows / Blocks

| Method   | Path                                            | Main Service                   |
| -------- | ----------------------------------------------- | ------------------------------ |
| `POST`   | `/api/v1/friends/requests/{addressee_id}`       | `send_friend_request`          |
| `POST`   | `/api/v1/friends/requests/{request_id}/respond` | `respond_to_friend_request`    |
| `GET`    | `/api/v1/friends`                               | `list_friends`                 |
| `GET`    | `/api/v1/friends/requests`                      | `list_pending_friend_requests` |
| `POST`   | `/api/v1/follows/{following_id}`                | `follow_user`                  |
| `DELETE` | `/api/v1/follows/{following_id}`                | `unfollow_user`                |
| `GET`    | `/api/v1/follows/following`                     | `list_following`               |
| `GET`    | `/api/v1/follows/followers`                     | `list_followers`               |
| `POST`   | `/api/v1/blocks/{blocked_id}`                   | `block_user`                   |
| `DELETE` | `/api/v1/blocks/{blocked_id}`                   | `unblock_user`                 |

## Backend Request Flow

1. Browser sends request through `frontend/src/lib/api.ts`.
2. `apiRequest()` reads `localStorage.authToken` or refreshes token from Firebase client auth.
3. Request includes `Authorization: Bearer <token>`.
4. FastAPI receives request in a route under `backend/app/routes/*`.
5. Route depends on `get_current_user` from `backend/app/core/auth.py`.
6. `get_current_user` depends on `get_firebase_uid` from `backend/app/core/firebase.py`.
7. Firebase Admin verifies the token and returns `uid`.
8. `UserService.get_user_by_firebase_uid()` finds the backend `users` row.
9. Route receives an `AsyncSession` from `get_db_session`.
10. Route calls a service in `backend/app/services/*`.
11. Service queries or mutates SQLAlchemy models in `backend/app/models/*`.
12. Pydantic schemas in `backend/app/schemas/*` serialize the response.
13. `StandardizeResponseMiddleware` and exception handlers shape responses/errors.

## Realtime Chat Flow

1. `frontend/src/pages/Chat.tsx` selects a peer from `GET /api/v1/users`.
2. `useWebSocket(selectedPeer.id)` creates a `WebSocketManager`.
3. `WebSocketManager.connect(token)` opens `/ws/chat/{peer_id}?token=<token>`.
4. `backend/app/websocket/chat_socket.py` verifies token through Firebase Admin.
5. Socket connection is stored in `ChatConnectionManager.active_connections[user_id]`.
6. Sender sends `{ "type": "message", "content": "..." }`.
7. Backend saves the message through `chat_service.send_message()`.
8. Backend sends `{ type: "message", data: message }` to sender and peer.
9. Typing, presence, and read receipt events are socket-only events.

Current behavior note: text messages use WebSocket for realtime delivery. Media messages use REST and then broadcast to connected users. Reply messages sent through REST are persisted but do not currently broadcast from the REST route.
