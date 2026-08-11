from unittest.mock import patch

import pytest

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from tests.state_invariants import assert_no_fields_dropped


def _state(text: str = "A dog runs in a field.") -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=text),
    )


def _populated_state(text: str = "A dog runs in a field.") -> StoryMemory:
    """What `worker/run_job.py:147` actually hands the graph — `word_count` and `truncated`
    are already set by the time `input_gate` runs. `_state` above omits them, which is why
    every existing test in this file passed while production reported `word_count=0`."""
    state = _state(text)
    return state.model_copy(
        update={"input": state.input.model_copy(update={"word_count": 79, "truncated": True})}
    )


# --- happy path ---

def test_both_classifiers_pass_sets_moderation_passed_and_redacted_text():
    """Spec §4a: both pass → moderation.passed = True; redacted_text always populated (CC-2)."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])) as mock_primary, \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(True, [])) as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs in a field."):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is True
    assert result["input"].redacted_text == "A dog runs in a field."
    mock_primary.assert_called_once()
    mock_backstop.assert_called_once()


# --- primary flags ---

def test_primary_flags_sets_passed_false_without_calling_backstop():
    """Spec §4a step 3: primary flags → moderation.passed=False; no backstop call."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.classify_text_backstop") as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        result = input_gate(_state("graphic violence"))

    assert result["input"].moderation.passed is False
    mock_backstop.assert_not_called()


def test_primary_flags_redacted_text_is_still_set():
    """CC-2 invariant: redacted_text populated even on fail (teacher sees the redacted version)."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.classify_text_backstop"), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].redacted_text == "[REDACTED]"
    assert result["input"].moderation.passed is False


# --- backstop flags ---

def test_primary_passes_backstop_flags_sets_passed_false():
    """Spec §4a step 4: primary passes, backstop flags → moderation.passed=False."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(False, ["S2"])), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is False


# --- primary OOM/error ---

def test_primary_error_falls_back_to_backstop_only():
    """Spec §4a edge case: primary OOM/load error → backstop-only path fires; error is logged, not raised."""
    with patch("pipeline.input_gate.classify_text_primary", side_effect=RuntimeError("OOM")), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(True, [])) as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs."):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is True
    mock_backstop.assert_called_once()


def test_primary_error_backstop_flags_sets_passed_false():
    """Spec §4a: primary errors AND backstop flags → moderation.passed=False."""
    with patch("pipeline.input_gate.classify_text_primary", side_effect=RuntimeError("OOM")), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is False


# --- backstop error ---

def test_backstop_error_sets_moderation_error_in_categories():
    """Spec §4a edge case: backstop OpenRouter error → passed=False, categories=['moderation_error']."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])), \
         patch("pipeline.input_gate.classify_text_backstop", side_effect=Exception("OpenRouter 500")), \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs."):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is False
    assert "moderation_error" in result["input"].moderation.categories


# --- state-write invariant (every return path) ---

@pytest.mark.parametrize(
    "primary, backstop, label",
    [
        ({"return_value": (True, [])},          {"return_value": (True, [])},          "both pass"),
        ({"return_value": (False, ["S1"])},     {"return_value": (True, [])},          "primary flags"),
        ({"return_value": (True, [])},          {"return_value": (False, ["S2"])},     "backstop flags"),
        ({"return_value": (True, [])},          {"side_effect": Exception("500")},     "backstop errors"),
    ],
)
def test_input_gate_carries_the_whole_input_model_through_every_return_path(primary, backstop, label):
    """Regression, prod job 4cb31620 (2026-08-11): a 79-word story reported `word_count=0`.

    `input` has no reducer, so `input_gate`'s return REPLACES the model. All four paths built a
    fresh `Input(...)`, so `word_count: int = 0` and `truncated: bool = False` reasserted
    themselves on every job that has ever run. Nothing downstream reads either field today,
    which is exactly why it went unnoticed for the entire life of the pipeline.

    `input_gate` was the only node of the thirteen that rebuilt a sub-model instead of using
    `model_copy` — 23 `model_copy` calls elsewhere got it right. Parametrized over every path
    because the bug was in all four, and a fix applied to three of them is the same bug.
    """
    with patch("pipeline.input_gate.classify_text_primary", **primary), \
         patch("pipeline.input_gate.classify_text_backstop", **backstop), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        state = _populated_state()
        result = input_gate(state)

    assert_no_fields_dropped(state, result)
    assert result["input"].word_count == 79, label
    assert result["input"].truncated is True, label
    # The node's actual job still happens — the carry-forward must not shadow the write.
    assert result["input"].redacted_text == "[REDACTED]", label
    assert result["input"].moderation is not None, label


def test_assert_no_fields_dropped_actually_catches_a_dropped_field():
    """The guard is only worth having if it fails. Rebuilding `Input` from scratch is the
    precise shape of the production bug, so that is what the guard is tested against."""
    from contracts.story_memory import ModerationResult

    state = _populated_state()
    naive = {"input": Input(raw_text=state.input.raw_text, redacted_text="[REDACTED]",
                            moderation=ModerationResult(passed=True))}

    with pytest.raises(AssertionError, match="word_count"):
        assert_no_fields_dropped(state, naive)


# --- moderation_router ---

def _moderation_router_state(passed: bool, categories: list[str] | None = None, flagged_char: bool = False):
    from contracts.story_memory import (
        CURRENT_SCHEMA_VERSION, Character, CharacterDescription, Input, ModerationResult, StoryMemory
    )
    chars = []
    if flagged_char:
        chars = [Character(
            char_id="c0", name="Dog",
            description=CharacterDescription(species="dog"),
            ref_moderation_status="flagged",
        )]
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(
            raw_text="text",
            redacted_text="text",
            moderation=ModerationResult(passed=passed, categories=categories or []),
        ),
        characters=chars,
    )


def test_moderation_router_passes_through_to_analyze_when_input_passed():
    """moderation_router returns 'analyze' when moderation passed and no flagged chars."""
    from pipeline.graph import moderation_router
    state = _moderation_router_state(passed=True)
    assert moderation_router(state) == "analyze"


def test_moderation_router_raises_content_flagged_when_input_failed():
    """moderation_router raises RuntimeError('content_flagged') when input.moderation.passed=False."""
    from pipeline.graph import moderation_router
    state = _moderation_router_state(passed=False, categories=["S1"])
    with pytest.raises(RuntimeError, match="content_flagged"):
        moderation_router(state)


def test_moderation_router_raises_moderation_error_when_category_set():
    """moderation_router raises RuntimeError('moderation_error') for backstop-error category."""
    from pipeline.graph import moderation_router
    state = _moderation_router_state(passed=False, categories=["moderation_error"])
    with pytest.raises(RuntimeError, match="moderation_error"):
        moderation_router(state)


def test_moderation_router_raises_ref_flagged_when_char_flagged():
    """moderation_router raises RuntimeError('ref_flagged') when a char has ref_moderation_status='flagged'."""
    from pipeline.graph import moderation_router
    state = _moderation_router_state(passed=True, flagged_char=True)
    with pytest.raises(RuntimeError, match="ref_flagged"):
        moderation_router(state)
