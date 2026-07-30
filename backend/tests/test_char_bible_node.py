from contracts.story_memory import CharacterDescription, RefVerdict
from pipeline.char_bible import best_draw, reference_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"


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
