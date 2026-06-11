# Toolchain and Dependency Review

This document contains a comprehensive audit of all backend and frontend dependencies in the ChattingApp project.

## Backend Dependencies (`backend/requirements.txt`)

We audited all Python dependencies in the backend. They are categorized as follows:

| Dependency | Category | Purpose | Status / Action |
| :--- | :--- | :--- | :--- |
| `fastapi` | Required | Core web API framework | Active |
| `uvicorn` | Required | ASGI server for FastAPI | Active |
| `sqlalchemy` | Required | Object-Relational Mapper (ORM) | Active |
| `psycopg2-binary` | Required | PostgreSQL database driver | Active |
| `python-dotenv` | Required | Loading configuration from environment variables | Active |
| `pydantic`, `pydantic-settings` | Required | Data validation and settings management | Active |
| `firebase-admin` | Required | Authentication backend provider | Active |
| `python-jose[cryptography]` | Required | Session token manipulation and JWT validation | Active |
| `passlib[bcrypt]` | Required | Password hashing for local fallbacks | Active |
| `python-multipart` | Required | Parsing multipart requests (media uploads) | Active |
| `websockets` | Required | Core WebSocket server communication | Active |
| `cryptography` | Required | Cryptographic utilities for password hashes and encryption | Active |
| `PyJWT` | Required | JWT parsing and verification | Active |
| `requests` | Required | HTTP client library for external calls | Active |
| `asyncpg` | Required | Async PostgreSQL driver for the database session pool | Active |
| `alembic` | Required | Database migration runner | Active |
| `python-json-logger` | Required | Production JSON-structured logging | Active |
| `redis` | Optional | Caching, rate-limiting, and WebSocket PubSub broker | Active (Environment-gated) |
| `celery` | Optional | Distributed background task queue | Active (Environment-gated) |
| `rq` | Optional | Redis-backed simple background queue fallback | Active (Environment-gated) |
| `aiokafka` | Optional | Distributed event streaming broker | Active (Environment-gated) |
| `Pillow` | Required | Media validation and processing (image resizing) | Active |
| `boto3` | Optional | AWS S3 object storage driver | Active (Environment-gated) |
| `prometheus_client` | Required | Exporting Prometheus metrics | Active |
| `sentry-sdk` | Optional | Error reporting and tracing | Active (Environment-gated) |
| `opentelemetry-api` | Required | Observability API instrumentation | Active |
| `opentelemetry-sdk` | Required | Observability tracing/metrics provider | Active |
| `opentelemetry-exporter-otlp-proto-http` | Required | Exporting OTLP telemetry to collector | Active |
| `httpx` | Required | Async HTTP client (used in test suite and external APIs) | Active |
| `pyotp` | Required | Multi-Factor Authentication (MFA) OTP generation/verification | Active |
| `qrcode[pil]` | Required | QR Code generation for MFA setups | Active |

### Backend Removals & Cleanup

- **Removed Files**:
  - `backend/app/routes/chat_routes_new.py`: Verified duplicate route module containing identical endpoints to `chat_routes.py`. Deleted to prevent import conflicts and remove technical debt.
  - `backend/tmp_run_chat_advancement_tests.py`: Obsolete scratch test-runner file. Deleted.
  - `backend/tmp_test_insert.py`: Obsolete database insert testing script. Deleted.

---

## Frontend Dependencies (`frontend/package.json`)

We audited all frontend dependencies. They are categorized as follows:

| Dependency | Category | Purpose | Status / Action |
| :--- | :--- | :--- | :--- |
| `react`, `react-dom` | Required | Frontend UI components | Active |
| `react-router-dom` | Required | Client-side routing | Active |
| `zustand` | Required | Lightweight client state management (IndexedDB queue) | Active |
| `@tanstack/react-query` | Required | Async query/mutation state synchronization | Active |
| `@tanstack/react-query-devtools` | Optional | Development aids for query debugging | Active (Dev-only) |
| `firebase` | Required | Client authentication provider SDK | Active |
| `react-window` | Required | Virtualized lists for rendering heavy message feeds | Active |
| `@capacitor/core`, `@capacitor/cli` | Required | Capacitor mobile wrapper runtime | Active (Capacitor/Mobile build) |
| `@capacitor/android` | Optional | Android platform package | Active (Capacitor/Mobile build) |
| `vite` | Required | Build tool and bundler | Active |
| `vitest` | Required | Fast testing framework (Vitest) | Active |
| `jsdom` | Required | Virtual browser environment for tests | Active |
| `@testing-library/react` | Required | React component testing utilities | Active |

### Frontend Removals & Cleanup

- All imported packages are active and serve essential roles for routing, component lifecycle, virtualized scroll rendering, offline queuing, or android app compilation. No package removals are required at this time.
- Verified forwarding files (`frontend/src/layout/Sidebar.tsx`, `frontend/src/layout/Topbar.tsx`, `frontend/src/features/auth/Login.tsx`, and `frontend/src/features/auth/Register.tsx`) are clean import/export wrappers.
