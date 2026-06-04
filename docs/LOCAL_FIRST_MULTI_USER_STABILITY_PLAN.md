# Local-First Multi-User Stability Plan

## 1. Mission

Stabilize ChattingApp for many simultaneous users while moving toward a local-first architecture:

- Multiple users can connect at the same time from one machine, a LAN, and later hosted infrastructure.
- Most user-owned data is stored locally on each device first.
- Backups are encrypted at creation time and decrypted only during authorized restore or recall.
- Online database sync remains available for identity, discovery, moderation, cross-device recovery, and multi-user coordination.
- Feed data uses a tamper-evident blockchain-style event log without putting private user content on a public chain.

The Autonomous Optimization Architect constraint is strict: every network, AI, blockchain, and sync path must have timeouts, retry caps, circuit breakers, budget limits, and measurable acceptance checks.

## 2. Current Foundation

Already present in the repo:

- FastAPI backend with async SQLAlchemy, PostgreSQL, Redis, task queue support, observability, and Docker Compose.
- React/Vite frontend with PWA shell, offline queue, React Query offline-first mode, WebSocket manager, Zustand stores, and service worker assets.
- Direct chat and group WebSockets with Redis fanout readiness.
- Chat backup/export foundation through `chat_backups` and chat advancement routes.
- Feed, posts, comments, likes, reposts, group posts, stories/status, reels foundation, suggestions, friends, followers, blocking, notifications, moderation, and admin dashboards.
- LAN and hosting guidance in `docs/STABILITY_HOSTING_APP_GUIDE.md`.

## 3. Target Architecture

### Local device layer

Use browser/device storage as the first write target for user-owned data:

- IndexedDB for messages, feed drafts, cached feed items, settings, local media metadata, restore manifests, and sync checkpoints.
- Cache Storage for PWA shell, images, thumbnails, and static assets.
- File System Access API or native wrapper storage later for larger media archives and manual backup files.
- Web Crypto for local encryption and backup package encryption.

### Local encrypted backup layer

Backups should be portable encrypted bundles:

- Manifest: version, user ID, device ID, schema version, created timestamp, data categories, item counts, hash tree root.
- Payload: encrypted JSONL or SQLite export chunks for chats, feed drafts, saved posts, settings, media index, notification preferences, and local-only metadata.
- Media: either encrypted blobs inside the bundle or external encrypted object references.
- Crypto: per-backup random salt and nonce, AES-GCM content encryption, passphrase-derived key with PBKDF2 or Argon2id where available, and optional device-held recovery key.
- Restore: verify manifest and hash tree before decrypting, decrypt in chunks, import into IndexedDB first, then reconcile with server.

### Server coordination layer

Keep the central database for coordination, not as the only source of user memory:

- Auth identity, user profiles, public discovery, relationship graph, moderation records, abuse controls, and server-authoritative indexes remain in PostgreSQL.
- Server stores encrypted sync envelopes where cloud recovery is enabled.
- Server stores feed/event metadata needed for discovery and moderation, but private content should stay encrypted or local-only when privacy requires it.
- Redis remains the realtime fanout and cache layer.

### Blockchain-style feed integrity layer

Do not store private feed or chat content directly on a public blockchain. Instead:

- Build a local append-only event log for feed actions: create post, edit post, delete post, like, comment, repost, story publish, moderation state change.
- Each event includes `event_id`, `author_id`, `device_id`, `created_at`, `prev_hash`, `payload_hash`, `visibility`, and signed metadata.
- Store event payloads locally and/or in the database according to visibility.
- Store hashes and signatures in PostgreSQL for server verification.
- Optionally anchor periodic Merkle roots to a public chain later for public/community feeds only. This should be a future feature flag with a strict cost cap.

## 4. Implementation Phases

### Phase 0: Stability gate

Goal: prove the current app can support concurrent users before adding local-first complexity.

Tasks:

1. Add automated LAN smoke tests for `/health`, login, feed load, direct WebSocket chat, group WebSocket chat, uploads, and reconnect.
2. Run two backend replicas behind nginx with Redis fanout and validate cross-replica delivery.
3. Add load tests for 10, 50, 100, and 500 concurrent WebSocket clients.
4. Add server-side WebSocket rate limits, max message size, heartbeat timeout, and per-user connection caps.
5. Add CI checks for Alembic single head, backend tests, frontend tests, frontend build, and WebSocket fanout smoke where possible.

Acceptance:

- 100 concurrent socket clients can connect locally without lost direct messages.
- Two users on different LAN devices can chat, post, comment, and reconnect.
- Backend emits metrics for active sockets, send failures, reconnects, dropped messages, queue depth, and request latency.

### Phase 1: Settings system

Goal: implement a real settings surface like mature messaging/social apps.

Settings categories:

- Account: username, profile, linked devices, sessions, MFA, export account data, delete account.
- Privacy: last seen, online status, read receipts, profile visibility, story visibility, blocked users, discoverability.
- Notifications: chat, groups, mentions, comments, likes, follows, quiet hours, sound/vibration flags for native builds.
- Chat: theme, wallpaper, media auto-download, message backups, disappearing messages, archived chats, pinned chats.
- Feed: ranking mode, local/community radius, muted words, muted users, sensitive content, autoplay, data saver.
- Storage: local cache size, media retention, backup location, automatic backup schedule, clear cache.
- Security: encrypted backup passphrase, recovery key, device trust, app lock, audit log.

Implementation:

- Add `user_settings` and `device_settings` database tables for server-backed preferences.
- Add IndexedDB settings cache for offline use.
- Add settings API with optimistic local writes and later reconciliation.
- Add settings UI route and sections using existing UI components.

Acceptance:

- Settings load offline from IndexedDB.
- Settings sync across devices after reconnect.
- Privacy settings are enforced by backend feed/chat/profile queries, not only hidden in the UI.

### Phase 2: Local-first data store

Goal: make the client resilient when offline and reduce dependence on constant database reads.

Tasks:

1. Create a frontend local database module around IndexedDB.
2. Define local tables: `messages`, `threads`, `feed_events`, `feed_items`, `drafts`, `settings`, `media_index`, `sync_queue`, `backup_manifests`, `device_keys`.
3. Replace simple `localStorage` offline queue with durable IndexedDB queue.
4. Add conflict-safe client mutation IDs for messages, posts, comments, likes, reposts, settings updates, and media uploads.
5. Add sync checkpoints per data category.
6. Add conflict rules:
   - Messages are append-only with edit/delete events.
   - Settings use last-write-wins per field with device timestamp and server receipt timestamp.
   - Feed uses event ordering by server receipt plus signed client created time.
   - Moderation actions always override client-local visibility.

Acceptance:

- User can draft posts and send queued messages while offline.
- Reconnect sends queued mutations once, with idempotency keys.
- Refreshing the app offline preserves local chat/feed/settings state.

### Phase 3: Encrypted backups and recall

Goal: regular and manual encrypted backup, with verified restore.

Tasks:

1. Extend existing chat backup model into a general `user_backup_archives` concept, or add separate backup tables for all user-owned categories.
2. Implement client-side backup creation from IndexedDB.
3. Encrypt backup bundles before writing to disk or uploading.
4. Add manual backup download from settings.
5. Add scheduled backup policy:
   - Daily local metadata checkpoint.
   - Weekly full encrypted local backup.
   - Optional cloud encrypted backup only when enabled.
6. Add restore flow:
   - Select backup file.
   - Verify manifest and hash tree.
   - Ask passphrase or recovery key.
   - Decrypt locally.
   - Preview categories and counts.
   - Import into local store.
   - Reconcile with server using idempotency keys.

Acceptance:

- Backup file cannot be read without passphrase/recovery key.
- Restore rejects tampered backup bundles.
- Restore can recover chats, feed drafts, saved posts, settings, and media index into a fresh browser profile.

### Phase 4: Feed event chain

Goal: improve the feed with tamper-evident, local-first event storage.

Tasks:

1. Add `feed_events` table in PostgreSQL with event hash, previous hash, payload hash, actor, visibility, target entity, device ID, signature, and server receipt time.
2. Add local `feed_events` IndexedDB table with the same event envelope.
3. Convert feed mutations into events:
   - `post.created`
   - `post.edited`
   - `post.deleted`
   - `comment.created`
   - `reaction.added`
   - `reaction.removed`
   - `repost.created`
   - `story.created`
   - `moderation.visibility_changed`
4. Add a verifier service that checks hash continuity, duplicate event IDs, invalid signatures, and payload mismatch.
5. Add materialized feed projections for fast reads.
6. Add optional Merkle root anchoring as a disabled-by-default future integration.

Acceptance:

- Feed rebuilds from event log for a user or group.
- Invalid event hashes are rejected or quarantined.
- Moderation can hide content without deleting local audit history.

### Phase 5: Social feature parity

Goal: converge mature social/messaging features around stable primitives.

WhatsApp/Telegram-like:

- Multi-device sync, encrypted backups, pinned chats, archived chats, starred/bookmarked messages, disappearing messages, broadcast lists, channels, admin roles, read receipts, typing, presence, voice notes, media gallery.

Instagram-like:

- Stories, reels/short videos, close friends, profile grid, saved posts, explore, hashtags, mentions, DMs, creator analytics, privacy controls.

Twitter/X-like:

- Follow graph, public timeline, reposts, quote posts, trends, muted words, lists, bookmarks, notification filters, public verification, report flow.

Implementation priority:

1. Settings and privacy enforcement.
2. Chat archives, pinned chats, disappearing message policy.
3. Feed lists, muted words, quote posts, trends refinement.
4. Stories/reels polish and media lifecycle.
5. Channels/broadcasts and community moderation workflows.

### Phase 6: LAN and peer-assisted local networks

Goal: support local network usage without breaking security.

Tasks:

1. Keep normal LAN mode server-centered: backend on `0.0.0.0`, frontend on LAN-visible host, Redis for fanout.
2. Add LAN device discovery only after HTTPS/dev-cert story is stable.
3. Add QR-based device pairing for trusted local sync.
4. Add WebRTC peer-assisted media transfer as an optional optimization, with server fallback.
5. Keep all peer traffic encrypted and authenticated by paired device keys.

Acceptance:

- LAN mode works without public internet for already-authenticated sessions where token validity permits.
- New device pairing requires explicit approval from an existing trusted device.
- Peer-assisted transfer falls back to server upload/download when blocked.

### Phase 7: Online deployment path

Goal: take the local-first app online safely.

Steps:

1. Hosted PWA first:
   - Frontend on static hosting or nginx.
   - Backend on container platform.
   - Managed PostgreSQL.
   - Managed Redis.
   - Object storage for media and encrypted backups.
   - HTTPS and WebSocket support.
2. Production controls:
   - Rate limits per user/IP/device.
   - Circuit breakers for external AI, moderation, storage, notification, and blockchain providers.
   - Budget caps for AI and blockchain anchoring.
   - Observability dashboards and alerts.
   - Rollback runbook and migration backup enforcement.
3. Native wrapper later:
   - Capacitor or TWA for Android first.
   - Push notifications, local file backup, biometric app lock, native share sheet, camera/mic permissions.

Acceptance:

- Hosted PWA passes login, feed, chat, group chat, upload, backup, restore, and offline shell smoke tests.
- WebSocket reconnect survives deploy/rollback.
- External provider outage does not block local-first read paths.

## 5. Guardrails

- No unbounded retries. All sync, upload, backup, AI, and chain-anchor jobs require max attempts and dead-letter status.
- No public-chain private content. Only hashes or public/community roots may be anchored.
- No plaintext backups. Backups must be encrypted before disk write or upload.
- No silent restore overwrite. Restore imports into local staging first, then reconciles.
- No server-trust-only privacy. Backend queries must enforce privacy, blocking, moderation, and visibility rules.
- No cost-open blockchain integration. Any chain provider must have disabled-by-default flags, per-day spend caps, and a fallback to local hash logs only.

## 6. Suggested Delivery Order

1. Stability gate and two-replica WebSocket validation.
2. Settings tables, APIs, and frontend settings screen.
3. IndexedDB local data layer and durable sync queue.
4. Encrypted manual backup and restore.
5. Scheduled encrypted backups.
6. Feed event chain and verifier.
7. Social feature parity polish.
8. LAN pairing and peer-assisted transfer.
9. Hosted PWA deployment.
10. Native wrapper proof of concept.

## 7. First Engineering Sprint

Deliver in the first sprint:

- `frontend/src/lib/localDb.ts` for IndexedDB wrappers.
- Durable offline queue migration from `localStorage` to IndexedDB.
- Settings backend model, migration, service, routes, and frontend page.
- Manual encrypted backup export/import proof of concept for settings, drafts, and messages.
- LAN smoke test script for health, feed, direct chat, group chat, and reconnect.
- Metrics for sync queue depth, backup success/failure, restore success/failure, and WebSocket active connections.

Definition of done:

- Backend tests pass.
- Frontend build and tests pass.
- Two local users can chat and post concurrently.
- Backup export is encrypted.
- Restore works in a fresh browser profile.
- All new network jobs have retry caps, timeouts, and logged failure states.
