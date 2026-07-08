from unittest.mock import MagicMock, patch

from pipeline.generate_scene import generate_scene, call_nano_banana_and_store


def test_call_nano_banana_and_store_uploads_image_bytes():
    fake_part = MagicMock()
    fake_part.inline_data.data = b"fake-png-bytes"
    fake_response = MagicMock()
    fake_response.candidates = [MagicMock(content=MagicMock(parts=[fake_part]))]

    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.genai.Client") as mock_client_cls, \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        path = call_nano_banana_and_store("a friendly dog", "job-123")

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
    with patch("pipeline.generate_scene.call_nano_banana_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)
    assert result["image_path"] == "job-123/scene-1.png"
    assert result["stage"] == "generate_scene"
