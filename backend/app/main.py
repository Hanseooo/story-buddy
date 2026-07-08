import uuid

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
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
        {"id": job_id, "status": "queued", "current_stage": "queued", "input_text": payload.text}
    ).execute()

    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)

    return CreateStorybookResponse(job_id=job_id)
