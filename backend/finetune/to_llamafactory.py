"""`manifest.jsonl` → sharegpt JSON + `dataset_info.json` (`judge-finetune.md` §6.1).

A BUILD ARTIFACT. Regenerate it, never edit it. Two rules, both silent when broken:

1. The number of `<image>` tokens must equal `len(images)` — the one rule the LLaMA-Factory
   loader enforces, and the one thing that will silently corrupt a run.
2. The `gpt` turn is the verdict serialized exactly as the production Pydantic schema serializes
   it. The schema is imported and its serializer called; the JSON is never hand-written. Train on
   a different byte sequence and you have trained the model to emit something `providers.judge()`
   cannot read.
"""
import json
from pathlib import Path

from contracts.story_memory import VlmVerdict
from finetune.manifest import ManifestRecord, read_manifest

# Mirrors `pipeline/consistency_check.JUDGE_PROMPT`'s shape — reason first, then score (ADR-004).
# Deliberately free of the character's name: the manifest's `char_id`/`name` are bookkeeping and
# must not leak into the training text (§5.3).
QUESTION = (
    "The FIRST image is a canonical character reference. The SECOND image is one page of a "
    "picture book in which that character should appear drawn to match the reference.\n\n"
    "First describe every difference you observe between the character on the page and the "
    "reference. Then say whether it is the same character; list which of the reference's "
    "attributes are actually present on the page; whether the page is drawn in the same art "
    "style as the reference; whether the character's anatomy is intact; whether the character is "
    "drawn exactly once; and whether the picture is free of any text. Finally list the failure "
    "reasons that apply, choosing only from the fixed set."
)

DATASET_INFO = {
    f"storybuddy_judge_{split}": {
        "file_name": f"{split}.json",
        "formatting": "sharegpt",
        "columns": {"messages": "conversations", "images": "images"},
    }
    for split in ("train", "val", "test")
}


def verdict_json(record: ManifestRecord) -> str:
    """The training target, produced by the production schema's own serializer.

    `VlmVerdict` carries the six verdict fields; `failure_reasons` is a sibling field on
    `Attempt`, and the wire shape `providers.judge` parses is the node-local `SceneVerdict` —
    `VlmVerdict`'s fields in declaration order, then `failure_reasons` last. Appending to the
    dump reproduces that byte-for-byte without importing a pipeline node into research tooling.

    ponytail: `subjects_unique` and `style_match` are omitted from the constructor deliberately —
    they are the two NON-GATING fields on `VlmVerdict` and are not annotated (see `manifest.py`),
    so they take their schema defaults. Upgrade path: annotate them if either is promoted to
    gating, and pass them through here in the same change.
    """
    verdict = VlmVerdict(
        differences_observed=record.differences_observed,
        same_character=record.same_character,
        anatomy_intact=record.anatomy_intact,
        text_free=record.text_free,
    )
    payload = verdict.model_dump(mode="json")
    payload["failure_reasons"] = [r.value for r in record.failure_reasons]
    return json.dumps(payload)


def to_sharegpt(record: ManifestRecord) -> dict:
    return {
        "conversations": [
            {"from": "human", "value": "<image>" * len(record.images) + QUESTION},
            {"from": "gpt", "value": verdict_json(record)},
        ],
        "images": list(record.images),
    }


def write_dataset(records: list[ManifestRecord], out_dir: Path) -> None:
    """One JSON file per split plus the registration file LLaMA-Factory reads."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        examples = [to_sharegpt(r) for r in records if r.split == split]
        (out_dir / f"{split}.json").write_text(json.dumps(examples, indent=2), encoding="utf-8")
    (out_dir / "dataset_info.json").write_text(json.dumps(DATASET_INFO, indent=2), encoding="utf-8")


def main(manifest: Path = Path("data/judge/manifest.jsonl"), out_dir: Path = Path("data/judge")) -> None:
    write_dataset(read_manifest(manifest), out_dir)   # read_manifest runs the §3.2 guard


if __name__ == "__main__":   # pragma: no cover
    main()
