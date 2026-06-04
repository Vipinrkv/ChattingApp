# backend/app/core/middleware.py
import json
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)
EXCLUDED_PATHS = ("/docs", "/redoc", "/openapi.json", "/static", "/uploads")


class StandardizeResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path.startswith(EXCLUDED_PATHS):
            return response

        if isinstance(response, JSONResponse) and response.status_code < 400:
            try:
                body = response.body
                if not body:
                    return response
                payload = json.loads(body.decode() if isinstance(body, (bytes, bytearray)) else body)
            except Exception as exc:
                logger.debug("Skipping response wrapping due to non-JSON body: %s", exc)
                return response

            if isinstance(payload, dict) and payload.get("success") is not None:
                return response

            return JSONResponse(
                {"success": True, "data": payload},
                status_code=response.status_code,
            )

        return response
