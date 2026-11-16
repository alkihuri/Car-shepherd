import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import cv2
import easyocr
import numpy as np
from ultralytics import YOLO
import asyncio

from app.tracking.vehicle import Detection

logger = logging.getLogger(__name__)


# COCO classes: 2=car, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 5, 7]
MODEL_PATH = Path(__file__).with_name("yolov8n.pt")
# Channel step used to quantize mean color, so similar shades share a fingerprint
COLOR_STEP = 32
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "llava:7b"


@dataclass(frozen=True)
class _DetectedCar:
    bbox: tuple[int, int, int, int]
    confidence: float
    jpeg: bytes
    color: tuple[int, int, int]
    fingerprint: str
    plate: str
    plate_confidence: float


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

    def _detect_cars_sync(self, image: np.ndarray) -> list[_DetectedCar]:
        results = self.model(image, conf=0.4, verbose=False, classes=VEHICLE_CLASSES)

        cars: list[_DetectedCar] = []

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                car_conf = float(box.conf[0].item())
                # Crop without drawing on the shared frame
                car = image[max(y1, 0):y2, max(x1, 0):x2]
                if car.size == 0:
                    continue

                ok, buffer = cv2.imencode(".jpg", car, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                if not ok:
                    raise RuntimeError("Failed to encode car crop to JPEG")

                color, fingerprint = self._color_fingerprint(car)
                # Plate is optional: cars without a readable plate keep their fingerprint
                plate, plate_conf = self._read_plate(car)

                cars.append(
                    _DetectedCar(
                        bbox=(x1, y1, x2, y2),
                        confidence=car_conf,
                        jpeg=buffer.tobytes(),
                        color=color,
                        fingerprint=fingerprint,
                        plate=plate,
                        plate_confidence=plate_conf,
                    )
                )

        return cars

    async def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        """
        Detect vehicles and recognize their make/brand sequentially.
        
        1. Detect all vehicles using YOLO
        2. For each detected car:
           - Extract bbox crop
           - Send to Ollama Vision to detect brand
           - Parse response (expect single word or 'unknown')
        3. Return Detection objects with make field populated
        """
        cars = await asyncio.to_thread(self._detect_cars_sync, image)
        if not cars:
            return []

        detections: list[Detection] = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1200)) as session:
            for car in cars:
                # Extract the car crop from the image using bbox
                car_crop = image[car.bbox[1]:car.bbox[3], car.bbox[0]:car.bbox[2]]
                make = "unknown"
                
                if car_crop.size > 0:
                    try:
                        # Encode crop to JPEG
                        ok, buffer = cv2.imencode(
                            '.jpg', car_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                        )
                        if ok:
                            # Send to Ollama for brand detection
                            make = await self._recognize_make(session, buffer.tobytes())
                    except Exception as e:
                        logger.warning("Failed to recognize car make: %s", e)
                
                # Create Detection with recognized make
                detections.append(
                    Detection(
                        plate_number=car.plate,
                        confidence=car.plate_confidence if car.plate else car.confidence,
                        camera_id=camera_id,
                        color=car.color,
                        fingerprint=car.fingerprint,
                        bbox=car.bbox,
                        make=make,
                    )
                )
        
        return detections

    async def _recognize_make(self, session: aiohttp.ClientSession, image_bytes: bytes) -> str:
        """
        Send image to Ollama and extract car brand/make.
        Returns single word (brand name) or 'unknown'.
        """
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Look at this car photo. Reply with ONLY the car brand name "
                        "(e.g., Toyota, BMW, Ford). If you cannot determine the brand, "
                        "reply with 'unknown'. Reply with one word only, no explanation."
                    ),
                    "images": [base64.b64encode(image_bytes).decode("ascii")],
                }
            ],
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 2048},
        }
        
        try:
            async with session.post(OLLAMA_URL, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
                response.raise_for_status()
                data = await response.json()
                
                raw_answer = data.get("message", {}).get("content", "").strip().lower()
                
                # Extract first word (brand name)
                if raw_answer and raw_answer != "unknown":
                    # Take only the first word, clean punctuation
                    make = raw_answer.split()[0].rstrip('.,!?;:')
                    if make and len(make) > 1:
                        return make
                
                return "unknown"
        except Exception as e:
            logger.warning("Ollama request failed: %s", e)
            return "unknown"
