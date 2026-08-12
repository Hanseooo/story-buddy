"""Deterministic contract tests (spec §6). Pure schema — no model calls, no graph."""
import pytest
from pydantic import ValidationError

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    Cost,
    Input,
    RefVerdict,
    ReferenceRetry,
    Scene,
    StoryMemory,
    VlmVerdict,
    upsert_scenes,
)


def _minimal() -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )


def _populated() -> StoryMemory:
    sm = _minimal()
    sm.characters.append(
        Character(
            char_id="c0",
            name="Rex",
            canonical_ref_image="job-1/ref-c0.png",
            ref_verdict=RefVerdict(differences_observed="none", matches_description=True),
        )
    )
    sm.scenes.append(
        Scene(
            scene_id="s0",
            text_excerpt="A dog runs in a field.",
            caption="A happy dog runs.",
            characters_present=["c0"],
            attempts=[
                Attempt(
                    image_ref="job-1/scene-1.png",
                    prompt="A happy dog runs.",
                    vlm_verdict=VlmVerdict(differences_observed="none", same_character=True),
                    failure_reasons=["wrong_colour"],
                    passed=True,
                )
            ],
            final_image_ref="job-1/scene-1.png",
        )
    )
    return sm


def test_populated_story_memory_round_trips():
    sm = _populated()
    assert StoryMemory(**sm.model_dump()) == sm


def test_minimal_story_memory_validates():
    """Proves the mostly-optional container (ADR-023, Consequences)."""
    sm = _minimal()
    assert sm.scenes == []
    assert sm.characters == []


def test_schema_version_is_required():
    """No default, deliberately: a checkpoint missing the key must NOT deserialize as current."""
    data = _minimal().model_dump()
    del data["schema_version"]
    with pytest.raises(ValidationError):
        StoryMemory(**data)


def test_schema_version_survives_model_dump():
    assert _minimal().model_dump()["schema_version"] == CURRENT_SCHEMA_VERSION


def test_upsert_keeps_a_replaced_scene_in_its_original_slot():
    """Scene list order is the contract — the ADR-024 loop and page sequence both rely on it."""
    current = [Scene(scene_id=f"s{i}", text_excerpt=str(i)) for i in range(3)]
    updated = Scene(scene_id="s1", text_excerpt="1", final_image_ref="p.png")
    result = upsert_scenes(current, [updated])

    assert [s.scene_id for s in result] == ["s0", "s1", "s2"]
    assert result[1].final_image_ref == "p.png"


def test_upsert_appends_a_new_scene_id():
    current = [Scene(scene_id="s0", text_excerpt="0")]
    result = upsert_scenes(current, [Scene(scene_id="s1", text_excerpt="1")])
    assert [s.scene_id for s in result] == ["s0", "s1"]


def test_vlm_verdict_declares_reason_before_score():
    """ADR-004: the judge must reason before it scores. Declaration order only —
    runtime enforcement is providers._assert_field_order, tested in test_providers.py."""
    props = list(VlmVerdict.model_json_schema()["properties"])
    assert props.index("differences_observed") < props.index("same_character")


def test_anatomy_intact_is_declared_after_style_match():
    """ADR-028: appended after style_match so the ADR-004 ordering above is untouched."""
    fields = list(VlmVerdict.model_fields)
    assert fields.index("anatomy_intact") > fields.index("style_match")



def test_ref_verdict_declares_reason_before_score():
    """ADR-004 applies to every judge call, not only the two-image one.

    ADR-034 put the real gate — `contradictions` — BETWEEN the two, so the judge must enumerate
    the defects before it scores. `providers._assert_field_order` enforces this on the wire; the
    schema order it checks against is this one, so moving a field here silently moves the wire
    contract with it.
    """
    props = list(RefVerdict.model_json_schema()["properties"])
    assert props.index("differences_observed") < props.index("contradictions")
    assert props.index("contradictions") < props.index("matches_description")


def test_failure_reason_is_a_closed_set():
    with pytest.raises(ValidationError):
        Attempt(image_ref="p.png", failure_reasons=["not_a_real_reason"])


def test_asset_fields_accept_a_plain_storage_path():
    """CC-4: durable paths, never signed URLs. Documented by convention, not type-enforced —
    this asserts nothing rejects a path."""
    scene = Scene(scene_id="s0", text_excerpt="x", final_image_ref="job-1/scene-1.png")
    assert scene.final_image_ref == "job-1/scene-1.png"


def test_cost_ref_retry_count_defaults_to_zero():
    assert Cost().ref_retry_count == 0


def test_story_memory_defaults_reference_retry_to_none():
    assert _minimal().reference_retry is None


def test_reference_retry_round_trips_on_story_memory():
    sm = _minimal()
    sm.reference_retry = ReferenceRetry(char_id="c0", attribute="orange sock")
    assert StoryMemory(**sm.model_dump()) == sm


def test_reference_retry_requires_char_id_and_attribute():
    with pytest.raises(ValidationError):
        ReferenceRetry()


# --- scene-setting-and-subject-binding §2: two additive fields, no schema_version bump ---

def test_scene_location_id_defaults_to_none():
    """Set by `segment`, consumed by `build_prompt`. A story that names no location leaves it
    None on every scene, which is byte-identical to today's behaviour."""
    assert Scene(scene_id="s0", text_excerpt="x").location_id is None


def test_vlm_verdict_subjects_unique_defaults_to_true():
    """CC-10: a scene judged BEFORE this change reads as non-duplicated. Same shape
    `anatomy_intact` had at its own introduction."""
    assert VlmVerdict(differences_observed="d", same_character=True).subjects_unique is True


def test_vlm_verdict_declares_subjects_unique_last():
    """ADR-004's reason-then-score order is enforced on the wire by
    `providers._assert_field_order`. The new field is appended; nothing above it moves."""
    assert list(VlmVerdict.model_fields) == [
        "differences_observed",
        "same_character",
        "attributes_present",
        "style_match",
        "anatomy_intact",
        "subjects_unique",
    ]


def test_a_checkpoint_blob_written_before_this_change_still_deserializes():
    """§6 test 22 / CC-10: both fields are additive with defaults, so a checkpoint that predates
    them resumes with the documented values rather than raising."""
    blob = _minimal().model_dump()
    blob["scenes"] = [
        {
            "scene_id": "s0",
            "text_excerpt": "x",
            "attempts": [
                {
                    "image_ref": "job-1/s0-1.png",
                    "vlm_verdict": {"differences_observed": "d", "same_character": True},
                }
            ],
        }
    ]

    restored = StoryMemory.model_validate(blob)

    assert restored.scenes[0].location_id is None
    assert restored.scenes[0].attempts[0].vlm_verdict.subjects_unique is True


def test_the_two_additive_fields_do_not_bump_the_schema_version():
    """§2: `story-memory-contract.md` §8 permits additive defaulted fields without a bump."""
    assert CURRENT_SCHEMA_VERSION == 1

