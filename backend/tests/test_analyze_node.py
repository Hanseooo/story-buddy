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
    ExtractedCharacter,
    ExtractedDescription,
    ExtractedLocation,
    ExtractedObject,
    SceneCaption,
    StoryAnalysis,
    analyze,
    caption_for,
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
