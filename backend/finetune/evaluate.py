"""The four baselines of `judge-finetune.md` §7.3, scored on the `different_character` class.

⚠️ **Tier B — offline eval harness, never CI** (MASTER_SPEC §6, AGENTS.md "Testing bright line").
It calls real models and costs real money. Only the pure metric helpers at the top are unit
tested; nothing here asserts on generated content.

The metric is F1 on `different_character` — the minority class, the class the control loop acts
on, and the class where a miss ships a broken page to a child (§3.3). `ManifestRecord.label` is
already that class; it is read, never re-derived (`build_dataset.py` owns the inversion).
"""
import base64
import hashlib
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Sequence


from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


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
PREDICTION_SCHEMA_VERSION = 2
REPORT_SCHEMA_VERSION = 1
SEEDS = (0, 1, 2)
REPORT_JUDGES = (
    "seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma",
    "clip_cosine", "dinov2_cosine",
)

Judge = Callable[[ManifestRecord], bool]      # record → predicted `different_character`
Observer = Callable[[ManifestRecord], "JudgeObservation"]


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
    latency_ms: int | None = Field(default=None, ge=0)
    latency_phase: Literal["cold", "warm"]
    parse_status: Literal["parsed", "malformed"]
    model_id: str
    adapter_id: str | None = None
    prompt_version: str
    threshold_id: str | None = None
    checkpoint_id: str | None = None


class AvailabilityMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float | None
    reason: str | None


class CalibrationBin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bin: int = Field(ge=0, le=9)
    range: list[float] = Field(min_length=2, max_length=2)
    count: int = Field(ge=0)
    mean_probability: float | None
    positive_rate: float | None


class CalibrationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["available", "unavailable"]
    reason: str | None
    brier_score: float | None
    bins: list[CalibrationBin]


class LatencySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = Field(ge=0)
    mean: float | None
    sample_std: float | None


class ParseFailureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(ge=0)
    rate: float = Field(ge=0.0, le=1.0)


class JudgeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = Field(ge=0)
    precision: float
    recall: float
    f1: float
    f1_ci95: list[float] = Field(min_length=2, max_length=2)
    auroc: AvailabilityMetric
    cohen_kappa: AvailabilityMetric
    calibration: CalibrationSummary
    latency_ms: LatencySummary
    cold_start_latency_ms: AvailabilityMetric
    cost_per_call_usd: AvailabilityMetric
    parse_failures: ParseFailureSummary
    label_prevalence: float | None
    prediction_rate: float | None
    delta_f1_ci95_vs_deployment_seed: list[float] | None = None
    mcnemar_p_vs_deployment_seed: float | None = None


class ObjectiveConclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_met: bool
    primary_judge: str
    reported_result: JudgeMetrics


class SeedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mean: float
    sample_std: float
    values: list[float] = Field(min_length=3, max_length=3)


class UnavailableSlice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["unavailable"]
    reason: str


class AgreementMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["available", "unavailable"]
    reason: str | None = None
    n: int | None = Field(default=None, ge=0)
    cohen_kappa: AvailabilityMetric | None = None
    percent_agreement: float | None = Field(default=None, ge=0.0, le=1.0)


class HumanAgreement(AgreementMetric):
    slices: dict[str, AgreementMetric]


class RegisteredEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["unavailable", "not_collected_by_heldout_runner"]
    reason: str


class DeploymentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rung: Literal["A", "B", "C", "D"]
    ship_candidate: bool
    incumbent_model: str
    incumbent_f1: float
    incumbent_recall: float
    candidate_seed: int
    candidate_checkpoint: str
    candidate_f1: float
    candidate_recall: float
    delta_f1_vs_incumbent: float
    model_to_deploy: str


class Objective4Report(BaseModel):
    """Canonical, identifier-free schema for the preregistered Objective-4 report."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    bootstrap_seed: int
    deployment_seed: int
    seeds_f1_summary: SeedSummary
    judges: dict[str, JudgeMetrics]
    slices: dict[str, dict[str, JudgeMetrics] | UnavailableSlice]
    intra_rater_agreement: HumanAgreement
    prediction_rate_drift: dict[str, float]
    registered_endpoints: dict[str, RegisteredEndpoint]
    objective4: ObjectiveConclusion
    deployment_decision: DeploymentDecision

    @model_validator(mode="after")
    def validate_registered_structure(self) -> "Objective4Report":
        if set(self.judges) != set(REPORT_JUDGES):
            raise ValueError("report must contain every registered judge exactly once")
        if set(self.slices) != {"human", "non_human"}:
            raise ValueError("report must contain both registered character slices")
        for value in self.slices.values():
            if isinstance(value, dict) and set(value) != set(REPORT_JUDGES):
                raise ValueError("available slices must contain every registered judge")
        if set(self.intra_rater_agreement.slices) != {"human", "non_human"}:
            raise ValueError("intra-rater agreement must contain both character slices")
        if set(self.registered_endpoints) != {
            "cost_per_call", "dreambench_transfer", "downstream_expert_feedback",
            "data_scaling_ablation",
        }:
            raise ValueError("report must contain every registered external endpoint exactly once")
        met = self.deployment_decision.rung != "D"
        ships = self.deployment_decision.rung in ("A", "B")
        if self.objective4.requirement_met != met or self.deployment_decision.ship_candidate != ships:
            raise ValueError("claim rung conflicts with research or deployment conclusion")
        return self


def _hash_directory(dir_path: Path) -> str:
    hasher = hashlib.sha256()
    for file_path in sorted(p for p in dir_path.rglob("*") if p.is_file()):
        rel_path = file_path.relative_to(dir_path).as_posix()
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        hasher.update(f"{rel_path}:{file_hash}\n".encode("utf-8"))
    return hasher.hexdigest()


def _publish_exclusive(path: Path, content: bytes) -> bool:
    """Publish complete bytes without ever exposing a partial final file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        try:
            os.link(temp_path, path)
            return True
        except FileExistsError:
            return False
    finally:
        temp_path.unlink(missing_ok=True)


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
        preds = [s > t for s in scores]
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
    model_config = ConfigDict(extra="forbid", strict=True)
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
    report_artifact_hashes: dict[str, str]
    prompt_version: str
    vlm_judge_model: str


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_evaluation_lock(lock: EvaluationLock, *, verify_checkpoints: bool = True) -> None:
    if lock.schema_version != PREDICTION_SCHEMA_VERSION:
        raise ManifestError(f"evaluation lock schema_version must be {PREDICTION_SCHEMA_VERSION}")
    if lock.seeds != list(SEEDS):
        raise ManifestError(f"evaluation lock seeds must be {list(SEEDS)}")
    if lock.base_model != BASE_MODEL or lock.base_revision != BASE_REVISION:
        raise ManifestError("evaluation lock base model/revision does not match fixed pins")
    if lock.llamafactory_version != LLAMAFACTORY_VERSION or lock.llamafactory_commit != LLAMAFACTORY_COMMIT:
        raise ManifestError("evaluation lock LLaMA-Factory pins do not match fixed pins")
    if lock.bootstrap_seed != BOOTSTRAP_SEED:
        raise ManifestError(f"bootstrap_seed must be {BOOTSTRAP_SEED}")
    if lock.deployment_seed not in SEEDS:
        raise ManifestError(f"deployment_seed must be one of {SEEDS}")
    for name, value in {
        "prompt_version": lock.prompt_version,
        "vlm_judge_model": lock.vlm_judge_model,
    }.items():
        if not value.strip():
            raise ManifestError(f"evaluation lock {name} must be non-blank")

    expected_seeds = {f"seed_{seed}" for seed in SEEDS}
    if set(lock.selected_checkpoints) != expected_seeds:
        raise ManifestError(f"evaluation lock selected_checkpoints must be {sorted(expected_seeds)}")
    for seed in SEEDS:
        key = f"seed_{seed}"
        checkpoint = lock.selected_checkpoints[key]
        required = {"model_id", "checkpoint_id", "step", "path", "sha256", "val_f1"}
        if set(checkpoint) != required:
            raise ManifestError(f"evaluation lock {key} fields must be {sorted(required)}")
        if any(not str(checkpoint[name]).strip() for name in ("model_id", "checkpoint_id", "path")):
            raise ManifestError(f"evaluation lock {key} identifiers must be non-blank")
        step = checkpoint["step"]
        val_f1 = checkpoint["val_f1"]
        if not isinstance(step, int) or isinstance(step, bool) or step < 0:
            raise ManifestError(f"evaluation lock {key} step must be a non-negative integer")
        if not isinstance(val_f1, (int, float)) or isinstance(val_f1, bool) or not 0.0 <= val_f1 <= 1.0:
            raise ManifestError(f"evaluation lock {key} val_f1 must be between 0 and 1")
        if checkpoint["model_id"] != f"seed{seed}_checkpoint{step}":
            raise ManifestError(f"evaluation lock {key} model_id does not match its seed and step")
        if not _is_sha256(checkpoint["sha256"]):
            raise ManifestError(f"evaluation lock {key} checkpoint SHA-256 must be lowercase hexadecimal")
        checkpoint_path = Path(checkpoint["path"])
        if checkpoint_path.name != checkpoint["checkpoint_id"]:
            raise ManifestError(f"evaluation lock {key} checkpoint path does not match checkpoint_id")
        if verify_checkpoints:
            if not checkpoint_path.is_dir():
                raise ManifestError(f"evaluation lock {key} checkpoint path is missing")
            if _hash_directory(checkpoint_path) != checkpoint["sha256"]:
                raise ManifestError(f"evaluation lock {key} checkpoint digest does not match its path")

    if set(lock.controls) != {"clip_cosine", "dinov2_cosine"}:
        raise ManifestError("evaluation lock requires both registered controls")
    for name, control in lock.controls.items():
        if set(control) != {"threshold", "val_f1", "selected_on"}:
            raise ManifestError(f"evaluation lock {name} fields are invalid")
        if control["selected_on"] != "manifest.val.jsonl":
            raise ManifestError(f"evaluation lock {name} must be selected on validation")
        if not isinstance(control["threshold"], (int, float)) or isinstance(control["threshold"], bool):
            raise ManifestError(f"evaluation lock {name} threshold must be numeric")
        if not isinstance(control["val_f1"], (int, float)) or isinstance(control["val_f1"], bool) or not 0.0 <= control["val_f1"] <= 1.0:
            raise ManifestError(f"evaluation lock {name} val_f1 must be between 0 and 1")
    required_manifests = {f"manifest.{split}.jsonl" for split in ("train", "val", "test")}
    if set(lock.manifest_hashes) != required_manifests:
        raise ManifestError("evaluation lock requires exactly the train, val, and test manifest hashes")
    if any(not _is_sha256(value) for value in lock.manifest_hashes.values()):
        raise ManifestError("evaluation lock manifest hashes must be normalized SHA-256 values")
    required_report_artifacts = {"annotation_agreement.jsonl", "character_slices.json"}
    if set(lock.report_artifact_hashes) != required_report_artifacts:
        raise ManifestError("evaluation lock requires both report artifact hashes")
    if any(not _is_sha256(value) for value in lock.report_artifact_hashes.values()):
        raise ManifestError("evaluation lock report artifact hashes must be normalized SHA-256 values")


def write_evaluation_lock(path: Path, payload: dict | EvaluationLock) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_obj = EvaluationLock.model_validate(payload)
    except ValidationError as exc:
        raise ManifestError(f"invalid evaluation lock schema: {exc}") from exc
    _validate_evaluation_lock(lock_obj)

    text = json.dumps(lock_obj.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    if not _publish_exclusive(path, text.encode("utf-8")):
        existing = path.read_text(encoding="utf-8")
        if existing != text:
            raise ManifestError(f"immutable evaluation lock differs at {path}")
        return json.loads(text)
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


def validate_agreement_alignment(pair_ids: Sequence[str], rows: Sequence[dict]) -> None:
    actual = [row.get("pair_id") for row in rows]
    if len(actual) != len(set(actual)) or actual != list(pair_ids):
        raise ManifestError("agreement evidence alignment must match held-out pair order exactly")


def validate_report_prediction_evidence(
    records: Sequence[ManifestRecord], predictions: Sequence[PredictionRecord], judge_id: str,
) -> None:
    validate_prediction_alignment(records, predictions)
    if any(row.judge_id != judge_id for row in predictions):
        raise ManifestError("prediction evidence judge identity mismatch")
    phases = [row.latency_phase for row in predictions]
    if phases != (["cold"] + ["warm"] * (len(phases) - 1) if phases else []):
        raise ManifestError("prediction evidence must record cold then warm latency phases")


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
    for index, record in enumerate(records):
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
                    latency_phase="cold" if index == 0 else "warm",
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
                    latency_ms=None,
                    latency_phase="cold" if index == 0 else "warm",
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
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest_path = path.with_suffix(path.suffix + ".sha256")
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ManifestError(f"immutable prediction file differs at {path}")
        if not digest_path.exists() or digest_path.read_text(encoding="ascii").strip() != digest:
            raise ManifestError(f"immutable prediction SHA-256 differs at {digest_path.name}")
        return

    digest_path.write_text(digest + "\n", encoding="ascii")
    if not _publish_exclusive(path, text.encode("utf-8")) and path.read_bytes() != text.encode("utf-8"):
        raise ManifestError(f"immutable prediction file differs at {path}")


def _load_completed_predictions(
    path: Path,
    records: Sequence[ManifestRecord],
    judge_id: str,
    **identity: object,
) -> list[PredictionRecord] | None:
    if not path.exists():
        return None
    digest_path = path.with_suffix(path.suffix + ".sha256")
    if not digest_path.exists() or digest_path.read_text(encoding="ascii").strip() != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ManifestError(f"prediction SHA-256 verification failed for {path.name}")
    try:
        rows = [PredictionRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except ValidationError as exc:
        raise ManifestError(f"invalid immutable prediction schema for {path.name}") from exc
    validate_prediction_alignment(records, rows)
    if any(row.judge_id != judge_id for row in rows):
        raise ManifestError(f"immutable prediction judge identity mismatch for {path.name}")
    for field, expected in identity.items():
        if any(getattr(row, field) != expected for row in rows):
            raise ManifestError(f"immutable prediction {field} mismatch for {path.name}")
    return rows


def score(records: Sequence[ManifestRecord], preds: Sequence[bool]) -> dict:
    labels = [r.label for r in records]
    precision, recall, f1 = prf1(labels, preds)
    lo, hi = clustered_f1_ci(labels, preds, [r.char_id for r in records])
    return {"n": len(records), "precision": precision, "recall": recall, "f1": f1, "f1_ci95": [lo, hi]}


# --- baselines ------------------------------------------------------------------------------

def _vlm_observer(
    model: str,
    image_loader: Callable[[str], str],
    *,
    prompt: str,
    schema: type[BaseModel],
    route: Literal["judge", "openrouter"] = "judge",
) -> Observer:
    """A prompted/fine-tuned VLM baseline. Every vendor call goes through `providers.py` (ADR-015).

    `model` is passed explicitly rather than read from `settings` because this harness runs three
    different models against the same pairs; the pipeline itself never does that.
    """
    from providers import judge_with_metadata

    def predict(record: ManifestRecord) -> JudgeObservation:
        urls = [image_loader(path) for path in record.images]
        result = judge_with_metadata(prompt, urls, schema, model=model, route=route)
        prediction = not result.verdict.same_character
        score = None if result.confidence is None else (
            result.confidence if prediction else 1.0 - result.confidence
        )
        return JudgeObservation(
            prediction=prediction,
            confidence=result.confidence,
            score=score,
            latency_ms=result.latency_ms,
        )

    return predict


def finetuned_judge(image_loader: Callable[[str], str], model: str = "judge") -> Observer:
    """The fine-tuned adapter, served behind vLLM (§8) — `JUDGE_BASE_URL` points at it."""
    return _vlm_observer(model, image_loader, prompt=QUESTION, schema=VlmVerdict)


def zero_shot_base_judge(image_loader: Callable[[str], str],
                         model: str = "Qwen/Qwen2.5-VL-7B-Instruct") -> Observer:
    """§7.1's PRIMARY comparator: same architecture, same weights, same prompt, no adapter."""
    return _vlm_observer(model, image_loader, prompt=QUESTION, schema=VlmVerdict)


def prompted_gemma_judge(image_loader: Callable[[str], str]) -> Observer:
    """§7.2's product gate: the incumbent the pipeline already ships. Model ID from `config.py`."""
    from pipeline.consistency_check import JUDGE_PROMPT, SceneVerdict

    return _vlm_observer(
        settings.vlm_judge_model,
        image_loader,
        prompt=JUDGE_PROMPT.format(name="the character"),
        schema=SceneVerdict,
        route="openrouter",
    )


EMBEDDING_CONTROLS = {
    "clip_cosine": "openai/clip-vit-large-patch14",
    "dinov2_cosine": "facebook/dinov2-base",
}


def embedding_control(name: str, threshold: float, image_loader: Callable[[str], "object"]) -> Observer:
    """CLIP / DINOv2 cosine — §7.3's two scientific CONTROLS, not product candidates.

    They emit a scalar, and ADR-010's regeneration controller consumes `failure_reasons`; a cosine
    similarity cannot tell it to restate the scarf. If DINOv2 wins on F1 that is a reported finding
    about metrics and changes nothing in the pipeline.

    `image_loader` returns a PIL image for a manifest path. `threshold` is the cosine above which
    the pair is called *same* — it must be fixed on VALIDATION before the held-out read (§5.5).

    ponytail: `torch` and `transformers` are imported HERE, on demand, and are deliberately NOT
    backend dependencies. `pyproject.toml` documents at length that merely having transformers
    installed costs +244 MB resident and OOM-kills the 512 MB worker — so these two controls run
    in the rented-GPU eval environment (`uv pip install torch transformers` there, alongside §6.4's
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

    def predict(record: ManifestRecord) -> JudgeObservation:
        started = time.perf_counter_ns()
        ref, scene = (embed(path) for path in record.images)
        similarity = float((ref @ scene.T).item())
        return _embedding_observation(
            similarity,
            threshold,
            (time.perf_counter_ns() - started) // 1_000_000,
        )

    return predict


def _embedding_observation(similarity: float, threshold: float, latency_ms: int) -> JudgeObservation:
    score = -similarity
    return JudgeObservation(
        prediction=score > threshold,
        confidence=None,
        score=score,
        latency_ms=latency_ms,
    )


BASELINES: dict[str, str] = {
    "finetuned": "the fine-tuned LoRA (§7.1 subject)",
    "zero_shot_base": "zero-shot Qwen2.5-VL-7B — the primary comparator (§7.1)",
    "prompted_gemma": "prompted gemma-3-27b-it — the product gate (§7.2)",
    "clip_cosine": "CLIP image-image cosine — scientific control (§7.3)",
    "dinov2_cosine": "DINOv2 cosine — scientific control (§7.3)",
}


def capture_validation(freeze_dir: Path, candidates_path: Path, predictions_dir: Path) -> list[str]:
    freeze_dir = Path(freeze_dir)
    records = list(read_manifest(freeze_dir / "manifest.val.jsonl"))
    candidates = json.loads(Path(candidates_path).read_text(encoding="utf-8"))["candidates"]
    predictions_dir = Path(predictions_dir)
    predictions_dir.mkdir(parents=True, exist_ok=True)

    def image_uri(relative_path: str) -> str:
        path = freeze_dir / relative_path
        suffix = path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/webp"
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()

    def pil_image(relative_path: str):
        from PIL import Image

        with Image.open(freeze_dir / relative_path) as image:
            return image.convert("RGB").copy()

    written = []
    for candidate in candidates:
        model_id = candidate["model_id"]
        rows = capture_predictions(
            records, model_id, finetuned_judge(image_uri, model=model_id),
            model_id=BASE_MODEL, adapter_id=model_id, prompt_version="4",
            checkpoint_id=candidate.get("checkpoint_id"),
        )
        filename = f"{model_id}.jsonl"
        write_predictions(predictions_dir / filename, rows)
        written.append(filename)
    for control in ("clip_cosine", "dinov2_cosine"):
        rows = capture_predictions(
            records, control, embedding_control(control, 0.0, pil_image),
            model_id=control, prompt_version="4",
        )
        filename = f"{control}.jsonl"
        write_predictions(predictions_dir / filename, rows)
        written.append(filename)
    return written


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
            "model_id": cand_detail["model_id"],
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
            raise ManifestError(f"prediction file missing for mandatory control {ctrl_name} at {ctrl_pred_file}")

    freeze_report_path = freeze_dir / "freeze_report.json"
    if not freeze_report_path.exists():
        raise ManifestError(f"freeze report missing at {freeze_report_path}")
    freeze_report = json.loads(freeze_report_path.read_text(encoding="utf-8"))
    artifact_hashes = freeze_report.get("artifact_sha256", {})
    required_manifests = {f"manifest.{split}.jsonl" for split in ("train", "val", "test")}
    required_report_artifacts = {"annotation_agreement.jsonl", "character_slices.json"}
    if not (required_manifests | required_report_artifacts).issubset(artifact_hashes):
        raise ManifestError("freeze report is missing evaluation artifact hashes")
    manifest_hashes = {name: artifact_hashes[name] for name in sorted(required_manifests)}
    report_artifact_hashes = {
        name: artifact_hashes[name] for name in sorted(required_report_artifacts)
    }

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
        "report_artifact_hashes": report_artifact_hashes,
        "prompt_version": "4",
        "vlm_judge_model": settings.vlm_judge_model,
    }
    return write_evaluation_lock(out_path, lock_payload)


class EvaluationSignoff(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_by: str = Field(min_length=1)
    approved_at: datetime


class HeldOutDeviation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    defect: str = Field(min_length=1)
    fix_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    debug_evidence_sha256: list[str] = Field(min_length=1)
    debug_splits: list[Literal["train", "val"]]
    approved_at: datetime


class HeldOutLedgerEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    timestamp: datetime
    status: Literal["reserved", "resumed", "completed", "failed"]
    ordinal: int = Field(ge=1, le=2)
    lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    rung: Literal["A", "B", "C", "D"] | None = None
    error: str | None = None


def _read_ledger(path: Path) -> list[HeldOutLedgerEvent]:
    path = Path(path)
    if not path.exists():
        return []
    return [
        HeldOutLedgerEvent.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _append_ledger(path: Path, event: HeldOutLedgerEvent) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _load_signoff(path: Path, lock_sha: str) -> EvaluationSignoff:
    path = Path(path)
    if not path.exists():
        raise ManifestError(f"evaluation sign-off missing at {path}")
    signoff = EvaluationSignoff.model_validate_json(path.read_text(encoding="utf-8"))
    if signoff.approved_at.tzinfo is None:
        raise ManifestError("evaluation sign-off timestamp requires a timezone")
    if signoff.evaluation_lock_sha256 != lock_sha:
        raise ManifestError("evaluation sign-off does not match evaluation lock")
    return signoff


def reserve_test_read(
    ledger_path: Path,
    lock_path: Path,
    signoff_path: Path,
    *,
    run_id: str,
    test_manifest_sha256: str,
    deviation_path: Path | None = None,
) -> dict:
    lock_path = Path(lock_path)
    if not lock_path.exists():
        raise ManifestError(f"evaluation lock missing at {lock_path}")
    try:
        lock = EvaluationLock.model_validate_json(lock_path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise ManifestError("invalid evaluation lock schema") from exc
    _validate_evaluation_lock(lock)

    lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    _load_signoff(signoff_path, lock_sha)
    if len(test_manifest_sha256) != 64 or any(c not in "0123456789abcdef" for c in test_manifest_sha256):
        raise ManifestError("manifest.test.jsonl sha256 must be 64 lowercase hex characters")

    ledger_path = Path(ledger_path)
    lock_file = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ManifestError("held-out ledger is locked by another process") from exc
    os.close(descriptor)
    try:
        events = _read_ledger(ledger_path)
        same_run = [event for event in events if event.run_id == run_id]
        if same_run:
            first = same_run[0]
            if first.lock_sha256 != lock_sha or first.manifest_test_sha256 != test_manifest_sha256:
                raise ManifestError("same-run resume requires identical hashes")
            if any(event.status == "completed" for event in same_run):
                raise ManifestError(f"run {run_id} already completed")
            event = first.model_copy(update={
                "timestamp": datetime.now(timezone.utc),
                "status": "resumed",
                "report_sha256": None,
                "rung": None,
                "error": None,
            })
            _append_ledger(ledger_path, event)
            return event.model_dump(mode="json")

        reservations = [event for event in events if event.status == "reserved"]
        completed = [event for event in events if event.status == "completed"]
        if len(reservations) >= 2 or len(completed) >= 2:
            raise ManifestError("third held-out read is always rejected")
        if reservations and not completed:
            raise ManifestError(f"held-out test split is reserved by run {reservations[-1].run_id}")

        ordinal = 1
        if completed:
            first = completed[0]
            if first.rung != "D" or not first.report_sha256:
                raise ManifestError("second held-out read requires a completed Rung-D report")
            if deviation_path is None:
                raise ManifestError("second held-out read requires a deviation record")
            deviation = HeldOutDeviation.model_validate_json(Path(deviation_path).read_text(encoding="utf-8"))
            if deviation.approved_at.tzinfo is None or deviation.debug_splits != ["train", "val"]:
                raise ManifestError("deviation requires timezone and train/val-only debugging evidence")
            if any(len(value) != 64 for value in deviation.debug_evidence_sha256):
                raise ManifestError("deviation evidence hashes must be SHA-256")
            if deviation.first_report_sha256 != first.report_sha256:
                raise ManifestError("deviation does not bind the first Rung-D report")
            ordinal = 2

        event = HeldOutLedgerEvent(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            status="reserved",
            ordinal=ordinal,
            lock_sha256=lock_sha,
            manifest_test_sha256=test_manifest_sha256,
        )
        _append_ledger(ledger_path, event)
        return event.model_dump(mode="json")
    finally:
        lock_file.unlink(missing_ok=True)


def record_test_result(
    ledger_path: Path,
    *,
    run_id: str,
    status: Literal["completed", "failed"],
    error: str | None = None,
    report_sha256: str | None = None,
    rung: Literal["A", "B", "C", "D"] | None = None,
) -> dict:
    events = _read_ledger(ledger_path)
    reservations = [event for event in events if event.run_id == run_id and event.status == "reserved"]
    if not reservations:
        raise ManifestError(f"run_id {run_id} not found in ledger")
    reservation = reservations[0]
    if status == "completed" and (report_sha256 is None or rung is None):
        raise ManifestError("completed held-out run requires report hash and rung")
    event = HeldOutLedgerEvent(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc),
        status=status,
        ordinal=reservation.ordinal,
        lock_sha256=reservation.lock_sha256,
        manifest_test_sha256=reservation.manifest_test_sha256,
        report_sha256=report_sha256,
        rung=rung,
        error=error,
    )
    _append_ledger(ledger_path, event)
    return event.model_dump(mode="json")


def run_heldout(
    freeze_dir: Path,
    lock_path: Path,
    signoff_path: Path,
    ledger_path: Path,
    *,
    run_id: str,
    predictions_dir: Path,
    report_path: Path,
    deviation_path: Path | None = None,
    predict_fn: Callable[[str, ManifestRecord], JudgeObservation] | None = None,
    image_loader: Callable[[str], str] | None = None,
) -> dict:
    try:
        lock = EvaluationLock.model_validate_json(Path(lock_path).read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise ManifestError("invalid evaluation lock schema") from exc
    _validate_evaluation_lock(lock)
    expected_test_sha = lock.manifest_hashes.get("manifest.test.jsonl")
    if expected_test_sha is None:
        raise ManifestError("evaluation lock is missing manifest.test.jsonl hash")
    reserve_test_read(
        ledger_path, lock_path, signoff_path,
        run_id=run_id, test_manifest_sha256=expected_test_sha, deviation_path=deviation_path,
    )

    freeze_dir = Path(freeze_dir)
    test_path = freeze_dir / "manifest.test.jsonl"
    try:
        test_bytes = test_path.read_bytes()
    except Exception as exc:
        record_test_result(ledger_path, run_id=run_id, status="failed", error=type(exc).__name__)
        raise
    test_sha = hashlib.sha256(test_bytes).hexdigest()
    if expected_test_sha != test_sha:
        err = f"manifest.test.jsonl sha256 mismatch against evaluation lock ({test_sha} vs {expected_test_sha})"
        record_test_result(ledger_path, run_id=run_id, status="failed", error=err)
        raise ManifestError(err)
    try:
        test_records = list(read_manifest(test_path))
    except Exception as exc:
        record_test_result(ledger_path, run_id=run_id, status="failed", error=type(exc).__name__)
        raise

    predictions_dir = Path(predictions_dir)
    predictions_dir.mkdir(parents=True, exist_ok=True)
    written_files = []
    results = {}

    try:
        for seed_key, ckpt_info in lock.selected_checkpoints.items():
            judge_id = seed_key
            pred_file = predictions_dir / f"{judge_id}.jsonl"
            rows = _load_completed_predictions(
                pred_file,
                test_records,
                judge_id,
                model_id=BASE_MODEL,
                adapter_id=ckpt_info["path"],
                prompt_version=lock.prompt_version,
                checkpoint_id=ckpt_info["checkpoint_id"],
            )
            if rows is None and predict_fn is not None:
                rows = capture_predictions(
                    test_records, judge_id, lambda r, j=judge_id: predict_fn(j, r),
                    model_id=BASE_MODEL, prompt_version=lock.prompt_version,
                    adapter_id=ckpt_info["path"], checkpoint_id=ckpt_info["checkpoint_id"],
                )
            elif rows is None:
                judge_callable = finetuned_judge(image_loader or (lambda p: p), model=ckpt_info["model_id"])
                rows = capture_predictions(
                    test_records, judge_id,
                    judge_callable,
                    model_id=BASE_MODEL, prompt_version=lock.prompt_version,
                    adapter_id=ckpt_info["path"], checkpoint_id=ckpt_info["checkpoint_id"],
                )
            if not pred_file.exists():
                write_predictions(pred_file, rows)
            written_files.append(pred_file.name)
            results[judge_id] = rows

        pred_file = predictions_dir / "zero_shot_base.jsonl"
        rows = _load_completed_predictions(
            pred_file,
            test_records,
            "zero_shot_base",
            model_id=BASE_MODEL,
            adapter_id=None,
            prompt_version=lock.prompt_version,
            checkpoint_id=None,
        )
        if rows is None and predict_fn is not None:
            rows = capture_predictions(
                test_records, "zero_shot_base", lambda r: predict_fn("zero_shot_base", r),
                model_id=BASE_MODEL, prompt_version=lock.prompt_version,
            )
        elif rows is None:
            judge_callable = zero_shot_base_judge(image_loader or (lambda p: p), model=BASE_MODEL)
            rows = capture_predictions(
                test_records, "zero_shot_base",
                judge_callable,
                model_id=BASE_MODEL, prompt_version=lock.prompt_version,
            )
        if not pred_file.exists():
            write_predictions(pred_file, rows)
        written_files.append(pred_file.name)
        results["zero_shot_base"] = rows

        pred_file = predictions_dir / "prompted_gemma.jsonl"
        rows = _load_completed_predictions(
            pred_file,
            test_records,
            "prompted_gemma",
            model_id=lock.vlm_judge_model,
            adapter_id=None,
            prompt_version=lock.prompt_version,
            checkpoint_id=None,
        )
        if rows is None and predict_fn is not None:
            rows = capture_predictions(
                test_records, "prompted_gemma", lambda r: predict_fn("prompted_gemma", r),
                model_id=lock.vlm_judge_model, prompt_version=lock.prompt_version,
            )
        elif rows is None:
            judge_callable = prompted_gemma_judge(image_loader or (lambda p: p))
            rows = capture_predictions(
                test_records, "prompted_gemma",
                judge_callable,
                model_id=lock.vlm_judge_model, prompt_version=lock.prompt_version,
            )
        if not pred_file.exists():
            write_predictions(pred_file, rows)
        written_files.append(pred_file.name)
        results["prompted_gemma"] = rows

        for ctrl_name in ("clip_cosine", "dinov2_cosine"):
            if ctrl_name in lock.controls:
                ctrl_threshold = lock.controls[ctrl_name]["threshold"]
                pred_file = predictions_dir / f"{ctrl_name}.jsonl"
                rows = _load_completed_predictions(
                    pred_file,
                    test_records,
                    ctrl_name,
                    model_id=ctrl_name,
                    adapter_id=None,
                    prompt_version=lock.prompt_version,
                    checkpoint_id=None,
                    threshold_id=str(ctrl_threshold),
                )
                if rows is None and predict_fn is not None:
                    rows = capture_predictions(
                        test_records, ctrl_name, lambda r, c=ctrl_name: predict_fn(c, r),
                        model_id=ctrl_name, prompt_version=lock.prompt_version,
                        threshold_id=str(ctrl_threshold),
                    )
                elif rows is None:
                    judge_callable = embedding_control(ctrl_name, ctrl_threshold, image_loader or (lambda p: p))
                    rows = capture_predictions(
                        test_records, ctrl_name,
                        judge_callable,
                        model_id=ctrl_name, prompt_version=lock.prompt_version,
                        threshold_id=str(ctrl_threshold),
                    )
                if not pred_file.exists():
                    write_predictions(pred_file, rows)
                written_files.append(pred_file.name)
                results[ctrl_name] = rows

        report = build_report(
            freeze_dir, lock_path, predictions_dir, report_path, test_records=test_records,
        )
        report_sha = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
        rung = report["deployment_decision"]["rung"]
        record_test_result(
            ledger_path, run_id=run_id, status="completed", report_sha256=report_sha, rung=rung,
        )
        return {"run_id": run_id, "predictions": results, "written": written_files, "report": report}
    except Exception as exc:
        record_test_result(ledger_path, run_id=run_id, status="failed", error=type(exc).__name__)
        raise


def classify_claim_rung(
    *,
    beats_base: bool,
    delta_f1_vs_incumbent: float,
    candidate_recall: float,
    incumbent_recall: float,
) -> dict[str, str | bool]:
    if not beats_base:
        rung = "D"
    elif delta_f1_vs_incumbent > 0:
        rung = "A"
    elif delta_f1_vs_incumbent >= -0.03 and candidate_recall >= incumbent_recall:
        rung = "B"
    else:
        rung = "C"
    return {
        "rung": rung,
        "objective4_requirement_met": rung != "D",
        "ship_candidate": rung in ("A", "B"),
    }


def _judge_metrics(
    labels: Sequence[bool],
    records: Sequence[PredictionRecord],
    char_ids: Sequence[str],
) -> dict:
    preds = [record.prediction for record in records]
    precision, recall, f1 = prf1(labels, preds)
    f1_lo, f1_hi = clustered_f1_ci(labels, preds, char_ids, seed=BOOTSTRAP_SEED)
    warm_latencies = [
        record.latency_ms for record in records
        if record.latency_phase == "warm" and record.latency_ms is not None
    ]
    cold_latencies = [
        record.latency_ms for record in records
        if record.latency_phase == "cold" and record.latency_ms is not None
    ]
    malformed = sum(record.parse_status == "malformed" for record in records)
    n = len(records)
    return {
        "n": n,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f1_ci95": [f1_lo, f1_hi],
        "auroc": auroc(labels, [record.score for record in records]),
        "cohen_kappa": cohen_kappa(labels, preds),
        "calibration": calibration(
            labels, [record.confidence for record in records], predictions=preds,
        ),
        "latency_ms": {"n": len(warm_latencies), **mean_sample_std(warm_latencies)},
        "cold_start_latency_ms": {
            "value": cold_latencies[0] if cold_latencies else None,
            "reason": None if cold_latencies else "cold-start observation missing",
        },
        "cost_per_call_usd": {
            "value": None,
            "reason": "cost is not recorded in immutable prediction evidence",
        },
        "parse_failures": {"count": malformed, "rate": malformed / n if n else 0.0},
        "label_prevalence": sum(labels) / n if n else None,
        "prediction_rate": sum(preds) / n if n else None,
    }


def _read_frozen_report_artifact(freeze_dir: Path, lock: EvaluationLock, name: str) -> bytes:
    expected = lock.report_artifact_hashes.get(name)
    path = freeze_dir / name
    if not isinstance(expected, str) or not path.exists():
        raise ManifestError(f"frozen report artifact missing: {name}")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ManifestError(f"frozen report artifact SHA-256 mismatch: {name}")
    return content


def build_report(
    freeze_dir: Path,
    lock_path: Path,
    predictions_dir: Path,
    out_path: Path | None = None,
    *,
    test_records: Sequence[ManifestRecord] | None = None,
) -> dict:
    freeze_dir = Path(freeze_dir)
    lock_path = Path(lock_path)
    predictions_dir = Path(predictions_dir)

    lock_dict = json.loads(lock_path.read_text(encoding="utf-8"))
    lock = EvaluationLock.model_validate(lock_dict)

    if test_records is None:
        raise ManifestError("held-out records must come from the guarded runner")
    test_records = list(test_records)
    test_labels = [r.label for r in test_records]
    test_char_ids = [r.char_id for r in test_records]

    slices_data = json.loads(
        _read_frozen_report_artifact(freeze_dir, lock, "character_slices.json").decode("utf-8")
    )
    if not isinstance(slices_data, dict) or any(
        not isinstance(char_id, str) or value not in ("human", "non_human")
        for char_id, value in slices_data.items()
    ):
        raise ManifestError("character slice evidence must map character IDs to human/non_human")
    missing_slice_ids = sorted(set(test_char_ids) - set(slices_data))
    if missing_slice_ids:
        raise ManifestError("character slice evidence does not cover every held-out character")
    non_human_char_ids = {
        char_id for char_id, slice_name in slices_data.items() if slice_name == "non_human"
    }

    predictions_by_judge: dict[str, list[PredictionRecord]] = {}
    for judge_name in REPORT_JUDGES:
        pred_file = predictions_dir / f"{judge_name}.jsonl"
        if not pred_file.exists():
            raise ManifestError(f"prediction file missing for {judge_name} at {pred_file}")
        pred_bytes = pred_file.read_bytes()
        digest_file = pred_file.with_suffix(pred_file.suffix + ".sha256")
        actual_digest = hashlib.sha256(pred_bytes).hexdigest()
        if not digest_file.exists() or digest_file.read_text(encoding="ascii").strip() != actual_digest:
            raise ManifestError(f"immutable prediction SHA-256 differs at {digest_file.name}")
        lines = [json.loads(line) for line in pred_bytes.decode("utf-8").splitlines() if line.strip()]
        preds = [PredictionRecord.model_validate(p) for p in lines]
        validate_report_prediction_evidence(test_records, preds, judge_name)
        predictions_by_judge[judge_name] = preds

    deployment_seed = lock.deployment_seed
    dep_key = f"seed_{deployment_seed}"
    dep_preds = [p.prediction for p in predictions_by_judge[dep_key]]

    judges_report = {}
    for judge_name, preds_list in predictions_by_judge.items():
        preds = [p.prediction for p in preds_list]
        record_dict = _judge_metrics(test_labels, preds_list, test_char_ids)

        if judge_name in ("zero_shot_base", "prompted_gemma"):
            delta_lo, delta_hi = clustered_delta_f1_ci(
                test_labels, dep_preds, preds, test_char_ids, seed=BOOTSTRAP_SEED
            )
            record_dict["delta_f1_ci95_vs_deployment_seed"] = [delta_lo, delta_hi]
            record_dict["mcnemar_p_vs_deployment_seed"] = mcnemar_exact(test_labels, dep_preds, preds)

        judges_report[judge_name] = record_dict

    seed_f1s = [judges_report[f"seed_{s}"]["f1"] for s in SEEDS]
    seeds_summary = mean_sample_std(seed_f1s)
    seeds_summary["values"] = seed_f1s

    slices_report = {}
    for slice_name, include in (
        ("human", lambda char_id: char_id not in non_human_char_ids),
        ("non_human", lambda char_id: char_id in non_human_char_ids),
    ):
        indices = [i for i, char_id in enumerate(test_char_ids) if include(char_id)]
        if not indices:
            slices_report[slice_name] = {
                "status": "unavailable",
                "reason": f"no {slice_name} characters in test split",
            }
            continue
        labels = [test_labels[i] for i in indices]
        char_ids = [test_char_ids[i] for i in indices]
        slices_report[slice_name] = {
            judge_name: _judge_metrics(
                labels, [predictions_by_judge[judge_name][i] for i in indices], char_ids,
            )
            for judge_name in REPORT_JUDGES
        }

    # One-rater test-retest agreement
    agreement_bytes = _read_frozen_report_artifact(
        freeze_dir, lock, "annotation_agreement.jsonl"
    )
    if not agreement_bytes:
        raise ManifestError("agreement evidence is empty")
    else:
        agr_lines = [json.loads(line) for line in agreement_bytes.decode("utf-8").splitlines() if line.strip()]
        test_slice_by_pair = {
            record.pair_id: (
                "non_human" if record.char_id in non_human_char_ids else "human"
            )
            for record in test_records
        }
        all_agreement_ids = [row.get("pair_id") for row in agr_lines]
        if len(all_agreement_ids) != len(set(all_agreement_ids)):
            raise ManifestError("agreement evidence contains duplicate pair IDs")
        agr_lines = [row for row in agr_lines if row.get("pair_id") in test_slice_by_pair]
        validate_agreement_alignment([record.pair_id for record in test_records], agr_lines)
        if agr_lines:
            if any(
                not isinstance(row.get("labels"), list)
                or len(row["labels"]) != 2
                or any(not isinstance(label, bool) for label in row["labels"])
                for row in agr_lines
            ):
                raise ManifestError("annotation agreement rows require exactly two boolean labels")
            a1_labels = [not row["labels"][0] for row in agr_lines]
            a2_labels = [not row["labels"][1] for row in agr_lines]
            def agreement(rows: Sequence[dict]) -> dict:
                if not rows:
                    return {"status": "unavailable", "reason": "empty slice"}
                left = [not row["labels"][0] for row in rows]
                right = [not row["labels"][1] for row in rows]
                return {
                    "status": "available",
                    "n": len(rows),
                    "cohen_kappa": cohen_kappa(left, right),
                    "percent_agreement": sum(x == y for x, y in zip(left, right)) / len(rows),
                }

            human_agreement = {
                "status": "available",
                "n": len(a1_labels),
                "cohen_kappa": cohen_kappa(a1_labels, a2_labels),
                "percent_agreement": sum(1 for x, y in zip(a1_labels, a2_labels) if x == y) / len(a1_labels),
                "slices": {
                    name: agreement([
                        row for row in agr_lines if test_slice_by_pair[row["pair_id"]] == name
                    ])
                    for name in ("human", "non_human")
                },
            }

    # Pre-registered Claim Ladder (§7.2 & §7.5)
    incumbent_f1 = judges_report["prompted_gemma"]["f1"]
    incumbent_recall = judges_report["prompted_gemma"]["recall"]
    candidate_f1 = judges_report[dep_key]["f1"]
    candidate_recall = judges_report[dep_key]["recall"]
    delta_incumbent = candidate_f1 - incumbent_f1

    base_delta_lo, _ = judges_report["zero_shot_base"]["delta_f1_ci95_vs_deployment_seed"]
    beats_base = base_delta_lo > 0
    claim = classify_claim_rung(
        beats_base=beats_base,
        delta_f1_vs_incumbent=delta_incumbent,
        candidate_recall=candidate_recall,
        incumbent_recall=incumbent_recall,
    )
    rung = claim["rung"]

    model_to_deploy = (
        lock.selected_checkpoints[dep_key]["path"] if claim["ship_candidate"] else lock.vlm_judge_model
    )
    deployment_decision = {
        "rung": rung,
        "ship_candidate": claim["ship_candidate"],
        "incumbent_model": lock.vlm_judge_model,
        "incumbent_f1": incumbent_f1,
        "incumbent_recall": incumbent_recall,
        "candidate_seed": deployment_seed,
        "candidate_checkpoint": lock.selected_checkpoints[dep_key]["checkpoint_id"],
        "candidate_f1": candidate_f1,
        "candidate_recall": candidate_recall,
        "delta_f1_vs_incumbent": delta_incumbent,
        "model_to_deploy": model_to_deploy,
    }

    prediction_rates = {
        name: metrics["prediction_rate"] for name, metrics in judges_report.items()
    }
    report = Objective4Report.model_validate({
        "schema_version": REPORT_SCHEMA_VERSION,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "deployment_seed": deployment_seed,
        "seeds_f1_summary": seeds_summary,
        "judges": judges_report,
        "slices": slices_report,
        "intra_rater_agreement": human_agreement,
        "prediction_rate_drift": {
            f"{dep_key}_vs_{name}": prediction_rates[dep_key] - rate
            for name, rate in prediction_rates.items() if name != dep_key
        },
        "registered_endpoints": {
            "cost_per_call": {
                "status": "unavailable",
                "reason": "not recorded in immutable prediction evidence",
            },
            "dreambench_transfer": {
                "status": "not_collected_by_heldout_runner",
                "reason": "separate descriptive transfer evaluation",
            },
            "downstream_expert_feedback": {
                "status": "not_collected_by_heldout_runner",
                "reason": "reported under Objective 3",
            },
            "data_scaling_ablation": {
                "status": "not_collected_by_heldout_runner",
                "reason": "validation-only experiment",
            },
        },
        "objective4": {
            "requirement_met": claim["objective4_requirement_met"],
            "primary_judge": dep_key,
            "reported_result": judges_report[dep_key],
        },
        "deployment_decision": deployment_decision,
    }).model_dump(mode="json")

    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if not _publish_exclusive(out_path, content) and out_path.read_bytes() != content:
            raise ManifestError(f"immutable report differs at {out_path}")

    return report



def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Objective-4 evaluation and validation runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inv_p = subparsers.add_parser("validation-inventory")
    inv_p.add_argument("--runs", required=True, type=Path)
    inv_p.add_argument("--out", required=True, type=Path)

    capture_p = subparsers.add_parser("capture-validation")
    capture_p.add_argument("--freeze", required=True, type=Path)
    capture_p.add_argument("--candidates", required=True, type=Path)
    capture_p.add_argument("--predictions", required=True, type=Path)

    val_p = subparsers.add_parser("validate")
    val_p.add_argument("--freeze", required=True, type=Path)
    val_p.add_argument("--candidates", required=True, type=Path)
    val_p.add_argument("--predictions", required=True, type=Path)
    val_p.add_argument("--out", required=True, type=Path)

    run_p = subparsers.add_parser("heldout")
    run_p.add_argument("--freeze", required=True, type=Path)
    run_p.add_argument("--lock", required=True, type=Path)
    run_p.add_argument("--signoff", required=True, type=Path)
    run_p.add_argument("--ledger", required=True, type=Path)
    run_p.add_argument("--run-id", required=True, type=str)
    run_p.add_argument("--predictions", required=True, type=Path)
    run_p.add_argument("--out", required=True, type=Path)
    run_p.add_argument("--deviation", type=Path)

    args = parser.parse_args()
    if args.command == "validation-inventory":
        inventory_checkpoints(args.runs, args.out)
    elif args.command == "capture-validation":
        capture_validation(args.freeze, args.candidates, args.predictions)
    elif args.command == "validate":
        validate_offline(args.freeze, args.candidates, args.predictions, args.out)
    elif args.command == "heldout":
        run_heldout(
            freeze_dir=args.freeze, lock_path=args.lock, signoff_path=args.signoff,
            ledger_path=args.ledger, run_id=args.run_id, predictions_dir=args.predictions,
            report_path=args.out, deviation_path=args.deviation,
        )


if __name__ == "__main__":
    cli()
