"""Does the scene editor carry a repaired reference's count onto a page?

Follows ref_repair_probe.py. One shipped page per repaired reference is redrawn through
`providers.edit_image` with the scene's stored prompt and the same references in the same order,
except that the repaired reference replaces the shipped one. One draw each, fixed seed. No judge
call: counting is by hand. Plan and pass rule: docs/capstone/model-probes-2026-10.md.

Run from `backend/`: `uv run python ../docs/product/evidence/scripts/ref_repair_page_check.py`
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from pipeline.prompt_optimizer import referenced_characters  # noqa: E402
from providers import edit_image, upload_reference  # noqa: E402
from contracts.story_memory import Character  # noqa: E402

CORPUS = REPO / "data" / "judge" / "corpus"
OUT = REPO / "data" / "judge" / "evaluations" / "ref-repair-probe-2026-10"
SEED = 11
MAX_CALLS = 6  # hard guard, about $0.18. Do not raise without new authorization.

# story, scene, repaired character, repaired reference file from ref_repair_probe.py
PAGES = [
    ("syn-002", "s4", "c1", "syn-002-c1-seed11.png"),
    ("syn-010", "s0", "c0", "syn-010-c0-seed11.png"),
    ("syn-012", "s1", "c1", "syn-012-c1-seed11.png"),
    ("syn-013", "s1", "c0", "syn-013-c0-seed11.png"),
    ("syn-015", "s0", "c0", "syn-015-c0-seed11.png"),
    ("syn-019", "s0", "c0", "syn-019-c0-seed22.png"),
]
assert len(PAGES) <= MAX_CALLS

calls = 0
for story, scene_id, repaired_id, repaired_file in PAGES:
    path = OUT / f"page-{story}-{scene_id}-seed{SEED}.png"
    if path.exists():
        print("skip", path.name, flush=True)
        continue
    memory = json.loads((CORPUS / "runs" / story / "memory.json").read_text(encoding="utf-8"))
    scene = next(s for s in memory["scenes"] if s["scene_id"] == scene_id)
    characters = [Character.model_validate(c) for c in memory["characters"]]
    # The same helper generate_scene uses, so "Image N is X" in the stored prompt still names url N.
    cast = referenced_characters(scene["characters_present"], characters)
    assert repaired_id in [c.char_id for c in cast]
    urls = [
        upload_reference(
            (OUT / repaired_file).read_bytes()
            if c.char_id == repaired_id
            else (CORPUS / "ref" / c.canonical_ref_image.replace("/", "_")).read_bytes()
        )
        for c in cast
    ]
    path.write_bytes(edit_image(scene["prompt"], urls, seed=SEED))
    calls += 1
    print("wrote", path.name, f"({len(urls)} references)", flush=True)

print(f"paid calls this run: {calls}")
