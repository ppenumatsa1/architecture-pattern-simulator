from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from service import (
    create_submission,
    ensure_submission_exists,
    get_submission,
    list_submissions,
    stream_submission_events,
)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "monolith-api"}


@router.post("/submissions")
def submission(payload: dict) -> dict:
    return create_submission(payload)


@router.get("/submissions/{submission_id}")
def get_submission_by_id(submission_id: int) -> dict:
    return get_submission(submission_id)


@router.get("/submissions")
def get_submissions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return list_submissions(limit=limit, offset=offset)


@router.get("/submissions/{submission_id}/events")
async def submission_events(submission_id: int, request: Request) -> StreamingResponse:
    ensure_submission_exists(submission_id)
    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(
        stream_submission_events(request=request, submission_id=submission_id),
        media_type="text/event-stream",
        headers=headers,
    )
