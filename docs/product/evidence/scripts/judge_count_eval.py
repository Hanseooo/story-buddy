"""Can the REFERENCE judge count when the spec states a number?

Eval set: the 12 count-probe images, ground truth counted by hand.
Arm A = the shipping JUDGE_PROMPT verbatim. Arm B = the same prompt plus ONE sentence
making cardinality explicit. Everything else held: same subject line, same schema, same model.

Scored on whether `contradictions` names the count attribute. Every verdict is printed so the
classification can be re-checked by hand (ADR-055 D3).
"""
import json
import pathlib
import sys

sys.path.insert(0, r"C:\Users\Asus\Desktop\story-buddy\backend")
from contracts.story_memory import CharacterDescription, RefVerdict  # noqa: E402
from pipeline.char_bible import JUDGE_PROMPT, _data_uri, _describe  # noqa: E402
from pipeline.prompt_optimizer import filtered_description  # noqa: E402
from providers import judge  # noqa: E402

RUNS = pathlib.Path(r"C:\Users\Asus\Desktop\story-buddy\data\judge\corpus-smoke-h\runs")
IMGS = pathlib.Path(__file__).parent / "countprobe"

COUNT_RULE = (
    " When a stated attribute names a NUMBER of something, count them in the image and compare "
    "to the stated number. If the image shows a different number than the description states, "
    "that is a contradiction and must be listed."
)

# (file, story, char_id, keyword, stated, actual)  -- actual counted by hand this session
TRUTH = [
    ("quill-seed11", "syn-001", "c0", "eye", 3, 3),
    ("quill-seed22", "syn-001", "c0", "eye", 3, 2),
    ("quill-seed33", "syn-001", "c0", "eye", 3, 2),
    ("quill-seed44", "syn-001", "c0", "eye", 3, 3),
    ("quill-seed55", "syn-001", "c0", "eye", 3, 2),
    ("quill-seed66", "syn-001", "c0", "eye", 3, 3),
    ("mopsi-seed11", "syn-002", "c1", "leg", 6, 5),
    ("mopsi-seed22", "syn-002", "c1", "leg", 6, 4),
    ("mopsi-seed33", "syn-002", "c1", "leg", 6, 4),
    ("mopsi-seed44", "syn-002", "c1", "leg", 6, 4),
    ("mopsi-seed55", "syn-002", "c1", "leg", 6, 4),
    ("mopsi-seed66", "syn-002", "c1", "leg", 6, 4),
]

MAX_CALLS = 24
calls = 0
subjects: dict[tuple[str, str], str] = {}


def subject_for(story: str, char_id: str) -> str:
    if (story, char_id) not in subjects:
        m = json.loads((RUNS / story / "memory.json").read_text(encoding="utf-8"))
        char = next(c for c in m["characters"] if c["char_id"] == char_id)
        desc = CharacterDescription.model_validate(char["description"])
        desc = filtered_description(desc, m["style"]["prompt_fragment"])
        subjects[(story, char_id)] = _describe(desc, char["name"], notes=False)
    return subjects[(story, char_id)]


results: dict[str, list] = {"A": [], "B": []}
for arm, extra in (("A", ""), ("B", COUNT_RULE)):
    print(f"\n########## ARM {arm} {'(shipping prompt)' if not extra else '(+ count rule)'}")
    for name, story, char_id, kw, stated, actual in TRUTH:
        if calls >= MAX_CALLS:
            print("MAX_CALLS guard hit")
            break
        subject = subject_for(story, char_id)
        assert str(stated) in subject or {3: "three", 6: "six"}[stated] in subject, subject
        prompt = JUDGE_PROMPT.format(subject=subject) + extra
        img = _data_uri((IMGS / f"{name}.png").read_bytes())
        v: RefVerdict = judge(prompt, [img], RefVerdict)
        calls += 1
        flagged = any(kw in c.lower() for c in v.contradictions)
        should = actual != stated
        ok = flagged == should
        results[arm].append((name, should, flagged, ok))
        print(f"  {'PASS' if ok else 'FAIL'} {name} stated={stated} actual={actual} "
              f"should_flag={should} flagged={flagged}")
        print(f"       contradictions={v.contradictions}")

print("\n########## SUMMARY")
for arm in ("A", "B"):
    rows = results[arm]
    if not rows:
        continue
    tp = sum(1 for _, s, f, _ in rows if s and f)
    fn = sum(1 for _, s, f, _ in rows if s and not f)
    fp = sum(1 for _, s, f, _ in rows if not s and f)
    tn = sum(1 for _, s, f, _ in rows if not s and not f)
    print(f"arm {arm}: caught {tp}/{tp+fn} real mismatches, "
          f"false alarms {fp}/{fp+tn} correct images")
print(f"total judge calls: {calls}")
