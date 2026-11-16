import base64
import json

import cv2
import httpx
import numpy as np

from app.tracking.vehicle import Detection

class OllamaCarRecognizer:
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
            "Look at this single car photo. Reply with ONLY a JSON object, "
            "exactly two keys: {\"model\": \"<brand or None>\", \"color\": \"<color or None>\"}. "
            "One car. No lists. No URLs. No extra fields. No markdown."
        )

    async def _encode_image(self, image: np.ndarray) -> str:
        ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("Failed to encode image to JPEG")
        return base64.b64encode(buffer.tobytes()).decode("ascii")

    async def recognize(self, image: np.ndarray, camera_id: str) -> list[dict]:
        image_b64 = await self._encode_image(image)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": self.prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_ctx": 2048  # or 2048, no more than 4096
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, json=payload)
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
        raw_answer = data.get("message", {}).get("content", "").strip()
        print(f"[OllamaRecognizer] Raw answer: {raw_answer}")
        if not raw_answer:
            return []

        try:
            parsed = json.loads(raw_answer)
        except json.JSONDecodeError:
            print(f"[OllamaRecognizer] Non-JSON answer: {raw_answer[:200]}")
            return []

        items = parsed if isinstance(parsed, list) else [parsed]

        results: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model = item.get("model")
            color = item.get("color")
            if model and color:
                results.append({
                    "model": model,
                    "color": color
                })


        print(f"[OllamaRecognizer] LLM MODEL {self.model} Results: {results}")

        return results