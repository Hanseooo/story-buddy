import pytest
from unittest.mock import MagicMock, patch

from pipeline.analyze import analyze, call_gemini_for_caption


def test_call_gemini_for_caption_validates_structured_response():
    fake_response = MagicMock()
    fake_response.text = '{"caption": "A dog runs through a sunny field."}'

    with patch("pipeline.analyze.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        caption = call_gemini_for_caption("A dog runs in a field.")

    assert caption == "A dog runs through a sunny field."


def test_call_gemini_for_caption_rejects_malformed_response():
    fake_response = MagicMock()
    fake_response.text = '{"wrong_field": "oops"}'

    with patch("pipeline.analyze.genai.Client") as mock_client_cls:
        mock_client_cls.return_value.models.generate_content.return_value = fake_response
        with pytest.raises(Exception):
            call_gemini_for_caption("A dog runs in a field.")


def test_analyze_node_sets_caption_and_stage():
    state = {
        "job_id": "t1",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    with patch("pipeline.analyze.call_gemini_for_caption", return_value="stub caption"):
        result = analyze(state)
    assert result["caption"] == "stub caption"
    assert result["stage"] == "analyze"
