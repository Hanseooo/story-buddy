import logging

from app.config import STYLE_PRESETS
from contracts.story_memory import Character, CharacterDescription, FailureReason, Location, StoryObject
from pipeline.prompt_optimizer import (
    ANATOMY_CLAUSE,
    COMPOSITION_CLAUSE,
    IDENTITY_CLAUSE,
    NON_HUMAN_CLAUSE,
    TEXT_CLAUSE,
    build_prompt,
    correct_prompt,
    filtered_description,
    filtered_location,
    permitted_words,
    referenced_characters,
    style_prohibitions,
)

FRAG = "flat cel-shaded cartoon, thick clean black outlines"


def test_visual_continuity_prompt_blocks_are_in_contract_order():
    ana = Character(
        char_id="c0",
        name="Ana",
        description=CharacterDescription(
            species="human",
            colours=["brown eyes"],
            body_features=["round face"],
            clothing=["yellow shirt"],
        ),
        canonical_ref_image="story/ref-c0.png",
    )
    maya = Character(
        char_id="c1",
        name="Maya",
        description=CharacterDescription(
            species="human",
            colours=["black hair"],
            body_features=["oval face"],
            clothing=["blue dress"],
        ),
    )
    sword = StoryObject(
        obj_id="obj0",
        name="wooden sword",
        description="a short wooden sword with a red cord grip",
        owner_char_id="c0",
    )
    prompt = build_prompt(
        "Ana ran toward the forest.",
        ["c0", "c1"],
        [ana, maya],
        "flat cel illustration, no gradients",
        Location(loc_id="loc0", name="forest", description="tall pine trees"),
        ["obj0"],
        [sword],
        "Ana runs right; Maya stays behind. wooden sword is held by Ana.",
    )

    markers = [
        "Image 1 is Ana",
        "Maya",
        "exactly 2 characters: Ana and Maya",
        "Visible objects:",
        "Visual direction:",
        "Setting:",
        "Ana ran toward the forest.",
        "flat cel illustration, no gradients",
    ]
    positions = [prompt.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert "wooden sword, a short wooden sword with a red cord grip" in prompt
    assert "reference images define appearance, not pose, crop, expression or viewing angle" in prompt


def test_build_prompt_skips_unknown_object_ids_and_deduplicates_in_first_seen_order():
    sword = StoryObject(
        obj_id="obj0",
        name="wooden sword",
        description="a short wooden sword",
    )
    shield = StoryObject(
        obj_id="obj1",
        name="iron shield",
        description="a round shield",
    )
    prompt = build_prompt(
        "Ana picked up her tools.",
        [],
        [],
        "flat cel illustration",
        objects_present=["obj0", "unknown_obj", "obj1", "obj0"],
        objects=[sword, shield],
        visual_direction="Ana stands in the center.",
    )

    assert "Visible objects:\nwooden sword, a short wooden sword\niron shield, a round shield" in prompt
    assert "unknown_obj" not in prompt


def test_build_prompt_filters_style_forbidden_words_from_object_description_not_excerpt():
    sword = StoryObject(
        obj_id="obj0",
        name="glowing sword",
        description="a glowing magic sword",
    )
    prompt = build_prompt(
        "She held the glowing sword.",
        [],
        [],
        "flat cel illustration, no glow",
        objects_present=["obj0"],
        objects=[sword],
        visual_direction="Ana holds the sword.",
    )

    assert "glowing sword, a magic sword" in prompt
    assert "She held the glowing sword." in prompt


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


def test_build_prompt_names_each_reference_image_by_index():
    """Issue #23: the payload sent prose plus ANONYMOUS image_urls, so the edit model composited
    both references into the canvas instead of using them as identity conditioning. Since
    scene-setting-and-subject-binding §4.2 each name carries its own attributes (the roll fold)."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star", species="star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("She held it toward the sky.", ["c0", "c1"], [ana, star], FRAG)

    assert "Image 1 is Ana, girl." in prompt
    assert "Image 2 is the star." in prompt      # species repeats the name → dropped (issue #32)


def test_build_prompt_numbers_images_in_upload_order_not_roster_order():
    """The drift this guards: generate_scene uploads ONLY characters with a canonical reference,
    so a present character without one must not consume an image number."""
    ana = _char("c0", "Ana", species="girl")                    # present, but no reference drawn
    star = _char("c1", "the star", species="star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("She held it toward the sky.", ["c0", "c1"], [ana, star], FRAG)

    assert "Image 1 is the star." in prompt
    assert "Image 2" not in prompt


def test_build_prompt_omits_the_image_roll_when_no_character_has_a_reference():
    """The text-to-image path (generate_scene:55-57) sends no images — naming them would lie."""
    bare = _char("c0", "the mystery creature")
    prompt = build_prompt("It appeared.", ["c0"], [bare], FRAG)

    assert "Image 1" not in prompt


def test_build_prompt_binds_a_named_character_in_the_scene_text_to_its_reference():
    """Issue #32: `REFERENCE_CLAUSE` governed the IMAGES only, so "found a tiny glowing star"
    summoned a second star independently of anything the prompt said about Image 2."""
    star = _char("c1", "the star", species="star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("Ana found a tiny glowing star.", ["c1"], [star], FRAG)

    assert "not to a second thing of the same name" in prompt


def test_build_prompt_omits_the_binding_clause_when_no_reference_was_sent():
    """The text-to-image path (generate_scene:55-57) sends no images, so there is nothing to
    bind the name TO — same reason the image roll is omitted."""
    star = _char("c1", "the star", species="star")

    prompt = build_prompt("Ana found a tiny glowing star.", ["c1"], [star], FRAG)

    assert "not to a second thing of the same name" not in prompt


def test_build_prompt_drops_a_species_that_only_repeats_the_name():
    """Issue #32: "the star - star" is a definition, not a description — a second bare assertion
    of the noun the excerpt is already summoning."""
    star = _char("c1", "the star", species="star")

    prompt = build_prompt("Ana found a star.", ["c1"], [star], FRAG)

    assert prompt.split("\n\n")[0] == "the star"


def test_build_prompt_keeps_the_other_axes_when_the_species_repeats_the_name():
    star = _char("c1", "the star", species="star", body_features=["tiny"])

    prompt = build_prompt("Ana found a star.", ["c1"], [star], FRAG)

    assert prompt.split("\n\n")[0] == "the star, tiny"


def test_build_prompt_keeps_a_species_the_name_does_not_carry():
    ana = _char("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert prompt.split("\n\n")[0] == "Ana, girl"


def test_build_prompt_keeps_a_multi_word_species_the_name_only_partly_carries():
    """Token match, not substring: "the retriever" does not carry "golden retriever", so the
    species survives. The degenerate case this drops is exact, not approximate."""
    dog = _char("c0", "the retriever", species="golden retriever")

    prompt = build_prompt("It barked.", ["c0"], [dog], FRAG)

    assert prompt.split("\n\n")[0] == "the retriever, golden retriever"


def test_a_scene_describes_its_characters_the_way_the_reference_prompt_does():
    """The docstring on `_describe` promises the scene prompt phrases a character the way
    `char_bible` does. Commit bef9982 moved char_bible to commas and left this copy on
    `"{name} - {a}; {b}"`, so the promise was false for an hour.

    It matters beyond tidiness: that label shape is what a prod cel page rendered as the word
    "Casey" lettered above the character, the same way the reference draw returned "Hoe - Star:".
    A dash and a semicolon after a proper noun read as a caption; commas read as description.
    """
    ana = _char("c0", "Ana", species="girl", colours=["red"], clothing=["jeans"])

    line = build_prompt("Ana waved.", ["c0"], [ana], FRAG).split("\n\n")[0]

    assert line == "Ana, girl, red, jeans"
    assert " - " not in line and ";" not in line


def test_referenced_characters_is_the_order_generate_scene_uploads():
    ana = _char("c0", "Ana")
    star = _char("c1", "the star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"
    bird = _char("c2", "the bird")
    bird.canonical_ref_image = "job-123/ref-c2-1.png"

    got = referenced_characters(["c2", "c0", "c1", "ghost-id"], [ana, star, bird])

    assert [c.name for c in got] == ["the bird", "the star"]


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
    # A real character, not `[]`: both these clauses interpolate an axis, and an empty roster now
    # drops them as unfillable, which would make this order assertion vacuous.
    dog = _char("c0", "the dog", colours=["orange"])
    result = correct_prompt(
        "base prompt", [FailureReason.character_absent, FailureReason.wrong_colour], [dog], FRAG
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


def test_correct_prompt_an_empty_axis_drops_its_clause_and_floors_on_identity():
    """Spec §4 edge case, revised. Still does not invent colours analyze/char_bible never captured
    — but "match the reference's exact colours: " corrects nothing, and once `wrong_colour` became
    a GATING_REASON it could be the SOLE reason on a page, making the retry the resample ADR-010
    rejects. The judge compares against the reference IMAGE, so it can flag a colour the contract
    never recorded; IDENTITY_CLAUSE points the retry at the images, which do know it."""
    dog = _char("c0", "the dog", colours=[])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)

    assert "match the reference's exact colours" not in result
    assert IDENTITY_CLAUSE in result


def test_correct_prompt_an_empty_axis_beside_a_filled_one_does_not_floor():
    """The floor is for a correction that came out EMPTY, not for every dropped clause. A page
    that still has something specific to say must not be handed the generic clause as well."""
    dog = _char("c0", "the dog", colours=[], body_features=["three eyes"])
    result = correct_prompt(
        "base prompt", [FailureReason.wrong_colour, FailureReason.wrong_body_feature], [dog], FRAG
    )

    assert "match these body features exactly: three eyes" in result
    assert "match the reference's exact colours" not in result
    assert IDENTITY_CLAUSE not in result


def test_correct_prompt_logs_the_clause_it_dropped(caplog):
    """CC-5. The whole point of the drop is that it happens silently in prod otherwise — this line
    is how a thin `analyze` description gets noticed instead of quietly costing a redraw."""
    dog = _char("c0", "the dog", colours=[])
    with caplog.at_level(logging.INFO):
        correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)

    assert "wrong_colour" in caplog.text


def test_correct_prompt_the_floor_never_fires_when_nothing_failed():
    """`failure_reasons` guards it: the no-op call must still return the prompt byte-identical."""
    assert correct_prompt("base prompt", [], [], FRAG) == "base prompt"


def test_correct_prompt_a_style_forbidden_axis_drops_rather_than_rendering_hollow():
    """ADR-035 leaves `colours == ["glowing"]` empty under `comic`. Same shape as a natively empty
    axis and the same answer — restating the forbidden attribute is issue #24, and rendering the
    clause with nothing left is the resample this now avoids."""
    star = _char("c0", "the star", colours=["glowing"])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [star], COMIC)

    assert "glowing" not in result
    assert "match the reference's exact colours" not in result
    assert IDENTITY_CLAUSE in result


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
        f"draw a dog\nmatch the reference character's face exactly\n{COMPOSITION_CLAUSE}"
    )


def test_correct_prompt_never_drops_the_base_prompt_under_either_boolean():
    """Invariant 3: correct_prompt only ever APPENDS."""
    for kwargs in ({"same_character": False}, {"anatomy_intact": False}):
        result = correct_prompt("the base prompt survives", [], [], "cel", **kwargs)
        assert "the base prompt survives" in result


# --- ADR-035: the style fragment's own prohibitions filter the description ---

COMIC = STYLE_PRESETS["comic"]    # "...no gradients, no glow"
CEL = STYLE_PRESETS["cel"]        # "...no glossy highlights, no airbrushing"


def test_style_prohibitions_reads_the_no_clauses_out_of_the_fragment():
    """ADR-035 Decision 1: derived, never hand-listed — ADR-022 keeps sole ownership.

    The shared lettering set that used to be OR'd into both of these left the fragments on
    2026-08-13 for `providers.NEGATIVE_PROMPT` (`app/config.py:74`), so what survives is each
    preset's own RENDERING prohibitions. Derivation is unchanged; its input shrank.
    """
    assert style_prohibitions(COMIC) == {"gradients", "glow"}
    assert style_prohibitions(CEL) == {"gradients", "glossy", "highlights", "airbrushing"}


def test_style_prohibitions_of_a_fragment_that_forbids_nothing_is_empty():
    assert style_prohibitions("flat gouache storybook illustration") == set()


def test_filtered_description_drops_a_colour_the_active_style_forbids():
    """Prod job b9506307: analyze put "glowing" in colours under a preset ending "no glow"."""
    filtered = filtered_description(
        CharacterDescription(species="star", colours=["glowing", "yellow"]), COMIC
    )
    assert filtered.colours == ["yellow"]


def test_filtered_description_keeps_an_attribute_the_fragment_never_forbids():
    """ADR-035 consequence: per-preset, not uniform. `cel` never says "no glow"."""
    filtered = filtered_description(CharacterDescription(species="star", colours=["glowing"]), CEL)
    assert filtered.colours == ["glowing"]


def test_filtered_description_removes_the_forbidden_word_and_keeps_the_rest_of_the_entry():
    """ADR-035 Decision 3: word-level. Dropping the whole entry would discard a real subject
    fact ("eyes") in order to remove a rendering one ("glowing")."""
    filtered = filtered_description(
        CharacterDescription(species="cat", body_features=["glowing eyes", "long tail"]), COMIC
    )
    assert filtered.body_features == ["eyes", "long tail"]


def test_filtered_description_never_touches_species():
    """ADR-035 Decision 2: species is REQUIRED at the analyze boundary precisely so acceptance is
    never vacuous, so it survives here even when the style forbids a word inside it (limit 4)."""
    filtered = filtered_description(
        CharacterDescription(species="a glowing star", colours=["glowing"]), COMIC
    )
    assert filtered.species == "a glowing star"
    assert filtered.colours == []


def test_filtered_description_drops_a_forbidden_notes_whole_rather_than_word_by_word():
    """ADR-035 limit 6. `notes` is free prose, so `_filter_axis`'s word-level rule would leave
    "softly in the dark" — a mangled fragment the generator still has to reconcile. Dropping it
    whole is safe in a way it is not for the other axes: ADR-034 removed `notes` from the judge
    prompt, so nothing here can make acceptance vacuous."""
    filtered = filtered_description(
        CharacterDescription(species="star", notes="glows softly in the dark"), COMIC
    )
    assert filtered.notes is None


def test_filtered_description_keeps_a_notes_the_style_permits():
    """The prod value. "secondary character" is framing the generator can use and no preset
    forbids, so limit 6 must not cost it."""
    filtered = filtered_description(
        CharacterDescription(species="star", notes="secondary character"), COMIC
    )
    assert filtered.notes == "secondary character"


def test_permitted_words_strips_only_the_forbidden_word_out_of_a_single_value():
    """ADR-035 amendment: the chip-scope helper. Same word-level rule as `_filter_axis`, over one
    string rather than a list, because `species` is a scalar axis."""
    assert permitted_words("glowing orb", COMIC) == "orb"
    assert permitted_words("orange dog", COMIC) == "orange dog"


def test_permitted_words_is_empty_when_nothing_survives():
    """`reveal._chips` drops falsy axis values, so an all-forbidden species offers no chip and
    the existing fallback (invariant 4) covers the empty list."""
    assert permitted_words("glowing", COMIC) == ""


def test_permitted_words_passes_none_through():
    """`CharacterDescription.species` is Optional."""
    assert permitted_words(None, COMIC) is None


def test_filtered_description_matches_on_prefix_in_both_directions():
    """"glowing" vs "glow" and "gradient" vs "gradients" — with a min length so short tokens
    cannot collide ("glove" is not "glow")."""
    filtered = filtered_description(
        CharacterDescription(species="thing", colours=["gradient", "glove"]), COMIC
    )
    assert filtered.colours == ["glove"]


def test_filtered_description_leaves_a_description_alone_when_the_style_forbids_nothing():
    description = CharacterDescription(species="dog", colours=["orange"], clothing=["a red scarf"])
    assert filtered_description(description, "flat gouache storybook") == description


def test_build_prompt_drops_a_style_forbidden_attribute_from_the_description_line():
    """ADR-035 surface 3 — issue #23's `s1`. The scene prompt asserted "glowing" against a
    reference the same style clause guaranteed would not be glowing."""
    star = _char("c1", "the star", species="star", colours=["glowing"])
    prompt = build_prompt("Ana found a star.", ["c1"], [star], COMIC)
    # The description line survives with the forbidden colour gone; its species is suppressed
    # separately, as a repeat of the name (issue #32).
    assert prompt.split("\n\n")[0] == "the star"
    assert "glowing" not in prompt


def test_build_prompt_still_emits_the_text_excerpt_verbatim_when_it_names_a_forbidden_term():
    """ADR-035 limit 1, pinned: ADR-013 is NOT amended. The excerpt is untouched — only the
    description axes are filtered."""
    star = _char("c1", "the star", species="star", colours=["glowing"])
    prompt = build_prompt("Ana found a tiny glowing star.", ["c1"], [star], COMIC)
    assert "Ana found a tiny glowing star." in prompt
    assert prompt.count("glowing") == 1


def test_correct_prompt_does_not_reinforce_a_style_forbidden_colour():
    """ADR-035 surface 4 — issue #24: `wrong_colour` answered with "match the reference's exact
    colours: glowing", reinforcing the side that is not in the reference."""
    star = _char("c1", "the star", species="star", colours=["glowing", "yellow"])
    result = correct_prompt("draw a star", [FailureReason.wrong_colour], [star], COMIC)
    assert "match the reference's exact colours: yellow" in result
    assert "glowing" not in result


# --- ADR-035 surface 5: location descriptions (§6 test 15) ---

def test_filtered_location_drops_a_forbidden_word_from_the_description():
    """Same word-level rule as `_filter_axis`: the forbidden rendering property goes, the real
    subject fact stays."""
    filtered = filtered_location(
        Location(loc_id="loc0", name="the cave", description="glowing cave"), COMIC
    )
    assert filtered.description == "cave"


def test_filtered_location_never_touches_the_name():
    """The name is what the child called the place, and it is the whole `Setting:` line when the
    description is null. Filtering it could empty the line entirely."""
    filtered = filtered_location(
        Location(loc_id="loc0", name="the glowing cave", description="glowing cave"), COMIC
    )
    assert filtered.name == "the glowing cave"


def test_filtered_location_drops_a_description_with_nothing_left():
    filtered = filtered_location(
        Location(loc_id="loc0", name="the cave", description="glowing"), COMIC
    )
    assert filtered.description is None


def test_filtered_location_leaves_a_permitted_description_alone():
    location = Location(loc_id="loc0", name="the beach", description="golden sand, palm trees")
    assert filtered_location(location, COMIC) == location


def test_filtered_location_passes_none_through():
    assert filtered_location(None, COMIC) is None


def test_filtered_location_handles_a_null_description():
    location = Location(loc_id="loc0", name="the beach")
    assert filtered_location(location, COMIC) == location


# --- §4.2 D2: the roll fold (§6 tests 8-11) ---

def test_the_roll_folds_the_description_into_the_image_sentence():
    """§6 test 8. Today the roll and the attribute line are two unbound blocks; folded, each
    reference image and its attributes are one sentence."""
    ana = _char("c0", "Ana", species="girl", colours=["red"], clothing=["jeans"])
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana, girl, red, jeans." in prompt


def test_the_roll_of_a_character_with_no_populated_axes_is_byte_identical_to_before():
    """§6 test 9. `_describe` floors to the bare name, so `"Image 1 is Ana."` is unchanged."""
    ana = _char("c0", "Ana")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana." in prompt


def test_a_present_character_with_no_reference_keeps_a_plain_line_below_the_roll():
    """§6 test 10. It has no image number to fold into, so it keeps the description line it has
    always had — and the line must appear AFTER the roll, not before it."""
    ana = _char("c0", "Ana", species="girl")                 # no canonical reference
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("Ana held the star.", ["c0", "c1"], [ana, star], FRAG)

    assert "Image 1 is the star, tiny." in prompt
    assert prompt.index("Image 1 is") < prompt.index("Ana, girl")


def test_a_referenced_character_is_described_once_and_only_in_the_roll():
    """The fold REPLACES the separate attribute line — emitting both would restore the two
    unbound blocks this change exists to remove, at double the tokens."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert prompt.count("Ana, girl") == 1


def test_the_roll_order_still_matches_referenced_characters_order():
    """§6 test 11 / invariant 4. `generate_scene`, `regenerate` and `output_mod` all index
    `ref_paths` against this roll, so a reorder here silently lies on three nodes."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"
    characters = [ana, star]

    prompt = build_prompt("She held it up.", ["c1", "c0"], characters, FRAG)
    order = [c.name for c in referenced_characters(["c1", "c0"], characters)]

    assert order == ["the star", "Ana"]
    assert prompt.index("Image 1 is the star") < prompt.index("Image 2 is Ana")


def test_the_reference_clause_still_follows_the_roll():
    """The clause is the antecedent-supplier for the generic "one of these characters" binding;
    the fold must not detach it from the roll."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana, girl. Use them only as references" in prompt


# --- §4.2 D2: the two guard clauses (§6 tests 12-14) ---

def _referenced(char_id: str, name: str, **kwargs) -> Character:
    character = _char(char_id, name, **kwargs)
    character.canonical_ref_image = f"job-123/ref-{char_id}-1.png"
    return character


def test_the_subject_count_clause_names_every_present_character():
    ana = _referenced("c0", "Ana", species="girl")
    star = _referenced("c1", "the star", body_features=["tiny"])

    prompt = build_prompt("She held it up.", ["c0", "c1"], [ana, star], FRAG)

    assert "This illustration contains exactly 2 characters: Ana and the star." in prompt


def test_both_guard_clauses_appear_on_the_reference_path():
    """§6 test 12, first half."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert NON_HUMAN_CLAUSE in prompt


def test_both_guard_clauses_appear_on_the_text_to_image_path():
    """§6 test 12, second half — the load-bearing half. The roll and REFERENCE_CLAUSE are omitted
    when no character has a reference, so a guard placed INSIDE the clause would be silently inert
    on every reference-less scene."""
    ana = _char("c0", "Ana", species="girl")               # no canonical reference

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1" not in prompt
    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert NON_HUMAN_CLAUSE in prompt


def test_the_count_reads_one_character_singular():
    """§6 test 13, second half: no `1 characters`."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "1 characters" not in prompt


def test_the_count_is_computed_after_the_missing_char_id_filter():
    """§6 test 13, first half. A char_id absent from `characters` is already warned + skipped, so
    counting before the filter asserts a number the prompt does not name."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0", "ghost-id"], [ana], FRAG)

    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert "ghost-id" not in prompt


def test_a_present_character_without_a_reference_is_still_counted():
    """§4.2 edge case: it keeps a plain description line and still occupies a subject slot."""
    ana = _char("c0", "Ana", species="girl")               # no reference
    star = _referenced("c1", "the star", body_features=["tiny"])

    prompt = build_prompt("Ana held the star.", ["c0", "c1"], [ana, star], FRAG)

    assert "This illustration contains exactly 2 characters: Ana and the star." in prompt


def test_the_count_names_three_characters_with_a_serial_comma_free_join():
    ana = _referenced("c0", "Ana", species="girl")
    star = _referenced("c1", "the star", body_features=["tiny"])
    bird = _referenced("c2", "the bird", species="bird")

    prompt = build_prompt("They met.", ["c0", "c1", "c2"], [ana, star, bird], FRAG)

    assert "exactly 3 characters: Ana, the star and the bird." in prompt


def test_no_clause_at_all_when_characters_present_is_empty():
    """§6 test 14 / §4.2 edge case: no roll, no count clause, no non-human clause — all three
    would reference nothing."""
    prompt = build_prompt("The waves crashed.", [], [], FRAG)

    assert "Image 1" not in prompt
    assert "This illustration contains exactly" not in prompt
    assert NON_HUMAN_CLAUSE not in prompt
    assert prompt == "\n\n".join(["The waves crashed.", FRAG])


def test_no_clause_at_all_when_every_char_id_is_missing_from_the_roster():
    """The filter can empty the list even when `characters_present` was not empty."""
    prompt = build_prompt("The waves crashed.", ["ghost-id"], [], FRAG)

    assert "This illustration contains exactly" not in prompt
    assert NON_HUMAN_CLAUSE not in prompt


def test_the_guard_clauses_sit_after_the_descriptions_and_before_the_excerpt():
    ana = _char("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved at the sea.", ["c0"], [ana], FRAG)

    assert prompt.index("Ana, girl") < prompt.index("This illustration contains")
    assert prompt.index(NON_HUMAN_CLAUSE) < prompt.index("Ana waved at the sea.")


# --- §4.1 D1: the Setting line (§6 tests 15-16) ---

def test_build_prompt_emits_a_setting_line_from_the_location():
    location = Location(loc_id="loc0", name="the beach", description="golden sand, palm trees")

    prompt = build_prompt("She ran.", [], [], FRAG, location)

    assert "Setting: the beach - golden sand, palm trees" in prompt


def test_build_prompt_emits_a_name_only_setting_line_when_the_description_is_null():
    """§4.1: `ExtractedLocation.description` stays optional, and name-only is still better than
    today's nothing."""
    prompt = build_prompt("She ran.", [], [], FRAG, Location(loc_id="loc0", name="the beach"))

    assert "Setting: the beach" in prompt
    assert "Setting: the beach -" not in prompt


def test_build_prompt_emits_no_setting_line_without_a_location():
    """§6 test 16 — the default, and the whole behaviour for a story that names no place."""
    prompt = build_prompt("She ran.", [], [], FRAG)

    assert "Setting:" not in prompt


def test_the_setting_line_is_style_filtered_but_keeps_its_name():
    """§6 test 15 through `build_prompt`, not just the helper."""
    location = Location(loc_id="loc0", name="the glowing cave", description="glowing cave")

    prompt = build_prompt("She went in.", [], [], COMIC, location)

    assert "Setting: the glowing cave - cave" in prompt


def test_the_setting_line_precedes_the_text_excerpt():
    """§4.1 edge case: on a conflict ("that night" vs a sunny description) the excerpt must be the
    LATER and more specific assertion. Reduced, not eliminated (§4.5.3)."""
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("That night it was dark.", [], [], FRAG, location)

    assert prompt.index("Setting: the beach") < prompt.index("That night it was dark.")


def test_the_setting_line_follows_the_guard_clauses():
    ana = _char("c0", "Ana", species="girl")
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("Ana ran.", ["c0"], [ana], FRAG, location)

    assert prompt.index(NON_HUMAN_CLAUSE) < prompt.index("Setting: the beach")


def test_the_style_fragment_is_still_last_with_a_location_present():
    """Invariant 1, pinned against the new block."""
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("She ran.", [], [], FRAG, location)

    assert prompt.endswith(FRAG)


# --- §4.3 D3(a): the defensive half (§6 test 17) ---

def test_referenced_characters_deduplicates_a_repeated_char_id():
    """§6 test 17. `segment` no longer emits one, but a checkpoint written before that change
    still can — and `_fal_ref_url` would return fresh signed URLs for the same reference twice, so
    the roll would say "Image 1 is the star. Image 2 is the star." over one character."""
    star = _char("c1", "the star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    assert [c.char_id for c in referenced_characters(["c1", "c1"], [star])] == ["c1"]


def test_referenced_characters_keeps_the_relative_order_of_the_survivors():
    """Invariant 4: `dict.fromkeys` preserves first-seen order, so removing a duplicate cannot
    reorder the survivors that "Image N is X" is indexed against on three nodes."""
    ana = _char("c0", "Ana")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    got = referenced_characters(["c1", "c0", "c1"], [ana, star])

    assert [c.name for c in got] == ["the star", "Ana"]


def test_the_roll_numbers_a_repeated_char_id_only_once():
    """The end-to-end shape of the bug: one image, one number, one subject."""
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("It shone.", ["c1", "c1"], [star], FRAG)

    assert "Image 1 is the star, tiny." in prompt
    assert "Image 2" not in prompt
    assert "This illustration contains exactly 1 character: the star." in prompt


def test_correct_prompt_appends_the_text_clause_when_text_free_is_false():
    """lettering-suppression §4.4: the clause fires off a BOOLEAN, mirroring anatomy_intact.
    FailureReason stays frozen at 7 (ADR-028) — there is no 8th value to hang this on."""
    dog = _char("c0", "the dog", species="dog")
    corrected = correct_prompt("base prompt", [], [dog], FRAG, text_free=False)

    assert TEXT_CLAUSE in corrected
    assert corrected.startswith("base prompt")     # invariant 3: never drops content


def test_correct_prompt_omits_the_text_clause_when_text_free_is_true():
    dog = _char("c0", "the dog", species="dog")
    assert TEXT_CLAUSE not in correct_prompt("base prompt", [], [dog], FRAG, text_free=True)
    assert TEXT_CLAUSE not in correct_prompt("base prompt", [], [dog], FRAG)


def test_the_text_clause_appends_alongside_the_anatomy_clause_without_disturbing_it():
    """§6 test 16: both booleans can fail on the same attempt. Neither duplicates nor reorders
    the other, and the anatomy clause keeps its position ahead of the new one."""
    dog = _char("c0", "the dog", species="dog")
    corrected = correct_prompt(
        "base prompt", [], [dog], FRAG, anatomy_intact=False, text_free=False
    )

    assert corrected.count(ANATOMY_CLAUSE) == 1
    assert corrected.count(TEXT_CLAUSE) == 1
    assert corrected.index(ANATOMY_CLAUSE) < corrected.index(TEXT_CLAUSE)


def test_the_text_clause_never_utters_a_word_the_negative_prompt_suppresses():
    """§6 test 17, the whole trick. Three prompt-wording attempts have already failed because
    naming a thing summons it: the fragments said "no lettering" and a page lettered; the
    reference prompt said "reference" and the word was drawn on the canvas. This clause fires
    precisely on images that ALREADY have text — the worst possible moment to name it — so it
    asserts blankness instead. Same invariant test_config.py already applies to STYLE_PRESETS.
    """
    import re

    from providers import NEGATIVE_PROMPT

    for term in (term.strip() for term in NEGATIVE_PROMPT.split(",")):
        assert not re.search(rf"\b{re.escape(term)}\b", TEXT_CLAUSE, re.I), \
            f"TEXT_CLAUSE names {term!r}, which is what put lettering on the canvas the last three times"
    assert "lettering" not in TEXT_CLAUSE.lower()


def test_correct_prompt_appends_every_scene_contradiction_after_existing_corrections():
    base = "Draw Ana running."
    ana = _char(
        "c0",
        "Ana",
        species="human",
        colours=["brown eyes"],
        body_features=["round face"],
        clothing=["yellow shirt"],
    )
    result = correct_prompt(
        base,
        [FailureReason.wrong_colour],
        [ana],
        "flat cel illustration",
        anatomy_intact=False,
        scene_contradictions=[
            "Ana faces left instead of right.",
            "The wooden sword is missing.",
        ],
    )

    markers = [
        "match the reference's exact colours",
        ANATOMY_CLAUSE,
        "Correct this scene contradiction: Ana faces left instead of right.",
        "Correct this scene contradiction: The wooden sword is missing.",
    ]
    positions = [result.index(marker) for marker in markers]
    assert positions == sorted(positions)


def test_correct_prompt_appends_composition_clause():
    """§7 test 7. All four correction paths — generic identity, boolean, reason-based, and scene
    contradiction — end with the clause, so no path can silently become composition-destructive.
    §7 test 8: a no-op call is still byte-identical.
    """
    base = "Draw Ana."

    # No correction at all → byte-identical, nothing appended.
    assert correct_prompt(base, [], [], "") == base

    dog = _char("c0", "the dog", colours=["brown"])
    paths = {
        "generic identity": correct_prompt(base, [], [], "", same_character=False),
        "boolean (anatomy)": correct_prompt(base, [], [], "", anatomy_intact=False),
        "boolean (text)": correct_prompt(base, [], [], "", text_free=False),
        "reason-based": correct_prompt(base, [FailureReason.wrong_colour], [dog], ""),
        # Reason present but unfillable → IDENTITY_CLAUSE floors it; the clause still lands last.
        "identity floor": correct_prompt(base, [FailureReason.wrong_colour], [], ""),
        "scene contradiction": correct_prompt(base, [], [], "", scene_contradictions=["Ana faces left"]),
    }
    for path, corrected in paths.items():
        assert corrected.endswith(COMPOSITION_CLAUSE), path
        assert corrected.count(COMPOSITION_CLAUSE) == 1, path
        assert corrected.startswith(base), path







