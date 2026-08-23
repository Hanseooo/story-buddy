"""Pipeline output + the `annotations` table → `manifest.jsonl` (`judge-finetune.md` §5.3, §5.4).

This module owns the **one** polarity conversion in the project. `annotations.same_character` is
`true` for *same*; the manuscript's positive class is `1 = different_character`. The mapping
`label = not same_character` is applied in `build_records` and re-derived nowhere else
(`annotation-surface.md` §2.1) — inverting it flips precision and recall for Objective 4 while
every number still looks plausible.
"""
import argparse
import hashlib
import itertools
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, NamedTuple

from app.db import get_supabase_client
from contracts.story_memory import Character, FailureReason, StoryMemory
from finetune.annotation_truth import (
    Consensus,
    fetch_adjudicator_ids,
    fetch_annotations,
    fetch_pilot_pairs,
    reconcile_pair_status,
    reconcile_remote_status,
    repair_pair_statuses,
    resolve_annotations,
)
from finetune.corpus_io import CorpusError
from finetune.freeze_dataset import FreezeReport, freeze_dataset
from finetune.manifest import (
    ManifestError,
    ManifestRecord,
    PairType,
    Provenance,
    Split,
    local_image_path,
    write_manifest,
)

__all__ = [
    "Consensus",
    "FreezeReport",
    "fetch_adjudicator_ids",
    "fetch_annotations",
    "fetch_pilot_pairs",
    "freeze_dataset",
    "reconcile_pair_status",
    "reconcile_remote_status",
    "repair_pair_statuses",
    "resolve_annotations",
]

log = logging.getLogger(__name__)


# §5.2: the rationale is rendered deterministically from the ticked taxonomy — no human writes it
# and no model writes it, so §3.4's distillation ceiling cannot come back through the side door.
# One sentence pattern per taxonomy entry, concatenated for multi-reason items.
REASON_SENTENCES: dict[FailureReason, str] = {
    FailureReason.wrong_colour:       "The character's colours do not match the reference.",
    FailureReason.wrong_species:      "The character is not the species the reference shows.",
    FailureReason.wrong_body_feature: "The character does not show the expected body features.",
    FailureReason.wrong_clothing:     "The character's clothing does not match the reference.",
    FailureReason.wrong_style:        "The character is not drawn in the reference's art style.",
    FailureReason.different_face:     "The face is that of a different individual.",
    FailureReason.character_absent:   "The character does not appear in the picture at all.",
}
UNSPECIFIED_DIFFERENCE = "The two images show different characters."
CONSTRUCTED_RATIONALE = (
    "The face and build are those of a different individual; this is not the reference character."
)


class Pair(NamedTuple):
    """One candidate training example, before a human has looked at it."""
    pair_id: str
    char_id: str
    ref_image: str
    scene_image: str


# --- pairing (§5.4 step 2 — a loop, not a labelling task) ------------------------------------

def mint_pair_id(char_id: str, scene_image: str) -> str:
    """Opaque and deterministic. Opaque because `annotate/` blinds on it (annotation-surface §2.1);
    deterministic because a re-run must line up with labels already collected against it."""
    return hashlib.sha256(f"{char_id}\0{scene_image}".encode()).hexdigest()[:16]


def lineage_id(story_id: str, char_id: str) -> str:
    """Qualify StoryMemory's story-local character IDs for corpus-wide split guards."""
    return f"{story_id}:{char_id}"


def pairs_from_memory(memory: StoryMemory) -> list[Pair]:
    """Each finalized scene against the canonical reference of every character present in it.

    Reference first, scene second — order is load-bearing (§5.2), and it is the same order
    `providers.judge` sends them in.
    """
    by_id = {c.char_id: c for c in memory.characters}
    pairs = []
    for scene in memory.scenes:
        if not scene.final_image_ref:
            continue
        for char_id in scene.characters_present:
            character = by_id.get(char_id)
            if character is None or not character.canonical_ref_image:
                continue    # nothing to compare against; consistency_check skips these too
            pairs.append(Pair(
                pair_id=mint_pair_id(char_id, scene.final_image_ref),
                char_id=char_id,
                ref_image=character.canonical_ref_image,
                scene_image=scene.final_image_ref,
            ))
    return pairs


# --- rationale rendering (§5.2) --------------------------------------------------------------

def bible_attributes(character: Character) -> list[str]:
    """The Character Bible's attribute list, flattened in declaration order."""
    d = character.description
    return [a for a in [d.species, *d.colours, *d.body_features, *d.clothing] if a]


def render_rationale(same_character: bool, failure_reasons: Iterable[str], attributes: list[str]) -> str:
    """Byte-stable prose from the checkbox supervision. §6.1's round-trip requires stability.

    A blank rationale on positives would teach the model that rationales only exist for failures,
    so a positive renders the attribute checklist as an "all present" sentence.
    """
    listed = ", ".join(attributes)
    if same_character:
        return f"Present on the page: {listed}." if listed else "Every expected attribute is present."

    order = {reason: i for i, reason in enumerate(FailureReason)}
    ticked = sorted({FailureReason(r) for r in failure_reasons}, key=order.get)
    sentences = [REASON_SENTENCES[r] for r in ticked] or [UNSPECIFIED_DIFFERENCE]
    if listed:
        sentences.append(f"Expected: {listed}.")
    return " ".join(sentences)


# --- records -----------------------------------------------------------------------------

def build_records(
    memory: StoryMemory,
    split: Split,
    provenance: Provenance,
    consensus: dict[str, Consensus],
    pilot_pairs: set[str],
    pair_type: PairType = "pipeline",
    image_root: Path | None = None,
) -> list[ManifestRecord]:
    """Pairs that have a resolved human label become manifest records. Pilot pairs are dropped.
    Non-pilot pairs with missing annotations trigger a HARD FAIL.

    THIS is the single polarity conversion site (`annotation-surface.md` §2.1).
    """
    by_id = {c.char_id: c for c in memory.characters}
    records = []
    for pair in pairs_from_memory(memory):
        if pair.pair_id in pilot_pairs:
            continue

        agreed = consensus.get(pair.pair_id)
        if agreed is None:
            raise ManifestError(f"Pair {pair.pair_id} has <2 annotations and is not a pilot pair.")

        records.append(ManifestRecord(
            pair_id=pair.pair_id,
            char_id=lineage_id(memory.story_id, pair.char_id),
            split=split,
            provenance=provenance,
            pair_type=pair_type,
            # Storage paths -> the local files `build_corpus` wrote. LLaMA-Factory resolves these
            # against the filesystem, so the manifest must carry the on-disk name (manifest.py).
            images=[
                local_image_path(pair.ref_image, "ref", root=image_root),
                local_image_path(pair.scene_image, "scene", root=image_root),
            ],
            differences_observed=render_rationale(
                agreed.same_character, agreed.failure_reasons, bible_attributes(by_id[pair.char_id])
            ),
            same_character=agreed.same_character,
            label=not agreed.same_character,   # ← the ONE inversion. Do not repeat it downstream.
            anatomy_intact=agreed.anatomy_intact,
            text_free=agreed.text_free,
            failure_reasons=agreed.failure_reasons,
        ))
    return records


def constructed_records(
    records: list[ManifestRecord], styles_by_char: dict[str, str] | None = None
) -> list[ManifestRecord]:
    """§5.4 step 5 — character A's reference against a scene generated from character B's.

    Free, definitely different, and TRAIN ONLY (§3.3): val and test must keep the deployment
    distribution. Non-train inputs are ignored rather than rejected so the caller can hand over
    the whole manifest.

    ponytail: one pass over adjacent character pairs, not the full cross product — the cross
    product of ~33 train characters is thousands of near-duplicate negatives and §5.4 budgets
    ~450. Upgrade path: if the class balance needs more, widen the `combinations` window.
    """
    train = [r for r in records if r.split == "train" and r.pair_type == "pipeline"]
    by_char: dict[str, list[ManifestRecord]] = defaultdict(list)
    for record in train:
        by_char[record.char_id].append(record)

    made = []
    for a, b in itertools.combinations(sorted(by_char), 2):
        if styles_by_char is not None and styles_by_char.get(a) != styles_by_char.get(b):
            continue
        ref = by_char[a][0].images[0]
        scene = by_char[b][0].images[1]
        made.append(ManifestRecord(
            pair_id=mint_pair_id(a, scene),
            char_id=a,                        # the REFERENCE owns the split (§3.2)
            split="train",
            provenance=by_char[a][0].provenance,
            pair_type="constructed",
            images=[ref, scene],
            differences_observed=CONSTRUCTED_RATIONALE,
            same_character=False,
            label=True,
            failure_reasons=[FailureReason.different_face],
        ))
    return made


def build_dataset(
    corpus: Iterable[tuple[StoryMemory, Split, Provenance]],
    out_path: Path = Path("data/judge/manifest.jsonl"),
    add_constructed: bool = True,
    *,
    annotation_rows: Iterable[dict] | None = None,
    adjudicator_ids: set[str] | None = None,
    pilot_pair_ids: set[str] | None = None,
    image_root: Path | None = None,
    styles_by_char: dict[str, str] | None = None,
) -> list[ManifestRecord]:
    """The entry point. Reads every annotation once, then writes a validated manifest and stats."""
    out_path = Path(out_path)
    adjudicators = fetch_adjudicator_ids() if adjudicator_ids is None else adjudicator_ids
    pilot_pairs = fetch_pilot_pairs() if pilot_pair_ids is None else pilot_pair_ids
    rows = fetch_annotations() if annotation_rows is None else annotation_rows
    consensus = resolve_annotations(rows, adjudicators, pilot_pairs)

    records: list[ManifestRecord] = []
    for memory, split, provenance in corpus:
        records += build_records(
            memory, split, provenance, consensus, pilot_pairs, image_root=image_root
        )
    if add_constructed:
        records += constructed_records(records, styles_by_char)

    write_manifest(out_path, records)     # validates — §3.2's guard is not optional
    log.info("build_dataset: wrote %d records to %s", len(records), out_path)

    # Compute SHA-256 of the generated JSONL
    h = hashlib.sha256()
    with open(out_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    file_hash = h.hexdigest()

    # Generate statistics
    stats = {
        "splits": {},
        "overall": {
            "characters": len(set(r.char_id for r in records)),
            "natural_pairs": sum(1 for r in records if r.pair_type == "pipeline"),
            "constructed_pairs": sum(1 for r in records if r.pair_type == "constructed"),
            "total_pairs": len(records),
        },
        "class_balance": {
            "same_character": sum(1 for r in records if r.same_character),
            "different_character": sum(1 for r in records if not r.same_character),
        },
        "failure_reasons": dict(Counter(
            reason.value if hasattr(reason, "value") else str(reason)
            for r in records
            for reason in r.failure_reasons
        )),
        "adjudication_rate": sum(1 for c in consensus.values() if getattr(c, "adjudicated", False)) / max(1, len(consensus)),
        "dataset_sha256": file_hash,
    }

    for s in ["train", "val", "test"]:
        split_records = [r for r in records if r.split == s]
        stats["splits"][s] = {
            "characters": len(set(r.char_id for r in split_records)),
            "natural_pairs": sum(1 for r in split_records if r.pair_type == "pipeline"),
            "constructed_pairs": sum(1 for r in split_records if r.pair_type == "constructed"),
        }

    stats_path = out_path.with_name("dataset_manifest.json")
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    log.info("build_dataset: wrote stats to %s", stats_path)

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile or freeze the Objective-4 judge dataset.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reconcile-only", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    parser.add_argument("--data", type=Path, default=Path("data/judge"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.reconcile_only:
            statuses, changed = reconcile_remote_status(get_supabase_client())
            print(json.dumps({"changed": changed, "statuses": dict(Counter(statuses.values()))}))
            return 0
        if args.out is None:
            parser.error("--freeze requires --out")
        report = freeze_dataset(args.data, args.out)
        print(report.model_dump_json())
        return 0
    except (CorpusError, ManifestError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
