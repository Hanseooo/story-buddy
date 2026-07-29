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
    SceneCaption,
    StoryAnalysis,
    analyze,
    caption_for,
    extract_entities,
)


def test_scene_caption_accepts_valid_shape():
    result = SceneCaption.model_validate({"caption": "A dog runs through a sunny field."})
    assert result.caption == "A dog runs through a sunny field."


def test_scene_caption_rejects_missing_field():
    with pytest.raises(ValidationError):
        SceneCaption.model_validate({})


def test_caption_for_returns_validated_caption():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="A dog runs through a sunny field."),
    ):
        caption = caption_for("A dog runs in a field.")

    assert caption == "A dog runs through a sunny field."


def test_caption_for_passes_the_schema_to_the_provider():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="x"),
    ) as mock_structured_text:
        caption_for("A dog runs in a field.")

    prompt, schema = mock_structured_text.call_args.args
    assert "A dog runs in a field." in prompt
    assert schema is SceneCaption


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


def test_analyze_is_a_pass_through_stub():
    """`analyze`'s real content is the story-analyzer spec, deliberately not started
    (DECISION_BACKLOG). It owns `caption_for` (D-F) but writes no state — `segment` owns
    scenes[].caption per MASTER_SPEC §2's node-I/O table."""
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field.", redacted_text="A dog runs in a field."),
    )
    assert analyze(state) == {}


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
    - the short-descriptive-label rule, so no proper noun or `<PERSON_1>` reaches a prompt
    - the always-answerable `species` ask that keeps ADR-028's re-roll from collapsing
    """
    prompt = EXTRACTION_PROMPT.lower()
    assert "3" in prompt
    assert "descriptive label" in prompt
    assert "species" in prompt


def test_extract_entities_logs_the_extracted_counts(caplog):
    """CC-5: a wrong reference downstream traces back to a specific roster entry."""
    with caplog.at_level(logging.INFO, logger="pipeline.analyze"):
        with patch("pipeline.analyze.structured_text", return_value=_analysis()):
            extract_entities("I went to the beach.")

    assert "1 characters" in caplog.text
