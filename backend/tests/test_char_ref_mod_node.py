from unittest.mock import patch

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    ModerationResult,
    StoryMemory,
)


def _state(characters: list[Character]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        characters=characters,
    )


def _char(char_id: str, ref_path: str | None = "job-1/c0.png") -> Character:
    return Character(
        char_id=char_id,
        name="Dog",
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref_path,
    )


# --- all pass ---

def test_all_characters_pass_both_classifiers_sets_status_passed():
    """Spec §4b step 5: all chars pass → ref_moderation_status = 'passed' for each."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0"), _char("c1")]))

    chars = result["characters"]
    assert all(c.ref_moderation_status == "passed" for c in chars)


# --- primary flags ---

def test_falconsai_flags_sets_ref_moderation_status_flagged():
    """Spec §4b step 4: primary flags → ref_moderation_status='flagged' (router raises content_flagged)."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=False), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    assert result["characters"][0].ref_moderation_status == "flagged"


# --- backstop flags ---

def test_gemma_flags_sets_ref_moderation_status_flagged():
    """Spec §4b step 4: backstop flags → ref_moderation_status='flagged' (even if primary passed)."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    assert result["characters"][0].ref_moderation_status == "flagged"


# --- backstop error ---

def test_gemma_error_raises_moderation_error():
    """Spec §4b edge case: classifier error → RuntimeError('moderation_error') — no proceed-without-one-check path."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", side_effect=Exception("OpenRouter 503")):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(RuntimeError, match="moderation_error"):
            char_ref_mod(_state([_char("c0")]))


# --- no canonical_ref_image ---

def test_character_with_no_canonical_ref_image_is_skipped_as_passed():
    """Spec §4b: char with no canonical_ref_image has nothing to moderate — mark passed."""
    with patch("pipeline.char_ref_mod.get_signed_url") as mock_sign, \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0", ref_path=None)]))

    mock_sign.assert_not_called()
    assert result["characters"][0].ref_moderation_status == "passed"


# --- image download retry ---

def test_signed_url_failure_retries_once_then_raises():
    """Spec §4b edge case: image download fails → one retry per ADR-025, then hard fail."""
    with patch("pipeline.char_ref_mod.get_signed_url", side_effect=Exception("Storage error")):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(RuntimeError, match="char_ref_mod"):
            char_ref_mod(_state([_char("c0")]))
