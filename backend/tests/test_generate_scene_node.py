from unittest.mock import MagicMock, patch

from pipeline.generate_scene import generate_and_store, generate_scene


def test_generate_and_store_uploads_image_bytes():
    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        path = generate_and_store("a friendly dog", "job-123")

    assert path == "job-123/scene-1.png"
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_scene_node_sets_image_path_and_stage():
    state = {
        "job_id": "job-123",
        "input_text": "x",
        "caption": "a friendly dog",
        "image_path": None,
        "stage": "analyze",
    }
    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)
    assert result["image_path"] == "job-123/scene-1.png"
    assert result["stage"] == "generate_scene"
