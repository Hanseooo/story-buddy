from unittest.mock import patch

import pytest
from pydantic import ValidationError

from contracts.job_state import JobState  # noqa: F401  (removed in Task 5)
from pipeline.analyze import SceneCaption, analyze, caption_for


def test_scene_caption_accepts_valid_shape():
    result = SceneCaption.model_validate({"caption": "A dog runs through a sunny field."})
    assert result.caption == "A dog runs through a sunny field."


def test_scene_caption_rejects_missing_field():
    with pytest.raises(ValidationError):
        SceneCaption.model_validate({})


def test_caption_for_returns_validated_caption():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="A dog runs through a sunny field."),
    ):
        caption = caption_for("A dog runs in a field.")

    assert caption == "A dog runs through a sunny field."


def test_caption_for_passes_the_schema_to_the_provider():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="x"),
    ) as mock_structured_text:
        caption_for("A dog runs in a field.")

    prompt, schema = mock_structured_text.call_args.args
    assert "A dog runs in a field." in prompt
    assert schema is SceneCaption


def test_analyze_node_sets_caption_and_stage():
    state = {
        "job_id": "t1",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    with patch("pipeline.analyze.caption_for", return_value="stub caption"):
        result = analyze(state)
    assert result["caption"] == "stub caption"
    assert result["stage"] == "analyze"
