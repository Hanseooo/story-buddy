"""Can the shipping EDIT model repair a reference whose stated count the text-to-image model missed?

The count screen showed no text-to-image model draws a stated body count (ADR-056). The stored
reference check already names the miss on most of these references, so the open question is the
repair, not the detection. Each shipped reference goes to `providers.edit_image` (the production
edit path) with one hand-written instruction naming the count. One draw each, fixed seed. No judge
call: counting is by hand. Plan and pass rule: docs/capstone/model-probes-2026-10.md.

Run from `backend/`: `uv run python ../docs/product/evidence/scripts/ref_repair_probe.py`
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from providers import edit_image, upload_reference  # noqa: E402

CORPUS = REPO / "data" / "judge" / "corpus"
OUT = REPO / "data" / "judge" / "evaluations" / "ref-repair-probe-2026-10"
SEED = 11
# fal's content checker rejected syn-019 at seed 11 six times out of six (unbilled). Deviation from
# the plan, recorded in the probes doc: that one reference is drawn at seed 22.
RESEEDED = {"syn-019": 22}
MAX_CALLS = 9  # hard guard, about $0.27 at $0.03 a call. Do not raise without new authorization.

KEEP = " Keep the character, its colours, the art style and the plain background exactly the same."
SUBJECTS = [
    ("syn-002", "c1", "Add two more legs to the sheep so it has six legs in total, three on each side."),
    ("syn-004", "c0", "Add two more blue stripes on the gecko's back so there are exactly seven blue stripes."),
    ("syn-005", "c0", "Add a second pair of wings to the paper crane so it has four wings in total."),
    ("syn-010", "c0", "Replace the badger face with a head covered in leaves that has no face: no eyes, "
                      "no nose, no mouth. Give the head exactly five leaf ears."),
    ("syn-012", "c1", "Add one more leg on each side of the beetle so it has eight legs in total."),
    ("syn-013", "c0", "Replace the dark green blotches on the toad's back with exactly nine yellow spots."),
    ("syn-014", "c0", "Remove the face, the stick arms, the stick legs and the loose falling raindrops. Give "
                      "the cloud exactly nine raindrop-shaped feet in a row along its underside."),
    ("syn-015", "c0", "Move the lantern on the fish's side up onto its head so there are exactly three "
                      "lanterns on top of the head and none on the body."),
    ("syn-019", "c0", "Replace the two black dot eyes with two mismatched button eyes, one large blue button "
                      "and one small yellow button, and remove the button on the ear."),
]
assert len(SUBJECTS) <= MAX_CALLS

OUT.mkdir(parents=True, exist_ok=True)
calls = 0
for story, char_id, instruction in SUBJECTS:
    seed = RESEEDED.get(story, SEED)
    path = OUT / f"{story}-{char_id}-seed{seed}.png"
    if path.exists():
        print("skip", path.name, flush=True)
        continue
    memory = json.loads((CORPUS / "runs" / story / "memory.json").read_text(encoding="utf-8"))
    character = next(c for c in memory["characters"] if c["char_id"] == char_id)
    source = CORPUS / "ref" / character["canonical_ref_image"].replace("/", "_")
    url = upload_reference(source.read_bytes())
    path.write_bytes(edit_image(instruction + KEEP, [url], seed=seed))
    calls += 1
    print("wrote", path.name, flush=True)

print(f"paid calls this run: {calls}")
