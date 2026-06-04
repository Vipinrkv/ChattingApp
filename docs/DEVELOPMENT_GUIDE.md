# Development Guide

## Purpose

This guide is the single developer-facing entry point for onboarding, local setup, engineering rules, sprint discipline, and first tasks for ChattingApp.

## Quick Start

Install backend dependencies:

```powershell
cd backend
venv\Scripts\activate
npm run backend:install
copy .env.example .env
```

Install frontend dependencies:

```powershell
cd frontend
npm install
copy .env.example .env
```

Run the local stack:

```powershell
docker compose up --build
```

Run the app directly during development:

```powershell
npm run backend
npm run frontend
```

For LAN and multi-device testing, follow `docs/STABILITY_HOSTING_APP_GUIDE.md`.

## Repo Map

- `backend/`: FastAPI app, SQLAlchemy models, services, routes, WebSocket handlers, workers, and tools.
- `frontend/`: React app, pages, Zustand stores, hooks, UI components, API client, WebSocket client, and PWA assets.
- `docs/`: current architecture, operations, stability, security, and planning docs.
- `nginx/`: reverse proxy config.
- `prometheus/` and `grafana/`: local observability config.
- `docker-compose.yml`: local stack orchestration.

## Reading Path

1. `README.md` for project overview and common commands.
2. `WorkProgress.md` for current priorities and active risks.
3. `docs/FILE_STRUCTURE_AND_SYSTEM_FLOW.md` for source layout and request flow.
4. `docs/CONNECTION_STRUCTURE.md` for API, auth, and WebSocket wiring.
5. `docs/SECURITY_ARCHITECTURE.md` before touching auth, privacy, encryption, or moderation.
6. `docs/STABILITY_HOSTING_APP_GUIDE.md` before changing LAN, hosting, WebSocket scaling, or app packaging.

## Onboarding Checklist

- [ ] Backend starts and `/health` responds.
- [ ] Frontend loads and login works.
- [ ] Docker Compose stack starts locally.
- [ ] Direct chat and group chat work in the UI.
- [ ] WebSocket reconnect behavior is understood.
- [ ] Current priority list in `WorkProgress.md` has been reviewed.

## Engineering Rules

- Keep business logic out of routes and UI components.
- Put backend domain operations in services.
- Use centralized validation, pagination, permission, response, and error helpers.
- Make database changes migration-first.
- Keep I/O async on the backend.
- Normalize WebSocket events and manage connection behavior centrally.
- Add or update docs when architecture, deployment, security, or developer workflows change.
- Keep `WorkProgress.md` as the active status dashboard. Do not restart duplicate progress trackers.

## Testing Expectations

- Backend-facing changes should include unit or route tests when behavior changes.
- Auth, authorization, security, backup, restore, and moderation changes require regression coverage.
- WebSocket and realtime changes require at least smoke validation and should include automated coverage when practical.
- Frontend changes should keep `npm --prefix frontend run build` and the frontend test suite passing.

## Sprint Discipline

- Prefer two-week planning windows.
- Keep each sprint centered on one clear system goal.
- Break work into vertical slices that can be tested end to end.
- Assign one owner per story.
- Track active status in `WorkProgress.md`.

Current recommended sprint order:

1. Multi-user stability and WebSocket fanout validation.
2. Settings and privacy enforcement.
3. Local-first IndexedDB data layer.
4. Encrypted backup and restore.
5. Feed event-chain integrity.
6. Hosted PWA validation.

## Release Discipline

- Use `staging` for pre-production validation and `main` for production releases.
- Keep PRs focused on one feature, fix, or operational change.
- Run migrations only after backup in staging or production.
- Validate health, metrics, logs, rollback path, and WebSocket behavior before promoting.
- Document rollback and restore evidence for any risky deployment.

## Useful Local Files

- `backend/app/core/`: auth, config, middleware, observability, response, and security helpers.
- `backend/app/services/`: business logic.
- `backend/app/routes/`: HTTP route boundaries.
- `backend/app/websocket/`: direct chat, group chat, and Redis broker code.
- `frontend/src/lib/api.ts`: API request handling.
- `frontend/src/lib/websocket.ts`: WebSocket manager.
- `frontend/src/stores/`: app state stores.
- `frontend/src/pages/`: product screens.
