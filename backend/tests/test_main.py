from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
