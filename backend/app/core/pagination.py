import base64
from datetime import datetime
from uuid import UUID
from sqlalchemy import or_, and_
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement


def encode_cursor(timestamp: datetime, item_id: str | UUID) -> str:
    """Encode timestamp and item ID into a base64 string cursor."""
    raw = f"{timestamp.isoformat()}|{str(item_id)}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str | None) -> tuple[datetime, str | None] | None:
    """Decode a cursor string. Supports both base64 tuple cursors and legacy ISO8601 string cursors."""
    if not cursor_str:
        return None
    try:
        # Try decoding base64 tuple
        decoded = base64.b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        if "|" in decoded:
            parts = decoded.split("|")
            return datetime.fromisoformat(parts[0]), parts[1]
    except Exception:
        pass

    # Fallback to legacy ISO8601 string cursor
    try:
        return datetime.fromisoformat(cursor_str), None
    except ValueError:
        return None


def parse_cursor(cursor: str | None, before: datetime | None = None) -> datetime | None:
    """Legacy parser for backward compatibility."""
    if cursor and not before:
        decoded = decode_cursor(cursor)
        if decoded:
            return decoded[0]
    return before


def apply_cursor_filter(
    query: Select,
    timestamp_field: ColumnElement,
    before: datetime | None,
) -> Select:
    """Legacy cursor filter for backward compatibility."""
    if before is None:
        return query
    return query.where(timestamp_field < before)


def apply_tuple_cursor_filter(
    query: Select,
    timestamp_field: ColumnElement,
    id_field: ColumnElement,
    cursor: str | None,
) -> Select:
    """Apply tuple-based (timestamp, id) cursor filtering to a query."""
    decoded = decode_cursor(cursor)
    if not decoded:
        return query

    before_time, before_id = decoded
    if not before_id:
        return query.where(timestamp_field < before_time)

    # Cast before_id to UUID if the column expects a UUID
    import uuid
    try:
        compare_id = uuid.UUID(before_id)
    except ValueError:
        compare_id = before_id

    return query.where(
        or_(
            timestamp_field < before_time,
            and_(timestamp_field == before_time, id_field < compare_id),
        )
    )
