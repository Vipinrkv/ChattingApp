from typing import Any


class PermissionError(Exception):
    def __init__(self, message: str, code: str = 'permission_denied', details: Any | None = None):
        super().__init__(message)
        self.code = code
        self.details = details


def ensure_not_self(user_id: Any, target_id: Any, message: str = 'Operation not allowed with self') -> None:
    if user_id == target_id:
        raise PermissionError(message)


def ensure_owner(user_id: Any, resource_owner_id: Any, message: str = 'User is not allowed to access this resource') -> None:
    if user_id != resource_owner_id:
        raise PermissionError(message)
