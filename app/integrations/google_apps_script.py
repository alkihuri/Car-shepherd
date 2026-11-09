from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import GoogleConfig
from app.core.event_dispatcher import EventDispatcher
from app.events.event_models import CarArrived, CarDetected, CarLeft
from app.tracking.vehicle import Vehicle

logger = logging.getLogger(__name__)


def _vehicle_payload(vehicle: Vehicle) -> dict[str, Any]:
    return {
        "plate_number": vehicle.plate_number,
        "vehicle_make": vehicle.vehicle_make,
        "owner_name": vehicle.owner_name,
        "owner_surname": vehicle.owner_surname,
        "first_seen": vehicle.first_seen.isoformat(),
        "last_seen": vehicle.last_seen.isoformat(),
        "camera_ids": sorted(vehicle.camera_ids),
        "status": vehicle.status,
    }


class GoogleAppsScriptClient:
    def __init__(self, config: GoogleConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        self._client = client or httpx.AsyncClient(timeout=15)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, action: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.config.apps_script_url:
            raise RuntimeError("Google Apps Script URL is not configured")
        try:
            if payload is None:
                response = await self._client.get(
                    self.config.apps_script_url,
                    params={"action": action, "token": self.config.api_token},
                )
            else:
                response = await self._client.post(
                    self.config.apps_script_url,
                    json={**payload, "action": action, "token": self.config.api_token},
                )
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            logger.error("Google Apps Script %s request failed: %s", action, error)
            raise
        if isinstance(result, dict) and result.get("error"):
            raise RuntimeError(f"Google Apps Script rejected {action}: {result['error']}")
        return result

    async def get_current_cars(self) -> Any:
        return await self._request("get_current_cars")

    async def get_config(self) -> dict[str, Any]:
        result = await self._request("get_config")
        return result.get("config", result) if isinstance(result, dict) else {}

    async def on_arrived(self, event: CarArrived) -> None:
        await self._request(
            "register_arrival",
            {"event_id": event.event_id, "vehicle": _vehicle_payload(event.vehicle)},
        )

    async def on_detected(self, event: CarDetected) -> None:
        await self._request(
            "update_car",
            {"event_id": event.event_id, "vehicle": _vehicle_payload(event.vehicle)},
        )

    async def on_left(self, event: CarLeft) -> None:
        await self._request(
            "register_departure",
            {
                "event_id": event.event_id,
                "vehicle": _vehicle_payload(event.vehicle),
                "left_at": event.left_at.isoformat(),
            },
        )

    def subscribe(self, dispatcher: EventDispatcher) -> None:
        dispatcher.subscribe(CarArrived, self.on_arrived)
        dispatcher.subscribe(CarDetected, self.on_detected)
        dispatcher.subscribe(CarLeft, self.on_left)
