from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BASE_DIR.parent / "shared"
for path in (SHARED_DIR,):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from python.db import session_scope  # noqa: E402

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "query-api"}


@router.get("/dashboard/submissions")
def list_submissions(
    limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0)
) -> list[dict]:
    stmt = text("""
        SELECT
            s.aggregate_id,
            s.submission_status,
            s.applicant_id,
            s.payload,
            s.last_event_version,
            s.submitted_at,
            r.risk_score,
            r.risk_level,
            r.factors,
            r.evaluated_at
        FROM event_sourcing.submission_read_model s
        LEFT JOIN event_sourcing.risk_summary_read_model r
          ON r.aggregate_id = s.aggregate_id
        ORDER BY s.submitted_at DESC
        LIMIT :limit OFFSET :offset
        """)
    with session_scope() as session:
        rows = (
            session.execute(stmt, {"limit": limit, "offset": offset}).mappings().all()
        )

    return [
        {
            "submissionId": str(row["aggregate_id"]),
            "status": row["submission_status"],
            "applicantId": row["applicant_id"],
            "payload": row["payload"],
            "lastEventVersion": row["last_event_version"],
            "submittedAt": (
                row["submitted_at"].isoformat() if row["submitted_at"] else None
            ),
            "risk": {
                "score": (
                    float(row["risk_score"]) if row["risk_score"] is not None else None
                ),
                "level": row["risk_level"],
                "factors": row["factors"] if row["factors"] is not None else [],
                "evaluatedAt": (
                    row["evaluated_at"].isoformat() if row["evaluated_at"] else None
                ),
            },
        }
        for row in rows
    ]


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: UUID) -> dict:
    stmt = text("""
        SELECT
            s.aggregate_id,
            s.submission_status,
            s.applicant_id,
            s.payload,
            s.last_event_version,
            s.submitted_at,
            r.risk_score,
            r.risk_level,
            r.factors,
            r.evaluated_at
        FROM event_sourcing.submission_read_model s
        LEFT JOIN event_sourcing.risk_summary_read_model r
          ON r.aggregate_id = s.aggregate_id
        WHERE s.aggregate_id = :submission_id
        """)

    with session_scope() as session:
        row = (
            session.execute(stmt, {"submission_id": submission_id})
            .mappings()
            .one_or_none()
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submissionId": str(row["aggregate_id"]),
        "status": row["submission_status"],
        "applicantId": row["applicant_id"],
        "payload": row["payload"],
        "lastEventVersion": row["last_event_version"],
        "submittedAt": row["submitted_at"].isoformat() if row["submitted_at"] else None,
        "risk": {
            "score": (
                float(row["risk_score"]) if row["risk_score"] is not None else None
            ),
            "level": row["risk_level"],
            "factors": row["factors"] if row["factors"] is not None else [],
            "evaluatedAt": (
                row["evaluated_at"].isoformat() if row["evaluated_at"] else None
            ),
        },
    }


@router.get("/submissions/{submission_id}/events")
async def stream_submission_events(
    submission_id: UUID, since_id: int = Query(default=0, ge=0)
) -> StreamingResponse:
    async def event_generator() -> str:
        last_seen = since_id
        idle_cycles = 0

        while idle_cycles < 30:
            with session_scope() as session:
                rows = (
                    session.execute(
                        text("""
                        SELECT
                            timeline_event_id,
                            event_id,
                            event_type,
                            event_data,
                            occurred_at
                        FROM event_sourcing.timeline_events
                        WHERE aggregate_id = :submission_id
                          AND timeline_event_id > :last_seen
                        ORDER BY timeline_event_id ASC
                        LIMIT 200
                        """),
                        {"submission_id": submission_id, "last_seen": last_seen},
                    )
                    .mappings()
                    .all()
                )

            if not rows:
                idle_cycles += 1
                await asyncio.sleep(1)
                continue

            idle_cycles = 0
            for row in rows:
                last_seen = int(row["timeline_event_id"])
                payload = {
                    "timelineEventId": last_seen,
                    "eventId": str(row["event_id"]),
                    "eventType": row["event_type"],
                    "eventData": row["event_data"],
                    "occurredAt": (
                        row["occurred_at"].isoformat() if row["occurred_at"] else None
                    ),
                }
                # Emit default SSE message events so browser onmessage receives CQRS updates.
                yield f"id: {last_seen}\ndata: {json.dumps(payload)}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
