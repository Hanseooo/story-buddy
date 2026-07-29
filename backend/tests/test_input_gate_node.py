from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.input_gate import input_gate


def test_input_gate_passes_raw_text_through_as_redacted_and_marks_moderation_passed():
    """CC-2: redacted_text is what downstream nodes consume, so the stub must populate it —
    a null here silently starves every node after it."""
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )

    result = input_gate(state)

    assert result["input"].raw_text == "A dog runs in a field."
    assert result["input"].redacted_text == "A dog runs in a field."
    assert result["input"].moderation.passed is True
