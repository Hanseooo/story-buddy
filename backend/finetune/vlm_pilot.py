"""Exploratory, synthetic-train-only two-image VLM screen. Not an Objective-4 evaluation.

Run only with a separately capped OpenRouter key. Results append after each call so a
partial run can resume without paying again for completed model/pair combinations.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from app.config import settings
from finetune.manifest import read_manifest
from pipeline.consistency_check import JUDGE_PROMPT, JUDGE_PROMPT_VERSION, SceneVerdict
from providers import judge_with_metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--challenger-model", required=True)
    parser.add_argument("--probe", action="store_true", help="Run the first pair with both models")
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    manifest_path = args.freeze / "manifest.train.jsonl"
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if digest != selection["train_manifest_sha256"]:
        raise ValueError("training manifest changed since pilot selection")
    records = {record.pair_id: record for record in read_manifest(manifest_path)}
    pair_ids = selection["pair_ids"][:1] if args.probe else selection["pair_ids"]
    if len(set(selection["pair_ids"])) != len(selection["pair_ids"]):
        raise ValueError("pilot selection has duplicate pair IDs")
    for pair_id in selection["pair_ids"]:
        record = records.get(pair_id)
        if record is None or (record.split, record.provenance, record.pair_type) != (
            "train", "synthetic", "pipeline"
        ):
            raise ValueError(f"{pair_id}: not an eligible synthetic training pipeline pair")
        if any(not (args.freeze / image).is_file() for image in record.images):
            raise ValueError(f"{pair_id}: image asset missing")

    models = (settings.vlm_judge_model, args.challenger_model)
    if models[0] == models[1]:
        raise ValueError("challenger must differ from incumbent")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if args.out.exists():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = (row["pair_id"], row["model_id"])
            if key in existing:
                raise ValueError(f"duplicate existing result: {key}")
            existing[key] = row
    if any(pair_id not in selection["pair_ids"] or model not in models for pair_id, model in existing):
        raise ValueError("output contains a pair or model outside this pilot")
    if not args.probe and any(
        existing.get((selection["pair_ids"][0], model), {}).get("parse_status") != "parsed"
        for model in models
    ):
        raise ValueError("both one-pair schema probes must parse before the full screen")

    prompt = JUDGE_PROMPT.format(name="the character")
    with args.out.open("a", encoding="utf-8") as out:
        for pair_id in pair_ids:
            record = records[pair_id]
            if all((pair_id, model) in existing for model in models):
                continue
            images = []
            for relative in record.images:
                path = args.freeze / relative
                mime = "image/png" if path.suffix.lower() == ".png" else "image/webp"
                images.append(f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode())
            for model in models:
                if (pair_id, model) in existing:
                    continue
                row = {
                    "pair_id": pair_id,
                    "char_id": record.char_id,
                    "label_different": record.label,
                    "model_id": model,
                    "prompt_version": JUDGE_PROMPT_VERSION,
                }
                try:
                    result = judge_with_metadata(
                        prompt, images, SceneVerdict, model=model, route="openrouter"
                    )
                    row.update(
                        parse_status="parsed",
                        predicted_different=not result.verdict.same_character,
                        same_character=result.verdict.same_character,
                        failure_reasons=[reason.value for reason in result.verdict.failure_reasons],
                        latency_ms=result.latency_ms,
                        generation_id=result.generation_id,
                    )
                except Exception as exc:
                    row.update(parse_status="error", error_type=type(exc).__name__)
                    if getattr(exc, "status_code", None) is not None:
                        row["http_status"] = exc.status_code
                out.write(json.dumps(row, sort_keys=True) + "\n")
                out.flush()
                os.fsync(out.fileno())
                print(f"{pair_id} {model}: {row['parse_status']}", flush=True)
                if row.get("http_status") == 402:
                    raise RuntimeError("capped OpenRouter key has no remaining credit")


if __name__ == "__main__":
    main()
