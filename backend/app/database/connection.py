# backend/app/database/connection.py
import os
import sys
import time
import logging
import ssl
from urllib.parse import urlparse
import certifi
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.observability import DB_QUERY_COUNT, DB_QUERY_LATENCY, DB_QUERY_ERRORS

logger = logging.getLogger(__name__)


def _ssl_mode(database_url: str) -> str | None:
    if database_url.startswith("sqlite"):
        return None
    if settings.DB_SSL_MODE is not None:
        return settings.DB_SSL_MODE.lower()

    host = urlparse(database_url).hostname or ""
    if host not in {"", "localhost", "127.0.0.1"} and not host.endswith(".local"):
        return "require"

    return None


def _build_ssl_context(database_url: str) -> ssl.SSLContext | bool | None:
    mode = _ssl_mode(database_url)
    if mode is None:
        return None
    if mode in {"disable", "false", "0", "no"}:
        return False
    if mode in {"require", "prefer"}:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    if mode in {"verify-full", "verify-ca"}:
        context = ssl.create_default_context(cafile=certifi.where())
        if mode == "verify-ca":
            context.check_hostname = False
        return context

    return None


def _attach_query_listeners(engine) -> None:
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_time = conn.info["query_start_time"].pop(-1)
        elapsed_ms = (time.time() - start_time) * 1000
        DB_QUERY_COUNT.inc()
        DB_QUERY_LATENCY.observe(elapsed_ms / 1000)
        if settings.ENABLE_QUERY_PROFILING:
            logger.info(
                "SQL query executed in %.2fms: %s",
                elapsed_ms,
                statement,
            )
            if elapsed_ms >= settings.QUERY_PROFILING_SLOW_THRESHOLD_MS:
                logger.warning(
                    "Slow SQL query detected (%.2fms): %s",
                    elapsed_ms,
                    statement,
                )

    @event.listens_for(engine.sync_engine, "handle_error")
    def handle_error(exception_context):
        DB_QUERY_ERRORS.inc()
        logger.error(
            "SQL execution error: %s",
            exception_context.original_exception,
        )


def _is_running_under_pytest() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if any("pytest" in str(arg).lower() for arg in sys.argv):
        return True
    return False


def _build_engine(database_url: str):
    connect_args = {
        "timeout": settings.DB_CONNECT_TIMEOUT_SECONDS,
    }
    if "postgresql" in database_url:
        connect_args["statement_cache_size"] = 0
    ssl_context = _build_ssl_context(database_url)
    if ssl_context is not None:
        connect_args["ssl"] = ssl_context

    engine_kwargs = {
        "echo": settings.SQL_ECHO,
        "future": True,
        "pool_pre_ping": False,
        "connect_args": connect_args,
    }

    if _is_running_under_pytest():
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
            }
        )

    engine = create_async_engine(database_url, **engine_kwargs)

    _attach_query_listeners(engine)
    return engine


engine = _build_engine(settings.DATABASE_URL)
read_engine = (
    _build_engine(settings.READ_REPLICA_DATABASE_URL)
    if settings.READ_REPLICA_DATABASE_URL
    else None
)
failover_engine = (
    _build_engine(settings.DB_FAILOVER_URL)
    if settings.DB_FAILOVER_URL
    else None
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
async_read_sessionmaker = async_sessionmaker(
    read_engine or engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# Ensure all models are imported before metadata creation
from app.models import (
    user,
    friend,
    follower,
    block,
    message,
    post,
    post_like,
    post_comment,
    post_repost,
    group,
    group_post,
    group_message,
    group_member,
    chat_settings,
    notification,
    notification_preference,  # New import for notification preferences
    mfa,
    session,
    login_history,
    csrf_token,
    ip_reputation,
    security_audit,
    report,
    report_evidence,
    moderation_action,
    analytics_event,
    ai_moderation,
    ai_smart_reply,
    chat_backup,
    device_sync,
    group_event,
    message_bookmark,
    message_translation,
    scheduled_message,
    shared_media_gallery,
    voice_transcription,
    social_feature,
    platform_expansion,
    enterprise_feature,
    globalization_feature,
)  # noqa: F401


async def init_db():
    """Validate database connectivity without automatic table creation."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Primary database connection validated")

        if read_engine is not None and read_engine is not engine:
            async with read_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Read replica database connection validated")

    except Exception as exc:
        logger.error(
            "Database connection failed: %s: %s. For hosted Postgres providers such as Supabase, "
            "ensure DATABASE_URL is correct, DB_SSL_MODE=require is set, and TCP access to the database host/port is available.",
            type(exc).__name__,
            exc,
        )
        if failover_engine is not None and failover_engine is not engine:
            try:
                async with failover_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.warning(
                    "Primary database unavailable; failover database connection validated.")
            except Exception as failover_exc:
                logger.error(
                    "Failover database connection failed: %s: %s",
                    type(failover_exc).__name__,
                    failover_exc,
                )
        raise RuntimeError("Database connection validation failed") from exc


async def get_db() -> AsyncSession:
    """Dependency for database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session error: {exc}")
            raise
        finally:
            await session.close()


async def get_read_db() -> AsyncSession:
    """Dependency for read-only database sessions."""
    async with async_read_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(f"Read database session error: {exc}")
            raise
        finally:
            await session.close()


AsyncSessionLocal = async_session_maker
AsyncReadSessionLocal = async_read_sessionmaker
get_db_session = get_db
get_read_db_session = get_read_db
