#!/usr/bin/env bash
#set -euo pipefail

# Simple post-migrate smoke test using psql. Expects DATABASE_URL env var.
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required. Export it before running this script."
  exit 2
fi

echo "Running post-migrate smoke tests against $DATABASE_URL"

# Check basic connectivity
if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null; then
  echo "Postgres connectivity test failed"
  exit 3
fi

# Check Alembic version table exists
AL_VERSION_COUNT=$(psql "$DATABASE_URL" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version';")
if [[ -z "$AL_VERSION_COUNT" || "$AL_VERSION_COUNT" -eq 0 ]]; then
  echo "alembic_version table not found in public schema"
  exit 4
fi

# Optionally attempt a lightweight query against known table (if exists)
# Example: check users table if present
USERS_COUNT=$(psql "$DATABASE_URL" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users';")
if [[ -n "$USERS_COUNT" && "$USERS_COUNT" -gt 0 ]]; then
  echo "users table exists, running lightweight query"
  if ! psql "$DATABASE_URL" -c "SELECT 1 FROM users LIMIT 1;" >/dev/null 2>&1; then
    echo "Lightweight users query failed (this may be OK if table is empty/unreadable)"
  fi
fi

echo "Post-migrate smoke tests passed"
exit 0
