"""Private, book-level teacher notes (ADR-081)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, StrictBool, field_validator

from app.auth import get_current_user, owned_classroom, owned_job, require_teacher, teacher_router
from app.config import MAX_REVIEW_NOTE_CHARS
from app.db import get_supabase_client


child_notes_router = APIRouter()
_PRIVATE = {"Cache-Control": "private, no-store"}


def _child_note_jobs(user) -> list[dict]:
    client = get_supabase_client()
    profiles = (client.table("profiles").select("role, classroom_id, removed_at")
                .eq("id", str(user.id)).execute().data)
    if (not profiles or profiles[0]["role"] != "student"
            or profiles[0].get("removed_at") or not profiles[0].get("classroom_id")):
        raise HTTPException(404, "not found", headers=_PRIVATE)
    classroom_id = profiles[0]["classroom_id"]
    classrooms = (client.table("classrooms").select("review_notes_enabled")
                  .eq("id", classroom_id).execute().data)
    if not classrooms or not classrooms[0].get("review_notes_enabled"):
        return []
    return (client.table("jobs").select("id").eq("profile_id", str(user.id))
            .eq("classroom_id", classroom_id).eq("status", "complete").execute().data)


@child_notes_router.get("/me/notes")
def get_child_notes(response: Response, user=Depends(get_current_user)):
    response.headers.update(_PRIVATE)
    jobs = _child_note_jobs(user)
    if not jobs:
        return []
    notes = (get_supabase_client().table("job_review_notes")
             .select("job_id, body, seen_at, updated_at").in_("job_id", [job["id"] for job in jobs])
             .is_("scene_id", "null").execute().data)
    return [{"job_id": note["job_id"], "body": note["body"],
             "seen": note["seen_at"] is not None, "updated_at": note["updated_at"]} for note in notes]


class SeenNoteRequest(BaseModel):
    updated_at: datetime


@child_notes_router.post("/jobs/{job_id}/note/seen", status_code=204)
def mark_child_note_seen(job_id: UUID, payload: SeenNoteRequest, user=Depends(get_current_user)):
    if str(job_id) not in {job["id"] for job in _child_note_jobs(user)}:
        raise HTTPException(404, "not found", headers=_PRIVATE)
    # Match the opened version so a concurrent edit remains unread.
    notes = (get_supabase_client().table("job_review_notes")
             .update({"seen_at": datetime.now(timezone.utc).isoformat()})
             .eq("job_id", str(job_id)).eq("updated_at", payload.updated_at.isoformat())
             .is_("scene_id", "null").execute().data)
    if not notes:
        raise HTTPException(404, "not found", headers=_PRIVATE)
    return Response(status_code=204, headers=_PRIVATE)


class ReviewNotesSettingsRequest(BaseModel):
    enabled: StrictBool


@teacher_router.patch("/classrooms/{classroom_id}/review-notes")
def save_review_notes_settings(
    payload: ReviewNotesSettingsRequest, classroom=Depends(owned_classroom),
):
    rows = (get_supabase_client().table("classrooms")
            .update({"review_notes_enabled": payload.enabled})
            .eq("id", classroom["id"]).execute().data)
    if not rows:
        raise HTTPException(404, "classroom not found")
    return {"enabled": rows[0]["review_notes_enabled"]}


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
