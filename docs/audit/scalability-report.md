# Scalability Report

This report summarizes our analysis of the platform's ability to scale horizontally.

---

## 1. WebSockets & Real-Time Sync
- **Fanout**: `RedisBroker` subscribes to a global Redis Pub/Sub channel, broadcasting message events to all active compute replicas to coordinate messages across users connected to different servers.
- **Stateless Replicas**: FastAPI backend processes are fully stateless, relying on JWT verification and external DB/Redis persistence.

---

## 2. Capacity Plan
- **1,000 Users**: Single Postgres/Redis instance on a 4GB VPS.
- **10,000 Users**: Two stateless backend replicas load-balanced by Nginx, utilizing a dedicated database server.
- **100,000 Users**: Multi-node Kubernetes or Nomad cluster, a sharded Redis cluster, and dedicated PostgreSQL read-replicas.
- **1,000,000 Users**: Sharded databases, PgBouncer poolers, multi-region Redis sharding, and CDN asset delivery.
