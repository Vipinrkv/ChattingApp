# File Structure and System Flow

## 1. Project Topology

```
ChattingApp/
  backend/
  frontend/
  docs/
  nginx/
  prometheus/
  docker-compose.yml
  package.json
  README.md
```

## 2. Backend Structure

- `backend/app/main.py`: FastAPI application setup, router mounting, middleware, startup/shutdown tasks
- `backend/app/core/config.py`: environment settings and validation
- `backend/app/core/firebase.py`: Firebase Admin initialization and token verification
- `backend/app/core/auth.py`: maps Firebase UID to backend `User`
- `backend/app/core/security.py`: cryptography helpers and security utilities
- `backend/app/core/middleware.py`: custom response and security middleware
- `backend/app/core/response.py`: standard API response formatting
- `backend/app/database/connection.py`: async SQLAlchemy engine and session provider
- `backend/app/models/`: SQLAlchemy model definitions
- `backend/app/schemas/`: Pydantic request/response models
- `backend/app/routes/`: HTTP API route handlers
- `backend/app/services/`: business logic and DB operations
- `backend/app/websocket/`: WebSocket handlers and Redis broker
- `backend/alembic/`: migration configuration and version files

## 3. Frontend Structure

- `frontend/src/main.tsx`: React app bootstrap and provider mounting
- `frontend/src/App.tsx`: route definitions and layout
- `frontend/src/firebase.ts`: Firebase client config
- `frontend/src/contexts/AuthContext.tsx`: auth lifecycle and token management
- `frontend/src/lib/api.ts`: REST client abstraction
- `frontend/src/lib/websocket.ts`: WebSocket manager
- `frontend/src/hooks/useWebSocket.ts`: hook wrapper for socket lifecycle
- `frontend/src/pages/`: page screens for dashboard, feed, chat, groups, profile, login, register
- `frontend/src/components/`: reusable UI components
- `frontend/src/layout/`: shell and layout components
- `frontend/src/stores/`: Zustand stores and app state
- `frontend/src/ui/`: design primitives and shared UI assets

## 4. System Flow Overview

### App Startup

1. User opens the browser at the frontend URL.
2. Vite loads the React app and renders `App`.
3. `AuthProvider` subscribes to Firebase auth state.
4. If the user is authenticated, the app loads protected content.
5. If not, the app redirects to login or register.

### Login and Registration

1. User submits credentials through login/register forms.
2. Firebase client authenticates and provides an ID token.
3. Frontend stores token in `localStorage.authToken`.
4. Frontend calls backend auth-protected endpoints with the bearer token.
5. Backend verifies token with Firebase Admin, resolves `users` row, and authorizes the request.

### Feed and Post Flow

1. `Feed` page requests `GET /api/v1/users/me`.
2. Backend resolves current user and returns profile data.
3. The app requests `GET /api/v1/posts/feed/{user_id}`.
4. Backend builds the feed from posts, followers, and privacy rules.
5. Feed actions (like, comment, repost) call dedicated post endpoints.

### Chat Flow

1. `Chat` page loads peer list from `GET /api/v1/users`.
2. User selects a peer and loads chat history from `GET /api/v1/chat/{peer_id}/messages`.
3. `useWebSocket` connects to `/ws/chat/{peer_id}` using the Firebase token.
4. Backend authenticates the socket and stores the active connection.
5. Messages are sent as WebSocket events and persisted by the backend.

### Group Flow

1. `Groups` page creates or joins group through `POST /api/v1/groups`.
2. Group messages are sent via REST and optionally broadcast via group WebSockets.
3. Group membership and permissions are enforced by service logic.

## 5. Developer Note

This file is the canonical map for developer onboarding and architecture discovery. If you need more detail, follow the linked docs under `README.md`.
