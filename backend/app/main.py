import uuid

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.config import STYLE_PRESETS, settings
from app.db import get_supabase_client
from app.queue import get_queue

if settings.sentry_dsn_backend:
    sentry_sdk.init(dsn=settings.sentry_dsn_backend, traces_sample_rate=0.1)

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
    supabase = get_supabase_client()
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "status": "queued",
            "current_stage": "queued",
            "input_text": payload.text,
            "style_preset_id": payload.style_preset_id,
        }
    ).execute()

    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)

    return CreateStorybookResponse(job_id=job_id)
