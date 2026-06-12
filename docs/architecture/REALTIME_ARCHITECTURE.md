# Realtime Architecture

## 1. Overview

The realtime subsystem is built around WebSockets for direct messaging and group chat. The backend supports event routing and can leverage Redis pub/sub for cross-instance delivery.

## 2. Core Components

- `frontend/src/lib/websocket.ts`: WebSocket manager and reconnect logic
- `frontend/src/hooks/useWebSocket.ts`: hook for chat pages
- `backend/app/websocket/chat_socket.py`: direct chat socket handler
- `backend/app/websocket/group_socket.py`: group chat socket handler
- `backend/app/websocket/redis_broker.py`: Redis-based cross-instance fanout

## 3. Connection Lifecycle

- Connect to `/ws/chat/{peer_id}` or `/ws/groups/{group_id}`
- Authenticate with Firebase token
- Authorize the socket after backend resolves `users` profile
- Keep a singleton socket manager to prevent duplicates
- Reconnect with exponential backoff on failure

## 4. Event Model

- `message`: send and receive chat text/media events
- `typing`: typing indicators
- `presence`: online/offline status
- `read_receipt`: message read confirmations
- `notification`: realtime notification delivery

## 5. Scaling and Reliability

### Current state

- WebSocket manager supports singleton sockets, reconnect backoff, heartbeat pings, token refresh reconnects, and bounded send queue behavior.
- Backend chat and group sockets support authenticated realtime traffic.
- Redis broker support is available for cross-instance fanout, but two-replica production validation is still required before declaring autoscaled WebSocket hosting complete.

### Planned enhancements

- Two-backend-replica validation with Redis fanout through nginx/load balancer
- Tenant-aware websocket session isolation
- Backpressure handling and flow control
- Reconnect and offline sync
- Guaranteed delivery semantics for critical events

## 6. Metrics and Monitoring

- Track active connection count
- Track message throughput and latency
- Monitor socket disconnect reasons
- Add Prometheus metrics for websocket events

## 7. Operational Guidelines

- Keep socket auth and REST auth aligned
- Avoid embedding business logic in socket handlers
- Use service layer functions for message persistence
- Support both REST and socket flows for critical message writes

## 8. Realtime Roadmap

- Add socket connection limits per user
- Add cross-instance routing with Redis
- Add ordered delivery and deduplication safeguards
- Add offline message replay and sync support
- Add realtime analytics dashboards
