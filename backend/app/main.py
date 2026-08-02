import logging
import uuid

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.config import MIN_STORY_WORDS, STYLE_PRESETS, settings
from app.length import clamp_story, word_count
from app.db import get_supabase_client
from app.queue import get_queue

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/storybooks", response_model=CreateStorybookResponse)
def create_storybook(payload: CreateStorybookRequest) -> CreateStorybookResponse:
    job_id = str(uuid.uuid4())
    before = word_count(payload.text)
    text, truncated = clamp_story(payload.text)
    if truncated:
        # CC-5: log counts only, never the text (ADR-025 D5).
        _log.info("story truncated: %d words → %d words", before, word_count(text))
    supabase = get_supabase_client()
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "status": "queued",
            "current_stage": "queued",
            "input_text": text,
            "truncated": truncated,
            "style_preset_id": payload.style_preset_id,
        }
    ).execute()

    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)

    return CreateStorybookResponse(job_id=job_id)
