from __future__ import annotations

import asyncio
from datetime import datetime

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.cameras.camera_manager import CameraManager
from app.tracking.vehicle_tracker import VehicleTracker


_INDEX = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Detailing Centre Monitor</title>
<style>
body{font:16px sans-serif;margin:2rem;color:#222}h1{margin-top:0}
.cameras{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}
article{border:1px solid #ccc;padding:1rem;border-radius:8px}img{width:100%;background:#222;min-height:120px}
.offline{color:#a00}.online{color:#176b2c}table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:.5rem;border-bottom:1px solid #ddd}
</style></head>
<body><h1>Detailing Centre Monitor</h1><p id="count"></p>
<section id="cameras" class="cameras"></section><h2>Cars on site</h2>
<table><thead><tr><th>Plate</th><th>Make</th><th>Arrived</th><th>Last seen</th><th>Duration</th></tr></thead>
<tbody id="cars"></tbody></table>
<script>
const fmt=v=>v?new Date(v).toLocaleString():"—";
async function refresh(){
 const [cameras,cars]=await Promise.all([fetch('/api/cameras').then(r=>r.json()),fetch('/api/cars').then(r=>r.json())]);
 document.querySelector('#cameras').innerHTML=cameras.map(c=>`<article><h3>${c.name}</h3>
 <p class="${c.connected?'online':'offline'}">${c.connected?'Connected':'Disconnected'} · Last frame: ${fmt(c.last_frame_at)}</p>
 ${c.enabled?`<img src="/video/${encodeURIComponent(c.camera_id)}" alt="${c.name} stream">`:'<p>Disabled</p>'}</article>`).join('');
 document.querySelector('#count').textContent=`${cars.length} car(s) on site`;
 document.querySelector('#cars').innerHTML=cars.map(c=>`<tr><td>${c.plate_number}</td><td>${c.vehicle_make||'—'}</td>
 <td>${fmt(c.first_seen)}</td><td>${fmt(c.last_seen)}</td><td>${Math.max(0,Math.floor((Date.now()-new Date(c.first_seen))/60000))} min</td></tr>`).join('');
}
refresh();setInterval(refresh,5000);
</script></body></html>"""


def create_app(camera_manager: CameraManager, tracker: VehicleTracker) -> FastAPI:
    app = FastAPI(title="Detailing Centre Monitor")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _INDEX

    @app.get("/api/cameras")
    async def cameras() -> list[dict[str, object]]:
        return [
            {
                "camera_id": status.camera_id,
                "name": status.name,
                "connected": status.connected,
                "enabled": status.enabled,
                "last_frame_at": status.last_frame_at.isoformat() if status.last_frame_at else None,
            }
            for status in camera_manager.statuses()
        ]

    @app.get("/api/cars")
    async def cars() -> list[dict[str, object]]:
        now = datetime.now().astimezone()
        return [
            {
                "plate_number": vehicle.plate_number,
                "vehicle_make": vehicle.vehicle_make,
                "owner_name": vehicle.owner_name,
                "owner_surname": vehicle.owner_surname,
                "first_seen": vehicle.first_seen.isoformat(),
                "last_seen": vehicle.last_seen.isoformat(),
                "duration_seconds": int((now - vehicle.first_seen).total_seconds()),
                "camera_ids": sorted(vehicle.camera_ids),
            }
            for vehicle in tracker.current_vehicles
        ]

    @app.get("/video/{camera_id}")
    async def video(camera_id: str) -> StreamingResponse:
        reader = camera_manager.readers.get(camera_id)
        if reader is None or not reader.enabled:
            raise HTTPException(status_code=404, detail="Camera not found or disabled")

        async def frames():
            while True:
                frame = await asyncio.to_thread(reader.get_frame)
                if frame is None:
                    await asyncio.sleep(0.2)
                    continue
                encoded, buffer = cv2.imencode(".jpg", frame)
                if encoded:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                await asyncio.sleep(0.05)

        return StreamingResponse(
            frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    return app
