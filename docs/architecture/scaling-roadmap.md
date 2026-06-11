# Infrastructure Scaling Roadmap

This document outlines the system capacity expansion plan to scale the ChattingApp platform from 1,000 to 1,000,000 concurrent users.

---

## 1. Scale Phase Capacity Matrix

| Target Concurrent Users | Compute Nodes | Database Topology | Redis Usage | Storage Engine |
| :--- | :--- | :--- | :--- | :--- |
| **1,000** | 1 VPS (2 vCPU, 4GB RAM) | Single SQLite / Postgres | Single local Redis instance | Local File System |
| **10,000** | 2 Stateless Replicas (Nginx) | Postgres Primary (RDS/Compute) | Cluster replica (Pub/Sub active) | Self-hosted MinIO (Local NVMe) |
| **100,000** | 5-10 Nodes (Kubernetes/Nomad) | Postgres Primary + 2 Read Replicas | Multi-node Redis Cluster | Distributed MinIO Cluster |
| **1,000,000**| 50+ Nodes (Geo-distributed) | PgBouncer + Sharded Postgres DBs | Redis Cluster (Sharded PubSub) | Dedicated Ceph / S3 Storage |

---

## 2. Scaling Path & Architecture Milestones

### Phase A: 1K to 10K Users
- Migrate from SQLite (development) to a dedicated PostgreSQL instance.
- Deploy two stateless FastAPI backend instances behind an Nginx reverse proxy.
- Enable `RedisBroker` to handle real-time WebSocket connection sync between the two instances.

### Phase B: 10K to 100K Users
- Place PgBouncer in front of PostgreSQL to handle connection pooling.
- Deploy the stateless FastAPI containers on a container orchestrator (e.g. Nomad, Kubernetes, or ECS).
- Setup two PostgreSQL read-replicas and route read operations (`get_feed`, `get_conversation`) to them, reserving the primary instance for transactional write operations.

### Phase C: 100K to 1M Users
- Set up a sharded Redis cluster to handle websocket Pub/Sub messages across regions.
- Partition PostgreSQL database tables (e.g., hash-partitioning the `messages` table by `conversation_id`).
- Set up global load balancing (GSLB) and deploy stateless compute instances in multiple geographic regions to reduce latency.
- Offload media delivery to a distributed CDN (e.g., Cloudflare or self-hosted Varnish caches).
