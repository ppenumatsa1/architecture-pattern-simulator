from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.python.db import session_scope
from shared.python.redis_client import RedisStreams

router = APIRouter()


class SubmissionCreateRequest(BaseModel):
    applicant_id: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "submission-api"}


@router.post("/submissions", status_code=status.HTTP_202_ACCEPTED)
def create_submission(payload: dict[str, Any]) -> dict[str, Any]:
    request = _validate_submission_payload(payload)
    submission_id = f"subm_{uuid4().hex}"
    received_at = datetime.now(tz=timezone.utc)

    try:
        with session_scope() as session:
            session.execute(
                text("""
                    INSERT INTO microservices.submissions (submission_id, status, payload, received_at, created_at, updated_at)
                    VALUES (:submission_id, 'received', CAST(:payload AS JSONB), :received_at, NOW(), NOW())
                    """),
                {
                    "submission_id": submission_id,
                    "payload": json.dumps(
                        {"applicant_id": request.applicant_id, **request.payload}
                    ),
                    "received_at": received_at,
                },
            )

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
                        'submissions-service',
                        'submission_received',
                        :idempotency_key,
                        CAST(:event_data AS JSONB),
                        :occurred_at
                    )
                    ON CONFLICT DO NOTHING
                    """),
                {
                    "submission_id": submission_id,
                    "idempotency_key": f"submission-received:{submission_id}",
                    "event_data": json.dumps(
                        {
                            "applicant_id": request.applicant_id,
                            "status": "received",
                            "source": "submission-api",
                        }
                    ),
                    "occurred_at": received_at,
                },
            )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to persist submission"
        ) from exc

    stream_payload = {
        "submission_id": submission_id,
        "applicant_id": request.applicant_id,
        "payload": request.payload,
        "received_at": received_at.isoformat(),
    }
    try:
        RedisStreams().publish_submission_request(stream_payload)
    except Exception as exc:  # pragma: no cover - network/runtime failure
        raise HTTPException(
            status_code=503, detail="Submission accepted but queue publish failed"
        ) from exc

    return {
        "status": "accepted",
        "submissionId": submission_id,
    }


def _validate_submission_payload(payload: dict[str, Any]) -> SubmissionCreateRequest:
    try:
        if hasattr(SubmissionCreateRequest, "model_validate"):
            return SubmissionCreateRequest.model_validate(payload)
        return SubmissionCreateRequest.parse_obj(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid submission payload: {exc}"
        ) from exc
