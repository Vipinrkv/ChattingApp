import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "")
os.environ.setdefault("AUDIT_LOGGING_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("REQUIRE_DATABASE_ON_STARTUP", "false")
os.environ.setdefault("ENABLE_TRACE_LOGGING", "false")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")
os.environ.setdefault("SENTRY_DSN", "")

from app.main import app
from app import main as app_main
from app.core import config
from app.core.event_bus import event_bus
from app.database import connection as db_connection
from app.core.redis_cache import redis_cache
from app.websocket.redis_broker import redis_broker
from app.core.task_queue import task_queue
from app.database.connection import AsyncSessionLocal


async def _async_noop() -> None:
    return None


@pytest.fixture(autouse=True, scope="session")
def backend_test_environment():
    """Disable external startup services so backend tests can run in isolation.

    Use a programmatic MonkeyPatch here so this fixture can safely be
    session-scoped (the builtin `monkeypatch` fixture is function-scoped).
    """
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(app_main, "initialize_firebase_app", lambda: None)
        mp.setattr(db_connection, "init_db", _async_noop)
        mp.setattr(redis_cache, "initialize", _async_noop)
        mp.setattr(redis_cache, "shutdown", _async_noop)
        mp.setattr(redis_broker, "initialize", _async_noop)
        mp.setattr(redis_broker, "shutdown", _async_noop)
        mp.setattr(event_bus, "initialize", _async_noop)
        mp.setattr(event_bus, "shutdown", _async_noop)
        mp.setattr(task_queue, "initialize", _async_noop)
        mp.setattr(task_queue, "shutdown", _async_noop)
        mp.setattr(config.settings, "RATE_LIMIT_ENABLED", False)
        mp.setattr(config.settings, "REQUIRE_DATABASE_ON_STARTUP", False)
        mp.setattr(config.settings, "AUDIT_LOGGING_ENABLED", False)
        yield
    finally:
        mp.undo()


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def session():
    """Provide an `AsyncSession` for tests."""
    async with AsyncSessionLocal() as s:
        yield s
