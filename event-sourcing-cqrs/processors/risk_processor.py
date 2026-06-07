from __future__ import annotations

from pathlib import Path
import sys
import time
from uuid import UUID

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BASE_DIR.parent / "shared"
for path in (BASE_DIR, SHARED_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from python.db import session_scope  # noqa: E402
from python.models import Submission  # noqa: E402
from python.redis_client import RedisStreams  # noqa: E402
from python.risk_rules import evaluate_risk  # noqa: E402
from event_store.events import DomainEvent, new_domain_event  # noqa: E402
from event_store.repository import EVENT_REPOSITORY  # noqa: E402

PROCESSOR_NAME = "risk_processor"
PARTITION_KEY = "default"
POLL_INTERVAL_SECONDS = 1
BATCH_SIZE = 100


def _load_offset(session) -> int:
    stmt = text("""
        SELECT last_sequence_number
        FROM event_sourcing.processor_offsets
        WHERE processor_name = :processor_name
          AND partition_key = :partition_key
        """)
    value = session.execute(
        stmt,
        {"processor_name": PROCESSOR_NAME, "partition_key": PARTITION_KEY},
    ).scalar_one_or_none()
    return int(value or 0)


def _save_offset(session, sequence_number: int, event_id: UUID) -> None:
    stmt = text("""
        INSERT INTO event_sourcing.processor_offsets (
            processor_name,
            partition_key,
            last_sequence_number,
            last_event_id,
            updated_at
        ) VALUES (
            :processor_name,
            :partition_key,
            :last_sequence_number,
            :last_event_id,
            NOW()
        )
        ON CONFLICT (processor_name, partition_key)
        DO UPDATE SET
            last_sequence_number = GREATEST(
                event_sourcing.processor_offsets.last_sequence_number,
                EXCLUDED.last_sequence_number
            ),
            last_event_id = CASE
                WHEN EXCLUDED.last_sequence_number >= event_sourcing.processor_offsets.last_sequence_number
                    THEN EXCLUDED.last_event_id
                ELSE event_sourcing.processor_offsets.last_event_id
            END,
            updated_at = NOW()
        """)
    session.execute(
        stmt,
        {
            "processor_name": PROCESSOR_NAME,
            "partition_key": PARTITION_KEY,
            "last_sequence_number": sequence_number,
            "last_event_id": event_id,
        },
    )


def _has_started_for_causation(session, causation_id: UUID) -> bool:
    stmt = text("""
        SELECT 1
        FROM event_sourcing.event_store
        WHERE aggregate_type = 'submission'
          AND event_type = 'risk.scoring.started'
          AND causation_id = :causation_id
        LIMIT 1
        """)
    return (
        session.execute(stmt, {"causation_id": causation_id}).scalar_one_or_none()
        is not None
    )


def _to_domain_event(payload: dict) -> DomainEvent:
    return DomainEvent.from_record(
        {
            "event_id": payload.get("event_id"),
            "aggregate_id": payload.get("aggregate_id"),
            "aggregate_type": payload.get("aggregate_type"),
            "event_type": payload.get("event_type"),
            "aggregate_version": payload.get(
                "aggregate_version", payload.get("event_version")
            ),
            "schema_version": payload.get("schema_version", 1),
            "event_data": payload.get("event_data", {}),
            "metadata": payload.get("metadata", {}),
            "correlation_id": payload.get("correlation_id"),
            "causation_id": payload.get("causation_id"),
            "created_at": payload.get("created_at"),
            "sequence_number": payload.get("sequence_number"),
        }
    )


def _emit_event(
    session,
    streams: RedisStreams,
    source: DomainEvent,
    event_type: str,
    event_data: dict,
) -> DomainEvent:
    event = new_domain_event(
        aggregate_id=source.aggregate_id,
        aggregate_type=source.aggregate_type,
        event_type=event_type,
        event_data=event_data,
        schema_version=1,
        metadata={
            "producer": PROCESSOR_NAME,
        },
        correlation_id=source.correlation_id or source.event_id,
        causation_id=source.event_id,
    )
    stored = EVENT_REPOSITORY.append(session, event)
    streams.publish_domain_event(stored.to_stream_payload())
    return stored


def run() -> None:
    print("risk processor started")
    streams = RedisStreams()

    while True:
        messages = streams.read_domain_events(
            last_id="0-0", count=BATCH_SIZE, block_ms=1000
        )
        if not messages:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        with session_scope() as session:
            offset = _load_offset(session)

            for _, payload in messages:
                source = _to_domain_event(payload)
                source_sequence = int(source.sequence_number or 0)

                if source_sequence <= offset:
                    continue

                if source.event_type != "submission.created":
                    _save_offset(session, source_sequence, source.event_id)
                    offset = source_sequence
                    continue

                if _has_started_for_causation(session, source.event_id):
                    _save_offset(session, source_sequence, source.event_id)
                    offset = source_sequence
                    continue

                submission_data = source.event_data
                submission = Submission(
                    id=str(source.aggregate_id),
                    payload=submission_data.get("payload", {}),
                )

                _emit_event(
                    session,
                    streams,
                    source,
                    "risk.scoring.started",
                    {
                        "submission_id": str(source.aggregate_id),
                    },
                )

                risk_result = evaluate_risk(submission)
                _emit_event(
                    session,
                    streams,
                    source,
                    "risk.scored",
                    {
                        "submission_id": risk_result.submission_id,
                        "score": risk_result.score,
                        "risk_level": risk_result.risk_level.lower(),
                        "factors": risk_result.reasons,
                    },
                )

                decision_event_type: str | None
                if risk_result.risk_level == "HIGH":
                    decision_event_type = "submission.rejected"
                elif risk_result.risk_level == "MEDIUM":
                    decision_event_type = "submission.review_requested"
                else:
                    decision_event_type = "submission.approved"

                _emit_event(
                    session,
                    streams,
                    source,
                    decision_event_type,
                    {
                        "submission_id": risk_result.submission_id,
                        "decision": decision_event_type.split(".", 1)[1],
                        "score": risk_result.score,
                        "risk_level": risk_result.risk_level.lower(),
                    },
                )

                _save_offset(session, source_sequence, source.event_id)
                offset = source_sequence


if __name__ == "__main__":
    run()
