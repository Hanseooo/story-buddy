"""ADR-080's private persistence and authorized product image boundary.

Teacher decisions are separate slices. No browser can read this table
or choose a Storage path through these product routes.
"""
import hashlib
from uuid import UUID, uuid5
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

import providers
from app.auth import get_current_user
from app.config import settings
from app.moderation_policy import OPTIONAL_THEMES, POLICY, TEACHER_MODERATION_CRITERIA, TEACHER_MODERATION_POLICY_VERSION
from app.queue import get_queue
from contracts.story_memory import StoryMemory
from pipeline.input_gate import has_text_clearance
from pipeline.optional_themes import has_bound_theme_review
from pipeline.moderation_replace import replacement_disabled_reason

hold_router = APIRouter()
PRIVATE = {"Cache-Control": "private, no-store"}


class ModerationSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=0)
    theme_ids: list[Literal["spooky_suspense", "story_conflict", "loss_separation"]]


@hold_router.get("/teacher/classrooms/{classroom_id}/moderation-settings")
def classroom_moderation_settings(classroom_id: UUID, response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn, conn.transaction():
            role = conn.execute("select role from profiles where id=%s", (str(user.id),)).fetchone()
            if not role or role["role"] != "teacher":
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
            teacher_classroom(conn, str(classroom_id), str(user.id))
            row = conn.execute("select moderation_theme_ids,moderation_settings_version from classrooms where id=%s",
                               (classroom_id,)).fetchone()
    except psycopg.Error:
        raise HTTPException(503, "settings_unavailable", headers=PRIVATE) from None
    response.headers.update(PRIVATE)
    return {"theme_ids": row["moderation_theme_ids"], "settings_version": row["moderation_settings_version"],
            "editable": settings.enable_teacher_moderation_review, "themes": OPTIONAL_THEMES}


@hold_router.patch("/teacher/classrooms/{classroom_id}/moderation-settings")
def save_classroom_moderation_settings(classroom_id: UUID, body: ModerationSettingsRequest,
                                      response: Response, user=Depends(get_current_user)):
    if len(body.theme_ids) != len(set(body.theme_ids)):
        raise HTTPException(422, "duplicate_theme_ids", headers=PRIVATE)
    try:
        with connect() as conn, conn.transaction():
            role = conn.execute("select role from profiles where id=%s", (str(user.id),)).fetchone()
            if not role or role["role"] != "teacher":
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
            row = conn.execute("select * from classrooms where id=%s and owner_id=%s for update",
                               (classroom_id, str(user.id))).fetchone()
            if not row:
                raise HTTPException(404, "classroom_not_found", headers=PRIVATE)
            if not settings.enable_teacher_moderation_review:
                raise HTTPException(409, "settings_disabled", headers=PRIVATE)
            if row["moderation_settings_version"] != body.expected_version:
                raise HTTPException(409, {"code": "settings_changed", "theme_ids": row["moderation_theme_ids"],
                    "settings_version": row["moderation_settings_version"]}, headers=PRIVATE)
            conn.execute("""update classrooms set moderation_theme_ids=%s,
              moderation_settings_version=moderation_settings_version+1 where id=%s""", (body.theme_ids, classroom_id))
    except psycopg.Error:
        raise HTTPException(503, "settings_unavailable", headers=PRIVATE) from None
    response.headers.update(PRIVATE)
    return {"theme_ids": body.theme_ids, "settings_version": body.expected_version + 1}


@hold_router.get("/teacher/moderation-policy")
def teacher_moderation_policy(response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn:
            if not conn.execute("select 1 from profiles where id=%s and role='teacher'", (str(user.id),)).fetchone():
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None
    response.headers.update(PRIVATE)
    return POLICY


def teacher_classroom(conn, classroom_id: str, user_id: str):
    if not conn.execute("""select 1 from classrooms c join profiles p on p.id=c.owner_id
      where c.id=%s and c.owner_id=%s and p.role='teacher' for share of c,p""", (classroom_id, user_id)).fetchone():
        raise HTTPException(404, "review_not_found", headers=PRIVATE)


def teacher_review(conn, job_id: str, user_id: str):
    job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
    if not job or job["status"] == "deleting":
        raise HTTPException(404, "review_not_found", headers=PRIVATE)
    teacher_classroom(conn, str(job["classroom_id"]), user_id)
    review = conn.execute("""select * from job_moderation_reviews
      where job_id=%s and decision is null""", (job_id,)).fetchone()
    return job, review


@hold_router.get("/teacher/classrooms/{classroom_id}/moderation-reviews")
def teacher_review_list(classroom_id: UUID, response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn:
            teacher_classroom(conn, str(classroom_id), str(user.id))
            rows = conn.execute("""select r.id as review_id,j.id as job_id,j.title,
              p.display_nickname as author,r.created_at as held_at,
              (r.decision in ('allow','replace')) as continuation_pending,
              (j.worker_finished_at is not null) as ready
              from job_moderation_reviews r join jobs j on j.id=r.job_id
              left join profiles p on p.id=j.profile_id
              where j.classroom_id=%s and ((j.status='awaiting_teacher' and r.decision is null)
                or (j.status='queued' and r.decision in ('allow','replace') and r.decision_epoch=j.generation_epoch
                    and r.dispatch_state in ('pending','failed')))
              order by r.created_at,r.id""", (str(classroom_id),)).fetchall()
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None
    response.headers.update(PRIVATE)
    return rows


def review_pictures(conn, job_id: str, review: dict):
    if review["kind"] == "title":
        return []
    # The review pins its retained checkpoint. Never use a later attempt or browser path.
    checkpoint = PostgresSaver(conn).get_tuple({"configurable": {
        "thread_id": job_id, "checkpoint_id": review["checkpoint_id"],
    }})
    pictures = []
    try:
        state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"]) if checkpoint else None
    except ValueError:
        state = None
    if state:
        for char in state.characters:
            held = char.char_id == review["subject_id"] and review["kind"] == "character_reference"
            pictures.append({"asset_id": f"ref-{char.char_id}", "label": f"Reference: {char.name}",
                             "path": char.canonical_ref_image, "state": "held" if held else "available" if char.canonical_ref_image else "not_generated"})
        for scene in state.scenes:
            held = scene.scene_id == review["subject_id"] and review["kind"] == "scene_image"
            path = review["subject"].get("image_path") if held else scene.final_image_ref
            pictures.append({"asset_id": f"scene-{scene.scene_id}", "label": scene.caption or scene.text_excerpt,
                             "path": path, "state": "held" if held else "available" if path else "unavailable" if scene.attempts else "not_generated"})
    else:
        pictures.append({"asset_id": "context-unavailable", "label": "Other story pictures",
                         "path": None, "state": "unavailable"})
    if review["kind"] not in ("story_text", "optional_themes") and not any(p["state"] == "held" for p in pictures):
        pictures.append({"asset_id": "held", "label": "Picture needing review",
                         "path": review["subject"].get("image_path"), "state": "held"})
    return pictures


@hold_router.get("/teacher/jobs/{job_id}/moderation-review")
def teacher_review_detail(job_id: UUID, response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn:
            job, review = teacher_review(conn, str(job_id), str(user.id))
            response.headers.update(PRIVATE)
            if not review or job["status"] != "awaiting_teacher":
                clearances = []
                pending = conn.execute("""select * from job_moderation_reviews where job_id=%s
                  and decision in ('allow','replace') and decision_epoch=%s and dispatch_state in ('pending','failed')""",
                                       (job_id, job["generation_epoch"])).fetchone() if job["status"] == "queued" else None
                if job["moderation_mode"] == "teacher_review_v1" and job["status"] in ("queued", "running", "awaiting_confirm", "complete"):
                    checkpoint = PostgresSaver(conn).get_tuple({"configurable": {"thread_id": str(job_id)}})
                    state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"]) if checkpoint else None
                    seen = set()
                    for allowed in conn.execute("""select * from job_moderation_reviews where job_id=%s
                      and decision='allow' and kind in ('scene_image','character_reference','story_text') order by decided_at desc,id""", (job_id,)).fetchall():
                        key = (allowed["kind"], allowed["subject_id"])
                        if key in seen:
                            continue
                        if allowed["kind"] == "story_text":
                            clearance = state.input.moderation_clearance if state else None
                            if (clearance and str(clearance.review_id) == str(allowed["id"])
                                    and clearance.subject_version == allowed["subject_version"]
                                    and state.input.redacted_text == allowed["subject"].get("story_text")):
                                seen.add(key)
                                clearances.append({"review_id": str(allowed["id"]), "subject_version": allowed["subject_version"],
                                                   "label": "Story text"})
                            continue
                        if allowed["kind"] == "character_reference":
                            char = next((c for c in state.characters if c.char_id == allowed["subject_id"]), None) if state else None
                            if char and char.ref_moderation_status == "teacher_allowed" and char.canonical_ref_image == allowed["subject"].get("image_path"):
                                seen.add(key)
                                clearances.append({"review_id": str(allowed["id"]), "subject_version": allowed["subject_version"],
                                                   "label": f"Reference: {char.name}"})
                            continue
                        scene = next((s for s in state.scenes if s.scene_id == allowed["subject_id"]), None) if state else None
                        if scene and scene.moderation_status == "teacher_allowed" and scene.final_image_ref == allowed["subject"].get("image_path"):
                            seen.add(key)
                            clearances.append({"review_id": str(allowed["id"]), "subject_version": allowed["subject_version"],
                                               "label": scene.caption or scene.scene_id})
                return {"status": job["status"], "review_id": None, "generation_epoch": job["generation_epoch"],
                        "clearances": clearances, "title": job["title"],
                        "story_text": pending["subject"].get("story_text") if pending else None,
                        "pending_command": {"review_id": str(pending["id"]), "subject_version": pending["subject_version"],
                            "expected_epoch": pending["decision_epoch"] - 1, "request_id": str(pending["request_id"]),
                            "action": pending["decision"], "policy_version": pending["decision_policy_version"],
                            "confirmed_criteria": pending["confirmed_criteria"], "confirmed": True} if pending else None}
            pictures = review_pictures(conn, str(job_id), review)
            retained = validate_review_checkpoint(conn, str(job_id), review)
            replacement_reason = (replacement_disabled_reason(retained, review["kind"], review["subject_id"], job["image_count"] or 0)
                                  if retained else "replacement_source_unavailable")
            author = conn.execute("select display_nickname from profiles where id=%s", (job["profile_id"],)).fetchone()
            return {"status": job["status"], "review_id": str(review["id"]),
                    "subject_id": review["subject_id"], "subject_version": review["subject_version"],
                    "generation_epoch": job["generation_epoch"], "title": job["title"],
                    "author": author["display_nickname"] if author else None,
                    "story_text": review["subject"].get("story_text"),
                    "subject_title": review["subject"].get("title") if review["kind"] == "title" else None,
                    "kind": review["kind"], "criteria": review["criteria"], "policy_version": review["policy_version"],
                    "origin": "optional_theme" if review["kind"] == "optional_themes" else "shared_safety",
                    "detected_themes": review["subject"].get("detected_themes", []),
                    "theme_check": review["subject"].get("theme_check"),
                    "current_policy_version": TEACHER_MODERATION_POLICY_VERSION,
                    "settings_snapshot": review["settings_snapshot"],
                    "classifier_evidence": review["classifier_evidence"],
                    "ready": job["worker_finished_at"] is not None,
                    "replacement_available": replacement_reason is None,
                    "replacement_disabled_reason": replacement_reason,
                    "dispatch_state": review["dispatch_state"],
                    "withdraws_review_id": str(review["withdraws_review_id"]) if review["withdraws_review_id"] else None,
                    "pictures": [{k: v for k, v in picture.items() if k != "path"} for picture in pictures]}
    except (psycopg.Error, ValueError):
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None


class ReviewReveal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_id: UUID
    subject_version: str


class ReviewDecision(ReviewReveal):
    expected_epoch: int = Field(ge=0)
    request_id: UUID
    action: Literal["allow", "replace", "stop"]
    policy_version: str
    confirmed_criteria: list[str]
    confirmed: Literal[True]


def command_state(job, review):
    return {"job_id": str(job["id"]), "status": job["status"],
            "generation_epoch": job["generation_epoch"],
            "review_id": str(review["id"]) if review else None,
            "dispatch_state": review["dispatch_state"] if review else None}


def command_conflict(code, job, review=None):
    raise HTTPException(409, {"code": code, **command_state(job, review)}, headers=PRIVATE)


def stop_held_job(conn, job, body, user_id, *, teacher=False):
    review = conn.execute("select * from job_moderation_reviews where job_id=%s and id=%s",
                          (job["id"], body.review_id)).fetchone()
    prior = conn.execute("select * from job_moderation_reviews where job_id=%s and request_id=%s",
                         (job["id"], body.request_id)).fetchone()
    if prior:
        if (str(prior["id"]) != str(body.review_id) or str(prior["actor_id"]) != user_id
                or prior["decision"] != "stop" or prior["decision_epoch"] != body.expected_epoch + 1
                or (teacher and (prior["subject_version"] != body.subject_version
                    or prior["decision_policy_version"] != body.policy_version
                    or prior["confirmed_criteria"] != body.confirmed_criteria))):
            command_conflict("request_conflict", job, review)
        return command_state(job, prior)
    if conn.execute("select 1 from job_moderation_reviews where job_id=%s and id=%s",
                    (job["id"], body.request_id)).fetchone():
        command_conflict("request_conflict", job, review)
    if (not review or review["decision"] is not None or job["status"] != "awaiting_teacher"
            or job["generation_epoch"] != body.expected_epoch
            or (teacher and review["subject_version"] != body.subject_version)):
        command_conflict("review_changed", job, review)
    if job["worker_finished_at"] is None:
        command_conflict("finishing_current_step", job, review)
    conn.execute("""update job_moderation_reviews set decision='stop',actor_id=%s,decided_at=now(),
      decision_policy_version=%s,confirmed_criteria=%s,request_id=%s,decision_epoch=%s,
      dispatch_state=null,dispatch_kind=null,dispatch_error_code=null where id=%s""",
                 (user_id, body.policy_version if teacher else None,
                  body.confirmed_criteria if teacher else [], body.request_id, body.expected_epoch + 1, body.review_id))
    job = conn.execute("""update jobs set status='stopped',generation_epoch=generation_epoch+1,
      pages='[]',reveal='{}',approved_at=null,rejected_at=null where id=%s returning *""", (job["id"],)).fetchone()
    return command_state(job, {**review, "dispatch_state": None})


class ChildStop(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_id: UUID
    expected_epoch: int = Field(ge=0)
    request_id: UUID
    confirmed: Literal[True]


@hold_router.post("/jobs/{job_id}/stop")
def child_stop(job_id: UUID, body: ChildStop, response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn, conn.transaction():
            job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
            if not job or str(job["profile_id"]) != str(user.id) or job["status"] == "deleting":
                raise HTTPException(404, "job_not_found", headers=PRIVATE)
            conn.execute("select id from profiles where id=%s for share", (user.id,))
            if job["moderation_mode"] != "teacher_review_v1" or not active_author(conn, job):
                raise HTTPException(404, "job_not_found", headers=PRIVATE)
            result = stop_held_job(conn, job, body, str(user.id))
        response.headers.update(PRIVATE)
        return result
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None


def dispatch_review(job_id, review_id, epoch):
    """Explicit delivery of an already committed continuation. Reads never enqueue."""
    from app.main import JOB_TIMEOUT_SECONDS
    from rq.exceptions import DuplicateJobError

    with connect() as conn:
        row = conn.execute("select * from job_moderation_reviews where id=%s and job_id=%s",
                           (review_id, job_id)).fetchone()
        if not row or row["dispatch_state"] not in ("pending", "failed"):
            return
    dispatch_id = f"review-{job_id}-{review_id}-{epoch}"
    try:
        queue = get_queue()
        try:
            queue.enqueue("worker.run_job.run_review_storybook_job", job_id,
                            expected_epoch=epoch, review_id=str(review_id),
                            job_id=dispatch_id, unique=True,
                            job_timeout=JOB_TIMEOUT_SECONDS)
        except DuplicateJobError:
            existing = queue.fetch_job(dispatch_id)
            if not existing:
                raise RuntimeError("dispatch_unavailable") from None
            status = existing.get_status()
            if status == "failed" and row["dispatch_kind"] == "anchor_withdrawal" and row["dispatch_state"] == "failed":
                existing.requeue()
            elif status not in ("queued", "started", "finished"):
                raise RuntimeError("dispatch_unavailable") from None
    except Exception:
        # An ambiguous Redis result is retried with the same identity and epoch.
        with connect() as conn:
            conn.execute("""update job_moderation_reviews set dispatch_error_code='queue_unavailable'
              where id=%s and dispatch_state='pending'""", (review_id,))
        return
    with connect() as conn:
        conn.execute("""update job_moderation_reviews set dispatch_state='queued',dispatch_error_code=null
          where id=%s and dispatch_state in ('pending','failed')""", (review_id,))


def validate_review_checkpoint(conn, job_id, review):
    checkpoint = PostgresSaver(conn).get_tuple({"configurable": {
        "thread_id": job_id, "checkpoint_id": review["checkpoint_id"],
    }}) if review["checkpoint_id"] else None
    if not checkpoint:
        return None
    try:
        state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"])
    except ValueError:
        return None
    saved = state.moderation_context.review
    if (state.story_id != job_id or state.moderation_context.mode != "teacher_review_v1"
            or not saved or str(saved.review_id) != str(review["id"]) or saved.subject_id != review["subject_id"]
            or saved.kind != review["kind"]
            or saved.subject_version != review["subject_version"] or saved.resolution is not None):
        return None
    if saved.kind == "optional_themes":
        context = state.moderation_context
        return state if (has_bound_theme_review(state)
            and review["criteria"] == saved.criteria
            and review["subject"].get("story_text") == state.input.redacted_text
            and review["subject"].get("detected_themes") == [d.model_dump() for d in context.detected_themes]
            and review["subject"].get("theme_check") == context.optional_theme_check.model_dump()
            and review["settings_snapshot"].get("theme_ids") == context.theme_ids
            and review["settings_snapshot"].get("settings_version") == context.settings_version) else None
    if saved.kind == "story_text":
        text = state.input.redacted_text
        return state if (saved.subject_id == "input" and text is not None
            and text == review["subject"].get("story_text")
            and hashlib.sha256(text.encode("utf-8")).hexdigest() == saved.subject_version) else None
    if saved.kind == "character_reference":
        char = next((c for c in state.characters if c.char_id == saved.subject_id), None)
        return state if char and char.canonical_ref_image == review["subject"].get("image_path") and char.canonical_ref_image else None
    scene = next((s for s in state.scenes if s.scene_id == saved.subject_id), None)
    if (review["kind"] != "scene_image" or not scene or scene.final_image_ref != review["subject"].get("image_path")
            or not any(a.image_ref == scene.final_image_ref for a in scene.attempts)):
        return None
    return state


def review_subject_bytes(review):
    """Exact private subject for decision, continuation and withdrawal checks."""
    if review["kind"] == "title":
        title = review["subject"].get("title")
        if not isinstance(title, str):
            raise RuntimeError("moderation_subject_unavailable")
        return title.encode("utf-8")
    if review["kind"] in ("story_text", "optional_themes"):
        text = review["subject"].get("story_text")
        if not isinstance(text, str):
            raise RuntimeError("moderation_subject_unavailable")
        return text.encode("utf-8")
    return providers.download_book_image(review["subject"]["image_path"])


@hold_router.post("/teacher/jobs/{job_id}/moderation-review/decision")
def teacher_decision(job_id: UUID, body: ReviewDecision, response: Response, user=Depends(get_current_user)):
    jid, uid = str(job_id), str(user.id)
    replay = False
    try:
        with connect() as conn, conn.transaction():
            job = conn.execute("select * from jobs where id=%s for update", (jid,)).fetchone()
            if not job or job["status"] == "deleting":
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            role = conn.execute("select role from profiles where id=%s", (uid,)).fetchone()
            if not role or role["role"] != "teacher":
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
            teacher_classroom(conn, str(job["classroom_id"]), uid)
            conn.execute("select id from profiles where id=%s for update", (job["profile_id"],))
            if job["moderation_mode"] != "teacher_review_v1" or (body.action != "stop" and not active_author(conn, job)):
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            if body.action == "stop":
                result = stop_held_job(conn, job, body, uid, teacher=True)
                response.headers.update(PRIVATE)
                return result
            review = conn.execute("select * from job_moderation_reviews where job_id=%s and id=%s",
                                  (jid, body.review_id)).fetchone()
            prior = conn.execute("select * from job_moderation_reviews where job_id=%s and request_id=%s",
                                 (jid, body.request_id)).fetchone()
            if conn.execute("""select 1 from job_moderation_reviews where job_id=%s
              and id=%s and withdraws_review_id is not null""", (jid, body.request_id)).fetchone():
                command_conflict("request_conflict", job, review)
            if prior:
                if (str(prior["id"]) != str(body.review_id) or str(prior["actor_id"]) != uid
                        or prior["subject_version"] != body.subject_version or prior["decision"] != body.action
                        or prior["decision_epoch"] != body.expected_epoch + 1
                        or prior["decision_policy_version"] != body.policy_version
                        or prior["confirmed_criteria"] != body.confirmed_criteria):
                    command_conflict("request_conflict", job, review)
                replay = True
            else:
                if (not review or review["decision"] is not None or job["status"] != "awaiting_teacher"
                        or job["generation_epoch"] != body.expected_epoch
                        or review["subject_version"] != body.subject_version):
                    command_conflict("review_changed", job, review)
                if job["worker_finished_at"] is None:
                    command_conflict("finishing_current_step", job, review)
                if body.action == "allow" and (body.policy_version != TEACHER_MODERATION_POLICY_VERSION
                        or set(body.confirmed_criteria) != set(review["criteria"])):
                    command_conflict("policy_confirmation_required", job, review)
                retained = validate_review_checkpoint(conn, jid, review) if review["kind"] != "title" else None
                if review["kind"] != "title" and retained is None:
                    command_conflict("checkpoint_unavailable", job, review)
                if body.action == "replace":
                    if review["kind"] == "title":
                        raise HTTPException(422, "replacement_not_available", headers=PRIVATE)
                    reason = replacement_disabled_reason(retained, review["kind"], review["subject_id"], job["image_count"] or 0)
                    if reason:
                        raise HTTPException(422, reason, headers=PRIVATE)
                # Bound to retained immutable bytes, including recovery after a failed read.
                try:
                    contents = review_subject_bytes(review)
                except Exception:
                    command_conflict("image_unavailable", job, review)
                if hashlib.sha256(contents).hexdigest() != review["subject_version"]:
                    command_conflict("image_unavailable", job, review)
                conn.execute("""update job_moderation_reviews set decision=%s,actor_id=%s,decided_at=now(),
                  decision_policy_version=%s,confirmed_criteria=%s,request_id=%s,decision_epoch=%s,
                  dispatch_state='pending',dispatch_kind='resume' where id=%s""",
                             (body.action, uid, body.policy_version, body.confirmed_criteria, body.request_id,
                              body.expected_epoch + 1, body.review_id))
                conn.execute("""update jobs set status='queued',generation_epoch=generation_epoch+1,
                  worker_finished_at=null where id=%s""", (jid,))
                if review["kind"] == "title":
                    conn.execute("update jobs set title=%s where id=%s", (review["subject"]["title"], jid))
        dispatch_review(jid, body.review_id, body.expected_epoch + 1)
        with connect() as conn:
            job, _ = teacher_review(conn, jid, uid)
            review = conn.execute("select * from job_moderation_reviews where id=%s", (body.review_id,)).fetchone()
            result = command_state(job, review)
        response.status_code = 200 if replay else 202
        response.headers.update(PRIVATE)
        return result
    except (psycopg.Error, ValueError):
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None


class ReviewWithdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clearance_review_id: UUID
    subject_version: str
    expected_epoch: int = Field(ge=0)
    request_id: UUID
    confirmed: Literal[True]


@hold_router.post("/teacher/jobs/{job_id}/moderation-review/withdraw")
def teacher_withdraw(job_id: UUID, body: ReviewWithdrawal, response: Response, user=Depends(get_current_user)):
    jid, uid = str(job_id), str(user.id)
    replay = False
    try:
        with connect() as conn, conn.transaction():
            job = conn.execute("select * from jobs where id=%s for update", (jid,)).fetchone()
            if not job or job["status"] == "deleting":
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            role = conn.execute("select role from profiles where id=%s", (uid,)).fetchone()
            if not role or role["role"] != "teacher":
                raise HTTPException(403, "teacher_required", headers=PRIVATE)
            teacher_classroom(conn, str(job["classroom_id"]), uid)
            prior = conn.execute("select * from job_moderation_reviews where job_id=%s and (id=%s or request_id=%s)",
                                 (jid, body.request_id, body.request_id)).fetchone()
            clearance = conn.execute("select * from job_moderation_reviews where id=%s and job_id=%s",
                                     (body.clearance_review_id, jid)).fetchone()
            if prior:
                if (str(prior["withdraws_review_id"]) != str(body.clearance_review_id)
                        or prior["subject_version"] != body.subject_version
                        or prior["settings_snapshot"].get("withdrawal_epoch") != body.expected_epoch + 1
                        or prior["settings_snapshot"].get("withdrawal_actor_id") != uid):
                    command_conflict("request_conflict", job, prior)
                replay = True
            else:
                if (job["moderation_mode"] != "teacher_review_v1" or job["status"] not in ("queued", "running", "awaiting_confirm", "complete")
                        or job["generation_epoch"] != body.expected_epoch or not clearance
                        or clearance["decision"] != "allow" or clearance["kind"] not in ("scene_image", "character_reference", "story_text")
                        or clearance["subject_version"] != body.subject_version
                        or conn.execute("select 1 from job_moderation_reviews where job_id=%s and decision is null", (jid,)).fetchone()):
                    command_conflict("clearance_changed", job)
                checkpoint = PostgresSaver(conn).get_tuple({"configurable": {"thread_id": jid}})
                state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"]) if checkpoint else None
                if clearance["kind"] == "story_text":
                    text_clearance = state.input.moderation_clearance if state else None
                    if (not text_clearance or str(text_clearance.review_id) != str(clearance["id"])
                            or text_clearance.subject_version != clearance["subject_version"]
                            or state.input.redacted_text != clearance["subject"].get("story_text")):
                        command_conflict("clearance_changed", job)
                elif clearance["kind"] == "character_reference":
                    char = next((c for c in state.characters if c.char_id == clearance["subject_id"]), None) if state else None
                    if not char or char.canonical_ref_image != clearance["subject"].get("image_path") or char.ref_moderation_status != "teacher_allowed":
                        command_conflict("clearance_changed", job)
                else:
                    scene = next((s for s in state.scenes if s.scene_id == clearance["subject_id"]), None) if state else None
                    if not scene or scene.final_image_ref != clearance["subject"].get("image_path") or scene.moderation_status != "teacher_allowed":
                        command_conflict("clearance_changed", job)
                snapshot = {**clearance["settings_snapshot"], "withdrawal_epoch": body.expected_epoch + 1,
                            "withdrawal_actor_id": uid}
                conn.execute("""insert into job_moderation_reviews
                  (id,job_id,kind,subject_id,subject_version,subject,criteria,policy_version,settings_snapshot,
                   classifier_evidence,return_node,withdraws_review_id,dispatch_kind,dispatch_state)
                  values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,'anchor_withdrawal','pending')""", (
                    body.request_id, jid, clearance["kind"], clearance["subject_id"], clearance["subject_version"], Jsonb(clearance["subject"]),
                    clearance["criteria"], clearance["policy_version"], Jsonb(snapshot), Jsonb(clearance["classifier_evidence"]),
                    body.clearance_review_id,
                ))
                conn.execute("""update jobs set status='awaiting_teacher',current_stage='moderation_review',
                  generation_epoch=generation_epoch+1,approved_at=null,rejected_at=null,pages='[]',reveal='{}',
                  worker_finished_at=null where id=%s""", (jid,))
        dispatch_review(jid, body.request_id, body.expected_epoch + 1)
        with connect() as conn:
            job, review = teacher_review(conn, jid, uid)
            if not review or str(review["id"]) != str(body.request_id):
                review = conn.execute("select * from job_moderation_reviews where id=%s", (body.request_id,)).fetchone()
        response.status_code = 200 if replay else 202
        response.headers.update(PRIVATE)
        return command_state(job, review)
    except (psycopg.Error, ValueError):
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None


def review_asset(conn, job_id: str, user_id: str, review_id: UUID, version: str, asset_id: str | None):
    job, review = teacher_review(conn, job_id, user_id)
    if (not review or job["status"] != "awaiting_teacher" or str(review["id"]) != str(review_id)
            or review["subject_version"] != version):
        raise HTTPException(409, "review_changed", headers=PRIVATE)
    picture = next((p for p in review_pictures(conn, job_id, review)
                    if (p["state"] == "held" if asset_id is None else p["asset_id"] == asset_id and p["state"] == "available")), None)
    path = picture["path"] if picture else None
    if not path or not path.startswith(f"{job_id}/"):
        raise HTTPException(404, "image_unavailable", headers=PRIVATE)
    return path, job["generation_epoch"]


def teacher_picture_bytes(job_id, user_id, review_id, version, asset_id=None):
    try:
        with connect() as conn:
            selected = review_asset(conn, job_id, user_id, review_id, version, asset_id)
        try:
            contents = providers.download_book_image(selected[0])
        except Exception:
            raise HTTPException(503, "image_unavailable", headers=PRIVATE) from None
        if asset_id is None and hashlib.sha256(contents).hexdigest() != version:
            raise HTTPException(503, "image_unavailable", headers=PRIVATE)
        with connect() as conn:
            if review_asset(conn, job_id, user_id, review_id, version, asset_id) != selected:
                raise HTTPException(409, "review_changed", headers=PRIVATE)
        return Response(contents, media_type="image/png", headers=PRIVATE)
    except (psycopg.Error, ValueError):
        raise HTTPException(503, "image_unavailable", headers=PRIVATE) from None


@hold_router.post("/teacher/jobs/{job_id}/moderation-review/reveal")
def teacher_reveal(job_id: UUID, body: ReviewReveal, user=Depends(get_current_user)):
    return teacher_picture_bytes(str(job_id), str(user.id), body.review_id, body.subject_version)


@hold_router.get("/teacher/jobs/{job_id}/moderation-review/images/{asset_id}")
def teacher_context_image(job_id: UUID, asset_id: str, review_id: UUID, subject_version: str,
                          user=Depends(get_current_user)):
    return teacher_picture_bytes(str(job_id), str(user.id), review_id, subject_version, asset_id)


class StaleGeneration(BaseException):
    """Safety fencing must bypass node/provider best-effort Exception handlers."""


def connect():
    return psycopg.connect(settings.supabase_db_url, autocommit=True, row_factory=dict_row)


def active_author(conn, job: dict) -> bool:
    return conn.execute("""select 1 from profiles where id=%s and role='student'
      and classroom_id=%s and removed_at is null
      and password_completed_version=password_reset_version""",
                        (job["profile_id"], job["classroom_id"])).fetchone() is not None


def insert_review_job(values: dict, *, title_evidence: list | None = None) -> None:
    # Recheck authorization in the insert transaction, after privacy/provider work.
    with connect() as conn, conn.transaction():
        author = conn.execute("select * from profiles where id=%s for update", (values["profile_id"],)).fetchone()
        if not author or not active_author(conn, values):
            raise HTTPException(403, "account_unavailable", headers=PRIVATE)
        classroom = conn.execute("""select moderation_theme_ids,moderation_settings_version
          from classrooms where id=%s for share""", (values["classroom_id"],)).fetchone()
        values["moderation_settings_snapshot"].update(
            theme_ids=classroom["moderation_theme_ids"], settings_version=classroom["moderation_settings_version"])
        conn.execute("""insert into jobs(id,status,current_stage,input_text,title,truncated,
          style_preset_id,profile_id,classroom_id,moderation_mode,moderation_settings_snapshot)
          values (%s,'queued','queued',%s,%s,%s,%s,%s,%s,'teacher_review_v1',%s)""", (
            values["id"], values["input_text"], "My story" if title_evidence is not None else values["title"], values["truncated"],
            values["style_preset_id"], values["profile_id"], values["classroom_id"],
            Jsonb(values["moderation_settings_snapshot"]),
        ))
        if title_evidence is not None:
            version = hashlib.sha256(values["title"].encode("utf-8")).hexdigest()
            review_id = uuid5(UUID(values["id"]), f"title:title:{version}:0")
            conn.execute("""insert into job_moderation_reviews(id,job_id,kind,subject_id,subject_version,
              subject,criteria,policy_version,settings_snapshot,classifier_evidence,return_node)
              values (%s,%s,'title','title',%s,%s,%s,%s,%s,%s,'input_gate')""", (
                review_id, values["id"], version, Jsonb({"title": values["title"], "story_text": values["input_text"]}),
                list(TEACHER_MODERATION_CRITERIA), values["moderation_settings_snapshot"]["policy_version"],
                Jsonb(values["moderation_settings_snapshot"]), Jsonb([e.model_dump(mode="json") for e in title_evidence]),
            ))
            conn.execute("""update jobs set status='awaiting_teacher',current_stage='moderation_review',
              generation_epoch=1,worker_finished_at=now() where id=%s""", (values["id"],))


def assert_current(conn, job_id: str, epoch: int) -> dict:
    job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
    if (not job or job["generation_epoch"] != epoch or job["status"] not in ("queued", "running")
            or not active_author(conn, job)
            or conn.execute("select 1 from job_moderation_reviews where job_id=%s and decision is null", (job_id,)).fetchone()):
        raise StaleGeneration()
    return job


def project_hold(conn, job_id: str, state: StoryMemory, checkpoint_id: str) -> int:
    review, context = state.moderation_context.review, state.moderation_context
    if (not review or review.kind not in ("scene_image", "character_reference", "story_text", "optional_themes") or review.resolution is not None
            or not checkpoint_id or not context.policy_version):
        raise RuntimeError("invalid_moderation_checkpoint")
    if review.kind in ("story_text", "optional_themes"):
        text = state.input.redacted_text
        if (text is None or review.subject_id != "input"
                or hashlib.sha256(text.encode("utf-8")).hexdigest() != review.subject_version):
            raise RuntimeError("invalid_moderation_subject")
        subject = {"story_text": text}
        if review.kind == "optional_themes":
            subject.update(detected_themes=[d.model_dump() for d in context.detected_themes],
                           theme_check=context.optional_theme_check.model_dump())
    elif review.kind == "character_reference":
        char = next(c for c in state.characters if c.char_id == review.subject_id)
        path = char.canonical_ref_image
        subject = {"image_path": path, "char_id": char.char_id, "prompt": char.ref_generation_prompt,
                   "reference_paths": []}
    else:
        scene = next(s for s in state.scenes if s.scene_id == review.subject_id)
        path = scene.final_image_ref
        selected = next((a for a in scene.attempts if a.image_ref == path), None)
        subject = {"image_path": path, "scene_id": scene.scene_id,
                   "prompt": selected.prompt if selected else scene.prompt,
                   "reference_paths": [c.canonical_ref_image for c in state.characters
                                       if c.char_id in scene.characters_present and c.canonical_ref_image]}
    if review.kind not in ("story_text", "optional_themes"):
        if not path or not path.startswith(f"{job_id}/"):
            raise RuntimeError("invalid_moderation_subject")
        subject.update(image_hash=review.subject_version, story_text=state.input.redacted_text or state.input.raw_text)
    with conn.transaction():
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        prior = conn.execute("select id from job_moderation_reviews where id=%s and job_id=%s",
                             (review.review_id, job_id)).fetchone()
        if prior and job["status"] == "awaiting_teacher":
            return job["generation_epoch"]
        if job["status"] == "failed" and job["error"] in ("hold_projection_failed", "worker_stopped"):
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
          worker_finished_at=null,image_count=greatest(coalesce(image_count,0),%s) where id=%s""",
                     (state.cost.image_count, job_id))
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


def can_reconcile_hold(conn, job: dict) -> bool:
    if job["moderation_mode"] != "teacher_review_v1":
        return False
    if job["status"] == "awaiting_teacher":
        if conn.execute("""select 1 from job_moderation_reviews where job_id=%s
          and decision is null and withdraws_review_id is not null and checkpoint_id is null""", (job["id"],)).fetchone():
            return False
        return job["worker_finished_at"] is None
    if job["status"] != "failed" or job["worker_finished_at"] is None:
        return False
    if job["error"] == "hold_projection_failed":
        return True
    if job["error"] == "worker_stopped":
        checkpoint = PostgresSaver(conn).get_tuple({"configurable": {"thread_id": str(job["id"])}})
        if checkpoint:
            state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"])
            review = state.moderation_context.review
            return review is not None and review.kind in ("scene_image", "character_reference", "story_text", "optional_themes") and review.resolution is None
    return False


@hold_router.get("/jobs/{job_id}/state")
def job_state(job_id: UUID, response: Response, user=Depends(get_current_user)):
    with connect() as conn:
        job = product_job(conn, str(job_id), str(user.id))
        repairable = can_reconcile_hold(conn, job)
        author = str(job["profile_id"]) == str(user.id)
        review = conn.execute("select id from job_moderation_reviews where job_id=%s and decision is null",
                              (job_id,)).fetchone() if author and job["status"] == "awaiting_teacher" else None
    response.headers.update(PRIVATE)
    return {"job_id": str(job_id), "status": job["status"], "moderation_mode": job["moderation_mode"],
            "generation_epoch": job["generation_epoch"], "worker_finished": job["worker_finished_at"] is not None,
            "can_reconcile_hold": (author and repairable),
            "review_id": str(review["id"]) if review else None,
            "saved_writing": {"text": job["input_text"], "title": job["title"] or ""}
                if author and job["status"] == "stopped" and job["moderation_mode"] == "teacher_review_v1" else None}


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
    if (not state.input.moderation or (not state.input.moderation.passed and not has_text_clearance(state))
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
        repairable = can_reconcile_hold(conn, job)
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
