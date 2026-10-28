"""Teacher note HTTP seam, with only Supabase mocked (§14.7)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


JOB = "00000000-0000-0000-0000-000000000001"
NOTE = {
    "id": "00000000-0000-0000-0000-000000000002", "job_id": JOB,
    "author_id": "teacher-1", "body": "Lovely story!", "scene_id": None,
    "anchor": None, "seen_at": None, "created_at": "2026-10-29T00:00:00+00:00",
    "updated_at": "2026-10-29T00:00:00+00:00",
}


@pytest.fixture
def boundary():
    sb = MagicMock()
    sb.auth.get_user.return_value.user = SimpleNamespace(id="teacher-1")
    sb.rows = {
        "profiles": [{"id": "teacher-1", "role": "teacher"}],
        "jobs": [{"id": JOB, "status": "complete", "classroom_id": "class-1"}],
        "classrooms": [{"id": "class-1", "owner_id": "teacher-1", "review_notes_enabled": False}],
    }
    def table(name):
        query = MagicMock()
        filters = {}
        memberships = {}
        changes = {}
        query.select.return_value = query
        def eq(key, value):
            filters[key] = value
            return query
        query.eq.side_effect = eq
        query.is_.side_effect = lambda key, value: eq(key, None if value == "null" else value)
        def in_(key, values):
            memberships[key] = values
            return query
        query.in_.side_effect = in_
        def update(values):
            changes.update(values)
            return query
        query.update.side_effect = update
        def execute():
            rows = [row for row in sb.rows[name] if all(row.get(key) == value for key, value in filters.items())
                    and all(row.get(key) in values for key, values in memberships.items())]
            for row in rows:
                row.update(changes)
            return SimpleNamespace(data=rows)
        query.execute.side_effect = execute
        return query
    sb.table.side_effect = table
    sb.rpc.return_value.execute.return_value.data = {"status": 200, "note": NOTE}
    with patch("app.auth.get_supabase_client", return_value=sb), \
         patch("app.review_notes.get_supabase_client", return_value=sb):
        yield TestClient(app), sb


def test_switch_saves_and_disabling_preserves_stored_note(boundary):
    client, sb = boundary
    headers = {"Authorization": "Bearer synthetic"}
    for enabled in (True, False):
        response = client.patch("/classrooms/class-1/review-notes", json={"enabled": enabled}, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"enabled": enabled}
        assert sb.rows["classrooms"][0]["review_notes_enabled"] is enabled
    assert client.get(f"/teacher/jobs/{JOB}/note", headers=headers).json() == NOTE
    assert set(call.args[0] for call in sb.table.call_args_list) <= {"profiles", "classrooms", "jobs"}
    assert all(call.args[1]["p_operation"] == "GET" for call in sb.rpc.call_args_list)


def test_switch_rejects_nonowners_students_and_invalid_values(boundary):
    client, sb = boundary
    url = "/classrooms/class-1/review-notes"
    headers = {"Authorization": "Bearer synthetic"}
    assert client.patch(url, json={"enabled": True}).status_code == 401
    sb.rows["profiles"] = [{"id": "teacher-1", "role": "student", "classroom_id": "class-1",
                            "password_reset_version": 0, "password_completed_version": 0}]
    assert client.patch(url, json={"enabled": True}, headers=headers).status_code == 403
    sb.rows["profiles"] = [{"id": "teacher-1", "role": "teacher"}]
    assert client.patch(url, json={"enabled": "false"}, headers=headers).status_code == 422
    sb.rows["classrooms"][0]["owner_id"] = "another-teacher"
    other = client.patch(url, json={"enabled": True}, headers=headers)
    missing = client.patch("/classrooms/missing/review-notes", json={"enabled": True}, headers=headers)
    assert other.status_code == missing.status_code == 404
    assert other.content == missing.content == b'{"detail":"classroom not found"}'
    sb.rpc.assert_not_called()


def test_teacher_can_send_and_read_note(boundary):
    client, sb = boundary
    headers = {"Authorization": "Bearer synthetic"}
    response = client.put(f"/teacher/jobs/{JOB}/note", json={"body": "Lovely story!"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == NOTE
    assert sb.rpc.call_args.args == ("teacher_review_note", {
        "p_job_id": JOB, "p_teacher_id": "teacher-1", "p_operation": "PUT", "p_body": "Lovely story!",
    })
    assert client.get(f"/teacher/jobs/{JOB}/note", headers=headers).json() == NOTE


@pytest.mark.parametrize("body", ["", " \t\n", "x" * 501])
def test_invalid_note_never_reaches_storage(boundary, body):
    client, sb = boundary
    response = client.put(f"/teacher/jobs/{JOB}/note", json={"body": body},
                          headers={"Authorization": "Bearer synthetic"})
    assert response.status_code == 422
    sb.rpc.assert_not_called()


def test_exactly_500_characters_and_server_author(boundary):
    client, sb = boundary
    response = client.put(f"/teacher/jobs/{JOB}/note", json={"body": "x" * 500, "author_id": "attacker"},
                          headers={"Authorization": "Bearer synthetic"})
    assert response.status_code == 200
    assert sb.rpc.call_args.args[1]["p_teacher_id"] == "teacher-1"
    assert sb.rpc.call_args.args[1]["p_body"] == "x" * 500


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_auth_and_ownership_guards_before_storage(boundary, method):
    client, sb = boundary
    url = f"/teacher/jobs/{JOB}/note"
    def request(headers=None):
        return client.request(method, url, json={"body": "Hello"}, headers=headers)
    assert request().status_code == 401
    headers = {"Authorization": "Bearer synthetic"}
    for role in ("student", "researcher"):
        sb.rows["profiles"] = [{"id": "teacher-1", "role": role, "classroom_id": "class-1",
                                "password_reset_version": 0, "password_completed_version": 0}]
        assert request(headers).status_code == 403
    sb.rows["profiles"] = [{"id": "teacher-1", "role": "teacher"}]
    sb.rows["classrooms"] = []
    other_class = request(headers)
    sb.rows["jobs"] = []
    missing = request(headers)
    assert other_class.status_code == missing.status_code == 404
    assert other_class.content == missing.content == b'{"detail":"not found"}'
    sb.rpc.assert_not_called()


@pytest.mark.parametrize("method,status,detail", [
    ("PUT", 409, "notes_disabled"), ("DELETE", 409, "notes_disabled"),
    ("PUT", 422, "book_not_complete"), ("GET", 404, "not found"), ("DELETE", 404, "not found"),
])
def test_database_guards_return_http_errors(boundary, method, status, detail):
    client, sb = boundary
    sb.rpc.return_value.execute.return_value.data = {"status": status, "detail": detail}
    response = client.request(method, f"/teacher/jobs/{JOB}/note", json={"body": "Hello"},
                              headers={"Authorization": "Bearer synthetic"})
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert response.headers["cache-control"] == "no-store"


def test_delete_and_browser_preflight(boundary):
    from app.config import settings
    client, sb = boundary
    sb.rpc.return_value.execute.return_value.data = {"status": 200, "note": None}
    response = client.delete(f"/teacher/jobs/{JOB}/note", headers={"Authorization": "Bearer synthetic"})
    assert response.status_code == 204
    assert response.content == b""
    for method in ("PUT", "DELETE"):
        response = client.options(f"/teacher/jobs/{JOB}/note", headers={
            "Origin": settings.frontend_origin, "Access-Control-Request-Method": method,
        })
        assert response.status_code == 200


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_invalid_job_uuid_is_rejected_before_job_query(boundary, method):
    client, sb = boundary
    response = client.request(method, "/teacher/jobs/not-a-uuid/note", json={"body": "Hello"},
                              headers={"Authorization": "Bearer synthetic"})
    assert response.status_code == 422
    assert "jobs" not in [call.args[0] for call in sb.table.call_args_list]
    sb.rpc.assert_not_called()


def student_notes(sb):
    sb.rows["profiles"] = [{"id": "teacher-1", "role": "student", "classroom_id": "class-1",
                            "removed_at": None, "password_reset_version": 0, "password_completed_version": 0}]
    sb.rows["jobs"][0]["profile_id"] = "teacher-1"
    sb.rows["classrooms"][0]["review_notes_enabled"] = True
    sb.rows["job_review_notes"] = [dict(NOTE)]


def test_child_reads_current_note_and_marks_only_opened_version_seen(boundary):
    client, sb = boundary
    student_notes(sb)
    headers = {"Authorization": "Bearer synthetic"}
    expected = [{"job_id": JOB, "body": "Lovely story!", "seen": False,
                 "updated_at": "2026-10-29T00:00:00+00:00"}]
    response = client.get("/me/notes", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == expected
    assert sb.rows["job_review_notes"][0]["seen_at"] is None
    response = client.post(f"/jobs/{JOB}/note/seen", json={"updated_at": NOTE["updated_at"]}, headers=headers)
    assert response.status_code == 204
    assert client.get("/me/notes", headers=headers).json()[0]["seen"] is True
    sb.rows["job_review_notes"][0].update(body="A new note", seen_at=None, updated_at="2026-10-29T01:00:00+00:00")
    assert client.post(f"/jobs/{JOB}/note/seen", json={"updated_at": NOTE["updated_at"]}, headers=headers).status_code == 404
    assert client.get("/me/notes", headers=headers).json()[0] == {
        "job_id": JOB, "body": "A new note", "seen": False, "updated_at": "2026-10-29T01:00:00+00:00",
    }
    sb.rows["classrooms"][0]["review_notes_enabled"] = False
    assert client.get("/me/notes", headers=headers).json() == []
    assert client.post(f"/jobs/{JOB}/note/seen", json={"updated_at": NOTE["updated_at"]}, headers=headers).status_code == 404
    sb.rows["classrooms"][0]["review_notes_enabled"] = True
    sb.rows["job_review_notes"] = []
    assert client.get("/me/notes", headers=headers).json() == []


@pytest.mark.parametrize("denial", ["peer", "missing", "teacher", "researcher", "removed", "classroom", "deleting", "signed_out"])
def test_child_note_access_never_leaks_to_other_viewers(boundary, denial):
    client, sb = boundary
    student_notes(sb)
    headers = {"Authorization": "Bearer synthetic"}
    if denial == "peer":
        sb.rows["jobs"][0]["profile_id"] = "another-child"
    elif denial == "missing":
        sb.rows["jobs"] = []
    elif denial in ("teacher", "researcher"):
        sb.rows["profiles"][0]["role"] = denial
    elif denial == "removed":
        sb.rows["profiles"][0]["removed_at"] = "2026-10-29T01:00:00Z"
    elif denial == "classroom":
        sb.rows["jobs"][0]["classroom_id"] = "another-class"
    elif denial == "deleting":
        sb.rows["jobs"][0]["status"] = "deleting"
    else:
        headers = {}
    response = client.get("/me/notes", headers=headers)
    expected = 401 if denial == "signed_out" else 403 if denial == "removed" else 404 if denial in ("teacher", "researcher") else 200
    assert response.status_code == expected
    if expected == 200:
        assert response.json() == []
    else:
        assert "Lovely story!" not in response.text
    response = client.post(f"/jobs/{JOB}/note/seen", json={"updated_at": NOTE["updated_at"]}, headers=headers)
    assert response.status_code == (401 if denial == "signed_out" else 403 if denial == "removed" else 404)
    if response.status_code == 404:
        assert response.json() == {"detail": "not found"}
    assert sb.rows["job_review_notes"][0]["seen_at"] is None
