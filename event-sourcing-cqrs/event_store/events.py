from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass(slots=True)
class DomainEvent:
    event_id: UUID
    aggregate_id: UUID
    aggregate_type: str
    event_type: str
    event_data: dict[str, Any]
    event_version: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    created_at: datetime | None = None
    sequence_number: int | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "event_data": self.event_data,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "created_at": self.created_at,
            "sequence_number": self.sequence_number,
        }

    def to_stream_payload(self) -> dict[str, Any]:
        payload = self.to_record()
        payload["event_id"] = str(self.event_id)
        payload["aggregate_id"] = str(self.aggregate_id)
        payload["correlation_id"] = str(self.correlation_id) if self.correlation_id else None
        payload["causation_id"] = str(self.causation_id) if self.causation_id else None
        payload["created_at"] = (
            self.created_at.astimezone(timezone.utc).isoformat()
            if self.created_at
            else datetime.now(tz=timezone.utc).isoformat()
        )
        return payload

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "DomainEvent":
        return cls(
            event_id=_to_uuid(record.get("event_id")),
            aggregate_id=_to_uuid(record.get("aggregate_id")),
            aggregate_type=str(record.get("aggregate_type")),
            event_type=str(record.get("event_type")),
            event_version=record.get("event_version"),
            event_data=_to_dict(record.get("event_data")),
            metadata=_to_dict(record.get("metadata")),
            correlation_id=_to_uuid_or_none(record.get("correlation_id")),
            causation_id=_to_uuid_or_none(record.get("causation_id")),
            created_at=_to_datetime_or_none(record.get("created_at")),
            sequence_number=record.get("sequence_number"),
        )


def new_domain_event(
    *,
    aggregate_id: UUID,
    aggregate_type: str,
    event_type: str,
    event_data: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    correlation_id: UUID | None = None,
    causation_id: UUID | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_id=uuid4(),
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        event_type=event_type,
        event_data=event_data,
        metadata=metadata or {},
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def _to_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _to_uuid_or_none(value: Any) -> UUID | None:
    if value in (None, ""):
        return None
    return _to_uuid(value)


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_datetime_or_none(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
