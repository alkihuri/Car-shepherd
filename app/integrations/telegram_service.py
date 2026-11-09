from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.core.config import AppConfig, RuntimeSettings
from app.core.event_dispatcher import EventDispatcher
from app.events.event_models import CarArrived, CarLeft

logger = logging.getLogger(__name__)


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y %H:%M")


class TelegramNotificationService:
    def __init__(
        self,
        app_config: AppConfig,
        settings: RuntimeSettings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app_config = app_config
        self.settings = settings
        self._client = client or httpx.AsyncClient(timeout=10)
        self._owns_client = client is None

    def subscribe(self, dispatcher: EventDispatcher) -> None:
        dispatcher.subscribe(CarArrived, self.on_arrived)
        dispatcher.subscribe(CarLeft, self.on_left)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _send(self, text: str) -> None:
        if not self.settings.telegram_enabled or not self.app_config.telegram.bot_token:
            return
        if not self.settings.telegram_chat_id:
            logger.warning("Telegram is enabled but telegram_chat_id is empty")
            return
        url = f"https://api.telegram.org/bot{self.app_config.telegram.bot_token}/sendMessage"
        try:
            response = await self._client.post(
                url,
                json={"chat_id": self.settings.telegram_chat_id, "text": text},
            )
            response.raise_for_status()
            if response.json().get("ok") is not True:
                raise RuntimeError("Telegram API returned an unsuccessful response")
        except (httpx.HTTPError, ValueError, RuntimeError) as error:
            logger.error("Telegram notification failed (%s)", type(error).__name__)

    async def on_arrived(self, event: CarArrived) -> None:
        if not self.settings.notify_on_arrival:
            return
        vehicle = event.vehicle
        await self._send(
            "🚘 Новый автомобиль в детейлинг-центре\n\n"
            f"Номер: {vehicle.plate_number}\n"
            f"Марка: {vehicle.vehicle_make or 'неизвестна'}\n"
            f"Время прибытия: {_format_time(vehicle.first_seen)}"
        )

    async def on_left(self, event: CarLeft) -> None:
        if not self.settings.notify_on_departure:
            return
        vehicle = event.vehicle
        duration = max(0, int((event.left_at - vehicle.first_seen).total_seconds()))
        hours, remainder = divmod(duration, 3600)
        minutes = remainder // 60
        await self._send(
            "🚗 Автомобиль покинул детейлинг-центр\n\n"
            f"Номер: {vehicle.plate_number}\n"
            f"Марка: {vehicle.vehicle_make or 'неизвестна'}\n"
            f"Время прибытия: {_format_time(vehicle.first_seen)}\n"
            f"Время выезда: {_format_time(event.left_at)}\n"
            f"Время нахождения: {hours} ч {minutes} мин"
        )
