"""Magic pencil ticket 10 (AC-18, SH-09): one page pencil edit, outside the graph.

The checkpoint is never read for writing or resumed (OD-01). The task is keyed by the use, so a
redelivery finds the row already settled and spends nothing more (SH-08).
"""
import hashlib
import logging
from uuid import uuid4

import providers
from app.config import MAX_PAGE_PENCILS, check_image_budget
from app.db import get_supabase_client
from app.moderation_policy import TEACHER_MODERATION_CRITERIA
from pipeline.output_mod import screen_page
from providers import edit_image, get_signed_url, is_fal_content_flag
from psycopg.types.json import Jsonb

log = logging.getLogger(__name__)
BUCKET = "storybook-images"
# The character pencil's keep clause (ADR-082 Decision 2), for a whole page.
PAGE_KEEP_CLAUSE = "Keep everything else about the picture, the characters and the art style exactly the same."


class PencilStopped(Exception):
    """The book or the request changed while the edit was in flight."""


def run_page_pencil(job_id: str, use_id: str) -> None:
    from app.moderation_hold import connect
    from app.page_pencil import page_uses, pencils_spent

    def load(conn):
        job = conn.execute("select * from jobs where id=%s", (job_id,)).fetchone()
        use = conn.execute("""select * from job_picture_records where job_id=%s and kind='pencil'
          and source='page_pencil' and version_id=%s""", (job_id, use_id)).fetchone()
        return job, use

    def drawable(job, use) -> bool:
        return (job is not None and job["status"] == "complete" and use is not None and use["reason"] is None
                and use["text_moderation"] in ("cleared", "teacher_allowed"))

    with connect() as conn:
        job, use = load(conn)
        if not drawable(job, use) or use["picture_moderation"] is not None:
            return
        path = use["image_path"]
        if path is None:
            page = next((p for p in job["pages"] or [] if isinstance(p, dict) and p.get("scene_id") == use["target_id"]), None)
            # A teacher replacement re-runs a go already spent (ticket 11), so only a first edit counts here.
            spent = use["replaced_path"] is None and pencils_spent(page_uses(conn, job_id)) >= MAX_PAGE_PENCILS
            if page is None or page["image_path"] != use["before_path"] or spent:
                conn.execute("update job_picture_records set reason='stale' where id=%s", (use["id"],))
                return
    if path is None:
        check_image_budget(job["image_count"] or 0)
        epoch = job["generation_epoch"]
        asked = False

        def fence():
            # `_run_fal` also calls this after fal returns. That image is already paid for, so only the
            # check before the call stops the edit. A result stored after the book changed is never
            # shown on a book that is not complete (`finished_page`).
            nonlocal asked
            if asked:
                return
            asked = True
            with connect() as conn:
                current, row = load(conn)
            if not drawable(current, row) or current["generation_epoch"] != epoch:
                raise PencilStopped(job_id)

        # A set fence also stops `_run_fal` asking again after a content flag: a refusal is final here.
        token = providers._generation_fence.set(fence)
        try:
            image = edit_image(f"{use['pencil_text']}\n\n{PAGE_KEEP_CLAUSE}", [get_signed_url(use["before_path"])])
        except PencilStopped:
            log.info("page_pencil: %s stopped before the edit was asked for", use_id)
            with connect() as conn:   # Nothing was spent, so the use ends instead of waiting as drawing.
                conn.execute("""update job_picture_records set reason='stale' where id=%s and reason is null
                  and image_path is null""", (use["id"],))
            return
        except Exception as exc:
            if not is_fal_content_flag(exc):
                raise
            log.info("page_pencil: %s edit refused by fal", use_id)
            with connect() as conn:
                conn.execute("update job_picture_records set reason='refused' where id=%s and image_path is null",
                             (use["id"],))
            return
        finally:
            providers._generation_fence.reset(token)
        # A replacement never overwrites the held picture its review is bound to.
        path = f"{job_id}/{use['target_id']}-pencil-{use_id}{'-replacement' if use['replaced_path'] else ''}.png"
        get_supabase_client().storage.from_(BUCKET).upload(path, image, {"content-type": "image/png", "upsert": "true"})
        with connect() as conn, conn.transaction():
            if conn.execute("update job_picture_records set image_path=%s where id=%s and image_path is null",
                            (path, use["id"])).rowcount:
                conn.execute("update jobs set image_count=coalesce(image_count,0)+1 where id=%s", (job_id,))
    # Output moderation before display. A classifier error raises, which is not a flag (SH-02):
    # the image stays stored and a retry checks it again without another edit.
    safe = screen_page(path)
    digest = None if safe else hashlib.sha256(providers.download_book_image(path)).hexdigest()
    with connect() as conn, conn.transaction():
        job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
        if not conn.execute("""update job_picture_records set picture_moderation=%s where id=%s
          and picture_moderation is null""", ("passed" if safe else "flagged", use["id"])).rowcount or safe:
            return
        snapshot = job["moderation_settings_snapshot"]
        conn.execute("""insert into job_moderation_reviews(id,job_id,kind,subject_id,subject_version,
          subject,criteria,policy_version,settings_snapshot,classifier_evidence,return_node)
          values (%s,%s,'page_pencil_result',%s,%s,%s,%s,%s,%s,%s,'page_pencil')""", (
            uuid4(), job_id, use_id, digest,
            Jsonb({"pencil_text": use["pencil_text"], "scene_id": use["target_id"],
                   "before_path": use["before_path"], "image_path": path}),
            list(TEACHER_MODERATION_CRITERIA), snapshot["policy_version"], Jsonb(snapshot), Jsonb([])))
