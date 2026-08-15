"""visual-continuity §7.1 — rescore the five checked-in `sample-dataset/` images.

⚠️ **Tier B — never CI.** Real judge calls, real money. No fal images: every picture is already
on disk, so this run costs VLM calls only.

    uv run python -m spikes.visual_continuity_7_1

Reads `sample-dataset/labels.json`, which YOU fill in first — one entry per image:

    [
      {
        "image": "BDjkzxf1Xc3bOuKR1F655.png",
        "constraints": "Visible characters: Ana, the shadow wizard.\\nAna: girl, ...",
        "subjects": [["the shadow wizard", "refs/wizard.png"]],
        "expect": "clean"
      }
    ]

- `constraints` is the text block the scene judge is held to. Paste the frozen profiles, the
  visible cast, the visible objects and the visual direction exactly as the pipeline would build
  them — the judge's answer is only about the constraints you gave it.
- `subjects` is optional: `[name, reference-image path]` pairs, relative to `sample-dataset/`.
  Omit it and only the composition half runs. The reference PNGs from job 3cc05c4b are not in the
  repo; drop them beside the scenes if you still have them.
- `expect` is YOUR label, printed beside the machine's answer. Free prose. `"clean"` means you
  see nothing wrong. This is the single-rater comparison §7.1 asks for; nothing here scores it.

The prompts are imported from `consistency_check`, never copied — a rescore that measures a
prompt this file owns would measure nothing about the shipped pipeline.
"""
import base64
import json
import sys
from pathlib import Path

from pipeline.consistency_check import (
    JUDGE_PROMPT,
    SCENE_CONSTRAINT_PROMPT,
    SceneConstraintVerdict,
    SceneVerdict,
)
from providers import judge

DATASET = Path(__file__).resolve().parents[2] / "sample-dataset"


def _uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> int:
    labels_path = DATASET / "labels.json"
    if not labels_path.exists():
        print(f"missing {labels_path} — see this module's docstring for the shape", file=sys.stderr)
        return 1

    only = set(sys.argv[1:])
    for entry in json.loads(labels_path.read_text(encoding="utf-8")):
        if only and entry["image"] not in only:
            continue
        scene = _uri(DATASET / entry["image"])
        print(f"\n=== {entry['image']}")
        print(f"  human : {entry.get('expect', '(unlabelled)')}")

        composition = judge(
            SCENE_CONSTRAINT_PROMPT.format(constraints=entry["constraints"]),
            [scene],
            SceneConstraintVerdict,
        )
        print(f"  judge : {composition.contradictions or 'clean'}")
        print(f"  prose : {composition.differences_observed}")

        for name, ref in entry.get("subjects", []):
            try:
                verdict = judge(
                    JUDGE_PROMPT.format(name=name),
                    [_uri(DATASET / ref), scene],
                    SceneVerdict,
                )
            except Exception as exc:
                # Same posture as `judge_attempt`: an unavailable check is unavailable, not a
                # failure of the image. Keeps one flaky call from discarding the other eight.
                print(f"  id[{name}] UNAVAILABLE — {type(exc).__name__}: {exc}")
                continue
            print(
                f"  id[{name}] same={verdict.same_character} "
                f"reasons={sorted({r.value for r in verdict.failure_reasons})}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
