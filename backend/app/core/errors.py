# backend/app/core/errors.py
from typing import Any

from fastapi import status


class APIException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "api_error",
        details: Any | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class BadRequestError(APIException):
    def __init__(self, message: str, code: str = "bad_request", details: Any | None = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, code, details)


class ValidationAppError(BadRequestError):
    def __init__(self, message: str, code: str = "validation_error", details: Any | None = None):
        super().__init__(message, code, details)


class AuthAppError(APIException):
    def __init__(self, message: str, code: str = "auth_error", details: Any | None = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, code, details)


class ForbiddenError(APIException):
    def __init__(self, message: str, code: str = "forbidden", details: Any | None = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, code, details)


class PermissionAppError(ForbiddenError):
    def __init__(self, message: str, code: str = "permission_denied", details: Any | None = None):
        super().__init__(message, code, details)


class NotFoundError(APIException):
    def __init__(self, message: str, code: str = "not_found", details: Any | None = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, code, details)


class NotFoundAppError(NotFoundError):
    def __init__(self, message: str, code: str = "not_found", details: Any | None = None):
        super().__init__(message, code, details)


class ConflictAppError(APIException):
    def __init__(self, message: str, code: str = "conflict", details: Any | None = None):
        super().__init__(message, status.HTTP_409_CONFLICT, code, details)


class RateLimitAppError(APIException):
    def __init__(self, message: str, code: str = "rate_limit_exceeded", details: Any | None = None):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, code, details)


class InternalServerError(APIException):
    def __init__(self, message: str, code: str = "internal_error", details: Any | None = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, code, details)
