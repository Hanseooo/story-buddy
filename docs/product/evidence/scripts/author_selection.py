"""Author `data/judge/intake/dataset_selection.json` — Phase C1, 2026-09-17.

Costs USD 0: reads the committed bundles and the donated intake, makes no provider call and no
database write. Run from `backend/`, which is where the venv lives:

    uv run python ../docs/product/evidence/scripts/author_selection.py

It exists so the frozen artifact is reproducible rather than hand-authored. ADR-057 Decision 3 says
the achieved constructed-pair count is *reported, not targeted*, and that no selection decision may
be made after seeing it. A script that applies a rule fixed in advance is how that commitment is
kept visible; picking targets by hand after reading the yields is exactly what it forbids.

Two mechanical rules, both content-blind:

  hard negatives   each eligible reference takes the FIRST target in `candidate_report`'s own
                   ordering, which is lexicographic by `target_char_id`. Eligibility is
                   `candidate_report`'s, so species and style equality are unchanged (ADR-057
                   Decision 2). A reference with no eligible partner carries no match, which is
                   legal under Decision 1.
  donated          each primary with no completed bundle is replaced by an unspent backup of the
                   same style, pairing the two lists in lexicographic order. Style equality is the
                   freeze's own rule; the ordering is arbitrary but fixed, and the resulting
                   selected set is identical under any pairing because every same-style backup is
                   spent either way.

Refuses to overwrite an existing selection. The artifact is frozen before annotation begins and its
SHA-256 is recorded in the freeze, so a silent rewrite would invalidate collected labels.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from finetune.build_dataset import pairs_from_memory          # noqa: E402
from finetune.corpus_io import load_completed_bundles, load_intake  # noqa: E402
from finetune.dataset_selection import candidate_report, lineage_id  # noqa: E402

DATA = ROOT / "data" / "judge" / "corpus"
INTAKE = ROOT / "data" / "judge" / "intake" / "donated.json"
OUT = ROOT / "data" / "judge" / "intake" / "dataset_selection.json"
EVIDENCE = "docs/specs/obj4-readiness-audit.md §7 + data/judge/corpus/build_state.json"


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite {OUT} — the selection is frozen; delete it deliberately first")
        return 1

    now = datetime.now(timezone.utc).replace(microsecond=0)
    bundles = load_completed_bundles(DATA)

    report = candidate_report(bundles)
    matches = [
        {"reference_char_id": row["reference_char_id"],
         "target_char_id": row["candidates"][0]["target_char_id"]}
        for row in report if row["candidates"]
    ]

    built = {b.memory.story_id for b in bundles}
    missing: dict[str, list[str]] = {}
    spare: dict[str, list[str]] = {}
    for rec in load_intake(INTAKE, mode="freeze_audit"):
        if rec.candidate_role == "primary" and rec.story_id not in built:
            missing.setdefault(rec.style_preset_id, []).append(rec.story_id)
        elif rec.candidate_role == "backup" and rec.story_id in built:
            spare.setdefault(rec.style_preset_id, []).append(rec.story_id)

    state = json.loads((DATA / "build_state.json").read_text(encoding="utf-8"))
    replacements = []
    for style, primaries in sorted(missing.items()):
        backups = sorted(spare.get(style, []))
        if len(backups) < len(primaries):
            print(f"{style}: {len(primaries)} primaries missing, only {len(backups)} backups built")
            return 1
        for primary, backup in zip(sorted(primaries), backups):
            replacements.append({
                "primary_story_id": primary,
                "backup_story_id": backup,
                # The run terminated without a bundle. don-013 is `budget_stopped` rather than a
                # crash, so it was recoverable in principle — the campaign ceiling was spent on the
                # synthetic equality instead (audit §7.1), and the reason_code below says so.
                "reason": "terminal_pipeline_failure",
                "approved_at": now.isoformat(),
                "evidence_ref": f"{EVIDENCE}: {primary} reason_code={state[primary]['reason_code']}",
            })

    payload = {
        "hard_negatives_frozen_at": now.isoformat(),
        "hard_negative_matches": matches,
        "donated_replacements": sorted(replacements, key=lambda r: r["primary_story_id"]),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    per_char: Counter[str] = Counter()
    for bundle in bundles:
        if bundle.provenance == "synthetic" and bundle.split == "train":
            for pair in pairs_from_memory(bundle.memory):
                per_char[lineage_id(bundle.memory.story_id, pair.char_id)] += 1
    constructed = sum(per_char[m["target_char_id"]] for m in matches)

    print(f"wrote {OUT}")
    print(f"  hard-negative matches   : {len(matches)} of {len(report)} synthetic train references")
    print(f"  constructed train pairs : {constructed}  (achieved, reported per ADR-057 Decision 3)")
    print(f"  natural train pairs     : {sum(per_char.values())}")
    for r in payload["donated_replacements"]:
        print(f"  replacement             : {r['primary_story_id']} -> {r['backup_story_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
