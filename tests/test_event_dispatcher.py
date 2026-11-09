import asyncio

from app.core.event_dispatcher import EventDispatcher


def test_dispatcher_calls_sync_and_async_subscribers() -> None:
    dispatcher = EventDispatcher()
    received: list[str] = []

    def sync_handler(event: str) -> None:
        received.append("sync:" + event)

    async def async_handler(event: str) -> None:
        received.append("async:" + event)

    dispatcher.subscribe(str, sync_handler)
    dispatcher.subscribe(str, async_handler)
    asyncio.run(dispatcher.dispatch("arrived"))

    assert received == ["sync:arrived", "async:arrived"]
