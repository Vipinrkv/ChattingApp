import json
import logging
import time
from html import escape
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.redis_cache import redis_cache
from app.services.csrf_service import csrf_service
from app.database.connection import async_session_maker

logger = logging.getLogger(__name__)
EXCLUDED_PATHS = ("/docs", "/redoc", "/openapi.json", "/static", "/uploads")


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return escape(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(val) for key, val in value.items()}
    return value


class RequestSanitizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.XSS_SANITIZATION_ENABLED:
            return await call_next(request)

        if request.url.path.startswith(EXCLUDED_PATHS):
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return await call_next(request)

        body = await request.body()
        if not body:
            return await call_next(request)

        try:
            payload = json.loads(body.decode("utf-8"))
            sanitized = _sanitize_value(payload)
            request._body = json.dumps(sanitized).encode("utf-8")
        except Exception:
            pass

        return await call_next(request)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._memory_counters: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(EXCLUDED_PATHS) or request.method == "OPTIONS":
            return await call_next(request)

        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}" if not request.url.path.startswith("/api/v1/users/register") else f"auth_rate_limit:{client_ip}"
        limit = settings.AUTH_RATE_LIMIT_REQUESTS if key.startswith("auth_rate_limit") else settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS

        current_count = await self._increment_counter(key, window)
        if current_count > limit:
            logger.warning("Rate limit exceeded for %s (%s requests)", client_ip, current_count)
            return JSONResponse(
                {"success": False, "error": "Too many requests. Please try again later."},
                status_code=429,
            )

        response = await call_next(request)
        return response

    async def _increment_counter(self, key: str, window: int) -> int:
        if redis_cache.enabled:
            try:
                value = await redis_cache.increment(key, ex=window)
                return value
            except Exception:
                logger.exception("Redis rate limit increment failed, falling back to in-memory counter")

        now = time.time()
        history = self._memory_counters.get(key, [])
        history = [timestamp for timestamp in history if timestamp > now - window]
        history.append(now)
        self._memory_counters[key] = history
        return len(history)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.CSRF_ENABLED or request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return await call_next(request)

        exempt_paths = (
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/uploads",
            "/api/v1/security/csrf",
        )

        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            logger.debug(
                "csrf_skipped_bearer_auth",
                extra={"method": request.method, "path": request.url.path},
            )
            return await call_next(request)

        csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)

        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            logger.warning(
                "csrf_rejected",
                extra={
                    "reason": "missing_or_mismatched_token",
                    "method": request.method,
                    "path": request.url.path,
                    "content_type": request.headers.get("content-type", ""),
                    "has_cookie": bool(csrf_cookie),
                    "has_header": bool(csrf_header),
                },
            )
            return JSONResponse(
                {"success": False, "error": "Missing or mismatched CSRF token."},
                status_code=403,
            )

        async with async_session_maker() as db_session:
            valid = await csrf_service.verify_token(
                db_session,
                csrf_header,
                consume=False,
            )
            if not valid:
                logger.warning(
                    "csrf_rejected",
                    extra={
                        "reason": "invalid_or_expired_token",
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    {"success": False, "error": "Invalid or expired CSRF token."},
                    status_code=403,
                )

        return await call_next(request)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "audit",
            extra={
                "client_ip": request.client.host if request.client else "unknown",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
        return response
