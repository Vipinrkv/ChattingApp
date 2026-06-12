# System Fallback and Recovery Architecture

This document defines the primary paths, fallback paths, and recovery strategies for all critical subsystems of the ChattingApp platform, ensuring service continuity and high fault tolerance.

---

## 1. Subsystem Fallback Matrix

| Subsystem | Primary Path | Fallback Path | Recovery Strategy |
| --- | --- | --- | --- |
| **Authentication** | Firebase Authentication | Supabase JWT / Local Signature Verification | Upon Firebase API timeout or network outage, verify incoming user sessions using local Supabase JWT signatures. Allow read-only access to cached IndexedDB data. Re-test Firebase availability every 60s. |
| **Data Storage** | Amazon S3 / MinIO Object Storage | Local Host Filesystem (`/uploads`) | If S3 API returns `5xx` errors or becomes unreachable, the storage manager redirects file uploads to the host's local storage path. A background sync worker sweeps local files to S3 once connection is restored. |
| **Notifications** | Firebase Cloud Messaging (FCM) | Local Client Polling | If FCM returns an error, the client switches to periodic HTTP long-polling (every 30s) to fetch unread notification counts. Once network logs show FCM requests succeeding, polling shuts down. |
| **WebSockets** | Redis Pub/Sub horizontal message fanout | Single-Replica Local WebSocket routing | If Redis broker goes down, uvicorn replicas fallback to direct in-process WebSocket connection routing. Scaling degrades to single-node routing, and a critical alert is sent to DevOps. |
| **Media Processing** | FFmpeg Transcoder & AVIF Optimizer | Raw File Pass-through | If the media optimization worker queue is full or transcoding fails, media is accepted in its original uploaded format without conversion. |
| **Sync Syncing** | Realtime WebSockets | Background HTTP queue syncing | If WebSockets disconnect, the outbox sync falls back to background HTTP batch requests. Once WebSocket connection is re-established, HTTP batches cease. |
| **External APIs (AI)** | Gemini AI API (Moderation / Tagging) | Rule-based local regex filter & human review queue | If Gemini API is unreachable, content is scanned using local keyword lists. Suspicious content is hidden from public feeds and queued for manual moderator review. |
| **Observability** | Hosted OpenTelemetry collector | Local system file logs | If the OTel agent fails, capture metrics in system logger files without blocking API responses. Telemetry exports are buffered locally up to 100MB before discarding. |
| **Caching** | Redis cache layer | Direct PostgreSQL query routing | If Redis cache is offline, all cache read requests are bypassed directly to the database. Expose degraded health status via `/health/details`. |
| **Background Jobs** | Celery / RQ distributed worker queue | In-process asyncio background threads | If Celery broker is offline, short tasks are executed in FastAPI using async tasks (`BackgroundTasks`), while heavy media tasks are throttled and run sequentially. |

---

## 2. Detailed Recovery Implementations

### 2.1 Database & Caching Fallback
- **Degraded Caching Mode:** The `redis_cache` module catches all `ConnectionError` exceptions. If Redis is unreachable:
  1. The cache manager marks `redis_cache.enabled = False`.
  2. All cache requests return `None`, causing routers to query the primary database.
  3. The manager schedules a `ping` check every 30 seconds to automatically re-enable caching once Redis comes back online.

### 2.2 Firebase to Supabase Auth Transition
- **Dynamic Provider Swapping:** The backend `ExternalProviderManager` implements dynamic verification:
  1. It reads the incoming bearer token.
  2. If the token is signed by Firebase, it verifies it against Firebase.
  3. If Firebase is offline (or disabled via configuration settings), the auth service attempts to verify the signature using the configured local JWT secret (`SUPABASE_JWT_SECRET`).
  4. User sessions are verified using database-backed records.

### 2.3 Storage Sync Backlog
- When the storage adapter switches to local storage fallback, it writes a sync manifest file containing the local path, S3 bucket target, and MIME type.
- A background cron task monitors this directory. When S3 connectivity is restored, it uploads the files in batches and deletes the local replicas upon successful verification.
