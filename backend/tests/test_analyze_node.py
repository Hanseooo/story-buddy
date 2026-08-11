import logging
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    StoryMemory,
)
from pipeline.analyze import (
    EXTRACTION_PROMPT,
    ExtractedCharacter,
    ExtractedDescription,
    ExtractedLocation,
    ExtractedObject,
    StoryAnalysis,
    analyze,
    extract_entities,
)


def test_extracted_description_requires_species():
    """Invariant 5 + ADR-028: an all-empty description makes `matches_description` vacuously
    true, collapsing the 3-draw re-roll to 1 draw with nobody noticing."""
    with pytest.raises(ValidationError):
        ExtractedDescription.model_validate({"colours": ["red"]})


def test_extracted_description_requires_no_visual_attribute():
    """Guards against someone later 'tightening' this into a Pydantic validator that fires
    AFTER a successful, paid call — under ADR-025 that fails the child's whole job because
    they never said what their dog was wearing. Spec §4."""
    assert ExtractedDescription(species="dog").species == "dog"


def test_extracted_description_inherits_every_contract_axis():
    """One source of truth for the axes — they are aligned to the FailureReason taxonomy
    the judge scores against, so re-deriving them here would fork it."""
    assert set(CharacterDescription.model_fields) <= set(ExtractedDescription.model_fields)


def test_contract_character_description_is_unchanged():
    """The boundary is strict; the contract stays a mostly-optional container (ADR-023)."""
    assert CharacterDescription().species is None
    assert Character(char_id="c0", name="x").description == CharacterDescription()


@pytest.mark.parametrize(
    ("model", "id_field"),
    [
        (ExtractedCharacter, "char_id"),
        (ExtractedLocation, "loc_id"),
        (ExtractedObject, "obj_id"),
    ],
)
def test_no_extraction_model_declares_an_id(model, id_field):
    """D-G: ids are minted node-side by list position; the LLM schema carries none."""
    assert id_field not in model.model_fields


def test_story_analysis_accepts_the_four_collections():
    analysis = StoryAnalysis.model_validate(
        {
            "characters": [{"name": "the narrator", "description": {"species": "girl"}}],
            "locations": [{"name": "the beach"}],
            "objects": [{"name": "a red bucket"}],
            "timeline": [{"order": 0, "summary": "They go to the beach."}],
        }
    )
    assert analysis.characters[0].description.species == "girl"
    assert analysis.locations[0].description is None
    assert analysis.timeline[0].summary == "They go to the beach."


def _analysis(**overrides) -> StoryAnalysis:
    """A minimal valid StoryAnalysis; override any collection per test."""
    return StoryAnalysis.model_validate(
        {
            "characters": [{"name": "the narrator", "description": {"species": "girl"}}],
            "locations": [{"name": "the beach"}],
            "objects": [{"name": "a red bucket"}],
            "timeline": [{"order": 0, "summary": "They go to the beach."}],
            **overrides,
        }
    )


def test_extract_entities_passes_the_text_and_schema_to_the_provider():
    with patch("pipeline.analyze.structured_text", return_value=_analysis()) as mock_provider:
        extract_entities("I went to the beach with my sister.")

    prompt, schema = mock_provider.call_args.args
    assert "I went to the beach with my sister." in prompt
    assert schema is StoryAnalysis


def test_extract_entities_returns_the_parsed_wrapper_unchanged():
    analysis = _analysis()
    with patch("pipeline.analyze.structured_text", return_value=analysis):
        assert extract_entities("I went to the beach.") is analysis


def test_extract_entities_does_not_name_a_model():
    """Model IDs are env-overridable settings in app/config.py; a call site never names one
    (AGENTS.md, ADR-015)."""
    with patch("pipeline.analyze.structured_text", return_value=_analysis()) as mock_provider:
        extract_entities("I went to the beach.")

    assert mock_provider.call_args.kwargs == {}
    assert len(mock_provider.call_args.args) == 2


def test_extract_entities_propagates_a_provider_failure():
    """ADR-025: a hard provider failure (including `message.parsed is None` on a self-refusal)
    raises → job `failed`. No node-level retry, never a partial roster."""
    with patch("pipeline.analyze.structured_text", side_effect=ValueError("no parsable output")):
        with pytest.raises(ValueError):
            extract_entities("A story about mild peril.")


def test_extraction_prompt_carries_the_three_asks():
    """The prompt string is the one artifact spec §4 states rules for but does not write, so
    a prompt that quietly drops an ask passes every other test in §6. Loose substring checks:
    rewording is fine, deleting an ask is not.

    - the <=3 character cap (belt-and-braces; the node is the real control)
    - the descriptive-label FALLBACK for a character the story never names
    - the always-answerable `species` ask that keeps ADR-028's re-roll from collapsing
    """
    prompt = EXTRACTION_PROMPT.lower()
    assert "3" in prompt
    assert "descriptive label" in prompt
    assert "species" in prompt


def test_extraction_prompt_prefers_the_name_the_story_gives():
    """A named character keeps their name; the descriptive label is the fallback, not the rule.

    Pseudonymization is the whole point of `providers.redact_pii` — it replaces "Jun" with a
    pool name ("Ana") specifically "so the story survives with a protagonist an illustrator can
    draw". This prompt then discarded that name and emitted "the narrator" for every protagonist
    the pipeline has ever produced. Two mechanisms, and the second negated the first.

    What reaches the book is a PSEUDONYM, never the child's real name: CC-2 is satisfied by
    `redact_pii` upstream, not by this prompt refusing proper nouns. That refusal was a second
    layer against a spaCy NER miss, and dropping it is the accepted cost (2026-08-11) of a book
    that calls its protagonist by name.
    """
    assert "never a proper noun" not in EXTRACTION_PROMPT
    assert "Use the name the story gives" in EXTRACTION_PROMPT


def test_extraction_prompt_still_forbids_redaction_placeholders():
    """The one token that must never reach a caption, whatever the naming rule is. A leaked
    `<PERSON_1>` is the failure `redact_pii` pseudonymizes to avoid in the first place, and
    prod job e94cc400 already proved placeholders reach captions when nothing forbids them.
    """
    assert "<PERSON_1>" in EXTRACTION_PROMPT
    assert "never" in EXTRACTION_PROMPT.lower()


def test_extract_entities_logs_the_extracted_counts(caplog):
    """CC-5: a wrong reference downstream traces back to a specific roster entry."""
    with caplog.at_level(logging.INFO, logger="pipeline.analyze"):
        with patch("pipeline.analyze.structured_text", return_value=_analysis()):
            extract_entities("I went to the beach.")

    assert "1 characters" in caplog.text


def _state(raw_text="A dog runs in a field.", redacted_text="A dog runs in a field.") -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw_text, redacted_text=redacted_text),
    )


def _character(name: str, species: str = "girl") -> dict:
    return {"name": name, "description": {"species": species}}


def test_analyze_mints_ids_by_list_position():
    analysis = _analysis(
        characters=[_character("the narrator"), _character("the younger sister")],
        locations=[{"name": "the beach"}, {"name": "the car"}],
        objects=[{"name": "a red bucket"}],
    )
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [c.char_id for c in result["characters"]] == ["c0", "c1"]
    assert [loc.loc_id for loc in result["locations"]] == ["loc0", "loc1"]
    assert [o.obj_id for o in result["objects"]] == ["obj0"]


def test_analyze_caps_characters_at_three_keeping_the_first_three():
    """Invariant 1. Prominence survives the cut — index 0 is the protagonist. The prompt also
    asks for <=3, so this is belt-and-braces; the node is the control (spec §4)."""
    names = ["first", "second", "third", "fourth", "fifth"]
    analysis = _analysis(characters=[_character(n) for n in names])
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [c.name for c in result["characters"]] == ["first", "second", "third"]
    assert [c.char_id for c in result["characters"]] == ["c0", "c1", "c2"]


@pytest.mark.parametrize("model_orders", [[1, 2, 5], [0, 0, 0], [3, 1, 2]])
def test_analyze_reindexes_timeline_order_from_list_position(model_orders):
    """Invariant 4. Gapped or duplicated `order` values validate fine against Pydantic and
    would silently corrupt the only ordering `segment` receives."""
    analysis = _analysis(
        timeline=[{"order": o, "summary": f"event {i}"} for i, o in enumerate(model_orders)]
    )
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [e.order for e in result["timeline"]] == [0, 1, 2]
    assert [e.summary for e in result["timeline"]] == ["event 0", "event 1", "event 2"]


def test_analyze_accepts_an_empty_roster_without_raising():
    """CC-9: an empty roster is valid, not a failure. `char_bible` mints no references and
    scenes generate unreferenced — a book with drifting art beats no book (ADR-010)."""
    analysis = _analysis(characters=[], timeline=[])
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert result["characters"] == []
    assert result["timeline"] == []
    assert [loc.loc_id for loc in result["locations"]] == ["loc0"]


def test_analyze_prefers_redacted_text():
    """CC-2: `redacted_text` is what downstream nodes consume."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()) as mock_extract:
        analyze(_state(raw_text="raw version", redacted_text="redacted version"))

    assert mock_extract.call_args.args[0] == "redacted version"


def test_analyze_falls_back_to_raw_text():
    """The same fallback `segment` already uses — `input_gate` is a pass-through stub today."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()) as mock_extract:
        analyze(_state(raw_text="raw version", redacted_text=None))

    assert mock_extract.call_args.args[0] == "raw version"


def test_analyze_partial_returns_exactly_four_keys_and_does_not_mutate_state():
    """ADR-024: nodes partial-return; they never mutate `state`."""
    state = _state()
    before = state.model_dump()
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()):
        result = analyze(state)

    assert set(result) == {"characters", "locations", "objects", "timeline"}
    assert state.model_dump() == before


def test_analyze_persists_the_contract_type_not_the_strict_subclass():
    """What is persisted is exactly `CharacterDescription`, never `ExtractedDescription` —
    the strictness is a boundary concern and must not leak into the checkpoint."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()):
        result = analyze(_state())

    description = result["characters"][0].description
    assert type(description) is CharacterDescription
    assert description.species == "girl"


def test_analyze_logs_the_minted_ids(caplog):
    """CC-5: a wrong reference downstream traces back to a specific roster entry."""
    analysis = _analysis(characters=[_character("the narrator"), _character("the cat", "cat")])
    with caplog.at_level(logging.INFO, logger="pipeline.analyze"):
        with patch("pipeline.analyze.extract_entities", return_value=analysis):
            analyze(_state())

    assert "c0" in caplog.text
    assert "c1" in caplog.text
