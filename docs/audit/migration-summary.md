# Migration Summary

This document outlines the database and schema migration processes, rollback steps, and backward-compatibility considerations for ChattingApp.

---

## 1. Alembic Database Migrations

All schema changes are tracked by Alembic. The current sequence runs from the baseline schema through `0013_feed_polish_and_social_features`.

### Migration Commands
- **Upgrade to Head**:
  ```bash
  alembic upgrade head
  ```
- **Rollback Last Migration**:
  ```bash
  alembic downgrade -1
  ```
- **Check Current Version**:
  ```bash
  alembic current
  ```

---

## 2. Backward Compatibility & Data Preservation

To protect existing user profiles, messages, and social media data, the following guidelines are applied:

1. **Non-Nullable Columns with Defaults**:
   - When introducing new columns, they are initialized with a default value (e.g., `ranking_mode = "engagement"`) to avoid breaking existing records.
2. **Deterministic UUID Casts**:
   - Inputs to the database are explicitly cast to `uuid.UUID` objects in Python code (e.g., `uuid.UUID(user_id)`) to prevent `AttributeError: 'str' object has no attribute 'hex'` under strict SQL engines.
3. **Optional JSON payloads**:
   - Event chains and logs store payloads in flexible JSONB/JSON columns, allowing model changes without requiring continuous database schema updates.

---

## 3. Frontend Client Migration

The client-side offline database utilizes browser IndexedDB managed by a versioned schema:
- **Upgrades**: Schema versions are bumped systematically (e.g., from v1 to v2).
- **Data Preservation**: Upgrades are handled inside the `onupgradeneeded` lifecycle handler, preserving existing local outbox items and session states.
