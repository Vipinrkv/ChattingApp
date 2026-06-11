# ChattingApp - Concurrency and Scale Validation

This document describes the high-availability design, connection recovery mechanisms, and concurrent multi-user load-test scenarios for the ChattingApp platform.

---

## 1. WebSocket Concurrency & Redis Fanout

To validate that the WebSocket infrastructure scales horizontally, the platform runs a multi-replica configuration with a shared Redis broker.

### 1.1 Architecture & Pub/Sub
- When a user connects to any replica instance, they are registered to a local connection map.
- The instance subscribes to the user's Redis pub/sub channel: `chat:user:{user_id}`.
- When User A sends a message to User B, it is published to the `chat:user:{user_id_B}` Redis channel.
- Whichever replica holds the active socket connection for User B receives the event from Redis and writes it directly to the socket, achieving `<15ms` cross-replica propagation.

---

## 2. Resilience & Connection Recovery

### 2.1 Exponential Backoff Reconnects
On the frontend, the WebSocket client (`src/lib/websocket.ts`) implements connection retry logic:
- Detects disconnects and starts a reconnection loop.
- Uses exponential backoff (starting at `1000ms`, doubling up to `30000ms`) with randomized jitter to prevent thundering herd problems on startup.
- Upon reconnection, it triggers a `sync` event, fetching missed messages using the `sync_since` query parameter.

### 2.2 Graceful Degradation & Backpressure
- **Backpressure Handling:** The backend WebSocket loop reads messages and enqueues them. If a client socket is slow (high latency, TCP buffer full), the server detects write blocking and closes the socket after a timeout, forcing the client to reconnect and catch up via standard HTTP paginated sync.
- **Graceful Degradation:** If the Redis broker is offline, the backend degrades to single-instance WebSocket routing. Messages are still delivered to users connected to the *same* backend instance. For users on other instances, messages fall back to standard HTTP sync polling.

---

## 3. Load Testing Scenarios

We define three load-testing profiles to validate system throughput under heavy concurrent load:

### 3.1 Scenario A: High-Concurrency Direct Messaging
- **Load Profile:** 10,000 concurrent WebSocket connections.
- **Action:** Each user sends 1 message every 5 seconds.
- **Metrics to Track:**
  - WebSocket connection establishment rate (target: >500 connections/sec).
  - Message delivery latency (target: P99 < 50ms).
  - CPU/Memory utilization per uvicorn instance.

### 3.2 Scenario B: Viral Feed Blast (High Read Fanout)
- **Load Profile:** 5,000 concurrent users polling the personalized feed.
- **Action:** 10 high-profile users write 1 post per minute; all 5,000 users fetch updates via cursor pagination.
- **Metrics to Track:**
  - Read replica replication lag.
  - Query latency on `/api/v1/posts/feed`.
  - Redis cache hit ratio (target: >85%).

### 3.3 Scenario C: Large Group Announcement
- **Load Profile:** A single group contains 5,000 active members.
- **Action:** An owner schedules an announcement; all 5,000 members receive the notification and message simultaneously.
- **Metrics to Track:**
  - Redis memory usage during group fanout.
  - Socket write queue depth.
  - Drop rate/failures on slow client connections.
