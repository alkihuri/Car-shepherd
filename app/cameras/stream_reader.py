from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraStatus:
    camera_id: str
    name: str
    connected: bool
    enabled: bool
    last_frame_at: datetime | None


class StreamReader:
    def __init__(self, camera_id: str, name: str, stream_url: str, enabled: bool = True) -> None:
        self.camera_id = camera_id
        self.name = name
        self.stream_url = stream_url
        self.enabled = enabled
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._last_frame_at: datetime | None = None
        self._connected = False
        self._thread: threading.Thread | None = None
        self._detections: list = []

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._read_loop, name=f"camera-{self.camera_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def set_detections(self, detections: list) -> None:
        with self._lock:
            self._detections = list(detections)

    def get_detections(self) -> list:
        with self._lock:
            return list(self._detections)

    def status(self) -> CameraStatus:
        with self._lock:
            return CameraStatus(
                self.camera_id,
                self.name,
                self._connected,
                self.enabled,
                self._last_frame_at,
            )

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            if not self.stream_url:
                logger.error("Camera %s has no configured stream URL", self.camera_id)
                self._stop.wait(5)
                continue
            try:
                capture = cv2.VideoCapture(
                    self.stream_url,
                    cv2.CAP_FFMPEG,
                    [
                        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                        5000,
                        cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                        5000,
                    ],
                )
            except (TypeError, cv2.error):
                capture = cv2.VideoCapture(self.stream_url)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not capture.isOpened():
                with self._lock:
                    self._connected = False
                logger.warning("Unable to connect to camera %s", self.camera_id)
                capture.release()
                self._stop.wait(5)
                continue
            logger.info("Connected to camera %s", self.camera_id)
            try:
                while not self._stop.is_set():
                    success, frame = capture.read()
                    if not success or frame is None:
                        with self._lock:
                            self._connected = False
                        logger.warning("Lost stream from camera %s", self.camera_id)
                        break
                    with self._lock:
                        self._frame = frame
                        self._last_frame_at = datetime.now(timezone.utc)
                        self._connected = True
                    time.sleep(0.01)
            finally:
                capture.release()
        with self._lock:
            self._connected = False
