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
from shared.python.models import Submission
from shared.python.redis_client import RedisStreams
from shared.python.risk_rules import evaluate_risk

POLL_BLOCK_MS = int(os.getenv("RISK_WORKER_BLOCK_MS", "5000"))


def run() -> None:
    streams = RedisStreams()
    last_id = os.getenv("RISK_WORKER_START_ID", "0-0")
    print("risk-service worker started")

    while True:
        messages = streams.read_submission_requests(
            last_id=last_id, count=20, block_ms=POLL_BLOCK_MS
        )
        if not messages:
            continue

        for stream_id, payload in messages:
            try:
                process_submission_request(stream_id=stream_id, payload=payload)
                last_id = stream_id
            except Exception as exc:
                print(f"risk-service failed stream_id={stream_id}: {exc}")
                time.sleep(1)


def process_submission_request(*, stream_id: str, payload: dict[str, Any]) -> None:
    submission_id = str(payload.get("submission_id", "")).strip()
    if not submission_id:
        raise ValueError("submission_id is required")

    raw_payload = payload.get("payload")
    submission_payload = raw_payload if isinstance(raw_payload, dict) else {}
    submission = Submission(id=submission_id, payload=submission_payload)

    risk = evaluate_risk(submission)
    normalized_score = max(0, min(int(risk.score), 100))
    mapped_level = _map_risk_level(normalized_score)
    evaluated_at = datetime.now(tz=timezone.utc)

    with session_scope() as session:
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
                    'risk-service',
                    'risk_scored',
                    :idempotency_key,
                    CAST(:event_data AS JSONB),
                    :occurred_at
                )
                ON CONFLICT DO NOTHING
                """),
            {
                "submission_id": submission_id,
                "idempotency_key": f"risk-scored:{stream_id}",
                "event_data": json.dumps(
                    {
                        "score": normalized_score,
                        "risk_level": mapped_level,
                        "factors": risk.reasons,
                        "source_message_id": stream_id,
                    }
                ),
                "occurred_at": evaluated_at,
            },
        )

        if mapped_level in {"high", "critical"}:
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
                        'risk-service',
                        'manual_review_requested',
                        :idempotency_key,
                        CAST(:event_data AS JSONB),
                        :occurred_at
                    )
                        ON CONFLICT DO NOTHING
                    """),
                {
                    "submission_id": submission_id,
                    "idempotency_key": f"manual-review:{stream_id}",
                    "event_data": json.dumps(
                        {
                            "reason": f"{mapped_level}_risk",
                            "source_message_id": stream_id,
                        }
                    ),
                    "occurred_at": evaluated_at,
                },
            )

        risk_result_payload = {
            "submission_id": submission_id,
            "score": normalized_score,
            "risk_level": mapped_level,
            "reasons": risk.reasons,
            "model_name": "shared-risk-rules",
            "model_version": "v1",
            "source_message_id": stream_id,
            "evaluated_at": evaluated_at.isoformat(),
        }
        session.execute(
            text("""
                INSERT INTO microservices.outbox_messages (
                    stream_name,
                    message_key,
                    payload
                ) VALUES (
                    'risk_results',
                    :message_key,
                    CAST(:payload AS JSONB)
                )
                ON CONFLICT DO NOTHING
                """),
            {
                "message_key": f"risk-result:{submission_id}:{stream_id}",
                "payload": json.dumps(risk_result_payload),
            },
        )


def _map_risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


if __name__ == "__main__":
    run()
