from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.core.event_dispatcher import EventDispatcher
from app.events.event_models import CarArrived, CarDetected, CarLeft
from app.tracking.vehicle import Detection, Vehicle

logger = logging.getLogger(__name__)

NO_PLATE_LABEL = "нет номера"
NO_PLATE_KEY_PREFIX = "NO_PLATE:"


def _tracking_key(detection: Detection, confidence_threshold: float) -> str | None:
    plate = detection.plate_number.strip().upper()
    if plate and detection.confidence >= confidence_threshold:
        return plate
    if detection.fingerprint:
        return f"{NO_PLATE_KEY_PREFIX}{detection.fingerprint}"
    return None


def _display_plate(key: str) -> str:
    return NO_PLATE_LABEL if key.startswith(NO_PLATE_KEY_PREFIX) else key


class VehicleTracker:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        confidence_threshold: float = 0.8,
        departure_timeout: int = 300,
    ) -> None:
        self.dispatcher = dispatcher
        self.confidence_threshold = confidence_threshold
        self.departure_timeout = departure_timeout
        self._vehicles: dict[str, Vehicle] = {}

    @property
    def current_vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(self._vehicles.values())

    def restore(self, vehicle: Vehicle) -> None:
        plate = vehicle.plate_number.strip().upper()
        if plate:
            vehicle.plate_number = plate
            self._vehicles[plate] = vehicle

    async def update(
        self,
        detections: Iterable[Detection],
        available_camera_ids: set[str],
        now: datetime | None = None,
    ) -> None:
        observed_at = now or datetime.now(timezone.utc)
        accepted: dict[str, set[str]] = {}
        colors: dict[str, tuple[int, int, int]] = {}
        for detection in detections:
            key = _tracking_key(detection, self.confidence_threshold)
            if key is None:
                continue
            accepted.setdefault(key, set()).add(detection.camera_id)
            if detection.color is not None:
                colors[key] = detection.color

        for key, camera_ids in accepted.items():
            vehicle = self._vehicles.get(key)
            if vehicle is None:
                vehicle = Vehicle(
                    plate_number=_display_plate(key),
                    first_seen=observed_at,
                    last_seen=observed_at,
                    camera_ids=set(camera_ids),
                    color=colors.get(key),
                )
                self._vehicles[key] = vehicle
                logger.info("Vehicle arrived: %s", vehicle.plate_number)
                await self.dispatcher.dispatch(CarArrived(vehicle))
            else:
                vehicle.last_seen = observed_at
                vehicle.camera_ids.update(camera_ids)
                if key in colors:
                    vehicle.color = colors[key]
                await self.dispatcher.dispatch(CarDetected(vehicle))

        if not available_camera_ids:
            return

        departure_cutoff = observed_at - timedelta(seconds=self.departure_timeout)
        for key, vehicle in tuple(self._vehicles.items()):
            if key not in accepted and vehicle.last_seen <= departure_cutoff:
                vehicle.status = "left"
                del self._vehicles[key]
                logger.info("Vehicle left: %s", vehicle.plate_number)
                await self.dispatcher.dispatch(CarLeft(vehicle, observed_at))

    async def update_vehicle(
        self,
        plate_number: str,
        *,
        vehicle_make: str | None = None,
        owner_name: str | None = None,
        owner_surname: str | None = None,
    ) -> Vehicle | None:
        vehicle = self._vehicles.get(plate_number.strip().upper())
        if vehicle is None:
            return None
        changed = False
        for field_name, value in (
            ("vehicle_make", vehicle_make),
            ("owner_name", owner_name),
            ("owner_surname", owner_surname),
        ):
            if value is not None and getattr(vehicle, field_name) != value:
                setattr(vehicle, field_name, value)
                changed = True
        if changed:
            from app.events.event_models import CarUpdated

            await self.dispatcher.dispatch(CarUpdated(vehicle))
        return vehicle
