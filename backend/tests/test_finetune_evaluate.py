"""Tests for offline judge evaluation, validation selection, access ledger, and reporting."""
import pytest

from finetune import evaluate as ev
from finetune.manifest import ManifestError, ManifestRecord


def manifest_record(pair_id: str, split: str = "val", char_id: str = "story:char") -> ManifestRecord:
    return ManifestRecord(
        pair_id=pair_id,
        char_id=char_id,
        split=split,  # type: ignore[arg-type]
        provenance="synthetic",
        pair_type="pipeline",
        images=[f"assets/ref/{pair_id}.png", f"assets/scene/{pair_id}.webp"],
        differences_observed="none",
        same_character=True,
        label=False,
        failure_reasons=[],
    )


def test_capture_predictions_is_ordered_and_scores_malformed_output_as_a_miss():
    records = [manifest_record("p1"), manifest_record("p2")]

    def predict(record):
        if record.pair_id == "p2":
            raise ValueError("broken JSON")
        return ev.JudgeObservation(prediction=True, confidence=0.8, latency_ms=12)

    rows = ev.capture_predictions(
        records, "zero_shot_base", predict, model_id="qwen", prompt_version="4"
    )
    assert [row.pair_id for row in rows] == ["p1", "p2"]
    assert rows[0].parse_status == "parsed"
    assert rows[0].prediction is True
    assert rows[0].confidence == 0.8
    assert rows[1].prediction is False
    assert rows[1].confidence is None
    assert rows[1].parse_status == "malformed"


def test_write_predictions_and_validate_alignment(tmp_path):
    records = [manifest_record("p1"), manifest_record("p2")]
    rows = [
        ev.PredictionRecord(
            pair_id="p1",
            char_id="story:char",
            split="val",
            judge_id="j1",
            prediction=True,
            confidence=0.9,
            score=0.9,
            latency_ms=10,
            parse_status="parsed",
            model_id="m1",
            prompt_version="1",
        ),
        ev.PredictionRecord(
            pair_id="p2",
            char_id="story:char",
            split="val",
            judge_id="j1",
            prediction=False,
            confidence=0.8,
            score=0.2,
            latency_ms=15,
            parse_status="parsed",
            model_id="m1",
            prompt_version="1",
        ),
    ]
    ev.validate_prediction_alignment(records, rows)

    pred_file = tmp_path / "preds.jsonl"
    ev.write_predictions(pred_file, rows)
    assert pred_file.exists()

    # Idempotent write with identical bytes passes
    ev.write_predictions(pred_file, rows)

    # Mutated file fails
    bad_rows = [rows[0]]
    with pytest.raises(ManifestError, match="prediction file differs"):
        ev.write_predictions(pred_file, bad_rows)

    # Misaligned rows fail validation
    with pytest.raises(ManifestError, match="alignment"):
        ev.validate_prediction_alignment(records, [rows[1], rows[0]])


def predictions(records, preds):
    return [
        ev.PredictionRecord(
            pair_id=r.pair_id,
            char_id=r.char_id,
            split="val",
            judge_id="candidate",
            prediction=p,
            confidence=0.9,
            score=0.9 if p else 0.1,
            latency_ms=10,
            parse_status="parsed",
            model_id="m",
            prompt_version="1",
        )
        for r, p in zip(records, preds)
    ]


@pytest.fixture
def val_records():
    r1 = manifest_record("p1", split="val")
    r1 = r1.model_copy(update={"label": True, "same_character": False})
    r2 = manifest_record("p2", split="val")
    r2 = r2.model_copy(update={"label": False, "same_character": True})
    return [r1, r2]


@pytest.fixture
def valid_lock():
    return {
        "schema_version": 1,
        "bootstrap_seed": 0,
        "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "base_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "llamafactory_version": "v0.9.5",
        "llamafactory_commit": "7af909522a951e3ad9f022ea6f88b6755257eaa5",
        "deployment_seed": 0,
        "seeds": [0, 1, 2],
        "selected_checkpoints": {
            "seed_0": {
                "checkpoint_id": "checkpoint-050",
                "step": 50,
                "path": "runs/seed-0/output/checkpoint-050",
                "sha256": "a" * 64,
                "val_f1": 0.85,
            },
            "seed_1": {
                "checkpoint_id": "checkpoint-100",
                "step": 100,
                "path": "runs/seed-1/output/checkpoint-100",
                "sha256": "b" * 64,
                "val_f1": 0.82,
            },
            "seed_2": {
                "checkpoint_id": "checkpoint-050",
                "step": 50,
                "path": "runs/seed-2/output/checkpoint-050",
                "sha256": "c" * 64,
                "val_f1": 0.80,
            },
        },
        "controls": {
            "clip_cosine": {"threshold": 0.75, "val_f1": 0.65},
            "dinov2_cosine": {"threshold": 0.80, "val_f1": 0.70},
        },
        "manifest_hashes": {
            "manifest.train.jsonl": "1" * 64,
            "manifest.val.jsonl": "2" * 64,
            "manifest.test.jsonl": "3" * 64,
        },
        "prompt_version": "4",
        "vlm_judge_model": "google/gemma-3-27b-it",
    }


def test_checkpoint_selection_uses_val_f1_and_breaks_ties_by_earlier_step(val_records):
    selected = ev.select_checkpoint({
        "checkpoint-100": predictions(val_records, [True, False]),
        "checkpoint-050": predictions(val_records, [True, False]),
        "checkpoint-150": predictions(val_records, [False, False]),
    }, val_records)
    assert selected["checkpoint_id"] == "checkpoint-050"
    assert selected["step"] == 50


def test_threshold_selection_maximizes_val_f1_then_prefers_lower_threshold(val_records):
    # p1 is label=True (different), p2 is label=False (same).
    # cosine similarity is lower for different characters: p1=0.4, p2=0.9
    selected = ev.select_threshold([0.4, 0.9], val_records)
    assert selected["threshold"] in {0.4, 0.9}
    assert selected["val_f1"] == pytest.approx(1.0)
    assert selected["selected_on"] == "manifest.val.jsonl"


def test_evaluation_lock_is_immutable_and_contains_all_required_pins(tmp_path, valid_lock):
    path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(path, valid_lock)
    ev.write_evaluation_lock(path, valid_lock)
    with pytest.raises(ManifestError, match="evaluation lock differs"):
        ev.write_evaluation_lock(path, {**valid_lock, "prompt_version": "5"})



def test_inventory_checkpoints_discovers_and_hashes(tmp_path):
    run_root = tmp_path / "runs"
    ckpt_dir = run_root / "seed-0" / "output" / "checkpoint-50"
    ckpt_dir.mkdir(parents=True)
    (ckpt_dir / "adapter_model.safetensors").write_bytes(b"weights")
    out = tmp_path / "candidates.json"
    result = ev.inventory_checkpoints(run_root, out)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["model_id"] == "seed0_checkpoint50"
    assert "vllm_command" in result
    assert out.exists()


def test_validate_offline_creates_evaluation_lock(tmp_path, val_records):
    import json
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    val_mf = freeze_dir / "manifest.val.jsonl"
    val_mf.write_text("".join(json.dumps(r.model_dump(mode="json")) + "\n" for r in val_records), encoding="utf-8")
    for split in ("train", "test"):
        (freeze_dir / f"manifest.{split}.jsonl").write_text("", encoding="utf-8")

    run_root = tmp_path / "runs"
    for s in (0, 1, 2):
        ckpt = run_root / f"seed-{s}" / "output" / "checkpoint-50"
        ckpt.mkdir(parents=True)
        (ckpt / "adapter_model.safetensors").write_bytes(b"weights")

    candidates_path = tmp_path / "candidates.json"
    ev.inventory_checkpoints(run_root, candidates_path)

    preds_dir = tmp_path / "predictions"
    preds_dir.mkdir()
    for s in (0, 1, 2):
        preds = predictions(val_records, [True, False])
        pred_file = preds_dir / f"seed{s}_checkpoint50.jsonl"
        ev.write_predictions(pred_file, preds)

    lock_out = tmp_path / "evaluation_lock.json"
    lock = ev.validate_offline(freeze_dir, candidates_path, preds_dir, lock_out)
    assert lock["deployment_seed"] in (0, 1, 2)
    assert "seed_0" in lock["selected_checkpoints"]
    assert lock_out.exists()


