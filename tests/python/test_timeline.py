from datetime import datetime, timezone

from shared.python.timeline import create_timeline_event, create_timeline_payload


def test_create_timeline_event_defaults_and_shape() -> None:
    event = create_timeline_event(" Submission Received ")

    assert event.id.startswith("evt_")
    assert event.type == "submission_received"
    assert event.data == {}
    assert event.timestamp.tzinfo is not None
    assert event.timestamp.utcoffset() == timezone.utc.utcoffset(event.timestamp)


def test_create_timeline_payload_serializes_timestamp_and_custom_values() -> None:
    timestamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    payload = create_timeline_payload(
        event_type="Risk Scored",
        data={"score": 42},
        event_id="evt_custom",
        timestamp=timestamp,
    )

    assert payload == {
        "id": "evt_custom",
        "type": "risk_scored",
        "timestamp": "2026-01-02T03:04:05+00:00",
        "data": {"score": 42},
    }
