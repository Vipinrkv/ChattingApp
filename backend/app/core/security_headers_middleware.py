# backend/app/core/security_headers_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # HSTS (only on HTTPS in production)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        response.headers["Cross-Origin-Opener-Policy"] = (
            "same-origin" if settings.is_production else "same-origin-allow-popups"
        )
        
        # Ensure auth cookies and CSRF cookies use secure attributes
        self._rewrite_set_cookie_headers(response)

        # Remove server header to avoid information disclosure
        if "server" in response.headers:
            del response.headers["server"]
        
        return response

    def _rewrite_set_cookie_headers(self, response: Response) -> None:
        """Ensure all Set-Cookie headers include secure attributes."""
        if "set-cookie" not in response.headers:
            return

        raw_value = response.headers["set-cookie"]
        if not raw_value:
            return

        segments = [segment.strip() for segment in raw_value.split(";")]
        lower_segments = [segment.lower() for segment in segments]
        cookie_name = segments[0].split("=", 1)[0].strip().lower() if segments else ""

        if "secure" not in lower_segments and settings.COOKIE_SECURE:
            segments.append("Secure")
        if settings.COOKIE_HTTP_ONLY and cookie_name != settings.CSRF_COOKIE_NAME.lower() and "httponly" not in lower_segments:
            segments.append("HttpOnly")
        if not any(segment.lower().startswith("samesite=") for segment in segments):
            segments.append(f"SameSite={settings.COOKIE_SAMESITE}")

        response.headers["set-cookie"] = "; ".join(segments)
