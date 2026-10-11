"""Read-only cuts of the October stage audit ($0, stdlib only, synthetic bundles only).

Joins the audit's AI reviews to the stored judge verdicts and answers four questions: which page
defects fall on human-only pages, what the scene redraws bought, how often each gate signal fires
on a page a reviewer called defective, and whether the reference check had already failed the
references a reviewer called defective. Inputs are local and git-ignored:
`data/judge/evaluations/stage-audit-2026-10/` and `data/judge/corpus/runs/syn-*/memory.json`.
The reviews are provisional (docs/capstone/pipeline-stage-audit-2026-10.md).

Run from the repo root: `uv run --project backend python docs/product/evidence/scripts/stage_audit_gate_cuts.py`
"""
import collections
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "data" / "judge"
AUDIT = ROOT / "evaluations" / "stage-audit-2026-10"
GATING = {"wrong_colour", "wrong_body_feature"}   # consistency_check.GATING_REASONS
DUP = {"duplicate_character", "extra_character"}

key = json.loads((AUDIT / "key.json").read_text(encoding="utf-8"))
reviews = []
for path in sorted(glob.glob(str(AUDIT / "reviews" / "img-*.jsonl"))):
    for line in open(path, encoding="utf-8"):
        if line.strip():
            review = json.loads(line)
            review["role"] = key[review["item_id"]].get("role")
            review["image_ref"] = key[review["item_id"]]["image_ref"]
            reviews.append(review)

attempts = {}
ref_verdicts = {}
scene_count = attempt_count = first_shipped_after_redraw = 0
for path in glob.glob(str(ROOT / "corpus" / "runs" / "syn-*" / "memory.json")):
    memory = json.loads(Path(path).read_text(encoding="utf-8"))
    for character in memory["characters"]:
        if character.get("canonical_ref_image"):
            ref_verdicts[character["canonical_ref_image"]] = character["ref_verdict"]
    for scene in memory["scenes"]:
        scene_count += 1
        attempt_count += len(scene["attempts"])
        if len(scene["attempts"]) > 1 and scene["attempts"][0]["image_ref"] == scene["final_image_ref"]:
            first_shipped_after_redraw += 1
        for attempt in scene["attempts"]:
            attempts[attempt["image_ref"]] = attempt


def majors(review, origin=None):
    return [
        d for d in review["defects"]
        if d["severity"] == "major" and (origin is None or d["origin"] == origin)
    ]


pages = [r for r in reviews if r["kind"] == "page"]
final = [r for r in pages if r["role"] == "final"]
rejected_first = [r for r in pages if r["role"] == "rejected_first"]
refs = [r for r in reviews if r["kind"] == "ref"]

print("1. Shipped pages by character kind")
for label, group in (
    ("human-only (no non_human tag)", [r for r in final if "non_human" not in r["scenario_tags"]]),
    ("non-human", [r for r in final if "non_human" in r["scenario_tags"]]),
):
    bad = [r for r in group if majors(r)]
    types = collections.Counter(t for r in bad for t in {d["type"] for d in majors(r)})
    print(f"  {label}: {len(bad)}/{len(group)} pages with a major; "
          f"duplicate or extra on {sum(1 for r in group if DUP & {d['type'] for d in majors(r)})}")
    print(f"    by type (pages): {dict(types.most_common())}")
human_refs = [r for r in refs if "non_human" not in r["scenario_tags"]]
print(f"  references with a major: {sum(1 for r in refs if majors(r))}/{len(refs)}; "
      f"human {sum(1 for r in human_refs if majors(r))}/{len(human_refs)}")

print("\n2. What the redraws bought")
shipped = {(r["story_id"], r["scene_id"]): r for r in final}
print(f"  scenes {scene_count}, attempts {attempt_count}, redraws {attempt_count - scene_count}")
print(f"  redrawn scenes where the first draw shipped anyway: {first_shipped_after_redraw}")
for label, origin in (("any major", None), ("generator-origin major", "generator")):
    table = collections.Counter()
    for first in rejected_first:
        last = shipped[(first["story_id"], first["scene_id"])]
        table[(bool(majors(first, origin)), bool(majors(last, origin)))] += 1
    print(f"  {len(rejected_first)} scenes where a redraw replaced the first draw, by {label}: "
          f"fixed {table[(True, False)]}, broken {table[(False, True)]}, "
          f"bad both {table[(True, True)]}, clean both {table[(False, False)]}")

print("\n3. Gate signals against the reviews")
for label, group in (("150 shipped pages", final), (f"all {len(pages)} reviewed page images", pages)):
    rows = []
    for review in group:
        attempt = attempts[review["image_ref"]]
        verdict = attempt.get("vlm_verdict")
        types = {d["type"] for d in majors(review)}
        rows.append({
            "any major": bool(majors(review)),
            "generator major": bool(majors(review, "generator")),
            "duplicate or extra": bool(DUP & types),
            "gate failed": not attempt["passed"],
            "scene contradictions": bool(attempt.get("scene_contradictions")),
            "gating reason": bool(GATING & set(attempt.get("failure_reasons") or [])),
            "same_character False": bool(verdict) and not verdict["same_character"],
            "anatomy_intact False": bool(verdict) and not verdict["anatomy_intact"],
            "subjects_unique False": bool(verdict) and not verdict["subjects_unique"],
        })
    print(f"  {label}: any major {sum(r['any major'] for r in rows)}, "
          f"generator major {sum(r['generator major'] for r in rows)}, "
          f"duplicate or extra {sum(r['duplicate or extra'] for r in rows)}")
    for signal, truth in (
        ("gate failed", "any major"),
        ("gate failed", "generator major"),
        ("scene contradictions", "generator major"),
        ("gating reason", "generator major"),
        ("same_character False", "generator major"),
        ("anatomy_intact False", "any major"),
        ("subjects_unique False", "duplicate or extra"),
    ):
        fired = [r for r in rows if r[signal]]
        hits = sum(r[truth] for r in fired)
        print(f"    {signal} -> {truth}: fired {len(fired)}, right {hits}, "
              f"missed {sum(r[truth] for r in rows) - hits}")

print("\n4. Reference check against the reviews")
table = collections.Counter()
types = collections.Counter()
for review in refs:
    verdict = ref_verdicts[review["image_ref"]]
    # char_bible.mint_reference accepts a draw on exactly this condition.
    accepted = not verdict["contradictions"] and verdict["text_free"]
    table[(accepted, bool(majors(review)))] += 1
    types.update({d["type"] for d in majors(review)})
print(f"  check failed, reviewer major: {table[(False, True)]}; "
      f"check failed, reviewer clean: {table[(False, False)]}; "
      f"check passed, reviewer major: {table[(True, True)]}; "
      f"check passed, reviewer clean: {table[(True, False)]}")
print(f"  major types (references): {dict(types.most_common())}")
