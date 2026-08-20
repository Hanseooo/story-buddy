"""Pipeline output + the `annotations` table → `manifest.jsonl` (`judge-finetune.md` §5.3, §5.4).

This module owns the **one** polarity conversion in the project. `annotations.same_character` is
`true` for *same*; the manuscript's positive class is `1 = different_character`. The mapping
`label = not same_character` is applied in `build_records` and re-derived nowhere else
(`annotation-surface.md` §2.1) — inverting it flips precision and recall for Objective 4 while
every number still looks plausible.
"""
import hashlib
import itertools
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, NamedTuple

from app.db import get_supabase_client
from contracts.story_memory import Character, FailureReason, StoryMemory
from finetune.manifest import (
    ManifestError,
    ManifestRecord,
    PairType,
    Provenance,
    Split,
    local_image_path,
    write_manifest,
)

log = logging.getLogger(__name__)

ANNOTATIONS_TABLE = "annotations"

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


class Consensus(NamedTuple):
    """What the annotators (plus the adjudicator) agreed a pair is."""
    same_character: bool
    failure_reasons: list[str]
    anatomy_intact: bool = True
    text_free: bool = True
    adjudicated: bool = False


# --- pairing (§5.4 step 2 — a loop, not a labelling task) ------------------------------------

def mint_pair_id(char_id: str, scene_image: str) -> str:
    """Opaque and deterministic. Opaque because `annotate/` blinds on it (annotation-surface §2.1);
    deterministic because a re-run must line up with labels already collected against it."""
    return hashlib.sha256(f"{char_id}\0{scene_image}".encode()).hexdigest()[:16]


def pairs_from_memory(memory: StoryMemory) -> list[Pair]:
    """Every attempt image against the canonical reference of every character present in it.

    Reference first, scene second — order is load-bearing (§5.2), and it is the same order
    `providers.judge` sends them in.
    """
    by_id = {c.char_id: c for c in memory.characters}
    pairs = []
    for scene in memory.scenes:
        for char_id in scene.characters_present:
            character = by_id.get(char_id)
            if character is None or not character.canonical_ref_image:
                continue    # nothing to compare against; consistency_check skips these too
            for attempt in scene.attempts:
                pairs.append(Pair(
                    pair_id=mint_pair_id(char_id, attempt.image_ref),
                    char_id=char_id,
                    ref_image=character.canonical_ref_image,
                    scene_image=attempt.image_ref,
                ))
    return pairs


# --- the `annotations` table (ADR-026) -------------------------------------------------------

def fetch_annotations() -> list[dict]:
    """The one effect boundary of this module — mocked by every deterministic test.

    ponytail: read straight through the existing `app.db` Supabase seam rather than adding a
    function to `providers.py`. `providers.py` is the *vendor model* seam (ADR-015); this is a
    plain table read, and `app/classrooms.py`, `app/auth.py` and `worker/run_job.py` all read
    their tables exactly this way. Upgrade path: if a second consumer of `annotations` appears,
    lift this into `app/db.py` beside `get_supabase_client`.
    """
    return get_supabase_client().table(ANNOTATIONS_TABLE).select("*").execute().data or []


def fetch_adjudicator_ids() -> set[str]:
    data = get_supabase_client().table("profiles").select("id").eq("is_adjudicator", True).execute().data or []
    return {row["id"] for row in data}


def fetch_pilot_pairs() -> set[str]:
    data = get_supabase_client().table("research_pairs").select("id").eq("is_pilot", True).execute().data or []
    return {row["id"] for row in data}


def resolve_annotations(
    rows: Iterable[dict],
    adjudicators: set[str],
    pilot_pairs: set[str],
) -> dict[str, Consensus]:
    """Independent labels → one consensus per pair.

    Hard fails on invalid states: >2 ordinary annotations, <2 ordinary annotations,
    unresolved conflicts, multiple adjudicators, or adjudicator rows on agreeing pairs.
    Pilot pairs are silently excluded.

    The gating booleans fold worst-wins and the reasons union, mirroring `consistency_check`'s
    fold so a human label and a judge verdict are combined the same way.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["pair_id"] in pilot_pairs:
            continue
        grouped[row["pair_id"]].append(row)

    resolved: dict[str, Consensus] = {}
    for pair_id, pair_rows in grouped.items():
        ordinary = [r for r in pair_rows if r["annotator_id"] not in adjudicators]
        adjs = [r for r in pair_rows if r["annotator_id"] in adjudicators]

        if len(ordinary) > 2:
            raise ManifestError(f"Pair {pair_id} has >2 ordinary annotations.")
        if len(ordinary) < 2:
            continue

        if ordinary[0]["annotator_id"] == ordinary[1]["annotator_id"]:
            raise ManifestError(f"Pair {pair_id} has duplicate annotator_ids for ordinary annotations.")

        def get_sig(r: dict) -> tuple:
            return (
                bool(r.get("same_character")),
                bool(r.get("anatomy_intact", True)),
                bool(r.get("text_free", True)),
                tuple(sorted(r.get("failure_reasons") or [])),
            )

        signatures = {get_sig(r) for r in ordinary}
        if len(signatures) == 1:
            if len(adjs) > 0:
                log.warning(f"Pair {pair_id}: ordinary annotators agreed, but adjudicator row exists.")
            winner = bool(ordinary[0].get("same_character"))
            final_rows = ordinary
            adjudicated = False
        else:
            if len(adjs) == 0:
                raise ManifestError(f"Pair {pair_id}: unresolved conflict (no adjudicator).")
            if len(adjs) > 1:
                raise ManifestError(f"Pair {pair_id}: multiple adjudicator rows.")
            winner = bool(adjs[0].get("same_character"))
            final_rows = adjs
            adjudicated = True

        reasons: list[str] = []
        for row in final_rows:
            for reason in row.get("failure_reasons") or []:
                if reason not in reasons:
                    reasons.append(reason)

        resolved[pair_id] = Consensus(
            same_character=winner,
            failure_reasons=reasons,
            anatomy_intact=all(r.get("anatomy_intact", True) for r in final_rows),
            text_free=all(r.get("text_free", True) for r in final_rows),
            adjudicated=adjudicated,
        )
    return resolved


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
            continue

        records.append(ManifestRecord(
            pair_id=pair.pair_id,
            char_id=pair.char_id,
            split=split,
            provenance=provenance,
            pair_type=pair_type,
            # Storage paths -> the local files `build_corpus` wrote. LLaMA-Factory resolves these
            # against the filesystem, so the manifest must carry the on-disk name (manifest.py).
            images=[
                local_image_path(pair.ref_image, "ref"),
                local_image_path(pair.scene_image, "scene"),
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


def constructed_records(records: list[ManifestRecord]) -> list[ManifestRecord]:
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
) -> list[ManifestRecord]:
    """The entry point. Reads every annotation once, then writes a validated manifest and stats."""
    out_path = Path(out_path)
    adjudicators = fetch_adjudicator_ids()
    pilot_pairs = fetch_pilot_pairs()
    consensus = resolve_annotations(fetch_annotations(), adjudicators, pilot_pairs)

    records: list[ManifestRecord] = []
    for memory, split, provenance in corpus:
        records += build_records(memory, split, provenance, consensus, pilot_pairs)
    if add_constructed:
        records += constructed_records(records)

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
