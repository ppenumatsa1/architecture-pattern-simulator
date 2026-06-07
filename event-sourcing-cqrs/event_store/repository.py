from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .events import DomainEvent
from .upcasters import upcast


class EventStoreConcurrencyError(RuntimeError):
    pass


class EventRepository:
    def append(
        self,
        session: Session,
        event: DomainEvent,
        *,
        expected_aggregate_version: int | None = None,
    ) -> DomainEvent:
        current_version = self.get_current_aggregate_version(
            session, event.aggregate_type, event.aggregate_id
        )
        if (
            expected_aggregate_version is not None
            and current_version != expected_aggregate_version
        ):
            raise EventStoreConcurrencyError(
                f"Concurrency conflict for {event.aggregate_type}/{event.aggregate_id}: "
                f"expected={expected_aggregate_version}, current={current_version}"
            )

        event.aggregate_version = event.aggregate_version or (current_version + 1)
        if event.aggregate_version <= current_version:
            raise EventStoreConcurrencyError(
                f"Invalid aggregate version {event.aggregate_version} for current version {current_version}"
            )

        metadata = dict(event.metadata or {})
        schema_version = int(event.schema_version or 1)

        insert_stmt = text("""
            INSERT INTO event_sourcing.event_store (
                event_id,
                aggregate_id,
                aggregate_type,
                event_type,
                aggregate_version,
                schema_version,
                event_data,
                metadata,
                correlation_id,
                causation_id
            ) VALUES (
                :event_id,
                :aggregate_id,
                :aggregate_type,
                :event_type,
                :aggregate_version,
                :schema_version,
                CAST(:event_data AS JSONB),
                CAST(:metadata AS JSONB),
                :correlation_id,
                :causation_id
            )
            RETURNING sequence_number, created_at
            """)

        try:
            result = session.execute(
                insert_stmt,
                {
                    "event_id": event.event_id,
                    "aggregate_id": event.aggregate_id,
                    "aggregate_type": event.aggregate_type,
                    "event_type": event.event_type,
                    "aggregate_version": event.aggregate_version,
                    "schema_version": schema_version,
                    "event_data": json.dumps(event.event_data),
                    "metadata": json.dumps(metadata),
                    "correlation_id": event.correlation_id,
                    "causation_id": event.causation_id,
                },
            ).one()
        except IntegrityError as exc:
            raise EventStoreConcurrencyError(
                "Could not append event due to integrity constraint"
            ) from exc

        event.metadata = metadata
        event.sequence_number = int(result.sequence_number)
        event.created_at = result.created_at
        return event

    def get_current_aggregate_version(
        self, session: Session, aggregate_type: str, aggregate_id: Any
    ) -> int:
        stmt = text("""
            SELECT COALESCE(MAX(aggregate_version), 0) AS version
            FROM event_sourcing.event_store
            WHERE aggregate_type = :aggregate_type
              AND aggregate_id = :aggregate_id
            """)
        value = session.execute(
            stmt,
            {"aggregate_type": aggregate_type, "aggregate_id": aggregate_id},
        ).scalar_one()
        return int(value)

    def read_aggregate_events(
        self,
        session: Session,
        *,
        aggregate_type: str,
        aggregate_id: Any,
        from_version: int = 1,
    ) -> list[DomainEvent]:
        stmt = text("""
            SELECT
                event_id,
                aggregate_id,
                aggregate_type,
                event_type,
                aggregate_version,
                schema_version,
                event_data,
                metadata,
                correlation_id,
                causation_id,
                created_at,
                sequence_number
            FROM event_sourcing.event_store
            WHERE aggregate_type = :aggregate_type
              AND aggregate_id = :aggregate_id
              AND aggregate_version >= :from_version
            ORDER BY sequence_number ASC
            """)

        rows = session.execute(
            stmt,
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "from_version": from_version,
            },
        ).mappings()
        return [self._row_to_event(dict(row)) for row in rows]

    def read_events_since(
        self,
        session: Session,
        *,
        after_sequence_number: int,
        limit: int = 100,
    ) -> list[DomainEvent]:
        stmt = text("""
            SELECT
                event_id,
                aggregate_id,
                aggregate_type,
                event_type,
                aggregate_version,
                schema_version,
                event_data,
                metadata,
                correlation_id,
                causation_id,
                created_at,
                sequence_number
            FROM event_sourcing.event_store
            WHERE sequence_number > :after_sequence_number
            ORDER BY sequence_number ASC
            LIMIT :limit
            """)
        rows = session.execute(
            stmt,
            {"after_sequence_number": after_sequence_number, "limit": limit},
        ).mappings()
        return [self._row_to_event(dict(row)) for row in rows]

    @staticmethod
    def _row_to_event(row: dict[str, Any]) -> DomainEvent:
        metadata = row.get("metadata") or {}
        schema_version = int(
            row.get("schema_version")
            or (metadata.get("schema_version", 1) if isinstance(metadata, dict) else 1)
        )
        upcasted = upcast(
            {
                "event_type": row["event_type"],
                "event_data": row.get("event_data") or {},
                "metadata": metadata,
                "schema_version": schema_version,
            }
        )
        row["event_data"] = upcasted.get("event_data") or {}
        row["metadata"] = upcasted.get("metadata") or metadata
        row["schema_version"] = int(upcasted.get("schema_version") or schema_version)
        return DomainEvent.from_record(row)


EVENT_REPOSITORY = EventRepository()
