from typing import Any, Awaitable, Callable, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


async def run_transaction(
    session: AsyncSession,
    work: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    async with session.begin():
        return await work(*args, **kwargs)
