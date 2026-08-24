"""The four baselines of `judge-finetune.md` §7.3, scored on the `different_character` class.

⚠️ **Tier B — offline eval harness, never CI** (MASTER_SPEC §6, AGENTS.md "Testing bright line").
It calls real models and costs real money. Only the pure metric helpers at the top are unit
tested; nothing here asserts on generated content.

The metric is F1 on `different_character` — the minority class, the class the control loop acts
on, and the class where a miss ships a broken page to a child (§3.3). `ManifestRecord.label` is
already that class; it is read, never re-derived (`build_dataset.py` owns the inversion).
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Sequence


from pydantic import BaseModel, ConfigDict, Field


from app.config import settings
from contracts.story_memory import VlmVerdict
from finetune.evaluation_metrics import (
    auroc,
    calibration,
    clustered_delta_f1_ci,
    clustered_f1_ci,
    cohen_kappa,
    mcnemar_exact,
    mean_sample_std,
    prf1,
)
from finetune.manifest import ManifestError, ManifestRecord, read_manifest
from finetune.to_llamafactory import QUESTION


log = logging.getLogger(__name__)

BASE_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
BASE_REVISION = "cc594898137f460bfe9f0759e9844b3ce807cfb5"
LLAMAFACTORY_VERSION = "v0.9.5"
LLAMAFACTORY_COMMIT = "7af909522a951e3ad9f022ea6f88b6755257eaa5"
BOOTSTRAP_SEED = 0
PREDICTION_SCHEMA_VERSION = 1
SEEDS = (0, 1, 2)

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


def _hash_directory(dir_path: Path) -> str:
    hasher = hashlib.sha256()
    for file_path in sorted(p for p in dir_path.rglob("*") if p.is_file()):
        rel_path = file_path.relative_to(dir_path).as_posix()
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        hasher.update(f"{rel_path}:{file_hash}\n".encode("utf-8"))
    return hasher.hexdigest()


def inventory_checkpoints(runs_root: Path, out_path: Path | None = None) -> dict:
    runs_root = Path(runs_root)
    candidates = []
    for seed_dir in sorted(runs_root.glob("seed-*")):
        if not seed_dir.is_dir():
            continue
        seed_str = seed_dir.name.replace("seed-", "")
        if not seed_str.isdigit():
            continue
        seed = int(seed_str)
        output_dir = seed_dir / "output"
        if not output_dir.is_dir():
            continue
        for ckpt_dir in sorted(output_dir.glob("checkpoint-*")):
            if not ckpt_dir.is_dir():
                continue
            step_str = ckpt_dir.name.replace("checkpoint-", "")
            if not step_str.isdigit():
                continue
            step = int(step_str)
            model_id = f"seed{seed}_checkpoint{step}"
            ckpt_hash = _hash_directory(ckpt_dir)
            candidates.append({
                "model_id": model_id,
                "seed": seed,
                "step": step,
                "path": str(ckpt_dir),
                "sha256": ckpt_hash,
                "checkpoint_id": ckpt_dir.name,
            })
    candidates.sort(key=lambda c: (c["seed"], c["step"]))
    vllm_command = [
        "vllm", "serve", BASE_MODEL, "--revision", BASE_REVISION,
        "--enable-lora", "--max-lora-rank", "16", "--lora-modules",
        *[f"{item['model_id']}={item['path']}" for item in candidates],
    ]
    payload = {"candidates": candidates, "vllm_command": vllm_command}
    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def select_checkpoint(
    candidates: dict[str, list[PredictionRecord]],
    records: Sequence[ManifestRecord],
) -> dict:
    scored = []
    labels = [r.label for r in records]
    for ckpt_id, preds in candidates.items():
        validate_prediction_alignment(records, preds)
        f1 = prf1(labels, [p.prediction for p in preds])[2]
        digits = "".join(ch for ch in ckpt_id if ch.isdigit())
        step = int(digits) if digits else 0
        scored.append({"checkpoint_id": ckpt_id, "step": step, "val_f1": f1})
    scored.sort(key=lambda item: (-item["val_f1"], item["step"]))
    if not scored:
        raise ManifestError("no checkpoint candidates provided for selection")
    return scored[0]


def select_threshold(
    scores: Sequence[float],
    records: Sequence[ManifestRecord],
) -> dict:
    if not scores:
        raise ManifestError("no scores provided for threshold selection")
    labels = [r.label for r in records]
    unique_scores = sorted(set(scores))
    candidates = [unique_scores[0] - 0.01, *unique_scores, unique_scores[-1] + 0.01]
    scored = []
    for t in candidates:
        preds = [s < t for s in scores]
        f1 = prf1(labels, preds)[2]
        scored.append({"threshold": t, "val_f1": f1})
    scored.sort(key=lambda item: (-item["val_f1"], item["threshold"]))
    best = scored[0]
    return {
        "threshold": best["threshold"],
        "val_f1": best["val_f1"],
        "selected_on": "manifest.val.jsonl",
    }


class EvaluationLock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    bootstrap_seed: int = 0
    base_model: str
    base_revision: str
    llamafactory_version: str
    llamafactory_commit: str
    deployment_seed: int
    seeds: list[int]
    selected_checkpoints: dict[str, dict]
    controls: dict[str, dict]
    manifest_hashes: dict[str, str]
    prompt_version: str
    vlm_judge_model: str


def write_evaluation_lock(path: Path, payload: dict | EvaluationLock) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        lock_obj = EvaluationLock.model_validate(payload)
    else:
        lock_obj = payload

    if lock_obj.seeds != [0, 1, 2]:
        raise ManifestError("evaluation lock seeds must be [0, 1, 2]")
    if lock_obj.base_model != BASE_MODEL or lock_obj.base_revision != BASE_REVISION:
        raise ManifestError("evaluation lock base model/revision does not match fixed pins")
    if lock_obj.llamafactory_version != LLAMAFACTORY_VERSION or lock_obj.llamafactory_commit != LLAMAFACTORY_COMMIT:
        raise ManifestError("evaluation lock LLaMA-Factory pins do not match fixed pins")
    if lock_obj.bootstrap_seed != BOOTSTRAP_SEED:
        raise ManifestError(f"bootstrap_seed must be {BOOTSTRAP_SEED}")
    if lock_obj.deployment_seed not in (0, 1, 2):
        raise ManifestError("deployment_seed must be 0, 1, or 2")

    text = json.dumps(lock_obj.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if json.loads(existing) != json.loads(text):
            raise ManifestError(f"immutable evaluation lock differs at {path}")
        return json.loads(text)

    tmp_path = path.with_suffix(f".tmp.{path.name}")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return json.loads(text)


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


def validate_offline(
    freeze_dir: Path,
    candidates_path: Path,
    predictions_dir: Path,
    out_path: Path,
) -> dict:
    freeze_dir = Path(freeze_dir)
    val_manifest = freeze_dir / "manifest.val.jsonl"
    if not val_manifest.exists():
        raise ManifestError(f"validation manifest missing at {val_manifest}")
    val_records = list(read_manifest(val_manifest))

    candidates_payload = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    candidates = candidates_payload["candidates"]

    predictions_dir = Path(predictions_dir)
    seed_groups: dict[int, dict[str, list[PredictionRecord]]] = {s: {} for s in SEEDS}
    for item in candidates:
        seed = item["seed"]
        model_id = item["model_id"]
        pred_file = predictions_dir / f"{model_id}.jsonl"
        if not pred_file.exists():
            raise ManifestError(f"prediction file missing for candidate {model_id} at {pred_file}")
        lines = [json.loads(line) for line in pred_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        preds = [PredictionRecord.model_validate(p) for p in lines]
        validate_prediction_alignment(val_records, preds)
        seed_groups[seed][item["checkpoint_id"]] = preds

    selected_checkpoints = {}
    for seed in SEEDS:
        ckpt_preds = seed_groups[seed]
        if not ckpt_preds:
            raise ManifestError(f"no candidate checkpoints found for seed {seed}")
        best = select_checkpoint(ckpt_preds, val_records)
        cand_detail = next(c for c in candidates if c["seed"] == seed and c["checkpoint_id"] == best["checkpoint_id"])
        selected_checkpoints[f"seed_{seed}"] = {
            "checkpoint_id": best["checkpoint_id"],
            "step": best["step"],
            "path": cand_detail["path"],
            "sha256": cand_detail["sha256"],
            "val_f1": best["val_f1"],
        }

    deployment_seed = min(SEEDS, key=lambda s: (-selected_checkpoints[f"seed_{s}"]["val_f1"], s))

    controls = {}
    for ctrl_name in ("clip_cosine", "dinov2_cosine"):
        ctrl_pred_file = predictions_dir / f"{ctrl_name}.jsonl"
        if ctrl_pred_file.exists():
            ctrl_lines = [json.loads(line) for line in ctrl_pred_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            ctrl_records = [PredictionRecord.model_validate(p) for p in ctrl_lines]
            validate_prediction_alignment(val_records, ctrl_records)
            scores = [p.score for p in ctrl_records if p.score is not None]
            threshold_res = select_threshold(scores, val_records)
            controls[ctrl_name] = threshold_res
        else:
            controls[ctrl_name] = {"threshold": 0.5, "val_f1": 0.0, "selected_on": "manifest.val.jsonl"}

    manifest_hashes = {}
    for split_name in ("train", "val", "test"):
        mf_path = freeze_dir / f"manifest.{split_name}.jsonl"
        if mf_path.exists():
            manifest_hashes[f"manifest.{split_name}.jsonl"] = hashlib.sha256(mf_path.read_bytes()).hexdigest()

    lock_payload = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
        "llamafactory_version": LLAMAFACTORY_VERSION,
        "llamafactory_commit": LLAMAFACTORY_COMMIT,
        "deployment_seed": deployment_seed,
        "seeds": list(SEEDS),
        "selected_checkpoints": selected_checkpoints,
        "controls": controls,
        "manifest_hashes": manifest_hashes,
        "prompt_version": "4",
        "vlm_judge_model": settings.vlm_judge_model,
    }
    return write_evaluation_lock(out_path, lock_payload)


class HeldOutLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    timestamp: str
    approver: str
    purpose: str
    status: Literal["reserved", "running", "completed", "failed"]
    lock_sha256: str
    manifest_test_sha256: str
    error: str | None = None
    predictions_written: list[str] = Field(default_factory=list)


class HeldOutLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entries: list[HeldOutLedgerEntry] = Field(default_factory=list)


def _read_ledger(path: Path) -> HeldOutLedger:
    path = Path(path)
    if not path.exists():
        return HeldOutLedger(entries=[])
    return HeldOutLedger.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _write_ledger(path: Path, ledger: HeldOutLedger) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(ledger.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_suffix(f".tmp.{path.name}")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def reserve_test_read(
    ledger_path: Path,
    lock_path: Path,
    freeze_dir: Path,
    *,
    run_id: str,
    approver: str,
    purpose: str,
) -> dict:
    lock_path = Path(lock_path)
    if not lock_path.exists():
        raise ManifestError(f"evaluation lock missing at {lock_path}")
    lock_dict = json.loads(lock_path.read_text(encoding="utf-8"))
    EvaluationLock.model_validate(lock_dict)

    freeze_dir = Path(freeze_dir)
    test_mf = freeze_dir / "manifest.test.jsonl"
    if not test_mf.exists():
        raise ManifestError(f"manifest.test.jsonl missing at {test_mf}")

    lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    test_mf_sha = hashlib.sha256(test_mf.read_bytes()).hexdigest()

    ledger = _read_ledger(ledger_path)
    for entry in ledger.entries:
        if entry.status in ("reserved", "running", "completed"):
            if entry.run_id != run_id:
                raise ManifestError(
                    f"held-out test split has already been accessed (run {entry.run_id} status {entry.status})"
                )
            if entry.status == "completed":
                raise ManifestError(f"run {run_id} already completed")
            return entry.model_dump(mode="json")

    entry = HeldOutLedgerEntry(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        approver=approver,
        purpose=purpose,
        status="reserved",
        lock_sha256=lock_sha,
        manifest_test_sha256=test_mf_sha,
    )
    ledger.entries.append(entry)
    _write_ledger(ledger_path, ledger)
    return entry.model_dump(mode="json")


def record_test_result(
    ledger_path: Path,
    *,
    run_id: str,
    status: Literal["running", "completed", "failed"],
    error: str | None = None,
    predictions_written: list[str] | None = None,
) -> dict:
    ledger = _read_ledger(ledger_path)
    target = None
    for entry in ledger.entries:
        if entry.run_id == run_id:
            target = entry
            break
    if target is None:
        raise ManifestError(f"run_id {run_id} not found in ledger")

    target.status = status
    if error is not None:
        target.error = error
    if predictions_written is not None:
        target.predictions_written = sorted(set(target.predictions_written + predictions_written))

    _write_ledger(ledger_path, ledger)
    return target.model_dump(mode="json")


def run_heldout(
    freeze_dir: Path,
    lock_path: Path,
    ledger_path: Path,
    *,
    run_id: str,
    approver: str,
    purpose: str,
    predictions_dir: Path,
    predict_fn: Callable[[str, ManifestRecord], JudgeObservation] | None = None,
    image_loader: Callable[[str], str] | None = None,
) -> dict:
    reserve_test_read(
        ledger_path, lock_path, freeze_dir,
        run_id=run_id, approver=approver, purpose=purpose,
    )
    record_test_result(ledger_path, run_id=run_id, status="running")

    lock_dict = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    lock = EvaluationLock.model_validate(lock_dict)

    freeze_dir = Path(freeze_dir)
    test_records = list(read_manifest(freeze_dir / "manifest.test.jsonl"))

    test_sha = hashlib.sha256((freeze_dir / "manifest.test.jsonl").read_bytes()).hexdigest()
    if lock.manifest_hashes.get("manifest.test.jsonl") != test_sha:
        err = f"manifest.test.jsonl sha256 mismatch against evaluation lock ({test_sha} vs {lock.manifest_hashes.get('manifest.test.jsonl')})"
        record_test_result(ledger_path, run_id=run_id, status="failed", error=err)
        raise ManifestError(err)

    predictions_dir = Path(predictions_dir)
    predictions_dir.mkdir(parents=True, exist_ok=True)
    written_files = []
    results = {}

    try:
        for seed_key, ckpt_info in lock.selected_checkpoints.items():
            judge_id = seed_key
            pred_file = predictions_dir / f"{judge_id}.jsonl"
            if predict_fn is not None:
                rows = capture_predictions(
                    test_records, judge_id, lambda r, j=judge_id: predict_fn(j, r),
                    model_id=BASE_MODEL, prompt_version=lock.prompt_version,
                    adapter_id=ckpt_info["path"], checkpoint_id=ckpt_info["checkpoint_id"],
                )
            else:
                judge_callable = finetuned_judge(image_loader or (lambda p: p), model=ckpt_info["checkpoint_id"])
                rows = capture_predictions(
                    test_records, judge_id,
                    lambda r: JudgeObservation(prediction=judge_callable(r), confidence=None, score=None, latency_ms=0),
                    model_id=BASE_MODEL, prompt_version=lock.prompt_version,
                    adapter_id=ckpt_info["path"], checkpoint_id=ckpt_info["checkpoint_id"],
                )
            write_predictions(pred_file, rows)
            written_files.append(pred_file.name)
            results[judge_id] = rows

        pred_file = predictions_dir / "zero_shot_base.jsonl"
        if predict_fn is not None:
            rows = capture_predictions(
                test_records, "zero_shot_base", lambda r: predict_fn("zero_shot_base", r),
                model_id=BASE_MODEL, prompt_version=lock.prompt_version,
            )
        else:
            judge_callable = zero_shot_base_judge(image_loader or (lambda p: p), model=BASE_MODEL)
            rows = capture_predictions(
                test_records, "zero_shot_base",
                lambda r: JudgeObservation(prediction=judge_callable(r), confidence=None, score=None, latency_ms=0),
                model_id=BASE_MODEL, prompt_version=lock.prompt_version,
            )
        write_predictions(pred_file, rows)
        written_files.append(pred_file.name)
        results["zero_shot_base"] = rows

        pred_file = predictions_dir / "prompted_gemma.jsonl"
        if predict_fn is not None:
            rows = capture_predictions(
                test_records, "prompted_gemma", lambda r: predict_fn("prompted_gemma", r),
                model_id=lock.vlm_judge_model, prompt_version=lock.prompt_version,
            )
        else:
            judge_callable = prompted_gemma_judge(image_loader or (lambda p: p))
            rows = capture_predictions(
                test_records, "prompted_gemma",
                lambda r: JudgeObservation(prediction=judge_callable(r), confidence=None, score=None, latency_ms=0),
                model_id=lock.vlm_judge_model, prompt_version=lock.prompt_version,
            )
        write_predictions(pred_file, rows)
        written_files.append(pred_file.name)
        results["prompted_gemma"] = rows

        for ctrl_name in ("clip_cosine", "dinov2_cosine"):
            if ctrl_name in lock.controls:
                ctrl_threshold = lock.controls[ctrl_name]["threshold"]
                pred_file = predictions_dir / f"{ctrl_name}.jsonl"
                if predict_fn is not None:
                    rows = capture_predictions(
                        test_records, ctrl_name, lambda r, c=ctrl_name: predict_fn(c, r),
                        model_id=ctrl_name, prompt_version=lock.prompt_version,
                        threshold_id=str(ctrl_threshold),
                    )
                else:
                    judge_callable = embedding_control(ctrl_name, ctrl_threshold, image_loader or (lambda p: p))
                    rows = capture_predictions(
                        test_records, ctrl_name,
                        lambda r: JudgeObservation(prediction=judge_callable(r), confidence=None, score=None, latency_ms=0),
                        model_id=ctrl_name, prompt_version=lock.prompt_version,
                        threshold_id=str(ctrl_threshold),
                    )
                write_predictions(pred_file, rows)
                written_files.append(pred_file.name)
                results[ctrl_name] = rows

        record_test_result(ledger_path, run_id=run_id, status="completed", predictions_written=written_files)
        return {"run_id": run_id, "predictions": results, "written": written_files}
    except Exception as exc:
        record_test_result(ledger_path, run_id=run_id, status="failed", error=str(exc))
        raise


def build_report(
    freeze_dir: Path,
    lock_path: Path,
    predictions_dir: Path,
    out_path: Path | None = None,
) -> dict:
    freeze_dir = Path(freeze_dir)
    lock_path = Path(lock_path)
    predictions_dir = Path(predictions_dir)

    lock_dict = json.loads(lock_path.read_text(encoding="utf-8"))
    lock = EvaluationLock.model_validate(lock_dict)

    test_records = list(read_manifest(freeze_dir / "manifest.test.jsonl"))
    test_labels = [r.label for r in test_records]
    test_char_ids = [r.char_id for r in test_records]

    slices_file = freeze_dir / "character_slices.json"
    slices_data = json.loads(slices_file.read_text(encoding="utf-8")) if slices_file.exists() else {}
    non_human_char_ids = set(slices_data.get("non_human", []))

    predictions_by_judge: dict[str, list[PredictionRecord]] = {}
    for judge_name in ("seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine"):
        pred_file = predictions_dir / f"{judge_name}.jsonl"
        if not pred_file.exists():
            raise ManifestError(f"prediction file missing for {judge_name} at {pred_file}")
        lines = [json.loads(line) for line in pred_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        preds = [PredictionRecord.model_validate(p) for p in lines]
        validate_prediction_alignment(test_records, preds)
        predictions_by_judge[judge_name] = preds

    deployment_seed = lock.deployment_seed
    dep_key = f"seed_{deployment_seed}"
    dep_preds = [p.prediction for p in predictions_by_judge[dep_key]]

    baselines_report = {}
    for judge_name, preds_list in predictions_by_judge.items():
        preds = [p.prediction for p in preds_list]
        scores = [p.score for p in preds_list]
        confidences = [p.confidence for p in preds_list]
        p_val, r_val, f1_val = prf1(test_labels, preds)
        f1_lo, f1_hi = clustered_f1_ci(test_labels, preds, test_char_ids, seed=BOOTSTRAP_SEED)

        record_dict = {
            "n": len(preds_list),
            "precision": p_val,
            "recall": r_val,
            "f1": f1_val,
            "f1_ci95": [f1_lo, f1_hi],
            "auroc": auroc(test_labels, scores),
            "cohen_kappa": cohen_kappa(test_labels, preds),
            "calibration": calibration(test_labels, confidences),
        }

        if judge_name in ("zero_shot_base", "prompted_gemma"):
            delta_lo, delta_hi = clustered_delta_f1_ci(
                test_labels, dep_preds, preds, test_char_ids, seed=BOOTSTRAP_SEED
            )
            record_dict["delta_f1_ci95_vs_deployment_seed"] = [delta_lo, delta_hi]
            record_dict["mcnemar_p_vs_deployment_seed"] = mcnemar_exact(test_labels, dep_preds, preds)

        baselines_report[judge_name] = record_dict

    seed_f1s = [baselines_report[f"seed_{s}"]["f1"] for s in (0, 1, 2)]
    seeds_summary = mean_sample_std(seed_f1s)
    seeds_summary["values"] = seed_f1s

    slices_report = {}
    non_human_indices = [i for i, r in enumerate(test_records) if r.char_id in non_human_char_ids]
    if non_human_indices:
        nh_labels = [test_labels[i] for i in non_human_indices]
        nh_chars = [test_char_ids[i] for i in non_human_indices]
        nh_results = {}
        for jname in (dep_key, "zero_shot_base", "prompted_gemma"):
            nh_preds = [predictions_by_judge[jname][i].prediction for i in non_human_indices]
            p_val, r_val, f1_val = prf1(nh_labels, nh_preds)
            f1_lo, f1_hi = clustered_f1_ci(nh_labels, nh_preds, nh_chars, seed=BOOTSTRAP_SEED)
            nh_results[jname] = {
                "n": len(non_human_indices),
                "precision": p_val,
                "recall": r_val,
                "f1": f1_val,
                "f1_ci95": [f1_lo, f1_hi],
            }
        slices_report["non_human"] = nh_results
    else:
        slices_report["non_human"] = {"status": "no non_human characters in test split"}

    incumbent_f1 = baselines_report["prompted_gemma"]["f1"]
    candidate_f1 = baselines_report[dep_key]["f1"]
    status = "pass" if candidate_f1 > incumbent_f1 else "fail"
    model_to_deploy = (
        lock.selected_checkpoints[dep_key]["path"] if status == "pass" else lock.vlm_judge_model
    )
    deployment_decision = {
        "status": status,
        "incumbent_model": lock.vlm_judge_model,
        "incumbent_f1": incumbent_f1,
        "candidate_seed": deployment_seed,
        "candidate_checkpoint": lock.selected_checkpoints[dep_key]["checkpoint_id"],
        "candidate_f1": candidate_f1,
        "delta_f1": candidate_f1 - incumbent_f1,
        "model_to_deploy": model_to_deploy,
    }

    report = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "deployment_seed": deployment_seed,
        "seeds_f1_summary": seeds_summary,
        "baselines": baselines_report,
        "slices": slices_report,
        "deployment_decision": deployment_decision,
    }

    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return report


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Objective-4 evaluation and validation runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inv_p = subparsers.add_parser("validation-inventory")
    inv_p.add_argument("--runs", required=True, type=Path)
    inv_p.add_argument("--out", required=True, type=Path)

    val_p = subparsers.add_parser("validate")
    val_p.add_argument("--freeze", required=True, type=Path)
    val_p.add_argument("--candidates", required=True, type=Path)
    val_p.add_argument("--predictions", required=True, type=Path)
    val_p.add_argument("--out", required=True, type=Path)

    res_p = subparsers.add_parser("reserve-test")
    res_p.add_argument("--ledger", required=True, type=Path)
    res_p.add_argument("--lock", required=True, type=Path)
    res_p.add_argument("--freeze", required=True, type=Path)
    res_p.add_argument("--run-id", required=True, type=str)
    res_p.add_argument("--approver", required=True, type=str)
    res_p.add_argument("--purpose", required=True, type=str)

    run_p = subparsers.add_parser("run-heldout")
    run_p.add_argument("--freeze", required=True, type=Path)
    run_p.add_argument("--lock", required=True, type=Path)
    run_p.add_argument("--ledger", required=True, type=Path)
    run_p.add_argument("--run-id", required=True, type=str)
    run_p.add_argument("--approver", required=True, type=str)
    run_p.add_argument("--purpose", required=True, type=str)
    run_p.add_argument("--predictions", required=True, type=Path)

    agg_p = subparsers.add_parser("aggregate")
    agg_p.add_argument("--freeze", required=True, type=Path)
    agg_p.add_argument("--lock", required=True, type=Path)
    agg_p.add_argument("--predictions", required=True, type=Path)
    agg_p.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "validation-inventory":
        inventory_checkpoints(args.runs, args.out)
    elif args.command == "validate":
        validate_offline(args.freeze, args.candidates, args.predictions, args.out)
    elif args.command == "reserve-test":
        reserve_test_read(
            args.ledger, args.lock, args.freeze,
            run_id=args.run_id, approver=args.approver, purpose=args.purpose,
        )
    elif args.command == "run-heldout":
        run_heldout(
            freeze_dir=args.freeze, lock_path=args.lock, ledger_path=args.ledger,
            run_id=args.run_id, approver=args.approver, purpose=args.purpose,
            predictions_dir=args.predictions,
        )
    elif args.command == "aggregate":
        build_report(args.freeze, args.lock, args.predictions, args.out)


if __name__ == "__main__":
    cli()


