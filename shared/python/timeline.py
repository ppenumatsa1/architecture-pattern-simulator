from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import TimelineEvent


def create_timeline_event(
    event_type: str,
    data: dict[str, Any] | None = None,
    *,
    event_id: str | None = None,
    timestamp: datetime | None = None,
) -> TimelineEvent:
    event_ts = timestamp or datetime.now(tz=timezone.utc)
    return TimelineEvent(
        id=event_id or f"evt_{uuid4().hex}",
        type=_normalize_event_type(event_type),
        timestamp=event_ts,
        data=data or {},
    )


def create_timeline_payload(
    event_type: str,
    data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    event = create_timeline_event(event_type=event_type, data=data, **kwargs)
    payload = event.model_dump() if hasattr(event, "model_dump") else event.dict()
    payload["timestamp"] = event.timestamp.astimezone(timezone.utc).isoformat()
    return payload


def _normalize_event_type(event_type: str) -> str:
    return "_".join(event_type.strip().split()).lower()
