import logging
import uuid
from typing import Literal

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.config import MIN_STORY_WORDS, STYLE_PRESETS, settings
from app.length import clamp_story, word_count
from app.db import get_supabase_client
from app.queue import get_queue
from app.auth import get_current_user, teacher_router
import app.classrooms  # noqa: F401 — registers routes on teacher_router as side-effect

if settings.sentry_dsn_backend:
    sentry_sdk.init(dsn=settings.sentry_dsn_backend, traces_sample_rate=0.1)

_log = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(teacher_router)


class CreateStorybookRequest(BaseModel):
    text: str
    style_preset_id: str | None = None

    @field_validator("text")
    @classmethod
    def validate_min_length(cls, v: str) -> str:
        if word_count(v) < MIN_STORY_WORDS:
            raise ValueError(f"Story text must be at least {MIN_STORY_WORDS} words")
        return v

    @field_validator("style_preset_id")
    @classmethod
    def validate_style_preset(cls, v: str | None) -> str | None:
        if v is not None and v not in STYLE_PRESETS:
            raise ValueError(f"Unknown style_preset_id: {v!r}")
        return v


class CreateStorybookResponse(BaseModel):
    job_id: str


class ConfirmRequest(BaseModel):
    action: Literal["confirm", "try_again"]
    char_id: str | None = None
    attribute: str | None = None


class ConfirmResponse(BaseModel):
    status: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/storybooks", response_model=CreateStorybookResponse)
def create_storybook(
    payload: CreateStorybookRequest, user=Depends(get_current_user)
) -> CreateStorybookResponse:
    job_id = str(uuid.uuid4())
    before = word_count(payload.text)
    text, truncated = clamp_story(payload.text)
    if truncated:
        # CC-5: log counts only, never the text (ADR-025 D5).
        _log.info("story truncated: %d words → %d words", before, word_count(text))
    supabase = get_supabase_client()
    profile_rows = (
        supabase.table("profiles").select("classroom_id").eq("id", user.id).execute().data
    )
    if not profile_rows or profile_rows[0]["classroom_id"] is None:
        raise HTTPException(403, "only students can submit stories")
    classroom_id = profile_rows[0]["classroom_id"]
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "status": "queued",
            "current_stage": "queued",
            "input_text": text,
            "truncated": truncated,
            "style_preset_id": payload.style_preset_id,
            "profile_id": user.id,
            "classroom_id": classroom_id,
        }
    ).execute()
    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)
    return CreateStorybookResponse(job_id=job_id)


@app.post("/jobs/{job_id}/confirm", response_model=ConfirmResponse)
def confirm_job(
    job_id: str, payload: ConfirmRequest, user=Depends(get_current_user)
) -> ConfirmResponse:
    supabase = get_supabase_client()

    rows = (
        supabase.table("jobs")
        .select("reveal, status, profile_id")
        .eq("id", job_id)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(404, "job not found")
    row = rows[0]

    if row["profile_id"] != user.id:
        raise HTTPException(403, "forbidden")

    if payload.action == "try_again":
        characters = row["reveal"].get("characters", [])
        character = next((c for c in characters if c["char_id"] == payload.char_id), None)
        if character is None or payload.attribute not in character["chips"]:
            raise HTTPException(422, "char_id or attribute not offered on this job's current reveal")

    cas = (
        supabase.table("jobs")
        .update({"status": "queued"})
        .eq("id", job_id)
        .eq("status", "awaiting_confirm")
        .execute()
    )
    if not cas.data:
        # Zero rows affected: already resumed, never paused, or swept. A double-tapping child
        # must not see an error (spec §4.9) — report the current status, enqueue nothing.
        return ConfirmResponse(status=row["status"])

    queue = get_queue()
    try:
        queue.enqueue("worker.run_job.resume_storybook_job", job_id, payload.model_dump())
    except Exception:
        # The CAS already flipped status to 'queued'; a Redis outage here would strand the book
        # with no worker coming and no way to re-confirm. Roll it back — nothing else ran.
        supabase.table("jobs").update({"status": "awaiting_confirm"}).eq("id", job_id).execute()
        raise HTTPException(503, "could not resume — try again")

    return ConfirmResponse(status="queued")
