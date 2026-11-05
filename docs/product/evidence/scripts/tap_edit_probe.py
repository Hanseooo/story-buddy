"""Would a reveal tap fix a count miss if it EDITED the reference with only the chip's wording?

Follow-up to `ref_repair_probe.py`, which used hand-written instructions. Here the instruction is
the tap's own `Be sure to include: {chip}.` with the chip verbatim from `reveal._chips`, plus the
fixed keep clause. Same references, model and seeds. One draw each, no judge call: counting is by
hand. Plan and pass rule: docs/capstone/model-probes-2026-10.md, "Tap wording as an edit".

Run from `backend/`: `uv run python ../docs/product/evidence/scripts/tap_edit_probe.py`
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from providers import edit_image, upload_reference  # noqa: E402

CORPUS = REPO / "data" / "judge" / "corpus"
OUT = REPO / "data" / "judge" / "evaluations" / "tap-edit-probe-2026-11"
SEED = 11
RESEEDED = {"syn-019": 22}  # same seeds as ref_repair_probe.py
MAX_CALLS = 9  # hard guard, about $0.27 at $0.03 a call. Do not raise without new authorization.

KEEP = " Keep the character, its colours, the art style and the plain background exactly the same."
SUBJECTS = [
    ("syn-002", "c1", "six legs"),
    ("syn-004", "c0", "seven blue stripes down back"),
    ("syn-005", "c0", "four wings"),
    ("syn-010", "c0", "five leaf ears"),
    ("syn-012", "c1", "eight legs"),
    ("syn-013", "c0", "nine spots on back"),
    ("syn-014", "c0", "rounded, floating mass with nine protruding raindrop feet"),
    ("syn-015", "c0", "three lanterns on head"),
    ("syn-019", "c0", "two mismatched buttons"),
]
assert len(SUBJECTS) <= MAX_CALLS

OUT.mkdir(parents=True, exist_ok=True)
calls = 0
for story, char_id, chip in SUBJECTS:
    seed = RESEEDED.get(story, SEED)
    path = OUT / f"{story}-{char_id}-seed{seed}.png"
    if path.exists():
        print("skip", path.name, flush=True)
        continue
    memory = json.loads((CORPUS / "runs" / story / "memory.json").read_text(encoding="utf-8"))
    character = next(c for c in memory["characters"] if c["char_id"] == char_id)
    source = CORPUS / "ref" / character["canonical_ref_image"].replace("/", "_")
    url = upload_reference(source.read_bytes())
    try:
        path.write_bytes(edit_image(f"Be sure to include: {chip}.{KEEP}", [url], seed=seed))
        print("wrote", path.name, flush=True)
    except Exception as exc:  # a content refusal is a miss under the pass rule; keep going
        print("failed", story, type(exc).__name__, str(exc)[:200], flush=True)
    calls += 1

print(f"calls this run: {calls}")
