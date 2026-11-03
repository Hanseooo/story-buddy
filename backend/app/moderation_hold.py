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
from providers import check_text
from app.auth import get_current_user
from app.config import settings
from app.moderation_policy import OPTIONAL_THEMES, POLICY, TEACHER_MODERATION_CRITERIA, TEACHER_MODERATION_POLICY_VERSION
from app.queue import get_queue
from contracts.story_memory import StoryMemory
from pipeline.char_ref_mod import screen_reference
from pipeline.output_mod import screen_page
from pipeline.input_gate import has_text_clearance
from pipeline.optional_themes import has_bound_theme_review
from pipeline.reveal import has_versions
from pipeline.moderation_replace import replacement_disabled_reason

hold_router = APIRouter()
PRIVATE = {"Cache-Control": "private, no-store"}
PAGE_PENCIL_KINDS = ("page_pencil_text", "page_pencil_result")


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
              (r.decision in ('allow','replace') or (r.decision='stop' and r.kind='character_pencil_text')) as continuation_pending,
              (j.worker_finished_at is not null) as ready
              from job_moderation_reviews r join jobs j on j.id=r.job_id
              left join profiles p on p.id=j.profile_id
              where j.classroom_id=%s and ((j.status='awaiting_teacher' and r.decision is null)
                or (j.status='complete' and r.decision is null and r.kind = any(%s))
                or (j.status='queued' and (r.decision in ('allow','replace') or (r.decision='stop' and r.kind='character_pencil_text'))
                    and r.decision_epoch=j.generation_epoch
                    and r.dispatch_state in ('pending','failed')))
              order by r.created_at,r.id""", (str(classroom_id), list(PAGE_PENCIL_KINDS))).fetchall()
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable", headers=PRIVATE) from None
    response.headers.update(PRIVATE)
    return rows


def review_pictures(conn, job_id: str, review: dict):
    if review["kind"] == "title":
        return []
    if review["kind"] in PAGE_PENCIL_KINDS:
        # magic-pencil 10: the finished book stays readable, so the context is the page as it is.
        before = {"asset_id": "page-before", "label": "The page before the change",
                  "path": review["subject"].get("before_path"), "state": "available"}
        return [before] if review["kind"] == "page_pencil_text" else [before, {
            "asset_id": "held", "label": "Picture needing review", "path": review["subject"].get("image_path"), "state": "held"}]
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
    if review["kind"] not in ("story_text", "optional_themes", "character_pencil_text") and not any(p["state"] == "held" for p in pictures):
        pictures.append({"asset_id": "held", "label": "Picture needing review",
                         "path": review["subject"].get("image_path"), "state": "held"})
    return pictures


@hold_router.get("/teacher/jobs/{job_id}/moderation-review")
def teacher_review_detail(job_id: UUID, response: Response, user=Depends(get_current_user)):
    try:
        with connect() as conn:
            job, review = teacher_review(conn, str(job_id), str(user.id))
            response.headers.update(PRIVATE)
            if not review or job["status"] != ("complete" if review["kind"] in PAGE_PENCIL_KINDS else "awaiting_teacher"):
                clearances = []
                pending = conn.execute("""select * from job_moderation_reviews where job_id=%s
                  and (decision in ('allow','replace') or (decision='stop' and kind='character_pencil_text'))
                  and decision_epoch=%s and dispatch_state in ('pending','failed')""",
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
            if review["kind"] in PAGE_PENCIL_KINDS:   # no checkpoint: the slot is in the pencil log (OD-01)
                from app.page_pencil import page_replacement_disabled_reason
                use = conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
                  and source='page_pencil' and version_id=%s""", (str(job_id), review["subject_id"])).fetchone()
                replacement_reason = page_replacement_disabled_reason(job, review["kind"], use)
            else:
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
                    "pencil_text": review["subject"].get("pencil_text")
                        if review["kind"] in ("character_pencil_text", *PAGE_PENCIL_KINDS) else None,
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
    if saved.kind == "character_pencil_text":
        use = next((u for u in state.pencil_uses if u.use_id == saved.subject_id), None)
        return state if (use and state.reference_pencil == use.use_id and use.text_moderation == "held"
            and use.text == review["subject"].get("pencil_text")
            and hashlib.sha256(use.text.encode("utf-8")).hexdigest() == saved.subject_version) else None
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
    if review["kind"] in ("story_text", "optional_themes", "character_pencil_text", "page_pencil_text"):
        text = review["subject"].get("story_text" if review["kind"] in ("story_text", "optional_themes") else "pencil_text")
        if not isinstance(text, str):
            raise RuntimeError("moderation_subject_unavailable")
        return text.encode("utf-8")
    return providers.download_book_image(review["subject"]["image_path"])


@hold_router.post("/teacher/jobs/{job_id}/moderation-review/decision")
def teacher_decision(job_id: UUID, body: ReviewDecision, response: Response, user=Depends(get_current_user)):
    jid, uid = str(job_id), str(user.id)
    replay = False
    with connect() as conn:   # A review's kind never changes, so this read needs no lock.
        page_pencil = conn.execute("""select 1 from job_moderation_reviews where job_id=%s and id=%s
          and kind = any(%s)""", (jid, body.review_id, list(PAGE_PENCIL_KINDS))).fetchone()
    if page_pencil:
        from app.page_pencil import page_pencil_decision
        return page_pencil_decision(jid, uid, body, response)
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
            # OD-08: stopping a held pencil text ends only that change; the story goes on. A removed
            # author cannot come back to the reveal, so their story stops as any other hold would.
            request_only = body.action == "stop" and active_author(conn, job) and bool(conn.execute(
                "select 1 from job_moderation_reviews where job_id=%s and id=%s and kind='character_pencil_text'",
                (jid, body.review_id)).fetchone())
            if job["moderation_mode"] != "teacher_review_v1" or (
                    body.action != "stop" and not active_author(conn, job)):
                raise HTTPException(404, "review_not_found", headers=PRIVATE)
            if body.action == "stop" and not request_only:
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
    if (not review or str(review["id"]) != str(review_id)
            or job["status"] != ("complete" if review["kind"] in PAGE_PENCIL_KINDS else "awaiting_teacher")
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
    if (not review or review.kind not in ("scene_image", "character_reference", "story_text", "optional_themes",
                                          "character_pencil_text") or review.resolution is not None
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
    elif review.kind == "character_pencil_text":
        use = next((u for u in state.pencil_uses if u.use_id == review.subject_id), None)
        if use is None or hashlib.sha256(use.text.encode("utf-8")).hexdigest() != review.subject_version:
            raise RuntimeError("invalid_moderation_subject")
        char = next(c for c in state.characters if c.char_id == use.char_id)
        subject = {"pencil_text": use.text, "char_id": char.char_id, "char_name": char.name,
                   "image_path": use.before_path, "story_text": state.input.redacted_text or state.input.raw_text}
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
    if review.kind not in ("story_text", "optional_themes", "character_pencil_text"):
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
        record_pencil_uses(conn, job_id, state)
        conn.execute("""update jobs set status='awaiting_teacher',current_stage='moderation_review',
          generation_epoch=generation_epoch+1,reveal='{}',pages='[]',error=null,failure_reason=null,
          worker_finished_at=null,image_count=greatest(coalesce(image_count,0),%s) where id=%s""",
                     (state.cost.image_count, job_id))
        return job["generation_epoch"] + 1


def record_pencil_uses(conn, job_id: str, state: StoryMemory) -> None:
    """AC-22 / OD-04: every pencil use is a job-owned row that follows the story. The checkpoint
    stays the source of truth, so each projection rewrites the row with what it now says."""
    for use in state.pencil_uses:
        char = next(c for c in state.characters if c.char_id == use.char_id)
        status = (char.ref_moderation_status if use.after_path == char.canonical_ref_image else next(
            (v.ref_moderation_status for v in char.versions if v.image_path == use.after_path), None))
        picture = None if use.after_path is None or status is None else (
            status if status in ("passed", "teacher_allowed") else "flagged")
        conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,
          before_path,pencil_text,text_moderation,picture_moderation,reason,choice)
          values (%s,'pencil',%s,%s,%s,'pencil',%s,%s,%s,%s,%s,%s)
          on conflict (job_id,kind,version_id) do update set image_path=excluded.image_path,
          text_moderation=excluded.text_moderation,
          picture_moderation=coalesce(excluded.picture_moderation,job_picture_records.picture_moderation),
          reason=excluded.reason,choice=excluded.choice""", (
            job_id, use.char_id, use.use_id, use.after_path, use.before_path, use.text,
            use.text_moderation, picture, use.reason, use.choice))


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
        review = conn.execute("select id,kind from job_moderation_reviews where job_id=%s and decision is null",
                              (job_id,)).fetchone() if author and job["status"] == "awaiting_teacher" else None
    response.headers.update(PRIVATE)
    return {"job_id": str(job_id), "status": job["status"], "moderation_mode": job["moderation_mode"],
            "generation_epoch": job["generation_epoch"], "worker_finished": job["worker_finished_at"] is not None,
            "can_reconcile_hold": (author and repairable),
            "review_id": str(review["id"]) if review else None,
            # SH-05: a held pencil text waits alone; the child sees neutral copy and no story stop.
            "pencil_hold": bool(review and review["kind"] == "character_pencil_text"),
            "saved_writing": {"text": job["input_text"], "title": job["title"] or ""}
                if author and job["status"] == "stopped" and job["moderation_mode"] == "teacher_review_v1" else None}


def authorized_asset(conn, job_id: str, asset_id: str, user_id: str) -> tuple[str, int]:
    job = product_job(conn, job_id, user_id)
    if (job["moderation_mode"] != "teacher_review_v1"
            or job["status"] not in ("awaiting_confirm", "complete")
            or not active_author(conn, job)
            or book_review_open(conn, job_id)):
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
            for version in char.versions if has_versions(state) else []:
                if asset_id == f"version-{version.version_id}" and (
                        version.ref_moderation_status == "passed" or (
                            version.ref_moderation_status is None
                            and opened_outcome(conn, job_id, version.version_id) == "passed")):
                    path = version.image_path
    elif job["status"] == "complete":
        if any(s.moderation_status not in ("passed", "teacher_allowed") or not any(
            a.image_ref == s.final_image_ref and a.safety_eligibility in ("cleared", "teacher_allowed")
            for a in s.attempts
        ) for s in state.scenes):
            raise HTTPException(404, "image_unavailable", headers=PRIVATE)
        # magic-pencil 09 (OD-01): `jobs.pages` is the book, but it can only name an attempt the
        # checkpoint holds and moderation cleared. The final as drawn, or a version the child chose.
        pages = {p.get("scene_id"): p.get("image_path") for p in job["pages"] or [] if isinstance(p, dict)}
        for scene in state.scenes:
            for index, attempt in enumerate(scene.attempts):
                if asset_id == f"scene-{scene.scene_id}" and attempt.image_ref == pages.get(scene.scene_id) and (
                        (attempt.image_ref == scene.final_image_ref
                         and attempt.safety_eligibility in ("cleared", "teacher_allowed"))
                        or (has_versions(state) and page_version_cleared(conn, job_id, scene, index))):
                    path = attempt.image_ref
                if (asset_id == f"page-version-{page_version_id(scene, index)}" and str(job["profile_id"]) == user_id
                        and has_versions(state) and page_version_cleared(conn, job_id, scene, index)):
                    path = attempt.image_ref
        # magic-pencil 10: a page pencil result is shown once output moderation passed it or a teacher
        # allowed it. A teacher-allowed result is never another version (ticket 04), only the kept page.
        for use in conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
          and source='page_pencil' and reason is null and picture_moderation in ('passed','teacher_allowed')""",
                                (job_id,)).fetchall() if has_versions(state) else []:
            if use["picture_moderation"] != "passed" and use["choice"] == "old":
                continue
            if asset_id == f"scene-{use['target_id']}" and use["image_path"] == pages.get(use["target_id"]):
                path = use["image_path"]
            if (str(job["profile_id"]) == user_id and (asset_id == f"page-pencil-{use['version_id']}" or (
                    asset_id == f"page-version-{use['version_id']}" and use in page_pencil_versions(conn, job_id)))):
                path = use["image_path"]
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


def opened_outcome(conn, job_id: str, version_id: str, source: str = "unchosen_draw") -> str | None:
    """The stored on-open outcome of an unchosen draw or page attempt: 'passed', 'excluded', or None (unchecked)."""
    row = conn.execute("""select moderation_status from job_picture_records
      where job_id=%s and kind='version' and source=%s and version_id=%s""",
                       (job_id, source, version_id)).fetchone()
    return row["moderation_status"] if row else None


@hold_router.post("/jobs/{job_id}/characters/{char_id}/versions/open")
def open_versions(job_id: UUID, char_id: str, response: Response, user=Depends(get_current_user)):
    """magic-pencil 05 (AC-03, SH-02, OD-03). Moderates each unchosen draw of this character that
    nobody has opened, in this process because the run is paused at the reveal, and stores each
    outcome once. A flag is excluded with no hold; a classifier error stores nothing and counts as
    unavailable. Returns the pictures the child may see."""
    job_id = str(job_id)
    with connect() as conn:
        job = product_job(conn, job_id, str(user.id))
        character = next((c for c in (job["reveal"] or {}).get("characters", []) if c["char_id"] == char_id), None)
        if (job["moderation_mode"] != "teacher_review_v1" or job["status"] != "awaiting_confirm"
                or str(job["profile_id"]) != str(user.id) or not active_author(conn, job) or character is None
                or "unreviewed" not in character
                or conn.execute("select 1 from job_moderation_reviews where job_id=%s and decision is null",
                                (job_id,)).fetchone()):
            raise HTTPException(404, "versions_unavailable", headers=PRIVATE)
        records = {r["version_id"]: r for r in conn.execute("""select version_id,image_path,moderation_status
          from job_picture_records where job_id=%s and kind='version' and source='unchosen_draw'
          and target_id=%s and version_id = any(%s)""", (job_id, char_id, character["unreviewed"])).fetchall()}
    versions, unavailable = list(character["versions"]), 0
    for version_id in character["unreviewed"]:
        record = records.get(version_id)
        if record is None or not record["image_path"].startswith(f"{job_id}/"):
            unavailable += 1
            continue
        status = record["moderation_status"]
        if status is None:
            try:
                status = "passed" if screen_reference(record["image_path"]) else "excluded"
            except Exception:
                unavailable += 1   # Not a flag (SH-02): nothing is stored, so the next open checks again.
                continue
            with connect() as conn:
                # First outcome wins, so a concurrent open cannot overwrite a stored one.
                conn.execute("""update job_picture_records set moderation_status=%s
                  where job_id=%s and kind='version' and source='unchosen_draw' and version_id=%s
                  and moderation_status is null""",
                             (status, job_id, version_id))
                status = opened_outcome(conn, job_id, version_id)
        if status == "passed":
            versions.append({"version_id": version_id, "image_path": record["image_path"]})
    response.headers.update(PRIVATE)
    return {"versions": versions, "unavailable": unavailable}


def book_pages(state: StoryMemory) -> list[dict]:
    """The finished book as `jobs.pages`. AC-13: a page with two attempts that can be shown
    offers "Other versions" on a job submitted with the setting on. A teacher-allowed attempt
    counts only as the current page (ticket 04: it is never another version)."""
    return [{"scene_id": s.scene_id, "caption": s.caption, "image_path": s.final_image_ref,
             **({"other_versions": True} if has_versions(state) and sum(
                 a.image_ref == s.final_image_ref or a.safety_eligibility in ("cleared", "unreviewed")
                 for a in s.attempts) >= 2 else {})}
            for s in state.scenes]


def record_page_choice(conn, job_id: str, scene, image_path: str, source: str) -> None:
    """SH-09: the child's page change outlives a rebuild of `jobs.pages`. `before_path` is the
    checkpoint's picture of the page the change was made over (migration 0032)."""
    conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,before_path)
      values (%s,'page',%s,%s,%s,%s,%s) on conflict (job_id,kind,version_id) do update set
      image_path=excluded.image_path,source=excluded.source,before_path=excluded.before_path""",
                 (job_id, scene.scene_id, scene.scene_id, image_path, source, scene.final_image_ref))


def book_on_completion(conn, job_id: str, state: StoryMemory) -> tuple[list[dict], int]:
    """`jobs.pages` and `image_count` when a run completes. A teacher withdrawal reruns a finished book
    from the checkpoint, which never learns the child's page changes (OD-01). Each one comes back only
    on a page the rerun did not redraw, and only if the picture passes the check its choice passed.
    Page pencil images were paid after the checkpoint, so they are added to its count."""
    scenes = {s.scene_id: s for s in state.scenes}
    pencils = conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
      and source='page_pencil'""", (job_id,)).fetchall()

    def allowed(record) -> bool:
        scene = scenes.get(record["target_id"])
        if scene is None or scene.final_image_ref != record["before_path"]:
            return False
        if record["source"] == "page_pencil":
            return any(u["target_id"] == scene.scene_id and u["image_path"] == record["image_path"]
                       and u["reason"] is None and u["choice"] is not None
                       and u["picture_moderation"] in ("passed", "teacher_allowed") for u in pencils)
        return any(a.image_ref == record["image_path"] and page_version_cleared(conn, job_id, scene, i)
                   for i, a in enumerate(scene.attempts))

    chosen = {r["target_id"]: r["image_path"] for r in conn.execute(
        "select * from job_picture_records where job_id=%s and kind='page'", (job_id,)).fetchall() if allowed(r)}
    pages = [{**p, "image_path": chosen[p["scene_id"]], "other_versions": True} if p["scene_id"] in chosen else p
             for p in book_pages(state)]
    paid = sum(u["image_path"] is not None for u in pencils) + sum(u["replaced_path"] is not None for u in pencils)
    return pages, state.cost.image_count + paid


def page_version_id(scene, index: int) -> str:
    return f"{scene.scene_id}-attempt-{index}"


def page_version_cleared(conn, job_id: str, scene, index: int) -> bool:
    """SH-02: an attempt the output check cleared when it was drawn, or when the child opened it.
    A teacher-allowed attempt is never another version (ticket 04: a teacher withdraws only the current one)."""
    attempt = scene.attempts[index]
    return attempt.safety_eligibility == "cleared" or (
        attempt.safety_eligibility == "unreviewed"
        and opened_outcome(conn, job_id, page_version_id(scene, index), "scene_attempt") == "passed")


def book_review_open(conn, job_id) -> bool:
    """An open review that holds the book. A held page pencil request (ticket 10) holds only itself:
    the book stays readable and its page tools stay open (SH-05)."""
    return conn.execute("""select 1 from job_moderation_reviews where job_id=%s and decision is null
      and kind <> all(%s)""", (job_id, list(PAGE_PENCIL_KINDS))).fetchone() is not None


def finished_book(conn, job: dict, user_id: str) -> StoryMemory:
    """SH-09: page tools exist only for the author of a complete feature book that is not held."""
    if (job["moderation_mode"] != "teacher_review_v1" or job["status"] != "complete"
            or str(job["profile_id"]) != user_id or not active_author(conn, job)
            or book_review_open(conn, job["id"])):
        raise HTTPException(404, "versions_unavailable", headers=PRIVATE)
    checkpoint = PostgresSaver(conn).get_tuple({"configurable": {"thread_id": str(job["id"])}})
    state = StoryMemory.model_validate(checkpoint.checkpoint["channel_values"]) if checkpoint else None
    if state is None or not has_versions(state):
        raise HTTPException(404, "versions_unavailable", headers=PRIVATE)
    return state


def page_pencil_versions(conn, job_id: str, scene_id: str | None = None) -> list[dict]:
    """magic-pencil 10 (AC-19): a page pencil result the child decided on and output moderation passed
    is another version of its page. A teacher-allowed one is only ever the kept page (ticket 04)."""
    return conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
      and source='page_pencil' and reason is null and picture_moderation='passed' and choice is not null
      and (%s::text is null or target_id=%s) order by created_at""", (job_id, scene_id, scene_id)).fetchall()


def finished_page(conn, job: dict, scene_id: str, user_id: str):
    state = finished_book(conn, job, user_id)
    scene = next((s for s in state.scenes if s.scene_id == scene_id), None)
    page = next((p for p in job["pages"] or [] if isinstance(p, dict) and p.get("scene_id") == scene_id), None)
    if scene is None or page is None:
        raise HTTPException(404, "versions_unavailable", headers=PRIVATE)
    return scene, page["image_path"]


@hold_router.post("/jobs/{job_id}/pages/{scene_id}/versions/open")
def open_page_versions(job_id: UUID, scene_id: str, response: Response, user=Depends(get_current_user)):
    """magic-pencil 09 (AC-13, AC-14, SH-02, OD-03). The pipeline moderated only each page's final;
    opening moderates every other attempt nobody checked and stores the outcome once. A flag is
    excluded with no hold; a classifier error stores nothing and counts as unavailable."""
    job_id = str(job_id)
    with connect() as conn:
        scene, current = finished_page(conn, product_job(conn, job_id, str(user.id)), scene_id, str(user.id))
        stored = {r["version_id"]: r["moderation_status"] for r in conn.execute("""select version_id,moderation_status
          from job_picture_records where job_id=%s and kind='version' and source='scene_attempt' and target_id=%s""",
                                                                              (job_id, scene_id)).fetchall()}
        pencil = page_pencil_versions(conn, job_id, scene_id)
    versions, unavailable = [], 0
    for index, attempt in enumerate(scene.attempts):
        version_id = page_version_id(scene, index)
        if attempt.image_ref == current or not attempt.image_ref.startswith(f"{job_id}/"):
            continue
        status = "passed" if attempt.safety_eligibility == "cleared" else stored.get(version_id)
        if attempt.safety_eligibility == "unreviewed" and status is None:
            try:
                status = "passed" if screen_page(attempt.image_ref) else "excluded"
            except Exception:
                unavailable += 1   # Not a flag (SH-02): nothing is stored, so the next open checks again.
                continue
            with connect() as conn:
                # First outcome wins, so a concurrent open cannot overwrite a stored one.
                conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,
                  moderation_status) values (%s,'version',%s,%s,%s,'scene_attempt',%s)
                  on conflict (job_id,kind,version_id) do nothing""",
                             (job_id, scene_id, version_id, attempt.image_ref, status))
                status = opened_outcome(conn, job_id, version_id, "scene_attempt")
        if status == "passed":
            versions.append({"version_id": version_id, "image_path": attempt.image_ref})
    versions += [{"version_id": u["version_id"], "image_path": u["image_path"]} for u in pencil if u["image_path"] != current]
    response.headers.update(PRIVATE)
    return {"versions": versions, "unavailable": unavailable}


class PageVersionChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: str = Field(max_length=200)
    source: str = Field(max_length=1000)


@hold_router.post("/jobs/{job_id}/pages/{scene_id}/version")
def choose_page_version(job_id: UUID, scene_id: str, body: PageVersionChoice, response: Response,
                        user=Depends(get_current_user)):
    """magic-pencil 09 (AC-15, AC-20, SH-08). The chosen attempt becomes the page in `jobs.pages`,
    and the whole-book review returns to pending under the same row lock, so a teacher approval
    that lands while the change is in flight is cleared by it. No image is spent."""
    job_id, user_id = str(job_id), str(user.id)
    with connect() as conn, conn.transaction():
        product_job(conn, job_id, user_id)
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        scene, current = finished_page(conn, job, scene_id, user_id)
        from app.page_pencil import pencil_in_progress
        if pencil_in_progress(conn, job_id):   # SH-07: a paid pencil result must not go stale under it
            raise HTTPException(409, "pencil_in_progress", headers=PRIVATE)
        index = next((i for i in range(len(scene.attempts)) if body.version_id == page_version_id(scene, i)), None)
        pencil = next((u for u in page_pencil_versions(conn, job_id, scene_id) if u["version_id"] == body.version_id), None)
        if index is None and pencil is None:
            raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
        chosen = scene.attempts[index].image_ref if index is not None else pencil["image_path"]
        if chosen != current:   # Equal is a repeat of a change already made (SH-08).
            if body.source != current:
                raise HTTPException(409, "stale_source", headers=PRIVATE)
            if index is not None and not page_version_cleared(conn, job_id, scene, index):
                raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
            pages = [{**p, "image_path": chosen} if isinstance(p, dict) and p.get("scene_id") == scene_id else p
                     for p in job["pages"]]
            conn.execute("update jobs set pages=%s,approved_at=null,rejected_at=null where id=%s", (Jsonb(pages), job_id))
            record_page_choice(conn, job_id, scene, chosen, "scene_attempt" if index is not None else "page_pencil")
    response.headers.update(PRIVATE)
    return {"image_path": chosen}


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


def pencil_offered(job: dict, payload: dict) -> None:
    """ADR-082 Decision 2 (SH-08): the pencil works on the picture on screen, with a go left, and a
    keep/old choice answers the choice the reveal is waiting on."""
    reveal = job["reveal"] or {}
    character = next((c for c in reveal.get("characters", []) if c["char_id"] == payload["char_id"]
                      and c["image_path"] == payload["source"] and "versions" in c), None)
    if payload["action"] == "pencil":
        offered = (character is not None and character.get("pencil_ready") is True
                   and not character.get("pencil_choice") and reveal.get("taps_left", 0) > 0)
    else:
        offered = character is not None and bool(character.get("pencil_choice"))
    if not offered:
        raise HTTPException(422, "choice_unavailable", headers=PRIVATE)


def checked_pencil_text(text: str) -> dict:
    """SH-03: Presidio first, so only the redacted text reaches the classifiers, the worker and the
    log (SH-10). A redaction or classifier failure spends nothing and holds nothing."""
    try:
        redacted = providers.redact_pii(text)
    except Exception:
        raise HTTPException(503, "privacy_processing_unavailable", headers=PRIVATE) from None
    evidence = []
    try:
        safe, categories, _ = check_text(redacted, evidence=evidence)
    except Exception:
        raise HTTPException(503, "moderation_unavailable", headers=PRIVATE) from None
    if categories == ["moderation_error"]:
        raise HTTPException(503, "moderation_unavailable", headers=PRIVATE)
    return {"text": redacted, "flagged": not safe, "evidence": [e.model_dump(mode="json") for e in evidence]}


def confirm_review_job(job_id: str, payload: dict, user_id: str) -> str:
    from app.main import JOB_TIMEOUT_SECONDS

    if payload["action"] == "pencil":
        # The classifiers are network calls, so they run before the row lock is taken and the
        # offer is checked again under it.
        with connect() as conn:
            job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
            if not job or str(job["profile_id"]) != user_id or not active_author(conn, job):
                raise HTTPException(404, "job_not_found", headers=PRIVATE)
        if job["status"] != "awaiting_confirm":
            return job["status"]   # SH-08: a double submit sees the first one's status
        pencil_offered(job, payload)
        payload = {**payload, **checked_pencil_text(payload["text"])}

    with connect() as conn, conn.transaction():
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        if not job or str(job["profile_id"]) != user_id or not active_author(conn, job):
            raise HTTPException(404, "job_not_found", headers=PRIVATE)
        if job["status"] != "awaiting_confirm":
            return job["status"]
        if job["worker_finished_at"] is None:
            raise HTTPException(409, "finishing_current_step", headers=PRIVATE)
        if payload["action"] in ("pencil", "pencil_choice"):
            pencil_offered(job, payload)
        if payload["action"] == "confirm" and any(
                c.get("pencil_choice") for c in (job["reveal"] or {}).get("characters", [])):
            raise HTTPException(422, "choice_pending", headers=PRIVATE)   # no page from an unchosen picture
        if payload["action"] == "try_again" and not any(
            c["char_id"] == payload["char_id"] and payload["attribute"] in c["chips"]
            for c in (job["reveal"] or {}).get("characters", [])
        ):
            raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
        if payload["action"] == "choose_version":
            character = next((c for c in (job["reveal"] or {}).get("characters", [])
                              if c["char_id"] == payload["char_id"] and c["image_path"] == payload["source"]), None)
            offered = character is not None and any(
                v["version_id"] == payload["version_id"] for v in character.get("versions", []))
            # An unchosen draw is offered once it passed on open; the worker trusts `cleared` (SH-02).
            cleared = (character is not None and not offered
                       and payload["version_id"] in character.get("unreviewed", [])
                       and opened_outcome(conn, job_id, payload["version_id"]) == "passed")
            if not (offered or cleared):
                raise HTTPException(422, "choice_unavailable", headers=PRIVATE)
            payload = {**payload, "cleared": cleared}
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
