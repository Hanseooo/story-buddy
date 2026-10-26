from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

REAL_CLIENT = httpx.Client


@pytest.fixture
def account(monkeypatch):
    user = SimpleNamespace(id="student-1", email="child@class.students.storybuddy.invalid")
    profile = {"id": user.id, "role": "student", "classroom_id": "class-1", "removed_at": None,
               "display_nickname": "Child", "password_reset_version": 1, "password_completed_version": 0,
               "introduction_dismissed_at": None}
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.side_effect = lambda: SimpleNamespace(data=[profile.copy()])
    database = MagicMock()
    database.table.return_value = query
    database.rpc.return_value.execute.return_value.data = "server-operation"
    monkeypatch.setattr("app.db.get_supabase_client", lambda: database)
    monkeypatch.setattr("app.auth.get_supabase_client", lambda: database)
    monkeypatch.setattr("app.avatar.get_supabase_client", lambda: database)
    app.dependency_overrides[get_current_user] = lambda: user
    calls = []

    def transport(request):
        import json
        payload = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, payload))
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"user": {"id": user.id}, "access_token": "proof-session"})
        if request.method == "PUT":
            profile["password_completed_version"] = 1
            return httpx.Response(200, json={"id": user.id})
        return httpx.Response(204)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(transport)))
    try:
        yield TestClient(app), profile, database, calls
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_password_change_checks_current_password_and_commits_server_operation(account):
    client, profile, database, calls = account
    response = client.post("/me/password", headers={"Authorization": "Bearer caller-session"}, json={
        "current_password": "teacher-word-12", "password": "        ", "confirmation": "        ",
    })
    assert response.status_code == 200
    assert response.json()["next_path"] == "/s/student-1/introduction"
    database.rpc.assert_called_with("begin_password_operation", {"p_user_id": "student-1", "p_kind": "change"})
    assert calls[0] == ("POST", "/auth/v1/token", {
        "email": "child@class.students.storybuddy.invalid", "password": "teacher-word-12",
    })
    assert calls[1] == ("PUT", "/auth/v1/user", {
        "current_password": "teacher-word-12", "password": "        ",
        "data": {"storybuddy_password_operation": "server-operation"},
    })


@pytest.mark.parametrize("auth_failure", [
    httpx.Response(502, text="Bad Gateway"),
    httpx.Response(500, json={"code": "unexpected_failure"}),
])
def test_auth_server_failure_after_proof_reports_unknown_outcome(account, monkeypatch, auth_failure):
    client, profile, database, calls = account

    def transport(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"user": {"id": "student-1"}, "access_token": "proof-session"})
        return auth_failure if request.method == "PUT" else httpx.Response(204)

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(transport)))
    response = client.post("/me/password", headers={"Authorization": "Bearer caller-session"}, json={
        "current_password": "teacher-word-12", "password": "new words", "confirmation": "new words",
    })
    assert response.status_code == 503
    assert response.json() == {"detail": "password_outcome_unknown"}


def test_invalid_password_does_not_reserve_or_call_auth_and_never_echoes_it(account):
    client, profile, database, calls = account
    for password in ["😀😀", "😀" * 19]:
        response = client.post("/me/password", json={
            "current_password": "teacher-word-12", "password": password, "confirmation": password,
        })
        assert response.status_code == 422
        assert password not in response.text
    database.rpc.assert_not_called()
    assert calls == []

    # Exercise the actual authentication dependency, mocking only Auth/database.
    app.dependency_overrides.pop(get_current_user, None)
    database.auth.get_user.return_value.user = SimpleNamespace(id="student-1")
    response = client.patch("/me/avatar", headers={"Authorization": "Bearer caller-session"},
                            json={"avatar_id": "peeps-01"})
    assert response.status_code == 403
    assert response.json() == {"detail": "password_change_required"}
