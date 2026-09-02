"""Throwaway. Does an object-cardinality clause stop the generator duplicating a shared object?

Control vs treatment on the two scenes that duplicated in probe_out3, SAME SEED across arms so
the only variable is the clause. Reference images are the ones probe_out3 already paid for.
8 edit calls at ~$0.024 = ~$0.19.
"""
import json, pathlib, sys

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
from providers import edit_image, upload_reference  # noqa: E402

S = pathlib.Path(__file__).parent
BUNDLE = S / "probe_out3"
OUT = S / "dupprobe"
OUT.mkdir(exist_ok=True)

CLAUSE = "Draw each object named above exactly once."

mem = json.loads((BUNDLE / "runs/syn-901/memory.json").read_text(encoding="utf-8"))
prompts = {s["scene_id"]: s["prompt"] for s in mem["scenes"]}

refs = [
    upload_reference((BUNDLE / "ref" / f"syn-901--campaign-0ea01a00da7b7f4a6487878f555fb58b_ref-{c}-1.png").read_bytes())
    for c in ("c0", "c1")
]
print("refs uploaded", flush=True)


def treated(prompt: str) -> str:
    """Append the clause to the Visible objects block, before the next blank-line block."""
    head, sep, tail = prompt.partition("\n\nVisual direction:")
    assert sep, "no Visual direction block"
    return f"{head}\n{CLAUSE}{sep}{tail}"


for scene in ("s1", "s4"):
    for arm, prompt in (("ctrl", prompts[scene]), ("treat", treated(prompts[scene]))):
        for seed in (11, 22):
            path = OUT / f"{scene}-{arm}-{seed}.png"
            if path.exists():
                print("skip", path.name, flush=True)
                continue
            path.write_bytes(edit_image(prompt, refs, seed=seed))
            print("wrote", path.name, flush=True)

print("\nTREATED s1 PROMPT:\n" + treated(prompts["s1"]))
