import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "false"

temp_db_path = Path(tempfile.gettempdir()) / "chat_app_test_temp.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_db_path.as_posix()}"

# Delete test database file before engine/app imports lock it
if temp_db_path.exists():
    try:
        os.remove(temp_db_path)
    except Exception:
        pass

if "DB_SSL_MODE" in os.environ:
    del os.environ["DB_SSL_MODE"]
os.environ["REDIS_URL"] = ""
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = ""
os.environ["AUDIT_LOGGING_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["REQUIRE_DATABASE_ON_STARTUP"] = "false"
os.environ["ENABLE_TRACE_LOGGING"] = "false"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
os.environ["SENTRY_DSN"] = ""

from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.ext.compiler import compiles

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

@compiles(JSON, "sqlite")
def compile_json_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.core import config
# Override environment validation to permit sqlite in test runs
config.Settings.validate_environment = lambda self: None
config.settings.DB_SSL_MODE = "disable"
config.settings.READ_REPLICA_DATABASE_URL = None
config.settings.DB_FAILOVER_URL = None

from app.main import app
from app import main as app_main
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
    """Disable external startup services so backend tests can run in isolation."""
    # Clean up database file from previous failed runs
    from pathlib import Path
    import os
    import tempfile
    db_path = Path(tempfile.gettempdir()) / "chat_app_test_temp.db"
    if db_path.exists():
        try:
            os.remove(db_path)
        except Exception:
            pass

    # Create tables in sqlite
    import asyncio
    from app.database.connection import Base, engine
    
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    asyncio.run(create_tables())

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
        # Clean up database file
        import os
        import tempfile
        from pathlib import Path
        db_path = Path(tempfile.gettempdir()) / "chat_app_test_temp.db"
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def session():
    """Provide an `AsyncSession` for tests."""
    async with AsyncSessionLocal() as s:
        yield s
