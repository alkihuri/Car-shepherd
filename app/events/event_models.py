from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from app.tracking.vehicle import Vehicle


@dataclass(frozen=True)
class CarArrived:
    vehicle: Vehicle
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class CarDetected:
    vehicle: Vehicle
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class CarLeft:
    vehicle: Vehicle
    left_at: datetime
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class CarUpdated:
    vehicle: Vehicle
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class RecognitionFailed:
    camera_id: str
    message: str
