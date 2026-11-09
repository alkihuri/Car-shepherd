import asyncio
import json
from datetime import datetime, timezone

import httpx

from app.core.config import GoogleConfig
from app.core.event_dispatcher import EventDispatcher
from app.events.event_models import CarArrived, CarUpdated
from app.integrations.google_apps_script import GoogleAppsScriptClient
from app.tracking.vehicle import Vehicle


def test_arrival_and_manual_updates_are_sent_to_apps_script() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        client = GoogleAppsScriptClient(
            GoogleConfig(apps_script_url="https://example.test/exec", api_token="test-token"),
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        dispatcher = EventDispatcher()
        client.subscribe(dispatcher)
        seen = datetime.now(timezone.utc)
        vehicle = Vehicle("AB123CD", seen, seen, {"front"})
        await dispatcher.dispatch(CarArrived(vehicle))
        vehicle.vehicle_make = "BMW"
        await dispatcher.dispatch(CarUpdated(vehicle))
        await client.close()

    asyncio.run(run())

    assert [request["action"] for request in requests] == ["register_arrival", "update_car"]
    assert all(request["token"] == "test-token" for request in requests)
    assert requests[1]["vehicle"]["vehicle_make"] == "BMW"
