from unittest.mock import MagicMock, patch

import pytest

from contracts.story_memory import CharacterDescription, RefVerdict
from pipeline.char_bible import best_draw, mint_reference, reference_prompt

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
    assert path == "story-1/ref-c0.png"


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
    assert path == "story-1/ref-c0.png"
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

    assert path == "story-1/ref-c0.png"
    assert _uploaded_path(supabase) == "story-1/ref-c0.png"
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
