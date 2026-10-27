"""ADR-080 synthetic integration checks. Run against a disposable migrated database.

TEST_MODERATION_DB_URL is deliberately separate from application credentials. These
tests create and remove their own synthetic accounts and never use a hosted project.
"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.main import app, get_current_user
from contracts.story_memory import Attempt, Input, ModerationContext, Scene, StoryMemory
from pipeline.graph import build_graph


@pytest.fixture
def held_database(monkeypatch):
    url = os.environ.get("TEST_MODERATION_DB_URL")
    if not url:
        pytest.skip("requires disposable migrated TEST_MODERATION_DB_URL")
    monkeypatch.setattr(settings, "supabase_db_url", url)
    teacher, child, classroom, job = [uuid4() for _ in range(4)]
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        for uid, metadata in [
            (teacher, {"role": "teacher", "display_name": "Synthetic teacher"}),
        ]:
            conn.execute("insert into auth.users(id, raw_app_meta_data) values (%s,%s)", (uid, Jsonb(metadata)))
        conn.execute("insert into classrooms(id,code,name,owner_id) values (%s,%s,'Synthetic',%s)",
                     (classroom, str(classroom), teacher))
        conn.execute("insert into auth.users(id,raw_app_meta_data) values (%s,%s)", (child, Jsonb({
            "role": "student", "classroom_id": str(classroom), "nickname": "synthetic",
            "display_nickname": "Synthetic child",
        })))
        yield conn, str(child), str(classroom), str(job), str(teacher)
        from langgraph.checkpoint.postgres import PostgresSaver
        saver = PostgresSaver(conn)
        for row in conn.execute("select id from jobs where classroom_id=%s", (classroom,)).fetchall():
            saver.delete_thread(str(row["id"]))
        conn.execute("delete from profiles where id = %s", (teacher,))


@pytest.mark.parametrize("projection_failure", [False, True])
def test_checkpointed_scene_flag_projects_private_hold_and_reload(monkeypatch, held_database, projection_failure):
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, job, teacher = held_database
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    db, queue = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)

    def redact(text):
        # Disabling later intake must not downgrade this captured request or its worker.
        settings.enable_teacher_moderation_review = False
        return text

    monkeypatch.setattr("providers.redact_pii", redact)
    monkeypatch.setattr("app.main.check_text", lambda title: (True, [], title))
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            submitted = client.post("/storybooks", json={
                "title": "Synthetic title", "text": "A hedgehog walks through a field.",
            })
            assert submitted.status_code == 200
            job = submitted.json()["job_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert queue.enqueue.call_args.args[0] == "worker.run_job.run_review_storybook_job"
    assert conn.execute("select moderation_mode from jobs where id=%s", (job,)).fetchone()["moderation_mode"] == "teacher_review_v1"
    # Enter via the real graph at the already-durable flag checkpoint. No classifier
    # or generation call is allowed while repairing this exact interruption.
    from langgraph.checkpoint.postgres import PostgresSaver
    # Real captured synthetic picture. Its hash is recorded in the fixture manifest.
    image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
    primary = MagicMock(return_value=False)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", primary)
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: "https://private.invalid/image")
    monkeypatch.setattr("pipeline.output_mod.download_book_image", lambda path: image)
    state = StoryMemory(schema_version=1, story_id=job, profile_id=child, classroom_id=classroom,
                        input=Input(raw_text="Synthetic story"),
                        scenes=[Scene(scene_id="s0", text_excerpt="Synthetic story", prompt="A field",
                                      final_image_ref=f"{job}/s0-1.png",
                                      attempts=[Attempt(image_ref=f"{job}/s0-1.png", prompt="A field")]),
                                Scene(scene_id="s1", text_excerpt="The next scene stays undrawn.")],
                        moderation_context=ModerationContext(mode="teacher_review_v1",
                            policy_version="teacher_review_policy_v1"))
    with PostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
        saver.setup()
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": job}}
        graph.update_state(config, dict(state), as_node="consistency_check")
        graph.invoke(None, config)
        held = graph.get_state(config)
        review = held.values["moderation_context"].review
        assert review.subject_version == "0e1cdbf033e2b06bb23842359a9ae55e74529a78fcdbf18a7b167e73961110ef"
        assert held.values["scenes"][1].attempts == []
        # Prove the installed update_state/as_node scheduling contract as well.
        graph.update_state(config, {"moderation_context": held.values["moderation_context"]}, as_node="moderation_review")
        assert graph.get_state(config).next == ("moderation_review",)
        graph.invoke(None, config)
    if projection_failure:
        conn.execute("""create function pg_temp.reject_review() returns trigger language plpgsql as $$
          begin raise exception 'synthetic write outage'; end $$""")
        conn.execute("create trigger synthetic_review_outage before insert on job_moderation_reviews for each row execute function pg_temp.reject_review()")
        try:
            with pytest.raises(psycopg.errors.RaiseException):
                run_review_storybook_job(job)
            failed = conn.execute("select status,error,generation_epoch from jobs where id=%s", (job,)).fetchone()
            assert failed == {"status": "failed", "error": "hold_projection_failed", "generation_epoch": 0}
            assert conn.execute("select count(*) as n from job_moderation_reviews where job_id=%s", (job,)).fetchone()["n"] == 0
        finally:
            conn.execute("drop trigger synthetic_review_outage on job_moderation_reviews")
    run_review_storybook_job(job)
    run_review_storybook_job(job)  # redelivery cannot advance epoch twice
    row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
    assert row["status"] == "awaiting_teacher"
    assert row["generation_epoch"] == 1
    assert row["worker_finished_at"] is not None
    assert not row["reveal"] and row["pages"] == [] and row["error"] is None
    saved = conn.execute("select * from job_moderation_reviews where job_id=%s", (job,)).fetchone()
    assert str(saved["id"]) == str(review.review_id)
    assert saved["subject"]["image_path"] == f"{job}/s0-1.png"
    assert saved["checkpoint_id"]
    primary.assert_called_once()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            for _ in range(2):
                response = client.get(f"/jobs/{job}/state")
                assert response.status_code == 200
                assert response.json()["status"] == "awaiting_teacher"
                assert "subject" not in response.text and "image_path" not in response.text
            response = client.get(f"/jobs/{job}/images/scene-s0")
            assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    conn.execute("insert into storage.objects(bucket_id,name) values ('storybook-images',%s)",
                 (f"{job}/s0-1.png",))
    for viewer in (child, teacher):
        with conn.transaction():
            conn.execute("set local role authenticated")
            conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (viewer,))
            assert conn.execute("select name from storage.objects where name=%s", (f"{job}/s0-1.png",)).fetchall() == []
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute("select * from job_moderation_reviews")
    conn.execute("delete from storage.objects where name=%s", (f"{job}/s0-1.png",))


def test_review_interrupt_cannot_be_written_to_child_reveal():
    from langgraph.types import Interrupt
    from worker.run_job import _finish

    db = MagicMock()
    with pytest.raises(RuntimeError, match="moderation"):
        _finish(db, str(uuid4()), {"__interrupt__": [Interrupt({
            "kind": "moderation_review", "review_id": str(uuid4()),
        })]})
    db.table.return_value.update.assert_not_called()
