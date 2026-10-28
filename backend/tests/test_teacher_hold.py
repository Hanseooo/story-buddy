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
