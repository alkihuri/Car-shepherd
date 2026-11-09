import re
import easyocr
import numpy as np

from app.tracking.vehicle import Detection

class EasyOCRRecognizer:
    def __init__(self):
        # CPU mode is safer for this project
        self.reader = easyocr.Reader(["en"], gpu=False)

    def _normalize_plate(self, text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
        # keep only common plate-like strings
        if 4 <= len(cleaned) <= 12:
            # Check if the plate matches the Russian format
            if re.match(r'^[A-Z]{1}[0-9]{3}[A-Z]{2}$', cleaned):
                return cleaned 
        return ""

    def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        results = self.reader.readtext(image, detail=1)

        detections: list[Detection] = []

        for bbox, text, confidence in results:
            plate = self._normalize_plate(text)
            if not plate:
                continue

            detections.append(
                Detection(
                    plate_number=plate,
                    confidence=float(confidence),
                    camera_id=camera_id,
                )
            )

        return detections