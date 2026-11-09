from __future__ import annotations

import asyncio
import logging

import uvicorn

from app.cameras.camera_manager import CameraManager
from app.core.config import AppConfig, RuntimeSettings, load_config
from app.core.event_dispatcher import EventDispatcher
from app.core.logger import configure_logging
from app.events.event_models import RecognitionFailed
from app.integrations.google_apps_script import GoogleAppsScriptClient
from app.integrations.telegram_service import TelegramNotificationService
from app.recognition.plate_recognizer import (
    RecognitionNotConfigured,
    UnavailablePlateRecognizer,
)
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
    recognizer: UnavailablePlateRecognizer,
    tracker: VehicleTracker,
    dispatcher: EventDispatcher,
    settings: RuntimeSettings,
) -> None:
    while True:
        detections = []
        statuses = {status.camera_id: status for status in camera_manager.statuses()}
        available = {camera_id for camera_id, status in statuses.items() if status.connected}
        for camera_id, frame in camera_manager.get_frames().items():
            if camera_id not in available:
                continue
            try:
                detections.extend(await asyncio.to_thread(recognizer.recognize, frame, camera_id))
            except RecognitionNotConfigured as error:
                logger.warning("%s", error)
                await dispatcher.dispatch(RecognitionFailed(camera_id, str(error)))
                break
            except Exception as error:
                logger.exception("Recognition failed for camera %s", camera_id)
                await dispatcher.dispatch(RecognitionFailed(camera_id, str(error)))
        tracker.confidence_threshold = settings.recognition_confidence_threshold
        tracker.departure_timeout = settings.departure_timeout
        await tracker.update(detections, available)
        await asyncio.sleep(settings.scan_interval)


async def run(config: AppConfig) -> None:
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

    try:
        await asyncio.gather(
            server.serve(),
            _scan_loop(camera_manager, UnavailablePlateRecognizer(), tracker, dispatcher, settings),
            refresh_loop(),
        )
    finally:
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
