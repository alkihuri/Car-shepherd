from __future__ import annotations
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import asyncio
import logging
from datetime import datetime, timezone

import uvicorn

from app.cameras.camera_manager import CameraManager
from app.core.config import AppConfig, RuntimeSettings, load_config, load_recognizer
from app.core.event_dispatcher import EventDispatcher
from app.core.logger import configure_logging
from app.events.event_models import RecognitionFailed
from app.integrations.google_apps_script import GoogleAppsScriptClient
from app.integrations.telegram_service import TelegramNotificationService
from app.recognition.plate_recognizer import PlateRecognizer, RecognitionNotConfigured
from app.tracking.vehicle import Vehicle
from app.tracking.vehicle_tracker import VehicleTracker
from app.web.app import create_app

logger = logging.getLogger(__name__)


def _initial_settings(config: AppConfig) -> RuntimeSettings:
    return RuntimeSettings(
        telegram_enabled=config.telegram.enabled,
        scan_interval=config.tracking.scan_interval,
        departure_timeout=config.tracking.departure_timeout,
        recognition_confidence_threshold=config.recognition.confidence_threshold,
    )


def _restore_current_cars(tracker: VehicleTracker, result: object) -> int:
    rows = result.get("cars", []) if isinstance(result, dict) else []
    if not isinstance(rows, list):
        return 0
    restored = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            first_value = row["first_seen"]
            last_value = row["last_seen"]
            if not isinstance(first_value, str) or not isinstance(last_value, str):
                raise TypeError("car timestamps must be strings")
            first_seen = datetime.fromisoformat(first_value.replace("Z", "+00:00"))
            last_seen = datetime.fromisoformat(last_value.replace("Z", "+00:00"))
            if first_seen.tzinfo is None:
                first_seen = first_seen.replace(tzinfo=timezone.utc)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            tracker.restore(
                Vehicle(
                    plate_number=str(row["plate_number"]),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    camera_ids=set(row.get("camera_ids", []))
                    if isinstance(row.get("camera_ids", []), list)
                    else set(),
                    vehicle_make=row.get("vehicle_make") or None,
                    owner_name=row.get("owner_name") or None,
                    owner_surname=row.get("owner_surname") or None,
                )
            )
            restored += 1
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid current-car row from Google Sheets")
    return restored


async def _refresh_settings(client: GoogleAppsScriptClient, settings: RuntimeSettings) -> None:
    try:
        values = await client.get_config()
        updated = RuntimeSettings.model_validate({**settings.model_dump(), **values})
    except Exception:
        logger.exception("Could not refresh settings from Google Apps Script")
        return
    for name, value in updated:
        setattr(settings, name, value)
    logger.info("Runtime settings refreshed from Google Sheets")


async def _scan_loop(
    camera_manager: CameraManager,
    recognizer: PlateRecognizer,
    tracker: VehicleTracker,
    dispatcher: EventDispatcher,
    settings: RuntimeSettings,
) -> None:
    last_scanned: dict[str, float] = {}
    completed_since_update: set[str] = set()
    failed_since_update: set[str] = set()
    while True:
        loop_time = asyncio.get_running_loop().time()
        statuses = {status.camera_id: status for status in camera_manager.statuses()}
        connected = {camera_id for camera_id, status in statuses.items() if status.connected}
        disconnected = set(last_scanned) - connected
        for camera_id in disconnected:
            last_scanned.pop(camera_id, None)
            completed_since_update.discard(camera_id)
            failed_since_update.discard(camera_id)
        frames = camera_manager.get_frames()
        detections = []
        for camera_id in connected:
            interval = camera_manager.scan_intervals.get(camera_id) or settings.scan_interval
            if loop_time - last_scanned.get(camera_id, float("-inf")) < interval:
                continue
            frame = frames.get(camera_id)
            if frame is None:
                continue
            last_scanned[camera_id] = loop_time
            try:
                camera_detections = await asyncio.to_thread(
                    recognizer.recognize, frame, camera_id
                )
                detections.extend(camera_detections)
                camera_manager.readers[camera_id].set_detections(camera_detections)
                if camera_detections:
                    logger.info(
                        "Recognized %d vehicle(s) on camera %s",
                        len(camera_detections),
                        camera_id,
                    )
                completed_since_update.add(camera_id)
                failed_since_update.discard(camera_id)
            except RecognitionNotConfigured as error:
                logger.warning("%s", error)
                await dispatcher.dispatch(RecognitionFailed(camera_id, str(error)))
                completed_since_update.add(camera_id)
                failed_since_update.add(camera_id)
            except Exception as error:
                logger.exception("Recognition failed for camera %s", camera_id)
                await dispatcher.dispatch(RecognitionFailed(camera_id, str(error)))
                completed_since_update.add(camera_id)
                failed_since_update.add(camera_id)

        tracker.confidence_threshold = settings.recognition_confidence_threshold
        tracker.departure_timeout = settings.departure_timeout
        if detections:
            await tracker.update(detections, set())

        if not connected:
            completed_since_update.clear()
            failed_since_update.clear()
            await tracker.update([], set())
        elif connected <= completed_since_update:
            available = connected - failed_since_update
            await tracker.update([], available)
            completed_since_update.clear()
            failed_since_update.clear()

        await asyncio.sleep(0.5)


async def run(config: AppConfig) -> None:
    recognizer = load_recognizer(config)
    dispatcher = EventDispatcher()
    settings = _initial_settings(config)
    tracker = VehicleTracker(
        dispatcher,
        settings.recognition_confidence_threshold,
        settings.departure_timeout,
    )
    camera_manager = CameraManager(config.cameras)
    google = GoogleAppsScriptClient(config.google)
    telegram = TelegramNotificationService(config, settings)
    if config.google.apps_script_url:
        google.subscribe(dispatcher)
        try:
            count = _restore_current_cars(tracker, await google.get_current_cars())
            logger.info("Restored %d current car(s) from Google Sheets", count)
        except Exception:
            logger.exception("Could not restore current cars from Google Sheets")
    telegram.subscribe(dispatcher)
    await camera_manager.start()
    app = create_app(camera_manager, tracker)
    server = uvicorn.Server(
        uvicorn.Config(app, host=config.server.host, port=config.server.port, log_level="info")
    )

    async def refresh_loop() -> None:
        while True:
            await asyncio.sleep(60)
            if config.google.apps_script_url:
                await _refresh_settings(google, settings)

    workers = [
        asyncio.create_task(
            _scan_loop(camera_manager, recognizer, tracker, dispatcher, settings)
        ),
        asyncio.create_task(refresh_loop()),
    ]
    try:
        await server.serve()
    finally:
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        await camera_manager.stop()
        await google.close()
        await telegram.close()


def main() -> None:
    configure_logging()
    config = load_config()
    logger.info("Starting detailing-centre surveillance application")
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
