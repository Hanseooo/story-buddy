"""Does the ADR-054 D1 rule change what `segment` writes? Text-only A/B, no image spend.

probe_out4 came back with s1/s4 byte-identical to probe_out3 despite the rule being in the
prompt, so the single-draw image improvement is unattributable. Run the segmenter N times with
the rule and N times without, on the same inputs, and count directions that resolve the holder.
"""
import json, pathlib, sys, collections

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
import pipeline.segment as S  # noqa: E402
from contracts.story_memory import Character, Location, StoryObject, TimelineEvent  # noqa: E402

BUNDLE = pathlib.Path(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4

m = json.loads((BUNDLE / "runs/syn-901/memory.json").read_text(encoding="utf-8"))
units = S.split_sentences(m["input"]["redacted_text"])
chars = [Character.model_validate(c) for c in m["characters"]]
locs = [Location.model_validate(x) for x in m.get("locations", [])]
objs = [StoryObject.model_validate(x) for x in m.get("objects", [])]
tl = [TimelineEvent.model_validate(x) for x in m.get("timeline", [])]

RULE = [ln for ln in S.SEGMENTATION_PROMPT.split("\n") if "must resolve who holds it" in ln]
assert len(RULE) == 1, RULE
WITHOUT = S.SEGMENTATION_PROMPT.replace(RULE[0] + "\n", "")
assert WITHOUT != S.SEGMENTATION_PROMPT

full = S.SEGMENTATION_PROMPT
for arm, prompt in (("with-rule", full), ("without-rule", WITHOUT)):
    S.SEGMENTATION_PROMPT = prompt
    print(f"\n=== {arm} ===", flush=True)
    for i in range(N):
        try:
            res = S.segment_scenes(units, chars, tl, locs, objs)
        except Exception as e:
            print(f" rep{i} FAILED {type(e).__name__}: {str(e)[:120]}", flush=True)
            continue
        for sc in res.scenes:
            names = [objs[int(o[3:])].name if o.startswith("obj") else o for o in []]
            ka = sc.visual_direction.key_action
            if "fan" in ka.lower() and len(sc.characters_present) > 1:
                print(f" rep{i}: {ka}", flush=True)
S.SEGMENTATION_PROMPT = full
