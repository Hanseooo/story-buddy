"""Sanitized corpus intake contract (research-corpus-operations §4.1)."""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from finetune.corpus_io import (
    AssetRecord,
    CorpusError,
    IntakeRecord,
    RunBundle,
    load_completed_bundles,
    load_intake,
    write_bundle,
)


CORPUS_PATH = Path(__file__).parents[1] / "finetune" / "corpus_synthetic.json"
APPROVAL_FIELDS = (
    "guardian_consent",
    "child_assent",
    "manual_pii_redaction",
    "independent_redaction_review",
)


def synthetic_record(**changes):
    record = {
        "story_id": "syn-001",
        "text": "A redacted fictional story.",
        "declared_characters": ["Quill"],
        "declared_non_human": ["Quill"],
        "provenance": "synthetic",
        "split": "train",
        "candidate_role": "not_applicable",
        "style_preset_id": "cel",
    }
    record.update(changes)
    return record


def donated_record(**changes):
    record = {
        "story_id": "don-001",
        "text": "A manually redacted donated story.",
        "declared_characters": ["Moss"],
        "declared_non_human": ["Moss"],
        "provenance": "donated",
        "split": "test",
        "candidate_role": "primary",
        "style_preset_id": "gouache",
        "guardian_consent": True,
        "child_assent": True,
        "manual_pii_redaction": True,
        "independent_redaction_review": True,
        "withdrawal_state": "active",
        "selection_frozen_at": "2026-08-01T00:00:00Z",
    }
    record.update(changes)
    return record


def write_intake(tmp_path, records):
    path = tmp_path / "intake.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


@pytest.mark.parametrize("field", APPROVAL_FIELDS)
@pytest.mark.parametrize("missing", [True, False])
def test_donated_record_requires_each_affirmative_approval(field, missing):
    record = donated_record(**({} if missing else {field: False}))
    if missing:
        record.pop(field)

    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(record)


@pytest.mark.parametrize("split", ["train", "val"])
def test_donated_record_is_held_out_test_only(split):
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(donated_record(split=split))


def test_synthetic_record_cannot_be_test_data():
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(split="test"))


def test_load_intake_rejects_duplicate_story_ids(tmp_path):
    with pytest.raises(ValueError, match="duplicate story_id"):
        load_intake(write_intake(tmp_path, [synthetic_record(), synthetic_record()]))


def test_load_intake_rejects_mixed_synthetic_and_donated_provenance(tmp_path):
    with pytest.raises(ValueError, match="one provenance"):
        load_intake(write_intake(tmp_path, [synthetic_record(), donated_record()]))


def test_intake_record_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(receipt_code="never-here"))


def test_intake_record_rejects_blank_text():
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(text=" \n\t "))


def test_donated_record_rejects_withdrawal_before_generation():
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(donated_record(withdrawal_state="withdrawn"))


@pytest.mark.parametrize("style", ["comic", "watercolor"])
def test_intake_record_rejects_non_selectable_style(style):
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(style_preset_id=style))


def test_declared_non_human_must_be_declared_characters():
    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(declared_non_human=["Unlisted"]))


@pytest.mark.parametrize("field", (*APPROVAL_FIELDS, "withdrawal_state", "selection_frozen_at"))
def test_synthetic_record_cannot_carry_donated_only_fields(field):
    value = "active" if field == "withdrawal_state" else True
    if field == "selection_frozen_at":
        value = "2026-08-01T00:00:00Z"

    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(synthetic_record(**{field: value}))


@pytest.mark.parametrize("candidate_role", ["primary", "backup"])
def test_donated_selection_freeze_must_be_completed(candidate_role):
    future = datetime.now(timezone.utc) + timedelta(minutes=1)

    with pytest.raises(ValidationError):
        IntakeRecord.model_validate(
            donated_record(candidate_role=candidate_role, selection_frozen_at=future.isoformat())
        )


def test_synthetic_corpus_has_the_frozen_split_and_style_allocation():
    records = load_intake(CORPUS_PATH)

    assert Counter(record.split for record in records) == {"train": 24, "val": 6}
    assert Counter((record.style_preset_id, record.split) for record in records) == {
        ("cel", "train"): 8,
        ("cel", "val"): 2,
        ("gouache", "train"): 8,
        ("gouache", "val"): 2,
        ("cut_paper", "train"): 8,
        ("cut_paper", "val"): 2,
    }


def donated_candidates():
    styles_and_roles = [
        *(("gouache", "primary") for _ in range(4)),
        *(("cel", "primary") for _ in range(3)),
        *(("cut_paper", "primary") for _ in range(3)),
        ("gouache", "backup"),
        *(("cel", "backup") for _ in range(2)),
        *(("cut_paper", "backup") for _ in range(2)),
    ]
    return [
        donated_record(story_id=f"don-{index:03d}", style_preset_id=style, candidate_role=role)
        for index, (style, role) in enumerate(styles_and_roles, start=1)
    ]


def test_donated_candidates_have_the_frozen_style_and_primary_allocation(tmp_path):
    loaded = load_intake(write_intake(tmp_path, donated_candidates()))

    assert Counter(record.style_preset_id for record in loaded) == {
        "cel": 5,
        "gouache": 5,
        "cut_paper": 5,
    }
    assert Counter(record.style_preset_id for record in loaded if record.candidate_role == "primary") == {
        "gouache": 4,
        "cel": 3,
        "cut_paper": 3,
    }


def test_load_intake_rejects_a_donated_batch_without_fifteen_candidates(tmp_path):
    with pytest.raises(ValueError, match="donated allocation"):
        load_intake(write_intake(tmp_path, donated_candidates()[:-1]))


def test_load_intake_rejects_a_donated_batch_with_style_allocation_drift(tmp_path):
    records = donated_candidates()
    records[-1]["style_preset_id"] = "cel"

    with pytest.raises(ValueError, match="donated allocation"):
        load_intake(write_intake(tmp_path, records))


def test_load_intake_rejects_a_donated_batch_with_primary_allocation_drift(tmp_path):
    records = donated_candidates()
    records[0]["candidate_role"] = "backup"

    with pytest.raises(ValueError, match="donated allocation"):
        load_intake(write_intake(tmp_path, records))


def run_bundle(**changes):
    bundle = RunBundle(
        memory=StoryMemory(
            schema_version=CURRENT_SCHEMA_VERSION,
            story_id="syn-001",
            classroom_id="judge-corpus",
            profile_id="judge-corpus",
            input=Input(raw_text="A redacted fictional story."),
        ),
        provenance="synthetic",
        split="train",
        candidate_role="not_applicable",
        run_metadata={"schema_version": CURRENT_SCHEMA_VERSION, "style_preset_id": "cel"},
        assets=[
            AssetRecord(
                storage_path="syn-001/ref-c1-1.png",
                local_path="ref/syn-001_ref-c1-1.png",
                sha256="a" * 64,
                mime_type="image/png",
                width=1,
                height=1,
                byte_length=1,
                kind="ref",
            )
        ],
    )
    return bundle.model_copy(update=changes)


def test_write_bundle_atomically_persists_a_reloadable_completed_run(tmp_path, monkeypatch):
    replaced = []
    original_replace = Path.replace

    def track_replace(self, target):
        replaced.append((self.name, Path(target).name))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", track_replace)

    bundle = run_bundle()
    bundle_dir = write_bundle(tmp_path, bundle)

    assert bundle_dir == tmp_path / "runs" / "syn-001"
    assert {target for _, target in replaced} == {"memory.json", "run.json", "assets.json"}
    assert load_completed_bundles(tmp_path) == [bundle]
    assert not list(bundle_dir.glob(".*.tmp"))


def test_write_bundle_rejects_a_rerun_with_different_asset_bytes(tmp_path):
    bundle = run_bundle()
    write_bundle(tmp_path, bundle)
    changed_asset = bundle.assets[0].model_copy(update={"sha256": "b" * 64})

    with pytest.raises(CorpusError, match="immutable bundle differs"):
        write_bundle(tmp_path, bundle.model_copy(update={"assets": [changed_asset]}))


def test_write_bundle_rejects_a_rerun_with_different_metadata(tmp_path):
    bundle = run_bundle()
    write_bundle(tmp_path, bundle)

    with pytest.raises(CorpusError, match="immutable bundle differs"):
        write_bundle(tmp_path, bundle.model_copy(update={"run_metadata": {"schema_version": 2}}))
