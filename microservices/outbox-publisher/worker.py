from __future__ import annotations

import json
import time

from sqlalchemy import text

from shared.python.db import session_scope
from shared.python.redis_client import (
    RISK_RESULTS_STREAM,
    SUBMISSION_REQUESTS_STREAM,
    RedisStreams,
)

BATCH_SIZE = 100
POLL_INTERVAL_SECONDS = 1


def _claim_batch() -> list[dict]:
    with session_scope() as session:
        rows = (
            session.execute(
                text("""
                    UPDATE microservices.outbox_messages o
                    SET attempts = o.attempts + 1,
                        last_attempt_at = NOW()
                    WHERE o.outbox_id IN (
                        SELECT outbox_id
                        FROM microservices.outbox_messages
                        WHERE published_at IS NULL
                          AND available_at <= NOW()
                          AND attempts < max_attempts
                        ORDER BY outbox_id ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT :batch_size
                    )
                    RETURNING outbox_id, stream_name, payload, attempts
                    """),
                {"batch_size": BATCH_SIZE},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def _mark_published(outbox_id: int) -> None:
    with session_scope() as session:
        session.execute(
            text("""
                UPDATE microservices.outbox_messages
                SET published_at = NOW(),
                    last_error = NULL
                WHERE outbox_id = :outbox_id
                """),
            {"outbox_id": outbox_id},
        )


def _mark_failed(outbox_id: int, attempts: int, error: str) -> None:
    backoff_seconds = min(60, max(1, attempts * 2))
    with session_scope() as session:
        session.execute(
            text("""
                UPDATE microservices.outbox_messages
                SET last_error = :last_error,
                    available_at = NOW() + (:backoff_seconds || ' seconds')::interval
                WHERE outbox_id = :outbox_id
                """),
            {
                "outbox_id": outbox_id,
                "last_error": error[:1000],
                "backoff_seconds": backoff_seconds,
            },
        )


def _publish(streams: RedisStreams, stream_name: str, payload: dict) -> None:
    if stream_name == SUBMISSION_REQUESTS_STREAM:
        streams.publish_submission_request(payload)
        return
    if stream_name == RISK_RESULTS_STREAM:
        streams.publish_risk_result(payload)
        return
    raise ValueError(f"Unsupported outbox stream '{stream_name}'")


def run() -> None:
    print("microservices outbox publisher started")
    streams = RedisStreams()

    while True:
        batch = _claim_batch()
        if not batch:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        for row in batch:
            outbox_id = int(row["outbox_id"])
            stream_name = str(row["stream_name"])
            attempts = int(row.get("attempts", 0))
            payload = row.get("payload")
            payload_dict = (
                payload
                if isinstance(payload, dict)
                else json.loads(str(payload or "{}"))
            )

            try:
                _publish(streams, stream_name, payload_dict)
                _mark_published(outbox_id)
            except Exception as exc:  # pragma: no cover - runtime transport guard
                _mark_failed(outbox_id, attempts, str(exc))


if __name__ == "__main__":
    run()
