"""Magic pencil ticket 10 (US-04): the page pencil on a finished book.

The edit runs in `worker.page_pencil`, outside the graph. The checkpoint stays the pipeline's record
and `jobs.pages` is the book (OD-01, SH-09). Every use is a `job_picture_records` row with
`kind='pencil'` and `source='page_pencil'` (AC-22), keyed by the client's request id (SH-08).
"""
import hashlib
from typing import Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth import get_current_user
from app.config import IMAGE_BUDGET, MAX_PAGE_PENCILS, MAX_PENCIL_CHARS
from app.moderation_hold import (PRIVATE, active_author, checked_pencil_text, command_conflict, command_state, connect,
                                 finished_book, finished_page, product_job, review_subject_bytes, teacher_classroom)
from app.moderation_policy import TEACHER_MODERATION_CRITERIA, TEACHER_MODERATION_POLICY_VERSION
from app.queue import get_queue

page_pencil_router = APIRouter()
# A use in one of these states is the book's one request in flight (SH-07).
ACTIVE_STATES = ("drawing", "held", "choice", "error")


class PagePencilRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    source: str = Field(max_length=1000)
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed or len(trimmed) > MAX_PENCIL_CHARS:
            raise ValueError(f"Write between 1 and {MAX_PENCIL_CHARS} characters.")
        return trimmed


class PagePencilChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use_id: UUID
    choice: Literal["kept", "old"]
    source: str = Field(max_length=1000)


def task_id(job_id: str, use_id: str) -> str:
    return f"page-pencil-{job_id}-{use_id}"


def use_state(row: dict) -> str:
    """The child's view of one use. 'drawing' covers a queued edit and an unchecked result."""
    if row["reason"] in ("refused", "stale"):
        return row["reason"]
    if row["reason"]:
        return "stopped"
    if row["choice"]:
        return row["choice"]
    if row["text_moderation"] == "held" or row["picture_moderation"] == "flagged":
        return "held"
    if row["picture_moderation"] in ("passed", "teacher_allowed"):
        return "choice"
    return "drawing"


def page_uses(conn, job_id: str) -> list[dict]:
    return conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
      and source='page_pencil' order by created_at""", (job_id,)).fetchall()


def pencil_in_progress(conn, job_id: str) -> bool:
    """SH-07: one page change per book at a time, including a result waiting for keep-or-old."""
    return any(use_state(u) in ACTIVE_STATES for u in page_uses(conn, job_id))


def pencils_spent(uses: list[dict]) -> int:
    """SH-04: a go is spent when an image came back and was checked. A refusal or a classifier
    error spends nothing."""
    return sum(u["image_path"] is not None and u["picture_moderation"] is not None for u in uses)


def disabled_reason(job: dict, uses: list[dict]) -> str | None:
    if pencils_spent(uses) >= MAX_PAGE_PENCILS:
        return "no_pencils"
    if (job["image_count"] or 0) >= IMAGE_BUDGET:
        return "image_budget"
    return None


def enqueue_edit(job_id: str, use_id: str) -> None:
    """One RQ job per use. A retry of a task that died re-runs it; a live one is left alone."""
    from rq.exceptions import DuplicateJobError

    queue = get_queue()
    try:
        queue.enqueue("worker.page_pencil.run_page_pencil", job_id, use_id,
                      job_id=task_id(job_id, use_id), unique=True)
    except DuplicateJobError:
        existing = queue.fetch_job(task_id(job_id, use_id))
        if existing and existing.get_status() == "failed":
            existing.requeue()


def child_view(row: dict, failed: bool = False) -> dict:
    state = use_state(row)
    if state == "drawing" and failed:
        state = "error"
    return {"use_id": row["version_id"], "scene_id": row["target_id"], "state": state, "text": row["pencil_text"],
            "before_path": row["before_path"],
            "after_path": row["image_path"] if state in ("choice", "kept", "old") else None}


def task_failed(job_id: str, use_id: str) -> bool:
    try:
        existing = get_queue().fetch_job(task_id(job_id, use_id))
    except Exception:
        return False
    return existing is None or existing.get_status() == "failed"


@page_pencil_router.get("/jobs/{job_id}/pages/pencil")
def page_pencil_status(job_id: UUID, response: Response, user=Depends(get_current_user)):
    job_id, user_id = str(job_id), str(user.id)
    with connect() as conn:
        job = product_job(conn, job_id, user_id)
        finished_book(conn, job, user_id)
        uses = page_uses(conn, job_id)
    left = max(MAX_PAGE_PENCILS - pencils_spent(uses), 0)
    response.headers.update(PRIVATE)
    return {"pencils_left": left, "disabled_reason": disabled_reason(job, uses),
            "uses": [child_view(u, use_state(u) == "drawing" and task_failed(job_id, u["version_id"]))
                     for u in uses]}


@page_pencil_router.post("/jobs/{job_id}/pages/{scene_id}/pencil", status_code=202)
def page_pencil(job_id: UUID, scene_id: str, body: PagePencilRequest, response: Response,
                user=Depends(get_current_user)):
    """AC-16, AC-17, SH-03, SH-08. Redact and moderate, then store the use. Flagged text holds for the
    teacher with no image; cleared text queues one edit. Nothing is spent here."""
    job_id, user_id, use_id = str(job_id), str(user.id), str(body.request_id)

    def admit(conn) -> dict:
        """The checks a new request passes, before the classifiers and again under the row lock."""
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        _, current = finished_page(conn, job, scene_id, user_id)
        if body.source != current:
            raise HTTPException(409, "stale_source", headers=PRIVATE)
        uses = page_uses(conn, job_id)
        if reason := disabled_reason(job, uses):
            raise HTTPException(409, reason, headers=PRIVATE)
        if pencil_in_progress(conn, job_id):
            raise HTTPException(409, "pencil_in_progress", headers=PRIVATE)
        return job

    with connect() as conn:
        product_job(conn, job_id, user_id)
        existing = conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
          and source='page_pencil' and version_id=%s""", (job_id, use_id)).fetchone()
        if existing is None:
            with conn.transaction():
                admit(conn)
    if existing is not None:   # SH-08: a repeat of this request spends nothing more.
        if use_state(existing) == "drawing" and task_failed(job_id, use_id):
            enqueue_edit(job_id, use_id)   # the retry after a task that died (a closed tab never needs one)
        response.headers.update(PRIVATE)
        return child_view(existing)

    checked = checked_pencil_text(body.text)   # network calls, outside the lock
    with connect() as conn, conn.transaction():
        job = admit(conn)
        row = conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,source,
          before_path,pencil_text,text_moderation) values (%s,'pencil',%s,%s,'page_pencil',%s,%s,%s)
          on conflict (job_id,kind,version_id) do nothing returning *""",
                           (job_id, scene_id, use_id, body.source, checked["text"],
                            "held" if checked["flagged"] else "cleared")).fetchone()
        if row is None:
            raise HTTPException(409, "request_conflict", headers=PRIVATE)
        if checked["flagged"]:
            snapshot = job["moderation_settings_snapshot"]
            conn.execute("""insert into job_moderation_reviews(id,job_id,kind,subject_id,subject_version,
              subject,criteria,policy_version,settings_snapshot,classifier_evidence,return_node)
              values (%s,%s,'page_pencil_text',%s,%s,%s,%s,%s,%s,%s,'page_pencil')""", (
                uuid4(), job_id, use_id, hashlib.sha256(checked["text"].encode()).hexdigest(),
                Jsonb({"pencil_text": checked["text"], "scene_id": scene_id, "before_path": body.source}),
                list(TEACHER_MODERATION_CRITERIA), snapshot["policy_version"], Jsonb(snapshot),
                Jsonb(checked["evidence"])))
    if not checked["flagged"]:
        enqueue_edit(job_id, use_id)
    response.headers.update(PRIVATE)
    return child_view(row)


@page_pencil_router.post("/jobs/{job_id}/pages/{scene_id}/pencil/choice")
def page_pencil_choice(job_id: UUID, scene_id: str, body: PagePencilChoice, response: Response,
                       user=Depends(get_current_user)):
    """AC-19, AC-20, SH-08. "Keep this" makes the result the page in `jobs.pages` and returns the book
    to pending under the row lock, as ticket 09's version choice does. "Use the old one" keeps the
    result as another version of the page. The character's canon is never touched."""
    job_id, user_id, use_id = str(job_id), str(user.id), str(body.use_id)
    stale = False
    with connect() as conn, conn.transaction():
        product_job(conn, job_id, user_id)
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        _, current = finished_page(conn, job, scene_id, user_id)
        use = conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
          and source='page_pencil' and version_id=%s and target_id=%s for update""",
                           (job_id, use_id, scene_id)).fetchone()
        if use is None or body.source != use["image_path"]:
            raise HTTPException(409, "stale_source", headers=PRIVATE)
        if use["choice"] is not None:
            if use["choice"] != body.choice:
                raise HTTPException(409, "already_chosen", headers=PRIVATE)
        elif use_state(use) != "choice":
            raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
        elif current != use["before_path"]:
            # The page changed under the result. Recorded, so it stops blocking a new pencil.
            conn.execute("update job_picture_records set reason='stale' where id=%s", (use["id"],))
            stale = True
        else:
            conn.execute("update job_picture_records set choice=%s where id=%s", (body.choice, use["id"]))
            pages = [{**p, "other_versions": True, **({"image_path": use["image_path"]} if body.choice == "kept" else {})}
                     if isinstance(p, dict) and p.get("scene_id") == scene_id else p for p in job["pages"]]
            if body.choice == "kept":
                conn.execute("update jobs set pages=%s,approved_at=null,rejected_at=null where id=%s",
                             (Jsonb(pages), job_id))
            else:
                conn.execute("update jobs set pages=%s where id=%s", (Jsonb(pages), job_id))
    if stale:
        raise HTTPException(409, "stale_source", headers=PRIVATE)
    response.headers.update(PRIVATE)
    return {"choice": body.choice}


def page_pencil_decision(job_id: str, user_id: str, body, response: Response) -> dict:
    """AC-17, AC-18, SH-05. A held page pencil request waits alone on a readable book, so a decision
    never changes the job. Allow on the text queues the edit; allow on a result offers keep-or-old.
    Stop ends only the request, also for a removed author, whose book is already out of the gallery.
    Replacement of a held result is ticket 11."""
    try:
        with connect() as conn, conn.transaction():
            job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
            if not job or job["status"] == "deleting":
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            role = conn.execute("select role from profiles where id=%s", (user_id,)).fetchone()
            if not role or role["role"] != "teacher":
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
            teacher_classroom(conn, str(job["classroom_id"]), user_id)
            conn.execute("select id from profiles where id=%s for update", (job["profile_id"],))
            if body.action == "allow" and not active_author(conn, job):
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            review = conn.execute("select * from job_moderation_reviews where job_id=%s and id=%s for update",
                                  (job_id, body.review_id)).fetchone()
            prior = conn.execute("select * from job_moderation_reviews where job_id=%s and request_id=%s",
                                 (job_id, body.request_id)).fetchone()
            if prior:
                if (str(prior["id"]) != str(body.review_id) or str(prior["actor_id"]) != user_id
                        or prior["decision"] != body.action or prior["subject_version"] != body.subject_version
                        or prior["decision_epoch"] != body.expected_epoch):
                    command_conflict("request_conflict", job, review)
                response.headers.update(PRIVATE)
                return command_state(job, prior)
            if (review["decision"] is not None or job["status"] != "complete"
                    or job["generation_epoch"] != body.expected_epoch or review["subject_version"] != body.subject_version):
                command_conflict("review_changed", job, review)
            if body.action == "replace":
                raise HTTPException(422, "replacement_not_available", headers=PRIVATE)
            if body.action == "allow" and (body.policy_version != TEACHER_MODERATION_POLICY_VERSION
                                           or set(body.confirmed_criteria) != set(review["criteria"])):
                command_conflict("policy_confirmation_required", job, review)
            try:
                contents = review_subject_bytes(review)
            except Exception:
                command_conflict("image_unavailable", job, review)
            if hashlib.sha256(contents).hexdigest() != review["subject_version"]:
                command_conflict("image_unavailable", job, review)
            review = conn.execute("""update job_moderation_reviews set decision=%s,actor_id=%s,decided_at=now(),
              decision_policy_version=%s,confirmed_criteria=%s,request_id=%s,decision_epoch=%s
              where id=%s returning *""", (body.action, user_id, body.policy_version, body.confirmed_criteria,
                                           body.request_id, body.expected_epoch, body.review_id)).fetchone()
            update = {("page_pencil_text", "allow"): "text_moderation='teacher_allowed'",
                      ("page_pencil_text", "stop"): "text_moderation='teacher_stopped',reason='text_stopped'",
                      ("page_pencil_result", "allow"): "picture_moderation='teacher_allowed'",
                      ("page_pencil_result", "stop"): "reason='result_stopped'"}[(review["kind"], body.action)]
            conn.execute(f"""update job_picture_records set {update} where job_id=%s and kind='pencil'
              and source='page_pencil' and version_id=%s""", (job_id, review["subject_id"]))
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None
    if (review["kind"], body.action) == ("page_pencil_text", "allow"):
        enqueue_edit(job_id, review["subject_id"])
    response.status_code = 202 if body.action == "allow" and review["kind"] == "page_pencil_text" else 200
    response.headers.update(PRIVATE)
    return command_state(job, review)
