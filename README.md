# ChattingApp

A production-grade realtime social communication platform with a React + Vite frontend and FastAPI backend.

## Project Overview

ChattingApp is a unified full-stack repository for social communication and community collaboration. It combines realtime chat, groups, feed, notifications, media, and role-based security in a developer-first architecture.

## Recommended Documentation

### Start here

- [WorkProgress](WorkProgress.md)
- [Documentation home](docs/README.md)
- [Development guide](docs/DEVELOPMENT_GUIDE.md)
- [System audit and architecture plan](docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md)
- [Stable system, network access, hosting, and app conversion guide](docs/STABILITY_HOSTING_APP_GUIDE.md)
- [Local-first multi-user stability plan](docs/LOCAL_FIRST_MULTI_USER_STABILITY_PLAN.md)

### Architecture and system design

- [System audit and architecture plan](docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md)
- [Database and backend details](docs/DATABASE_BACKEND_DETAILS.md)
- [Connection structure](docs/CONNECTION_STRUCTURE.md)
- [File structure and system flow](docs/FILE_STRUCTURE_AND_SYSTEM_FLOW.md)
- [Realtime architecture](docs/REALTIME_ARCHITECTURE.md)
- [Security architecture](docs/SECURITY_ARCHITECTURE.md)
- [Multi-tenant architecture](docs/MULTI_TENANT_ARCHITECTURE.md)
- [AI moderation and safety](docs/AI_MODERATION_AND_SAFETY.md)
- [Mohalla Connect architecture](docs/MOHALLA_CONNECT_ARCHITECTURE.md)
- [Mohalla Connect implementation plan](docs/MOHALLA_CONNECT_IMPLEMENTATION_PLAN.md)

### Operations and delivery

- [Deployment and DevOps](docs/DEPLOYMENT_AND_DEVOPS.md)
- [Stable system, network access, hosting, and app conversion guide](docs/STABILITY_HOSTING_APP_GUIDE.md)
- [Observability and monitoring](docs/OBSERVABILITY.md)
- [Production rollback runbook](docs/PRODUCTION_ROLLBACK_RUNBOOK.md)

## Tech Stack

### Frontend

- React 18 + TypeScript
- Vite build system
- Zustand state management
- TanStack Query / React Query data layer
- Firebase Client SDK for auth
- WebSockets for realtime chat
- Responsive premium UI system with dark, light, and system theme support

## Frontend Experience

- Pre-auth users land on a responsive product experience before choosing login or signup.
- Authenticated users keep the existing dashboard, feed, chat, groups, profile, notifications, and media workflows.
- The UI design system centralizes cosmic blue surfaces, glass panels, typography, radius, shadows, focus states, skeleton loading, and reduced-motion-safe animation behavior.
- Layouts are tuned for mobile, tablet, laptop, desktop, and ultrawide breakpoints from 320px upward.
- Mobile users get a safe-area bottom tab bar, search sheet, floating create-post action, and chat list-to-thread flow.
- Social UX includes friend discovery, friend requests, local nicknames, chat gating for non-friends, group directory sections, and profile visibility previews.
- Authenticated desktop uses fixed left navigation, centered main content, and a live API-backed utility rail for notifications, trends, friends, and groups.
- Notification loading waits for Firebase auth/token readiness, and encrypted chat payloads are protected from raw token display if upstream decryption is unavailable.

### Backend

- FastAPI + Uvicorn ASGI
- Python 3.12
- SQLAlchemy Async + PostgreSQL
- Alembic migrations
- Redis cache / pubsub
- Firebase Admin SDK token verification
- WebSockets for direct and group realtime events

### Infrastructure

- Docker and `docker-compose`
- Nginx reverse proxy
- Prometheus monitoring
- GitHub Actions CI/CD
- Structured logs and observability

## Development Quick Start

### Backend

```powershell
cd backend
venv\Scripts\activate
npm run backend:install
copy .env.example .env
# update .env values
npm run backend:migrate
npm run backend
```

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Troubleshooting Notes

- If authenticated POST requests return `403`, check backend logs for `csrf_rejected`. Firebase Bearer-token API calls are exempt from CSRF; cookie-authenticated unsafe requests still require the configured CSRF cookie/header pair.
- If `/api/v1/chats/backups` returns `500`, verify migrations are current with `cd backend && venv\Scripts\python.exe -m alembic current`. Chat backup tables require `0008_chat_system_advancement`.
- WebSocket handshake failures now log `websocket_auth_failed` or `websocket_rejected` with the rejection reason. Browser clients should pass a valid Firebase ID token as `?token=...`.
- Local OAuth popup flows use `Cross-Origin-Opener-Policy: same-origin-allow-popups`; production keeps `same-origin`.

### Root commands

```powershell
npm run backend:install
npm run backend
npm run frontend
npm run frontend:wait
npm run backend:migrate
npm run dev
```

## Docker Local Stack

```powershell
docker compose up --build
```

## Local Network Access

For multi-device testing on the same Wi-Fi/LAN, run the backend on `0.0.0.0`, run Vite with `--host 0.0.0.0`, add the host machine IP to backend `CORS_ORIGINS` and `ALLOWED_HOSTS`, then open `http://<host-ip>:5173` from another device. The full runbook is in [Stable system, network access, hosting, and app conversion guide](docs/STABILITY_HOSTING_APP_GUIDE.md).

## Production and CI

- GitHub Actions workflow: `.github/workflows/ci-cd.yml`
- Production images are built and pushed for `main`
- Staging images are built for `staging`
- Rollback is handled through the workflow-dispatch rollback path and [Production rollback runbook](docs/PRODUCTION_ROLLBACK_RUNBOOK.md)

### Running Alembic migrations (local & CI)

- Local helper scripts are in `backend/tools`:
  - `db_backup_and_migrate.py` — create a `pg_dump` backup and run `alembic upgrade head` with optional Redis lock coordination
  - `backup_and_migrate.sh` — Linux/macOS wrapper that prefers the Python helper when available
  - `backup_and_migrate.ps1` — PowerShell wrapper that prefers the Python helper when available
  - `backend/tools/README.md` — usage notes and examples

- CI workflow: `.github/workflows/alembic-migrate-staging.yml` runs the shell script against a staging DB. Before running the workflow, set the repository secret `STAGING_DATABASE_URL` in GitHub (Settings → Secrets -> Actions).

Run locally (example):

```bash
export DATABASE_URL="postgresql://user:password@staging-host:5432/dbname"
./backend/tools/backup_and_migrate.sh
```

## What This Repo Contains

- `backend/`: FastAPI service, models, services, routes, and WebSocket handlers
- `frontend/`: React SPA, auth, state stores, and realtime UI
- `docs/`: architecture, operations, onboarding, security, and planning documents
- `docker-compose.yml`: local orchestration for backend, frontend, database, Redis, and Prometheus

## Documentation Principles

- Keep docs aligned with actual architecture
- Treat [System audit and architecture plan](docs/SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md) as the cleanup roadmap for error handling, fallback behavior, admin panel work, file organization, and documentation consolidation
- Separate completed work from remaining priorities
- Use enterprise-grade terminology and priority planning
- Drive onboarding through clear toolchain and runbook guidance
