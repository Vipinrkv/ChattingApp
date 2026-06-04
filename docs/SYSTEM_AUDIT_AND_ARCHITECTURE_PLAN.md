# System Audit and Architecture Plan

> Last updated: 2026-05-31
> Scope: whole-system cleanup, architecture hardening, admin panel planning, error handling, fallback behavior, file organization, and documentation consolidation.

> 2026-06-01 implementation update: first stability slice integrated. Frontend fallback/error handling, guarded `/admin`, admin moderation/system-health dashboard, frontend API error normalization, and backend async engine pool hardening are now implemented. Alembic is currently single-head at `0010_merge_archive_and_group_heads`.

> 2026-06-04 documentation update: duplicate progress, onboarding, sprint, governance, quickfix, prompt, learning, and small moderation docs were consolidated or removed. `WorkProgress.md`, `docs/README.md`, `docs/DEVELOPMENT_GUIDE.md`, and focused architecture/runbook docs are now the active documentation set.

## Executive Status

ChattingApp has a broad full-stack foundation: FastAPI backend, React/Vite frontend, Firebase auth, PostgreSQL/Alembic, Redis-aware realtime paths, moderation routes, media handling, observability hooks, Docker, Prometheus, and Grafana assets.

The next stage should be stabilization and simplification. The codebase has enough features to be useful, but it also has duplicated files, generated artifacts in the workspace, contradictory progress docs, two Alembic migration heads, partial admin UI coverage, and inconsistent frontend/backend error presentation. The goal is not to add more surface area first. The goal is to make the existing system reliable, explainable, and easy to operate.

## Current System Status Report

| Area | Status | Notes |
| --- | --- | --- |
| Backend API | Functional but needs consolidation | Routes, services, schemas, middleware, and observability exist. Several routes still translate domain failures directly to generic `HTTPException` strings. |
| Frontend app | Functional user app with admin first slice | Authenticated shell, feed, chat, groups, friends, profile, search, responsive layout, and guarded `/admin` dashboard exist. |
| Auth/security | Strong foundation, needs verification | Firebase verification, RBAC helpers, CSRF, rate limiting, security headers, session/device endpoints, and audit services exist. Production defaults and coverage should be tested. |
| Realtime | Implemented, needs failure-mode testing | WebSocket managers, reconnect logic, Redis broker fallback, direct chat, and group sockets exist. Multi-instance behavior needs integration tests. |
| Error handling | Partially centralized | Backend global handlers exist, frontend API retry/timeouts exist, but domain errors and user-facing fallback states are inconsistent. |
| Observability | Implemented foundation | `/health`, `/health/details`, `/metrics`, `/performance`, Prometheus, Grafana, tracing hooks, and Sentry hooks exist. Alert runbooks need to be tied to failures. |
| Database/migrations | Single-head as of 2026-06-01 | Alembic currently reports one head: `0010_merge_archive_and_group_heads`. Keep the single-head check in CI. |
| Documentation | Consolidated | `WorkProgress.md` is the active status dashboard; `docs/README.md` is the docs index; `docs/DEVELOPMENT_GUIDE.md` owns onboarding, governance, sprint, and release practices. |
| Repository hygiene | Needs cleanup | `node_modules`, `frontend/dist`, `backend/venv`, `backend/uploads`, generated logs, and accidental pip output files appear in the workspace and should not be treated as source. |

## Critical Findings

1. Resolve the Alembic branch split before more database work.
   - `0005_security_hardening` branches into moderation and message archive migrations.
   - Current heads are `0006_add_message_archive_partitions` and `0008_chat_system_advancement`.
   - Add a merge migration or explicitly rebase the archive migration into the main line after testing on a disposable database.

2. Expand the real admin panel beyond the first frontend slice.
   - Backend admin moderation report endpoints exist under `/api/v1/admin`.
   - Frontend now has a guarded `/admin` dashboard for report review and system health.
   - Next panels should cover audit logs, user risk, support tooling, and analytics.

3. Standardize error handling end to end.
   - Backend has global exception handlers and `build_error_response`.
   - Many route/service paths still return inconsistent messages or catch broad exceptions.
   - Frontend has API retries and local error states, but no app-level error boundary and no shared error taxonomy.

4. Separate source from generated/runtime artifacts.
   - Generated dependency folders, build output, local uploads, local virtual environments, and pip output logs should stay out of source review and release artifacts.
   - Existing `.gitignore` covers many of these patterns, but the workspace still contains them.

5. Consolidate documentation.
   - Completed on 2026-06-04 by removing stale duplicate trackers and folding onboarding, governance, sprint, quickfix, and moderation summary guidance into active docs.
   - Root `README.md` and `docs/README.md` are now entry points instead of duplicate roadmap documents.

## Target Architecture

### Backend

- Keep the current modular FastAPI structure, but enforce a clearer boundary:
  - `app/routes`: HTTP/WebSocket transport only.
  - `app/services`: business use cases and domain decisions.
  - `app/models`: SQLAlchemy persistence models.
  - `app/schemas`: request/response contracts.
  - `app/core`: cross-cutting infrastructure such as auth, config, errors, logging, metrics, permissions, pagination, security, and task queue.
  - `app/database`: engine, sessions, health checks, migration helpers.
  - `app/websocket`: realtime connection managers and broker adapters.

- Add or strengthen:
  - `app/core/exceptions.py`: typed domain/application exceptions.
  - `app/core/error_codes.py`: stable API error codes.
  - `app/core/fallbacks.py`: database/Redis/external-service fallback policies.
  - `app/core/dependencies.py`: shared dependency wiring for auth, roles, DB, pagination, and request metadata.
  - `app/admin`: optional future package if admin use cases grow beyond moderation routes.

### Frontend

- Keep user product pages under `src/pages`.
- Put durable feature modules under `src/features`.
- Add an admin feature:
  - `src/features/admin/AdminLayout.tsx`
  - `src/features/admin/AdminDashboard.tsx`
  - `src/features/admin/ReportsQueue.tsx`
  - `src/features/admin/UserRiskPanel.tsx`
  - `src/features/admin/SystemHealthPanel.tsx`
  - `src/features/admin/auditLogApi.ts`

- Add shared resilience components:
  - `src/components/ErrorBoundary.tsx`
  - `src/components/EmptyState.tsx`
  - `src/components/RetryPanel.tsx`
  - `src/lib/errors.ts`
  - `src/lib/fallbacks.ts`

### Infrastructure

- Treat Docker, Nginx, Prometheus, and Grafana as deployable infrastructure.
- Keep local/generated outputs out of release review.
- Add health gates to CI:
  - backend tests
  - frontend tests/build
  - Alembic heads check
  - dependency vulnerability check
  - docs link check

## Error Handling Plan

### Backend

1. Define a stable API error envelope:

```json
{
  "success": false,
  "error": {
    "code": "resource_not_found",
    "message": "Report not found",
    "details": {}
  },
  "request_id": "..."
}
```

2. Introduce typed exceptions:
   - `ValidationAppError`
   - `AuthAppError`
   - `PermissionAppError`
   - `NotFoundAppError`
   - `ConflictAppError`
   - `RateLimitAppError`
   - `DependencyUnavailableError`

3. Map typed exceptions in one global handler.

4. Remove broad `except Exception` blocks from route files unless they add useful context and re-raise typed errors.

5. Add `request_id`, `user_id`, route, method, status, error code, and dependency health metadata to structured logs.

6. Ensure WebSocket failures emit stable close codes and structured error events.

### Frontend

1. Add an app-level `ErrorBoundary`.
2. Create `AppError` parsing in `src/lib/errors.ts`.
3. Show consistent retry/fallback panels for:
   - backend unavailable
   - auth expired
   - permission denied
   - upload failed
   - websocket disconnected
   - offline mode
4. Route all API failures through shared toast/error UI.
5. Add tests for API error parsing and critical page fallback states.

## System Fallback Plan

| Dependency | Fallback |
| --- | --- |
| PostgreSQL unavailable | Startup can continue only in development. Production must fail fast. UI shows maintenance state. |
| Redis cache unavailable | Continue without cache, log degraded mode, expose degraded health in `/health/details`. |
| Redis WebSocket broker unavailable | Use in-process WebSocket delivery for single-instance development; production alert required. |
| Firebase unavailable | Block protected API calls, show auth service unavailable state, avoid infinite logout loops. |
| Media processor unavailable | Accept original upload only when policy allows; mark optimization/transcoding as pending or failed. |
| AI moderation unavailable | Fall back to rule-based moderation and queue content for review. |
| Observability exporter unavailable | Do not fail user requests; log exporter errors and expose degraded telemetry status. |

## Admin Panel Plan

### Phase 1: Moderation Console

- Add `/admin` route guarded by `admin` or `moderator` role.
- Show report queue from `/api/v1/admin/reports`.
- Add report detail, evidence, reporter, target, status, and action history.
- Add resolve, dismiss, mute, suspend, shadow-ban, and note actions.
- Add clear empty/loading/error states.

### Phase 2: System Operations

- Add health panel using `/health/details`, `/metrics` summary, and `/performance`.
- Show database, Redis, WebSocket broker, queue, upload storage, AI moderation, and background task health.
- Add audit log view from security endpoints.

### Phase 3: User and Trust Tools

- Add user search, risk summary, session/device view, login history, abuse summary, and IP reputation.
- Add role management only after a full authorization audit.

### Phase 4: Analytics

- Add moderation analytics, user growth, engagement, retention, system latency, and realtime connection dashboards.

## File System Reorganization Plan

### Keep

- `backend/app`
- `backend/alembic`
- `backend/tests`
- `backend/tools`
- `backend/supabase`
- `frontend/src`
- `frontend/public`
- `docs`
- `.github/workflows`
- `docker-compose.yml`
- `nginx`
- `prometheus`
- `grafana`

### Move or Consolidate

- Consolidate duplicate frontend auth files:
  - Prefer `frontend/src/features/auth/Login.tsx` and `frontend/src/features/auth/Register.tsx`.
  - Remove or convert `frontend/src/pages/Login.tsx` and `frontend/src/pages/Register.tsx` after verifying imports.

- Consolidate duplicate navigation/layout components:
  - Prefer `frontend/src/layout/Sidebar.tsx` and `frontend/src/layout/Topbar.tsx`.
  - Remove or merge `frontend/src/components/Sidebar.tsx` and `frontend/src/components/Topbar.tsx` after checking usage.

- Consolidate virtual list components:
  - Compare `frontend/src/ui/VirtualList.tsx` and `frontend/src/ui/VirtualizedList.tsx`.
  - Keep one canonical component and update imports.

- Consolidate route files:
  - `backend/app/routes/chat_routes.py` is included by the app.
  - `backend/app/routes/chat_routes_new.py` appears unused and should be removed only after diffing behavior.

- Consolidate progress docs:
  - `WorkProgress.md` is the active status dashboard.
  - Duplicate historical trackers were removed from the active docs set.

### Remove From Source Review / Cleanup Locally

These are not source-of-truth project files:

- `node_modules/`
- `frontend/node_modules/`
- `backend/venv/`
- `frontend/dist/`
- `frontend/build.log`
- `backend/uploads/` sample/runtime upload files
- `backend/0.24.0`
- `backend/7.4.2`
- duplicate uploaded README files under `backend/uploads/` were removed on 2026-06-04
- local `.env` files and secret-bearing files

Do not delete runtime uploads blindly if they are needed for manual testing. Archive or clear them as a deliberate cleanup task.

## Documentation Reorganization Plan

### Canonical Docs

- `README.md`: concise project overview and quick start.
- `docs/README.md`: documentation index.
- `WorkProgress.md`: current system status, active risks, and next milestones.
- `CHANGELOG.md`: append-only release/change history.
- `docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md`: current cleanup and architecture roadmap.
- `docs/DEVELOPMENT_GUIDE.md`: onboarding, local setup, engineering rules, sprint discipline, and release practices.

### Completed Consolidation

- Removed duplicate `Progress.md` and `TODO.md`.
- Removed old prompt, learning, quickfix, sprint, governance, and onboarding docs after consolidating useful content.
- Folded moderation API notes into `docs/AI_MODERATION_AND_SAFETY.md`.
- Keep Mohalla Connect docs only while that product scope remains active.

### Documentation Rules

- Every doc must have a clear owner purpose: overview, architecture, runbook, roadmap, or historical note.
- Do not repeat completion percentages across multiple files.
- Every status report must include an update date.
- Remove claims of completion unless code, tests, and runbook coverage exist.

## Execution Roadmap

### Phase 0: Safety Baseline

- Run backend tests and frontend tests/build.
- Add CI check for multiple Alembic heads.
- Snapshot current docs before consolidation.
- Confirm which generated/runtime folders are intentionally kept locally.

### Phase 1: Migration and Cleanup

- Resolve Alembic branch heads.
- Remove accidental pip output files.
- Remove or archive generated build/runtime artifacts from source review.
- Consolidate duplicate frontend and backend files after import checks.

### Phase 2: Error and Fallback Architecture

- Add typed backend application exceptions and error codes.
- Normalize route error mapping.
- Add frontend `ErrorBoundary`, shared error parser, retry panels, and offline/backend-down states.
- Add WebSocket error event contract tests.

### Phase 3: Admin Panel

- Build guarded `/admin` frontend route.
- Implement moderation queue and report detail.
- Add system health and audit log panels.
- Add tests for role protection and admin API contracts.

### Phase 4: Architecture Hardening

- Add domain event/task queue policy.
- Formalize repository/service boundaries only where needed.
- Add stronger observability runbooks.
- Add production readiness gates for deploys.

## Immediate Next Tasks

1. Create Alembic merge migration for the two current heads.
2. Add `npm`/CI script that fails when more than one Alembic head exists.
3. Add frontend `ErrorBoundary` and wrap `App`.
4. Add shared backend typed exceptions and update two representative route groups first.
5. Build `/admin/reports` frontend MVP.
6. Remove or archive accidental/generated files after confirmation.
7. Keep duplicate docs removed and avoid reintroducing parallel status trackers.

## Definition of Done

- `alembic heads` reports one head.
- Backend and frontend tests pass.
- Frontend build passes.
- Admin route is role-guarded and usable.
- Critical user journeys have clear loading, empty, error, and retry states.
- Runtime/generated files are excluded from source review.
- Docs index points to one current status source.
- `WorkProgress.md` matches actual system status.
