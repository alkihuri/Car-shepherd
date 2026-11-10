from pathlib import Path

import easyocr
import numpy as np
from ultralytics import YOLO

from app.tracking.vehicle import Detection

# COCO classes: 2=car, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 5, 7]
MODEL_PATH = Path(__file__).with_name("yolov8n.pt")
# Channel step used to quantize mean color, so similar shades share a fingerprint
COLOR_STEP = 32


class YolloRecognizer:
    def __init__(self):
        self.model = YOLO(str(MODEL_PATH))
        # CPU mode is safer for this project
        self.reader = easyocr.Reader(["en"], gpu=False)

    def _color_fingerprint(self, crop: np.ndarray) -> tuple[tuple[int, int, int], str]:
        # OpenCV images are BGR
        mean_b, mean_g, mean_r = (int(v) for v in crop.reshape(-1, 3).mean(axis=0))
        fingerprint = f"{mean_r // COLOR_STEP}-{mean_g // COLOR_STEP}-{mean_b // COLOR_STEP}"
        return (mean_r, mean_g, mean_b), fingerprint

    def _read_plate(self, crop: np.ndarray) -> tuple[str, float]:
        best_text, best_conf = "", 0.0
        for _bbox, text, confidence in self.reader.readtext(crop, detail=1):
            if confidence > best_conf:
                best_text, best_conf = text.strip().upper(), float(confidence)
        return best_text, best_conf

    def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        results = self.model(image, conf=0.4, verbose=False, classes=VEHICLE_CLASSES)

        detections: list[Detection] = []

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                car_conf = float(box.conf[0].item())
                # Crop without drawing on the shared frame
                car = image[max(y1, 0):y2, max(x1, 0):x2]
                if car.size == 0:
                    continue

                color, fingerprint = self._color_fingerprint(car)
                # Plate is optional: cars without a readable plate keep their fingerprint
                plate, plate_conf = self._read_plate(car)

                detections.append(
                    Detection(
                        plate_number=plate,
                        confidence=plate_conf if plate else car_conf,
                        camera_id=camera_id,
                        color=color,
                        fingerprint=fingerprint,
                        bbox=(x1, y1, x2, y2),
                    )
                )

        return detections
  