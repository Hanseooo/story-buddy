from unittest.mock import patch

import pytest
from pydantic import ValidationError

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
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


def test_analyze_is_a_pass_through_stub():
    """`analyze`'s real content is the story-analyzer spec, deliberately not started
    (DECISION_BACKLOG). It owns `caption_for` (D-F) but writes no state — `segment` owns
    scenes[].caption per MASTER_SPEC §2's node-I/O table."""
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field.", redacted_text="A dog runs in a field."),
    )
    assert analyze(state) == {}
