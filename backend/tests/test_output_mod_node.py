from unittest.mock import patch

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    Input,
    ModerationResult,
    Scene,
    StoryMemory,
)


def _state(scenes: list[Scene], characters: list[Character] | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        characters=characters or [],
        scenes=scenes,
    )


def _scene(scene_id: str = "s0", final_image_ref: str | None = "job-1/s0-1.png", prompt: str = "A dog runs.") -> Scene:
    return Scene(
        scene_id=scene_id,
        text_excerpt="A dog runs in a field.",
        final_image_ref=final_image_ref,
        prompt=prompt,
        attempts=[Attempt(image_ref="job-1/s0-1.png", prompt=prompt, passed=True)],
    )


# --- all scenes pass ---

def test_all_scenes_pass_sets_moderation_status_passed():
    """Spec §4c step 3: all pass → moderation_status = 'passed' for each scene."""
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=True), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0"), _scene("s1", final_image_ref="job-1/s1-1.png")]))

    scenes = result["scenes"]
    assert all(s.moderation_status == "passed" for s in scenes)


# --- first check fails, retry passes ---

def test_first_check_fails_soften_retry_triggers_and_passes():
    """Spec §4c step 4: fail → soften-and-retry triggered; retry passes → moderation_status = 'passed'."""
    check_calls = [False, True]  # first call fails, retry call passes
    primary_iter = iter(check_calls)

    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=primary_iter), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)) as mock_gen:
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0")]))

    assert result["scenes"][0].moderation_status == "passed"
    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"
    mock_gen.assert_called_once()


def test_retry_uses_softened_prompt():
    """Spec §4c: soften-and-retry modifies the prompt before regenerating."""
    original_prompt = "A scary monster attacks."
    calls = []

    def _gen(prompt, story_id, scene_id, attempt_n, ref_paths):
        calls.append(prompt)
        return ("job-1/s0-2.png", True)

    check_responses = iter([False, True])

    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=check_responses), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", side_effect=_gen):
        from pipeline.output_mod import output_mod
        output_mod(_state([_scene("s0", prompt=original_prompt)]))

    assert calls[0] != original_prompt, "Retry must use a softened prompt, not the original"
    assert "child" in calls[0].lower() or "safe" in calls[0].lower(), "Softened prompt must add safety qualifier"


# --- retry also fails ---

def test_retry_also_fails_sets_moderation_status_failed():
    """Spec §4c step 5: first and retry both fail → moderation_status='failed' (route_after_output_mod raises)."""
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=False), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0")]))

    assert result["scenes"][0].moderation_status == "failed"


def test_route_after_output_mod_raises_when_scene_failed():
    """route_after_output_mod raises RuntimeError('output_moderation_failed') on failed scene."""
    from pipeline.graph import route_after_output_mod
    from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, ModerationResult, Scene, StoryMemory

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="text", redacted_text="text", moderation=ModerationResult(passed=True)),
        scenes=[Scene(scene_id="s0", text_excerpt="text", moderation_status="failed")],
    )
    with pytest.raises(RuntimeError, match="output_moderation_failed"):
        route_after_output_mod(state)


# --- classifier-error posture (spec §4c step 2: "same two-classifier check as char_ref_mod") ---

def test_primary_classifier_error_degrades_to_backstop_only():
    """The 2026-08-11 posture alignment (44489cb) reached `input_gate` and `char_ref_mod` and
    stopped there, leaving this node the strictest gate in the pipeline while it screens the
    LEAST risky thing: an image we generated, from text that passed `input_gate`, from a
    reference that passed `char_ref_mod`. It is also the most expensive place to fail — prod job
    f4d0fd74 died here on scene s5 with every one of the seven scenes already drawn and paid for.

    Spec §4c step 2 already binds this node to `char_ref_mod`'s check; the code had simply stopped
    matching. Mirrors `test_primary_classifier_error_degrades_to_backstop_only` in
    `test_char_ref_mod_node.py`, deliberately, because these two must never drift again.
    """
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=Exception("OpenRouter 400")), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True) as mock_backstop:
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0")]))

    mock_backstop.assert_called_once()
    assert result["scenes"][0].moderation_status == "passed"


def test_primary_error_still_lets_the_backstop_flag():
    """The degraded path must not become a bypass. Primary erroring on both the first check and
    the softened retry, with the backstop flagging both, still ends `failed` — what degrades is
    the call count, never the gate. This is the test that makes the one above safe to keep.
    """
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=Exception("OpenRouter 400")), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=False), \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0")]))

    assert result["scenes"][0].moderation_status == "failed"


def test_primary_flag_short_circuits_the_backstop_call():
    """Spec §4a step 3: a primary flag needs no second opinion. Worth more here than in
    `char_ref_mod` — this node runs per SCENE, so a 7-scene book spent 14 classifier calls where
    the flagged ones need 1 each, on 0.2 vCPU / 512 MB against a pool that is already 429ing.
    """
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=False), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True) as mock_backstop, \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)):
        from pipeline.output_mod import output_mod
        output_mod(_state([_scene("s0")]))

    # Two checks run (initial + softened retry); neither consults the backstop after a primary flag.
    mock_backstop.assert_not_called()


def test_backstop_error_still_raises_moderation_error():
    """Unchanged by the posture alignment: the backstop is the layer with nothing behind it, so an
    error there means the image is genuinely unchecked and there is no proceed-without-a-check
    path. Only a PRIMARY error degrades."""
    with patch("pipeline.output_mod.get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=True), \
         patch("pipeline.output_mod.classify_image_backstop", side_effect=Exception("OpenRouter 503")):
        from pipeline.output_mod import output_mod
        with pytest.raises(RuntimeError, match="moderation_error"):
            output_mod(_state([_scene("s0")]))


# --- scene with no final_image_ref ---

def test_scene_with_no_final_image_ref_is_skipped():
    """Spec §4c edge case: final_image_ref is None → output_mod only runs on resolved refs."""
    with patch("pipeline.output_mod.get_signed_url") as mock_sign, \
         patch("pipeline.output_mod.classify_image_primary", return_value=True), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0", final_image_ref=None)]))

    mock_sign.assert_not_called()
    # Scene returned unchanged (no moderation_status set for unresolved refs)
    assert result["scenes"][0].moderation_status is None
