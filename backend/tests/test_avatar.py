import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app, get_current_user

client = TestClient(app)

FAKE_USER_ID = "student-abc-123"


@pytest.fixture(autouse=True)
def _bypass_auth():
    fake_user = MagicMock()
    fake_user.id = FAKE_USER_ID
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield fake_user
    app.dependency_overrides.pop(get_current_user, None)


# --- spec §8 test 1 ---
def test_valid_avatar_id_updates_caller_row():
    fake_supabase = MagicMock()
    with patch("app.avatar.get_supabase_client", return_value=fake_supabase):
        response = client.patch("/me/avatar", json={"avatar_id": "peeps-01"})
    assert response.status_code == 200
    update_args = fake_supabase.table.return_value.update.call_args[0][0]
    assert update_args["avatar_id"] == "peeps-01"
    # must scope to caller's row only
    eq_calls = fake_supabase.table.return_value.update.return_value.eq.call_args_list
    assert any(call.args == ("id", FAKE_USER_ID) for call in eq_calls)


# --- spec §8 test 2 — invalid ids → 422 ---
@pytest.mark.parametrize("bad_id", [
    "../../etc/passwd",
    "peeps-1",        # one digit
    "PEEPS-01",       # uppercase
    "javascript:alert(1)",
    "//evil.com/x",
    "",               # empty string
    "pixel-99",       # well-formed but non-existent — regex still passes, caught at render
])
def test_invalid_avatar_id_returns_422(bad_id):
    # Only ids that fail the regex get 422. pixel-99 is well-formed and passes.
    fake_supabase = MagicMock()
    with patch("app.avatar.get_supabase_client", return_value=fake_supabase):
        response = client.patch("/me/avatar", json={"avatar_id": bad_id})
    if bad_id in ("../../etc/passwd", "peeps-1", "PEEPS-01", "javascript:alert(1)", "//evil.com/x", ""):
        assert response.status_code == 422
    else:
        # pixel-99 passes the regex — backend allows it, render falls back to letter avatar
        assert response.status_code == 200


# --- spec §8 test 3 ---
def test_null_avatar_id_clears_column():
    fake_supabase = MagicMock()
    with patch("app.avatar.get_supabase_client", return_value=fake_supabase):
        response = client.patch("/me/avatar", json={"avatar_id": None})
    assert response.status_code == 200
    update_args = fake_supabase.table.return_value.update.call_args[0][0]
    assert update_args["avatar_id"] is None


# --- spec §8 test 4 ---
def test_no_auth_header_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.patch("/me/avatar", json={"avatar_id": "peeps-01"})
    assert response.status_code == 401
    # restore for other tests
    fake_user = MagicMock()
    fake_user.id = FAKE_USER_ID
    app.dependency_overrides[get_current_user] = lambda: fake_user


# --- spec §8 test 5 — write always targets auth.uid(), not any id in the body ---
def test_write_targets_caller_uid_not_body():
    """The body has no profile_id field — the route only writes auth.uid()'s row."""
    fake_supabase = MagicMock()
    with patch("app.avatar.get_supabase_client", return_value=fake_supabase):
        response = client.patch("/me/avatar", json={"avatar_id": "thumbs-01"})
    assert response.status_code == 200
    eq_calls = fake_supabase.table.return_value.update.return_value.eq.call_args_list
    # must scope by the authenticated user's ID
    assert any(call.args == ("id", FAKE_USER_ID) for call in eq_calls)
    # must NOT scope by any other user id
    other_ids = [c.args[1] for c in eq_calls if c.args[0] == "id"]
    assert all(uid == FAKE_USER_ID for uid in other_ids)
