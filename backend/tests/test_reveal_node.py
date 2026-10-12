"""Deterministic tests for the reveal node and its projection (spec §7)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    Input,
    ReferenceRetry,
    RefVerdict,
    StoryMemory,
    Style,
)
from app.config import STYLE_PRESETS
from pipeline.reveal import _project_reveal, reveal


def _char(
    char_id: str,
    name: str,
    ref: str | None = "job-1/ref-c0-1.png",
    description: CharacterDescription | None = None,
    verdict: RefVerdict | None = None,
) -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=description or CharacterDescription(),
        canonical_ref_image=ref,
        ref_verdict=verdict,
    )


def _state(characters: list[Character], cost: Cost | None = None, reference_retry=None,
           style: Style | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="The dog ran."),
        characters=characters,
        cost=cost or Cost(),
        reference_retry=reference_retry,
        style=style or Style(),
    )


# --- _project_reveal (pure) ---

def test_project_reveal_lists_only_characters_with_a_reference():
    state = _state([_char("c0", "Kiko", ref="job-1/ref-c0-1.png"), _char("c1", "Milo", ref=None)])
    payload = _project_reveal(state)
    assert [c["char_id"] for c in payload["characters"]] == ["c0"]


def test_project_reveal_image_path_is_the_durable_storage_path():
    state = _state([_char("c0", "Kiko", ref="job-1/ref-c0-1.png")])
    payload = _project_reveal(state)
    assert payload["characters"][0]["image_path"] == "job-1/ref-c0-1.png"


def test_project_reveal_taps_left_is_three_minus_ref_retry_count():
    state = _state([_char("c0", "Kiko")], cost=Cost(ref_retry_count=1))
    assert _project_reveal(state)["taps_left"] == 2


def test_project_reveal_offers_present_and_missing_traits_despite_a_failed_verdict():
    description = CharacterDescription(species="dog", colours=["Orange"], body_features=["one floppy ear"])
    verdict = RefVerdict(
        differences_observed="d",
        contradictions=["the ear is upright, the description says floppy"],
        matches_description=False,
        attributes_present=["dog", "orange"],
    )
    state = _state([_char("c0", "Kiko", description=description, verdict=verdict)])
    chips = _project_reveal(state)["characters"][0]["chips"]
    assert chips == ["dog", "Orange", "one floppy ear"]


def test_project_reveal_deduplicates_casefolded_traits_and_keeps_first_offered_text():
    description = CharacterDescription(
        species="dog", colours=[" Orange ", "orange", "ORANGE", "Straße", "STRASSE"],
        body_features=[" DOG "],
    )
    state = _state(
        [_char("c0", "Kiko", description=description, verdict=None)],
        style=Style(prompt_fragment="flat shapes"),
    )
    chips = _project_reveal(state)["characters"][0]["chips"]
    assert chips == ["dog", " Orange ", "Straße"]


def test_project_reveal_offers_present_traits_when_there_are_no_contradictions():
    description = CharacterDescription(species="dog", colours=["orange"])
    verdict = RefVerdict(differences_observed="d", matches_description=True, attributes_present=["dog", "orange"])
    state = _state([_char("c0", "Kiko", description=description, verdict=verdict)])
    chips = _project_reveal(state)["characters"][0]["chips"]
    assert chips == ["dog", "orange"]


def test_project_reveal_ignores_contradictions_that_disagree_with_matches_description():
    """ADR-069: emphasis choices stay available even for the b9506307 verdict shape."""
    description = CharacterDescription(species="dog", colours=["orange"], body_features=["one floppy ear"])
    verdict = RefVerdict(
        differences_observed="the ear is upright. This is a contradiction.",
        contradictions=["the ear is upright, the description says floppy"],
        matches_description=True,
        attributes_present=["dog", "orange"],
    )
    state = _state([_char("c0", "Kiko", description=description, verdict=verdict)])
    assert _project_reveal(state)["characters"][0]["chips"] == ["dog", "orange", "one floppy ear"]


@pytest.mark.parametrize("description", [
    CharacterDescription(),
    CharacterDescription(
        species=" HuMaN ",
        colours=[" Skin TONE ", "average height"],
        body_features=[
            "human", "bipedal human", "human face", "human body", "humanoid body",
            "child's humanoid body", "adult’s humanoid body", "child‘s body", "adult's body",
        ],
        clothing=["warm clothing", "casual clothes", "plain clothes", "traditional or warm clothes"],
        is_humanoid=False,
    ),
])
def test_project_reveal_falls_back_to_fixed_chip_when_no_eligible_axes_remain(description):
    state = _state([_char("c0", "Leo", description=description, verdict=None)])

    assert _project_reveal(state)["characters"][0]["chips"] == [
        "overall physical appearance"
    ]


def test_project_reveal_suppresses_redundant_human_axes_from_the_committed_capture():
    capture_path = (
        Path(__file__).resolve().parents[2]
        / "docs/product/evidence/bundles/probe_out3/memory.json"
    )
    captured = json.loads(capture_path.read_text(encoding="utf-8"))
    character = Character.model_validate(captured["characters"][0])
    original = character.model_dump()

    assert _project_reveal(_state([character]))["characters"][0]["chips"] == ["short hair"]
    assert character.model_dump() == original


@pytest.mark.parametrize("species", ["robot", "human child", None])
def test_project_reveal_preserves_nonhuman_and_specific_body_and_face_chips(species):
    description = CharacterDescription(
        species=species,
        colours=["silver"],
        body_features=[
            "small box-shaped metal body",
            "rounded metal head with two blue LED lenses",
            "human face",
            "child’s body",
            "human face with freckles",
        ],
        clothing=["plain clothes", "traditional blue coat"],
        is_humanoid=True,
    )
    state = _state([_char("c0", "Leo", description=description, verdict=None)])

    chips = _project_reveal(state)["characters"][0]["chips"]
    if species is not None:
        assert chips[0] == species
        chips = chips[1:]
    assert chips == [
        "silver",
        "small box-shaped metal body",
        "rounded metal head with two blue LED lenses",
        "human face",
        "child’s body",
        "human face with freckles",
        "traditional blue coat",
    ]


def test_project_reveal_preserves_specific_and_unknown_human_traits():
    description = CharacterDescription(
        species="human",
        body_features=["human face", "human face with freckles", "humanoid silhouette"],
        clothing=["warm clothing", "warm clothing with red trim"],
    )
    state = _state([_char("c0", "Leo", description=description)])

    assert _project_reveal(state)["characters"][0]["chips"] == [
        "human face with freckles", "humanoid silhouette", "warm clothing with red trim",
    ]


def test_project_reveal_never_offers_notes_as_a_chip():
    description = CharacterDescription(species="dog", notes="always smiling")
    state = _state([_char("c0", "Kiko", description=description, verdict=None)])
    chips = _project_reveal(state)["characters"][0]["chips"]
    assert "always smiling" not in chips
    assert chips == ["dog"]


# --- reveal (the node) ---

def test_reveal_with_no_referenced_character_returns_empty_and_never_interrupts():
    state = _state([_char("c0", "Kiko", ref=None)])
    with patch("pipeline.reveal.interrupt") as mock_interrupt:
        result = reveal(state)
    mock_interrupt.assert_not_called()
    assert result == {}


def test_reveal_confirm_resume_returns_empty_dict():
    state = _state([_char("c0", "Kiko")])
    with patch("pipeline.reveal.interrupt", return_value={"action": "confirm"}):
        result = reveal(state)
    assert result == {}


def test_reveal_try_again_resume_returns_reference_retry_only():
    state = _state([_char("c0", "Kiko")])
    answer = {"action": "try_again", "char_id": "c0", "attribute": "orange sock"}
    with patch("pipeline.reveal.interrupt", return_value=answer):
        result = reveal(state)
    assert set(result) == {"reference_retry"}
    assert result["reference_retry"] == ReferenceRetry(char_id="c0", attribute="orange sock")


def test_reveal_treats_an_unrecognised_resume_payload_as_a_confirm():
    state = _state([_char("c0", "Kiko")])
    with patch("pipeline.reveal.interrupt", return_value={"action": "nonsense"}):
        result = reveal(state)
    assert result == {}


def test_reveal_never_touches_cost():
    state = _state([_char("c0", "Kiko")], cost=Cost(image_count=5))
    with patch("pipeline.reveal.interrupt", return_value={"action": "confirm"}):
        result = reveal(state)
    assert "cost" not in result


# --- ADR-035: chips never offer an attribute the active style forbids ---

def test_project_reveal_never_offers_a_chip_for_a_style_forbidden_attribute():
    """ADR-035 surface 5. A chip is a promise that tapping it buys a redraw which could plausibly
    fix that attribute. Under `comic` ("no glow") a tap on "glowing" spends one of the three
    ADR-029 taps and one paid draw on something the style guarantees will not change.

    The permitted axes still populate the list, so invariant 4 (never empty) is unaffected.
    """
    star = _char(
        "c1", "the star",
        description=CharacterDescription(species="star", colours=["glowing", "yellow"]),
    )
    payload = _project_reveal(_state([star], style=Style(prompt_fragment=STYLE_PRESETS["comic"])))

    assert payload["characters"][0]["chips"] == ["star", "yellow"]


def test_project_reveal_deduplicates_collisions_after_style_word_filtering():
    """ADR-035 amendment. Decision 2 keeps `species` unfiltered in the DESCRIPTION — it is what
    stops acceptance going vacuous — but Decision 5 lists `_chips` as a filtered surface, and its
    reason ("a tap that cannot succeed") applies to a forbidden species word just as much as to a
    forbidden colour. The two cells conflicted, and the species chip was the live leak: the tapped
    chip becomes `_mint_targeted`'s explicit emphasis, so "glowing orb" would come back into the
    draw prompt under a fragment ending "no glow" on a FRESH job, not just an in-flight one.

    Chip scope only. The reference prompt still says "glowing orb" (see the char_bible test) —
    what is removed is the promise that tapping it can change anything.
    """
    orb = _char(
        "c1", "the orb",
        description=CharacterDescription(
            species="glowing orb", colours=[" Orb ", "blue", " BLUE "],
            body_features=["glowing blue"],
        ),
    )
    payload = _project_reveal(_state([orb], style=Style(prompt_fragment=STYLE_PRESETS["comic"])))

    assert payload["characters"][0]["chips"] == ["orb", "blue"]


def test_project_reveal_falls_back_to_fixed_chip_when_style_forbids_every_axis():
    """Invariant 4: an empty chip list dead-ends the "try again" button. The existing fallback
    already covers this — pinned because filtering is now a way to reach it."""
    star = _char(
        "c1",
        "the star",
        description=CharacterDescription(species="glowing", colours=["glowing"]),
    )
    payload = _project_reveal(_state([star], style=Style(prompt_fragment=STYLE_PRESETS["comic"])))

    assert payload["characters"][0]["chips"] == ["overall physical appearance"]


def test_project_reveal_still_offers_the_chip_when_the_active_style_permits_it():
    """Per-preset, not a blanket ban — `cel` never forbids glow."""
    star = _char(
        "c1", "the star", description=CharacterDescription(species="star", colours=["glowing"]),
    )
    payload = _project_reveal(_state([star], style=Style(prompt_fragment=STYLE_PRESETS["cel"])))

    assert "glowing" in payload["characters"][0]["chips"]
