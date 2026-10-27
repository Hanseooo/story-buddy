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


@pytest.mark.parametrize("failure", [None, "projection", "worker_stopped"])
def test_checkpointed_scene_flag_projects_private_hold_and_reload(monkeypatch, held_database, failure):
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
                "title": "Synthetic title", "text": "The orange dog walks through the grassy field past the trees and stops near the stream. The dog looks across the water and sees a bird perched on the branch of a tree.",
            })
            assert submitted.status_code == 200
            job = submitted.json()["job_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert queue.enqueue.call_args.args[0] == "worker.run_job.run_review_storybook_job"
    assert conn.execute("select moderation_mode from jobs where id=%s", (job,)).fetchone()["moderation_mode"] == "teacher_review_v1"
    # Failure cases enter the real graph at a retained selection. The main case
    # drives the queued worker from fresh intake through child reveal and confirm.
    from langgraph.checkpoint.postgres import PostgresSaver
    # Real captured synthetic picture. Its hash is recorded in the fixture manifest.
    image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
    def flag(url, *, reasons):
        if failure == "projection":
            reasons.append("Synthetic review explanation")
        return False

    primary = MagicMock(side_effect=flag)
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
    if failure is None:
        import importlib
        from contracts.story_memory import RefVerdict
        from tests.test_graph_stub import STUB_ANALYSIS
        from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation

        objects = {}
        storage = MagicMock()

        def download(path):
            if path not in objects:
                raise FileNotFoundError(path)
            return objects[path]

        storage.storage.from_.return_value.download.side_effect = download
        storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})

        def structured(prompt, schema, **kwargs):
            if schema.__name__ == "StoryAnalysis":
                return STUB_ANALYSIS
            assert schema is SceneSegmentation
            return SceneSegmentation(scenes=[ExtractedScene(
                start=i, end=i, characters_present=["the orange dog"],
                visual_direction=ExtractedVisualDirection(key_action="A dog walks.", viewpoint="front view", framing="wide shot"),
            ) for i in range(2)])

        def judge(prompt, urls, schema, **kwargs):
            if schema is RefVerdict:
                return RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"])
            return schema(differences_observed="none", contradictions=[], same_character=True)

        boundaries = {
            "analyze": {"structured_text": structured}, "segment": {"structured_text": structured},
            "input_gate": {"classify_text_primary": lambda text: (True, []), "classify_text_backstop": lambda text: (True, [])},
            "char_bible": {"text_to_image": lambda *a, **kw: image, "judge": judge, "get_supabase_client": lambda: storage},
            "char_ref_mod": {"classify_image_primary": lambda url: True, "classify_image_backstop": lambda url: True,
                             "get_signed_url": lambda path: f"https://private.invalid/{path}"},
            "generate_scene": {"edit_image": lambda *a, **kw: image, "get_signed_url": lambda path: f"https://private.invalid/{path}",
                               "get_supabase_client": lambda: storage},
            "consistency_check": {"judge": judge, "get_supabase_client": lambda: storage},
        }
        for module, replacements in boundaries.items():
            for name, replacement in replacements.items():
                monkeypatch.setattr(importlib.import_module(f"pipeline.{module}"), name, replacement)
        run_review_storybook_job(job, expected_epoch=0)
        assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "awaiting_confirm"
        monkeypatch.setattr("providers.download_book_image", download)
        monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
        persisted = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        persisted["profile_id"] = child
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [persisted]
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
        try:
            with TestClient(app) as client:
                assert client.get(f"/jobs/{job}/images/ref-c0").content == image
                response = client.post(f"/jobs/{job}/confirm", json={"action": "confirm"})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        run_review_storybook_job(job, {"action": "confirm"}, expected_epoch=0)
    with PostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
        saver.setup()
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": job}}
        if failure is not None:
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
    if failure == "worker_stopped":
        from worker.run_worker import _report_failed
        _report_failed(SimpleNamespace(args=[job], kwargs={"expected_epoch": 0},
                                      func_name="worker.run_job.run_review_storybook_job"), "synthetic death")
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
        try:
            with TestClient(app) as client:
                assert client.get(f"/jobs/{job}/state").json()["can_reconcile_hold"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)
    if failure == "projection":
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

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
    monkeypatch.setattr("providers.download_book_image", lambda path: image)
    try:
        with TestClient(app) as client:
            listing = client.get(f"/teacher/classrooms/{classroom}/moderation-reviews")
            assert listing.status_code == 200
            assert [r["job_id"] for r in listing.json()] == [job]
            detail = client.get(f"/teacher/jobs/{job}/moderation-review")
            assert detail.status_code == 200
            body = detail.json()
            assert body["review_id"] == str(review.review_id)
            assert body["pictures"][-1]["state"] == "not_generated"
            assert body["criteria"] == ["sexual_content", "exposure", "graphic_harm", "harm_instruction",
                                        "targeted_abuse", "discriminatory_slur", "exploitation", "substances",
                                        "adult_detail", "privacy"]
            assert body["policy_version"] == "teacher_review_policy_v1"
            assert body["settings_snapshot"] == {"theme_ids": [], "settings_version": 0}
            captured_model = body["classifier_evidence"][0]["model_id"]
            monkeypatch.setattr(settings, "moderation_primary_image_model", "changed-after-hold")
            again = client.get(f"/teacher/jobs/{job}/moderation-review").json()
            assert again["classifier_evidence"][0]["model_id"] == captured_model
            assert again["classifier_evidence"][0]["reason"] == (
                "Synthetic review explanation" if failure == "projection" else None)
            policy = client.get("/teacher/moderation-policy")
            assert policy.status_code == 200
            assert policy.headers["cache-control"] == "private, no-store"
            assert policy.json()["criteria"][1]["id"] == "exposure"
            assert policy.json()["optional_themes"][0]["origin"] == "optional_theme"
            assert "image_path" not in detail.text and "https://" not in detail.text
            payload = {"review_id": str(review.review_id), "subject_version": review.subject_version}
            assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal",
                               json={**payload, "subject_version": "stale"}).status_code == 409
            assert client.get(f"/teacher/jobs/{job}/moderation-review/images/scene-s0", params=payload).status_code == 404
            if failure is None:
                context_image = client.get(f"/teacher/jobs/{job}/moderation-review/images/ref-c0", params=payload)
                assert context_image.status_code == 200 and context_image.content == image
                assert context_image.headers["cache-control"] == "private, no-store"
            revealed = client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload)
            assert revealed.status_code == 200 and revealed.content == image
            assert revealed.headers["cache-control"] == "private, no-store"
            monkeypatch.setattr("providers.download_book_image", lambda path: b"changed picture")
            assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload).status_code == 503
            monkeypatch.setattr("providers.download_book_image", MagicMock(side_effect=OSError("signing failed")))
            assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload).status_code == 503
            assert client.get(f"/teacher/jobs/{job}/moderation-review").json()["story_text"] == body["story_text"]
            assert conn.execute("select decision from job_moderation_reviews where job_id=%s", (job,)).fetchone()["decision"] is None
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.get("/teacher/moderation-policy").status_code == 403
            assert client.get(f"/teacher/jobs/{job}/moderation-review").status_code == 404
            assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload).status_code == 404
            outsider = str(uuid4())
            conn.execute("insert into auth.users(id,raw_app_meta_data) values (%s,%s)",
                         (outsider, Jsonb({"role": "teacher", "display_name": "Other synthetic teacher"})))
            try:
                app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=outsider)
                assert client.get(f"/teacher/classrooms/{classroom}/moderation-reviews").status_code == 404
                assert client.get(f"/teacher/jobs/{job}/moderation-review").status_code == 404
                assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload).status_code == 404
                app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)

                def lose_ownership(path):
                    conn.execute("update classrooms set owner_id=%s where id=%s", (outsider, classroom))
                    return image

                monkeypatch.setattr("providers.download_book_image", lose_ownership)
                assert client.post(f"/teacher/jobs/{job}/moderation-review/reveal", json=payload).status_code == 404
            finally:
                conn.execute("update classrooms set owner_id=%s where id=%s", (teacher, classroom))
                conn.execute("delete from profiles where id=%s", (outsider,))
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Death after projection but before the final marker must also be repairable.
    conn.execute("update jobs set worker_finished_at=null where id=%s", (job,))

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            assert client.get(f"/jobs/{job}/state").json()["can_reconcile_hold"] is True
            run_review_storybook_job(job, expected_epoch=1)
            assert conn.execute("select worker_finished_at from jobs where id=%s", (job,)).fetchone()["worker_finished_at"] is not None
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
