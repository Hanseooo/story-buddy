import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from app.auth import owned_job, require_teacher, teacher_router
from app.db import get_supabase_client

_log = logging.getLogger(__name__)


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected", "pending"]


class ReviewResponse(BaseModel):
    approved_at: str | None
    rejected_at: str | None


def _state(job: dict) -> str:
    if job["approved_at"] is not None:
        return "approved"
    if job["rejected_at"] is not None:
        return "rejected"
    return "pending"


@teacher_router.post("/jobs/{job_id}/review", response_model=ReviewResponse)
def review_job(
    payload: ReviewRequest,
    job: dict = Depends(owned_job),
    teacher: dict = Depends(require_teacher),
) -> ReviewResponse:
    if job["status"] != "complete":
        raise HTTPException(422, f"job status is {job['status']!r}, not 'complete'")

    current = _state(job)

    if current == payload.decision:
        # Idempotent — no write, no log
        return ReviewResponse(approved_at=job["approved_at"], rejected_at=job["rejected_at"])

    now = datetime.now(timezone.utc).isoformat()
    if payload.decision == "approved":
        update = {"approved_at": now, "rejected_at": None}
    elif payload.decision == "rejected":
        update = {"approved_at": None, "rejected_at": now}
    else:  # "pending"
        update = {"approved_at": None, "rejected_at": None}

    result = (
        get_supabase_client()
        .table("jobs")
        .update(update)
        .eq("id", job["id"])
        .execute()
    )
    updated = result.data[0]

    _log.info(
        "review: job=%s classroom=%s teacher=%s from=%s to=%s",
        job["id"],
        job["classroom_id"],
        teacher["id"],
        current,
        payload.decision,
    )

    return ReviewResponse(
        approved_at=updated["approved_at"],
        rejected_at=updated["rejected_at"],
    )
