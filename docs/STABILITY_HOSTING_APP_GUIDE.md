# Stable System, Network Access, Hosting, and App Conversion Guide

## 1. Scope

This guide is the operational plan for moving ChattingApp from a local feature-rich system to a stable multi-connection platform that can run on a developer machine, across a local network, and later on hosted infrastructure.

It is based on the current repository scan of:

- Backend FastAPI app, routers, services, models, Alembic migrations, WebSocket handlers, Redis broker, task queue, security middleware, observability, and Dockerfile
- Frontend React/Vite app, API client, WebSocket manager, PWA service worker, manifest, route protection, stores, and production build
- Docker Compose, nginx reverse proxy, Prometheus, Grafana, Alertmanager, CI/CD workflow, and existing architecture docs

## 2. Current System Check

### Working foundations

- Backend binds to `0.0.0.0:8000`, which supports local and LAN access when the host firewall allows it.
- Root `npm run backend` already starts Uvicorn with `--host 0.0.0.0 --port 8000`.
- Frontend API and WebSocket clients dynamically replace localhost API bases with the current browser hostname when opened from another device on the same network.
- WebSocket reconnect, heartbeat, singleton connection management, and send queue behavior are implemented in `frontend/src/lib/websocket.ts`.
- Backend direct chat and group WebSockets exist, with Redis broker support for cross-instance fanout.
- Docker Compose includes PostgreSQL, Redis, backend, frontend, nginx, Prometheus, Alertmanager, and Grafana.
- Nginx proxies `/api`, `/ws`, `/uploads`, `/metrics`, and frontend traffic, including WebSocket upgrade headers.
- Alembic is current through `0012_platform_enterprise_globalization`.
- PWA manifest, service worker, offline shell, install prompt, and background sync hooks are present.
- GitHub Actions build/test/image-publish workflow exists for staging and production images.

### Stability gaps

- Full backend test suite still needs fixture stabilization beyond targeted smoke tests.
- CI uses full backend tests but may fail until chat/group/media DB fixtures are normalized.
- Rollback in CI/CD remains a placeholder.
- LAN usage requires explicit CORS, allowed host, firewall, and frontend bind guidance.
- Docker Compose is good for single-host deployment but not yet an autoscaled production topology.
- WebSocket cross-instance support exists through Redis, but production validation with two backend replicas is still required.
- PWA conversion is ready as a web app install path, while native Android/iOS wrapping still needs a Capacitor or TWA packaging workflow.

## 3. Stable Local Multi-Connection Plan

### Target

Allow multiple browser sessions and multiple devices on the same machine or LAN to use REST, uploads, and WebSockets reliably.

### Steps

1. Start the backend on all interfaces.

   ```powershell
   npm run backend
   ```

2. Start the frontend on a LAN-visible interface.

   ```powershell
   cd frontend
   npm run dev -- --host 0.0.0.0 --port 5173
   ```

3. Find the host machine IP.

   ```powershell
   ipconfig
   ```

   Use the IPv4 address on the active Wi-Fi or Ethernet adapter, for example `192.168.1.25`.

4. Set development environment values.

   Backend `.env`:

   ```env
   APP_ENV=development
   DEBUG=true
   HOST=0.0.0.0
   PORT=8000
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.25:5173
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.25
   REDIS_URL=redis://localhost:6379/0
   TASK_QUEUE_BACKEND=inprocess
   ```

   Frontend `.env.local`:

   ```env
   VITE_API_BASE=http://192.168.1.25:8000
   VITE_WS_BASE=ws://192.168.1.25:8000
   ```

5. Allow local firewall access to ports:

   - `5173` for Vite dev server
   - `8000` for backend REST and WebSocket traffic
   - `3000`, `80`, and `443` when testing Docker/nginx

6. Open the app from another LAN device:

   ```text
   http://192.168.1.25:5173
   ```

7. Validate connection health:

   - `http://192.168.1.25:8000/health`
   - `http://192.168.1.25:8000/health/details`
   - Browser devtools Network tab for `/api/v1/users/me`
   - Browser devtools WebSocket frames for `/ws/chat/{peer_id}` or `/ws/groups/{group_id}`

### Acceptance checklist

- [ ] Two browser profiles can log in with separate users.
- [ ] Two LAN devices can load the frontend and call `/health`.
- [ ] Direct chat messages arrive over WebSocket without page refresh.
- [ ] Group WebSocket messages arrive for two connected users.
- [ ] Uploads resolve through `/uploads`.
- [ ] Refreshing one client does not disconnect other clients.
- [ ] Offline/reconnect UI recovers after temporarily stopping and restarting the backend.

## 4. Stable Docker Local Network Plan

### Target

Run the complete stack behind nginx for a local production-like environment.

### Steps

1. Configure `backend/.env.production`.

   ```env
   APP_ENV=production
   DEBUG=false
   DATABASE_URL=postgresql+asyncpg://chattingapp:strongpassword@postgres:5432/chat_platform
   REDIS_URL=redis://redis:6379/0
   CORS_ORIGINS=https://localhost,https://127.0.0.1,https://192.168.1.25
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.25
   JWT_SECRET_KEY=replace-with-32-plus-character-secret
   AES_KEY=replace-with-32-plus-character-secret
   ```

2. Configure `frontend/.env.production`.

   ```env
   VITE_API_BASE=https://192.168.1.25
   VITE_WS_BASE=wss://192.168.1.25
   ```

3. Generate or install local TLS certs for nginx.

   ```bash
   cd nginx
   ./generate-certs.sh
   ```

4. Start the stack.

   ```powershell
   docker compose up --build
   ```

5. Apply migrations inside the backend environment if the deployment process has not already run them.

   ```powershell
   docker compose exec backend alembic upgrade head
   ```

6. Validate:

   - `https://192.168.1.25/`
   - `https://192.168.1.25/health`
   - `https://192.168.1.25/metrics`
   - Grafana at `http://192.168.1.25:3001`
   - Prometheus at `http://192.168.1.25:9090`

## 5. Production Stability Plan

### Phase 1: Baseline hardening

- Freeze environment templates for local, staging, and production.
- Require `APP_ENV=production`, `DEBUG=false`, strong `JWT_SECRET_KEY`, strong `AES_KEY`, explicit `CORS_ORIGINS`, and explicit `ALLOWED_HOSTS`.
- Run Alembic `upgrade head` only after backup in staging/production.
- Keep `/health`, `/health/details`, `/metrics`, and `/performance` available for monitoring.
- Keep Redis enabled for cache, task queue, and WebSocket fanout.

### Phase 2: Multi-connection validation

- Run two backend replicas behind nginx or a load balancer.
- Confirm WebSocket fanout through Redis with users connected to different backend instances.
- Add connection-limit tests for direct chat and group chat.
- Add WebSocket disconnect reason dashboards.
- Add smoke tests for login, feed load, direct chat, group chat, upload, and admin summary.

### Phase 3: Release discipline

- Make CI green for frontend build/tests and backend tests before deployment.
- Add deployment smoke tests after container rollout.
- Replace rollback placeholder with previous-image redeploy.
- Store migration backups with date, revision, and environment labels.
- Record production deploy notes in `CHANGELOG.md`.

### Phase 4: Scale readiness

- Move PostgreSQL to managed Postgres with SSL.
- Move Redis to managed Redis or a monitored Redis cluster.
- Put static assets and uploads behind object storage/CDN.
- Use horizontal backend replicas for API/WebSocket load.
- Use a dedicated worker process for notification, analytics, media, and moderation jobs.
- Use Prometheus/Grafana alerts for latency, errors, DB pool saturation, Redis failures, and WebSocket disconnect spikes.

## 6. Hosting Guide

### Minimum supported hosting topology

- Frontend: static host or nginx container
- Backend: containerized FastAPI service
- Database: managed PostgreSQL
- Redis: managed Redis
- Proxy: nginx, cloud load balancer, or platform routing
- TLS: platform-managed certificate or nginx certificate
- Observability: Prometheus/Grafana or hosted equivalent

### Recommended environment variables

Backend:

```env
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://...
DB_SSL_MODE=require
REDIS_URL=redis://...
FIREBASE_PROJECT_ID=...
FIREBASE_CREDENTIALS_PATH=/run/secrets/firebase-admin.json
JWT_SECRET_KEY=...
AES_KEY=...
CORS_ORIGINS=https://app.example.com
ALLOWED_HOSTS=app.example.com,api.example.com
SECURE_SSL_REDIRECT=true
COOKIE_SECURE=true
COOKIE_SAMESITE=Strict
RATE_LIMIT_ENABLED=true
AUDIT_LOGGING_ENABLED=true
SENTRY_DSN=...
OTEL_EXPORTER_OTLP_ENDPOINT=...
CDN_URL=https://cdn.example.com
```

Frontend:

```env
VITE_API_BASE=https://api.example.com
VITE_WS_BASE=wss://api.example.com
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

### Host-specific options

- VPS or bare metal: use `docker compose`, nginx TLS, managed database preferred.
- Render/Fly/Railway-style platforms: deploy backend container, frontend static build, managed Postgres, managed Redis, and set env vars in the platform dashboard.
- AWS/GCP/Azure: use container service, managed Postgres, managed Redis, object storage, CDN, load balancer, and managed TLS.
- Firebase Hosting plus backend elsewhere: host `frontend/dist` on Firebase Hosting and point API/WS env vars to the backend domain.

### Hosting rollout checklist

- [ ] Create staging environment first.
- [ ] Configure DNS and TLS.
- [ ] Configure production env vars.
- [ ] Apply migrations after backup.
- [ ] Run smoke tests.
- [ ] Verify Firebase authorized domains.
- [ ] Verify CORS and allowed hosts.
- [ ] Verify WebSocket upgrade through proxy.
- [ ] Verify uploads and CDN URLs.
- [ ] Verify metrics, logs, and alerts.
- [ ] Promote to production only after staging passes.

## 7. App Conversion Guide

### Path A: Installable PWA

This is the shortest path because the repo already includes:

- `frontend/public/manifest.webmanifest`
- `frontend/public/sw.js`
- `frontend/public/offline.html`
- `frontend/src/lib/serviceWorker.ts`
- install prompt handling in `frontend/src/App.tsx`

Steps:

1. Build the frontend.

   ```powershell
   cmd /c npm --prefix frontend run build
   ```

2. Serve over HTTPS.
3. Confirm manifest and service worker load from the production origin.
4. Confirm the browser install prompt appears.
5. Test offline shell, cached navigation, and update banner.

PWA acceptance checklist:

- [ ] Lighthouse PWA checks pass.
- [ ] App can be installed on Android and desktop Chrome/Edge.
- [ ] Offline page opens when network is unavailable.
- [ ] New service worker update displays reload prompt.
- [ ] Firebase auth domain includes the deployed host.

### Path B: Android wrapper with Trusted Web Activity

Use this when the hosted PWA is the source of truth and Android should open it as a store-distributed app.

Steps:

1. Host the PWA on HTTPS.
2. Create an Android TWA project.
3. Add Digital Asset Links from the web domain to the Android package.
4. Set the app start URL to the hosted PWA.
5. Test login, WebSocket traffic, uploads, and offline shell on a physical device.
6. Prepare Play Store assets, privacy policy, and data safety form.

### Path C: Capacitor native shell

Use this when native APIs are required beyond the browser/PWA surface.

Steps:

1. Add Capacitor to the frontend package.
2. Configure `webDir` as `dist`.
3. Build frontend with production API/WS values.
4. Sync Android/iOS projects.
5. Add platform permissions for camera, microphone, notifications, and file access as needed.
6. Test Firebase auth redirect/popup behavior inside the shell.
7. Keep API and WebSocket URLs pointed at hosted HTTPS/WSS domains.

### App conversion risks

- OAuth redirect domains must be configured for the hosted app and native shell.
- Push notifications need a mobile-specific setup plan.
- Camera/microphone permissions need platform prompts and privacy copy.
- WebSocket connections must use `wss://` in production.
- Offline writes must be tested against app lifecycle pauses and resumes.

## 8. Verification Commands

Use these commands after major system or hosting changes:

```powershell
venv\Scripts\python.exe -m compileall app
venv\Scripts\python.exe -m alembic current
venv\Scripts\python.exe -m pytest
cmd /c npm --prefix frontend run test
cmd /c npm --prefix frontend run build
docker compose up --build
```

## 9. Immediate Next Work

1. Add a documented LAN smoke test script for health, API base, and WebSocket reachability.
2. Stabilize full backend tests by fixing chat/group/media fixture setup.
3. Add a two-backend-replica Docker Compose profile to validate Redis WebSocket fanout.
4. Replace CI rollback placeholder with previous-image redeploy instructions.
5. Add Capacitor or TWA proof-of-concept only after the hosted PWA path is stable.
