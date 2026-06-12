# Connection Structure

## 1. Architecture Summary

ChattingApp uses a split frontend/backend architecture. The frontend is a React SPA built with Vite. The backend is a FastAPI service that exposes REST and WebSocket endpoints. Authentication is handled by Firebase on the client and verified by Firebase Admin on the backend.

## 2. High-Level Connection Flow

### Core connection pipeline

- Browser runs React app
- Browser authenticates with Firebase client SDK
- Frontend stores the Firebase ID token and sends it to backend with each API request
- Backend verifies the token with Firebase Admin SDK
- Backend maps Firebase UID to a backend `users` record
- Backend executes business logic and persists state to PostgreSQL
- Backend returns JSON responses to the frontend

### Realtime connection pipeline

- User opens chat or group page
- Frontend connects WebSocket to backend with token in query string or headers
- Backend verifies the token and authorizes the socket
- Backend stores the connection and routes events to peers
- Updates are broadcast back to clients over WebSocket

## 3. Frontend / Backend Boundaries

### Frontend responsibilities

- Firebase auth lifecycle
- Token refresh and sign-out
- UI rendering and state management
- WebSocket connection lifecycle
- API request retry and error handling
- Local storage and client caching

### Backend responsibilities

- Token validation and authorization
- DB persistence and query handling
- Business logic and permissions
- WebSocket event routing
- Upload validation and file handling
- Observability and metrics endpoints

## 4. Environment Variables

### Frontend

- `VITE_API_BASE`: REST API base URL
- `VITE_WS_BASE`: WebSocket URL base (optional)
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

### Backend

- `DATABASE_URL`: PostgreSQL connection string
- `DB_SSL_MODE`: optional SSL mode for DB
- `REDIS_URL`: Redis connection string for pub/sub and cache
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CREDENTIALS_PATH`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRATION_HOURS`
- `AES_KEY`
- `CORS_ORIGINS`
- `ALLOWED_HOSTS`

## 5. API Traffic Patterns

### Authentication traffic

- Login/register uses Firebase on the frontend
- Backend routes validate with Firebase Admin
- Protected endpoints require `Authorization: Bearer <token>`

### Feed traffic

- `GET /api/v1/users/me`
- `GET /api/v1/posts/feed/{user_id}`
- `POST /api/v1/posts/{post_id}/like`
- `POST /api/v1/posts/{post_id}/comments`

### Chat traffic

- `GET /api/v1/chat/{peer_id}/messages`
- `POST /api/v1/chat/{receiver_id}/messages`
- WebSocket `/ws/chat/{peer_id}`

### Group traffic

- `POST /api/v1/groups`
- `GET /api/v1/groups/{group_id}/messages`
- `POST /api/v1/groups/{group_id}/messages`
- WebSocket `/ws/groups/{group_id}`

## 6. Infrastructure Connections

- PostgreSQL stores users, posts, messages, groups, and metadata
- Redis supports pub/sub for cross-instance websocket broadcast
- Nginx proxies frontend and backend traffic in containers
- Prometheus scrapes backend metrics for monitoring
- GitHub Actions manages CI/CD builds and deployment artifacts

## 7. Connection Rules

- All protected API calls must carry Firebase bearer auth
- Backend should never trust a Firebase token without user profile resolution
- WebSocket sessions use the same auth model as REST requests
- Media uploads must be validated on receipt and stored safely
- Deployment environments must enforce strict `CORS_ORIGINS` and `ALLOWED_HOSTS`

## 8. Local Network Access

The backend is already configured to bind to `0.0.0.0`, and the frontend API/WebSocket clients can resolve the current browser hostname for LAN devices. To test from another device, expose the frontend with `npm run dev -- --host 0.0.0.0 --port 5173`, add the host machine IP to `CORS_ORIGINS` and `ALLOWED_HOSTS`, and open `http://<host-ip>:5173`.

Use [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md) as the canonical runbook for local multi-connection testing, Docker/nginx testing, and hosted rollout.
