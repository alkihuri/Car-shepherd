from __future__ import annotations

from typing import Protocol

import numpy as np


class PlateDetector(Protocol):
    def detect(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Return plate bounding boxes; implementations supply a real detector."""
