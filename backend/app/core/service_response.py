from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar('T')

@dataclass
class ServiceResult(Generic[T]):
    success: bool
    data: T | None = None
    error: dict | None = None


def success_result(data: T | None = None) -> ServiceResult[T]:
    return ServiceResult(success=True, data=data)


def error_result(message: str, code: str = 'error', details: Any | None = None) -> ServiceResult[None]:
    return ServiceResult(success=False, error={
        'message': message,
        'code': code,
        'details': details,
    })
