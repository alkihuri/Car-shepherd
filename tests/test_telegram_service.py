import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import AppConfig, RuntimeSettings
from app.events.event_models import CarArrived
from app.integrations.telegram_service import TelegramNotificationService
from app.tracking.vehicle import Vehicle


def test_telegram_failures_do_not_log_the_bot_token(caplog) -> None:
    token = "123456789:bot-secret-value"

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("request failed", request=request)

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = TelegramNotificationService(
            AppConfig(telegram={"enabled": True, "bot_token": token}),
            RuntimeSettings(telegram_enabled=True, telegram_chat_id="chat"),
            client,
        )
        await service.on_arrived(
            CarArrived(Vehicle("AB123CD", datetime.now(timezone.utc), datetime.now(timezone.utc)))
        )

    with caplog.at_level(logging.ERROR):
        asyncio.run(run())

    assert "Telegram notification failed (ConnectError)" in caplog.text
    assert token not in caplog.text
