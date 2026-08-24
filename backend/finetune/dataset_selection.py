"""Strict dataset selection artifact and audit for Objective-4 fine-tuning."""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Literal, Sequence, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from finetune.corpus_io import IntakeRecord, RunBundle, intake_sha256, load_intake
from finetune.manifest import ManifestError

SYNTHETIC_INTAKE = Path(__file__).with_name("corpus_synthetic.json")


def lineage_id(story_id: str, char_id: str) -> str:
    """Qualify StoryMemory's story-local character IDs for corpus-wide split guards."""
    return f"{story_id}:{char_id}"


ReplacementReason = Literal[
    "withdrawal",
    "deidentification_failure",
    "terminal_pipeline_failure",
    "inadequate_character_yield",
]


class HardNegativeMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_char_id: str
    target_char_id: str


class DonatedReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_story_id: str
    backup_story_id: str
    reason: ReplacementReason
    approved_at: datetime
    evidence_ref: str

    @field_validator("evidence_ref")
    @classmethod
    def evidence_ref_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence_ref must not be blank")
        return value

    @field_validator("approved_at")
    @classmethod
    def approved_at_must_be_completed(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("approved_at must be a completed timezone-aware timestamp")
        return value


class DatasetSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_negatives_frozen_at: datetime
    hard_negative_matches: list[HardNegativeMatch]
    donated_replacements: list[DonatedReplacement]

    @field_validator("hard_negatives_frozen_at")
    @classmethod
    def frozen_at_must_be_completed(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("hard_negatives_frozen_at must be a completed timezone-aware timestamp")
        return value

    @model_validator(mode="after")
    def validate_selection_integrity(self) -> Self:
        refs = [m.reference_char_id for m in self.hard_negative_matches]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate reference_char_id in hard_negative_matches")
        for match in self.hard_negative_matches:
            if match.reference_char_id == match.target_char_id:
                raise ValueError(f"self-pair forbidden: {match.reference_char_id}")

        primaries = [r.primary_story_id for r in self.donated_replacements]
        if len(primaries) != len(set(primaries)):
            raise ValueError("duplicate primary_story_id in donated_replacements")
        backups = [r.backup_story_id for r in self.donated_replacements]
        if len(backups) != len(set(backups)):
            raise ValueError("reused backup_story_id in donated_replacements")
        return self


@dataclass(frozen=True)
class DatasetSelectionAudit:
    selected_donated_stories: list[str]
    excluded_donated_stories: list[str]
    replacement_reasons: dict[str, str]
    selection_sha256: str | None


def selection_sha256(path: Path) -> str:
    """Exact-byte SHA-256 hash of the dataset selection JSON artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset_selection(path: Path) -> DatasetSelection:
    """Load and strictly validate the controlled dataset selection artifact."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DatasetSelection.model_validate(payload)


def candidate_report(bundles: Sequence[RunBundle]) -> list[dict[str, object]]:
    """Produce deterministic candidate report JSON for manual hard-negative selection.

    Lists each synthetic training character with its canonical reference and candidate
    target characters of the same species and art style having at least one natural scene.
    """
    train_bundles = [
        b for b in bundles if b.provenance == "synthetic" and b.split == "train"
    ]

    # Collect character metadata and scene counts across train bundles
    # char_info: lineage_id -> (character, style, canonical_ref, scene_count)
    char_info: dict[str, dict[str, object]] = {}
    for bundle in train_bundles:
        style = str(bundle.run_metadata.get("style_preset_id", ""))
        scene_counts: Counter[str] = Counter()
        for scene in bundle.memory.scenes:
            if scene.final_image_ref:
                for cid in scene.characters_present:
                    scene_counts[cid] += 1

        for char in bundle.memory.characters:
            if not char.canonical_ref_image:
                continue
            lid = lineage_id(bundle.memory.story_id, char.char_id)
            char_info[lid] = {
                "lineage_id": lid,
                "character": char,
                "species": char.description.species.strip(),
                "style": style,
                "canonical_ref": char.canonical_ref_image,
                "scene_count": scene_counts[char.char_id],
            }

    report: list[dict[str, object]] = []
    for lid in sorted(char_info):
        info = char_info[lid]
        species = str(info["species"])
        style = str(info["style"])

        candidates = []
        for other_lid, other_info in char_info.items():
            if other_lid == lid:
                continue
            other_species = str(other_info["species"])
            other_style = str(other_info["style"])
            other_scenes = int(other_info["scene_count"])
            if (
                species.casefold() == other_species.casefold()
                and style == other_style
                and other_scenes > 0
            ):
                candidates.append({
                    "target_char_id": other_lid,
                    "target_reference_image": other_info["canonical_ref"],
                    "scene_count": other_scenes,
                })

        candidates.sort(key=lambda c: str(c["target_char_id"]))
        report.append({
            "reference_char_id": lid,
            "reference_image": info["canonical_ref"],
            "species": species,
            "style": style,
            "candidates": candidates,
        })

    return report


def select_dataset_bundles(
    bundles: Sequence[RunBundle],
    synthetic_intake: Sequence[IntakeRecord],
    donated_intake: Sequence[IntakeRecord],
    selection: DatasetSelection,
    selection_hash: str,
) -> tuple[list[RunBundle], DatasetSelectionAudit]:
    """Validate intake provenance and apply strict donated membership rules."""
    intake_by_id = {r.story_id: r for r in [*synthetic_intake, *donated_intake]}

    # Validate all production bundles against intake records and intake hashes
    for bundle in bundles:
        story_id = bundle.memory.story_id
        intake_rec = intake_by_id.get(story_id)
        if intake_rec is None:
            raise ManifestError(f"bundle {story_id} not found in intake")
        expected_hash = intake_sha256(intake_rec)
        recorded_hash = bundle.run_metadata.get("intake_sha256")
        if recorded_hash != expected_hash:
            raise ManifestError(
                f"bundle {story_id} intake_sha256 mismatch: recorded={recorded_hash} expected={expected_hash}"
            )

    # Donated candidate validation
    donated_by_id = {r.story_id: r for r in donated_intake}
    donated_bundles_by_id = {
        b.memory.story_id: b for b in bundles if b.provenance == "donated"
    }

    primaries = {r.story_id for r in donated_intake if r.candidate_role == "primary"}
    backups = {r.story_id for r in donated_intake if r.candidate_role == "backup"}

    # Process replacements
    replacement_reasons: dict[str, str] = {}
    replaced_primaries: set[str] = set()
    used_backups: set[str] = set()

    for repl in selection.donated_replacements:
        pid = repl.primary_story_id
        bid = repl.backup_story_id

        if pid not in primaries:
            raise ManifestError(f"replacement primary {pid} is not a primary donated candidate")
        if bid not in backups:
            raise ManifestError(f"replacement backup {bid} is not a backup donated candidate")

        primary_rec = donated_by_id[pid]
        backup_rec = donated_by_id[bid]

        if primary_rec.style_preset_id != backup_rec.style_preset_id:
            raise ManifestError(
                f"cross-style replacement forbidden: primary {pid} ({primary_rec.style_preset_id}) != backup {bid} ({backup_rec.style_preset_id})"
            )
        if backup_rec.withdrawal_state == "withdrawn":
            raise ManifestError(f"replacement backup {bid} is withdrawn")

        replaced_primaries.add(pid)
        used_backups.add(bid)
        replacement_reasons[pid] = repl.reason

    selected_donated_ids = (primaries - replaced_primaries) | used_backups

    # Verify no selected story is withdrawn
    for sid in selected_donated_ids:
        if donated_by_id[sid].withdrawal_state == "withdrawn":
            raise ManifestError(f"selected story {sid} is withdrawn without replacement")
        if sid not in donated_bundles_by_id:
            raise ManifestError(f"selected donated story {sid} is missing from completed bundles")

    # Verify 10 stories with 4 gouache, 3 cel, 3 cut_paper
    if len(selected_donated_ids) != 10:
        raise ManifestError(f"final donated selection must have 10 stories, got {len(selected_donated_ids)}")

    selected_styles = Counter(donated_by_id[sid].style_preset_id for sid in selected_donated_ids)
    if selected_styles != {"gouache": 4, "cel": 3, "cut_paper": 3}:
        raise ManifestError(f"final donated selection style distribution must be 4 gouache / 3 cel / 3 cut_paper, got {selected_styles}")

    excluded_donated_stories = sorted(sid for sid in donated_by_id if sid not in selected_donated_ids)

    # Return selected bundles: synthetic bundles + selected donated bundles
    synthetic_bundles = [b for b in bundles if b.provenance == "synthetic"]
    selected_don_bundles = [donated_bundles_by_id[sid] for sid in sorted(selected_donated_ids)]
    selected_bundles = synthetic_bundles + selected_don_bundles

    audit = DatasetSelectionAudit(
        selected_donated_stories=sorted(selected_donated_ids),
        excluded_donated_stories=excluded_donated_stories,
        replacement_reasons=replacement_reasons,
        selection_sha256=selection_hash,
    )
    return selected_bundles, audit


def prepare_dataset_bundles(
    bundles: Sequence[RunBundle],
    donated_intake_path: Path | None,
    selection_path: Path | None,
    *,
    synthetic_intake_path: Path = SYNTHETIC_INTAKE,
) -> tuple[list[RunBundle], DatasetSelection | None, DatasetSelectionAudit]:
    """Prepare and audit bundles before remote materialization and freeze."""
    fixture_flags = [bool(b.run_metadata.get("fixture")) for b in bundles]
    if all(fixture_flags):
        return (
            list(bundles),
            None,
            DatasetSelectionAudit(
                selected_donated_stories=[],
                excluded_donated_stories=[],
                replacement_reasons={},
                selection_sha256=None,
            ),
        )

    if any(fixture_flags):
        raise ManifestError("mixed fixture and production bundles found")

    if donated_intake_path is None or selection_path is None:
        raise ManifestError("production dataset preparation requires --donated-intake and --selection")

    synthetic = load_intake(synthetic_intake_path)
    donated = load_intake(donated_intake_path, mode="freeze_audit")
    selection = load_dataset_selection(selection_path)
    selected, audit = select_dataset_bundles(
        bundles, synthetic, donated, selection, selection_sha256(selection_path)
    )
    return selected, selection, audit
