from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Vehicle:
    plate_number: str
    first_seen: datetime
    last_seen: datetime
    camera_ids: set[str] = field(default_factory=set)
    vehicle_make: str | None = None
    owner_name: str | None = None
    owner_surname: str | None = None
    status: str = "present"
    color: tuple[int, int, int] | None = None


@dataclass(frozen=True)
class Detection:
    plate_number: str
    confidence: float
    camera_id: str
    color: tuple[int, int, int] | None = None
    fingerprint: str | None = None
    bbox: tuple[int, int, int, int] | None = None
