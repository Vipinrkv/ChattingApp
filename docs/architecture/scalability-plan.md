# System Scalability and Reliability Plan

This document outlines the scaling profiles, database structures, and server topologies required to support user growth from 1,000 to 1,000,000 active users.

---

## 1. Subsystem Scaling Topologies

### 1.1 WebSocket Scaling (Realtime Channels)
- **Bottleneck:** A single node can handle ~10,000 concurrent sockets before CPU/RAM constraints limits it.
- **Scaling Solution:** Deploy behind a load balancer (Nginx/HAProxy) routing connections to multiple FastAPI/Uvicorn replicas. Replicas synchronize message events horizontally using a clustered **Redis Pub/Sub** broker.
- **Connection Backoff:** Clients must implement exponential backoff reconnection algorithms with random jitter to prevent reconnect-storms from overloading nodes after outages.

### 1.2 Redis scaling
- **Bottleneck:** High Pub/Sub traffic + cache queries can exhaust Redis single-threaded performance.
- **Scaling Solution:** Segregate Redis instances:
  - Instance A: WebSockets Pub/Sub broker (high throughput, volatile).
  - Instance B: Application Caching (high memory limits, LRU eviction).
  - Instance C: Task queue broker (Celery/RQ, persistent data).
- For large scale, deploy **Redis Sentinel** or **Redis Cluster** to support automatic failovers.

### 1.3 Database scaling
- **Bottleneck:** Write bottlenecks on the primary Postgres node due to chat logs and feed activity.
- **Scaling Solution:**
  - **Read/Write Split:** Route all write operations (creating posts, sending messages) to the Primary node. Route read queries (loading feeds, user searches) to Read Replicas using SQLX / PGPool connection routers.
  - **Partitioning:** Partition the `messages` and `notifications` tables by time (monthly partitions) to keep indexes small and queries fast.
  - **Sharding:** Beyond 500,000 users, shard the user data across multiple database instances using `user_id` hash ranges.

### 1.4 Media scaling
- **Bottleneck:** Local storage disk capacity exhaustion and processing bottlenecks.
- **Scaling Solution:** Move upload targets entirely to AWS S3 or Google Cloud Storage. Deliver media objects globally using a Content Delivery Network (CDN) like Cloudflare or CloudFront to cache assets near users and reduce origin load.

---

## 2. Growth Scaling Profiles

### 👤 Stage 1: 1,000 Users (Development / Pilot)
- **Topology:** Single-server VPS.
- **Database:** Co-located PostgreSQL + Redis.
- **Storage:** Local host disk storage.
- **Monitoring:** Periodic health checks via API.

### 👥 Stage 2: 10,000 Users (Production Entry)
- **Topology:** 2 FastAPI application replicas behind Nginx.
- **Database:** Dedicated PostgreSQL instance + 1 Read Replica.
- **Storage:** AWS S3 or MinIO bucket.
- **Redis:** Dedicated Redis instance (combining Cache + Pub/Sub).
- **Monitoring:** Prometheus + Grafana dashboards.

### 🌐 Stage 3: 100,000 Users (Mid-Tier Scale)
- **Topology:** 4 Application nodes behind HAProxy.
- **Database:** PostgreSQL primary + 2 Read Replicas. Partitioned message tables.
- **Storage:** S3 + Cloudflare CDN.
- **Redis:** Redis Sentinel master-replica cluster.
- **Task Queue:** 4 Celery worker nodes.
- **Monitoring:** Alerts tied to Sentry and PagerDuty.

### 🚀 Stage 4: 1,000,000 Users (Global Production)
- **Topology:** Multi-region Kubernetes (EKS/GKE) deployments.
- **Database:** Sharded PostgreSQL cluster (e.g. using Citus Data).
- **Storage:** Multi-region S3 replication with geo-aware CDN routing.
- **Redis:** Clustered Redis (5 shard pairs).
- **Event Bus:** Dedicated Kafka cluster for event fanout.
- **Observability:** Distributed tracing (Jaeger/OTel) with auto-scaling triggers.
