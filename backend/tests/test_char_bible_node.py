from unittest.mock import MagicMock, patch

import pytest

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, CharacterDescription, Cost, Input, RefVerdict, StoryMemory, Style
from pipeline.char_bible import best_draw, char_bible, mint_reference, reference_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"
DRAWS = [b"draw-1-bytes", b"draw-2-bytes", b"draw-3-bytes"]


def _verdict(matches: bool, attributes: list[str] | None = None) -> RefVerdict:
    return RefVerdict(
        differences_observed="the scarf is blue, not red",
        matches_description=matches,
        attributes_present=attributes or [],
    )


# --- best_draw (pure) ---

def test_best_draw_ranks_on_attributes_present_length():
    """Spec §4: best-of ranks on len(attributes_present) — lengths 1, 3, 2 → index 1."""
    verdicts = [
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ]
    assert best_draw(verdicts) == 1


def test_best_draw_breaks_ties_toward_the_earliest_draw():
    """Spec §4: ties → earliest draw. Lengths 2, 2, 2 → index 0."""
    verdicts = [_verdict(False, ["a", "b"]) for _ in range(3)]
    assert best_draw(verdicts) == 0


def test_best_draw_returns_zero_when_every_verdict_is_empty():
    """Spec §4 edge case: all attributes_present empty → 0. Deterministic, never arbitrary."""
    verdicts = [_verdict(False), _verdict(False), _verdict(False)]
    assert best_draw(verdicts) == 0


# --- reference_prompt (pure) ---

def test_reference_prompt_contains_every_populated_description_axis():
    description = CharacterDescription(
        species="dog",
        colours=["orange"],
        body_features=["three eyes"],
        clothing=["a red scarf"],
        notes="always smiling",
    )
    prompt = reference_prompt(description, "the orange dog", FRAG)
    for axis in ["dog", "orange", "three eyes", "a red scarf", "always smiling"]:
        assert axis in prompt


def test_reference_prompt_floors_to_the_character_name_on_an_empty_description():
    """Spec §4: CharacterDescription is all-Optional, so a fully empty one is contract-legal
    (a resumed pre-story-analyzer checkpoint could carry one). The prompt floors to the name."""
    prompt = reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert "Character: the orange dog\n" in prompt


def test_reference_prompt_always_contains_the_style_fragment():
    """ADR-022: style rides the reference, so the fragment is never optional in this prompt."""
    assert FRAG in reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert FRAG in reference_prompt(CharacterDescription(species="dog"), "the orange dog", FRAG)


# --- mint_reference (effect boundary) ---

def _mint(judge_side_effect, images=None):
    """Runs mint_reference with all three effects patched.

    Returns (result, text_to_image_mock, judge_mock, fake_supabase).
    """
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=list(images or DRAWS)) as t2i, \
         patch("pipeline.char_bible.judge", side_effect=judge_side_effect) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = mint_reference(
            CharacterDescription(species="dog", colours=["orange"]),
            "the orange dog",
            FRAG,
            "story-1",
            "c0",
        )
    return result, t2i, judge_mock, fake_supabase


def _uploaded_bytes(fake_supabase) -> bytes:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[1]


def _uploaded_path(fake_supabase) -> str:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[0]


def test_mint_reference_accepts_a_passing_first_draw():
    """Spec §6: one text_to_image call, one judge call, verdict returned unchanged."""
    passing = _verdict(True, ["dog", "orange"])
    (path, verdict, draws), t2i, judge_mock, supabase = _mint([passing])

    assert t2i.call_count == 1
    assert judge_mock.call_count == 1
    assert verdict is passing
    assert draws == 1
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"
    assert path == "story-1/ref-c0-1.png"


def test_mint_reference_rerolls_until_a_draw_passes():
    """Spec §6: fail → fail → pass yields 3 draws, and the THIRD image's bytes are uploaded."""
    (_, verdict, draws), t2i, _, supabase = _mint(
        [_verdict(False), _verdict(False), _verdict(True, ["dog"])]
    )

    assert t2i.call_count == 3
    assert draws == 3
    assert verdict.matches_description is True
    assert _uploaded_bytes(supabase) == b"draw-3-bytes"


def test_mint_reference_best_of_uploads_the_draw_with_most_attributes_present():
    """Spec §6 exhaustion best-of: attributes_present lengths 1, 3, 2 → the SECOND draw wins.
    Guards the ranking key."""
    (_, verdict, draws), _, _, supabase = _mint([
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-2-bytes"
    assert draws == 3
    # A FAILING verdict is persisted — loud, never a placeholder, never a failed job (ADR-010).
    assert verdict.matches_description is False


def test_mint_reference_best_of_ties_go_to_the_earliest_draw():
    """Spec §6: lengths 2, 2, 2 → the FIRST draw's bytes are uploaded."""
    (_, _, _), _, _, supabase = _mint([
        _verdict(False, ["a", "b"]),
        _verdict(False, ["c", "d"]),
        _verdict(False, ["e", "f"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_never_draws_more_than_three_times():
    """Spec §6 cap (ADR-028): never more than 3 text_to_image calls, however many verdicts fail."""
    (_, _, draws), t2i, _, _ = _mint([_verdict(False) for _ in range(3)])

    assert t2i.call_count == 3
    assert draws == 3


def test_mint_reference_degrades_to_a_null_verdict_when_the_judge_fails():
    """Spec §4 two-policies table: the artifact exists and is paid for, only the CHECK failed.
    Accept the draw, return None, and STOP re-rolling — exactly one text_to_image call."""
    (path, verdict, draws), t2i, _, supabase = _mint(RuntimeError("openrouter 500"))

    assert verdict is None
    assert draws == 1
    assert t2i.call_count == 1
    assert path == "story-1/ref-c0-1.png"
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_propagates_a_text_to_image_failure():
    """Spec §6 (guards ADR-025 Decision 1): no artifact exists, so there is nothing to ship.
    The exception propagates and the job fails. No node-level retry."""
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=RuntimeError("fal 503")), \
         patch("pipeline.char_bible.judge") as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        with pytest.raises(RuntimeError, match="fal 503"):
            mint_reference(CharacterDescription(species="dog"), "the dog", FRAG, "story-1", "c0")

    judge_mock.assert_not_called()
    fake_supabase.storage.from_.return_value.upload.assert_not_called()


def test_mint_reference_uploads_to_the_exact_reference_path():
    """Spec §6 upload target: `{story_id}/ref-{char_id}.png`, in the storybook-images bucket."""
    (path, _, _), _, _, supabase = _mint([_verdict(True)])

    assert path == "story-1/ref-c0-1.png"
    assert _uploaded_path(supabase) == "story-1/ref-c0-1.png"
    supabase.storage.from_.assert_called_with("storybook-images")


def test_mint_reference_shows_the_judge_a_data_uri_never_a_url():
    """Spec §6 (guards invariant 5 and the CC-4 posture): the judge sees base64, never a signed
    URL, and what is PERSISTED is the path, never the data URI."""
    (path, _, _), _, judge_mock, _ = _mint([_verdict(True)])

    image_urls = judge_mock.call_args.args[1]
    assert len(image_urls) == 1
    assert image_urls[0].startswith("data:image/png;base64,")
    assert not image_urls[0].startswith("http")
    assert not path.startswith("data:")
    assert not path.startswith("http")


def test_mint_reference_reports_a_draw_count_equal_to_the_provider_calls():
    """Spec §6: the count the helper reports equals the number of text_to_image calls.
    Invariant 4 rides on this — the node cannot compute it, the loop is in here."""
    for side_effect, expected in [
        ([_verdict(True)], 1),
        ([_verdict(False), _verdict(True)], 2),
        ([_verdict(False), _verdict(False), _verdict(False)], 3),
    ]:
        (_, _, draws), t2i, _, _ = _mint(side_effect)
        assert draws == t2i.call_count == expected


def test_mint_reference_passes_no_seed_to_the_image_model():
    """Spec §4 "No seed, by necessity": a fixed seed makes all three draws identical and the
    re-roll a no-op. CC-7 is unsatisfied here as a consequence of the mechanism (§5)."""
    _, t2i, _, _ = _mint([_verdict(False), _verdict(False), _verdict(False)])

    for call in t2i.call_args_list:
        assert call.kwargs.get("seed") is None
        assert len(call.args) == 1   # prompt only — no positional seed


# --- char_bible node (mint_reference mocked) ---

def _char(char_id: str, name: str, ref: str | None = None) -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref,
    )


def _state(characters: list[Character], style: Style | None = None, cost: Cost | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="story-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="The dog ran.", redacted_text="The dog ran."),
        characters=characters,
        style=style or Style(),
        cost=cost or Cost(),
    )


def _minted(path: str = "story-1/ref.png", draws: int = 1):
    """A mint_reference stand-in: same 3-tuple shape, one accepted draw."""
    return (path, _verdict(True, ["dog"]), draws)


def test_char_bible_references_at_most_two_characters():
    """Invariant 1 (ADR-004: max 2 canonical refs, v1): a 3-character roster calls the helper
    exactly twice, for c0 and c1."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(state)

    assert mint.call_count == 2
    assert [call.args[4] for call in mint.call_args_list] == ["c0", "c1"]


def test_char_bible_returns_the_complete_character_list():
    """Invariant 2 — THE REDUCER TRAP. `characters` has no reducer, so a partial return
    REPLACES the list. Returning only the two modified entries deletes c2 silently."""
    c2 = _char("c2", "the bird")
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), c2])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert len(result["characters"]) == 3
    assert result["characters"][2] == c2          # byte-identical to input
    assert result["characters"][2].canonical_ref_image is None
    assert [c.char_id for c in result["characters"]] == ["c0", "c1", "c2"]


def test_char_bible_writes_the_path_and_verdict_onto_the_referenced_characters():
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted("story-1/ref-c0-1.png")):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict.matches_description is True


def test_char_bible_persists_a_failing_verdict_rather_than_failing_the_job():
    """ADR-010/ADR-028: a failed acceptance loop is loud, never a failed job, never a placeholder."""
    failing = ("story-1/ref-c0-1.png", _verdict(False, ["dog"]), 3)
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=failing):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict.matches_description is False


def test_char_bible_accepts_a_null_verdict_from_a_degraded_judge():
    """Spec §4: ref_verdict=None is honest and distinguishable from a FAILED verdict."""
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=("story-1/ref-c0-1.png", None, 1)):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict is None


def test_char_bible_bumps_image_count_by_the_draws_made_and_preserves_the_rest_of_cost():
    """Invariant 4: cost has no reducer, so it is COPIED and bumped — never rebuilt from zero,
    which would erase any field a future node has written."""
    state = _state(
        [_char("c0", "the dog"), _char("c1", "the cat")],
        cost=Cost(image_count=4, regen_count=2, usd_estimate=1.25),
    )

    with patch("pipeline.char_bible.mint_reference", side_effect=[_minted(draws=3), _minted(draws=2)]):
        result = char_bible(state)

    assert result["cost"].image_count == 4 + 3 + 2
    assert result["cost"].regen_count == 2
    assert result["cost"].usd_estimate == 1.25


def test_char_bible_on_an_empty_roster_returns_without_calling_the_helper():
    """Spec §4 edge case: zero characters → no refs, no cost change, and the node does NOT raise.
    Scenes generate unreferenced — a book with drifting art beats no book (ADR-010)."""
    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(_state([]))

    mint.assert_not_called()
    assert result == {}


def test_char_bible_on_a_single_character_mints_exactly_one_reference():
    """Spec §4: the cap is a ceiling, not a quota."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(_state([_char("c0", "the dog")]))

    assert mint.call_count == 1
    assert len(result["characters"]) == 1


def test_char_bible_skips_a_character_that_already_has_a_reference():
    """Invariant 6 / CC-10: idempotent re-entry — zero draws, zero cost for an existing ref."""
    state = _state([_char("c0", "the dog", ref="story-1/ref-c0-1.png"), _char("c1", "the cat")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted(draws=1)) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"


def test_char_bible_makes_zero_helper_calls_when_both_references_already_exist():
    """Invariant 6: full re-entry after success costs nothing."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0-1.png"),
        _char("c1", "the cat", ref="story-1/ref-c1-1.png"),
    ])

    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(state)

    mint.assert_not_called()
    assert result == {}


def test_char_bible_caps_before_it_filters():
    """Spec §4's trap. A 3-character roster where c0 is already referenced calls the helper
    ONCE, for c1 only — never for c2. Filtering before capping slides the 2-slot window onto c2
    and mints a THIRD canonical reference against ADR-004."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0-1.png"),
        _char("c1", "the cat"),
        _char("c2", "the bird"),
    ])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][2].canonical_ref_image is None


def test_char_bible_leaves_ref_moderation_status_untouched():
    """Contract slice: ref_moderation_status is owned by the Phase-2 char-ref moderation node.
    CC-1 is NOT closed by this node completing (spec §5)."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    for character in result["characters"]:
        assert character.ref_moderation_status is None


def test_char_bible_partial_returns_exactly_characters_and_cost_without_mutating_state():
    """ADR-024: partial-return, never mutate."""
    state = _state([_char("c0", "the dog")])
    before = state.model_dump()

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert set(result) == {"characters", "cost"}
    assert state.model_dump() == before


def test_char_bible_falls_back_to_the_default_style_fragment():
    """Spec §4: nothing writes `style` today, so the fallback is the NORMAL Phase-1 path."""
    from app.config import settings

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment=None)))

    assert mint.call_args.args[2] == settings.default_style_fragment


def test_char_bible_prefers_the_state_style_fragment_when_set():
    """ADR-022: the style is frozen before the reference is drawn, and state wins over the default."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment="flat gouache storybook")))

    assert mint.call_args.args[2] == "flat gouache storybook"


# --- targeted mode (ADR-029, spec §4.5-4.7) ---

def _targeted_state(char_id: str = "c0", attribute: str = "orange sock", ref_retry_count: int = 0) -> StoryMemory:
    from contracts.story_memory import ReferenceRetry

    c0 = _char("c0", "the dog", ref="story-1/ref-c0-1.png")
    c0.ref_verdict = _verdict(True, ["dog"])
    c0.ref_moderation_status = "passed"
    return _state(
        [c0, _char("c1", "the cat", ref="story-1/ref-c1-1.png")],
        cost=Cost(image_count=2, ref_retry_count=ref_retry_count),
    ).model_copy(update={"reference_retry": ReferenceRetry(char_id=char_id, attribute=attribute)})


def test_char_bible_targeted_mode_makes_exactly_one_draw_and_one_judge_call():
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"redraw-bytes") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True, ["dog"])) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    assert t2i.call_count == 1
    assert judge_mock.call_count == 1
    assert result["characters"][0].char_id == "c0"


def test_char_bible_targeted_mode_restates_the_tapped_attribute_in_the_prompt():
    state = _targeted_state(attribute="orange sock")
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(state)

    assert "orange sock" in t2i.call_args.args[0]


def test_char_bible_targeted_mode_only_mutates_the_flagged_character():
    state = _targeted_state()
    c1_before = next(c for c in state.characters if c.char_id == "c1")
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    c1_after = next(c for c in result["characters"] if c.char_id == "c1")
    assert c1_after == c1_before


def test_char_bible_targeted_mode_bumps_image_count_and_ref_retry_count_and_clears_retry():
    state = _targeted_state(ref_retry_count=1)
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    assert result["cost"].image_count == 3
    assert result["cost"].ref_retry_count == 2
    assert result["reference_retry"] is None


def test_char_bible_targeted_mode_overwrites_unconditionally():
    """ADR-029 §2: best-of over old-versus-new would risk showing the child the same picture
    back, the worst answer to "try again". The overwrite never compares to the prior verdict."""
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(False, ["dog"])), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    c0 = next(c for c in result["characters"] if c.char_id == "c0")
    assert c0.ref_verdict.matches_description is False   # overwritten even though it "got worse"


def test_char_bible_targeted_mode_uploads_to_a_new_path_and_clears_moderation_status():
    """Invariant 6 (spec §4.6-4.7): first tap (ref_retry_count=0) must write ref-c0-2.png, not
    ref-c0-1.png (the initial mint's path). Uses the realistic first-tap state so the Storage-path
    collision the spec warns against is directly covered."""
    state = _targeted_state()   # ref_retry_count=0: the first tap
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = char_bible(state)

    c0 = next(c for c in result["characters"] if c.char_id == "c0")
    assert c0.canonical_ref_image == "story-1/ref-c0-2.png"
    assert c0.ref_moderation_status is None
    assert _uploaded_path(fake_supabase) == "story-1/ref-c0-2.png"


def test_char_bible_ignores_invariant_six_skip_when_reference_retry_targets_an_existing_ref():
    """The targeted overwrite applies even though c0 already has canonical_ref_image set —
    invariant 6's skip is for the first-pass path only (spec §3)."""
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(state)

    assert t2i.call_count == 1
