"""ADR-055 Verification step 1 (free). Current code — inline prompt rule plus the D5 normalizer.
N segmentations, same inputs, counting multi-character directions that name the fan and whether
they resolve who holds it. Prints every direction so the classification can be re-checked by hand.
"""
import json
import pathlib
import re
import sys

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

SHARED = re.compile(
    r"\btogether\b|\bbetween them\b|\bshares?\b|\bsharing\b|\btakes? turns\b|\btaking turns\b", re.I
)


def resolved(ka: str) -> bool:
    if SHARED.search(ka):
        return True
    holders = [
        c.name for c in chars
        if re.search(rf"\b{re.escape(c.name)}\b[^.]*?\b(holds|holding|pulls|reaches|dips)\b", ka)
    ]
    subjects = [c.name for c in chars if re.search(rf"\b{re.escape(c.name)}\b", ka)]
    return len(subjects) > 1 and len(holders) == 1


ok = total = 0
for i in range(N):
    try:
        res = S.segment_scenes(units, chars, tl, locs, objs)
    except Exception as e:
        print(f" rep{i} FAILED {type(e).__name__}: {str(e)[:120]}", flush=True)
        continue
    for sc in res.scenes:
        ka = sc.visual_direction.key_action
        names = [c.name for c in chars if re.search(rf"\b{re.escape(c.name)}\b", ka)]
        if "fan" not in ka.lower() or len(names) < 2:
            continue
        good = resolved(ka)
        total += 1
        ok += good
        print(f" {'OK ' if good else '   '} {ka}", flush=True)

print(f"\nresolved {ok} / {total}")
