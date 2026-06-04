# Backend tools README

This folder contains helper scripts related to database backups and running Alembic migrations.

Files

- `backup_and_migrate.sh` — Linux/macOS script to create a `pg_dump` backup and run `alembic upgrade head` from the `backend` folder. Usage:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
./backend/tools/backup_and_migrate.sh
```

- `backup_and_migrate.ps1` — PowerShell equivalent for Windows hosts. Usage:

```powershell
.\backend\tools\backup_and_migrate.ps1 -DatabaseUrl 'postgresql://user:pass@host:5432/dbname' -BackupDir './backups'
```

- `db_backup_and_migrate.py` — Python helper for backup and migration with optional Redis coordination and distributed lock support.

Notes

- The scripts create a timestamped custom-format dump file in `./backups` by default.
- Make sure `pg_dump` is available on the host and the `DATABASE_URL` has the correct credentials and network access.
- When `REDIS_URL` is available, `db_backup_and_migrate.py` can coordinate migration execution across hosts using a Redis-based lock.
- A GitHub Actions workflow `.github/workflows/alembic-migrate-staging.yml` was added to run the shell script against a staging DB using the `STAGING_DATABASE_URL` secret.
- A lightweight post-migrate smoke test script is available at `backend/tools/post_migrate_smoke_test.sh` and is run by the CI workflow after migrations complete.
- `lan_websocket_smoke.py` validates LAN/backend health, auth, feed, direct chat WebSocket delivery, group WebSocket delivery, reconnect/offline sync, and chat media upload against a running backend. CI runs `python tools/lan_websocket_smoke.py --ci-guard` as a no-backend coverage-contract guard; use `docs/LAN_WEBSOCKET_SMOKE.md` for full and manual fallback runs.

See also: `docs/ALEMBIC_PRODUCTION.md` for recommended production migration workflow and rollback guidance.
