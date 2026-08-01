from contracts.story_memory import Character, CharacterDescription, FailureReason
from pipeline.prompt_optimizer import ANATOMY_CLAUSE, IDENTITY_CLAUSE, build_prompt, correct_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"


def _char(char_id: str, name: str, **description_kwargs) -> Character:
    return Character(char_id=char_id, name=name, description=CharacterDescription(**description_kwargs))


def test_build_prompt_contains_every_populated_axis_for_each_present_character():
    dog = _char("c0", "the orange dog", species="dog", colours=["orange"], body_features=["three eyes"],
                clothing=["a red scarf"], notes="always smiling")
    prompt = build_prompt("The dog ran.", ["c0"], [dog], FRAG)
    for axis in ["dog", "orange", "three eyes", "a red scarf", "always smiling"]:
        assert axis in prompt


def test_build_prompt_always_contains_the_style_fragment():
    prompt = build_prompt("The dog ran.", [], [], FRAG)
    assert FRAG in prompt


def test_build_prompt_falls_back_to_the_default_style_fragment_when_none():
    from app.config import settings

    prompt = build_prompt("The dog ran.", [], [], None)
    assert settings.default_style_fragment in prompt


def test_build_prompt_always_contains_the_verbatim_text_excerpt():
    prompt = build_prompt("The dog ran across the yard.", [], [], FRAG)
    assert "The dog ran across the yard." in prompt


def test_build_prompt_with_empty_characters_present_is_text_excerpt_and_style_only():
    """Spec §4 edge case: valid — segment's and char_bible's precedent is scenes may be unreferenced."""
    prompt = build_prompt("The dog ran.", [], [], FRAG)
    assert prompt == "\n\n".join(["The dog ran.", FRAG])


def test_build_prompt_skips_a_char_id_not_found_in_characters():
    """Spec §4 edge case: same posture as segment's 'name not in roster' case — may not extend
    the roster, does not raise."""
    prompt = build_prompt("The dog ran.", ["c0", "missing-id"], [_char("c0", "the dog", species="dog")], FRAG)
    assert "dog" in prompt
    assert "missing-id" not in prompt


def test_build_prompt_never_invents_detail_for_an_empty_description():
    """Spec invariant 2: a character with no populated axes floors to just its name."""
    bare = _char("c0", "the mystery creature")
    prompt = build_prompt("It appeared.", ["c0"], [bare], FRAG)
    assert "the mystery creature" in prompt


def test_correct_prompt_wrong_colour_appends_the_documented_clause():
    dog = _char("c0", "the dog", colours=["orange", "white"])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)
    assert "match the reference's exact colours: orange, white" in result


def test_correct_prompt_wrong_species_appends_the_documented_clause():
    dog = _char("c0", "the dog", species="dog")
    result = correct_prompt("base prompt", [FailureReason.wrong_species], [dog], FRAG)
    assert "the character is a dog, not anything else" in result


def test_correct_prompt_wrong_body_feature_appends_the_documented_clause():
    dog = _char("c0", "the dog", body_features=["three eyes"])
    result = correct_prompt("base prompt", [FailureReason.wrong_body_feature], [dog], FRAG)
    assert "match these body features exactly: three eyes" in result


def test_correct_prompt_wrong_clothing_appends_the_documented_clause():
    dog = _char("c0", "the dog", clothing=["a red scarf"])
    result = correct_prompt("base prompt", [FailureReason.wrong_clothing], [dog], FRAG)
    assert "match this clothing exactly: a red scarf" in result


def test_correct_prompt_wrong_style_restates_the_style_fragment():
    result = correct_prompt("base prompt", [FailureReason.wrong_style], [], FRAG)
    assert FRAG in result


def test_correct_prompt_wrong_style_falls_back_to_the_default_style_fragment():
    from app.config import settings

    result = correct_prompt("base prompt", [FailureReason.wrong_style], [], None)
    assert settings.default_style_fragment in result


def test_correct_prompt_different_face_appends_the_documented_clause():
    result = correct_prompt("base prompt", [FailureReason.different_face], [], FRAG)
    assert "match the reference character's face exactly" in result


def test_correct_prompt_character_absent_appends_the_documented_clause():
    dog = _char("c0", "the dog")
    result = correct_prompt("base prompt", [FailureReason.character_absent], [dog], FRAG)
    assert "make sure the dog is clearly visible in the scene" in result


def test_correct_prompt_multiple_reasons_all_appear_in_enum_declaration_order():
    result = correct_prompt(
        "base prompt", [FailureReason.character_absent, FailureReason.wrong_colour], [], FRAG
    )
    colour_clause = "match the reference's exact colours:"
    absent_clause = "is clearly visible in the scene"
    assert result.index(colour_clause) < result.index(absent_clause)


def test_correct_prompt_a_repeated_reason_produces_its_clause_once():
    result = correct_prompt(
        "base prompt", [FailureReason.different_face, FailureReason.different_face], [], FRAG
    )
    assert result.count("match the reference character's face exactly") == 1


def test_correct_prompt_two_characters_join_both_characters_colours():
    """Guards the attribution-ceiling behavior (spec §4): axis-based clauses fill from EVERY
    character, since VlmVerdict carries no per-character breakdown."""
    a = _char("c0", "the dog", colours=["orange"])
    b = _char("c1", "the cat", colours=["black"])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [a, b], FRAG)
    assert "orange, black" in result


def test_correct_prompt_on_empty_failure_reasons_returns_the_prompt_unchanged():
    assert correct_prompt("base prompt", [], [], FRAG) == "base prompt"


def test_correct_prompt_never_alters_the_original_prompt_content():
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [], FRAG)
    assert result.startswith("base prompt")


def test_correct_prompt_an_empty_axis_still_appends_an_empty_clause():
    """Spec §4 edge case: does not invent colours analyze/char_bible never captured."""
    dog = _char("c0", "the dog", colours=[])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)
    assert "match the reference's exact colours: " in result


# --- regeneration-controller §4: the two booleans that make the correction total ---

def test_correct_prompt_anatomy_intact_false_appends_the_anatomy_clause():
    """ADR-028 froze anatomy OUT of FailureReason, so an anatomy-only failure yields no
    reason clause. Without this the retry is a pure resample — what ADR-010 rejects."""
    result = correct_prompt("draw a dog", [], [], "cel", anatomy_intact=False)

    assert result.startswith("draw a dog")
    assert ANATOMY_CLAUSE in result


def test_correct_prompt_anatomy_intact_true_appends_nothing():
    assert correct_prompt("draw a dog", [], [], "cel", anatomy_intact=True) == "draw a dog"


def test_correct_prompt_same_character_false_with_no_reasons_appends_the_identity_clause():
    """The judge named the failure but no reason for it — a generic identity clause is the
    only correction available, and it beats resampling."""
    result = correct_prompt("draw a dog", [], [], "cel", same_character=False)

    assert result.startswith("draw a dog")
    assert IDENTITY_CLAUSE in result


def test_correct_prompt_same_character_false_with_reasons_omits_the_identity_clause():
    """Guarded on EMPTY failure_reasons so it never duplicates different_face."""
    result = correct_prompt(
        "draw a dog", [FailureReason.different_face], [], "cel", same_character=False
    )

    assert IDENTITY_CLAUSE not in result
    assert "match the reference character's face exactly" in result


def test_correct_prompt_both_booleans_false_appends_identity_then_anatomy():
    result = correct_prompt("draw a dog", [], [], "cel", same_character=False, anatomy_intact=False)

    assert result.index(IDENTITY_CLAUSE) < result.index(ANATOMY_CLAUSE)


def test_correct_prompt_reason_clauses_precede_the_two_boolean_clauses():
    """Enum-order reason clauses first, then identity, then anatomy — so a reader of the
    prompt sees the specific corrections before the generic ones."""
    result = correct_prompt(
        "draw a dog",
        [FailureReason.different_face],
        [],
        "cel",
        same_character=False,
        anatomy_intact=False,
    )

    assert result.index("match the reference character's face exactly") < result.index(ANATOMY_CLAUSE)


def test_correct_prompt_defaults_reproduce_the_previous_behaviour_exactly():
    """The existing call signature stays byte-compatible: four positional args, no clauses
    added by the new params. Every pre-existing assertion in this file depends on it."""
    assert correct_prompt("draw a dog", [], [], "cel") == "draw a dog"
    assert correct_prompt("draw a dog", [FailureReason.different_face], [], "cel") == (
        "draw a dog\nmatch the reference character's face exactly"
    )


def test_correct_prompt_never_drops_the_base_prompt_under_either_boolean():
    """Invariant 3: correct_prompt only ever APPENDS."""
    for kwargs in ({"same_character": False}, {"anatomy_intact": False}):
        result = correct_prompt("the base prompt survives", [], [], "cel", **kwargs)
        assert "the base prompt survives" in result
