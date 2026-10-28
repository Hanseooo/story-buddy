"""Private, book-level teacher notes (ADR-081)."""
from uuid import UUID

from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from app.auth import owned_job, require_teacher, teacher_router
from app.config import MAX_REVIEW_NOTE_CHARS
from app.db import get_supabase_client


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_REVIEW_NOTE_CHARS)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Write a note before sending.")
        return value


def _note(job: dict, teacher: dict, operation: str, body: str | None = None):
    result = get_supabase_client().rpc("teacher_review_note", {
        "p_job_id": job["id"], "p_teacher_id": teacher["id"],
        "p_operation": operation, "p_body": body,
    }).execute().data
    if result["status"] != 200:
        raise HTTPException(result["status"], result["detail"], headers={"Cache-Control": "no-store"})
    return result["note"]


def _owned_note_job(job_id: UUID, teacher=Depends(require_teacher)) -> dict:
    # Validate before owned_job's string-based Supabase query runs.
    return owned_job(str(job_id), teacher)


@teacher_router.get("/teacher/jobs/{job_id}/note")
def get_note(response: Response, job=Depends(_owned_note_job), teacher=Depends(require_teacher)):
    response.headers["Cache-Control"] = "no-store"
    return _note(job, teacher, "GET")


@teacher_router.put("/teacher/jobs/{job_id}/note")
def put_note(
    payload: NoteRequest, response: Response,
    job=Depends(_owned_note_job), teacher=Depends(require_teacher),
):
    response.headers["Cache-Control"] = "no-store"
    return _note(job, teacher, "PUT", payload.body)


@teacher_router.delete("/teacher/jobs/{job_id}/note", status_code=204)
def delete_note(job=Depends(_owned_note_job), teacher=Depends(require_teacher)):
    _note(job, teacher, "DELETE")
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
