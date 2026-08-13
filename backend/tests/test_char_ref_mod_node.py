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


def test_early_character_flagged_does_not_drop_later_characters():
    """A flag on a non-last character must not truncate `characters[]` on the checkpointed state —
    `characters` has no reducer, so the return value replaces the whole list."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", side_effect=[False, True]), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0"), _char("c1")]))

    chars = result["characters"]
    assert [c.char_id for c in chars] == ["c0", "c1"]
    assert chars[0].ref_moderation_status == "flagged"
    assert chars[1].ref_moderation_status == "passed"


# --- backstop error ---

def test_primary_classifier_error_degrades_to_backstop_only():
    """Posture aligned with `input_gate` on 2026-08-11. Both nodes cite ADR-025 and used to read
    it in opposite directions: `input_gate` degraded to backstop-only on a primary error, this
    node failed the whole book.

    The asymmetry was backwards on the risk. `input_gate` screens UNTRUSTED child-supplied text;
    this node screens an image WE generated from text that already passed `input_gate`. The node
    downstream of the safer input has no business being the stricter of the two — and on a free
    tier where OpenRouter blips are routine it turned a transient into a dead book, after the
    reference draws were already paid for.

    Two checks remain the invariant: what degrades is the count, never the gate. The backstop
    still runs and can still flag.
    """
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", side_effect=Exception("OpenRouter 503")), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True) as mock_backstop:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    mock_backstop.assert_called_once()
    assert result["characters"][0].ref_moderation_status == "passed"


def test_primary_error_still_lets_the_backstop_flag():
    """The degraded path must not become a bypass — a primary error plus an unsafe image is
    still `flagged`. This is the test that makes the one above safe to keep."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", side_effect=Exception("OpenRouter 503")), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    assert result["characters"][0].ref_moderation_status == "flagged"


def test_primary_flag_short_circuits_the_backstop_call():
    """`input_gate` spec §4a step 3: a primary flag needs no second opinion — the verdict cannot
    change. This node called both unconditionally, so a 2-character book spent 4 classifier calls
    where 2 could decide it. Pure waste on 0.2 vCPU / 512 MB.
    """
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=False), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True) as mock_backstop:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    mock_backstop.assert_not_called()
    assert result["characters"][0].ref_moderation_status == "flagged"


def test_gemma_error_raises_moderation_error():
    """Spec §4b edge case: a BACKSTOP error → RuntimeError('moderation_error'). Unchanged by the
    2026-08-11 posture alignment: the backstop is the layer with no fallback behind it, so an
    error there means the image is genuinely unchecked and there is no proceed-without-a-check
    path. A PRIMARY error is different and is covered above."""
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


# --- spec reference-moderation-retry §4.1 ---

def test_a_backstop_flag_clears_the_canonical_ref_image():
    """§6 test 1. Clearing is the mechanism: char_bible.py:377 re-mints exactly the characters
    whose canonical_ref_image is None. The status stays "flagged" so the router can read it."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    char = result["characters"][0]
    assert char.canonical_ref_image is None
    assert char.ref_moderation_status == "flagged"


def test_a_primary_flag_clears_the_ref_without_consulting_the_backstop():
    """§6 test 2. The short-circuit at char_ref_mod.py:42-46 is unchanged; the retry is
    downstream of BOTH classifiers, so the clearing has to happen on this branch too."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=False), \
         patch("pipeline.char_ref_mod.classify_image_backstop") as backstop:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0")]))

    assert result["characters"][0].canonical_ref_image is None
    assert result["characters"][0].ref_moderation_status == "flagged"
    backstop.assert_not_called()


def test_a_character_that_already_passed_is_returned_untouched_and_costs_nothing():
    """§6 test 3. The second pass must not re-bill two classifier calls to re-derive an answer
    nothing invalidated. Safe ONLY because both mint paths clear the status when they overwrite
    the image (`moderation-stack.md:144-148`) — see the char_bible reset."""
    passed = _char("c0").model_copy(update={"ref_moderation_status": "passed"})
    with patch("pipeline.char_ref_mod.get_signed_url") as signer, \
         patch("pipeline.char_ref_mod.classify_image_primary") as primary, \
         patch("pipeline.char_ref_mod.classify_image_backstop") as backstop:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([passed]))

    assert result["characters"][0] == passed        # byte-identical
    signer.assert_not_called()
    primary.assert_not_called()
    backstop.assert_not_called()


def test_only_the_flagged_character_is_cleared_and_the_passed_one_is_not_rescreened():
    """§6 test 3 + §4.6 row 3, on one mixed roster: c0 flags, c1 already passed. Exactly one
    character is screened, and exactly one is cleared."""
    c0 = _char("c0")
    c1 = _char("c1").model_copy(update={"ref_moderation_status": "passed"})
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False) as backstop:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([c0, c1]))

    assert backstop.call_count == 1
    assert result["characters"][0].canonical_ref_image is None
    assert result["characters"][1] == c1


def test_a_species_only_character_with_no_reference_is_still_marked_passed():
    """§6 test 4 / §4.6 row 1: the char_ref_mod.py:12-14 path is UNCHANGED. It must not be
    swallowed by the new already-passed guard, and it must never enter the loop."""
    with patch("pipeline.char_ref_mod.get_signed_url") as signer, \
         patch("pipeline.char_ref_mod.classify_image_primary") as primary:
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0", ref_path=None)]))

    assert result["characters"][0].ref_moderation_status == "passed"
    signer.assert_not_called()
    primary.assert_not_called()


def test_char_ref_mod_bumps_no_counter_and_returns_no_cost():
    """§6 test 5 / §4.1: the node reports, the router decides, char_bible does the accounting.
    A partial return carrying `cost` here would double-count against char_bible's bump."""
    with patch("pipeline.char_ref_mod.get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False):
        from pipeline.char_ref_mod import char_ref_mod
        state = _state([_char("c0")])
        result = char_ref_mod(state)

    assert set(result) == {"characters"}
    assert state.cost.ref_mod_retry_count == 0

