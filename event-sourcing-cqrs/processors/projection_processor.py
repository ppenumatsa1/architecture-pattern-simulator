from __future__ import annotations

from pathlib import Path
import sys
import time
import json

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BASE_DIR.parent / "shared"
for path in (BASE_DIR, SHARED_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from python.db import session_scope  # noqa: E402
from event_store.repository import EVENT_REPOSITORY  # noqa: E402

PROCESSOR_NAME = "projection_processor"
PARTITION_KEY = "default"
BATCH_SIZE = 200
IDLE_SLEEP_SECONDS = 1


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


def _save_offset(session, sequence_number: int, event_id) -> None:
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


def _apply_submission_projection(session, event) -> None:
    event_type = event.event_type
    event_data = event.event_data

    if event_type == "submission.created":
        stmt = text("""
            INSERT INTO event_sourcing.submission_read_model (
                aggregate_id,
                submission_status,
                applicant_id,
                payload,
                last_event_version,
                submitted_at,
                projection_updated_at
            ) VALUES (
                :aggregate_id,
                'received',
                :applicant_id,
                CAST(:payload AS JSONB),
                :event_version,
                COALESCE(CAST(:submitted_at AS TIMESTAMPTZ), NOW()),
                NOW()
            )
            ON CONFLICT (aggregate_id)
            DO UPDATE SET
                applicant_id = EXCLUDED.applicant_id,
                payload = EXCLUDED.payload,
                last_event_version = EXCLUDED.last_event_version,
                projection_updated_at = NOW()
            WHERE event_sourcing.submission_read_model.last_event_version < EXCLUDED.last_event_version
            """)
        session.execute(
            stmt,
            {
                "aggregate_id": event.aggregate_id,
                "applicant_id": event_data.get("applicant_id", "unknown"),
                "payload": json.dumps(event_data.get("payload", {})),
                "event_version": event.event_version,
                "submitted_at": event_data.get("submitted_at"),
            },
        )
        return

    status_updates = {
        "risk.scoring.started": "under_review",
        "submission.review_requested": "under_review",
        "submission.approved": "approved",
        "submission.rejected": "rejected",
    }
    if event_type in status_updates:
        stmt = text("""
            UPDATE event_sourcing.submission_read_model
            SET submission_status = :submission_status,
                last_event_version = :event_version,
                projection_updated_at = NOW()
            WHERE aggregate_id = :aggregate_id
              AND last_event_version < :event_version
            """)
        session.execute(
            stmt,
            {
                "aggregate_id": event.aggregate_id,
                "submission_status": status_updates[event_type],
                "event_version": event.event_version,
            },
        )


def _apply_risk_projection(session, event) -> None:
    if event.event_type != "risk.scored":
        return

    event_data = event.event_data
    stmt = text("""
        INSERT INTO event_sourcing.risk_summary_read_model (
            aggregate_id,
            risk_score,
            risk_level,
            factors,
            evaluated_at,
            last_event_version,
            projection_updated_at
        ) VALUES (
            :aggregate_id,
            :risk_score,
            :risk_level,
            CAST(:factors AS JSONB),
            COALESCE(CAST(:evaluated_at AS TIMESTAMPTZ), NOW()),
            :event_version,
            NOW()
        )
        ON CONFLICT (aggregate_id)
        DO UPDATE SET
            risk_score = EXCLUDED.risk_score,
            risk_level = EXCLUDED.risk_level,
            factors = EXCLUDED.factors,
            evaluated_at = EXCLUDED.evaluated_at,
            last_event_version = EXCLUDED.last_event_version,
            projection_updated_at = NOW()
        WHERE event_sourcing.risk_summary_read_model.last_event_version < EXCLUDED.last_event_version
        """)
    session.execute(
        stmt,
        {
            "aggregate_id": event.aggregate_id,
            "risk_score": event_data.get("score"),
            "risk_level": event_data.get("risk_level"),
            "factors": json.dumps(event_data.get("factors", [])),
            "evaluated_at": event.created_at.isoformat() if event.created_at else None,
            "event_version": event.event_version,
        },
    )


def _apply_timeline_projection(session, event) -> None:
    stmt = text("""
        INSERT INTO event_sourcing.timeline_events (
            aggregate_id,
            event_id,
            event_type,
            event_data,
            occurred_at,
            created_at
        ) VALUES (
            :aggregate_id,
            :event_id,
            :event_type,
            CAST(:event_data AS JSONB),
            :occurred_at,
            NOW()
        )
        ON CONFLICT (event_id) DO NOTHING
        """)
    session.execute(
        stmt,
        {
            "aggregate_id": event.aggregate_id,
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_data": json.dumps(event.event_data),
            "occurred_at": event.created_at,
        },
    )


def run() -> None:
    print("projection processor started")
    while True:
        with session_scope() as session:
            offset = _load_offset(session)
            events = EVENT_REPOSITORY.read_events_since(
                session,
                after_sequence_number=offset,
                limit=BATCH_SIZE,
            )

            if not events:
                time.sleep(IDLE_SLEEP_SECONDS)
                continue

            for event in events:
                _apply_submission_projection(session, event)
                _apply_risk_projection(session, event)
                _apply_timeline_projection(session, event)
                _save_offset(
                    session, int(event.sequence_number or offset), event.event_id
                )


if __name__ == "__main__":
    run()
