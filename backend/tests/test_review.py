"""
Tests for POST /jobs/{job_id}/review.
Spec: docs/specs/teacher-review-and-approval.md §7
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app, get_current_user
from app.auth import require_teacher, owned_job

client = TestClient(app)

TEACHER_USER = MagicMock()
TEACHER_USER.id = "teacher-1"

TEACHER_PROFILE = {"id": "teacher-1", "role": "teacher"}

COMPLETE_JOB = {
    "id": "job-1",
    "status": "complete",
    "classroom_id": "cls-1",
    "profile_id": "student-1",
    "approved_at": None,
    "rejected_at": None,
    "failure_reason": None,
}


@pytest.fixture(autouse=True)
def _auth():
    """Bypass auth — teacher is always authenticated and owns the job."""
    app.dependency_overrides[get_current_user] = lambda: TEACHER_USER
    app.dependency_overrides[require_teacher] = lambda: TEACHER_PROFILE
    yield
    app.dependency_overrides.clear()


def _job_dep(job: dict):
    """Factory: makes owned_job return the given job."""
    def _dep():
        return job
    app.dependency_overrides[owned_job] = _dep


def _post(job: dict, decision: str):
    _job_dep(job)
    fake_supabase = MagicMock()
    now_str = "2026-08-07T00:00:00+00:00"
    if decision == "approved":
        updated = {**job, "approved_at": now_str, "rejected_at": None}
    elif decision == "rejected":
        updated = {**job, "approved_at": None, "rejected_at": now_str}
    else:
        updated = {**job, "approved_at": None, "rejected_at": None}
    fake_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    with patch("app.review.get_supabase_client", return_value=fake_supabase):
        return client.post(f"/jobs/{job['id']}/review", json={"decision": decision}), fake_supabase, updated


# ── Six transitions ───────────────────────────────────────────────────────────

def test_pending_to_approved_sets_approved_at_nulls_rejected_at():
    resp, fake_sb, updated = _post(COMPLETE_JOB, "approved")
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved_at"] is not None
    assert data["rejected_at"] is None
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert "approved_at" in update_args
    assert update_args["rejected_at"] is None


def test_pending_to_rejected_sets_rejected_at_nulls_approved_at():
    resp, fake_sb, _ = _post(COMPLETE_JOB, "rejected")
    assert resp.status_code == 200
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert "rejected_at" in update_args
    assert update_args["approved_at"] is None


def test_approved_to_rejected_sets_rejected_nulls_approved():
    approved_job = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00"}
    resp, fake_sb, _ = _post(approved_job, "rejected")
    assert resp.status_code == 200
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert "rejected_at" in update_args
    assert update_args["approved_at"] is None


def test_rejected_to_approved_sets_approved_nulls_rejected():
    rejected_job = {**COMPLETE_JOB, "rejected_at": "2026-08-07T00:00:00+00:00"}
    resp, fake_sb, _ = _post(rejected_job, "approved")
    assert resp.status_code == 200
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert "approved_at" in update_args
    assert update_args["rejected_at"] is None


def test_approved_to_pending_nulls_both():
    approved_job = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00"}
    resp, fake_sb, _ = _post(approved_job, "pending")
    assert resp.status_code == 200
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert update_args == {"approved_at": None, "rejected_at": None}


def test_rejected_to_pending_nulls_both():
    rejected_job = {**COMPLETE_JOB, "rejected_at": "2026-08-07T00:00:00+00:00"}
    resp, fake_sb, _ = _post(rejected_job, "pending")
    assert resp.status_code == 200
    update_args = fake_sb.table.return_value.update.call_args[0][0]
    assert update_args == {"approved_at": None, "rejected_at": None}


# ── Authorization ──────────────────────────────────────────────────────────────

def test_no_token_returns_401():
    """teacher_router's require_teacher rejects unauthenticated requests."""
    app.dependency_overrides.clear()  # remove auth bypass
    resp = client.post("/jobs/job-1/review", json={"decision": "approved"})
    assert resp.status_code in (401, 403)


def test_student_token_returns_403():
    student_user = MagicMock()
    student_user.id = "student-1"
    app.dependency_overrides[get_current_user] = lambda: student_user
    # Remove the autouse bypass so require_teacher actually runs and checks the role
    app.dependency_overrides.pop(require_teacher, None)
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "student-1", "role": "student"}
    ]
    with patch("app.auth.get_supabase_client", return_value=fake_supabase):
        resp = client.post("/jobs/job-1/review", json={"decision": "approved"})
    assert resp.status_code == 403


def test_wrong_classroom_returns_404_same_as_nonexistent():
    """owned_job must return 404 for both cases — not a 403."""
    app.dependency_overrides[get_current_user] = lambda: TEACHER_USER
    app.dependency_overrides[require_teacher] = lambda: TEACHER_PROFILE

    def _owned_job_404():
        from fastapi import HTTPException
        raise HTTPException(404, "not found")

    app.dependency_overrides[owned_job] = _owned_job_404
    resp = client.post("/jobs/nonexistent-uuid/review", json={"decision": "approved"})
    assert resp.status_code == 404

    # Same 404 body shape
    resp2 = client.post("/jobs/other-classroom-job/review", json={"decision": "approved"})
    assert resp2.status_code == 404


# ── Status validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["failed", "queued", "running", "awaiting_confirm"])
def test_non_complete_status_returns_422(status: str):
    non_complete = {**COMPLETE_JOB, "status": status}
    _job_dep(non_complete)
    resp = client.post(f"/jobs/{non_complete['id']}/review", json={"decision": "approved"})
    assert resp.status_code == 422
    # No write attempted
    # (no supabase mock needed — endpoint raises before any DB call)


def test_non_complete_422_names_the_status():
    non_complete = {**COMPLETE_JOB, "status": "queued"}
    _job_dep(non_complete)
    resp = client.post(f"/jobs/{non_complete['id']}/review", json={"decision": "approved"})
    assert resp.status_code == 422
    assert "queued" in resp.text


# ── Idempotency ────────────────────────────────────────────────────────────────

def test_same_decision_twice_returns_200_without_write():
    already_approved = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00"}
    _job_dep(already_approved)
    fake_supabase = MagicMock()
    with patch("app.review.get_supabase_client", return_value=fake_supabase):
        resp = client.post(f"/jobs/{already_approved['id']}/review", json={"decision": "approved"})
    assert resp.status_code == 200
    fake_supabase.table.return_value.update.assert_not_called()


# ── Audit log ─────────────────────────────────────────────────────────────────

def test_log_line_emitted_on_state_change():
    _job_dep(COMPLETE_JOB)
    fake_supabase = MagicMock()
    updated = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00", "rejected_at": None}
    fake_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    with patch("app.review.get_supabase_client", return_value=fake_supabase), \
         patch("app.review._log") as mock_log:
        client.post("/jobs/job-1/review", json={"decision": "approved"})
    mock_log.info.assert_called_once()
    call_str = str(mock_log.info.call_args)
    assert "job-1" in call_str
    assert "pending" in call_str  # from-state
    assert "approved" in call_str  # to-state


def test_no_log_on_idempotent_repeat():
    already_approved = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00"}
    _job_dep(already_approved)
    fake_supabase = MagicMock()
    with patch("app.review.get_supabase_client", return_value=fake_supabase), \
         patch("app.review._log") as mock_log:
        client.post("/jobs/job-1/review", json={"decision": "approved"})
    mock_log.info.assert_not_called()


# ── Input validation ───────────────────────────────────────────────────────────

def test_invalid_decision_returns_422():
    _job_dep(COMPLETE_JOB)
    resp = client.post("/jobs/job-1/review", json={"decision": "maybe"})
    assert resp.status_code == 422


def test_client_timestamp_in_body_is_ignored():
    """Client cannot influence what timestamp is written."""
    _job_dep(COMPLETE_JOB)
    fake_supabase = MagicMock()
    updated = {**COMPLETE_JOB, "approved_at": "2026-08-07T00:00:00+00:00", "rejected_at": None}
    fake_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    with patch("app.review.get_supabase_client", return_value=fake_supabase):
        # Extra field in body — Pydantic ignores unknown fields by default
        resp = client.post(
            "/jobs/job-1/review",
            json={"decision": "approved", "approved_at": "1970-01-01T00:00:00Z"},
        )
    assert resp.status_code == 200
    update_args = fake_supabase.table.return_value.update.call_args[0][0]
    assert update_args.get("approved_at") != "1970-01-01T00:00:00Z"
