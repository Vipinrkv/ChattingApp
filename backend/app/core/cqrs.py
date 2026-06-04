from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Dict, Type, TypeVar

logger = logging.getLogger(__name__)

CommandHandler = Callable[[Any], Coroutine[Any, Any, Any]]
QueryHandler = Callable[[Any], Coroutine[Any, Any, Any]]

T = TypeVar("T")


class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[Type[Any], CommandHandler] = {}

    def register(self, command_type: Type[Any], handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    async def execute(self, command: Any) -> Any:
        command_type = type(command)
        handler = self._handlers.get(command_type)
        if handler is None:
            message = f"No handler registered for command type {command_type.__name__}"
            logger.error(message)
            raise RuntimeError(message)
        return await handler(command)


class QueryBus:
    def __init__(self) -> None:
        self._handlers: dict[Type[Any], QueryHandler] = {}

    def register(self, query_type: Type[Any], handler: QueryHandler) -> None:
        self._handlers[query_type] = handler

    async def execute(self, query: Any) -> Any:
        query_type = type(query)
        handler = self._handlers.get(query_type)
        if handler is None:
            message = f"No handler registered for query type {query_type.__name__}"
            logger.error(message)
            raise RuntimeError(message)
        return await handler(query)


command_bus = CommandBus()
query_bus = QueryBus()
