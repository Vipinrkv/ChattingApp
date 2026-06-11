# System Architecture Report

This document outlines the core architectural components of the ChattingApp platform, including frontend state, backend services, real-time messaging, and offline-first capabilities.

---

## 1. High-Level Architecture Overview

ChattingApp is built on a decoupled, client-server model designed for sub-second messaging and social interaction:

- **Frontend**: A modern React SPA compiled using Vite and TypeScript. Native integration on mobile is achieved via Capacitor.
- **Backend**: An asynchronous FastAPI service utilizing Uvicorn and Python 3.11.
- **Database**: PostgreSQL handles structured, relational data models (Users, Posts, Groups, Messages).
- **Caching & Broker**: Redis handles WebSocket connection fanout and API cache entries.

---

## 2. Backend Design Patterns

### A. CQRS (Command Query Responsibility Segregation)
- Backend writes (Commands) and reads (Queries) are partitioned in `app/core/cqrs.py`.
- **Benefit**: Separates query optimization (caching, database-level views) from transactional write validation, increasing query throughput.

### B. Domain Event Dispatcher
- Modifying transactions publish events to the `event_bus` (`app/core/event_bus.py`).
- Depending on environment variables, the system instantiates an `InMemoryEventBus`, `RedisEventBus`, or `KafkaEventBus`.

### C. Connection Pools & Transactions
- Relational database sessions are pooled asynchronously using `asyncpg`.
- The `transaction` context manager in `app/core/transaction.py` wraps complex write steps, executing safe commits and automatic rollback on failure.

---

## 3. Real-Time WebSocket Infrastructure

To support high concurrent messaging and feed updates:
- **WebSocket Gateway**: Handled by FastAPI's built-in websockets implementation.
- **Redis Multi-Node Fanout**: When multiple backend replicas run, the `RedisBroker` subscribes to Redis pub/sub channels. Realtime messages are broadcasted to all replicas, and the replica holding the recipient's active WebSocket connection delivers the payload.
- **Graceful Reconnections**: The frontend implements exponential backoff and connection recovery.

---

## 4. Offline-First Architecture

To ensure usability in low-connectivity or offline scenarios:
- **IndexedDB Sync Engine**: Stores a local copy of user chats, feeds, and profiles.
- **Offline Outbox Queue**: Outgoing messages, stories, and reactions are placed in a persistent queue in IndexedDB.
- **Conflict Resolution**: When connection is restored:
  - The client reconciles local updates sequentially.
  - Server-side validation handles sequence numbers and filters duplicates.
  - Verification is covered by 22 Vitest tests passing under `localFirst.test.ts`.
