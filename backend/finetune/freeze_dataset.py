"""Validate completed corpus bundles and install one immutable training dataset."""
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.config import SELECTABLE_STYLE_PRESET_IDS
from finetune.annotation_truth import (
    fetch_adjudicator_ids,
    fetch_annotations,
    fetch_pilot_pairs,
    resolve_annotations,
)
from finetune.corpus_io import (
    CorpusError,
    RunBundle,
    load_completed_bundles,
    reconcile_declared_roster,
)
from finetune.dataset_selection import (
    SYNTHETIC_INTAKE,
    prepare_dataset_bundles,
    validate_hard_negative_matches,
)
from finetune.manifest import ManifestError, ManifestRecord, local_image_path

PINNED_METADATA_KEYS = {
    "code_commit", "schema_version", "text_model", "image_model", "image_edit_model",
    "judge_model", "moderation_primary_model", "moderation_primary_image_model",
    "moderation_backstop_model", "moderation_backstop_image_model",
    "extraction_prompt_version", "reference_judge_prompt_version", "scene_prompt_version",
    "judge_prompt_version", "scene_constraint_prompt_version", "image_budget", "recursion_limit",
}


class FreezeReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_sha256: str
    counts: dict[str, dict[str, int]]
    adjudication_rate: float
    exclusions: list[str]
    pinned_versions: dict[str, str]
    selected_donated_stories: list[str] = Field(default_factory=list)
    excluded_donated_stories: list[str] = Field(default_factory=list)
    replacement_reasons: dict[str, str] = Field(default_factory=dict)
    selection_sha256: str | None = None


def _pinned_versions(bundles: list[RunBundle]) -> dict[str, str]:
    for bundle in bundles:
        missing = PINNED_METADATA_KEYS - bundle.run_metadata.keys()
        if missing:
            raise ManifestError(f"{bundle.memory.story_id}: missing pinned run metadata: {sorted(missing)}")
    pinned = {}
    for key in sorted(PINNED_METADATA_KEYS):
        values = {str(bundle.run_metadata[key]) for bundle in bundles}
        if len(values) != 1:
            raise ManifestError(f"pinned run metadata differs for {key}: {sorted(values)}")
        pinned[key] = values.pop()
    pinned["style_preset_ids"] = ",".join(
        sorted({str(bundle.run_metadata["style_preset_id"]) for bundle in bundles})
    )
    return pinned


def _validate_bundles(
    bundles: list[RunBundle], data_dir: Path
) -> tuple[dict[str, str], dict[str, str]]:
    from finetune.build_dataset import lineage_id, pairs_from_memory
    from finetune.materialize_pairs import _preflight

    seen_stories, seen_pairs = set(), set()
    pair_to_story, char_to_story = {}, {}
    for bundle in bundles:
        story_id = bundle.memory.story_id
        if story_id in seen_stories:
            raise ManifestError(f"duplicate story_id: {story_id}")
        seen_stories.add(story_id)
        style = bundle.memory.style.style_preset_id
        if style not in SELECTABLE_STYLE_PRESET_IDS:
            raise ManifestError(f"unknown style_preset_id: {style}")
        if bundle.run_metadata.get("style_preset_id") != style:
            raise ManifestError(f"reference/scene style disagreement: {story_id}")
        if bundle.declared_characters is None or bundle.declared_non_human is None:
            raise ManifestError(f"{story_id}: missing declared roster")
        try:
            reconcile_declared_roster(bundle.declared_characters, bundle.declared_non_human, bundle.memory)
        except CorpusError as error:
            raise ManifestError(str(error)) from error
        for character in bundle.memory.characters:
            qualified_id = lineage_id(story_id, character.char_id)
            char_to_story[qualified_id] = story_id
        for pair in pairs_from_memory(bundle.memory):
            if pair.pair_id in seen_pairs:
                raise ManifestError(f"duplicate pair_id: {pair.pair_id}")
            seen_pairs.add(pair.pair_id)
            pair_to_story[pair.pair_id] = story_id
    _preflight(bundles, data_dir)

    fixture_states = {bundle.run_metadata.get("fixture") for bundle in bundles}
    if fixture_states == {"true"}:
        return pair_to_story, char_to_story
    if fixture_states != {"false"}:
        raise ManifestError("fixture and production bundles cannot share a freeze")
    synthetic = Counter(
        (bundle.memory.style.style_preset_id, bundle.split)
        for bundle in bundles if bundle.provenance == "synthetic"
    )
    expected_synthetic = Counter(
        {(style, "train"): 8 for style in SELECTABLE_STYLE_PRESET_IDS}
        | {(style, "val"): 2 for style in SELECTABLE_STYLE_PRESET_IDS}
    )
    donated = Counter(
        bundle.memory.style.style_preset_id for bundle in bundles if bundle.provenance == "donated"
    )
    if synthetic != expected_synthetic or donated != Counter({"gouache": 4, "cel": 3, "cut_paper": 3}):
        raise ManifestError("style allocation drift in production bundles")
    return pair_to_story, char_to_story


def _freeze_counts(
    records: list[ManifestRecord], pair_to_story: dict[str, str], char_to_story: dict[str, str]
) -> dict[str, dict[str, int]]:
    return {
        "story": dict(Counter(pair_to_story.get(r.pair_id) or char_to_story[r.char_id] for r in records)),
        "character": dict(Counter(r.char_id for r in records)),
        "split": dict(Counter(r.split for r in records)),
        "class": dict(Counter("same_character" if r.same_character else "different_character" for r in records)),
        "reason": dict(Counter(
            reason.value if hasattr(reason, "value") else str(reason)
            for record in records for reason in record.failure_reasons
        )),
    }


def _same_directory(left: Path, right: Path) -> bool:
    left_files = {path.relative_to(left): path for path in left.rglob("*") if path.is_file()}
    right_files = {path.relative_to(right): path for path in right.rglob("*") if path.is_file()}
    return left_files.keys() == right_files.keys() and all(
        path.read_bytes() == right_files[name].read_bytes() for name, path in left_files.items()
    )


def freeze_dataset(
    data_dir: Path,
    out_dir: Path,
    *,
    donated_intake_path: Path | None = None,
    selection_path: Path | None = None,
    synthetic_intake_path: Path = SYNTHETIC_INTAKE,
) -> FreezeReport:
    from finetune.build_dataset import build_dataset, pairs_from_memory
    from finetune.materialize_pairs import read_verified_asset
    from finetune.to_llamafactory import write_dataset

    data_dir, out_dir = Path(data_dir), Path(out_dir)
    bundles = load_completed_bundles(data_dir)
    if not bundles:
        raise ManifestError("no completed run bundles")

    selected_bundles, selection, audit = prepare_dataset_bundles(
        bundles,
        donated_intake_path,
        selection_path,
        synthetic_intake_path=synthetic_intake_path,
    )

    pair_to_story, char_to_story = _validate_bundles(selected_bundles, data_dir)
    annotations, adjudicators, pilot_pairs = (
        fetch_annotations(), fetch_adjudicator_ids(), fetch_pilot_pairs()
    )
    declared_exclusions = {pair_id for bundle in selected_bundles for pair_id in bundle.exclusions}
    unknown_exclusions = declared_exclusions - pair_to_story.keys()
    if unknown_exclusions:
        raise ManifestError(f"unknown exclusions: {sorted(unknown_exclusions)}")
    exclusions = declared_exclusions | (pilot_pairs & pair_to_story.keys())
    ignored_pairs = declared_exclusions | pilot_pairs

    all_loaded_pairs = {p.pair_id for b in bundles for p in pairs_from_memory(b.memory)}
    unknown = {row["pair_id"] for row in annotations} - all_loaded_pairs - pilot_pairs
    if unknown:
        raise ManifestError(f"pair/memory mismatch: {sorted(unknown)}")

    relevant_annotations = [
        row for row in annotations
        if row.get("pair_id") in pair_to_story or row.get("pair_id") in pilot_pairs
    ]

    matches = {} if selection is None else validate_hard_negative_matches(
        selected_bundles, selection, relevant_annotations, pilot_pairs
    )

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{out_dir.name}.", dir=out_dir.parent) as temporary:
        staged = Path(temporary) / out_dir.name
        staged.mkdir()
        for bundle in selected_bundles:
            for asset in bundle.assets:
                target = Path(local_image_path(asset.storage_path, asset.kind, root=Path("assets")))
                output = staged / target
                output.parent.mkdir(parents=True, exist_ok=True)
                contents = read_verified_asset(asset, data_dir)
                if output.exists() and output.read_bytes() != contents:
                    raise ManifestError(f"frozen asset path conflict: {target.as_posix()}")
                output.write_bytes(contents)
        records = build_dataset(
            [(bundle.memory, bundle.split, bundle.provenance) for bundle in selected_bundles],
            out_path=staged / "manifest.jsonl",
            annotation_rows=relevant_annotations,
            adjudicator_ids=adjudicators,
            pilot_pair_ids=ignored_pairs,
            image_root=Path("assets"),
            hard_negative_matches=matches,
        )
        write_dataset(records, staged)
        consensus = resolve_annotations(relevant_annotations, adjudicators, ignored_pairs)
        report = FreezeReport(
            dataset_sha256=hashlib.sha256((staged / "manifest.jsonl").read_bytes()).hexdigest(),
            counts=_freeze_counts(records, pair_to_story, char_to_story),
            adjudication_rate=sum(item.adjudicated for item in consensus.values()) / max(1, len(consensus)),
            exclusions=sorted(exclusions),
            pinned_versions=_pinned_versions(selected_bundles),
            selected_donated_stories=audit.selected_donated_stories,
            excluded_donated_stories=audit.excluded_donated_stories,
            replacement_reasons=audit.replacement_reasons,
            selection_sha256=audit.selection_sha256,
        )
        (staged / "freeze_report.json").write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if out_dir.exists():
            if not _same_directory(staged, out_dir):
                raise ManifestError("immutable freeze differs; use a new output directory")
        else:
            staged.replace(out_dir)
    return report
