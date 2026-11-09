from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.tracking.vehicle import Detection


@dataclass(frozen=True)
class RecognitionResult:
    plate_number: str
    confidence: float


class PlateRecognizer(Protocol):
    def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        """Recognize plates using a configured OCR/model implementation."""


class RecognitionNotConfigured(RuntimeError):
    pass


class UnavailablePlateRecognizer:
    def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        raise RecognitionNotConfigured(
            "No license-plate recognition model is configured; provide a PlateRecognizer plugin"
        )
