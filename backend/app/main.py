# backend/app/main.py
import sys
from pathlib import Path
import logging
from contextlib import asynccontextmanager

# Add the parent directory to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import APIException
from app.core.firebase import initialize_firebase_app
from app.core.logging_config import configure_logging
from app.core.middleware import StandardizeResponseMiddleware
from app.core.observability import (
    PrometheusMiddleware,
    OpenTelemetryTracingMiddleware,
    capture_exception,
    initialize_observability,
    metrics_response,
    performance_summary,
)
from app.core.response import build_error_response
from app.core.redis_cache import redis_cache
from app.core.security_middleware import (
    AuditLoggingMiddleware,
    CSRFMiddleware,
    RateLimitingMiddleware,
    RequestSanitizationMiddleware,
)
from app.core.security_headers_middleware import SecurityHeadersMiddleware
from app.core.event_bus import event_bus
from app.core.task_queue import task_queue
from app.database.connection import engine, init_db
from app.routes import (
    user_routes,
    friend_routes,
    follow_routes,
    block_routes,
    chat_routes,
    group_routes,
    post_routes,
    notification_routes,
    analytics_routes,
    social_feature_routes,
    platform_expansion_routes,
    enterprise_feature_routes,
    globalization_feature_routes,
)
from app.routes.admin_routes import router as admin_routes
from app.routes.moderation_routes import router as moderation_routes
from app.routes.ai_moderation_routes import router as ai_moderation_routes
from app.routes.notification_pref_routes import router as notification_pref_routes
from app.routes.security_routes import router as security_routes
from app.routes import user_feed_control_routes, user_list_routes
from app.services.notification_service import NotificationService
from app.websocket import chat_socket, group_socket
from app.websocket.redis_broker import redis_broker


# Lightweight dev CORS middleware to ensure responses always include CORS headers.
# It is intentionally pure ASGI so it can also cover exception paths where
# BaseHTTPMiddleware may not get a normal response object back.
from starlette.types import Message, Receive, Scope, Send


class DevCorsMiddleware:
    def __init__(self, app, allow_credentials: bool = True):
        self.app = app
        self.allow_credentials = allow_credentials

    def _cors_headers(self, scope: Scope) -> list[tuple[bytes, bytes]]:
        request_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        origin = request_headers.get("origin")
        headers = [
            (b"access-control-allow-origin", origin.encode("latin-1") if origin else b"*"),
            (b"access-control-allow-methods", b"GET,POST,PUT,PATCH,DELETE,OPTIONS"),
            (
                b"access-control-allow-headers",
                request_headers.get("access-control-request-headers", "*").encode("latin-1"),
            ),
        ]
        if origin:
            headers.append((b"vary", b"Origin"))
        if self.allow_credentials:
            headers.append((b"access-control-allow-credentials", b"true"))
        return headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cors_headers = self._cors_headers(scope)

        if scope.get("method") == "OPTIONS":
            await send(
                {
                    "type": "http.response.start",
                    "status": 204,
                    "headers": cors_headers,
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        response_started = False

        async def send_with_cors(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                existing = {key.lower() for key, _value in message.get("headers", [])}
                message["headers"] = message.get("headers", []) + [
                    header for header in cors_headers if header[0].lower() not in existing
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_cors)
        except Exception:
            if response_started:
                raise
            logger.exception("Unhandled exception before CORS headers were applied")
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": cors_headers + [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"success":false,"error":{"message":"An internal server error occurred.","code":"error"}}',
                }
            )

configure_logging()
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Validating environment configuration...")
    settings.validate_environment()
    logger.info("Initializing Firebase...")
    initialize_firebase_app()
    logger.info("Initializing database connection...")
    try:
        await init_db()
    except Exception as exc:
        if settings.REQUIRE_DATABASE_ON_STARTUP or settings.is_production:
            raise
        logger.warning(
            "Database unavailable during startup; continuing in development mode. "
            "Database-backed endpoints will fail until the connection is restored. Error: %s",
            exc,
        )
    logger.info("Initializing Redis cache... ")
    try:
        await redis_cache.initialize()
        if redis_cache.enabled:
            logger.info("Redis cache initialized successfully")
        else:
            logger.info("Redis cache disabled; continuing without cache")
    except Exception as exc:
        logger.warning("Redis cache initialization failed: %s", exc)

    logger.info("Initializing Redis broker... ")
    try:
        await redis_broker.initialize()
        if redis_broker.enabled:
            logger.info("Redis broker initialized successfully")
        else:
            logger.info("Redis broker disabled; using in-process WebSocket delivery")
    except Exception as exc:
        logger.warning(
            "Redis broker initialization failed: %s",
            exc,
        )

    logger.info("Initializing event bus... ")
    try:
        await event_bus.initialize()
        logger.info("Event bus backend: %s", event_bus.backend_name)
    except Exception as exc:
        logger.warning("Event bus initialization failed: %s", exc)

    logger.info("Initializing background task queue... ")
    await task_queue.initialize()
    try:
        await task_queue.register_distributed_task(
            "notification.deliver",
            NotificationService._deliver_notification,
        )
    except Exception as exc:
        logger.warning("Failed to register distributed notification task: %s", exc)
    yield

    logger.info("Shutting down background task queue... ")
    await task_queue.shutdown()

    logger.info("Shutting down event bus... ")
    try:
        await event_bus.shutdown()
    except Exception as exc:
        logger.warning("Event bus shutdown failed: %s", exc)

    logger.info("Shutting down Redis broker... ")
    await redis_broker.shutdown()

    logger.info("Shutting down Redis cache... ")
    await redis_cache.shutdown()


app = FastAPI(
    title="Chat & Social Platform API",
    description="Secure backend for Android chat + social + group platform",
    version="1.0.0",
    lifespan=lifespan,
)

initialize_observability(app)

# CORS Configuration (hardened for production)
logger.info("CORS origins: %s", settings.CORS_ORIGINS)
allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"] if settings.is_production else ["*"]
allowed_headers = ["Authorization", "Content-Type", "Accept"] if settings.is_production else ["*"]
allow_origins = settings.CORS_ORIGINS

cors_kwargs = {
    "allow_origins": allow_origins,
    "allow_credentials": True,
    "allow_methods": allowed_methods,
    "allow_headers": allowed_headers,
}

if not settings.is_production:
    cors_kwargs["allow_origin_regex"] = r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+)(:\d+)?$"

app.add_middleware(RequestSanitizationMiddleware)
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OpenTelemetryTracingMiddleware)
app.add_middleware(PrometheusMiddleware)

logger.info("Trusted hosts: %s", settings.ALLOWED_HOSTS)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
else:
    logger.info("Skipping TrustedHostMiddleware in non-production (development/testing).")
# Standard response middleware
app.add_middleware(StandardizeResponseMiddleware)

app.add_middleware(CORSMiddleware, **cors_kwargs)
if not settings.is_production:
    # Ensure dev CORS middleware is active to cover error responses and uploads
    app.add_middleware(DevCorsMiddleware, allow_credentials=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(user_routes.router, prefix="/api/v1/users", tags=["users"])
app.include_router(friend_routes.router, prefix="/api/v1/friends", tags=["friends"])
app.include_router(follow_routes.router, prefix="/api/v1/follows", tags=["follows"])
app.include_router(block_routes.router, prefix="/api/v1/blocks", tags=["blocks"])
app.include_router(chat_routes.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(
    __import__("app.routes.chat_advancement_routes", fromlist=["router"]).router,
    prefix="/api/v1",
    tags=["chat-advancement"],
)
app.include_router(group_routes.router, prefix="/api/v1/groups", tags=["groups"])
app.include_router(post_routes.router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(
    __import__("app.routes.media_routes", fromlist=["router"]).router,
    prefix="/api/v1/media",
    tags=["media"],
)
app.include_router(
    __import__("app.routes.mock_ai_routes", fromlist=["router"]).router,
    prefix="/api/v1/admin",
    tags=["admin"],
)
app.include_router(moderation_routes, prefix="/api/v1/moderation", tags=["moderation"])
app.include_router(admin_routes, prefix="/api/v1/admin", tags=["admin"])
app.include_router(ai_moderation_routes, prefix="/api/v1/ai-moderation", tags=["ai-moderation"])
app.include_router(chat_socket.router)
app.include_router(group_socket.router)
app.include_router(notification_routes.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(analytics_routes.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(social_feature_routes.router, prefix="/api/v1/social", tags=["social"])
app.include_router(platform_expansion_routes.router, prefix="/api/v1/platform", tags=["platform-expansion"])
app.include_router(enterprise_feature_routes.router, prefix="/api/v1/enterprise", tags=["enterprise"])
app.include_router(globalization_feature_routes.router, prefix="/api/v1/globalization", tags=["globalization"])
app.include_router(notification_pref_routes, prefix="/api/v1/notifications/preferences", tags=["notification_preferences"])
app.include_router(security_routes, prefix="/api/v1/security", tags=["security"])
app.include_router(user_feed_control_routes.router)
app.include_router(user_list_routes.router)


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    logger.warning(
        "Typed API exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "status_code": exc.status_code,
            "exception_type": type(exc).__name__,
            "exception_message": exc.message,
            "error_code": exc.code,
            "detail": exc.details,
        },
    )
    return build_error_response(
        message=exc.message,
        status_code=exc.status_code,
        code=exc.code,
        details=exc.details,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    logger.warning(
        "HTTP exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "status_code": exc.status_code,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc.detail),
            "detail": exc.detail,
        },
    )
    return build_error_response(message=str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "errors": exc.errors(),
        },
    )
    return build_error_response(
        message="Request validation failed.",
        status_code=422,
        details=exc.errors(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    logger.warning(
        "Pydantic validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "errors": exc.errors(),
        },
    )
    return build_error_response(
        message="Data validation failed.",
        status_code=422,
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    user_id = getattr(request.state, "user_id", None)
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        },
    )
    capture_exception(exc)
    return build_error_response(
        message="An internal server error occurred.",
        status_code=500,
    )


@app.get("/health", include_in_schema=True)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/details", include_in_schema=True)
async def health_details() -> dict[str, object]:
    checks: dict[str, object] = {"status": "ok", "database": "ok", "redis": "disabled"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("health_database_check_failed", extra={"exception_type": type(exc).__name__, "exception_message": str(exc)})
        checks["status"] = "degraded"
        checks["database"] = "error"

    if redis_cache.enabled and redis_cache.redis:
        try:
            await redis_cache.redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            logger.exception("health_redis_check_failed", extra={"exception_type": type(exc).__name__, "exception_message": str(exc)})
            checks["status"] = "degraded"
            checks["redis"] = "error"

    return checks


@app.head("/health", include_in_schema=False)
async def health_check_head():
    return JSONResponse(content={})


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return metrics_response()


@app.get("/performance", include_in_schema=False)
async def performance() -> dict[str, object]:
    return performance_summary()


@app.get("/", include_in_schema=True)
async def root() -> dict[str, str]:
    return {"message": "Chat & Social Platform API Running"}


@app.head("/", include_in_schema=False)
async def root_head():
    return JSONResponse(content={})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
