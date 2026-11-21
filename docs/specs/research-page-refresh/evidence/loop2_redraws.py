"""Loop 2's gate, checked against the October pipeline audit (docs/capstone/pipeline-stage-audit-2026-10.md).

For every redrawn scene in the audit, compares the AI reviewers' verdicts on the rejected first draw and the
shipped page with the judge's own stored verdicts. Reads only gitignored local data under data/judge/; prints
counts, no story text. Run from the repo root: python docs/specs/research-page-refresh/evidence/loop2_redraws.py

Result on 2026-11-22: 71 redrawn scenes; 9 had a defective first draw and an acceptable shipped page; the
judge passed the shipped page in 1 of them (syn-001 s4), whose defect was an action (awake, not asleep),
not an off-model character. The other 8 shipped as the best-of fallback after every draw failed.
"""
import collections
import glob
import json
import pathlib

AUDIT = pathlib.Path("data/judge/evaluations/stage-audit-2026-10")
RUNS = pathlib.Path("data/judge/corpus/runs")

key = json.loads((AUDIT / "key.json").read_text(encoding="utf8"))
review = {}
for f in glob.glob(str(AUDIT / "reviews/img-*.jsonl")):
    for line in open(f, encoding="utf8"):
        if line.strip():
            r = json.loads(line)
            review[r["item_id"]] = r

scenes = collections.defaultdict(dict)
for item, v in key.items():
    if v["kind"] == "page":
        scenes[(v["story_id"], v["scene_id"])][v["role"]] = item

redrawn = {s: d for s, d in scenes.items() if "rejected_first" in d}
fixed = {s: d for s, d in redrawn.items()
         if review[d["rejected_first"]]["verdict"] == "defect" and review[d["final"]]["verdict"] == "acceptable"}
print("redrawn scenes:", len(redrawn))
print("defective first draw, acceptable shipped page:", len(fixed))
for (story, scene), d in sorted(fixed.items()):
    memory = json.loads((RUNS / story / "memory.json").read_text(encoding="utf8"))
    s = next(x for x in memory["scenes"] if x["scene_id"] == scene)
    shipped = next(a for a in s["attempts"] if a["image_ref"] == s["final_image_ref"])
    majors = [x["type"] for x in review[d["rejected_first"]]["defects"] if x["severity"] == "major"]
    print(f"  {story} {scene}: judge passed shipped page = {shipped['passed']}; reviewer's major defects = {majors}")
