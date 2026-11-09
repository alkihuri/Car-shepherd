import asyncio
from datetime import datetime, timedelta, timezone

from app.core.event_dispatcher import EventDispatcher
from app.events.event_models import CarArrived, CarDetected, CarLeft
from app.tracking.vehicle import Detection, Vehicle
from app.tracking.vehicle_tracker import VehicleTracker


def test_tracker_merges_cameras_and_suppresses_duplicate_arrivals() -> None:
    dispatcher = EventDispatcher()
    events: list[object] = []
    for event_type in (CarArrived, CarDetected, CarLeft):
        dispatcher.subscribe(event_type, events.append)
    tracker = VehicleTracker(dispatcher, confidence_threshold=0.8)
    now = datetime.now(timezone.utc)

    asyncio.run(
        tracker.update(
            [
                Detection("ab123cd", 0.95, "north"),
                Detection("AB123CD", 0.91, "south"),
                Detection("LOW123", 0.2, "north"),
            ],
            {"north", "south"},
            now,
        )
    )
    asyncio.run(tracker.update([Detection("AB123CD", 0.99, "west")], {"west"}, now + timedelta(seconds=30)))

    assert [type(event) for event in events] == [CarArrived, CarDetected]
    assert len(tracker.current_vehicles) == 1
    assert tracker.current_vehicles[0].camera_ids == {"north", "south", "west"}
    assert tracker.current_vehicles[0].last_seen == now + timedelta(seconds=30)


def test_tracker_pauses_departures_when_all_cameras_are_unavailable() -> None:
    dispatcher = EventDispatcher()
    events: list[object] = []
    dispatcher.subscribe(CarArrived, events.append)
    dispatcher.subscribe(CarLeft, events.append)
    tracker = VehicleTracker(dispatcher, departure_timeout=10)
    now = datetime.now(timezone.utc)
    asyncio.run(tracker.update([Detection("AB123CD", 0.95, "north")], {"north"}, now))

    asyncio.run(tracker.update([], set(), now + timedelta(minutes=5)))
    assert len(tracker.current_vehicles) == 1
    assert not any(isinstance(event, CarLeft) for event in events)

    asyncio.run(tracker.update([], {"north"}, now + timedelta(minutes=5)))
    assert tracker.current_vehicles == ()
    assert sum(isinstance(event, CarLeft) for event in events) == 1


def test_tracker_can_restore_current_vehicle_without_emitting_arrival() -> None:
    dispatcher = EventDispatcher()
    events: list[object] = []
    dispatcher.subscribe(CarArrived, events.append)
    tracker = VehicleTracker(dispatcher)
    seen = datetime.now(timezone.utc)
    tracker.restore(Vehicle("ab123cd", seen, seen, {"front"}))

    asyncio.run(tracker.update([Detection("AB123CD", 0.9, "front")], {"front"}, seen))

    assert tracker.current_vehicles[0].plate_number == "AB123CD"
    assert not events
