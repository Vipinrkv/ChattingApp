# Changelog

Dont change or update the data only add the data please

## 2026-06-04

- Added an active priority-based TODO roadmap to `WorkProgress.md`, separating completed foundations from incomplete P0/P1/P2/P3 work.
- Added active status and quick-reference sections to `WorkProgress.md`, and marked the older dashboard/reference sections as legacy to avoid stale status confusion.
- Recreated `Progress.md` as a compact progress snapshot that points to `WorkProgress.md` as the detailed source of truth.
- Consolidated developer onboarding, engineering governance, sprint planning, and quick local setup guidance into `docs/DEVELOPMENT_GUIDE.md`.
- Removed stale duplicate documentation files from the active project docs set: `Progress.md`, `TODO.md`, old prompt/learning notes, quickfix notes, separate onboarding/governance/sprint docs, horizontal scaling duplicate, production readiness duplicate, and uploaded runtime README copies.
- Folded the small moderation and safety notes into `docs/AI_MODERATION_AND_SAFETY.md` so moderation API and enforcement guidance live in one place.
- Updated `README.md`, `docs/README.md`, `docs/DEPLOYMENT_AND_DEVOPS.md`, `docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md`, and `WorkProgress.md` to point at the slimmer canonical documentation structure.

## 2026-06-01

- Scanned the current system, deployment files, realtime stack, PWA assets, CI/CD workflow, Docker/nginx setup, observability files, and docs to produce a stable-system rollout plan.
- Added `docs/STABILITY_HOSTING_APP_GUIDE.md` with local multi-connection setup, LAN access steps, Docker/nginx validation, production stability phases, hosting environment guidance, and PWA/TWA/Capacitor app conversion paths.
- Linked the new stability/hosting/app conversion guide from `README.md`, `docs/README.md`, `docs/DEPLOYMENT_AND_DEVOPS.md`, `docs/CONNECTION_STRUCTURE.md`, and `docs/PRODUCTION_READINESS.md`.
- Refreshed realtime and production-readiness docs to reflect the current WebSocket manager, Redis fanout foundation, nginx proxy support, observability setup, and remaining two-replica validation work.
- Updated `WorkProgress.md` and `Progress.md` with the stable system plan, LAN/multi-device runbook status, revised deployment/realtime/observability percentages, and next validation tasks.
- Completed long-term platform expansion foundations: live stream lifecycle APIs, voice/video call sessions with quality capture, screen-share sessions, creator monetization profiles, marketplace listings, subscription plans, platform events, and community channels.
- Added enterprise operations foundations: role assignment, audit review center, support tickets, revenue ledger entries, reporting snapshots, and enterprise summary rollups for the guarded admin console.
- Added globalization foundations: user locale/timezone preferences, localization string upserts, regional content policies, international moderation queue, timezone-aware scheduling, and region-specific recommendations.
- Added Alembic revision `0012_platform_enterprise_globalization`, wired the new models into metadata loading, registered `/api/v1/platform`, `/api/v1/enterprise`, and `/api/v1/globalization` routes, and upgraded the database to the new head.
- Expanded the frontend admin dashboard with platform expansion, enterprise operations, and globalization readiness panels.
- Updated `WorkProgress.md` and `Progress.md` to mark the requested long-term platform, enterprise, and globalization items complete.
- Verified `compileall app`, frontend production build, Alembic head/current, and targeted backend tests (`test_auth.py`, `test_service_example.py`) pass.
- Completed the backend architecture evolution checklist with RQ queue backend support, existing Celery/Redis queue routing, Kafka event-bus readiness, runtime scaling status, and `docs/HORIZONTAL_SCALING_STRATEGY.md`.
- Added analytics and business-system foundations: durable analytics events, admin summary endpoint, user/engagement/creator/revenue/moderation/retention rollups, and realtime hourly engagement heatmap data.
- Expanded the frontend admin dashboard with analytics cards, retention/moderation/revenue metrics, heatmap visualization, and runtime scaling readiness.
- Added advanced social feature foundations: suggested users, mutual friends, close friends, verification requests/badge fields, social graph ranking signals, polls, stories/status, and short video/reels APIs.
- Added Alembic revision `0011_analytics_social_scaling` and widened Alembic `version_num` handling so long revision IDs apply cleanly.
- Verified `compileall app`, frontend production build, Alembic current/heads, and targeted backend smoke tests pass; full backend suite remains partially blocked by existing chat/group/media fixture/auth failures.
- Added advanced group community features across backend and frontend: richer discovery metadata, directory search/ranking, analytics and growth metrics, onboarding templates, event scheduling, announcement-only channels, and verification request flow.
- Completed advanced group integration with discovery ranking, template onboarding guidance, announcement-only channel UX, event scheduling, verification requests, and analytics endpoint support.
- Added database support for advanced group settings and `group_events` with Alembic revision `0009_advanced_group_features`.
- Added Alembic merge revision `0010_merge_archive_and_group_heads` so the migration graph now has a single head.
- Fixed `0006_add_message_archive_partitions` so PostgreSQL can create the range-partitioned archive table without an invalid primary key on a non-partition column.
- Added frontend PWA and offline support with service worker caching, install prompt handling, offline shell fallback, background sync registration, and accessible offline status flows.
- Added backend event-driven architecture and distributed task queue support with optional Redis/Celery worker backends and in-memory fallback.
- Upgraded the Groups UI with template-based creation, tags/categories, discoverable and announcement toggles, onboarding cards, event management, verification actions, and live group metric summaries.
- Integrated the first stability implementation slice from the system audit plan: frontend fallback handling, guarded admin panel entry, API error parsing, and backend test/import hardening.
- Added frontend app-level `ErrorBoundary`, reusable `RetryPanel`, and shared `AppError` parsing utilities so UI crashes, API failures, request timeouts, and fallback states are handled consistently.
- Added guarded `/admin` route with role verification through `/api/v1/users/me`, plus an admin dashboard for moderation reports and `/health/details` system status.
- Added admin navigation entry and responsive admin/fallback styling.
- Stabilized backend async engine creation by applying pool sizing options only when the engine is not using `NullPool`; this fixes backend test/import failures caused by incompatible SQLAlchemy pool arguments.
- Verified frontend production build and frontend tests pass.
- Verified Alembic reports a single head: `0010_merge_archive_and_group_heads`.
- Backend tests now import and start, but DB-backed chat advancement tests still fail on missing fixture data for foreign-key-backed user/message rows; logged as the next backend test-stability task.

## 2026-05-31

- Added `docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md` as the canonical cleanup and architecture roadmap covering system status, error handling, fallback behavior, admin panel work, file organization, documentation consolidation, and removal candidates.
- Updated documentation entry points so `README.md`, `docs/README.md`, and `WorkProgress.md` point to the new audit plan.
- Recorded current architecture risks found during the whole-system scan, including the two-head Alembic migration graph, missing frontend admin panel, inconsistent error handling, generated/runtime files in the workspace, and duplicate/stale documentation.

## 2026-05-30

- Transformed the frontend visual system with a premium responsive social communication UI, public landing page, system-aware theme persistence, glassmorphism surfaces, skeleton states, accessibility focus states, reduced-motion support, and mobile/ultrawide layout fixes.
- Fixed false-positive CSRF `403` responses for Firebase Bearer-token API calls, including registration and multipart chat media uploads.
- Added explicit WebSocket authentication failure logging for missing/invalid tokens and missing users/peers.
- Fixed chat advancement migrations and applied database schema through `0008_chat_system_advancement`, including chat backup tables.
- Fixed chat backup enum mappings so database values remain lowercase.
- Added defensive backup API error logging and a detailed health endpoint at `/health/details`.
- Added frontend in-flight guards to reduce duplicate login, registration, and backup requests during development.
