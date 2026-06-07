from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.python.models import Submission
from shared.python.risk_rules import evaluate_risk
from shared.python.timeline import create_timeline_payload
from shared.python.db import session_scope

SSE_POLL_INTERVAL_SECONDS = 1.0


class SubmissionCreateRequest(BaseModel):
    applicant_id: str = Field(..., min_length=1, alias="applicantId")
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"
        allow_population_by_field_name = True


def create_submission(payload: dict[str, Any]) -> dict[str, Any]:
    request = _validate_submission_payload(payload)
    timeline_records: list[dict[str, Any]] = []

    try:
        with session_scope() as session:
            created_submission = (
                session.execute(
                    text("""
                    INSERT INTO monolith.submissions (applicant_id, status, payload)
                    VALUES (:applicant_id, 'under_review', CAST(:payload AS JSONB))
                    RETURNING submission_id, status, submitted_at
                    """),
                    {
                        "applicant_id": request.applicant_id,
                        "payload": json.dumps(request.payload),
                    },
                )
                .mappings()
                .one()
            )

            submission_id = int(created_submission["submission_id"])
            risk = evaluate_risk(
                Submission(id=str(submission_id), payload=request.payload)
            )
            bounded_score = _bound_risk_score(risk.score)
            mapped_level = _map_risk_level(risk.score)
            computed_state = _compute_state(mapped_level)

            session.execute(
                text("""
                    INSERT INTO monolith.risk_results (submission_id, risk_score, risk_level, factors)
                    VALUES (:submission_id, :risk_score, :risk_level, CAST(:factors AS JSONB))
                    """),
                {
                    "submission_id": submission_id,
                    "risk_score": Decimal(str(bounded_score)),
                    "risk_level": mapped_level,
                    "factors": json.dumps(risk.reasons),
                },
            )

            session.execute(
                text("""
                    UPDATE monolith.submissions
                    SET status = :status, updated_at = NOW()
                    WHERE submission_id = :submission_id
                    """),
                {"status": computed_state, "submission_id": submission_id},
            )

            timeline_records.extend(
                [
                    _build_timeline_row(
                        submission_id=submission_id,
                        event_type="submission_received",
                        data={
                            "applicant_id": request.applicant_id,
                            "status": "under_review",
                        },
                    ),
                    _build_timeline_row(
                        submission_id=submission_id,
                        event_type="risk_scored",
                        data={
                            "score": bounded_score,
                            "risk_level": mapped_level,
                            "factors": risk.reasons,
                        },
                    ),
                ]
            )
            if computed_state == "under_review":
                timeline_records.append(
                    _build_timeline_row(
                        submission_id=submission_id,
                        event_type="manual_review_requested",
                        data={"reason": f"{mapped_level}_risk"},
                    )
                )
            else:
                timeline_records.append(
                    _build_timeline_row(
                        submission_id=submission_id,
                        event_type="decision_made",
                        data={"decision": computed_state},
                    )
                )

            for record in timeline_records:
                session.execute(
                    text("""
                        INSERT INTO monolith.timeline_events (
                            submission_id, event_type, event_data, occurred_at
                        )
                        VALUES (
                            :submission_id,
                            :event_type,
                            CAST(:event_data AS JSONB),
                            :occurred_at
                        )
                        """),
                    record,
                )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to persist submission"
        ) from exc

    return {
        "submission_id": submission_id,
        "state": computed_state,
        "risk": {
            "score": bounded_score,
            "level": mapped_level,
            "factors": risk.reasons,
        },
    }


def _bound_risk_score(score: float | int) -> float:
    return max(0.0, min(100.0, float(score)))


def get_submission(submission_id: int) -> dict[str, Any]:
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text("""
                    SELECT
                        s.submission_id,
                        s.applicant_id,
                        s.status,
                        s.payload,
                        s.submitted_at,
                        rr.risk_score,
                        rr.risk_level,
                        rr.factors,
                        rr.evaluated_at
                    FROM monolith.submissions s
                    LEFT JOIN monolith.risk_results rr
                      ON rr.submission_id = s.submission_id
                    WHERE s.submission_id = :submission_id
                    """),
                    {"submission_id": submission_id},
                )
                .mappings()
                .one_or_none()
            )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to read submission"
        ) from exc

    if not row:
        raise HTTPException(
            status_code=404, detail=f"Submission {submission_id} not found"
        )

    return {
        "submission_id": row["submission_id"],
        "applicant_id": row["applicant_id"],
        "state": row["status"],
        "payload": row["payload"] or {},
        "submitted_at": _isoformat(row["submitted_at"]),
        "risk": {
            "score": (
                float(row["risk_score"]) if row["risk_score"] is not None else None
            ),
            "level": row["risk_level"],
            "factors": row["factors"] or [],
            "evaluated_at": _isoformat(row["evaluated_at"]),
        },
    }


def list_submissions(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text("""
                    SELECT
                        s.submission_id,
                        s.applicant_id,
                        s.status,
                        s.submitted_at,
                        rr.risk_score,
                        rr.risk_level
                    FROM monolith.submissions s
                    LEFT JOIN monolith.risk_results rr
                      ON rr.submission_id = s.submission_id
                    ORDER BY s.submitted_at DESC
                    LIMIT :limit OFFSET :offset
                    """),
                    {"limit": limit, "offset": offset},
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to list submissions"
        ) from exc

    return {
        "items": [
            {
                "submission_id": row["submission_id"],
                "applicant_id": row["applicant_id"],
                "state": row["status"],
                "submitted_at": _isoformat(row["submitted_at"]),
                "risk_score": (
                    float(row["risk_score"]) if row["risk_score"] is not None else None
                ),
                "risk_level": row["risk_level"],
            }
            for row in rows
        ],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


def ensure_submission_exists(submission_id: int) -> None:
    try:
        with session_scope() as session:
            found = session.execute(
                text("""
                    SELECT 1
                    FROM monolith.submissions
                    WHERE submission_id = :submission_id
                    """),
                {"submission_id": submission_id},
            ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to validate submission"
        ) from exc

    if not found:
        raise HTTPException(
            status_code=404, detail=f"Submission {submission_id} not found"
        )


async def stream_submission_events(
    request: Request,
    submission_id: int,
) -> AsyncGenerator[str, None]:
    last_event_id = 0
    while not await request.is_disconnected():
        try:
            with session_scope() as session:
                rows = (
                    session.execute(
                        text("""
                        SELECT timeline_event_id, event_type, event_data, occurred_at
                        FROM monolith.timeline_events
                        WHERE submission_id = :submission_id
                          AND timeline_event_id > :last_event_id
                        ORDER BY timeline_event_id ASC
                        """),
                        {
                            "submission_id": submission_id,
                            "last_event_id": last_event_id,
                        },
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError:
            payload = json.dumps({"error": "Failed to load timeline events"})
            yield f"event: error\ndata: {payload}\n\n"
            break

        if rows:
            for row in rows:
                last_event_id = int(row["timeline_event_id"])
                data = {
                    "timeline_event_id": last_event_id,
                    "submission_id": submission_id,
                    "event_type": row["event_type"],
                    "event_data": row["event_data"] or {},
                    "occurred_at": _isoformat(row["occurred_at"]),
                }
                # Emit default SSE "message" events so the current UI onmessage handler receives them.
                yield f"id: {last_event_id}\ndata: {json.dumps(data)}\n\n"
        else:
            yield ": keep-alive\n\n"

        await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)


def _build_timeline_row(
    submission_id: int, event_type: str, data: dict[str, Any]
) -> dict[str, Any]:
    payload = create_timeline_payload(event_type=event_type, data=data)
    occurred_at = datetime.fromisoformat(payload["timestamp"])
    return {
        "submission_id": submission_id,
        "event_type": payload["type"],
        "event_data": json.dumps(payload["data"]),
        "occurred_at": occurred_at,
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


def _map_risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _compute_state(risk_level: str) -> str:
    if risk_level == "critical":
        return "rejected"
    if risk_level == "low":
        return "approved"
    return "under_review"


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
