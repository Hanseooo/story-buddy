"""The manifest record (`judge-finetune.md` §5.2) and the guards CI runs against it (§3.2, §10).

One JSONL line = one training example. The manifest is the source of truth; the LLaMA-Factory
JSON is a build artifact. `char_id`, `split`, `provenance` and `pair_type` are bookkeeping and
must never reach the training text — if they did, the model could read the answer off them.
"""
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from contracts.story_memory import FailureReason

Split = Literal["train", "val", "test"]
PairType = Literal["pipeline", "constructed"]
# §5.4 open reconciliation item, resolved 2026-08-14: train + val characters come from the
# SYNTHETIC corpus; the held-out test split is drawn exclusively from the DONATED stories. The
# guard below enforces that as an invariant rather than leaving it a comment, because a synthetic
# character in the held-out set voids Objective 4 and nothing in the metrics would show it.
Provenance = Literal["synthetic", "donated"]


DATA_ROOT = Path("data/judge")
ImageKind = Literal["ref", "scene"]


def local_image_path(storage_path: str, kind: ImageKind, root: Path | None = None) -> str:
    """The on-disk dataset path for a Storage path. The ONE naming rule, shared by both sides.

    `build_corpus.download_images` writes the file; `build_dataset` names it in the manifest;
    LLaMA-Factory resolves `images` against the filesystem and reports nothing useful when a path
    is wrong — it just trains on whatever it managed to load. The two sides were built separately
    and disagreed (manifest carried the raw Storage path), so the rule lives here and is imported,
    never re-implemented.

    Flattening `/` to `_` keeps the name unique across stories, because the Storage path is already
    prefixed with `story_id`, and keeps it losslessly reversible.
    """
    return ((root or DATA_ROOT) / kind / storage_path.replace("/", "_")).as_posix()


class ManifestError(ValueError):
    """A manifest that would silently corrupt Objective 4. Never caught — it stops the build."""


class ManifestRecord(BaseModel):
    pair_id: str                       # opaque; minted by `build_dataset.mint_pair_id`
    char_id: str                       # the only field §3.2 splits on. Never enters training text.
    split: Split
    provenance: Provenance
    pair_type: PairType
    images: list[str] = Field(min_length=2, max_length=2)   # reference FIRST, scene second (§5.2)

    # --- the training target, in the order the model must emit it (§2, ADR-004) ---
    differences_observed: str          # rendered deterministically by `build_dataset.render_rationale`
    same_character: bool               # the schema's polarity: True = SAME character
    # The manuscript's positive class, `label = not same_character` (annotation-surface §2.1).
    # Derived in `build_dataset.py` and NOWHERE else; carried here so no consumer re-derives it.
    label: bool
    # Both GATE `Attempt.passed` in production (`pipeline/consistency_check.py`), so both are
    # human-annotated and both are read from the `annotations` table.
    anatomy_intact: bool = True
    text_free: bool = True
    failure_reasons: list[FailureReason] = Field(default_factory=list)   # closed set (§4)

    # ponytail: `subjects_unique` and `style_match` are NOT annotated — they are the two
    # non-gating fields on `VlmVerdict`, so a human label on them buys nothing the loop acts on
    # and costs annotator seconds per pair. `to_llamafactory` takes their schema defaults.
    # Upgrade path: if either is ever promoted to gating (spec §8.1 for `subjects_unique`,
    # ADR-007 for `style_match`), add it here, add its checkbox to the annotation surface, and
    # re-annotate — a default cannot be back-filled into a label.


def validate_manifest(records: list[ManifestRecord]) -> None:
    """The §10 CI guard. Raises `ManifestError` on any of the three silent corruptions."""
    splits_by_char: dict[str, set[str]] = {}
    for record in records:
        splits_by_char.setdefault(record.char_id, set()).add(record.split)

        # §5.4 (resolved): the held-out set measures transfer to real donated stories.
        if record.split == "test" and record.provenance == "synthetic":
            raise ManifestError(
                f"{record.pair_id}: test-split record has provenance='synthetic'; the held-out "
                "split is drawn exclusively from the donated stories"
            )

        # §3.3: constructed negatives are train-only — val and test must keep the deployment
        # distribution, and a constructed pair is trivially separable.
        if record.pair_type == "constructed" and record.split != "train":
            raise ManifestError(
                f"{record.pair_id}: pair_type='constructed' in split={record.split!r}; constructed "
                "negatives belong to the train split only"
            )

    # §3.2: every image derived from a given canonical reference belongs to exactly one split.
    leaked = {char_id: sorted(splits) for char_id, splits in splits_by_char.items() if len(splits) > 1}
    if leaked:
        raise ManifestError(f"char_id leaks across splits: {leaked}")


def write_manifest(path: Path, records: list[ManifestRecord], validate: bool = True) -> None:
    if validate:
        validate_manifest(records)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")


def read_manifest(path: Path) -> list[ManifestRecord]:
    """Reading always validates — a corrupt manifest must not survive a round trip unnoticed."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    records = [ManifestRecord.model_validate_json(line) for line in lines if line.strip()]
    validate_manifest(records)
    return records
