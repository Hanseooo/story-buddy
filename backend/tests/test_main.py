import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app, get_current_user

client = TestClient(app)

FAKE_USER_ID = "user-student-123"


@pytest.fixture(autouse=True)
def _bypass_auth():
    """Inject a fake student user for all tests. Auth-boundary tests pop this override."""
    fake_user = MagicMock()
    fake_user.id = FAKE_USER_ID
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield fake_user
    app.dependency_overrides.pop(get_current_user, None)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_storybook_inserts_job_and_enqueues():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()

    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id

    fake_supabase.table.assert_called_with("jobs")
    insert_call_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_call_args["input_text"] == "A dog runs in a field."
    assert insert_call_args["id"] == job_id

    fake_queue.enqueue.assert_called_once_with("worker.run_job.run_storybook_job", job_id)


# --- style-presets spec: API validation (tests 3–5) ---

def test_create_storybook_stores_style_preset_id_when_provided():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()

    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field.", "style_preset_id": "comic"})

    assert response.status_code == 200
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["style_preset_id"] == "comic"


def test_create_storybook_rejects_unknown_style_preset_with_422():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field.", "style_preset_id": "watercolour"})
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_rejects_empty_string_style_preset_with_422():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field.", "style_preset_id": ""})
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_omitting_style_preset_stores_null():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()

    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})

    assert response.status_code == 200
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["style_preset_id"] is None


# --- input-gate-hardening spec: length guard (§4d) ---

def test_create_storybook_rejects_under_minimum_words_with_422():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "too short"})
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()
    fake_queue.enqueue.assert_not_called()


def test_create_storybook_rejects_empty_text_with_422():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": ""})
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_clamps_over_max_words_and_marks_truncated():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    long_text = " ".join(f"w{i}" for i in range(900))
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": long_text})

    assert response.status_code == 200
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["truncated"] is True
    assert len(insert_args["input_text"].split()) == 800


def test_create_storybook_normal_body_is_not_truncated():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})

    assert response.status_code == 200
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["truncated"] is False
    assert insert_args["input_text"] == "A dog runs in a field."


# --- kid-flow-pause-lifecycle spec: POST /jobs/{id}/confirm (§4.9) ---

REVEAL_ROW = {
    "status": "awaiting_confirm",
    "profile_id": FAKE_USER_ID,
    "reveal": {
        "characters": [{"char_id": "c0", "name": "Kiko", "image_path": "job-1/ref-c0-2.png", "chips": ["orange sock"]}],
        "taps_left": 2,
    },
}


def _select_returns(fake_supabase, rows: list[dict]) -> None:
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows


def _cas_returns(fake_supabase, rows: list[dict]) -> None:
    fake_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows


def test_confirm_returns_404_for_an_unknown_job():
    fake_supabase = MagicMock()
    _select_returns(fake_supabase, [])
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/jobs/unknown-job/confirm", json={"action": "confirm"})
    assert response.status_code == 404


def test_confirm_rejects_unknown_char_id_with_422_and_does_not_change_status():
    fake_supabase = MagicMock()
    _select_returns(fake_supabase, [REVEAL_ROW])
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post(
            "/jobs/job-1/confirm", json={"action": "try_again", "char_id": "nope", "attribute": "orange sock"}
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.update.assert_not_called()


def test_confirm_rejects_an_attribute_offered_for_a_different_character_with_422():
    fake_supabase = MagicMock()
    row = {
        "status": "awaiting_confirm",
        "profile_id": FAKE_USER_ID,
        "reveal": {
            "characters": [
                {"char_id": "c0", "name": "Kiko", "image_path": "p1", "chips": ["orange sock"]},
                {"char_id": "c1", "name": "Milo", "image_path": "p2", "chips": ["blue hat"]},
            ],
            "taps_left": 3,
        },
    }
    _select_returns(fake_supabase, [row])
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post(
            "/jobs/job-1/confirm", json={"action": "try_again", "char_id": "c1", "attribute": "orange sock"}
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.update.assert_not_called()


def test_confirm_rejects_missing_action_with_422():
    fake_supabase = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/jobs/job-1/confirm", json={})
    assert response.status_code == 422
    fake_supabase.table.assert_not_called()


def test_confirm_rejects_unknown_action_with_422():
    fake_supabase = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/jobs/job-1/confirm", json={"action": "give_up"})
    assert response.status_code == 422
    fake_supabase.table.assert_not_called()


def test_confirm_valid_try_again_enqueues_once_and_returns_queued():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(fake_supabase, [REVEAL_ROW])
    _cas_returns(fake_supabase, [{"id": "job-1"}])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post(
            "/jobs/job-1/confirm", json={"action": "try_again", "char_id": "c0", "attribute": "orange sock"}
        )

    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    fake_queue.enqueue.assert_called_once_with(
        "worker.run_job.resume_storybook_job", "job-1", {"action": "try_again", "char_id": "c0", "attribute": "orange sock"}
    )


def test_confirm_valid_confirm_enqueues_once_and_returns_queued():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(fake_supabase, [REVEAL_ROW])
    _cas_returns(fake_supabase, [{"id": "job-1"}])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})

    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    fake_queue.enqueue.assert_called_once_with("worker.run_job.resume_storybook_job", "job-1", {"action": "confirm", "char_id": None, "attribute": None})


def test_confirm_second_identical_request_enqueues_nothing_and_returns_200():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(fake_supabase, [REVEAL_ROW])
    _cas_returns(fake_supabase, [])   # zero rows affected — someone already resumed it
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})

    assert response.status_code == 200
    assert response.json() == {"status": "awaiting_confirm"}
    fake_queue.enqueue.assert_not_called()


def test_confirm_against_a_complete_job_returns_200_and_enqueues_nothing():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(fake_supabase, [{"status": "complete", "profile_id": FAKE_USER_ID, "reveal": {"characters": [], "taps_left": 3}}])
    _cas_returns(fake_supabase, [])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})

    assert response.status_code == 200
    assert response.json() == {"status": "complete"}
    fake_queue.enqueue.assert_not_called()


def test_confirm_rolls_back_the_cas_and_returns_503_when_enqueue_raises():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    fake_queue.enqueue.side_effect = RuntimeError("redis down")
    _select_returns(fake_supabase, [REVEAL_ROW])
    _cas_returns(fake_supabase, [{"id": "job-1"}])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})

    assert response.status_code == 503
    rollback_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert rollback_update == {"status": "awaiting_confirm"}


# --- S2 auth-boundary tests (spec §8 tests 1–6) ---

def test_create_storybook_no_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/storybooks", json={"text": "A dog runs in a field."})
    assert response.status_code == 401


def test_create_storybook_bad_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    fake_supabase = MagicMock()
    fake_supabase.auth.get_user.return_value = MagicMock(user=None)
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field."},
            headers={"Authorization": "Bearer bad-token"},
        )
    assert response.status_code == 401


def test_create_storybook_teacher_token_returns_403():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"classroom_id": None}
    ]
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})
    assert response.status_code == 403


def test_confirm_no_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 401


def test_confirm_wrong_owner_returns_403():
    fake_supabase = MagicMock()
    # profile_id in the job row does NOT match FAKE_USER_ID
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "status": "awaiting_confirm",
            "profile_id": "other-user-id",
            "reveal": {"characters": [], "taps_left": 2},
        }
    ]
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 403


def test_confirm_matching_owner_awaiting_confirm_returns_200():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(
        fake_supabase,
        [{"status": "awaiting_confirm", "profile_id": FAKE_USER_ID, "reveal": {"characters": [], "taps_left": 2}}],
    )
    _cas_returns(fake_supabase, [{"id": "job-1"}])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), patch(
        "app.main.get_queue", return_value=fake_queue
    ):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 200
    assert response.json() == {"status": "queued"}


# ── Tests 10–15: teacher authorization dependencies (spec §6 tests 10–15) ──────
# These import from app.auth; they will fail (ImportError) until auth.py exists.

from app.auth import get_current_user as _auth_get_current_user, require_teacher, owned_classroom, teacher_router  # noqa: E402


def _make_teacher_app():
    """Mount one test route on teacher_router so we can hit it."""
    from fastapi import Depends, FastAPI
    from app.auth import teacher_router
    ta = FastAPI()

    @teacher_router.get("/classrooms/{classroom_id}/ping")
    def ping(classroom=Depends(owned_classroom)):
        return {"ok": True, "classroom_id": str(classroom["id"])}

    ta.include_router(teacher_router, prefix="/teacher")
    return ta


def test_student_token_on_teacher_router_returns_403():
    """spec §6 test 10."""
    fake_supabase = MagicMock()
    fake_user = MagicMock()
    fake_user.id = "student-uid"
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "student-uid", "role": "student"}
    ]

    ta = _make_teacher_app()
    ta.dependency_overrides[_auth_get_current_user] = lambda: fake_user
    tc = TestClient(ta)
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        r = tc.get("/teacher/classrooms/some-id/ping")
    assert r.status_code == 403


def test_valid_token_no_profiles_row_returns_403():
    """spec §6 test 11."""
    fake_supabase = MagicMock()
    fake_user = MagicMock()
    fake_user.id = "ghost-uid"
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    ta = _make_teacher_app()
    ta.dependency_overrides[_auth_get_current_user] = lambda: fake_user
    tc = TestClient(ta)
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        r = tc.get("/teacher/classrooms/some-id/ping")
    assert r.status_code == 403


def test_no_authorization_header_returns_401():
    """spec §6 test 12."""
    ta = _make_teacher_app()
    tc = TestClient(ta)
    r = tc.get("/teacher/classrooms/some-id/ping")
    assert r.status_code == 401


def test_teacher_own_classroom_returns_row():
    """spec §6 test 13."""
    fake_supabase = MagicMock()
    teacher_id = "teacher-uid"
    classroom_id = "cls-123"
    fake_user = MagicMock()
    fake_user.id = teacher_id

    def _select(table_name):
        m = MagicMock()
        if table_name == "profiles":
            m.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": teacher_id, "role": "teacher"}
            ]
        elif table_name == "classrooms":
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": classroom_id, "owner_id": teacher_id, "code": "abc", "name": "My Class"}
            ]
        return m

    fake_supabase.table.side_effect = _select
    ta = _make_teacher_app()
    ta.dependency_overrides[_auth_get_current_user] = lambda: fake_user
    tc = TestClient(ta)
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        r = tc.get(f"/teacher/classrooms/{classroom_id}/ping")
    assert r.status_code == 200


def test_teacher_another_teachers_classroom_returns_404():
    """spec §6 test 14: ownership mismatch is 404, not 403."""
    fake_supabase = MagicMock()
    teacher_id = "teacher-uid"
    fake_user = MagicMock()
    fake_user.id = teacher_id

    def _select(table_name):
        m = MagicMock()
        if table_name == "profiles":
            m.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": teacher_id, "role": "teacher"}
            ]
        elif table_name == "classrooms":
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        return m

    fake_supabase.table.side_effect = _select
    ta = _make_teacher_app()
    ta.dependency_overrides[_auth_get_current_user] = lambda: fake_user
    tc = TestClient(ta)
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        r = tc.get("/teacher/classrooms/other-cls/ping")
    assert r.status_code == 404


def test_teacher_nonexistent_classroom_returns_404():
    """spec §6 test 15: nonexistent classroom is indistinguishable from test 14."""
    fake_supabase = MagicMock()
    teacher_id = "teacher-uid"
    fake_user = MagicMock()
    fake_user.id = teacher_id

    def _select(table_name):
        m = MagicMock()
        if table_name == "profiles":
            m.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": teacher_id, "role": "teacher"}
            ]
        elif table_name == "classrooms":
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        return m

    fake_supabase.table.side_effect = _select
    ta = _make_teacher_app()
    ta.dependency_overrides[_auth_get_current_user] = lambda: fake_user
    tc = TestClient(ta)
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        r = tc.get("/teacher/classrooms/ghost-cls/ping")
    assert r.status_code == 404
