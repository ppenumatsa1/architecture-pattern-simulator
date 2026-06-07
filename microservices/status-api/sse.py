from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.python.db import session_scope

SSE_POLL_INTERVAL_SECONDS = 1.0

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "status-api"}


@router.get("/dashboard/submissions")
def list_submissions(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text("""
                    SELECT
                        s.submission_id,
                        s.submission_version,
                        s.status,
                        s.payload,
                        s.received_at,
                        s.updated_at,
                        rr.risk_score,
                        rr.risk_level,
                        rr.factors,
                        rr.model_name,
                        rr.model_version,
                        rr.evaluated_at
                    FROM microservices.submissions s
                    LEFT JOIN microservices.risk_results rr
                      ON rr.submission_id = s.submission_id
                    ORDER BY s.received_at DESC
                    LIMIT :limit OFFSET :offset
                    """),
                    {"limit": limit, "offset": offset},
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to load submissions dashboard"
        ) from exc

    return [
        {
            "submissionId": row["submission_id"],
            "version": row["submission_version"],
            "status": row["status"],
            "payload": row["payload"] or {},
            "receivedAt": _isoformat(row["received_at"]),
            "updatedAt": _isoformat(row["updated_at"]),
            "risk": {
                "score": (
                    float(row["risk_score"]) if row["risk_score"] is not None else None
                ),
                "level": row["risk_level"],
                "factors": row["factors"] or [],
                "modelName": row["model_name"],
                "modelVersion": row["model_version"],
                "evaluatedAt": _isoformat(row["evaluated_at"]),
            },
        }
        for row in rows
    ]


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: str) -> dict[str, Any]:
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text("""
                    SELECT
                        s.submission_id,
                        s.submission_version,
                        s.status,
                        s.payload,
                        s.received_at,
                        s.updated_at,
                        rr.risk_score,
                        rr.risk_level,
                        rr.factors,
                        rr.model_name,
                        rr.model_version,
                        rr.evaluated_at
                    FROM microservices.submissions s
                    LEFT JOIN microservices.risk_results rr
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
            status_code=500, detail="Failed to load submission"
        ) from exc

    if not row:
        raise HTTPException(
            status_code=404, detail=f"Submission {submission_id} not found"
        )

    return {
        "submissionId": row["submission_id"],
        "version": row["submission_version"],
        "status": row["status"],
        "payload": row["payload"] or {},
        "receivedAt": _isoformat(row["received_at"]),
        "updatedAt": _isoformat(row["updated_at"]),
        "risk": {
            "score": (
                float(row["risk_score"]) if row["risk_score"] is not None else None
            ),
            "level": row["risk_level"],
            "factors": row["factors"] or [],
            "modelName": row["model_name"],
            "modelVersion": row["model_version"],
            "evaluatedAt": _isoformat(row["evaluated_at"]),
        },
    }


@router.get("/submissions/{submission_id}/events")
async def submission_events(
    submission_id: str,
    request: Request,
    since_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    ensure_submission_exists(submission_id)
    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(
        stream_submission_events(
            request=request, submission_id=submission_id, since_event_id=since_event_id
        ),
        media_type="text/event-stream",
        headers=headers,
    )


async def stream_submission_events(
    *, request: Request, submission_id: str, since_event_id: int
) -> AsyncGenerator[str, None]:
    last_event_id = since_event_id

    while not await request.is_disconnected():
        try:
            with session_scope() as session:
                rows = (
                    session.execute(
                        text("""
                        SELECT timeline_event_id, producer_service, event_type, event_data, occurred_at
                        FROM microservices.timeline_events
                        WHERE submission_id = :submission_id
                          AND timeline_event_id > :last_event_id
                        ORDER BY timeline_event_id ASC
                        LIMIT 200
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
            yield 'event: error\ndata: {"error": "failed_to_load_events"}\n\n'
            await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)
            continue

        if rows:
            for row in rows:
                last_event_id = int(row["timeline_event_id"])
                payload = {
                    "timelineEventId": last_event_id,
                    "submissionId": submission_id,
                    "producerService": row["producer_service"],
                    "eventType": row["event_type"],
                    "eventData": row["event_data"] or {},
                    "occurredAt": _isoformat(row["occurred_at"]),
                }
                # Emit default SSE "message" events so the current UI onmessage handler consumes updates.
                yield f"id: {last_event_id}\ndata: {json.dumps(payload)}\n\n"
        else:
            yield ": keep-alive\n\n"

        await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)


def ensure_submission_exists(submission_id: str) -> None:
    try:
        with session_scope() as session:
            exists = session.execute(
                text("""
                    SELECT 1
                    FROM microservices.submissions
                    WHERE submission_id = :submission_id
                    """),
                {"submission_id": submission_id},
            ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail="Failed to validate submission"
        ) from exc

    if not exists:
        raise HTTPException(
            status_code=404, detail=f"Submission {submission_id} not found"
        )


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
