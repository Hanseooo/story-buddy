"""Can the SHIPPING reference model hit a stated numeric attribute at all?

Same prompt char_bible builds, same negatives, `fal-ai/qwen-image`, N fixed seeds per subject.
Question: does ANY draw show six legs (Mopsi) / three eyes (Quill)?
Hit  -> generator is capable, the judge's false pass is the bottleneck (ADR-018 fine-tune).
Miss -> generator limit, and only then is the ADR-001 escalation ladder worth its cost.
No judge call: the judge is the thing under suspicion. Counting is by hand.
"""
import json
import pathlib
import sys

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
from contracts.story_memory import CharacterDescription  # noqa: E402
from pipeline.char_bible import (  # noqa: E402
    NON_HUMAN_NEGATIVE,
    REFERENCE_NEGATIVE,
    reference_prompt,
)
from pipeline.prompt_optimizer import filtered_description  # noqa: E402
from providers import text_to_image  # noqa: E402

CORPUS = pathlib.Path(r"C:\Users\Asus\Desktop\story-buddy\data\judge\corpus-smoke-h\runs")
OUT = pathlib.Path(__file__).parent / "countprobe"
OUT.mkdir(exist_ok=True)

SEEDS = [11, 22, 33, 44, 55, 66]
MAX_CALLS = 12  # hard guard: ~$0.19 at $0.02/MP. Do not raise without new authorization.

SUBJECTS = [
    ("mopsi", "syn-002", "c1", "six legs"),
    ("quill", "syn-001", "c0", "three amber eyes"),
]

calls = 0
for tag, story, char_id, target in SUBJECTS:
    m = json.loads((CORPUS / story / "memory.json").read_text(encoding="utf-8"))
    char = next(c for c in m["characters"] if c["char_id"] == char_id)
    desc = CharacterDescription.model_validate(char["description"])
    frag = m["style"]["prompt_fragment"]
    desc = filtered_description(desc, frag)
    prompt = reference_prompt(desc, char["name"], frag)
    neg = REFERENCE_NEGATIVE if desc.is_humanoid else f"{REFERENCE_NEGATIVE}, {NON_HUMAN_NEGATIVE}"

    print(f"\n=== {tag} ({char['name']}) target: {target}")
    print(f"PROMPT: {prompt}\n")
    # ADR-001's near-miss: a silent contract mismatch reads as a substrate result.
    # Assert the spec text actually reached the prompt before trusting any count.
    assert target.split()[0] in prompt.lower(), f"spec number missing from prompt: {target}"

    for seed in SEEDS:
        if calls >= MAX_CALLS:
            print("hit MAX_CALLS guard")
            break
        img = text_to_image(prompt, seed=seed, negative_extra=neg)
        calls += 1
        p = OUT / f"{tag}-seed{seed}.png"
        p.write_bytes(img)
        print(f"  seed {seed} -> {p.name} ({len(img)} bytes)")

print(f"\ntotal calls: {calls}")
