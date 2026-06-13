from typing import Any, Awaitable, Callable, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


async def run_transaction(
    session: AsyncSession,
    work: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    if session.in_transaction():
        return await work(*args, **kwargs)
    else:
        async with session.begin():
            return await work(*args, **kwargs)

