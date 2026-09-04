"""Phase C rehearsal: can a valid dataset_selection.json exist for this corpus?

Run from backend/:  uv run python <this> ../data/judge/corpus-smoke-h

Free. No provider calls, no DB writes. Loads the real corpus-smoke-h bundles.
"""
import sys, itertools
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from finetune.corpus_io import load_completed_bundles
from finetune.dataset_selection import (
    DatasetSelection, lineage_id, validate_hard_negative_matches,
)
from finetune.manifest import ManifestError

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/judge/corpus-smoke-h")

bundles = load_completed_bundles(DATA)
print("bundles loaded:", [b.memory.story_id for b in bundles])

train = [b for b in bundles if b.provenance == "synthetic" and b.split == "train"]
chars = {}
for b in train:
    style = str(b.run_metadata.get("style_preset_id", ""))
    counts = Counter()
    for sc in b.memory.scenes:
        if sc.final_image_ref:
            for cid in sc.characters_present:
                counts[cid] += 1
    for ch in b.memory.characters:
        if not ch.canonical_ref_image:
            continue
        lid = lineage_id(b.memory.story_id, ch.char_id)
        chars[lid] = ((ch.description.species or "").strip(), style, counts[ch.char_id])

print("\ntrain characters requiring a hard-negative match:", len(chars))
for lid, (sp, st, n) in sorted(chars.items()):
    print("  %-14s species=%-14r style=%-9s scenes=%d" % (lid, sp, st, n))

# Best possible attempt: pair anything that legally can be paired.
matches = []
for a, b_ in itertools.permutations(sorted(chars), 2):
    sa, ta, _ = chars[a]
    sb, tb, nb = chars[b_]
    if sa.casefold() == sb.casefold() and ta == tb and nb >= 1:
        if a not in {m["reference_char_id"] for m in matches}:
            matches.append({"reference_char_id": a, "target_char_id": b_})

print("\nlegal pairings found: %d / %d characters" % (len(matches), len(chars)))
for m in matches:
    print("  ", m)

sel = DatasetSelection.model_validate({
    "hard_negatives_frozen_at": datetime.now(timezone.utc).isoformat(),
    "hard_negative_matches": matches,
    "donated_replacements": [],
})

print("\ncalling validate_hard_negative_matches ...")
try:
    validate_hard_negative_matches(bundles, sel, [], set())
    print("PASS -- a valid selection exists")
except (ManifestError, Exception) as exc:
    print("FAIL -- %s: %s" % (type(exc).__name__, exc))
