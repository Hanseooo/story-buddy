"""Count donated scenes carrying an age or costume change — Phase C1a, 2026-09-17.

Evidence for Finding J (`docs/specs/obj4-readiness-audit.md §5`). Costs USD 0: reads the committed
bundles only, no provider call and no database write. Run from `backend/`:

    uv run python ../docs/product/evidence/scripts/count_narrative_changes.py

Report only — it selects and excludes nothing (preregistration §9.7). Two tiers, because the
boundary is the finding:

  named    the direction states the change in words the image model receives. This is the set
           Finding J calls at risk: `build_prompt` sends the character's frozen axes and this
           direction, never the story text, so a change the direction does not name is not drawn.
  implied  the direction implies an age gap through a relation or a time word without naming it
           ("Ana's daughter", "future"). The generator still draws the frozen child reference, so
           these are NOT at risk by Finding J's criterion — counted so the headline is not silently
           narrow, and so a reader can see where the line was drawn.

Keyword-matched and then printed in full, because a keyword list both over- and under-counts and
the listing is what makes the number checkable. don-014:s6 is a known false positive: the "younger
cousin" is a second character, not Lily at a different age.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from finetune.corpus_io import load_completed_bundles  # noqa: E402
from finetune.dataset_selection import prepare_dataset_bundles  # noqa: E402

NAMED_AGE = r"\b(?:older|younger|grown[- ]?up|grown|adult|elderly|aged|as an adult|as a child|child again|teenager|baby|old(?:er)? (?:wo)?man)\b"
NAMED_COSTUME = r"\b(?:costume|disguise|dressed as|changes? into|now wears?|puts? on (?:his|her|their|a|the)|wearing (?:a )?(?:new|different)|uniform|cloak|mask|crown|nightgown|py[jg]amas|different clothes|no longer wears?)\b"
IMPLIED = r"\b(?:her|his|their|\w+'s)\s+(?:daughter|son|grandchild|grandson|granddaughter|own child)\b|\byears?\s+later\b|\bfuture\b"

bundles = load_completed_bundles(ROOT / "data" / "judge" / "corpus")
selected, _, _ = prepare_dataset_bundles(
    bundles, ROOT / "data" / "judge" / "intake" / "donated.json",
    ROOT / "data" / "judge" / "intake" / "dataset_selection.json",
)
donated = sorted((b for b in selected if b.provenance == "donated"), key=lambda b: b.memory.story_id)

total = 0
named, implied = [], []
for bundle in donated:
    for scene in bundle.memory.scenes:
        if not scene.final_image_ref:
            continue
        total += 1
        vd = scene.visual_direction or ""
        age = re.search(NAMED_AGE, vd, re.I)
        cos = re.search(NAMED_COSTUME, vd, re.I)
        imp = re.search(IMPLIED, vd, re.I)
        row = (bundle.memory.story_id, scene.scene_id, vd)
        if age or cos:
            kind = ",".join(k for k, m in (("age", age), ("costume", cos)) if m)
            named.append((*row, kind, (age or cos).group(0)))
        elif imp:
            implied.append((*row, "implied", imp.group(0)))

print(f"donated stories in the held-out set : {len(donated)}")
print(f"finalized donated scenes            : {total}")
print(f"  visual direction NAMES an age or costume change : {len(named)} ({len(named) / total:.1%})")
print(f"  age gap implied but NOT named                   : {len(implied)} ({len(implied) / total:.1%})")
for label, rows in (("NAMED", named), ("IMPLIED", implied)):
    print(f"\n{label}")
    for sid, scene_id, vd, kind, term in rows:
        print(f"  {sid}:{scene_id}  [{kind}: {term!r}]\n      {vd[:200]}")
