from typing import Literal
from sqlalchemy import asc, desc
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement


def apply_order_by(
    query: Select,
    column: ColumnElement,
    direction: Literal['asc', 'desc'] = 'asc',
) -> Select:
    return query.order_by(asc(column) if direction == 'asc' else desc(column))


def apply_limit(query: Select, limit: int) -> Select:
    return query.limit(limit)
