"""N=8 tally. A direction "resolves the holder" when it names one holder or says the characters
share/hold the one object between them. Scored by hand-checkable substrings, printed in full so
the classification can be audited.
"""
import json, pathlib, re, sys, collections

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
import pipeline.segment as S  # noqa: E402
from contracts.story_memory import Character, Location, StoryObject, TimelineEvent  # noqa: E402

BUNDLE, N = pathlib.Path(sys.argv[1]), int(sys.argv[2])
m = json.loads((BUNDLE / "runs/syn-901/memory.json").read_text(encoding="utf-8"))
units = S.split_sentences(m["input"]["redacted_text"])
chars = [Character.model_validate(c) for c in m["characters"]]
locs = [Location.model_validate(x) for x in m.get("locations", [])]
objs = [StoryObject.model_validate(x) for x in m.get("objects", [])]
tl = [TimelineEvent.model_validate(x) for x in m.get("timeline", [])]

full = S.SEGMENTATION_PROMPT
RULE = [ln for ln in full.split("\n") if "must resolve who holds it" in ln][0]
stripped = full.replace(RULE + "\n", "")
OLD_KA = "key_action (one visible action with subject and target)"
NEW_KA = (
    "key_action (one visible action with subject and target; if two or more characters act on the "
    "same object, the action must name which single character holds it, or say they hold the one "
    "object between them — never phrase it so each character would need their own copy)"
)
ARMS = {"control": stripped, "bullet(committed)": full, "inline": stripped.replace(OLD_KA, NEW_KA)}

SHARED = re.compile(r"\btogether\b|\bbetween them\b|\bshare\b|\bsharing\b|\btaking turns\b|\btake turns\b", re.I)
def resolved(ka: str, present: list[str]) -> bool:
    if SHARED.search(ka):
        return True
    # one holder named: exactly one character name precedes a holding verb
    holders = [c.name for c in chars if re.search(rf"\b{re.escape(c.name)}\b[^.]*?\b(holds|holding|pulls|reaches|dips)\b", ka)]
    subjects = [c.name for c in chars if re.search(rf"\b{re.escape(c.name)}\b", ka)]
    return len(subjects) > 1 and len(holders) == 1

tally = collections.Counter()
for arm, prompt in ARMS.items():
    S.SEGMENTATION_PROMPT = prompt
    print(f"\n=== {arm} ===", flush=True)
    for i in range(N):
        try:
            res = S.segment_scenes(units, chars, tl, locs, objs)
        except Exception as e:
            print(f" rep{i} FAILED {type(e).__name__}", flush=True); continue
        for sc in res.scenes:
            ka = sc.visual_direction.key_action
            names = [c.name for c in chars if re.search(rf"\b{re.escape(c.name)}\b", ka)]
            if "fan" not in ka.lower() or len(names) < 2:
                continue
            ok = resolved(ka, names)
            tally[(arm, "resolved" if ok else "UNRESOLVED")] += 1
            print(f" {'OK ' if ok else '   '} {ka}", flush=True)
S.SEGMENTATION_PROMPT = full
print("\n=== TALLY (multi-character directions naming the fan) ===")
for arm in ARMS:
    r, u = tally[(arm, "resolved")], tally[(arm, "UNRESOLVED")]
    print(f" {arm:20s} resolved {r:2d} / {r+u:2d}")
