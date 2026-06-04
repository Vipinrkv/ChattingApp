from datetime import datetime
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement


def parse_cursor(cursor: str | None, before: datetime | None = None) -> datetime | None:
    if cursor and not before:
        return datetime.fromisoformat(cursor)
    return before


def apply_cursor_filter(
    query: Select,
    timestamp_field: ColumnElement,
    before: datetime | None,
) -> Select:
    if before is None:
        return query
    return query.where(timestamp_field < before)


def apply_limit(query: Select, limit: int) -> Select:
    return query.limit(limit)
