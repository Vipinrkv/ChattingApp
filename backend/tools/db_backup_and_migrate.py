#!/usr/bin/env python3
from __future__ import annotations
import argparse
import asyncio
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Final

from redis.asyncio import Redis, from_url

logger = logging.getLogger(__name__)
LOG_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOCK_SCRIPT: Final[str] = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Postgres backup and safely run Alembic migrations with an optional Redis coordination lock."
    )
    parser.add_argument("--database-url", help="Postgres connection URL", default=os.getenv("DATABASE_URL"))
    parser.add_argument(
        "--backup-dir",
        help="Directory where backups are written",
        default=os.getenv("BACKUP_DIR", "./backups"),
    )
    parser.add_argument(
        "--redis-url",
        help="Redis connection URL used for distributed lock coordination",
        default=os.getenv("REDIS_URL", ""),
    )
    parser.add_argument(
        "--lock-key",
        help="Redis key used to serialize backup and migration execution",
        default=os.getenv("DB_MIGRATION_LOCK_KEY", "db_migration_lock"),
    )
    parser.add_argument(
        "--lock-ttl",
        type=int,
        default=int(os.getenv("DB_MIGRATION_LOCK_TTL_SECONDS", "300")),
        help="Lock TTL in seconds",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Skip Redis locking and run backup/migration immediately.",
    )
    return parser.parse_args()


async def acquire_lock(
    redis: Redis,
    key: str,
    token: str,
    ttl_seconds: int,
    retry_delay: float = 0.25,
    max_attempts: int = 20,
) -> bool:
    attempt = 0
    while attempt < max_attempts:
        try:
            if await redis.set(key, token, nx=True, ex=ttl_seconds):
                logger.info("Acquired Redis lock %s", key)
                return True
        except Exception as exc:
            logger.exception("Unable to acquire Redis lock %s: %s", key, exc)
            raise

        attempt += 1
        logger.debug("Retrying Redis lock acquisition (%s/%s)", attempt, max_attempts)
        await asyncio.sleep(retry_delay)

    return False


async def release_lock(redis: Redis, key: str, token: str) -> bool:
    try:
        result = await redis.eval(LOCK_SCRIPT, 1, key, token)
        logger.info("Released Redis lock %s", key)
        return bool(result)
    except Exception as exc:
        logger.exception("Failed to release Redis lock %s: %s", key, exc)
        return False


def create_backup(database_url: str, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_file = backup_dir / f"db-backup-{timestamp}.dump"
    logger.info("Backing up database to: %s", backup_file)
    subprocess.run(
        ["pg_dump", database_url, "--format=custom", f"--file={backup_file}"],
        check=True,
    )
    return backup_file


def run_alembic(backend_dir: Path) -> None:
    logger.info("Running Alembic migrations from: %s", backend_dir)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        check=True,
    )


async def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.database_url:
        logger.error("DATABASE_URL is required. Set the env var or pass --database-url.")
        return 2

    backend_dir = Path(__file__).resolve().parent.parent
    backup_path = Path(args.backup_dir)
    lock_token = None
    redis: Redis | None = None

    if args.redis_url and not args.no_lock:
        redis = from_url(
            args.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable for lock coordination: %s", exc)
            redis = None

    if redis is not None and not args.no_lock:
        lock_token = uuid.uuid4().hex
        acquired = await acquire_lock(redis, args.lock_key, lock_token, args.lock_ttl)
        if not acquired:
            logger.error("Could not acquire distributed lock after retrying. Exiting.")
            return 3

    try:
        backup_file = create_backup(args.database_url, backup_path)
        run_alembic(backend_dir)
        logger.info("Migration succeeded. Backup retained at: %s", backup_file)
        return 0
    except subprocess.CalledProcessError as exc:
        logger.exception("Backup or migration step failed: %s", exc)
        return exc.returncode or 1
    finally:
        if redis is not None and lock_token is not None:
            await release_lock(redis, args.lock_key, lock_token)
            await redis.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
