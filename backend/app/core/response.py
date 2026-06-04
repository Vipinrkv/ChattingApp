# backend/app/core/response.py
from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse


def build_success_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    payload = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return JSONResponse(content=payload, status_code=status_code)


def build_error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    code: str = "error",
    details: Any | None = None,
) -> JSONResponse:
    payload = {
        "success": False,
        "error": {"message": message, "code": code},
    }
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(content=payload, status_code=status_code)
