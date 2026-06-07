from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.python.db import session_scope
from shared.python.redis_client import RedisStreams

POLL_BLOCK_MS = int(os.getenv("PERSISTENCE_WORKER_BLOCK_MS", "5000"))


def run() -> None:
    streams = RedisStreams()
    last_id = os.getenv("PERSISTENCE_WORKER_START_ID", "0-0")
    print("persistence-service worker started")

    while True:
        messages = streams.read_risk_results(last_id=last_id, count=20, block_ms=POLL_BLOCK_MS)
        if not messages:
            continue

        for stream_id, payload in messages:
            try:
                process_risk_result(stream_id=stream_id, payload=payload)
                last_id = stream_id
            except Exception as exc:
                print(f"persistence-service failed stream_id={stream_id}: {exc}")
                time.sleep(1)


def process_risk_result(*, stream_id: str, payload: dict[str, Any]) -> None:
    submission_id = str(payload.get("submission_id", "")).strip()
    if not submission_id:
        raise ValueError("submission_id is required")

    score = max(0, min(float(payload.get("score", 0)), 100))
    risk_level = str(payload.get("risk_level", "medium")).strip().lower() or "medium"
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "medium"

    reasons = payload.get("reasons") if isinstance(payload.get("reasons"), list) else []
    model_name = str(payload.get("model_name", "shared-risk-rules")).strip() or "shared-risk-rules"
    model_version = str(payload.get("model_version", "v1")).strip() or "v1"
    evaluated_at = _parse_datetime(payload.get("evaluated_at"))
    status = _map_submission_status(risk_level)

    with session_scope() as session:
        found = session.execute(
            text("""
                SELECT status
                FROM microservices.submissions
                WHERE submission_id = :submission_id
                """),
            {"submission_id": submission_id},
        ).scalar_one_or_none()

        if found is None:
            raise ValueError(f"submission_id {submission_id} not found")

        session.execute(
            text("""
                INSERT INTO microservices.risk_results (
                    submission_id,
                    risk_score,
                    risk_level,
                    model_name,
                    model_version,
                    factors,
                    evaluated_at,
                    created_at
                )
                VALUES (
                    :submission_id,
                    :risk_score,
                    :risk_level,
                    :model_name,
                    :model_version,
                    CAST(:factors AS JSONB),
                    :evaluated_at,
                    NOW()
                )
                ON CONFLICT (submission_id)
                DO UPDATE SET
                    risk_score = EXCLUDED.risk_score,
                    risk_level = EXCLUDED.risk_level,
                    model_name = EXCLUDED.model_name,
                    model_version = EXCLUDED.model_version,
                    factors = EXCLUDED.factors,
                    evaluated_at = EXCLUDED.evaluated_at
                """),
            {
                "submission_id": submission_id,
                "risk_score": score,
                "risk_level": risk_level,
                "model_name": model_name,
                "model_version": model_version,
                "factors": json.dumps(reasons),
                "evaluated_at": evaluated_at,
            },
        )

        session.execute(
            text("""
                UPDATE microservices.submissions
                SET
                    status = :status,
                    submission_version = CASE
                        WHEN status <> :status THEN submission_version + 1
                        ELSE submission_version
                    END,
                    updated_at = NOW()
                WHERE submission_id = :submission_id
                """),
            {"submission_id": submission_id, "status": status},
        )

        if status == "under_review":
            session.execute(
                text("""
                    INSERT INTO microservices.timeline_events (
                        submission_id,
                        producer_service,
                        event_type,
                        idempotency_key,
                        event_data,
                        occurred_at
                    )
                    VALUES (
                        :submission_id,
                        'orchestrator-service',
                        'manual_review_requested',
                        :idempotency_key,
                        CAST(:event_data AS JSONB),
                        :occurred_at
                    )
                        ON CONFLICT DO NOTHING
                    """),
                {
                    "submission_id": submission_id,
                    "idempotency_key": f"persist-manual-review:{stream_id}",
                    "event_data": json.dumps(
                        {
                            "reason": f"{risk_level}_risk",
                            "source_message_id": stream_id,
                        }
                    ),
                    "occurred_at": evaluated_at,
                },
            )
        else:
            session.execute(
                text("""
                    INSERT INTO microservices.timeline_events (
                        submission_id,
                        producer_service,
                        event_type,
                        idempotency_key,
                        event_data,
                        occurred_at
                    )
                    VALUES (
                        :submission_id,
                        'orchestrator-service',
                        'decision_made',
                        :idempotency_key,
                        CAST(:event_data AS JSONB),
                        :occurred_at
                    )
                        ON CONFLICT DO NOTHING
                    """),
                {
                    "submission_id": submission_id,
                    "idempotency_key": f"persist-decision:{stream_id}",
                    "event_data": json.dumps(
                        {
                            "decision": status,
                            "risk_level": risk_level,
                            "source_message_id": stream_id,
                        }
                    ),
                    "occurred_at": evaluated_at,
                },
            )


def _map_submission_status(risk_level: str) -> str:
    if risk_level == "low":
        return "approved"
    if risk_level == "critical":
        return "rejected"
    return "under_review"


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value)
            return (
                parsed.astimezone(timezone.utc)
                if parsed.tzinfo
                else parsed.replace(tzinfo=timezone.utc)
            )
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


if __name__ == "__main__":
    run()
