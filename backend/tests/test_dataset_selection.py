"""Tests for finetune.dataset_selection artifact loading and validation."""
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    Scene,
    StoryMemory,
)
from finetune.corpus_io import (
    AssetRecord,
    IntakeRecord,
    RunBundle,
    intake_sha256,
)
from finetune.dataset_selection import (
    DatasetSelection,
    DonatedReplacement,
    HardNegativeMatch,
    candidate_report,
    load_dataset_selection,
    prepare_dataset_bundles,
    select_dataset_bundles,
    selection_sha256,
    validate_hard_negative_matches,
)
from finetune.manifest import ManifestError

VALID_SELECTION = {
    "hard_negatives_frozen_at": "2026-08-24T10:00:00+08:00",
    "hard_negative_matches": [
        {"reference_char_id": "syn-001:c0", "target_char_id": "syn-007:c0"}
    ],
    "donated_replacements": [
        {
            "primary_story_id": "don-001",
            "backup_story_id": "don-011",
            "reason": "withdrawal",
            "approved_at": "2026-08-24T11:00:00+08:00",
            "evidence_ref": "restricted-record-017",
        }
    ],
}


def write_selection(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "dataset_selection.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_load_valid_selection(tmp_path):
    path = write_selection(tmp_path, VALID_SELECTION)
    loaded = load_dataset_selection(path)
    assert len(loaded.hard_negative_matches) == 1
    assert len(loaded.donated_replacements) == 1
    assert loaded.hard_negative_matches[0].reference_char_id == "syn-001:c0"
    assert loaded.donated_replacements[0].reason == "withdrawal"
    assert selection_sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_selection_rejects_unknown_fields():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["extra_field"] = "not_allowed"
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)

    payload = copy.deepcopy(VALID_SELECTION)
    payload["hard_negative_matches"][0]["extra"] = "bad"
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)

    payload = copy.deepcopy(VALID_SELECTION)
    payload["donated_replacements"][0]["extra"] = "bad"
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)


@pytest.mark.parametrize("field", ["hard_negatives_frozen_at", "approved_at"])
def test_selection_rejects_naive_timestamp(field):
    payload = copy.deepcopy(VALID_SELECTION)
    if field == "hard_negatives_frozen_at":
        payload["hard_negatives_frozen_at"] = "2026-08-24T10:00:00"
    else:
        payload["donated_replacements"][0]["approved_at"] = "2026-08-24T11:00:00"
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)


@pytest.mark.parametrize("field", ["hard_negatives_frozen_at", "approved_at"])
def test_selection_rejects_future_timestamp(field):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = copy.deepcopy(VALID_SELECTION)
    if field == "hard_negatives_frozen_at":
        payload["hard_negatives_frozen_at"] = future
    else:
        payload["donated_replacements"][0]["approved_at"] = future
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)


def test_selection_rejects_duplicate_reference_mappings():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["hard_negative_matches"].append(
        {"reference_char_id": "syn-001:c0", "target_char_id": "syn-008:c0"}
    )
    with pytest.raises(ValidationError, match="duplicate reference_char_id"):
        DatasetSelection.model_validate(payload)


def test_selection_rejects_self_pairs():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["hard_negative_matches"] = [
        {"reference_char_id": "syn-001:c0", "target_char_id": "syn-001:c0"}
    ]
    with pytest.raises(ValidationError, match="self"):
        DatasetSelection.model_validate(payload)


def test_selection_rejects_duplicate_primary_replacement():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["donated_replacements"].append(
        {
            "primary_story_id": "don-001",
            "backup_story_id": "don-012",
            "reason": "withdrawal",
            "approved_at": "2026-08-24T11:00:00+08:00",
            "evidence_ref": "restricted-record-018",
        }
    )
    with pytest.raises(ValidationError, match="duplicate primary_story_id"):
        DatasetSelection.model_validate(payload)


def test_selection_rejects_reused_backup():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["donated_replacements"].append(
        {
            "primary_story_id": "don-002",
            "backup_story_id": "don-011",
            "reason": "withdrawal",
            "approved_at": "2026-08-24T11:00:00+08:00",
            "evidence_ref": "restricted-record-018",
        }
    )
    with pytest.raises(ValidationError, match="reused backup_story_id"):
        DatasetSelection.model_validate(payload)


def test_selection_rejects_invalid_reason():
    payload = copy.deepcopy(VALID_SELECTION)
    payload["donated_replacements"][0]["reason"] = "unsupported_reason"
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)


@pytest.mark.parametrize("blank_evidence", ["", "   ", "\t\n"])
def test_selection_rejects_blank_evidence(blank_evidence):
    payload = copy.deepcopy(VALID_SELECTION)
    payload["donated_replacements"][0]["evidence_ref"] = blank_evidence
    with pytest.raises(ValidationError):
        DatasetSelection.model_validate(payload)


# --- Helper fixture builders for bundles and intake ---


def make_bundle(
    story_id: str,
    char_id: str,
    *,
    species: str = "fox",
    style: str = "cel",
    split: str = "train",
    provenance: str = "synthetic",
    role: str = "not_applicable",
    fixture: bool = False,
    intake_hash: str | None = None,
    num_scenes: int = 1,
) -> RunBundle:
    character = Character(
        char_id=char_id,
        name=f"Char {char_id}",
        description=CharacterDescription(
            species=species,
            is_humanoid=False,
            colours=["orange"],
            body_features=["bushy tail"],
            clothing=["scarf"],
        ),
        canonical_ref_image=f"{story_id}/ref.png",
    )
    scenes = [
        Scene(
            scene_id=f"s{i}",
            text_excerpt=f"Scene {i}",
            prompt="Prompt",
            characters_present=[char_id],
            final_image_ref=f"{story_id}/scene-{i}.webp",
        )
        for i in range(num_scenes)
    ]
    memory = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=story_id,
        classroom_id="test-class",
        profile_id="test-profile",
        input=Input(raw_text="A story text."),
        characters=[character],
        scenes=scenes,
    )
    metadata: dict[str, str | int | float | bool] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "style_preset_id": style,
    }
    if fixture:
        metadata["fixture"] = True
    if intake_hash is not None:
        metadata["intake_sha256"] = intake_hash

    assets = [
        AssetRecord(
            storage_path=f"{story_id}/ref.png",
            local_path=f"ref/{story_id}_ref.png",
            sha256="r" * 64,
            mime_type="image/png",
            width=1,
            height=1,
            byte_length=1,
            kind="ref",
        ),
        *(
            AssetRecord(
                storage_path=f"{story_id}/scene-{i}.webp",
                local_path=f"scene/{story_id}_scene-{i}.webp",
                sha256=f"s{i}" * 32,
                mime_type="image/webp",
                width=1,
                height=1,
                byte_length=1,
                kind="scene",
            )
            for i in range(num_scenes)
        ),
    ]
    return RunBundle(
        memory=memory,
        provenance=provenance,  # type: ignore[arg-type]
        split=split,  # type: ignore[arg-type]
        candidate_role=role,  # type: ignore[arg-type]
        run_metadata=metadata,  # type: ignore[arg-type]
        assets=assets,
    )


def test_candidate_report_lists_only_same_species_style_candidates():
    report = candidate_report([
        make_bundle("syn-a", "a", species="fox", style="cel", split="train"),
        make_bundle("syn-b", "b", species="fox", style="cel", split="train"),
        make_bundle("syn-c", "c", species="bear", style="cel", split="train"),
        make_bundle("syn-d", "d", species="fox", style="gouache", split="train"),
        make_bundle("syn-e", "e", species="fox", style="cel", split="val"),
    ])
    row = next(item for item in report if item["reference_char_id"] == "syn-a:a")
    assert row["reference_image"] == "syn-a/ref.png"
    assert row["species"] == "fox"
    assert row["style"] == "cel"
    assert [item["target_char_id"] for item in row["candidates"]] == ["syn-b:b"]
    assert row["candidates"][0]["scene_count"] == 1
    # val character should not appear as reference row in train candidate report
    assert not any(item["reference_char_id"] == "syn-e:e" for item in report)


def sample_intakes_and_bundles():
    # 2 synthetic train records
    syn_intakes = [
        IntakeRecord.model_validate({
            "story_id": "syn-001",
            "text": "Story 1",
            "declared_characters": ["Char a"],
            "declared_non_human": ["Char a"],
            "provenance": "synthetic",
            "split": "train",
            "candidate_role": "not_applicable",
            "style_preset_id": "cel",
        }),
        IntakeRecord.model_validate({
            "story_id": "syn-002",
            "text": "Story 2",
            "declared_characters": ["Char b"],
            "declared_non_human": ["Char b"],
            "provenance": "synthetic",
            "split": "train",
            "candidate_role": "not_applicable",
            "style_preset_id": "cel",
        }),
    ]
    syn_bundles = [
        make_bundle(
            "syn-001", "a", species="fox", style="cel", split="train",
            intake_hash=intake_sha256(syn_intakes[0]),
        ).model_copy(update={
            "declared_characters": syn_intakes[0].declared_characters,
            "declared_non_human": syn_intakes[0].declared_non_human,
        }),
        make_bundle(
            "syn-002", "b", species="fox", style="cel", split="train",
            intake_hash=intake_sha256(syn_intakes[1]),
        ).model_copy(update={
            "declared_characters": syn_intakes[1].declared_characters,
            "declared_non_human": syn_intakes[1].declared_non_human,
        }),
    ]

    # 15 donated records
    # 4 gouache primary, 3 cel primary, 3 cut_paper primary, 1 gouache backup, 2 cel backup, 2 cut_paper backup
    styles_and_roles = [
        *(("gouache", "primary") for _ in range(4)),
        *(("cel", "primary") for _ in range(3)),
        *(("cut_paper", "primary") for _ in range(3)),
        ("gouache", "backup"),
        *(("cel", "backup") for _ in range(2)),
        *(("cut_paper", "backup") for _ in range(2)),
    ]
    don_intakes = [
        IntakeRecord.model_validate({
            "story_id": f"don-{i:03d}",
            "text": f"Donated story {i}",
            "declared_characters": [f"Char c{i}"],
            "declared_non_human": [f"Char c{i}"],
            "provenance": "donated",
            "split": "test",
            "candidate_role": role,
            "style_preset_id": style,
            "guardian_consent": True,
            "child_assent": True,
            "manual_pii_redaction": True,
            "independent_redaction_review": True,
            "withdrawal_state": "active",
            "selection_frozen_at": "2026-08-24T00:00:00Z",
        })
        for i, (style, role) in enumerate(styles_and_roles, start=1)
    ]
    don_bundles = [
        make_bundle(
            f"don-{i:03d}",
            f"c{i}",
            species="cat",
            style=style,
            split="test",
            provenance="donated",
            role=role,
            intake_hash=intake_sha256(don_intakes[i - 1]),
        ).model_copy(update={
            "declared_characters": don_intakes[i - 1].declared_characters,
            "declared_non_human": don_intakes[i - 1].declared_non_human,
        })
        for i, (style, role) in enumerate(styles_and_roles, start=1)
    ]

    return syn_intakes, syn_bundles, don_intakes, don_bundles


def test_select_dataset_bundles_default_primaries():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    all_bundles = syn_bundles + don_bundles
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[],
    )
    selected, audit = select_dataset_bundles(
        all_bundles, syn_intakes, don_intakes, selection, "selection-hash-123"
    )

    # 2 synthetic + 10 primary donated = 12
    assert len(selected) == 12
    selected_don_ids = [b.memory.story_id for b in selected if b.provenance == "donated"]
    assert len(selected_don_ids) == 10
    assert audit.selected_donated_stories == sorted(selected_don_ids)
    assert len(audit.excluded_donated_stories) == 5
    assert audit.selection_sha256 == "selection-hash-123"
    assert audit.replacement_reasons == {}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provenance", "synthetic"),
        ("split", "train"),
        ("candidate_role", "backup"),
        ("declared_characters", ["Drifted character"]),
        ("declared_non_human", ["Drifted character"]),
    ],
)
def test_select_dataset_bundles_rejects_bundle_metadata_drift(field, value):
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    don_bundles[0] = don_bundles[0].model_copy(update={field: value})

    with pytest.raises(ManifestError, match=f"{field} differs from intake"):
        select_dataset_bundles(
            syn_bundles + don_bundles,
            syn_intakes,
            don_intakes,
            DatasetSelection(
                hard_negatives_frozen_at=datetime.now(timezone.utc),
                hard_negative_matches=[],
                donated_replacements=[],
            ),
            "sel-hash",
        )


def test_select_dataset_bundles_rejects_bundle_style_drift():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    metadata = {**don_bundles[0].run_metadata, "style_preset_id": "cel"}
    don_bundles[0] = don_bundles[0].model_copy(update={"run_metadata": metadata})

    with pytest.raises(ManifestError, match="style_preset_id differs from intake"):
        select_dataset_bundles(
            syn_bundles + don_bundles,
            syn_intakes,
            don_intakes,
            DatasetSelection(
                hard_negatives_frozen_at=datetime.now(timezone.utc),
                hard_negative_matches=[],
                donated_replacements=[],
            ),
            "sel-hash",
        )


def test_select_dataset_bundles_with_valid_backup_replacement():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    # don-005 is cel primary. don-012 is cel backup.
    don_intakes[4] = don_intakes[4].model_copy(update={"withdrawal_state": "withdrawn"})
    all_bundles = syn_bundles + don_bundles
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[
            DonatedReplacement(
                primary_story_id="don-005",
                backup_story_id="don-012",
                reason="withdrawal",
                approved_at=datetime.now(timezone.utc),
                evidence_ref="doc-123",
            )
        ],
    )
    selected, audit = select_dataset_bundles(
        all_bundles, syn_intakes, don_intakes, selection, "sel-hash"
    )
    selected_don_ids = [b.memory.story_id for b in selected if b.provenance == "donated"]
    assert "don-005" not in selected_don_ids
    assert "don-012" in selected_don_ids
    assert len(selected_don_ids) == 10
    assert audit.replacement_reasons == {"don-005": "withdrawal"}
    assert "don-005" in audit.excluded_donated_stories


def test_select_dataset_bundles_rejects_withdrawal_replacement_for_active_primary():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[
            DonatedReplacement(
                primary_story_id="don-005",
                backup_story_id="don-012",
                reason="withdrawal",
                approved_at=datetime.now(timezone.utc),
                evidence_ref="doc-123",
            )
        ],
    )

    with pytest.raises(ManifestError, match="withdrawal replacement primary don-005 is active"):
        select_dataset_bundles(
            syn_bundles + don_bundles, syn_intakes, don_intakes, selection, "sel-hash"
        )


def test_select_dataset_bundles_rejects_withdrawn_primary_without_replacement():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    # Mark don-001 withdrawn in intake
    don_intakes[0] = don_intakes[0].model_copy(update={"withdrawal_state": "withdrawn"})
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="withdrawn"):
        select_dataset_bundles(
            syn_bundles + don_bundles, syn_intakes, don_intakes, selection, "sel-hash"
        )


def test_select_dataset_bundles_rejects_withdrawn_backup():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    # don-005 is the withdrawn cel primary; don-012 is a withdrawn cel backup.
    don_intakes[4] = don_intakes[4].model_copy(update={"withdrawal_state": "withdrawn"})
    don_intakes[11] = don_intakes[11].model_copy(update={"withdrawal_state": "withdrawn"})
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[
            DonatedReplacement(
                primary_story_id="don-005",
                backup_story_id="don-012",
                reason="withdrawal",
                approved_at=datetime.now(timezone.utc),
                evidence_ref="doc-123",
            )
        ],
    )
    with pytest.raises(ManifestError, match="withdrawn"):
        select_dataset_bundles(
            syn_bundles + don_bundles, syn_intakes, don_intakes, selection, "sel-hash"
        )


def test_select_dataset_bundles_rejects_cross_style_replacement():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    # don-001 is gouache primary, don-012 is cel backup
    don_intakes[0] = don_intakes[0].model_copy(update={"withdrawal_state": "withdrawn"})
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[
            DonatedReplacement(
                primary_story_id="don-001",
                backup_story_id="don-012",
                reason="withdrawal",
                approved_at=datetime.now(timezone.utc),
                evidence_ref="doc-123",
            )
        ],
    )
    with pytest.raises(ManifestError, match="style"):
        select_dataset_bundles(
            syn_bundles + don_bundles, syn_intakes, don_intakes, selection, "sel-hash"
        )


def test_select_dataset_bundles_rejects_intake_hash_mismatch():
    syn_intakes, syn_bundles, don_intakes, don_bundles = sample_intakes_and_bundles()
    # Corrupt intake hash in bundle metadata
    syn_bundles[0].run_metadata["intake_sha256"] = "wrong-hash"
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="intake_sha256"):
        select_dataset_bundles(
            syn_bundles + don_bundles, syn_intakes, don_intakes, selection, "sel-hash"
        )


def test_prepare_dataset_bundles_all_fixtures():
    fixtures = [
        make_bundle("fix-001", "a", fixture=True),
        make_bundle("fix-002", "b", fixture=True),
    ]
    selected, sel, audit = prepare_dataset_bundles(fixtures, None, None)
    assert len(selected) == 2
    assert sel is None
    assert audit.selection_sha256 is None


def test_prepare_dataset_bundles_mixed_fixture_fails():
    mixed = [
        make_bundle("fix-001", "a", fixture=True),
        make_bundle("syn-001", "b", fixture=False),
    ]
    with pytest.raises(ManifestError, match="mixed fixture"):
        prepare_dataset_bundles(mixed, None, None)


# --- validate_hard_negative_matches tests ---

def test_validate_hard_negative_matches_success():
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train"),
        make_bundle("syn-002", "c2", species="fox", style="cel", split="train"),
    ]
    frozen_at = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    selection = DatasetSelection(
        hard_negatives_frozen_at=frozen_at,
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    annotations = [
        {"pair_id": "p1", "created_at": "2026-08-24T11:00:00+00:00"},
        {"pair_id": "pilot-1", "created_at": "2026-08-24T09:00:00+00:00"},  # pilot ignored
    ]
    matches = validate_hard_negative_matches(bundles, selection, annotations, {"pilot-1"})
    assert matches == {
        "syn-001:c1": "syn-002:c2",
        "syn-002:c2": "syn-001:c1",
    }


def test_validate_hard_negative_matches_allows_partial_coverage():
    # ADR-057: coverage is best-effort. syn-002:c2 carries no hard negative and that is legal.
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train"),
        make_bundle("syn-002", "c2", species="fox", style="cel", split="train"),
    ]
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
        ],
        donated_replacements=[],
    )
    matches = validate_hard_negative_matches(bundles, selection, [], set())
    assert matches == {"syn-001:c1": "syn-002:c2"}


def test_validate_hard_negative_matches_rejects_excess_reference():
    # ADR-057: the membership check is the only guard on a reference outside the train split.
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train"),
        make_bundle("syn-002", "c2", species="fox", style="cel", split="train"),
        make_bundle("syn-003", "c3", species="fox", style="cel", split="val"),
    ]
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
            HardNegativeMatch(reference_char_id="syn-003:c3", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="reference character syn-003:c3"):
        validate_hard_negative_matches(bundles, selection, [], set())


def test_validate_hard_negative_matches_rejects_species_or_style_mismatch():
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train"),
        make_bundle("syn-002", "c2", species="bear", style="cel", split="train"),
        make_bundle("syn-003", "c3", species="fox", style="gouache", split="train"),
    ]
    # Species mismatch
    selection_species = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
            HardNegativeMatch(reference_char_id="syn-003:c3", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="species"):
        validate_hard_negative_matches(bundles, selection_species, [], set())

    # Style mismatch
    selection_style = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-003:c3"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
            HardNegativeMatch(reference_char_id="syn-003:c3", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="style"):
        validate_hard_negative_matches(bundles, selection_style, [], set())


def test_validate_hard_negative_matches_rejects_target_without_natural_scenes():
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train", num_scenes=1),
        make_bundle("syn-002", "c2", species="fox", style="cel", split="train", num_scenes=0),
    ]
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc),
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    with pytest.raises(ManifestError, match="natural scenes"):
        validate_hard_negative_matches(bundles, selection, [], set())


@pytest.mark.parametrize(
    "created_at",
    ["2026-08-24T11:59:59+00:00", "2026-08-24T12:00:00+00:00"],
)
def test_validate_hard_negative_matches_rejects_annotation_not_after_freeze(created_at):
    bundles = [
        make_bundle("syn-001", "c1", species="fox", style="cel", split="train"),
        make_bundle("syn-002", "c2", species="fox", style="cel", split="train"),
    ]
    frozen_at = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    selection = DatasetSelection(
        hard_negatives_frozen_at=frozen_at,
        hard_negative_matches=[
            HardNegativeMatch(reference_char_id="syn-001:c1", target_char_id="syn-002:c2"),
            HardNegativeMatch(reference_char_id="syn-002:c2", target_char_id="syn-001:c1"),
        ],
        donated_replacements=[],
    )
    annotations = [
        {"pair_id": "p1", "created_at": created_at},
    ]
    with pytest.raises(ManifestError, match="precede"):
        validate_hard_negative_matches(bundles, selection, annotations, set())
