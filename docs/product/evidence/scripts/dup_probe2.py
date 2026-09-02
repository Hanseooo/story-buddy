"""Arm 2. `prompt_optimizer.py:239` says the per-subject clause was insufficient for characters and
the CANVAS-level count is what contradicted compositing. Arm 1 tested only the per-subject analogue
and it failed 4/4. Test the canvas form, alone and paired, on s1 — the reliable reproducer.
4 edit calls, ~$0.10.
"""
import json, pathlib, sys

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
from providers import edit_image, upload_reference  # noqa: E402

S = pathlib.Path(__file__).parent
BUNDLE = S / "probe_out3"
OUT = S / "dupprobe"

COUNT = "This illustration contains exactly one bamboo fan."
EACH = "Draw each object named above exactly once."

mem = json.loads((BUNDLE / "runs/syn-901/memory.json").read_text(encoding="utf-8"))
base = {s["scene_id"]: s["prompt"] for s in mem["scenes"]}["s1"]

refs = [
    upload_reference((BUNDLE / "ref" / f"syn-901--campaign-0ea01a00da7b7f4a6487878f555fb58b_ref-{c}-1.png").read_bytes())
    for c in ("c0", "c1")
]
print("refs uploaded", flush=True)


def with_lines(*lines: str) -> str:
    head, sep, tail = base.partition("\n\nVisual direction:")
    return head + "\n" + "\n".join(lines) + sep + tail


arms = {"count": with_lines(COUNT), "both": with_lines(EACH, COUNT)}
for arm, prompt in arms.items():
    for seed in (11, 22):
        path = OUT / f"s1-{arm}-{seed}.png"
        if path.exists():
            print("skip", path.name, flush=True)
            continue
        path.write_bytes(edit_image(prompt, refs, seed=seed))
        print("wrote", path.name, flush=True)

print("\nCOUNT ARM OBJECT BLOCK:")
print(arms["count"].split("\n\n")[2])
