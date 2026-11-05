"""ADR-080 synthetic integration checks. Run against a disposable migrated database.

TEST_MODERATION_DB_URL is deliberately separate from application credentials. These
tests create and remove their own synthetic accounts and never use a hosted project.
"""
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
import pytest
from fastapi import Request
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
        conn.execute("delete from jobs where classroom_id=%s", (classroom,))
        conn.execute("delete from profiles where id = %s", (teacher,))


def test_optional_themes_capture_grouped_review_before_paid_work(monkeypatch, held_database):
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, _, teacher = held_database
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    queue, db = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("providers.redact_pii", lambda text: text)
    monkeypatch.setattr("providers.classify_text_primary", lambda text: (True, []))
    monkeypatch.setattr("providers.classify_text_backstop", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.classify_text_primary", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.classify_text_backstop", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.redact_pii", lambda text: text)
    # Existing captured synthetic story, not a classifier-quality fixture.
    text = "A dog runs in a field. The dog barks."
    detector = MagicMock(side_effect=lambda prompt, schema, **kwargs: schema.model_validate({"matches": [
        {"theme_id": "spooky_suspense", "reason": "Synthetic detector evidence"},
        {"theme_id": "story_conflict", "reason": "Synthetic detector evidence"},
    ]}))
    monkeypatch.setattr("pipeline.optional_themes.structured_text", detector)
    monkeypatch.setattr("pipeline.optional_themes.redact_pii", lambda text: text)
    paid = MagicMock(side_effect=AssertionError("paid generation before review"))
    monkeypatch.setattr("providers.text_to_image", paid)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
    route = f"/teacher/classrooms/{classroom}/moderation-settings"
    try:
        with TestClient(app) as client:
            assert client.get(route).json()["theme_ids"] == []
            saved = client.patch(route, json={"expected_version": 0, "theme_ids": ["spooky_suspense", "story_conflict"]})
            assert saved.status_code == 200, saved.text
            assert saved.json()["settings_version"] == 1
            assert client.patch(route, json={"expected_version": 0, "theme_ids": []}).status_code == 409
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.patch(route, json={"expected_version": 1, "theme_ids": []}).status_code == 403
            submitted = client.post("/storybooks", json={"title": "Synthetic title", "text": text})
            assert submitted.status_code == 200, submitted.text
            job = submitted.json()["job_id"]
            # Change after intake but before the queued worker starts.
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            assert client.patch(route, json={"expected_version": 1, "theme_ids": []}).status_code == 200
            run_review_storybook_job(job, expected_epoch=0)
            detail = client.get(f"/teacher/jobs/{job}/moderation-review").json()
            assert detail["kind"] == "optional_themes" and detail["origin"] == "optional_theme"
            assert detail["criteria"] == ["spooky_suspense", "story_conflict"]
            assert detail["settings_snapshot"]["settings_version"] == 1
            assert detail["story_text"] == text and detail["pictures"] == []
            assert len(detail["detected_themes"]) == 2
            assert detail["theme_check"]["instruction_version"] == "optional_themes_v1"
            assert detail["theme_check"]["model_id"] == settings.text_model
            detector.assert_called_once()
            paid.assert_not_called()
            assert client.patch(route, json={"expected_version": 2, "theme_ids": ["loss_separation"]}).status_code == 200
            assert client.get(f"/teacher/jobs/{job}/moderation-review").json() == detail
            # Global switch off freezes edits, but saved settings and captured holds remain readable.
            monkeypatch.setattr(settings, "enable_teacher_moderation_review", False)
            assert client.get(route).json()["theme_ids"] == ["loss_separation"]
            assert client.patch(route, json={"expected_version": 3, "theme_ids": []}).status_code == 409
            assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "awaiting_teacher"
            # Accept the captured group even though current settings and the feature switch changed.
            from langgraph.checkpoint.postgres import PostgresSaver
            from contracts.story_memory import RefVerdict
            from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation
            from tests.test_graph_stub import STUB_ANALYSIS, _judge_returning
            from pipeline.consistency_check import SceneVerdict, SceneConstraintVerdict

            monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
            review_route = f"/teacher/jobs/{job}/moderation-review"
            command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()), "action": "allow",
                "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"], "confirmed": True}
            accepted = client.post(f"{review_route}/decision", json=command)
            assert accepted.status_code == 202, accepted.text
            assert client.post(f"{review_route}/decision", json=command).status_code == 200
            recorded = conn.execute("select * from job_moderation_reviews where id=%s", (detail["review_id"],)).fetchone()
            assert recorded["confirmed_criteria"] == ["spooky_suspense", "story_conflict"]
            assert recorded["settings_snapshot"]["settings_version"] == 1
            image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
            storage = MagicMock()
            objects = {}
            def download(path):
                if path not in objects:
                    raise FileNotFoundError(path)
                return objects[path]
            storage.storage.from_.return_value.download.side_effect = download
            storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})
            monkeypatch.setattr("pipeline.analyze.structured_text", lambda *a, **kw: STUB_ANALYSIS)
            monkeypatch.setattr("pipeline.segment.structured_text", lambda *a, **kw: SceneSegmentation(scenes=[
                ExtractedScene(start=i, end=i, characters_present=["the orange dog"], visual_direction=ExtractedVisualDirection(
                    key_action="A dog runs." if i == 0 else "The dog barks.", viewpoint="front view", framing="wide shot"))
                for i in range(2)]))
            draws = MagicMock(return_value=image)
            monkeypatch.setattr("pipeline.char_bible.text_to_image", draws)
            monkeypatch.setattr("pipeline.char_bible.get_supabase_client", lambda: storage)
            monkeypatch.setattr("pipeline.char_bible.judge", lambda *a: RefVerdict(
                differences_observed="none", matches_description=True, attributes_present=["dog"]))
            monkeypatch.setattr("pipeline.char_ref_mod.classify_image_primary", lambda *a, **kw: True)
            monkeypatch.setattr("pipeline.char_ref_mod.classify_image_backstop", lambda *a, **kw: True)
            monkeypatch.setattr("pipeline.char_ref_mod.get_signed_url", lambda path: path)
            monkeypatch.setattr("pipeline.generate_scene.edit_image", draws)
            monkeypatch.setattr("pipeline.generate_scene.get_supabase_client", lambda: storage)
            monkeypatch.setattr("pipeline.generate_scene.get_signed_url", lambda path: path)
            monkeypatch.setattr("pipeline.consistency_check.get_supabase_client", lambda: storage)
            monkeypatch.setattr("pipeline.consistency_check.judge", lambda prompt, urls, schema, **kw:
                _judge_returning(same=True) if schema is SceneVerdict else SceneConstraintVerdict(differences_observed="none", contradictions=[]))
            scene_safety = MagicMock(side_effect=[True, False])
            monkeypatch.setattr("pipeline.output_mod.classify_image_primary", scene_safety)
            monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", lambda *a, **kw: True)
            monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
            monkeypatch.setattr("pipeline.output_mod.download_book_image", lambda path: image)
            monkeypatch.setattr("providers.download_book_image", lambda path: image)
            epoch = detail["generation_epoch"] + 1
            run_review_storybook_job(job, expected_epoch=epoch)
            job_row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
            job_row["profile_id"] = child
            db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [job_row]
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.post(f"/jobs/{job}/confirm", json={"action": "confirm"}).status_code == 200
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            run_review_storybook_job(job, {"action": "confirm"}, expected_epoch=epoch)
            later = client.get(review_route).json()
            assert later["kind"] == "scene_image" and later["subject_id"] == "s1"
            assert later["origin"] == "shared_safety" and later["ready"]
            snapshot = build_graph(checkpointer=PostgresSaver(conn)).get_state({"configurable": {"thread_id": job}})
            context = snapshot.values["moderation_context"]
            assert context.accepted_theme_ids == ["spooky_suspense", "story_conflict"]
            assert context.optional_theme_check.subject_version == detail["subject_version"]
            assert context.optional_theme_check.settings_version == context.settings_version == 1
            assert snapshot.values["input"].moderation_clearance is None
            assert snapshot.values["scenes"][0].moderation_status == "passed"
            assert scene_safety.call_count == 2
            assert draws.call_count == 3  # One reference plus two scene pictures, once each.
            detector.assert_called_once()
            # A new submission captures current settings, never the earlier acceptance.
            monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            new_job = client.post("/storybooks", json={"title": "Synthetic title", "text": text}).json()["job_id"]
            captured = conn.execute("select moderation_settings_snapshot from jobs where id=%s", (new_job,)).fetchone()
            assert captured["moderation_settings_snapshot"]["theme_ids"] == ["loss_separation"]
            assert "accepted_theme_ids" not in captured["moderation_settings_snapshot"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("output", [
    {"matches": [{"theme_id": "loss_separation", "reason": "Disabled ID"}]},
    {"matches": [{"theme_id": "spooky_suspense", "reason": "One"}, {"theme_id": "spooky_suspense", "reason": "Two"}]},
    {"matches": [], "unexpected": "not a valid response"},
])
def test_optional_detector_invalid_response_is_service_failure_not_clearance(monkeypatch, held_database, output):
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, job, _ = held_database
    # Use the same persisted intake shape as the main HTTP journey, isolating the
    # worker's malformed-provider failure path from unrelated title checks.
    conn.execute("""insert into jobs(id,profile_id,classroom_id,status,input_text,title,moderation_mode,moderation_settings_snapshot)
      values (%s,%s,%s,'queued','A dog runs in a field.','Synthetic title','teacher_review_v1',%s)""", (
        job, child, classroom, Jsonb({"policy_version": "teacher_review_policy_v1", "theme_ids": ["spooky_suspense"], "settings_version": 1})))
    monkeypatch.setattr("pipeline.input_gate.classify_text_primary", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.classify_text_backstop", lambda text: (True, []))
    monkeypatch.setattr("pipeline.optional_themes.structured_text", lambda *args, **kwargs: output)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with pytest.raises(RuntimeError, match="optional_theme_error"):
            run_review_storybook_job(job, expected_epoch=0)
        with TestClient(app) as client:
            failed = client.get(f"/jobs/{job}/state").json()
        assert failed["status"] == "failed"
        assert conn.execute("select failure_reason from jobs where id=%s", (job,)).fetchone()["failure_reason"] == "service_busy"
        assert conn.execute("select count(*) as n from job_moderation_reviews where job_id=%s", (job,)).fetchone()["n"] == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("action", ["allow", "stop", "projection"])
def test_flagged_title_waits_privately_until_exact_teacher_decision(monkeypatch, held_database, action):
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, _, teacher = held_database
    title, text = "Synthetic title", "A dog runs in a field. The dog barks."
    db, queue = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
    monkeypatch.setattr("providers.redact_pii", lambda value: value)
    monkeypatch.setattr("providers.classify_text_primary", lambda value: (False, ["S1"]))
    backstop = MagicMock()
    monkeypatch.setattr("providers.classify_text_backstop", backstop)
    # The real graph must perform story moderation independently after title allow.
    story_classifier = MagicMock(return_value=(False, ["S2"]))
    monkeypatch.setattr("pipeline.input_gate.classify_text_primary", story_classifier)
    monkeypatch.setattr("pipeline.input_gate.redact_pii", lambda value: value)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            submitted = client.post("/storybooks", json={"title": title, "text": text})
            assert submitted.status_code == 200, submitted.text
            job = submitted.json()["job_id"]
            queue.enqueue.assert_not_called()
            backstop.assert_not_called()
            stored = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
            assert stored["status"] == "awaiting_teacher" and stored["title"] != title
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            route = f"/teacher/jobs/{job}/moderation-review"
            detail_response = client.get(route)
            assert detail_response.status_code == 200, detail_response.text
            detail = detail_response.json()
            assert detail["kind"] == "title" and detail["ready"]
            assert detail["subject_title"] == title and detail["story_text"] == text
            assert detail["pictures"] == [] and not detail["replacement_available"]
            assert detail["classifier_evidence"][0]["categories"] == ["S1"]
            command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()), "action": "stop" if action == "stop" else "allow",
                "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"], "confirmed": True}
            response = client.post(f"{route}/decision", json=command)
            assert response.status_code in (200, 202), response.text
            assert client.post(f"{route}/decision", json=command).status_code == 200
            if action == "stop":
                queue.enqueue.assert_not_called()
                app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
                saved = client.get(f"/jobs/{job}/state").json()
                assert saved["status"] == "stopped" and saved["saved_writing"]["text"] == text
            else:
                queue.enqueue.assert_called_once()
                assert conn.execute("select title from jobs where id=%s", (job,)).fetchone()["title"] == title
                if action == "projection":
                    execute = psycopg.Connection.execute

                    def fail_projection(connection, query, params=None, **kwargs):
                        if "insert into job_moderation_reviews" in str(query).lower():
                            raise psycopg.OperationalError("synthetic projection outage")
                        return execute(connection, query, params, **kwargs)

                    with monkeypatch.context() as outage:
                        outage.setattr(psycopg.Connection, "execute", fail_projection)
                        with pytest.raises(psycopg.OperationalError, match="synthetic projection outage"):
                            run_review_storybook_job(job, expected_epoch=2, review_id=detail["review_id"])
                    assert conn.execute("select error from jobs where id=%s", (job,)).fetchone()["error"] == "hold_projection_failed"
                    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
                    assert client.post(f"/jobs/{job}/reconcile-hold").status_code == 202
                    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
                run_review_storybook_job(job, expected_epoch=2, review_id=detail["review_id"])
                current = client.get(route).json()
                assert current["kind"] == "story_text" and current["ready"]
                assert current["story_text"] == text
                # Duplicate worker delivery cannot start another graph.
                run_review_storybook_job(job, expected_epoch=2, review_id=detail["review_id"])
                assert client.get(route).json()["review_id"] == current["review_id"]
                story_classifier.assert_called_once_with(text)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("failure", [None, "projection", "worker_stopped", "withdraw_inflight", "withdraw_queued_allow", "withdraw_queued_allow_revoked", "child_stop", "teacher_stop", "stop_race", "replacement_pass", "replacement_flag", "replacement_refusal", "replacement_budget"])
def test_checkpointed_scene_flag_projects_private_hold_and_reload(monkeypatch, held_database, failure):
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, job, teacher = held_database
    full_run = failure not in ("projection", "worker_stopped")
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
    monkeypatch.setattr("app.main.check_text", lambda title, **kwargs: (True, [], title))
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
    if full_run:
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
            "char_ref_mod": {"classify_image_primary": lambda url, **kw: True, "classify_image_backstop": lambda url, **kw: True,
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
        if not full_run:
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

    if full_run:
        # Continue the real graph via the public command, including duplicate delivery.
        monkeypatch.setattr("providers.download_book_image", lambda path: image)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
        try:
            with TestClient(app) as client:
                detail = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                           "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                           "action": "allow", "policy_version": detail["current_policy_version"],
                           "confirmed_criteria": detail["criteria"], "confirmed": True}
                if failure and failure.startswith("replacement_"):
                    from app.config import IMAGE_BUDGET
                    from pipeline.consistency_check import Contradiction, SceneConstraintVerdict

                    graph = build_graph(PostgresSaver(conn))
                    route = f"/teacher/jobs/{job}/moderation-review/decision"
                    replacement = {**command, "action": "replace", "confirmed_criteria": []}
                    assert detail["replacement_available"] is True
                    draws = []
                    def draw(prompt, urls):
                        draws.append((prompt, urls))
                        if failure == "replacement_refusal":
                            raise RuntimeError("synthetic provider refusal before image")
                        return image
                    monkeypatch.setattr("pipeline.generate_scene.edit_image", draw)
                    if failure == "replacement_budget":
                        conn.execute("update jobs set image_count=%s where id=%s", (IMAGE_BUDGET, job))
                        exhausted = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                        assert exhausted["replacement_available"] is False
                        assert exhausted["replacement_disabled_reason"] == "image_budget_exhausted"
                        assert client.post(route, json=replacement).status_code == 422
                        assert draws == []
                        assert client.get(f"/teacher/jobs/{job}/moderation-review").json()["review_id"] == detail["review_id"]
                        return
                    queue.enqueue.side_effect = RuntimeError("synthetic lost queue response")
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(lambda _: client.post(route, json=replacement), range(2)))
                    assert sorted(r.status_code for r in results) == [200, 202]
                    pending = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                    assert pending["pending_command"] == replacement
                    assert client.get(f"/teacher/classrooms/{classroom}/moderation-reviews").json()[0]["continuation_pending"] is True
                    queue.enqueue.side_effect = None
                    assert client.post(route, json=replacement).status_code == 200
                    # A failing fresh judgment must finalize the fresh image, even when
                    # the rejected original had a clean verdict and attempts remain.
                    checks = []
                    def fresh_judge(prompt, urls, schema, **kwargs):
                        checks.append(schema.__name__)
                        if schema is SceneConstraintVerdict:
                            return schema(differences_observed="action differs", contradictions=[Contradiction(
                                subject="dog", required="walking", observed="sitting")] if len(checks) == 2 else [])
                        return schema(differences_observed="none", same_character=True)
                    monkeypatch.setattr("pipeline.consistency_check.judge", fresh_judge)
                    monkeypatch.setattr("pipeline.output_mod.classify_image_primary",
                                        lambda url, **kwargs: failure != "replacement_flag")
                    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", lambda url, **kwargs: True)
                    # Stop at a later flag so only this replacement is charged.
                    state_before = graph.get_state(config)
                    source_scene = state_before.values["scenes"][0]
                    if failure == "replacement_refusal":
                        with pytest.raises(RuntimeError, match="synthetic provider refusal"):
                            run_review_storybook_job(job, expected_epoch=2)
                        assert client.get(f"/teacher/jobs/{job}/moderation-review").json()["status"] == "failed"
                        assert checks == []
                    else:
                        if failure == "replacement_pass":
                            monkeypatch.setattr("pipeline.output_mod.classify_image_primary",
                                lambda url, **kwargs: "s1-" not in url)
                            monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
                        run_review_storybook_job(job, expected_epoch=2)
                        after = StoryMemory.model_validate(graph.get_state(config).values)
                        scene = after.scenes[0]
                        assert scene.final_image_ref == f"{job}/s0-2.png"
                        assert scene.attempts[0].safety_eligibility == "excluded"
                        assert scene.attempts[-1].passed is False
                        assert scene.attempts[-1].scene_contradictions == ["dog: sitting, but the constraints require walking"]
                        assert scene.moderation_replacement_count == 1
                        assert draws[0] == (source_scene.prompt, [f"https://private.invalid/{job}/ref-c0-1.png"])
                        assert scene.moderation_status == (None if failure == "replacement_flag" else "passed")
                        current = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                        if failure == "replacement_flag":
                            assert current["subject_id"] == "s0"
                            assert current["replacement_available"] is False
                            assert current["replacement_disabled_reason"] == "replacement_already_used"
                            assert client.post(route, json={**replacement, "review_id": current["review_id"],
                                "subject_version": current["subject_version"], "expected_epoch": current["generation_epoch"],
                                "request_id": str(uuid4())}).status_code == 422
                        else:
                            assert current["subject_id"] == "s1"
                        assert current["review_id"] != detail["review_id"]
                    before_replay = len(draws)
                    run_review_storybook_job(job, expected_epoch=2)
                    assert len(draws) == before_replay
                    assert client.post(route, json=command).status_code == 409
                    assert client.post(route, json=replacement).status_code == 200
                    assert len(draws) == (2 if failure == "replacement_pass" else 1)
                    assert conn.execute("select image_count from jobs where id=%s", (job,)).fetchone()["image_count"] == (
                        4 if failure == "replacement_pass" else 2 if failure == "replacement_refusal" else 3)
                    return
                if failure == "stop_race":
                    def race_user(request: Request):
                        return SimpleNamespace(id=teacher if request.url.path.startswith("/teacher/") else child)
                    app.dependency_overrides[get_current_user] = race_user
                    child_command = {k: command[k] for k in ("review_id", "expected_epoch", "request_id", "confirmed")}
                    child_command["request_id"] = str(uuid4())
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        allow = pool.submit(client.post, f"/teacher/jobs/{job}/moderation-review/decision", json=command)
                        stop = pool.submit(client.post, f"/jobs/{job}/stop", json=child_command)
                        results = [allow.result(), stop.result()]
                    assert sorted(r.status_code for r in results) in ([200, 409], [202, 409])
                    current = conn.execute("select status,generation_epoch from jobs where id=%s", (job,)).fetchone()
                    assert current["generation_epoch"] == 2
                    assert current["status"] in ("stopped", "queued")
                    if current["status"] == "queued":
                        assert results[1].json()["detail"]["status"] == "queued"
                    else:
                        run_review_storybook_job(job, expected_epoch=1)
                        assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "stopped"
                    return
                if failure in ("child_stop", "teacher_stop"):
                    before = conn.execute("select input_text,image_count from jobs where id=%s", (job,)).fetchone()
                    stop = {**command, "action": "stop", "confirmed_criteria": []}
                    route = f"/teacher/jobs/{job}/moderation-review/decision"
                    if failure == "child_stop":
                        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
                        route = f"/jobs/{job}/stop"
                        stop = {k: command[k] for k in ("review_id", "expected_epoch", "request_id", "confirmed")}
                        conn.execute("update profiles set removed_at=now() where id=%s", (child,))
                        assert client.post(route, json=stop).status_code == 404
                        conn.execute("update profiles set removed_at=null where id=%s", (child,))
                    assert client.post(route, json={**stop, "confirmed": False}).status_code == 422
                    conn.execute("update jobs set worker_finished_at=null where id=%s", (job,))
                    assert client.post(route, json=stop).status_code == 409
                    conn.execute("update jobs set worker_finished_at=now() where id=%s", (job,))
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        responses = list(pool.map(lambda _: client.post(route, json=stop), range(2)))
                    assert [r.status_code for r in responses] == [200, 200]
                    assert all(r.json()["status"] == "stopped" for r in responses)
                    assert client.post(route, json={**stop, "expected_epoch": 0}).status_code == 409
                    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
                    assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command).status_code == 409
                    run_review_storybook_job(job, expected_epoch=1)
                    after = conn.execute("select status,input_text,image_count,generation_epoch from jobs where id=%s", (job,)).fetchone()
                    assert after == {**before, "status": "stopped", "generation_epoch": 2}
                    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
                    recovery = client.get(f"/jobs/{job}/state").json()
                    assert recovery["saved_writing"] == {"text": before["input_text"], "title": "Synthetic title"}
                    assert client.get(f"/jobs/{job}/images/scene-s0").status_code == 404
                    return
                conn.execute("update profiles set removed_at=now() where id=%s", (child,))
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command).status_code == 404
                conn.execute("update profiles set removed_at=null where id=%s", (child,))
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json={**command, "subject_version": "stale"}).status_code == 409
                queue.enqueue.side_effect = RuntimeError("synthetic Redis outage")
                with ThreadPoolExecutor(max_workers=2) as pool:
                    responses = list(pool.map(lambda _: client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command), range(2)))
                assert sorted(r.status_code for r in responses) == [200, 202]
                assert all(r.json()["dispatch_state"] == "pending" for r in responses)
                assert conn.execute("select generation_epoch from jobs where id=%s", (job,)).fetchone()["generation_epoch"] == 2
                pending_detail = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                assert pending_detail["pending_command"] == command
                pending_list = client.get(f"/teacher/classrooms/{classroom}/moderation-reviews").json()
                assert pending_list[0]["continuation_pending"] is True
                queue.enqueue.side_effect = None
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command).status_code == 200
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json={**command, "subject_version": "stale"}).status_code == 409
                if failure == "withdraw_inflight":
                    from app.moderation_hold import StaleGeneration
                    import providers
                    withdrawal = {"clearance_review_id": command["review_id"], "subject_version": command["subject_version"],
                                  "expected_epoch": 2, "request_id": str(uuid4()), "confirmed": True}
                    def finish_inflight(*args, **kwargs):
                        providers._generation_fence.get()()
                        providers._fal_event_sink.get()("completed")
                        assert client.post(f"/teacher/jobs/{job}/moderation-review/withdraw", json=withdrawal).status_code == 202
                        with pytest.raises(StaleGeneration):
                            providers._generation_fence.get()()
                        # Real provider fencing exits before upload or another call.
                        providers._generation_fence.get()()
                    monkeypatch.setattr("pipeline.generate_scene.edit_image", finish_inflight)
                    run_review_storybook_job(job, expected_epoch=2)
                    hidden = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                    assert hidden["status"] == "awaiting_teacher" and hidden["generation_epoch"] == 3
                    assert hidden["image_count"] == 3 and not hidden["pages"] and hidden["worker_finished_at"] is None
                    run_review_storybook_job(job, expected_epoch=2)
                    with pytest.raises(RuntimeError, match="checkpoint_not_resumable"):
                        run_review_storybook_job(job, expected_epoch=3, review_id=withdrawal["request_id"])
                    failed = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                    assert failed["status"] == "failed" and failed["image_count"] == 3
                    assert failed["worker_finished_at"] is not None
                    primary.assert_called_once()
                    return
                run_review_storybook_job(job, expected_epoch=2)
                run_review_storybook_job(job, expected_epoch=2)
                later = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                assert later["subject_id"] == "s1"
                assert later["review_id"] != detail["review_id"]
                assert primary.call_count == 2
                assert conn.execute("select image_count from jobs where id=%s", (job,)).fetchone()["image_count"] == 3
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command).status_code == 200
                assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "awaiting_teacher"
                later_command = {**command, "review_id": later["review_id"], "subject_version": later["subject_version"],
                                 "expected_epoch": later["generation_epoch"], "request_id": str(uuid4())}
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=later_command).status_code == 202
                if failure in ("withdraw_queued_allow", "withdraw_queued_allow_revoked"):
                    withdrawal = {"clearance_review_id": command["review_id"], "subject_version": command["subject_version"],
                                  "expected_epoch": 4, "request_id": str(uuid4()), "confirmed": True}
                    assert client.post(f"/teacher/jobs/{job}/moderation-review/withdraw", json=withdrawal).status_code == 202
                    if failure == "withdraw_queued_allow_revoked":
                        from fastapi import HTTPException
                        new_owner = uuid4()
                        conn.execute("insert into auth.users(id,raw_app_meta_data) values (%s,%s)",
                                     (new_owner, Jsonb({"role": "teacher", "display_name": "New synthetic owner"})))
                        conn.execute("update classrooms set owner_id=%s where id=%s", (new_owner, classroom))
                        try:
                            with pytest.raises(HTTPException) as denied:
                                run_review_storybook_job(job, expected_epoch=5, review_id=withdrawal["request_id"])
                            assert denied.value.status_code == 404
                            failed = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                            assert failed["status"] == "failed" and failed["image_count"] == 3
                            assert primary.call_count == 2
                        finally:
                            conn.execute("update classrooms set owner_id=%s where id=%s", (teacher, classroom))
                            conn.execute("delete from profiles where id=%s", (new_owner,))
                        return
                    run_review_storybook_job(job, expected_epoch=5, review_id=withdrawal["request_id"])
                    reopened = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                    assert reopened["ready"] is True
                    release = {**command, "review_id": reopened["review_id"], "expected_epoch": 5, "request_id": str(uuid4())}
                    assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=release).status_code == 202
                    run_review_storybook_job(job, expected_epoch=6)
                    completed = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                    assert completed["status"] == "complete" and completed["image_count"] == 3
                    assert completed["approved_at"] is None and primary.call_count == 2
                    return
                run_review_storybook_job(job, expected_epoch=4)
                complete = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                assert complete["status"] == "complete"
                assert complete["image_count"] == 3 and complete["approved_at"] is None
                assert len(client.get(f"/teacher/jobs/{job}/moderation-review").json()["clearances"]) == 2
                conn.execute("update jobs set approved_at=now() where id=%s", (job,))
                withdrawal = {"clearance_review_id": command["review_id"], "subject_version": command["subject_version"],
                              "expected_epoch": 4, "request_id": str(uuid4()), "confirmed": True}
                withdrawn = client.post(f"/teacher/jobs/{job}/moderation-review/withdraw", json=withdrawal)
                assert withdrawn.status_code == 202, withdrawn.text
                assert client.post(f"/teacher/jobs/{job}/moderation-review/withdraw", json=withdrawal).status_code == 200
                hidden = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                assert hidden["status"] == "awaiting_teacher" and hidden["approved_at"] is None
                from worker.run_worker import _report_failed
                _report_failed(SimpleNamespace(args=[job], kwargs={"expected_epoch": 5, "review_id": withdrawal["request_id"]},
                                              func_name="worker.run_job.run_review_storybook_job"), "synthetic anchor death")
                dispatch = conn.execute("select dispatch_state from job_moderation_reviews where id=%s", (withdrawal["request_id"],)).fetchone()
                assert dispatch["dispatch_state"] == "failed"
                from rq.exceptions import DuplicateJobError
                queue.enqueue.side_effect = DuplicateJobError("synthetic existing failed anchor")
                queue.fetch_job.return_value.get_status.return_value = "failed"
                assert client.post(f"/teacher/jobs/{job}/moderation-review/withdraw", json=withdrawal).status_code == 200
                queue.fetch_job.return_value.requeue.assert_called_once()
                queue.enqueue.side_effect = None
                from app.auth import owned_job, require_teacher
                app.dependency_overrides[owned_job] = lambda: complete
                app.dependency_overrides[require_teacher] = lambda: {"id": teacher}
                try:
                    assert client.post(f"/jobs/{job}/review", json={"decision": "approved"}).status_code == 409
                finally:
                    app.dependency_overrides.pop(owned_job, None)
                    app.dependency_overrides.pop(require_teacher, None)
                run_review_storybook_job(job, expected_epoch=5, review_id=withdrawn.json()["review_id"])
                reopened = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                assert reopened["ready"] is True and reopened["review_id"] == withdrawal["request_id"]
                release = {**command, "review_id": reopened["review_id"], "expected_epoch": 5, "request_id": str(uuid4())}
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=release).status_code == 202
                run_review_storybook_job(job, expected_epoch=6)
                restored = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
                assert restored["status"] == "complete" and restored["approved_at"] is None
                assert restored["image_count"] == 3 and primary.call_count == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)
    elif failure == "projection":
        # Missing retained evidence must never become a restart or a new paid job.
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
        monkeypatch.setattr("providers.download_book_image", lambda path: image)
        try:
            with TestClient(app) as client:
                detail = client.get(f"/teacher/jobs/{job}/moderation-review").json()
                command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                           "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                           "action": "allow", "policy_version": detail["current_policy_version"],
                           "confirmed_criteria": detail["criteria"], "confirmed": True}
                queue = MagicMock()
                monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
                assert client.post(f"/teacher/jobs/{job}/moderation-review/decision", json=command).status_code == 202
                PostgresSaver(conn).delete_thread(job)
                primary_text, backstop_text = MagicMock(side_effect=RuntimeError("unexpected restart")), MagicMock(side_effect=RuntimeError("unexpected restart"))
                monkeypatch.setattr("pipeline.input_gate.classify_text_primary", primary_text)
                monkeypatch.setattr("pipeline.input_gate.classify_text_backstop", backstop_text)
                with pytest.raises(RuntimeError, match="checkpoint_unavailable"):
                    run_review_storybook_job(job, expected_epoch=2, review_id=detail["review_id"])
                assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "failed"
                primary.assert_called_once()
                primary_text.assert_not_called()
                backstop_text.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("action", ["allow", "replace", "stop", "budget", "withdraw"])
def test_reference_hold_uses_private_teacher_decisions(monkeypatch, held_database, action):
    from langgraph.checkpoint.postgres import PostgresSaver
    from contracts.story_memory import Character, RefVerdict
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, job, teacher = held_database
    image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
    conn.execute("""insert into jobs(id,status,input_text,title,profile_id,classroom_id,moderation_mode)
      values (%s,'running','The dog walks across the field.','Synthetic title',%s,%s,'teacher_review_v1')""", (job, child, classroom))
    state = StoryMemory(schema_version=1, story_id=job, profile_id=child, classroom_id=classroom,
        input=Input(raw_text="The dog walks across the field."),
        characters=[Character(char_id="c0", name="Dog", canonical_ref_image=f"{job}/ref-c0-1.png",
                              ref_generation_prompt="A dog. Be sure to include: white paws.")],
        scenes=[Scene(scene_id="s0", text_excerpt="The dog walks.")],
        moderation_context=ModerationContext(mode="teacher_review_v1", policy_version="teacher_review_policy_v1"))
    primary, draw, queue, storage = MagicMock(return_value=False), MagicMock(return_value=image), MagicMock(), MagicMock()
    monkeypatch.setattr("pipeline.char_ref_mod.classify_image_primary", primary)
    monkeypatch.setattr("pipeline.char_ref_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.char_ref_mod.download_book_image", lambda path: image)
    monkeypatch.setattr("providers.download_book_image", lambda path: image)
    monkeypatch.setattr("pipeline.char_bible.text_to_image", draw)
    monkeypatch.setattr("pipeline.char_bible.get_supabase_client", lambda: storage)
    monkeypatch.setattr("pipeline.char_bible.judge", lambda *a: RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"]))
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
    saver = PostgresSaver(conn)
    saver.setup()
    graph, config = build_graph(saver), {"configurable": {"thread_id": job}}
    graph.update_state(config, dict(state), as_node="char_bible")
    graph.invoke(None, config)
    run_review_storybook_job(job)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
    try:
        with TestClient(app) as client:
            route = f"/teacher/jobs/{job}/moderation-review"
            detail = client.get(route).json()
            assert detail["kind"] == "character_reference" and detail["ready"]
            assert detail["pictures"][0]["state"] == "held"
            assert [p["state"] for p in detail["pictures"]].count("held") == 1
            assert detail["replacement_available"] is True
            assert "image_path" not in str(detail)
            reveal = {"review_id": detail["review_id"], "subject_version": detail["subject_version"]}
            assert client.get(f"{route}/images/ref-c0", params=reveal).status_code == 404
            assert client.post(f"{route}/reveal", json=reveal).content == image
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.get(f"/jobs/{job}/images/ref-c0").status_code == 404
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            command = {**reveal, "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                       "action": action if action in ("replace", "stop") else "allow",
                       "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"], "confirmed": True}
            if action == "budget":
                from app.config import IMAGE_BUDGET
                conn.execute("update jobs set image_count=%s where id=%s", (IMAGE_BUDGET, job))
                assert client.get(route).json()["replacement_disabled_reason"] == "image_budget_exhausted"
                assert client.post(f"{route}/decision", json={**command, "action": "replace"}).status_code == 422
                draw.assert_not_called()
                return
            result = client.post(f"{route}/decision", json=command)
            assert result.status_code == (200 if action == "stop" else 202), result.text
            assert client.post(f"{route}/decision", json=command).status_code == 200
            run_review_storybook_job(job, expected_epoch=2)
            run_review_storybook_job(job, expected_epoch=2)
            current = client.get(route).json()
            if action == "replace":
                assert current["status"] == "awaiting_teacher" and current["review_id"] != detail["review_id"]
                assert current["replacement_disabled_reason"] == "replacement_already_used"
                assert draw.call_count == 1
                assert draw.call_args.args[0] == "A dog. Be sure to include: white paws."
                assert client.post(f"{route}/decision", json={**command, "request_id": str(uuid4()), "action": "allow"}).status_code == 409
                assert graph.get_state(config).values["characters"][0].canonical_ref_image == f"{job}/ref-c0-2.png"
            else:
                draw.assert_not_called()
                assert current["status"] == ("stopped" if action == "stop" else "awaiting_confirm")
            if action == "withdraw":
                assert len(current["clearances"]) == 1
                withdrawal = {"clearance_review_id": detail["review_id"], "subject_version": detail["subject_version"],
                              "expected_epoch": 2, "request_id": str(uuid4()), "confirmed": True}
                response = client.post(f"{route}/withdraw", json=withdrawal)
                assert response.status_code == 202, response.text
                run_review_storybook_job(job, expected_epoch=3, review_id=withdrawal["request_id"])
                reopened = client.get(route).json()
                assert reopened["ready"] and reopened["kind"] == "character_reference"
                release = {**command, "review_id": reopened["review_id"], "expected_epoch": 3, "request_id": str(uuid4())}
                assert client.post(f"{route}/decision", json=release).status_code == 202
                run_review_storybook_job(job, expected_epoch=4)
                assert client.get(route).json()["status"] == "awaiting_confirm"
                assert primary.call_count == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("action", ["allow", "stop", "withdraw_during_analyze", "withdraw_during_segment"])
def test_processed_story_hold_uses_exact_teacher_decision(monkeypatch, held_database, action):
    from langgraph.checkpoint.postgres import PostgresSaver
    from contracts.story_memory import RefVerdict
    from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation
    from tests.test_graph_stub import STUB_ANALYSIS
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, job, teacher = held_database
    text = "A dog runs in a field. The dog barks."
    primary, backstop = MagicMock(return_value=(False, ["S1"])), MagicMock()
    queue, storage, db = MagicMock(), MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("providers.classify_text_primary", lambda text: (True, []))
    monkeypatch.setattr("providers.classify_text_backstop", lambda text: (True, []))
    monkeypatch.setattr("providers.redact_pii", lambda text: text.replace(" Contact 09171234567.", ""))
    image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
    storage.storage.from_.return_value.download.return_value = image
    monkeypatch.setattr("pipeline.input_gate.classify_text_primary", primary)
    monkeypatch.setattr("pipeline.input_gate.classify_text_backstop", backstop)
    monkeypatch.setattr("pipeline.input_gate.redact_pii", lambda text: text)
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
    analysis = MagicMock(return_value=STUB_ANALYSIS)
    monkeypatch.setattr("pipeline.analyze.structured_text", analysis)
    monkeypatch.setattr("pipeline.segment.structured_text", lambda *a, **kw: SceneSegmentation(scenes=[ExtractedScene(
        start=0, end=1, characters_present=["the orange dog"],
        visual_direction=ExtractedVisualDirection(key_action="A dog runs.", viewpoint="front view", framing="wide shot"))]))
    monkeypatch.setattr("pipeline.char_bible.text_to_image", lambda *a, **kw: image)
    monkeypatch.setattr("pipeline.char_bible.get_supabase_client", lambda: storage)
    monkeypatch.setattr("pipeline.char_bible.judge", lambda *a: RefVerdict(
        differences_observed="none", matches_description=True, attributes_present=["dog"]))
    reference_check = MagicMock(return_value=False)
    monkeypatch.setattr("pipeline.char_ref_mod.classify_image_primary", reference_check)
    monkeypatch.setattr("pipeline.char_ref_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.char_ref_mod.download_book_image", lambda path: image)
    monkeypatch.setattr("providers.download_book_image", lambda path: image)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            submitted = client.post("/storybooks", json={"text": text + " Contact 09171234567.", "title": "Synthetic title"})
            assert submitted.status_code == 200, submitted.text
            job = submitted.json()["job_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert conn.execute("select input_text from jobs where id=%s", (job,)).fetchone()["input_text"] == text
    run_review_storybook_job(job, expected_epoch=0)
    analysis.assert_not_called()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
    route = f"/teacher/jobs/{job}/moderation-review"
    try:
        with TestClient(app) as client:
            detail = client.get(route).json()
            assert detail["kind"] == "story_text" and detail["ready"]
            assert detail["story_text"] == text and detail["pictures"] == []
            assert detail["replacement_available"] is False
            assert detail["classifier_evidence"][0]["categories"] == ["S1"]
            command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()), "action": "stop" if action == "stop" else "allow",
                "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"], "confirmed": True}
            assert client.post(f"{route}/decision", json={**command, "subject_version": "stale"}).status_code == 409
            assert client.post(f"{route}/decision", json={**command, "action": "replace"}).status_code == 422
            response = client.post(f"{route}/decision", json=command)
            assert response.status_code == (200 if action == "stop" else 202), response.text
            assert client.post(f"{route}/decision", json=command).status_code == 200
            early_withdrawal = {"clearance_review_id": detail["review_id"], "subject_version": detail["subject_version"],
                "expected_epoch": 2, "request_id": str(uuid4()), "confirmed": True}
            if action.startswith("withdraw_during_"):
                def withdraw_after_check(*args, **kwargs):
                    response = client.post(f"{route}/withdraw", json=early_withdrawal)
                    assert response.status_code == 202, response.text
                    return STUB_ANALYSIS if action == "withdraw_during_analyze" else segmentation
                if action == "withdraw_during_analyze":
                    analysis.side_effect = withdraw_after_check
                else:
                    segmentation = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1,
                        characters_present=["the orange dog"], visual_direction=ExtractedVisualDirection(
                            key_action="A dog runs.", viewpoint="front view", framing="wide shot"))])
                    monkeypatch.setattr("pipeline.segment.structured_text", withdraw_after_check)
            run_review_storybook_job(job, expected_epoch=2)
            run_review_storybook_job(job, expected_epoch=2)
            if action == "stop":
                assert client.get(route).json()["status"] == "stopped"
                analysis.assert_not_called()
                reference_check.assert_not_called()
                return
            if action.startswith("withdraw_during_"):
                run_review_storybook_job(job, expected_epoch=3, review_id=early_withdrawal["request_id"])
                reopened = client.get(route).json()
                assert reopened["kind"] == "story_text" and reopened["ready"]
                retained = build_graph(PostgresSaver(conn)).get_state({"configurable": {"thread_id": job}})
                assert retained.values["moderation_context"].review.return_node == (
                    "segment" if action == "withdraw_during_analyze" else "char_bible")
                release = {**command, "review_id": reopened["review_id"], "expected_epoch": 3, "request_id": str(uuid4())}
                assert client.post(f"{route}/decision", json=release).status_code == 202
                run_review_storybook_job(job, expected_epoch=4)
            # Text permission cannot release a later generated picture.
            held_reference = client.get(route).json()
            assert held_reference["kind"] == "character_reference" and held_reference["ready"]
            assert held_reference["review_id"] != detail["review_id"]
            assert client.post(f"{route}/decision", json={**command, "request_id": str(uuid4())}).status_code == 409
            next_command = {**command, "review_id": held_reference["review_id"],
                "subject_version": held_reference["subject_version"], "expected_epoch": held_reference["generation_epoch"],
                "request_id": str(uuid4())}
            assert client.post(f"{route}/decision", json=next_command).status_code == 202
            reference_epoch = held_reference["generation_epoch"] + 1
            run_review_storybook_job(job, expected_epoch=reference_epoch)
            assert client.get(route).json()["status"] == "awaiting_confirm"
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.get(f"/jobs/{job}/images/ref-c0").status_code == 200
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            retained = build_graph(PostgresSaver(conn)).get_state({"configurable": {"thread_id": job}})
            assert retained.values["input"].redacted_text == text
            assert retained.values["input"].moderation.passed is False
            assert retained.values["input"].moderation_clearance.subject_version == detail["subject_version"]
            assert retained.values["moderation_context"].review.kind == "character_reference"
            assert analysis.call_count == reference_check.call_count == primary.call_count == 1
            backstop.assert_not_called()
            monkeypatch.setattr("pipeline.generate_scene.edit_image", lambda *a: image)
            monkeypatch.setattr("pipeline.generate_scene.get_signed_url", lambda path: path)
            monkeypatch.setattr("pipeline.generate_scene.get_supabase_client", lambda: storage)
            monkeypatch.setattr("pipeline.consistency_check.get_supabase_client", lambda: storage)
            monkeypatch.setattr("pipeline.consistency_check.judge", lambda prompt, urls, schema, **kw:
                schema(differences_observed="none", contradictions=[], same_character=True))
            scene_check = MagicMock(return_value=False)
            monkeypatch.setattr("pipeline.output_mod.classify_image_primary", scene_check)
            monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
            monkeypatch.setattr("pipeline.output_mod.download_book_image", lambda path: image)
            db = MagicMock()
            job_row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
            job_row["profile_id"] = child
            db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [job_row]
            monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.post(f"/jobs/{job}/confirm", json={"action": "confirm"}).status_code == 200
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            run_review_storybook_job(job, {"action": "confirm"}, expected_epoch=reference_epoch)
            held_scene = client.get(route).json()
            assert held_scene["kind"] == "scene_image" and held_scene["ready"]
            scene_command = {**command, "review_id": held_scene["review_id"], "subject_version": held_scene["subject_version"],
                "expected_epoch": held_scene["generation_epoch"], "request_id": str(uuid4())}
            assert client.post(f"{route}/decision", json=scene_command).status_code == 202
            scene_epoch = held_scene["generation_epoch"] + 1
            run_review_storybook_job(job, expected_epoch=scene_epoch)
            complete = client.get(route).json()
            assert complete["status"] == "complete"
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
            assert client.get(f"/jobs/{job}/images/scene-s0").status_code == 200
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=teacher)
            text_clearance = next(c for c in complete["clearances"] if c["label"] == "Story text")
            withdrawal = {"clearance_review_id": text_clearance["review_id"], "subject_version": text_clearance["subject_version"],
                "expected_epoch": scene_epoch, "request_id": str(uuid4()), "confirmed": True}
            response = client.post(f"{route}/withdraw", json=withdrawal)
            assert response.status_code == 202, response.text
            run_review_storybook_job(job, expected_epoch=scene_epoch + 1, review_id=withdrawal["request_id"])
            reopened = client.get(route).json()
            assert reopened["kind"] == "story_text" and reopened["ready"]
            assert build_graph(PostgresSaver(conn)).get_state({"configurable": {"thread_id": job}}).values["input"].moderation_clearance is None
            release = {**command, "review_id": reopened["review_id"], "expected_epoch": scene_epoch + 1, "request_id": str(uuid4())}
            assert client.post(f"{route}/decision", json=release).status_code == 202
            run_review_storybook_job(job, expected_epoch=scene_epoch + 2)
            assert client.get(route).json()["status"] == "complete"
            assert analysis.call_count == reference_check.call_count == scene_check.call_count == primary.call_count == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_review_interrupt_cannot_be_written_to_child_reveal():
    from langgraph.types import Interrupt
    from worker.run_job import _finish

    db = MagicMock()
    with pytest.raises(RuntimeError, match="moderation"):
        _finish(db, str(uuid4()), {"__interrupt__": [Interrupt({
            "kind": "moderation_review", "review_id": str(uuid4()),
        })]})
    db.table.return_value.update.assert_not_called()


def test_draw_again_keeps_the_replaced_picture_and_choosing_it_costs_nothing(monkeypatch, held_database):
    """Magic pencil ticket 04 (US-01): tap → the old picture is offered → choosing it restores it
    with no draw and no go. Stale and repeated choices change nothing; the record follows the story."""
    import importlib
    from contracts.story_memory import RefVerdict
    from langgraph.checkpoint.postgres import PostgresSaver
    from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation
    from tests.test_graph_stub import STUB_ANALYSIS
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, _, _ = held_database
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    monkeypatch.setattr(settings, "enable_magic_pencil", True)
    db, queue = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)

    def redact(text):
        # SH-01: the setting is captured at submission; turning it off later changes nothing.
        settings.enable_magic_pencil = False
        return text

    monkeypatch.setattr("providers.redact_pii", redact)
    monkeypatch.setattr("app.main.check_text", lambda title, **kwargs: (True, [], title))
    image = (Path(__file__).parent / "fixtures/qwen35-resize-scene.png").read_bytes()
    objects, storage = {}, MagicMock()

    def download(path):
        if path not in objects:
            raise FileNotFoundError(path)
        return objects[path]

    storage.storage.from_.return_value.download.side_effect = download
    storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})
    monkeypatch.setattr("providers.download_book_image", download)

    def structured(prompt, schema, **kwargs):
        if schema.__name__ == "StoryAnalysis":
            return STUB_ANALYSIS
        return SceneSegmentation(scenes=[ExtractedScene(
            start=0, end=0, characters_present=["the orange dog"],
            visual_direction=ExtractedVisualDirection(key_action="A dog walks.", viewpoint="front view", framing="wide shot"),
        )])

    drawn = MagicMock(side_effect=lambda *a, **kw: image)
    boundaries = {
        "analyze": {"structured_text": structured}, "segment": {"structured_text": structured},
        "input_gate": {"classify_text_primary": lambda text: (True, []), "classify_text_backstop": lambda text: (True, [])},
        "char_bible": {"text_to_image": drawn, "get_supabase_client": lambda: storage,
                       "judge": lambda *a, **kw: RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"])},
        "char_ref_mod": {"classify_image_primary": lambda url, **kw: True, "classify_image_backstop": lambda url, **kw: True,
                         "get_signed_url": lambda path: f"https://private.invalid/{path}"},
    }
    for module, replacements in boundaries.items():
        for name, replacement in replacements.items():
            monkeypatch.setattr(importlib.import_module(f"pipeline.{module}"), name, replacement)

    def reveal_of(job):
        # confirm_job reads the row through the Supabase client; serve it the persisted one.
        persisted = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{**persisted, "profile_id": child}]
        return persisted["reveal"]["characters"][0]

    def counts(job):
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
            cost = build_graph(saver).get_state({"configurable": {"thread_id": job}}).values["cost"]
        return cost.image_count, cost.ref_retry_count

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            job = client.post("/storybooks", json={
                "title": "Synthetic title", "text": "The orange dog walks through the grassy field past the trees and stops near the stream.",
            }).json()["job_id"]
            run_review_storybook_job(job, expected_epoch=0)
            first = reveal_of(job)
            assert first["image_path"] == f"{job}/ref-c0-1.png" and first["versions"] == []
            tap = {"action": "try_again", "char_id": "c0", "attribute": first["chips"][0]}
            assert client.post(f"/jobs/{job}/confirm", json=tap).json()["status"] == "queued"
            run_review_storybook_job(job, tap, expected_epoch=0)
            tapped = reveal_of(job)
            assert tapped["image_path"] == f"{job}/ref-c0-2.png"
            version = {"version_id": "ref-c0-1", "image_path": f"{job}/ref-c0-1.png"}
            assert tapped["versions"] == [version]
            assert client.get(f"/jobs/{job}/images/version-{version['version_id']}").content == image
            assert client.get(f"/jobs/{job}/images/version-nope").status_code == 404
            before = counts(job)
            choose = {"action": "choose_version", "char_id": "c0", "version_id": version["version_id"], "source": tapped["image_path"]}
            assert client.post(f"/jobs/{job}/confirm", json={**choose, "source": first["image_path"]}).status_code == 422
            assert client.post(f"/jobs/{job}/confirm", json={**choose, "version_id": "ref-c0-9"}).status_code == 422
            queue.enqueue.reset_mock()
            assert client.post(f"/jobs/{job}/confirm", json=choose).json()["status"] == "queued"
            assert client.post(f"/jobs/{job}/confirm", json=choose).json()["status"] == "queued"
            assert queue.enqueue.call_count == 1
            draws = drawn.call_count
            run_review_storybook_job(job, queue.enqueue.call_args.args[2], expected_epoch=0)
            restored = reveal_of(job)
            assert restored["image_path"] == first["image_path"]
            assert restored["versions"] == [{"version_id": "ref-c0-2", "image_path": f"{job}/ref-c0-2.png"}]
            assert drawn.call_count == draws and counts(job) == before
            assert client.get(f"/jobs/{job}/images/ref-c0").content == image
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    recorded = conn.execute("select image_path from job_picture_records where job_id=%s order by created_at", (job,)).fetchall()
    assert [r["image_path"] for r in recorded] == [first["image_path"], tapped["image_path"]]
    conn.execute("delete from jobs where id=%s", (job,))
    assert conn.execute("select count(*) as n from job_picture_records where job_id=%s", (job,)).fetchone()["n"] == 0


def test_unchosen_draws_are_moderated_once_when_opened_and_a_passed_one_can_be_chosen(monkeypatch, held_database):
    """Magic pencil ticket 05 (US-01 AC-02, AC-03, SH-02, OD-03): the mint's two unchosen draws are
    kept unreviewed; opening "Other versions" moderates each once. A pass is shown, a flag is
    excluded with no hold, a classifier error is neither shown nor stored."""
    import importlib
    from contracts.story_memory import RefVerdict
    from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation
    from tests.test_graph_stub import STUB_ANALYSIS
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, _, _ = held_database
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    monkeypatch.setattr(settings, "enable_magic_pencil", True)
    db, queue = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
    monkeypatch.setattr("providers.redact_pii", lambda text: text)
    monkeypatch.setattr("app.main.check_text", lambda title, **kwargs: (True, [], title))
    draws = iter([b"draw-1", b"draw-2", b"draw-3"])
    objects, storage = {}, MagicMock()
    storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])

    def structured(prompt, schema, **kwargs):
        if schema.__name__ == "StoryAnalysis":
            return STUB_ANALYSIS
        return SceneSegmentation(scenes=[ExtractedScene(
            start=0, end=0, characters_present=["the orange dog"],
            visual_direction=ExtractedVisualDirection(key_action="A dog walks.", viewpoint="front view", framing="wide shot"),
        )])

    # Every draw contradicts once; draw 2 shows the most, so best-of picks it and draws 1 and 3 are unchosen.
    shown = iter([["dog"], ["dog", "orange"], ["dog"]])
    primary, backstop = {}, {}

    def classify(table):
        def call(url, **kwargs):
            outcome = table.get(url.rsplit("/", 1)[-1], True)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return MagicMock(side_effect=call)

    primary_mock, backstop_mock = classify(primary), classify(backstop)
    boundaries = {
        "analyze": {"structured_text": structured}, "segment": {"structured_text": structured},
        "input_gate": {"classify_text_primary": lambda text: (True, []), "classify_text_backstop": lambda text: (True, [])},
        "char_bible": {"text_to_image": lambda *a, **kw: next(draws), "get_supabase_client": lambda: storage,
                       "judge": lambda *a, **kw: RefVerdict(differences_observed="a red comb", contradictions=["comb"],
                                                            matches_description=False, attributes_present=next(shown))},
        "char_ref_mod": {"classify_image_primary": primary_mock, "classify_image_backstop": backstop_mock,
                         "get_signed_url": lambda path: f"https://private.invalid/{path}"},
    }
    for module, replacements in boundaries.items():
        for name, replacement in replacements.items():
            monkeypatch.setattr(importlib.import_module(f"pipeline.{module}"), name, replacement)

    def reveal_of(job):
        persisted = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{**persisted, "profile_id": child}]
        return persisted["reveal"]["characters"][0]

    def calls():
        return primary_mock.call_count + backstop_mock.call_count

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            job = client.post("/storybooks", json={
                "title": "Synthetic title", "text": "The orange dog walks through the grassy field past the trees and stops near the stream.",
            }).json()["job_id"]
            run_review_storybook_job(job, expected_epoch=0)
            first = reveal_of(job)
            assert first["image_path"] == f"{job}/ref-c0-1.png" and objects[first["image_path"]] == b"draw-2"
            assert first["versions"] == [] and first["unreviewed"] == ["ref-c0-1-u1", "ref-c0-1-u3"]
            assert client.get(f"/jobs/{job}/images/version-ref-c0-1-u1").status_code == 404
            reviews = conn.execute("select count(*) as n from job_moderation_reviews where job_id=%s", (job,)).fetchone()["n"]

            route = f"/jobs/{job}/characters/c0/versions/open"
            backstop["ref-c0-1-u3.png"] = RuntimeError("classifier down")
            before = calls()
            opened = client.post(route)
            assert opened.status_code == 200
            assert opened.json() == {"versions": [{"version_id": "ref-c0-1-u1", "image_path": f"{job}/ref-c0-1-u1.png"}],
                                     "unavailable": 1}
            assert calls() - before == 4   # both layers on each of two draws
            assert client.get(f"/jobs/{job}/images/version-ref-c0-1-u1").content == b"draw-1"
            assert client.get(f"/jobs/{job}/images/version-ref-c0-1-u3").status_code == 404

            primary["ref-c0-1-u3.png"] = False
            before = calls()
            assert client.post(route).json() == {
                "versions": [{"version_id": "ref-c0-1-u1", "image_path": f"{job}/ref-c0-1-u1.png"}], "unavailable": 0}
            assert calls() - before == 1   # only the errored draw is checked again; a primary flag needs no backstop
            before = calls()
            assert client.post(route).json()["unavailable"] == 0
            assert calls() == before       # every outcome is stored once
            assert conn.execute("select count(*) as n from job_moderation_reviews where job_id=%s",
                                (job,)).fetchone()["n"] == reviews
            assert client.get(f"/jobs/{job}/images/version-ref-c0-1-u3").status_code == 404
            assert client.post(f"/jobs/{job}/characters/c9/versions/open").status_code == 404

            choose = {"action": "choose_version", "char_id": "c0", "version_id": "ref-c0-1-u3", "source": first["image_path"]}
            assert client.post(f"/jobs/{job}/confirm", json=choose).status_code == 422
            queue.enqueue.reset_mock()
            choose["version_id"] = "ref-c0-1-u1"
            assert client.post(f"/jobs/{job}/confirm", json=choose).json()["status"] == "queued"
            resume = queue.enqueue.call_args.args[2]
            assert resume["cleared"] is True
            run_review_storybook_job(job, resume, expected_epoch=0)
            chosen = reveal_of(job)
            assert chosen["image_path"] == f"{job}/ref-c0-1-u1.png"
            assert chosen["versions"] == [{"version_id": "ref-c0-1", "image_path": f"{job}/ref-c0-1.png"}]
            assert chosen["unreviewed"] == []   # AC-01: an excluded draw no longer counts as another version
            assert client.get(f"/jobs/{job}/images/ref-c0").content == b"draw-1"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    recorded = conn.execute("""select version_id,moderation_status from job_picture_records
      where job_id=%s and source='unchosen_draw' order by version_id""", (job,)).fetchall()
    assert [(r["version_id"], r["moderation_status"]) for r in recorded] == [
        ("ref-c0-1-u1", "passed"), ("ref-c0-1-u3", "excluded")]


def _pencil_book(monkeypatch, held_database, text_check):
    """A feature job paused at the reveal, with every provider boundary stubbed (spec §6.2-6.3).
    `text_check` stands in for `check_text` on the child's pencil text."""
    import importlib
    from contracts.story_memory import RefVerdict
    from pipeline.segment import ExtractedScene, ExtractedVisualDirection, SceneSegmentation
    from tests.test_graph_stub import STUB_ANALYSIS
    from worker.run_job import run_review_storybook_job

    conn, child, classroom, _, teacher = held_database
    monkeypatch.setattr(settings, "enable_teacher_moderation_review", True)
    monkeypatch.setattr(settings, "enable_magic_pencil", True)
    db, queue = MagicMock(), MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"classroom_id": classroom}]
    monkeypatch.setattr("app.main.get_supabase_client", lambda: db)
    monkeypatch.setattr("app.main.get_queue", lambda: queue)
    monkeypatch.setattr("app.moderation_hold.get_queue", lambda: queue)
    redacted = []

    def redact(text):
        redacted.append(text)
        return text.replace("Ana Cruz", "<PERSON>")

    monkeypatch.setattr("providers.redact_pii", redact)
    monkeypatch.setattr("app.main.check_text", lambda title, **kwargs: (True, [], title))
    monkeypatch.setattr("app.moderation_hold.check_text", text_check)
    objects, storage = {}, MagicMock()
    storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])

    def structured(prompt, schema, **kwargs):
        if schema.__name__ == "StoryAnalysis":
            return STUB_ANALYSIS
        return SceneSegmentation(scenes=[ExtractedScene(
            start=0, end=0, characters_present=["the orange dog"],
            visual_direction=ExtractedVisualDirection(key_action="A dog walks.", viewpoint="front view", framing="wide shot"),
        )])

    edit = MagicMock(return_value=b"edited")
    judge = MagicMock(return_value=RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"]))
    boundaries = {
        "analyze": {"structured_text": structured}, "segment": {"structured_text": structured},
        "input_gate": {"classify_text_primary": lambda text: (True, []), "classify_text_backstop": lambda text: (True, [])},
        "char_bible": {"text_to_image": lambda *a, **kw: b"first", "edit_image": edit, "judge": judge,
                       "get_supabase_client": lambda: storage, "get_signed_url": lambda path: f"https://private.invalid/{path}"},
        "char_ref_mod": {"classify_image_primary": lambda url, **kw: True, "classify_image_backstop": lambda url, **kw: True,
                         "get_signed_url": lambda path: f"https://private.invalid/{path}"},
    }
    for module, replacements in boundaries.items():
        for name, replacement in replacements.items():
            monkeypatch.setattr(importlib.import_module(f"pipeline.{module}"), name, replacement)

    def reveal_of(job):
        persisted = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{**persisted, "profile_id": child}]
        return persisted["reveal"]

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    client = TestClient(app)
    job = client.post("/storybooks", json={
        "title": "Synthetic title", "text": "The orange dog walks through the grassy field past the trees and stops near the stream.",
    }).json()["job_id"]
    run_review_storybook_job(job, expected_epoch=0)
    redacted.clear()
    judge.reset_mock()
    return SimpleNamespace(conn=conn, client=client, job=job, queue=queue, edit=edit, judge=judge, objects=objects,
                           redacted=redacted, reveal_of=reveal_of, run=run_review_storybook_job, child=child, teacher=teacher)


def _pencil_rows(conn, job):
    return [dict(r) for r in conn.execute("""select target_id,version_id,before_path,image_path,pencil_text,
      text_moderation,picture_moderation,reason,choice from job_picture_records where job_id=%s and kind='pencil'
      order by version_id""", (job,)).fetchall()]


def test_a_cleared_pencil_text_edits_the_picture_once_and_the_child_keeps_or_goes_back(monkeypatch, held_database):
    """Magic pencil ticket 06 (US-02 AC-07..AC-11, SH-03, SH-08, SH-10, AC-22)."""
    checked = []

    def text_check(text, *, evidence=None):
        checked.append(text)
        return True, [], text

    book = _pencil_book(monkeypatch, held_database, text_check)
    job, client, queue = book.job, book.client, book.queue
    try:
        first = book.reveal_of(job)
        assert first["taps_left"] == 3 and first["characters"][0]["pencil_ready"] is True
        old = first["characters"][0]["image_path"]
        pencil = {"action": "pencil", "char_id": "c0", "text": "  give Ana Cruz a red hat ", "source": old}
        for bad in ({**pencil, "text": "   "}, {**pencil, "text": "x" * 201}):
            assert client.post(f"/jobs/{job}/confirm", json=bad).status_code == 422
        assert client.post(f"/jobs/{job}/confirm", json={**pencil, "source": f"{job}/ref-c0-9.png"}).status_code == 422
        assert book.redacted == [] and checked == []   # nothing was redacted, moderated or queued
        queue.enqueue.reset_mock()
        assert client.post(f"/jobs/{job}/confirm", json=pencil).json()["status"] == "queued"
        assert client.post(f"/jobs/{job}/confirm", json=pencil).json()["status"] == "queued"   # SH-08
        assert queue.enqueue.call_count == 1
        # SH-03: redacted before moderation; only the redacted text leaves the API.
        assert book.redacted == ["give Ana Cruz a red hat"] and checked == ["give <PERSON> a red hat"]
        resume = queue.enqueue.call_args.args[2]
        assert (resume["text"], resume["flagged"]) == ("give <PERSON> a red hat", False)
        assert "Ana Cruz" not in str(resume)

        book.run(job, resume, expected_epoch=0)
        edited = book.reveal_of(job)
        book.edit.assert_called_once()
        assert book.edit.call_args.args[0].startswith("give <PERSON> a red hat\n\n")
        book.judge.assert_not_called()
        assert edited["taps_left"] == 2
        character = edited["characters"][0]
        assert character["image_path"] == f"{job}/ref-c0-2.png"
        assert character["pencil_choice"] == {"use_id": "pencil-1", "version_id": "ref-c0-1", "image_path": old}
        assert client.get(f"/jobs/{job}/images/version-ref-c0-1").content == b"first"
        assert client.get(f"/jobs/{job}/images/ref-c0").content == b"edited"
        # The book cannot go on from an unchosen pencil result.
        assert client.post(f"/jobs/{job}/confirm", json={"action": "confirm"}).status_code == 422

        choose = {"action": "pencil_choice", "char_id": "c0", "choice": "old", "source": character["image_path"]}
        assert client.post(f"/jobs/{job}/confirm", json={**choose, "source": old}).status_code == 422
        queue.enqueue.reset_mock()
        assert client.post(f"/jobs/{job}/confirm", json=choose).json()["status"] == "queued"
        book.run(job, queue.enqueue.call_args.args[2], expected_epoch=0)
        back = book.reveal_of(job)
        assert back["taps_left"] == 2   # AC-11: the go is spent either way
        assert back["characters"][0]["image_path"] == old
        assert back["characters"][0]["pencil_choice"] is None
        assert {"version_id": "ref-c0-2", "image_path": f"{job}/ref-c0-2.png"} in back["characters"][0]["versions"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert _pencil_rows(book.conn, job) == [{
        "target_id": "c0", "version_id": "pencil-1", "before_path": old, "image_path": f"{job}/ref-c0-2.png",
        "pencil_text": "give <PERSON> a red hat", "text_moderation": "cleared", "picture_moderation": "passed",
        "reason": None, "choice": "old"}]


def test_a_redaction_failure_rejects_the_pencil_text_and_spends_nothing(monkeypatch, held_database):
    book = _pencil_book(monkeypatch, held_database, lambda text, **kw: (True, [], text))
    monkeypatch.setattr("providers.redact_pii", MagicMock(side_effect=RuntimeError("presidio down")))
    try:
        source = book.reveal_of(book.job)["characters"][0]["image_path"]
        book.queue.enqueue.reset_mock()
        response = book.client.post(f"/jobs/{book.job}/confirm", json={
            "action": "pencil", "char_id": "c0", "text": "a red hat", "source": source})
        assert (response.status_code, response.json()["detail"]) == (503, "privacy_processing_unavailable")
        book.queue.enqueue.assert_not_called()
        assert book.conn.execute("select status from jobs where id=%s", (book.job,)).fetchone()["status"] == "awaiting_confirm"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("decision", ["stop", "allow", "stop_removed"])
def test_flagged_pencil_text_is_held_with_no_picture_and_a_teacher_stop_ends_only_the_request(
        monkeypatch, held_database, decision):
    """Ticket 06 (AC-08, SH-05, OD-08): no image and no go while held; allow runs the edit; stop
    returns the child to the reveal with the old picture and the story goes on."""
    from contracts.story_memory import ClassifierEvidence

    def text_check(text, *, evidence=None):
        evidence.append(ClassifierEvidence(layer="primary", model_id="synthetic", instruction_version="v1",
                                           outcome="flagged", categories=["violence"]))
        return False, ["violence"], text

    book = _pencil_book(monkeypatch, held_database, text_check)
    job, client, queue, conn = book.job, book.client, book.queue, book.conn
    try:
        old = book.reveal_of(job)["characters"][0]["image_path"]
        queue.enqueue.reset_mock()
        assert client.post(f"/jobs/{job}/confirm", json={
            "action": "pencil", "char_id": "c0", "text": "a big sword", "source": old}).json()["status"] == "queued"
        book.run(job, queue.enqueue.call_args.args[2], expected_epoch=0)
        held = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        assert held["status"] == "awaiting_teacher"
        book.edit.assert_not_called()
        assert client.get(f"/jobs/{job}/state").json()["pencil_hold"] is True   # SH-05 neutral copy

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        route = f"/teacher/jobs/{job}/moderation-review"
        detail = client.get(route).json()
        assert (detail["kind"], detail["pencil_text"], detail["replacement_available"]) == (
            "character_pencil_text", "a big sword", False)
        assert detail["classifier_evidence"][0]["categories"] == ["violence"]
        command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                   "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                   "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"],
                   "confirmed": True}
        assert client.post(f"{route}/decision", json={**command, "action": "replace"}).status_code == 422
        if decision == "stop_removed":
            # A removed child cannot come back to the reveal, so the stop ends the story instead of
            # leaving a hold nobody can clear.
            conn.execute("update profiles set removed_at=now() where id=%s", (book.child,))
            response = client.post(f"{route}/decision", json={**command, "action": "stop", "confirmed_criteria": []})
            conn.execute("update profiles set removed_at=null where id=%s", (book.child,))
            assert (response.status_code, response.json()["status"]) == (200, "stopped")
            book.edit.assert_not_called()
            return
        queue.enqueue.reset_mock()
        assert client.post(f"{route}/decision", json={**command, "action": decision}).status_code == 202
        dispatched = queue.enqueue.call_args.kwargs
        book.run(job, expected_epoch=dispatched["expected_epoch"], review_id=dispatched["review_id"])
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.child)
        after = book.reveal_of(job)
        assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "awaiting_confirm"
        if decision == "stop":
            assert after["taps_left"] == 3 and after["characters"][0]["image_path"] == old
            book.edit.assert_not_called()
        else:
            assert after["taps_left"] == 2 and after["characters"][0]["pencil_choice"]["image_path"] == old
            book.edit.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    row = _pencil_rows(conn, job)[0]
    assert (row["pencil_text"], row["before_path"]) == ("a big sword", old)
    if decision == "stop":
        assert (row["text_moderation"], row["reason"], row["image_path"]) == ("teacher_stopped", "text_stopped", None)
    else:
        assert (row["text_moderation"], row["image_path"]) == ("teacher_allowed", f"{job}/ref-c0-2.png")


@pytest.mark.parametrize("outcome", ["passes", "flags_again", "budget"])
def test_a_held_pencil_result_is_replaced_by_the_same_edit_once(monkeypatch, held_database, outcome):
    """Ticket 07 (AC-10, AC-22): a teacher replacement of a held pencil result re-runs the same edit
    of the same source picture in ADR-080's one replacement slot; no fresh draw, no child go."""
    from app.config import IMAGE_BUDGET
    from langgraph.checkpoint.postgres import PostgresSaver

    book = _pencil_book(monkeypatch, held_database, lambda text, **kw: (True, [], text))
    job, client, queue, conn = book.job, book.client, book.queue, book.conn
    draw = MagicMock()
    monkeypatch.setattr("pipeline.char_bible.text_to_image", draw)
    flagged = {f"{job}/ref-c0-2.png"} | ({f"{job}/ref-c0-3.png"} if outcome == "flags_again" else set())
    monkeypatch.setattr("pipeline.char_ref_mod.classify_image_primary",
                        lambda url, **kw: url.removeprefix("https://private.invalid/") not in flagged)
    monkeypatch.setattr("pipeline.char_ref_mod.download_book_image", lambda path: book.objects[path])
    try:
        old = book.reveal_of(job)["characters"][0]["image_path"]
        queue.enqueue.reset_mock()
        assert client.post(f"/jobs/{job}/confirm", json={
            "action": "pencil", "char_id": "c0", "text": "a red hat", "source": old}).json()["status"] == "queued"
        book.run(job, queue.enqueue.call_args.args[2], expected_epoch=0)
        assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "awaiting_teacher"

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        route = f"/teacher/jobs/{job}/moderation-review"
        if outcome == "budget":
            conn.execute("update jobs set image_count=%s where id=%s", (IMAGE_BUDGET, job))
        detail = client.get(route).json()
        assert detail["kind"] == "character_reference"
        assert (detail["replacement_available"], detail["replacement_disabled_reason"]) == (
            (False, "image_budget_exhausted") if outcome == "budget" else (True, None))
        command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                   "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()), "action": "replace",
                   "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"],
                   "confirmed": True}
        queue.enqueue.reset_mock()
        response = client.post(f"{route}/decision", json=command)
        if outcome == "budget":
            assert (response.status_code, response.json()["detail"]) == (422, "image_budget_exhausted")
            assert book.edit.call_count == 1
            assert [(r["image_path"], r["picture_moderation"]) for r in _pencil_rows(conn, job)] == [
                (f"{job}/ref-c0-2.png", "flagged")]
            return
        assert response.status_code == 202, response.text
        dispatched = queue.enqueue.call_args.kwargs
        book.run(job, expected_epoch=dispatched["expected_epoch"], review_id=dispatched["review_id"])

        draw.assert_not_called()
        book.judge.assert_not_called()
        assert book.edit.call_count == 2
        prompt, sources = book.edit.call_args.args
        assert prompt.startswith("a red hat\n\n") and sources == [f"https://private.invalid/{old}"]
        assert book.edit.call_args_list[1] == book.edit.call_args_list[0]
        values = build_graph(PostgresSaver(conn)).get_state({"configurable": {"thread_id": job}}).values
        assert (values["cost"].ref_mod_retry_count, values["cost"].ref_retry_count) == (1, 1)
        if outcome == "flags_again":
            current = client.get(route).json()
            assert current["status"] == "awaiting_teacher" and current["review_id"] != detail["review_id"]
            assert current["replacement_disabled_reason"] == "replacement_already_used"
        else:
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.child)
            after = book.reveal_of(job)
            assert after["taps_left"] == 2   # the replacement spends the book's slot, not a child go
            character = after["characters"][0]
            assert character["image_path"] == f"{job}/ref-c0-3.png"
            assert character["pencil_choice"] == {"use_id": "pencil-1", "version_id": "ref-c0-1", "image_path": old}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert _pencil_rows(conn, job) == [{
        "target_id": "c0", "version_id": "pencil-1", "before_path": old, "image_path": f"{job}/ref-c0-3.png",
        "pencil_text": "a red hat", "text_moderation": "cleared",
        "picture_moderation": "flagged" if outcome == "flags_again" else "passed", "reason": None, "choice": None}]


def _finished_feature_book(conn, child, classroom, job, *, magic_pencil=True):
    """A complete teacher-review book. Page s0 has three kept attempts: the cleared final (a1) and two
    the pipeline never moderated (a0, a2). Page s1 has only its final."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from contracts.story_memory import ModerationResult

    paths = {name: f"{job}/{name}.png" for name in ("s0-a0", "s0-a1", "s0-a2", "s1-a0")}
    pages = [{"scene_id": "s0", "caption": "The dog ran.", "image_path": paths["s0-a1"], "other_versions": True},
             {"scene_id": "s1", "caption": "It found a stick.", "image_path": paths["s1-a0"]}]
    conn.execute("""insert into jobs(id,status,input_text,title,profile_id,classroom_id,moderation_mode,
      moderation_settings_snapshot,pages,image_count,worker_finished_at)
      values (%s,'complete','The dog ran. It found a stick.','Synthetic title',%s,%s,'teacher_review_v1',%s,%s,4,now())""",
                 (job, child, classroom, Jsonb({"policy_version": "teacher_review_policy_v1", "magic_pencil": magic_pencil}),
                  Jsonb(pages)))
    state = StoryMemory(schema_version=1, story_id=job, profile_id=child, classroom_id=classroom,
        input=Input(raw_text="The dog ran. It found a stick.", moderation=ModerationResult(passed=True)),
        scenes=[Scene(scene_id="s0", text_excerpt="The dog ran.", caption="The dog ran.", moderation_status="passed",
                      final_image_ref=paths["s0-a1"], attempts=[
                          Attempt(image_ref=paths["s0-a0"]),
                          Attempt(image_ref=paths["s0-a1"], safety_eligibility="cleared"),
                          Attempt(image_ref=paths["s0-a2"])]),
                Scene(scene_id="s1", text_excerpt="It found a stick.", caption="It found a stick.", moderation_status="passed",
                      final_image_ref=paths["s1-a0"], attempts=[Attempt(image_ref=paths["s1-a0"], safety_eligibility="cleared")])],
        moderation_context=ModerationContext(mode="teacher_review_v1", policy_version="teacher_review_policy_v1",
                                             magic_pencil=magic_pencil))
    saver = PostgresSaver(conn)
    saver.setup()
    build_graph(saver).update_state({"configurable": {"thread_id": job}}, dict(state), as_node="compose")
    return paths


def test_a_finished_page_offers_its_other_attempts_moderated_once_on_open(monkeypatch, held_database):
    """Magic pencil ticket 09 (US-03 AC-13, AC-14, SH-02, OD-03): opening a page's other versions
    moderates each attempt nobody checked, once. A pass is shown, a flag is excluded with no hold, a
    classifier error is neither shown nor stored."""
    conn, child, classroom, job, _ = held_database
    paths = _finished_feature_book(conn, child, classroom, job)
    objects = {path: name.encode() for name, path in paths.items()}
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: f"https://private.invalid/{path}")
    outcomes = {"s0-a0.png": True, "s0-a2.png": RuntimeError("classifier down")}

    def classify(url, **kwargs):
        outcome = outcomes[url.rsplit("/", 1)[-1]]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    primary, backstop = MagicMock(return_value=True), MagicMock(side_effect=classify)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", primary)
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", backstop)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            route = f"/jobs/{job}/pages/s0/versions/open"
            opened = client.post(route)
            assert opened.status_code == 200, opened.text
            assert opened.json() == {"versions": [{"version_id": "s0-attempt-0", "image_path": paths["s0-a0"]}],
                                     "unavailable": 1}
            assert primary.call_count == backstop.call_count == 2
            assert client.get(f"/jobs/{job}/images/page-version-s0-attempt-0").content == b"s0-a0"
            assert client.get(f"/jobs/{job}/images/page-version-s0-attempt-2").status_code == 404

            outcomes["s0-a2.png"] = False
            assert client.post(route).json() == {
                "versions": [{"version_id": "s0-attempt-0", "image_path": paths["s0-a0"]}], "unavailable": 0}
            assert backstop.call_count == 3   # only the errored attempt is checked again
            assert client.post(route).json()["unavailable"] == 0
            assert backstop.call_count == 3   # every outcome is stored once
            assert client.get(f"/jobs/{job}/images/page-version-s0-attempt-2").status_code == 404
            assert conn.execute("select count(*) as n from job_moderation_reviews where job_id=%s",
                                (job,)).fetchone()["n"] == 0
            assert client.post(f"/jobs/{job}/pages/s1/versions/open").json() == {"versions": [], "unavailable": 0}
            assert client.post(f"/jobs/{job}/pages/s9/versions/open").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("review", ["approved", "rejected"])
def test_choosing_a_page_version_changes_the_book_and_returns_it_to_the_teacher(monkeypatch, held_database, review):
    """Magic pencil ticket 09 (AC-15, AC-20, SH-08): a chosen version replaces that page in
    `jobs.pages` and on the delivery guard, costs no image, and sets a reviewed book back to pending.
    A repeat applies once; a choice made from a picture that has since changed is rejected."""
    conn, child, classroom, job, _ = held_database
    paths = _finished_feature_book(conn, child, classroom, job)
    conn.execute(f"update jobs set {review}_at=now() where id=%s", (job,))
    objects = {path: name.encode() for name, path in paths.items()}
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", MagicMock(return_value=True))
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop",
                        MagicMock(side_effect=lambda url, **kw: url.endswith("s0-a0.png")))
    paid = MagicMock(side_effect=AssertionError("a version choice drew a picture"))
    monkeypatch.setattr("providers.text_to_image", paid)
    monkeypatch.setattr("providers.edit_image", paid)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            route = f"/jobs/{job}/pages/s0/version"
            assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a1"
            # Not opened yet, so not moderated: nothing to choose.
            assert client.post(route, json={"version_id": "s0-attempt-0", "source": paths["s0-a1"]}).status_code == 422
            client.post(f"/jobs/{job}/pages/s0/versions/open")
            assert client.post(route, json={"version_id": "s0-attempt-2", "source": paths["s0-a1"]}).status_code == 422

            choice = {"version_id": "s0-attempt-0", "source": paths["s0-a1"]}
            chosen = client.post(route, json=choice)
            assert chosen.status_code == 200, chosen.text
            row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
            assert row["pages"] == [
                {"scene_id": "s0", "caption": "The dog ran.", "image_path": paths["s0-a0"], "other_versions": True},
                {"scene_id": "s1", "caption": "It found a stick.", "image_path": paths["s1-a0"]}]
            assert row["approved_at"] is None and row["rejected_at"] is None
            assert row["image_count"] == 4 and row["status"] == "complete"
            assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a0"

            conn.execute("update jobs set approved_at=now() where id=%s", (job,))
            assert client.post(route, json=choice).status_code == 200   # a double submit applies once
            assert conn.execute("select approved_at from jobs where id=%s", (job,)).fetchone()["approved_at"] is not None
            stale = client.post(route, json={"version_id": "s0-attempt-1", "source": paths["s0-a1"]})
            assert stale.status_code == 409 and stale.json()["detail"] == "stale_source"
            assert client.post(f"/jobs/{job}/pages/s0/versions/open").json()["versions"] == [
                {"version_id": "s0-attempt-1", "image_path": paths["s0-a1"]}]
            assert client.post(route, json={"version_id": "s0-attempt-1", "source": paths["s0-a0"]}).status_code == 200
            assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a1"
            # The teacher approved while that change was in flight: the change still wins.
            assert conn.execute("select approved_at from jobs where id=%s", (job,)).fetchone()["approved_at"] is None
            paid.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("book", ["setting_off", "held", "stopped", "classmate"])
def test_page_versions_are_closed_on_a_book_that_is_not_a_finished_feature_book(monkeypatch, held_database, book):
    """Magic pencil ticket 09 (SH-01, SH-09): no page tools on a book submitted with the setting off,
    held for the teacher, or stopped, and none for anyone but the author."""
    conn, child, classroom, job, teacher = held_database
    paths = _finished_feature_book(conn, child, classroom, job, magic_pencil=book != "setting_off")
    conn.execute("insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,moderation_status) "
                 "values (%s,'version','s0','s0-attempt-0',%s,'scene_attempt','passed')", (job, paths["s0-a0"]))
    viewer = teacher if book == "classmate" else child
    if book == "classmate":
        conn.execute("update jobs set approved_at=now() where id=%s", (job,))
    if book == "stopped":
        conn.execute("update jobs set status='stopped' where id=%s", (job,))
    if book == "held":
        conn.execute("""insert into job_moderation_reviews(id,job_id,kind,subject_id,subject_version,subject,criteria,
          policy_version,settings_snapshot,classifier_evidence,return_node)
          values (%s,%s,'scene_image','s1','v',%s,%s,'teacher_review_policy_v1',%s,%s,'output_mod')""",
                     (uuid4(), job, Jsonb({}), ["violence"], Jsonb({}), Jsonb([])))
    monkeypatch.setattr("providers.download_book_image", lambda path: b"picture")
    screen = MagicMock(side_effect=AssertionError("moderated a closed book"))
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", screen)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=viewer)
    try:
        with TestClient(app) as client:
            assert client.post(f"/jobs/{job}/pages/s0/versions/open").status_code == 404
            assert client.post(f"/jobs/{job}/pages/s0/version",
                               json={"version_id": "s0-attempt-0", "source": paths["s0-a1"]}).status_code == 404
            assert client.get(f"/jobs/{job}/images/page-version-s0-attempt-0").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert conn.execute("select pages from jobs where id=%s", (job,)).fetchone()["pages"][0]["image_path"] == paths["s0-a1"]


@pytest.mark.parametrize("magic_pencil", [True, False])
def test_the_finished_book_marks_only_pages_with_two_kept_attempts(magic_pencil):
    """Magic pencil ticket 09 (AC-13, SH-01): "Other versions" is offered on a page with at least two
    attempts that are not excluded, and only on a job submitted with the setting on."""
    from app.moderation_hold import book_pages

    state = StoryMemory(schema_version=1, story_id=str(uuid4()), profile_id="p", classroom_id="c",
        input=Input(raw_text="Synthetic story"),
        scenes=[Scene(scene_id="s0", text_excerpt="a", caption="One.", final_image_ref="j/s0-2.png", attempts=[
                    Attempt(image_ref="j/s0-1.png"), Attempt(image_ref="j/s0-2.png", safety_eligibility="cleared")]),
                Scene(scene_id="s1", text_excerpt="b", caption="Two.", final_image_ref="j/s1-1.png", attempts=[
                    Attempt(image_ref="j/s1-1.png", safety_eligibility="cleared"),
                    Attempt(image_ref="j/s1-2.png", safety_eligibility="excluded")]),
                Scene(scene_id="s2", text_excerpt="c", caption="Three.", final_image_ref="j/s2-2.png", attempts=[
                    Attempt(image_ref="j/s2-1.png", safety_eligibility="teacher_allowed"),
                    Attempt(image_ref="j/s2-2.png", safety_eligibility="cleared")])],
        moderation_context=ModerationContext(mode="teacher_review_v1", magic_pencil=magic_pencil))
    assert book_pages(state) == [
        {"scene_id": "s0", "caption": "One.", "image_path": "j/s0-2.png", **({"other_versions": True} if magic_pencil else {})},
        {"scene_id": "s1", "caption": "Two.", "image_path": "j/s1-1.png"},
        {"scene_id": "s2", "caption": "Three.", "image_path": "j/s2-2.png"}]


def test_the_pdf_of_a_reapproved_book_prints_the_chosen_page_version(monkeypatch, held_database):
    """Magic pencil ticket 09 (AC-15, edge row "PDF export after an edit"): the export reads the
    current `jobs.pages` picture, and the delivery guard accepts it."""
    from io import BytesIO
    from PIL import Image

    conn, child, classroom, job, _ = held_database
    paths = _finished_feature_book(conn, child, classroom, job)

    def png(shade):
        buffer = BytesIO()
        Image.new("RGB", (4, 4), (shade, 0, 0)).save(buffer, "PNG")
        return buffer.getvalue()

    objects = {paths["s0-a0"]: png(10), paths["s0-a1"]: png(20), paths["s1-a0"]: png(30)}
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", MagicMock(return_value=True))
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", MagicMock(return_value=True))
    printed = MagicMock(return_value=b"%PDF-synthetic")
    monkeypatch.setattr("app.pdf_export.render_book_pdf", printed)

    def supabase():
        profile = conn.execute("select * from profiles where id=%s", (child,)).fetchone()
        row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            **profile, "classroom_id": str(profile["classroom_id"])}]
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
            **row, "classroom_id": str(row["classroom_id"]), "profile_id": str(row["profile_id"]),
            "approved_at": row["approved_at"] and row["approved_at"].isoformat(),
            "profiles": {"role": "student", "removed_at": None, "classroom_id": str(row["classroom_id"])}}]
        return client

    monkeypatch.setattr("app.db.get_supabase_client", supabase)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            client.post(f"/jobs/{job}/pages/s0/versions/open")
            assert client.post(f"/jobs/{job}/pages/s0/version",
                               json={"version_id": "s0-attempt-0", "source": paths["s0-a1"]}).status_code == 200
            conn.execute("update jobs set approved_at=now() where id=%s", (job,))
            response = client.get(f"/jobs/{job}/pdf")
            assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert printed.call_args.args[2] == [png(10), png(30)]


def _page_pencil_book(monkeypatch, held_database, *, text_safe=True, result_safe=True):
    """A finished feature book with every provider boundary of the page pencil stubbed (spec §6.2-6.3)."""
    conn, child, classroom, job, teacher = held_database
    paths = _finished_feature_book(conn, child, classroom, job)
    queue = MagicMock()
    monkeypatch.setattr("app.page_pencil.get_queue", lambda: queue)
    redacted, checks = [], {"text": text_safe, "result": result_safe}

    def redact(text):
        redacted.append(text)
        return text.replace("Ana Cruz", "<PERSON>")

    monkeypatch.setattr("providers.redact_pii", redact)
    monkeypatch.setattr("app.moderation_hold.check_text",
                        lambda text, **kw: (checks["text"], [] if checks["text"] else ["violence"], text))
    objects = {path: name.encode() for name, path in paths.items()}
    storage = MagicMock()
    storage.storage.from_.return_value.upload.side_effect = lambda path, content, options: objects.update({path: content})
    monkeypatch.setattr("worker.page_pencil.get_supabase_client", lambda: storage)
    monkeypatch.setattr("providers.download_book_image", lambda path: objects[path])
    edit = MagicMock(return_value=b"edited")
    monkeypatch.setattr("worker.page_pencil.edit_image", edit)
    monkeypatch.setattr("worker.page_pencil.get_signed_url", lambda path: f"https://private.invalid/{path}")
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", MagicMock(return_value=True))
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop",
                        MagicMock(side_effect=lambda url, **kw: checks["result"] if "pencil" in url else True))
    monkeypatch.setattr("providers.text_to_image", MagicMock(side_effect=AssertionError("a page pencil drew from scratch")))

    def run():
        from worker.page_pencil import run_page_pencil
        assert queue.enqueue.call_args.args[0] == "worker.page_pencil.run_page_pencil"
        run_page_pencil(*queue.enqueue.call_args.args[1:])

    def status():
        response = client.get(f"/jobs/{job}/pages/pencil")
        assert response.status_code == 200, response.text
        return response.json()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    client = TestClient(app)
    return SimpleNamespace(conn=conn, client=client, job=job, paths=paths, queue=queue, edit=edit, objects=objects,
                           redacted=redacted, checks=checks, run=run, status=status, child=child, teacher=teacher)


def test_a_cleared_page_pencil_edits_that_page_once_and_keeping_it_changes_the_book(monkeypatch, held_database):
    """Magic pencil ticket 10 (US-04 AC-16..AC-19, AC-20, AC-22, SH-03, SH-08, SH-10)."""
    book = _page_pencil_book(monkeypatch, held_database)
    job, client, paths, conn = book.job, book.client, book.paths, book.conn
    conn.execute("update jobs set approved_at=now() where id=%s", (job,))
    route = f"/jobs/{job}/pages/s0/pencil"
    request = {"request_id": str(uuid4()), "text": "  give Ana Cruz a red hat ", "source": paths["s0-a1"]}
    try:
        assert book.status() == {"pencils_left": 5, "disabled_reason": None, "uses": []}
        for bad in ({**request, "text": "   "}, {**request, "text": "x" * 201}):
            assert client.post(route, json=bad).status_code == 422
        stale = client.post(route, json={**request, "source": paths["s0-a0"]})
        assert stale.status_code == 409 and stale.json()["detail"] == "stale_source"
        assert book.redacted == []   # nothing was redacted, moderated or queued

        assert client.post(route, json=request).status_code == 202
        assert client.post(route, json=request).status_code == 202   # SH-08: a double submit spends once
        assert book.queue.enqueue.call_count == 1 and book.redacted == ["give Ana Cruz a red hat"]
        use_id = request["request_id"]
        assert book.status()["uses"] == [{"use_id": use_id, "scene_id": "s0", "state": "drawing",
                                          "text": "give <PERSON> a red hat", "before_path": paths["s0-a1"], "after_path": None}]

        book.run()   # the worker task, outside the graph (OD-01)
        book.run()   # a redelivery spends nothing more
        book.edit.assert_called_once()
        prompt, sources = book.edit.call_args.args
        assert prompt.startswith("give <PERSON> a red hat\n\n") and sources == [f"https://private.invalid/{paths['s0-a1']}"]
        after = f"{job}/s0-pencil-{use_id}.png"
        assert book.status() == {"pencils_left": 4, "disabled_reason": None, "uses": [
            {"use_id": use_id, "scene_id": "s0", "state": "choice", "text": "give <PERSON> a red hat",
             "before_path": paths["s0-a1"], "after_path": after}]}
        row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        assert row["image_count"] == 5 and row["status"] == "complete" and row["approved_at"] is not None
        assert client.get(f"/jobs/{job}/images/page-pencil-{use_id}").content == b"edited"
        assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a1"   # the book is unchanged until keep

        choice = f"{route}/choice"
        keep = {"use_id": use_id, "choice": "kept", "source": after}
        assert client.post(choice, json={**keep, "source": paths["s0-a1"]}).status_code == 409
        assert client.post(choice, json=keep).status_code == 200
        assert client.post(choice, json=keep).status_code == 200   # a repeat changes nothing
        row = conn.execute("select * from jobs where id=%s", (job,)).fetchone()
        assert row["pages"][0] == {"scene_id": "s0", "caption": "The dog ran.", "image_path": after, "other_versions": True}
        assert row["approved_at"] is None and row["image_count"] == 5
        assert client.get(f"/jobs/{job}/images/scene-s0").content == b"edited"
        assert book.status()["uses"][0]["state"] == "kept"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert [dict(r) for r in conn.execute("""select target_id,source,before_path,image_path,pencil_text,
      text_moderation,picture_moderation,reason,choice from job_picture_records where job_id=%s and kind='pencil'""",
                                          (job,)).fetchall()] == [{
        "target_id": "s0", "source": "page_pencil", "before_path": paths["s0-a1"], "image_path": after,
        "pencil_text": "give <PERSON> a red hat", "text_moderation": "cleared", "picture_moderation": "passed",
        "reason": None, "choice": "kept"}]
    from langgraph.checkpoint.postgres import PostgresSaver
    retained = PostgresSaver(conn).get_tuple({"configurable": {"thread_id": job}}).checkpoint["channel_values"]
    assert StoryMemory.model_validate(retained).scenes[0].final_image_ref == paths["s0-a1"]   # OD-01, AC-19


def test_a_refused_page_pencil_draws_nothing_and_spends_no_pencil(monkeypatch, held_database):
    """Magic pencil ticket 10 (SH-04 edge case): fal's checker refuses the edit. No image, no go spent,
    and the child may try different words."""
    from providers import FalFlaggedImage

    book = _page_pencil_book(monkeypatch, held_database)
    book.edit.side_effect = FalFlaggedImage()
    route, use_id = f"/jobs/{book.job}/pages/s0/pencil", str(uuid4())
    try:
        assert book.client.post(route, json={"request_id": use_id, "text": "a hat",
                                             "source": book.paths["s0-a1"]}).status_code == 202
        book.run()
        assert book.status() == {"pencils_left": 5, "disabled_reason": None, "uses": [
            {"use_id": use_id, "scene_id": "s0", "state": "refused", "text": "a hat", "before_path": book.paths["s0-a1"],
             "after_path": None}]}
        again = {"request_id": str(uuid4()), "text": "a blue hat", "source": book.paths["s0-a1"]}
        assert book.client.post(route, json=again).status_code == 202   # a refusal does not block a new request
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert book.conn.execute("select image_count from jobs where id=%s", (book.job,)).fetchone()["image_count"] == 4


@pytest.mark.parametrize("changed", ["before_the_edit", "after_the_edit"])
def test_a_book_that_changes_mid_edit_spends_only_for_an_image_it_got(monkeypatch, held_database, changed):
    """Magic pencil ticket 10 (SH-04): the book changes while the edit runs. Stopped before fal is asked,
    the use ends with nothing spent. Once fal returned, the paid image is kept and counted."""
    import providers

    book = _page_pencil_book(monkeypatch, held_database)
    bump = "update jobs set generation_epoch=generation_epoch+1 where id=%s"
    if changed == "before_the_edit":
        book.edit.side_effect = lambda *a: (book.conn.execute(bump, (book.job,)), providers.check_generation_fence(),
                                            b"edited")[-1]
    else:
        book.edit.side_effect = lambda *a: (providers.check_generation_fence(), book.conn.execute(bump, (book.job,)),
                                            providers.check_generation_fence(), b"edited")[-1]
    use_id = str(uuid4())
    try:
        assert book.client.post(f"/jobs/{book.job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a hat", "source": book.paths["s0-a1"]}).status_code == 202
        book.run()
        assert book.status()["uses"][0]["state"] == ("stale" if changed == "before_the_edit" else "choice")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    row = book.conn.execute("select image_count from jobs where id=%s", (book.job,)).fetchone()
    assert row["image_count"] == (4 if changed == "before_the_edit" else 5)


@pytest.mark.parametrize("result_safe", [True, False])
def test_a_withdrawal_during_a_page_edit_ends_the_use_without_a_hold(monkeypatch, held_database, result_safe):
    """Magic pencil review 2026-11-03 (SH-09, SH-07): a teacher withdrawal reopens the book while the edit
    runs. The paid image is counted, but the use ends as stale: no pencil result hold on a book that is not
    complete, and nothing left in progress to block the page tools once the book is finished again."""
    import providers

    book = _page_pencil_book(monkeypatch, held_database, result_safe=result_safe)

    def withdrawn(*args):
        providers.check_generation_fence()
        book.conn.execute("""update jobs set status='awaiting_teacher',generation_epoch=generation_epoch+1,
          pages='[]' where id=%s""", (book.job,))
        book.conn.execute("""insert into job_moderation_reviews(id,job_id,kind,subject_id,subject_version,subject,
          policy_version,settings_snapshot,classifier_evidence,return_node)
          values (%s,%s,'scene_image','s1','v','{}','p','{}','[]','pending')""", (uuid4(), book.job))
        return b"edited"

    book.edit.side_effect = withdrawn
    use_id = str(uuid4())
    try:
        assert book.client.post(f"/jobs/{book.job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a hat", "source": book.paths["s0-a1"]}).status_code == 202
        book.run()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    use = book.conn.execute("""select reason,picture_moderation from job_picture_records where job_id=%s
      and kind='pencil'""", (book.job,)).fetchone()
    assert (use["reason"], use["picture_moderation"]) == ("stale", None)
    assert book.conn.execute("""select count(*) from job_moderation_reviews where job_id=%s
      and kind='page_pencil_result'""", (book.job,)).fetchone()["count"] == 0
    assert book.conn.execute("select image_count from jobs where id=%s", (book.job,)).fetchone()["image_count"] == 5


def _rerun(state, scene_id, path):
    """The checkpoint after a withdrawal rerun redrew one page."""
    return state.model_copy(update={"scenes": [s.model_copy(update={
        "final_image_ref": path, "attempts": [*s.attempts, Attempt(image_ref=path, safety_eligibility="cleared")]})
        if s.scene_id == scene_id else s for s in state.scenes]})


def test_a_version_choice_survives_a_rerun_only_on_a_page_the_rerun_did_not_redraw(monkeypatch, held_database):
    """Magic pencil review 2026-11-03 (SH-09, AC-15): a teacher withdrawal rebuilds `jobs.pages` from the
    checkpoint. The child's version choice comes back on a page the rerun left alone, never on a redrawn one."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from app.moderation_hold import book_on_completion

    conn, child, classroom, job, _ = held_database
    paths = _finished_feature_book(conn, child, classroom, job)
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: path)
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", MagicMock(return_value=True))
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", MagicMock(return_value=True))
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=child)
    try:
        with TestClient(app) as client:
            assert client.post(f"/jobs/{job}/pages/s0/versions/open").status_code == 200
            assert client.post(f"/jobs/{job}/pages/s0/version",
                               json={"version_id": "s0-attempt-0", "source": paths["s0-a1"]}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    state = StoryMemory.model_validate(
        PostgresSaver(conn).get_tuple({"configurable": {"thread_id": job}}).checkpoint["channel_values"])

    pages, _ = book_on_completion(conn, job, _rerun(state, "s1", f"{job}/s1-2.png"))
    assert [p["image_path"] for p in pages] == [paths["s0-a0"], f"{job}/s1-2.png"]
    pages, _ = book_on_completion(conn, job, _rerun(state, "s0", f"{job}/s0-4.png"))
    assert [p["image_path"] for p in pages] == [f"{job}/s0-4.png", paths["s1-a0"]]


def test_a_kept_page_pencil_result_and_its_image_survive_a_rerun(monkeypatch, held_database):
    """Magic pencil review 2026-11-03 (SH-09, SH-04): a kept page pencil result comes back after a rerun,
    and its paid image stays in the book's image count, which the checkpoint never learned."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from app.moderation_hold import book_on_completion

    book = _page_pencil_book(monkeypatch, held_database)
    use_id = str(uuid4())
    after = f"{book.job}/s0-pencil-{use_id}.png"
    try:
        assert book.client.post(f"/jobs/{book.job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a hat", "source": book.paths["s0-a1"]}).status_code == 202
        book.run()
        assert book.client.post(f"/jobs/{book.job}/pages/s0/pencil/choice", json={
            "use_id": use_id, "choice": "kept", "source": after}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    state = StoryMemory.model_validate(
        PostgresSaver(book.conn).get_tuple({"configurable": {"thread_id": book.job}}).checkpoint["channel_values"])

    pages, image_count = book_on_completion(book.conn, book.job, _rerun(state, "s1", f"{book.job}/s1-2.png"))
    assert pages[0] == {"scene_id": "s0", "caption": "The dog ran.", "image_path": after, "other_versions": True}
    assert image_count == 1   # the checkpoint's 0 plus the one page pencil edit


def test_other_versions_wait_while_a_page_pencil_is_in_progress(monkeypatch, held_database):
    """Magic pencil ticket 10 (SH-07): one page change per book at a time, so a version choice cannot
    make a paid pencil result stale while it is drawing."""
    book = _page_pencil_book(monkeypatch, held_database)
    try:
        assert book.client.post(f"/jobs/{book.job}/pages/s0/pencil", json={
            "request_id": str(uuid4()), "text": "a hat", "source": book.paths["s0-a1"]}).status_code == 202
        chosen = book.client.post(f"/jobs/{book.job}/pages/s0/version",
                                  json={"version_id": "s0-attempt-0", "source": book.paths["s0-a1"]})
        assert chosen.status_code == 409 and chosen.json()["detail"] == "pencil_in_progress"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert book.conn.execute("select pages from jobs where id=%s", (book.job,)).fetchone()["pages"][0]["image_path"] \
        == book.paths["s0-a1"]


@pytest.mark.parametrize("decision", ["allow", "stop", "stop_removed"])
def test_held_page_pencil_text_keeps_the_book_readable_and_a_stop_ends_only_the_request(
        monkeypatch, held_database, decision):
    """Magic pencil ticket 10 (AC-17, AC-18, SH-05): flagged text holds with no image while the book
    stays complete and readable. Allow runs the edit; stop ends only the request, even for a removed author."""
    book = _page_pencil_book(monkeypatch, held_database, text_safe=False)
    job, client, conn, paths = book.job, book.client, book.conn, book.paths
    use_id = str(uuid4())
    try:
        assert client.post(f"/jobs/{job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a big sword", "source": paths["s0-a1"]}).status_code == 202
        book.queue.enqueue.assert_not_called()
        assert book.status()["uses"][0]["state"] == "held"
        assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a1"   # the book stays readable
        assert client.post(f"/jobs/{job}/pages/s1/versions/open").status_code == 200   # versions still work
        assert client.post(f"/jobs/{job}/pages/s1/pencil", json={   # one request per book (SH-07)
            "request_id": str(uuid4()), "text": "a hat", "source": paths["s1-a0"]}).json()["detail"] == "pencil_in_progress"

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        assert [r["job_id"] for r in client.get(f"/teacher/classrooms/{held_database[2]}/moderation-reviews").json()] == [job]
        route = f"/teacher/jobs/{job}/moderation-review"
        detail = client.get(route).json()
        assert (detail["status"], detail["kind"], detail["pencil_text"], detail["replacement_available"]) == (
            "complete", "page_pencil_text", "a big sword", False)
        assert [(p["asset_id"], p["state"]) for p in detail["pictures"]] == [("page-before", "available")]
        context = client.get(f"{route}/images/page-before", params={
            "review_id": detail["review_id"], "subject_version": detail["subject_version"]})
        assert context.content == b"s0-a1"
        command = {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                   "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                   "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"],
                   "confirmed": True}
        assert client.post(f"{route}/decision", json={**command, "action": "replace"}).status_code == 422
        from app.auth import owned_job, require_teacher
        app.dependency_overrides[owned_job] = lambda: {"id": job, "moderation_mode": "teacher_review_v1"}
        app.dependency_overrides[require_teacher] = lambda: {"id": book.teacher}
        try:   # The held request waits alone: the teacher can still approve the book (spec §4).
            assert client.post(f"/jobs/{job}/review", json={"decision": "approved"}).status_code == 200
        finally:
            app.dependency_overrides.pop(owned_job, None)
            app.dependency_overrides.pop(require_teacher, None)
        if decision == "stop_removed":
            conn.execute("update profiles set removed_at=now() where id=%s", (book.child,))
        action = "allow" if decision == "allow" else "stop"
        response = client.post(f"{route}/decision", json={**command, "action": action})
        assert response.status_code == (202 if action == "allow" else 200), response.text
        assert client.post(f"{route}/decision", json={**command, "action": action}).status_code == 200   # replay
        assert client.get(f"/teacher/classrooms/{held_database[2]}/moderation-reviews").json() == []
        assert conn.execute("select status from jobs where id=%s", (job,)).fetchone()["status"] == "complete"
        if decision == "stop_removed":
            book.queue.enqueue.assert_not_called()
            return
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.child)
        if action == "allow":
            book.run()
            book.edit.assert_called_once()
            assert book.status()["uses"][0]["state"] == "choice"
        else:
            book.queue.enqueue.assert_not_called()
            assert book.status() == {"pencils_left": 5, "disabled_reason": None, "uses": [
                {"use_id": use_id, "scene_id": "s0", "state": "stopped", "text": "a big sword", "before_path": paths["s0-a1"],
                 "after_path": None}]}
    finally:
        conn.execute("update profiles set removed_at=null where id=%s", (book.child,))
        app.dependency_overrides.pop(get_current_user, None)
    row = conn.execute("select * from job_picture_records where job_id=%s and kind='pencil'", (job,)).fetchone()
    assert (row["text_moderation"], row["reason"]) == (
        ("teacher_allowed", None) if action == "allow" else ("teacher_stopped", "text_stopped"))


@pytest.mark.parametrize("decision", ["allow", "stop"])
def test_a_flagged_page_pencil_result_holds_while_the_book_keeps_its_picture(monkeypatch, held_database, decision):
    """Magic pencil ticket 10 (AC-18, SH-05): the edit is paid, so the pencil is spent; the result waits
    for the teacher while the page keeps its picture. Allow offers keep-or-old; stop ends the request."""
    book = _page_pencil_book(monkeypatch, held_database, result_safe=False)
    job, client, paths = book.job, book.client, book.paths
    use_id = str(uuid4())
    after = f"{job}/s0-pencil-{use_id}.png"
    try:
        assert client.post(f"/jobs/{job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a hat", "source": paths["s0-a1"]}).status_code == 202
        book.run()
        assert book.status() == {"pencils_left": 4, "disabled_reason": None, "uses": [
            {"use_id": use_id, "scene_id": "s0", "state": "held", "text": "a hat", "before_path": paths["s0-a1"], "after_path": None}]}
        assert client.get(f"/jobs/{job}/images/page-pencil-{use_id}").status_code == 404
        assert client.get(f"/jobs/{job}/images/scene-s0").content == b"s0-a1"

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        route = f"/teacher/jobs/{job}/moderation-review"
        detail = client.get(route).json()
        assert (detail["kind"], detail["pencil_text"]) == ("page_pencil_result", "a hat")
        assert [(p["asset_id"], p["state"]) for p in detail["pictures"]] == [("page-before", "available"), ("held", "held")]
        reveal = {"review_id": detail["review_id"], "subject_version": detail["subject_version"]}
        assert client.post(f"{route}/reveal", json=reveal).content == b"edited"
        command = {**reveal, "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                   "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"],
                   "confirmed": True, "action": decision}
        assert client.post(f"{route}/decision", json=command).status_code == 200
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.child)
        if decision == "stop":
            assert book.status()["uses"][0]["state"] == "stopped"
            assert client.get(f"/jobs/{job}/images/page-pencil-{use_id}").status_code == 404
            return
        assert book.status()["uses"][0] == {"use_id": use_id, "scene_id": "s0", "state": "choice", "text": "a hat",
                                            "before_path": paths["s0-a1"], "after_path": after}
        assert client.get(f"/jobs/{job}/images/page-pencil-{use_id}").content == b"edited"
        assert client.post(f"/jobs/{job}/pages/s0/pencil/choice", json={
            "use_id": use_id, "choice": "kept", "source": after}).status_code == 200
        assert client.get(f"/jobs/{job}/images/scene-s0").content == b"edited"
        # A teacher-allowed result is only ever the current page, never another version (ticket 04).
        versions = client.post(f"/jobs/{job}/pages/s0/versions/open").json()["versions"]
        assert use_id not in [v["version_id"] for v in versions]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("second", ["passes", "flagged"])
def test_a_teacher_replacement_of_a_held_page_result_reruns_the_same_edit(monkeypatch, held_database, second):
    """Magic pencil ticket 11 (AC-18, AC-22): one more edit of the recorded source with the same text,
    no fresh draw, one image spent. A pass is offered for keep-or-old; a flag holds again with the
    slot used. The log row keeps the replaced picture. The held use is the book's fifth pencil, so the
    replacement must not count it twice."""
    book = _page_pencil_book(monkeypatch, held_database, result_safe=False)
    job, client, conn, paths = book.job, book.client, book.conn, book.paths
    for n in range(4):
        conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,
          before_path,pencil_text,text_moderation,picture_moderation,choice)
          values (%s,'pencil','s1',%s,%s,'page_pencil',%s,'a hat','cleared','passed','old')""",
                     (job, str(uuid4()), f"{job}/s1-pencil-{n}.png", paths["s1-a0"]))
    use_id = str(uuid4())
    first, after = f"{job}/s0-pencil-{use_id}.png", f"{job}/s0-pencil-{use_id}-replacement.png"
    route = f"/teacher/jobs/{job}/moderation-review"

    def command(detail, action):
        return {"review_id": detail["review_id"], "subject_version": detail["subject_version"],
                "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()),
                "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"],
                "confirmed": True, "action": action}

    try:
        assert client.post(f"/jobs/{job}/pages/s0/pencil", json={
            "request_id": use_id, "text": "a hat", "source": paths["s0-a1"]}).status_code == 202
        book.run()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        detail = client.get(route).json()
        assert (detail["replacement_available"], detail["replacement_disabled_reason"]) == (True, None)
        book.checks["result"] = second == "passes"
        book.edit.return_value = b"edited again"
        assert client.post(f"{route}/decision", json=command(detail, "replace")).status_code == 202
        # Its own RQ task: the first one stays in the registry after it finished.
        assert book.queue.enqueue.call_args.kwargs["job_id"] == f"page-pencil-{job}-{use_id}-replacement"
        book.run()
        assert book.edit.call_count == 2 and book.edit.call_args_list[1] == book.edit.call_args_list[0]
        assert conn.execute("select image_count from jobs where id=%s", (job,)).fetchone()["image_count"] == 6
        if second == "flagged":
            again = client.get(route).json()
            assert again["review_id"] != detail["review_id"] and again["kind"] == "page_pencil_result"
            assert (again["replacement_available"], again["replacement_disabled_reason"]) == (False, "replacement_already_used")
            refused = client.post(f"{route}/decision", json=command(again, "replace"))
            assert (refused.status_code, refused.json()["detail"]) == (422, "replacement_already_used")
            assert book.queue.enqueue.call_count == 2
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.child)
        status = book.status()
        assert status["pencils_left"] == 0
        assert status["uses"][-1]["state"] == ("choice" if second == "passes" else "held")
        if second == "passes":
            assert client.get(f"/jobs/{job}/images/page-pencil-{use_id}").content == b"edited again"
            assert client.post(f"/jobs/{job}/pages/s0/pencil/choice", json={
                "use_id": use_id, "choice": "kept", "source": after}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    row = conn.execute("""select image_path,replaced_path,picture_moderation,reason from job_picture_records
      where job_id=%s and kind='pencil' and version_id=%s""", (job, use_id)).fetchone()
    assert dict(row) == {"image_path": after, "replaced_path": first, "reason": None,
                         "picture_moderation": "passed" if second == "passes" else "flagged"}


def test_a_held_page_result_cannot_be_replaced_at_the_image_budget(monkeypatch, held_database):
    """Magic pencil ticket 11 (AC-18): the dialog and the decision give the same reason."""
    book = _page_pencil_book(monkeypatch, held_database, result_safe=False)
    job, client = book.job, book.client
    route = f"/teacher/jobs/{job}/moderation-review"
    try:
        assert client.post(f"/jobs/{job}/pages/s0/pencil", json={
            "request_id": str(uuid4()), "text": "a hat", "source": book.paths["s0-a1"]}).status_code == 202
        book.run()
        book.conn.execute("update jobs set image_count=55 where id=%s", (job,))
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.teacher)
        detail = client.get(route).json()
        assert (detail["replacement_available"], detail["replacement_disabled_reason"]) == (False, "image_budget_exhausted")
        refused = client.post(f"{route}/decision", json={
            "review_id": detail["review_id"], "subject_version": detail["subject_version"],
            "expected_epoch": detail["generation_epoch"], "request_id": str(uuid4()), "action": "replace",
            "policy_version": detail["current_policy_version"], "confirmed_criteria": detail["criteria"], "confirmed": True})
        assert (refused.status_code, refused.json()["detail"]) == (422, "image_budget_exhausted")
        assert book.queue.enqueue.call_count == 1 and book.edit.call_count == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_using_the_old_picture_keeps_a_page_pencil_result_as_another_version(monkeypatch, held_database):
    """Magic pencil ticket 10 (AC-19): "Use the old one" leaves the page and its approval alone, and the
    result is offered later as another version of that page."""
    book = _page_pencil_book(monkeypatch, held_database)
    job, client, conn, paths = book.job, book.client, book.conn, book.paths
    conn.execute("update jobs set approved_at=now() where id=%s", (job,))
    use_id = str(uuid4())
    after = f"{job}/s1-pencil-{use_id}.png"
    try:
        assert client.post(f"/jobs/{job}/pages/s1/pencil", json={
            "request_id": use_id, "text": "a hat", "source": paths["s1-a0"]}).status_code == 202
        book.run()
        assert client.post(f"/jobs/{job}/pages/s1/pencil/choice", json={
            "use_id": use_id, "choice": "old", "source": after}).status_code == 200
        row = conn.execute("select pages,approved_at from jobs where id=%s", (job,)).fetchone()
        assert row["pages"][1] == {"scene_id": "s1", "caption": "It found a stick.", "image_path": paths["s1-a0"],
                                   "other_versions": True}
        assert row["approved_at"] is not None
        assert book.status()["uses"][0]["state"] == "old"
        opened = client.post(f"/jobs/{job}/pages/s1/versions/open").json()
        assert opened == {"versions": [{"version_id": use_id, "image_path": after}], "unavailable": 0}
        assert client.get(f"/jobs/{job}/images/page-version-{use_id}").content == b"edited"
        chosen = client.post(f"/jobs/{job}/pages/s1/version", json={"version_id": use_id, "source": paths["s1-a0"]})
        assert chosen.status_code == 200
        assert client.get(f"/jobs/{job}/images/scene-s1").content == b"edited"
        assert conn.execute("select approved_at from jobs where id=%s", (job,)).fetchone()["approved_at"] is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("limit", ["no_pencils", "image_budget"])
def test_the_page_pencil_is_disabled_with_its_reason_and_versions_still_work(monkeypatch, held_database, limit):
    """Magic pencil ticket 10 (SH-04): five page pencils per book, and none once the book's image_count
    reaches IMAGE_BUDGET (55). Nothing is redacted or spent; other versions still open."""
    book = _page_pencil_book(monkeypatch, held_database)
    job, client, conn, paths = book.job, book.client, book.conn, book.paths
    if limit == "image_budget":
        conn.execute("update jobs set image_count=55 where id=%s", (job,))
    else:
        for n in range(5):
            conn.execute("""insert into job_picture_records(job_id,kind,target_id,version_id,image_path,source,
              before_path,pencil_text,text_moderation,picture_moderation,choice)
              values (%s,'pencil','s1',%s,%s,'page_pencil',%s,'a hat','cleared','passed','old')""",
                         (job, str(uuid4()), f"{job}/s1-pencil-{n}.png", paths["s1-a0"]))
    try:
        status = book.status()
        assert (status["pencils_left"], status["disabled_reason"]) == (0 if limit == "no_pencils" else 5, limit)
        refused = client.post(f"/jobs/{job}/pages/s0/pencil", json={
            "request_id": str(uuid4()), "text": "a hat", "source": paths["s0-a1"]})
        assert (refused.status_code, refused.json()["detail"]) == (409, limit)
        assert book.redacted == [] and book.queue.enqueue.call_count == 0
        assert client.post(f"/jobs/{job}/pages/s0/versions/open").status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
