# ChattingApp - Database Re-evaluation & Audit Report

**Date:** June 11, 2026  
**Target:** PostgreSQL 15+ & Alembic Migration Harness

---

## 1. Schema Inventory & Redundancy Analysis

ChattingApp has 44 defined tables mapping direct/group messaging, feed posts, user relations, security sessions, and moderator auditing.

### 1.1 Social Graph Redundancy Review
- **Followers vs. Friends:** The schema maintains both `followers` (uni-directional follower model) and `friends` (bi-directional relationship). This is mathematically correct: `followers` serves X/Twitter-style interest feeds, while `friends` gates WhatsApp-style direct messaging limits. They are not redundant and are justified.
- **Message Partitions:** Message archive partitioning is configured in migration `0006` to store older messages in partitioned sub-tables based on range constraints. This prevents the primary `messages` table from growing unbounded.

---

## 2. Indexing Strategy & Query Performance

We analyzed query paths for high-frequency direct messaging, feed lookups, and friend verification. The following adjustments are recommended to prevent full-table scans under production loads:

### 2.1 Proposed Composite Indexes

1. **User Relationships (`friends` table):**
   - *Current:* Single indexes on `user_id` and `friend_id`.
   - *Recommendation:* Composite unique index on `(user_id, friend_id, status)` to speed up bi-directional friendship checks.
2. **Followers (`followers` table):**
   - *Current:* Single indexes.
   - *Recommendation:* Composite index on `(follower_id, following_id)`.
3. **Private Messaging (`messages` table):**
   - *Current:* Indexes on `sender_id`, `receiver_id`.
   - *Recommendation:* Composite index on `(sender_id, receiver_id, created_at DESC)` to optimize message history queries.
4. **Sessions (`user_sessions` table):**
   - *Current:* Index on `user_id`, `refresh_token_hash`.
   - *Recommendation:* Composite index on `(user_id, refresh_token_hash, status)` to optimize refresh token rotation checks.

---

## 3. Database Connection Pool & Resource Allocation

Under `backend/app/core/config.py`, the database pool configuration is optimized for concurrent high-load execution:
- **`DB_POOL_SIZE`:** 20 connections (default). Allows 20 concurrent transactions per container instance.
- **`DB_MAX_OVERFLOW`:** 10 connections. Spawns transient connections during sudden spikes.
- **`DB_POOL_TIMEOUT`:** 30 seconds. Prevents request starvation.
- **`pool_pre_ping`:** False. Disabled in tests to save roundtrips; enabled in production to test connection liveness.

---

## 4. Zero-Downtime Migration & Rollback Protocol

To update schemas in production without dropping connections:
1. **Never Rename Columns directly:** Instead, add a new column, dual-write, backfill, and deprecate the old column.
2. **Add Indexes CONCURRENTLY:** In PostgreSQL, always use `CREATE INDEX CONCURRENTLY` in alembic migrations to avoid locking table writes.
3. **Rollback Verification:** Every Alembic migration must have a robust `downgrade()` block.
4. **Single-Head Verification:** Running `alembic heads` must always return exactly one head before applying.
