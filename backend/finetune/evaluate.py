"""The four baselines of `judge-finetune.md` §7.3, scored on the `different_character` class.

⚠️ **Tier B — offline eval harness, never CI** (MASTER_SPEC §6, AGENTS.md "Testing bright line").
It calls real models and costs real money. Only the pure metric helpers at the top are unit
tested; nothing here asserts on generated content.

The metric is F1 on `different_character` — the minority class, the class the control loop acts
on, and the class where a miss ships a broken page to a child (§3.3). `ManifestRecord.label` is
already that class; it is read, never re-derived (`build_dataset.py` owns the inversion).
"""
import json
import logging
from pathlib import Path
from typing import Callable, Iterable, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from contracts.story_memory import VlmVerdict
from finetune.evaluation_metrics import clustered_f1_ci, prf1
from finetune.manifest import ManifestError, ManifestRecord, read_manifest
from finetune.to_llamafactory import QUESTION

log = logging.getLogger(__name__)

Judge = Callable[[ManifestRecord], bool]      # record → predicted `different_character`


class JudgeObservation(BaseModel):
    prediction: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score: float | None = None
    latency_ms: int = Field(ge=0)


class PredictionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pair_id: str
    char_id: str
    split: Literal["val", "test"]
    judge_id: str
    prediction: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score: float | None = None
    latency_ms: int = Field(ge=0)
    parse_status: Literal["parsed", "malformed"]
    model_id: str
    adapter_id: str | None = None
    prompt_version: str
    threshold_id: str | None = None
    checkpoint_id: str | None = None


def validate_prediction_alignment(
    records: Sequence[ManifestRecord], predictions: Sequence[PredictionRecord]
) -> None:
    if len(records) != len(predictions):
        raise ManifestError(f"alignment error: {len(records)} records vs {len(predictions)} predictions")
    for r, p in zip(records, predictions):
        if r.pair_id != p.pair_id:
            raise ManifestError(f"alignment error: expected pair_id {r.pair_id}, got {p.pair_id}")
        if r.char_id != p.char_id:
            raise ManifestError(f"alignment error: expected char_id {r.char_id}, got {p.char_id}")
        if r.split != p.split:
            raise ManifestError(f"alignment error: expected split {r.split}, got {p.split}")


def capture_predictions(
    records: Sequence[ManifestRecord],
    judge_id: str,
    predict_fn: Callable[[ManifestRecord], JudgeObservation],
    model_id: str,
    prompt_version: str,
    adapter_id: str | None = None,
    threshold_id: str | None = None,
    checkpoint_id: str | None = None,
) -> list[PredictionRecord]:
    rows: list[PredictionRecord] = []
    for record in records:
        try:
            obs = predict_fn(record)
            rows.append(
                PredictionRecord(
                    pair_id=record.pair_id,
                    char_id=record.char_id,
                    split=record.split,  # type: ignore[arg-type]
                    judge_id=judge_id,
                    prediction=obs.prediction,
                    confidence=obs.confidence,
                    score=obs.score,
                    latency_ms=obs.latency_ms,
                    parse_status="parsed",
                    model_id=model_id,
                    adapter_id=adapter_id,
                    prompt_version=prompt_version,
                    threshold_id=threshold_id,
                    checkpoint_id=checkpoint_id,
                )
            )
        except Exception as exc:
            log.warning("malformed output for pair %s: %s", record.pair_id, exc)
            rows.append(
                PredictionRecord(
                    pair_id=record.pair_id,
                    char_id=record.char_id,
                    split=record.split,  # type: ignore[arg-type]
                    judge_id=judge_id,
                    prediction=False,
                    confidence=None,
                    score=None,
                    latency_ms=0,
                    parse_status="malformed",
                    model_id=model_id,
                    adapter_id=adapter_id,
                    prompt_version=prompt_version,
                    threshold_id=threshold_id,
                    checkpoint_id=checkpoint_id,
                )
            )
    return rows


def write_predictions(path: Path, rows: list[PredictionRecord]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row.model_dump(mode="json"), sort_keys=True) + "\n" for row in rows)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != text:
            raise ManifestError(f"immutable prediction file differs at {path}")
        return

    tmp_path = path.with_suffix(f".tmp.{path.name}")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def score(records: Sequence[ManifestRecord], preds: Sequence[bool]) -> dict:
    labels = [r.label for r in records]
    precision, recall, f1 = prf1(labels, preds)
    lo, hi = clustered_f1_ci(labels, preds, [r.char_id for r in records])
    return {"n": len(records), "precision": precision, "recall": recall, "f1": f1, "f1_ci95": [lo, hi]}


# --- baselines ------------------------------------------------------------------------------

def _vlm_judge(model: str, image_loader: Callable[[str], str]) -> Judge:
    """A prompted/fine-tuned VLM baseline. Every vendor call goes through `providers.py` (ADR-015).

    `model` is passed explicitly rather than read from `settings` because this harness runs three
    different models against the same pairs; the pipeline itself never does that.
    """
    from providers import judge as provider_judge

    def predict(record: ManifestRecord) -> bool:
        urls = [image_loader(path) for path in record.images]
        try:
            verdict = provider_judge(QUESTION, urls, VlmVerdict, model=model)
        except Exception:
            # §7.5's pre-registered malformed-output rule: an unparseable verdict is scored as a
            # MISS on `different_character`, counted against the judge that produced it.
            log.warning("evaluate: %s produced no parseable verdict for %s", model, record.pair_id)
            return False
        return not verdict.same_character

    return predict


def finetuned_judge(image_loader: Callable[[str], str], model: str = "judge") -> Judge:
    """The fine-tuned adapter, served behind vLLM (§8) — `JUDGE_BASE_URL` points at it."""
    return _vlm_judge(model, image_loader)


def zero_shot_base_judge(image_loader: Callable[[str], str],
                         model: str = "Qwen/Qwen2.5-VL-7B-Instruct") -> Judge:
    """§7.1's PRIMARY comparator: same architecture, same weights, same prompt, no adapter."""
    return _vlm_judge(model, image_loader)


def prompted_gemma_judge(image_loader: Callable[[str], str]) -> Judge:
    """§7.2's product gate: the incumbent the pipeline already ships. Model ID from `config.py`."""
    return _vlm_judge(settings.vlm_judge_model, image_loader)


EMBEDDING_CONTROLS = {
    "clip_cosine": "openai/clip-vit-large-patch14",
    "dinov2_cosine": "facebook/dinov2-base",
}


def embedding_control(name: str, threshold: float, image_loader: Callable[[str], "object"]) -> Judge:
    """CLIP / DINOv2 cosine — §7.3's two scientific CONTROLS, not product candidates.

    They emit a scalar, and ADR-010's regeneration controller consumes `failure_reasons`; a cosine
    similarity cannot tell it to restate the scarf. If DINOv2 wins on F1 that is a reported finding
    about metrics and changes nothing in the pipeline.

    `image_loader` returns a PIL image for a manifest path. `threshold` is the cosine above which
    the pair is called *same* — it must be fixed on VALIDATION before the held-out read (§5.5).

    ponytail: `torch` and `transformers` are imported HERE, on demand, and are deliberately NOT
    backend dependencies. `pyproject.toml` documents at length that merely having transformers
    installed costs +244 MB resident and OOM-kills the 512 MB worker — so these two controls run
    in the rented-GPU eval environment (`pip install torch transformers` there, alongside §6.4's
    llamafactory install), never in the deployed image. Calling this without them raises
    ImportError, which is the intended signal rather than a failure mode.
    """
    import torch                                    # noqa: PLC0415 — deliberate, see docstring
    from transformers import AutoImageProcessor, AutoModel   # noqa: PLC0415

    checkpoint = EMBEDDING_CONTROLS[name]
    processor = AutoImageProcessor.from_pretrained(checkpoint)
    model = AutoModel.from_pretrained(checkpoint).eval()

    def embed(path: str):
        inputs = processor(images=image_loader(path), return_tensors="pt")
        with torch.no_grad():
            out = model.get_image_features(**inputs) if hasattr(model, "get_image_features") \
                else model(**inputs).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(out, dim=-1)

    def predict(record: ManifestRecord) -> bool:
        ref, scene = (embed(path) for path in record.images)
        return bool((ref @ scene.T).item() < threshold)   # below threshold ⇒ different_character

    return predict


BASELINES: dict[str, str] = {
    "finetuned": "the fine-tuned LoRA (§7.1 subject)",
    "zero_shot_base": "zero-shot Qwen2.5-VL-7B — the primary comparator (§7.1)",
    "prompted_gemma": "prompted gemma-3-27b-it — the product gate (§7.2)",
    "clip_cosine": "CLIP image-image cosine — scientific control (§7.3)",
    "dinov2_cosine": "DINOv2 cosine — scientific control (§7.3)",
}


def evaluate(records: Sequence[ManifestRecord], judges: dict[str, Judge]) -> dict:
    """Run each baseline over the same pairs and report §7's metrics per baseline.

    ⚠️ **The held-out test set is read exactly once** (§5.5, §7.5). Tune on validation.
    """
    return {name: score(records, [predict(r) for r in records]) for name, predict in judges.items()}


def main(manifest: Path, split: str, judges: dict[str, Judge], out: Path | None = None) -> dict:
    records = [r for r in read_manifest(manifest) if r.split == split]
    results = evaluate(records, judges)
    if out:
        Path(out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def slice_by(records: Iterable[ManifestRecord], char_ids: set[str]) -> list[ManifestRecord]:
    """§7.4 item 2 — the non-human character slice. Membership is a curated list, not inferred."""
    return [r for r in records if r.char_id in char_ids]
