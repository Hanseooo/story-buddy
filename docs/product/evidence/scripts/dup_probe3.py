"""Arm 3. Two clause variants failed 8/8, so the lever is probably not the objects block at all.

s3 ("paint the bamboo fan together") was the one multi-actor scene that did NOT duplicate. Test
whether the DIRECTION's phrasing is what decides it: same prompt, same seeds, only key_action
rewritten so the object has a single holder or is explicitly shared. If these come back single,
the fix belongs in `segment`, not `prompt_optimizer`. 4 edit calls, ~$0.10.
"""
import json, pathlib, sys

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
from providers import edit_image, upload_reference  # noqa: E402

S = pathlib.Path(__file__).parent
BUNDLE = S / "probe_out3"
OUT = S / "dupprobe"

ORIGINAL = "Mila and Tala shake the bamboo fan outside in the rain both look at the falling rain"
ARMS = {
    "holder": "Tala holds the one bamboo fan and shakes it while Mila watches the falling rain",
    "shared": "Mila and Tala together shake the one bamboo fan they are both holding, both look at the falling rain",
}

mem = json.loads((BUNDLE / "runs/syn-901/memory.json").read_text(encoding="utf-8"))
base = {s["scene_id"]: s["prompt"] for s in mem["scenes"]}["s1"]
assert ORIGINAL in base

refs = [
    upload_reference((BUNDLE / "ref" / f"syn-901--campaign-0ea01a00da7b7f4a6487878f555fb58b_ref-{c}-1.png").read_bytes())
    for c in ("c0", "c1")
]
print("refs uploaded", flush=True)

for arm, action in ARMS.items():
    prompt = base.replace(ORIGINAL, action)
    for seed in (11, 22):
        path = OUT / f"s1-{arm}-{seed}.png"
        if path.exists():
            print("skip", path.name, flush=True)
            continue
        path.write_bytes(edit_image(prompt, refs, seed=seed))
        print("wrote", path.name, flush=True)
