"""ADR-080's private persistence and authorized product image boundary.

Teacher inspection/decisions are separate slices. No browser can read this table
or choose a Storage path through these product routes.
"""
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import providers
from app.auth import get_current_user
from app.config import settings
from app.queue import get_queue
from contracts.story_memory import StoryMemory

hold_router = APIRouter()
PRIVATE = {"Cache-Control": "private, no-store"}


class StaleGeneration(BaseException):
    """Safety fencing must bypass node/provider best-effort Exception handlers."""


def connect():
    return psycopg.connect(settings.supabase_db_url, autocommit=True, row_factory=dict_row)


def active_author(conn, job: dict) -> bool:
    return conn.execute("""select 1 from profiles where id=%s and role='student'
      and classroom_id=%s and removed_at is null
      and password_completed_version=password_reset_version""",
                        (job["profile_id"], job["classroom_id"])).fetchone() is not None


def insert_review_job(values: dict) -> None:
    # Recheck authorization in the insert transaction, after privacy/provider work.
    with connect() as conn, conn.transaction():
        author = conn.execute("select * from profiles where id=%s for update", (values["profile_id"],)).fetchone()
        if not author or not active_author(conn, values):
            raise HTTPException(403, "account_unavailable", headers=PRIVATE)
        conn.execute("""insert into jobs(id,status,current_stage,input_text,title,truncated,
          style_preset_id,profile_id,classroom_id,moderation_mode,moderation_settings_snapshot)
          values (%s,'queued','queued',%s,%s,%s,%s,%s,%s,'teacher_review_v1',%s)""", (
            values["id"], values["input_text"], values["title"], values["truncated"],
            values["style_preset_id"], values["profile_id"], values["classroom_id"],
            Jsonb(values["moderation_settings_snapshot"]),
        ))


def assert_current(conn, job_id: str, epoch: int) -> dict:
    job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
    if (not job or job["generation_epoch"] != epoch or job["status"] not in ("queued", "running")
            or not active_author(conn, job)
            or conn.execute("select 1 from job_moderation_reviews where job_id=%s and decision is null", (job_id,)).fetchone()):
        raise StaleGeneration()
    return job


def project_hold(conn, job_id: str, state: StoryMemory, checkpoint_id: str) -> int:
    review, context = state.moderation_context.review, state.moderation_context
    if (not review or review.kind != "scene_image" or review.resolution is not None
            or not checkpoint_id or not context.policy_version):
        raise RuntimeError("invalid_moderation_checkpoint")
    scene = next(s for s in state.scenes if s.scene_id == review.subject_id)
    if not scene.final_image_ref or not scene.final_image_ref.startswith(f"{job_id}/"):
        raise RuntimeError("invalid_moderation_subject")
    selected = next((a for a in scene.attempts if a.image_ref == scene.final_image_ref), None)
    subject = {
        "image_path": scene.final_image_ref, "image_hash": review.subject_version,
        "scene_id": scene.scene_id, "prompt": selected.prompt if selected else scene.prompt,
        "reference_paths": [c.canonical_ref_image for c in state.characters
                            if c.char_id in scene.characters_present and c.canonical_ref_image],
        "story_text": state.input.redacted_text or state.input.raw_text,
    }
    with conn.transaction():
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        prior = conn.execute("select id from job_moderation_reviews where id=%s and job_id=%s",
                             (review.review_id, job_id)).fetchone()
        if prior and job["status"] == "awaiting_teacher":
            return job["generation_epoch"]
        if job["status"] == "failed" and job["error"] == "hold_projection_failed":
            conn.execute("update jobs set status='running' where id=%s", (job_id,))
        assert_current(conn, job_id, context.generation_epoch)
        conn.execute("""insert into job_moderation_reviews
          (id,job_id,kind,subject_id,subject_version,subject,criteria,policy_version,
           settings_snapshot,classifier_evidence,checkpoint_id,return_node)
          values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
            review.review_id, job_id, review.kind, review.subject_id, review.subject_version,
            Jsonb(subject), review.criteria, context.policy_version,
            Jsonb({"theme_ids": context.theme_ids, "settings_version": context.settings_version}),
            Jsonb([e.model_dump(mode="json") for e in review.classifier_evidence]), checkpoint_id, review.return_node,
        ))
        conn.execute("""update jobs set status='awaiting_teacher',current_stage='moderation_review',
          generation_epoch=generation_epoch+1,reveal='{}',pages='[]',error=null,failure_reason=null,
          worker_finished_at=null where id=%s""", (job_id,))
        return job["generation_epoch"] + 1


def product_job(conn, job_id: str, user_id: str) -> dict:
    job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
    viewer = conn.execute("select * from profiles where id=%s", (user_id,)).fetchone()
    if not job or not viewer or job["status"] == "deleting":
        raise HTTPException(404, "job_not_found", headers=PRIVATE)
    if viewer["role"] == "student":
        if (viewer["removed_at"] is not None or viewer["classroom_id"] != job["classroom_id"]
                or viewer["password_completed_version"] != viewer["password_reset_version"]
                or not active_author(conn, job)):
            raise HTTPException(404, "job_not_found", headers=PRIVATE)
        if str(job["profile_id"]) == str(user_id):
            return job
        if job["status"] == "complete" and job["approved_at"] and not job["rejected_at"]:
            return job
    elif viewer["role"] == "teacher" and conn.execute(
        "select 1 from classrooms where id=%s and owner_id=%s", (job["classroom_id"], user_id)
    ).fetchone():
        return job
    raise HTTPException(404, "job_not_found", headers=PRIVATE)


@hold_router.get("/jobs/{job_id}/state")
def job_state(job_id: UUID, response: Response, user=Depends(get_current_user)):
    with connect() as conn:
        job = product_job(conn, str(job_id), str(user.id))
    response.headers.update(PRIVATE)
    return {"job_id": str(job_id), "status": job["status"], "moderation_mode": job["moderation_mode"],
            "generation_epoch": job["generation_epoch"], "worker_finished": job["worker_finished_at"] is not None,
            "can_reconcile_hold": (str(job["profile_id"]) == str(user.id)
                and job["moderation_mode"] == "teacher_review_v1"
                and ((job["error"] == "hold_projection_failed" and job["worker_finished_at"] is not None)
                     or (job["status"] == "awaiting_teacher" and job["worker_finished_at"] is None)))}


def authorized_asset(conn, job_id: str, asset_id: str, user_id: str) -> tuple[str, int]:
    job = product_job(conn, job_id, user_id)
    if (job["moderation_mode"] != "teacher_review_v1"
            or job["status"] not in ("awaiting_confirm", "complete")
            or not active_author(conn, job)
            or conn.execute("select 1 from job_moderation_reviews where job_id=%s and decision is null", (job_id,)).fetchone()):
        raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    # Read the persisted selection and verdict. Neither the URL nor browser metadata
    # can select an attempt. Do not call setup() from a product read.
    saver = PostgresSaver(conn)
    checkpoint = saver.get_tuple({"configurable": {"thread_id": job_id}})
    if not checkpoint:
        raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"])
    if (not state.input.moderation or not state.input.moderation.passed
            or any(c.canonical_ref_image and c.ref_moderation_status not in ("passed", "teacher_allowed")
                   for c in state.characters)):
        raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    path = None
    if job["status"] == "awaiting_confirm" and str(job["profile_id"]) == user_id:
        for char in state.characters:
            if asset_id == f"ref-{char.char_id}" and char.ref_moderation_status in ("passed", "teacher_allowed"):
                path = char.canonical_ref_image
    elif job["status"] == "complete":
        if any(s.moderation_status not in ("passed", "teacher_allowed") or not any(
            a.image_ref == s.final_image_ref and a.safety_eligibility in ("cleared", "teacher_allowed")
            for a in s.attempts
        ) for s in state.scenes):
            raise HTTPException(404, "image_unavailable", headers=PRIVATE)
        for scene in state.scenes:
            if asset_id == f"scene-{scene.scene_id}" and any(
                a.image_ref == scene.final_image_ref and a.safety_eligibility in ("cleared", "teacher_allowed")
                for a in scene.attempts
            ):
                path = scene.final_image_ref
    if not path or not path.startswith(f"{job_id}/"):
        raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    return path, job["generation_epoch"]


@hold_router.get("/jobs/{job_id}/images/{asset_id}")
def job_image(job_id: UUID, asset_id: str, user=Depends(get_current_user)):
    with connect() as conn:
        selected = authorized_asset(conn, str(job_id), asset_id, str(user.id))
    try:
        contents = providers.download_book_image(selected[0])
    except Exception:
        raise HTTPException(503, "image_unavailable", headers=PRIVATE) from None
    with connect() as conn:
        if authorized_asset(conn, str(job_id), asset_id, str(user.id)) != selected:
            raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    return Response(contents, media_type="image/png", headers=PRIVATE)


@hold_router.post("/jobs/{job_id}/reconcile-hold")
def reconcile_hold(job_id: UUID, user=Depends(get_current_user)):
    with connect() as conn:
        job = product_job(conn, str(job_id), str(user.id))
        repairable = (job["error"] == "hold_projection_failed" and job["worker_finished_at"] is not None
                      or job["status"] == "awaiting_teacher" and job["worker_finished_at"] is None)
        if (str(job["profile_id"]) != str(user.id) or job["moderation_mode"] != "teacher_review_v1" or not repairable):
            raise HTTPException(409, "hold_not_repairable", headers=PRIVATE)
    # This worker only repairs the retained checkpoint. It never restarts a failed run.
    get_queue().enqueue("worker.run_job.run_review_storybook_job", str(job_id),
                        job_id=f"hold-{job_id}-{job['generation_epoch']}", expected_epoch=job["generation_epoch"])
    return Response(status_code=202, headers=PRIVATE)


def confirm_review_job(job_id: str, payload: dict, user_id: str) -> str:
    from app.main import JOB_TIMEOUT_SECONDS

    with connect() as conn, conn.transaction():
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        if not job or str(job["profile_id"]) != user_id or not active_author(conn, job):
            raise HTTPException(404, "job_not_found", headers=PRIVATE)
        if job["status"] != "awaiting_confirm":
            return job["status"]
        if job["worker_finished_at"] is None:
            raise HTTPException(409, "finishing_current_step", headers=PRIVATE)
        if payload["action"] == "try_again" and not any(
            c["char_id"] == payload["char_id"] and payload["attribute"] in c["chips"]
            for c in (job["reveal"] or {}).get("characters", [])
        ):
            raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
        conn.execute("update jobs set status='queued',worker_finished_at=null where id=%s", (job_id,))
    try:
        get_queue().enqueue("worker.run_job.run_review_storybook_job", job_id, payload,
                            job_timeout=JOB_TIMEOUT_SECONDS, expected_epoch=job["generation_epoch"])
    except Exception:
        with connect() as conn:
            conn.execute("""update jobs set status='awaiting_confirm',worker_finished_at=now()
              where id=%s and status='queued' and generation_epoch=%s""", (job_id, job["generation_epoch"]))
        raise HTTPException(503, "could_not_resume", headers=PRIVATE) from None
    return "queued"
