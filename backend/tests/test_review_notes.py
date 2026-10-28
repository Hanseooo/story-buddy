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
        "classrooms": [{"id": "class-1"}],
    }
    def table(name):
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value.data = sb.rows[name]
        return query
    sb.table.side_effect = table
    sb.rpc.return_value.execute.return_value.data = {"status": 200, "note": NOTE}
    with patch("app.auth.get_supabase_client", return_value=sb), \
         patch("app.review_notes.get_supabase_client", return_value=sb):
        yield TestClient(app), sb


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
