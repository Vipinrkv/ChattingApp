# Alembic production migration workflow

This document describes a safe workflow for running Alembic migrations in production, including backups, validation, and rollback guidance.

Prerequisites

- `pg_dump` and `psql` available on the host where you run migrations (Postgres client tools).
- A committed Alembic revision in `backend/alembic/versions/`.
- Application instances able to be updated one-at-a-time (rolling/staged restart) or a maintenance window.
- Environment variables configured (see `backend/app/core/config.py`).

Recommended workflow

1. Prepare
   - Ensure migrations are reviewed and test migrations locally against a copy of production schema.
   - Create an explicit Alembic revision with `alembic revision --autogenerate -m "desc"` from the `backend/` folder.

2. Backup the production database (always):

```bash
# Example (Linux/macOS)
export DATABASE_URL="postgresql://user:password@db-host:5432/dbname"
export REDIS_URL="redis://cache-host:6379/0"
python backend/tools/db_backup_and_migrate.py --database-url "$DATABASE_URL" --backup-dir "/backups"
```

If you are running from a host without Redis access, use the existing `pg_dump` and `alembic upgrade head` commands manually.

3. Run migrations from a single control host

```bash
cd backend
python -m alembic upgrade head
```

4. Validate after upgrade

- Run smoke tests and schema checks against the upgraded DB (selects on new/changed tables).
- Inspect application logs and metrics for performance regressions.

5. Rollback plan

- If a migration needs to be reverted quickly, you can:
  - Run `python -m alembic downgrade -1` to roll back one migration (only when the migration is reversible).
  - Restore from `pg_restore` using the backup created earlier if the downgrade is unsafe.

```bash
# Restore (Linux/macOS)
pg_restore --clean --no-owner --dbname "$DATABASE_URL" "/backups/db-backup-2025...dump"
```

Operational tips

- Use transactional DDL patterns where possible.
- Avoid destructive operations without staged deprecation.
- Prefer zero-downtime techniques: add columns, backfill, switch readers, then drop old columns later.

Automation and CI

- Add a CI job that runs migrations against a staging replica and runs the test suite.
- Consider adding a pre-check job that validates `alembic heads` and ensures migrations are linear.

Emergency rollback checklist

1. Stop incoming writes (maintenance page or pause queues).
2. Restore DB from backup using `pg_restore`.
3. Re-deploy the previous application release that matches the restored schema.
4. Re-enable writes and verify.

References

- Alembic docs: https://alembic.sqlalchemy.org/
- PostgreSQL pg_dump/pg_restore: https://www.postgresql.org/docs/current/app-pgdump.html
