from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import providers
from app.auth import get_current_user
from app.main import app


@pytest.fixture
def pdf_request(monkeypatch):
    # Existing worker persistence payload and a captured synthetic scene image.
    row = {
        "id": "job-1", "profile_id": "student-1", "classroom_id": "class-1",
        "status": "complete", "approved_at": "2026-10-21T00:00:00Z", "rejected_at": None,
        "title": "A dog runs in a field.",
        "pages": [{"scene_id": "s0", "caption": "stub caption", "image_path": "job-1/scene-1.png"}],
        "profiles": {"role": "student", "removed_at": None, "classroom_id": "class-1"},
    }
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.side_effect = lambda: SimpleNamespace(data=[row])
    viewer = {"id": "student-1", "role": "student", "removed_at": None, "classroom_id": "class-1",
              "password_reset_version": 0, "password_completed_version": 0}
    profiles = MagicMock()
    profiles.select.return_value = profiles
    profiles.eq.return_value = profiles
    profiles.execute.side_effect = lambda: SimpleNamespace(data=[viewer])
    database = MagicMock()
    database.table.side_effect = lambda table: profiles if table == "profiles" else query
    monkeypatch.setattr("app.db.get_supabase_client", lambda: database)
    image = Path("tests/fixtures/qwen35-resize-scene.png").read_bytes()
    download = MagicMock(return_value=image)
    monkeypatch.setattr(providers, "download_book_image", download, raising=False)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="student-1")
    yield TestClient(app), row, query, download, viewer, profiles
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("viewer_id", ["student-1", "classmate-1"])
def test_approved_classroom_student_downloads_complete_pdf_without_writes(pdf_request, viewer_id):
    client, row, query, download, viewer, profiles = pdf_request
    viewer["id"] = viewer_id
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=viewer_id)
    content = app.openapi()["paths"]["/jobs/{job_id}/pdf"]["get"]["responses"]["200"]["content"]
    assert content == {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}
    response = client.get("/jobs/job-1/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"] == 'attachment; filename="storybuddy-A-dog-runs-in-a-field.pdf"'
    assert response.content.startswith(b"%PDF-")
    download.assert_called_once_with("job-1/scene-1.png")
    assert query.execute.call_count == 2  # Approval checked again after rendering.
    assert profiles.execute.call_count == 2  # Membership is checked again too.
    profiles.eq.assert_any_call("id", viewer_id)
    query.eq.assert_any_call("classroom_id", "class-1")
    selected = query.select.call_args.args[0]
    assert "input_text" not in selected
    query.insert.assert_not_called()
    query.update.assert_not_called()
    query.delete.assert_not_called()


@pytest.mark.parametrize("failure, expected", [
    ("missing", 404), ("other_class", 404), ("removed", 404), ("teacher", 404),
    ("researcher", 404), ("viewer_removed", 404), ("viewer_missing", 404),
    ("viewer_no_class", 404), ("author_moved", 404), ("author_not_student", 404),
    ("peer_pending", 404), ("peer_rejected", 404), ("peer_incomplete", 404),
    ("pending", 409), ("rejected", 409), ("incomplete", 409), ("empty", 409),
    ("image_failure", 503), ("invalid_image", 503), ("foreign_path", 503),
    ("withdrawn", 409), ("peer_withdrawn", 404), ("membership_withdrawn", 404),
    ("author_removed_during_export", 404), ("unauthenticated", 401),
])
def test_pdf_fails_closed_without_partial_download(pdf_request, failure, expected):
    client, row, query, download, viewer, profiles = pdf_request
    if failure == "missing":
        query.execute.side_effect = lambda: SimpleNamespace(data=[])
    elif failure == "other_class":
        viewer["classroom_id"] = "other-class"
    elif failure.startswith("peer_"):
        row["profile_id"] = "another-student"
        if failure == "peer_pending":
            row["approved_at"] = None
        elif failure == "peer_rejected":
            row["rejected_at"] = "2026-10-21T01:00:00Z"
        elif failure == "peer_incomplete":
            row["status"] = "running"
    elif failure == "removed":
        row["profiles"]["removed_at"] = "2026-10-21T01:00:00Z"
    elif failure == "teacher":
        viewer["role"] = "teacher"
    elif failure == "researcher":
        viewer["role"] = "researcher"
    elif failure == "viewer_removed":
        viewer["removed_at"] = "2026-10-21T01:00:00Z"
    elif failure == "viewer_missing":
        profiles.execute.side_effect = lambda: SimpleNamespace(data=[])
    elif failure == "viewer_no_class":
        viewer["classroom_id"] = None
    elif failure == "author_moved":
        row["profiles"]["classroom_id"] = "other-class"
    elif failure == "author_not_student":
        row["profiles"]["role"] = "researcher"
    elif failure == "pending":
        row["approved_at"] = None
    elif failure == "rejected":
        row["rejected_at"] = "2026-10-21T01:00:00Z"
    elif failure == "incomplete":
        row["status"] = "running"
    elif failure == "empty":
        row["pages"] = []
    elif failure == "image_failure":
        download.side_effect = RuntimeError("private storage details")
    elif failure == "invalid_image":
        download.return_value = b"not an image"
    elif failure == "foreign_path":
        row["pages"][0]["image_path"] = "other-book/scene-1.png"
    if failure in {"withdrawn", "peer_withdrawn", "membership_withdrawn", "author_removed_during_export"}:
        def withdraw(_path):
            if failure == "membership_withdrawn":
                viewer["classroom_id"] = "other-class"
            elif failure == "author_removed_during_export":
                row["profiles"]["removed_at"] = "2026-10-21T01:00:00Z"
            else:
                row["approved_at"] = None
            return Path("tests/fixtures/qwen35-resize-scene.png").read_bytes()
        download.side_effect = withdraw
    elif failure == "unauthenticated":
        app.dependency_overrides.pop(get_current_user)

    response = client.get("/jobs/job-1/pdf")
    assert response.status_code == expected
    assert response.headers.get("content-type") != "application/pdf"
    assert "private storage details" not in response.text
    if failure not in {"image_failure", "invalid_image", "withdrawn", "peer_withdrawn",
                       "membership_withdrawn", "author_removed_during_export"}:
        download.assert_not_called()
