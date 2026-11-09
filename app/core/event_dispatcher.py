from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Callable
from typing import Any


EventHandler = Callable[[Any], Any]


class EventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[type[Any], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[Any], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def dispatch(self, event: Any) -> None:
        for event_type, handlers in self._handlers.items():
            if isinstance(event, event_type):
                for handler in tuple(handlers):
                    result = handler(event)
                    if inspect.isawaitable(result):
                        await result
