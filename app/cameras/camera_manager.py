from __future__ import annotations

import asyncio

from app.cameras.stream_reader import CameraStatus, StreamReader
from app.core.config import CameraConfig


class CameraManager:
    def __init__(self, cameras: list[CameraConfig]) -> None:
        self.scan_intervals = {camera.id: camera.scan_interval for camera in cameras}
        self.readers = {
            camera.id: StreamReader(camera.id, camera.name, camera.stream_url, camera.enabled)
            for camera in cameras
        }

    async def start(self) -> None:
        await asyncio.gather(*(asyncio.to_thread(reader.start) for reader in self.readers.values()))

    async def stop(self) -> None:
        await asyncio.gather(*(asyncio.to_thread(reader.stop) for reader in self.readers.values()))

    def get_frames(self) -> dict[str, object]:
        return {
            camera_id: frame
            for camera_id, reader in self.readers.items()
            if reader.status().connected and (frame := reader.get_frame()) is not None
        }

    def statuses(self) -> list[CameraStatus]:
        return [reader.status() for reader in self.readers.values()]
