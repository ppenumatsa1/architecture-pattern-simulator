from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BASE_DIR.parent / "shared"
for path in (BASE_DIR, SHARED_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from python.db import session_scope  # noqa: E402
from event_store.events import new_domain_event  # noqa: E402
from event_store.repository import (
    EVENT_REPOSITORY,
    EventStoreConcurrencyError,
)  # noqa: E402

router = APIRouter()


class CreateSubmissionCommand(BaseModel):
    applicant_id: str = Field(alias="applicantId", min_length=1)
    payload: dict = Field(default_factory=dict)
    correlation_id: UUID | None = Field(default=None, alias="correlationId")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
        extra = "forbid"


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "command-api"}


@router.post("/commands/create-submission", status_code=status.HTTP_202_ACCEPTED)
def create_submission(command: CreateSubmissionCommand) -> dict:
    submission_id = uuid4()
    now = datetime.now(tz=timezone.utc)
    metadata = {
        "producer": "command-api",
        "command": "create-submission",
    }

    event = new_domain_event(
        aggregate_id=submission_id,
        aggregate_type="submission",
        event_type="submission.created",
        schema_version=1,
        event_data={
            "submission_id": str(submission_id),
            "applicant_id": command.applicant_id,
            "payload": command.payload,
            "submitted_at": now.isoformat(),
        },
        metadata=metadata,
        correlation_id=command.correlation_id,
    )

    try:
        with session_scope() as session:
            EVENT_REPOSITORY.append(session, event, expected_aggregate_version=0)
    except EventStoreConcurrencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive transport error handling
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to persist command event",
        ) from exc

    return {
        "submissionId": str(submission_id),
        "eventId": str(event.event_id),
        "status": "accepted",
    }
