#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL=${DATABASE_URL:-}
BACKUP_DIR=${BACKUP_DIR:-./backups}

if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL is required. Export it or pass env var."
  exit 2
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_FILE="$BACKUP_DIR/db-backup-$TIMESTAMP.dump"

echo "Backing up database to: $BACKUP_FILE"
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python)
fi

SCRIPT_DIR=$(dirname "$(realpath "$0")")
if [[ -n "$PYTHON_BIN" && -f "$SCRIPT_DIR/db_backup_and_migrate.py" ]]; then
  "$PYTHON_BIN" "$SCRIPT_DIR/db_backup_and_migrate.py" --database-url "$DATABASE_URL" --backup-dir "$BACKUP_DIR"
  exit $?
fi

pg_dump "$DATABASE_URL" --format=custom --file="$BACKUP_FILE"

echo "Running Alembic migrations from backend folder"
SCRIPT_DIR=$(dirname "$(realpath "$0")")
BACKEND_DIR=$(realpath "$SCRIPT_DIR/..")
pushd "$BACKEND_DIR" >/dev/null
python -m alembic upgrade head
popd >/dev/null

echo "Migration succeeded. Backup retained at: $BACKUP_FILE"
