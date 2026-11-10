import base64
import json

import cv2
import httpx
import numpy as np

from app.tracking.vehicle import Detection


class OllamaRecognizer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,          # ✅ исправлено
        model: str = "llava:7b",
        timeout: float = 1200.0,
    ):
        self.model = model
        self.url = f"http://{host}:{port}/api/chat"
        self.timeout = timeout
        self.prompt = ( 
 " Are there any cars? if yes describe each car with make, model, color, plate, and people nearby. Reply ONLY with a JSON array, no markdown, no explanations. Format: [{ plate_number : ABC123 or EMPTY , car_make : Toyota or unknown , car_model : Camry or unknown , people_nearby : false, color : white , people_nearby : false, confidence : 0.0}] confidence is a number between 0.0 and 1.0 reflecting how certain you are about the plate."
)

    def _encode_image(self, image: np.ndarray) -> str:
        ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("Failed to encode image to JPEG")
        return base64.b64encode(buffer.tobytes()).decode("ascii")

    def recognize(self, image: np.ndarray, camera_id: str) -> list[Detection]:
        image_b64 = self._encode_image(image)

        payload = {
            "model": self.model,
            "messages": [                          # ✅ /api/chat формат
                {
                    "role": "user",
                    "content": self.prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "format": "json","options": {
            "temperature": 0.0,
            "num_ctx": 2048  # или 2048, не больше 4096
},
        }

        try:
            response = httpx.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama recognition failed ({exc.response.status_code}): {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Ollama recognition request failed: {exc}"
            ) from exc

        data = response.json()
        raw_answer = data.get("message", {}).get("content", "").strip()   # ✅
        print(f"[OllamaRecognizer] Raw answer: {raw_answer}")
        if not raw_answer:
            return []

        try:
            parsed = json.loads(raw_answer)
        except json.JSONDecodeError:
            print(f"[OllamaRecognizer] Non-JSON answer: {raw_answer[:200]}")
            return []

        items = parsed if isinstance(parsed, list) else [parsed]

        detections: list[Detection] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            plate = item.get("plate_number")
            confidence = item.get("confidence")
            if not plate or confidence is None:
                continue
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            detections.append(
                Detection(
                    plate_number=str(plate).strip().upper(),
                    confidence=confidence,
                    camera_id=camera_id,
                )
            )

        return detections