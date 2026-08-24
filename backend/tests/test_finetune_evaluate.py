"""Tests for offline judge evaluation, validation selection, access ledger, and reporting."""
import pytest

from finetune import evaluate as ev
from finetune.manifest import ManifestError, ManifestRecord


def manifest_record(pair_id: str, split: str = "val", char_id: str = "story:char") -> ManifestRecord:
    provenance = "donated" if split == "test" else "synthetic"
    return ManifestRecord(
        pair_id=pair_id,
        char_id=char_id,
        split=split,  # type: ignore[arg-type]
        provenance=provenance,  # type: ignore[arg-type]
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


def test_reserve_test_read_prevents_duplicate_reservations(tmp_path, valid_lock):
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    (freeze_dir / "manifest.test.jsonl").write_text("test_data", encoding="utf-8")
    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"

    # First reservation succeeds
    entry1 = ev.reserve_test_read(
        ledger_path, lock_path, freeze_dir, run_id="run-1", approver="Hanseooo", purpose="capstone final test"
    )
    assert entry1["status"] == "reserved"
    assert entry1["run_id"] == "run-1"

    # Second reservation for different run_id fails closed
    with pytest.raises(ManifestError, match="already been accessed"):
        ev.reserve_test_read(
            ledger_path, lock_path, freeze_dir, run_id="run-2", approver="Hanseooo", purpose="repeat"
        )


def test_record_test_result_updates_status(tmp_path, valid_lock):
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    (freeze_dir / "manifest.test.jsonl").write_text("test_data", encoding="utf-8")
    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"

    ev.reserve_test_read(
        ledger_path, lock_path, freeze_dir, run_id="run-1", approver="Hanseooo", purpose="capstone final test"
    )
    res = ev.record_test_result(ledger_path, run_id="run-1", status="completed", predictions_written=["preds.jsonl"])
    assert res["status"] == "completed"
    assert res["predictions_written"] == ["preds.jsonl"]


def test_run_heldout_evaluates_only_test_manifest_and_records_ledger(tmp_path, valid_lock):
    import json
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    test_rec = manifest_record("p_test", split="test")
    (freeze_dir / "manifest.test.jsonl").write_text(json.dumps(test_rec.model_dump(mode="json")) + "\n", encoding="utf-8")
    for split in ("train", "val"):
        (freeze_dir / f"manifest.{split}.jsonl").write_text("", encoding="utf-8")

    # Update manifest hash in valid_lock for test manifest
    import hashlib
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        (freeze_dir / "manifest.test.jsonl").read_bytes()
    ).hexdigest()

    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"
    preds_dir = tmp_path / "test_predictions"

    def mock_predict(judge_name, record):
        return ev.JudgeObservation(prediction=True, confidence=0.85, score=0.85, latency_ms=20)

    res = ev.run_heldout(
        freeze_dir=freeze_dir,
        lock_path=lock_path,
        ledger_path=ledger_path,
        run_id="run-1",
        approver="Hanseooo",
        purpose="capstone final held-out run",
        predictions_dir=preds_dir,
        predict_fn=mock_predict,
    )
    assert "predictions" in res
    assert (preds_dir / "seed_0.jsonl").exists()

    # Repeat run fails closed
    with pytest.raises(ManifestError, match="already completed|already been accessed"):
        ev.run_heldout(
            freeze_dir=freeze_dir,
            lock_path=lock_path,
            ledger_path=ledger_path,
            run_id="run-2",
            approver="Hanseooo",
            purpose="repeat attempt",
            predictions_dir=preds_dir,
            predict_fn=mock_predict,
        )


def test_build_report_computes_three_seeds_baselines_slices_and_deployment_rung(tmp_path, valid_lock):
    import json
    import hashlib
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()

    r1 = manifest_record("p1", split="test", char_id="dragon")
    r1 = r1.model_copy(update={"label": True, "same_character": False})
    r2 = manifest_record("p2", split="test", char_id="human")
    r2 = r2.model_copy(update={"label": False, "same_character": True})
    records = [r1, r2]

    (freeze_dir / "manifest.test.jsonl").write_text("".join(json.dumps(r.model_dump(mode="json")) + "\n" for r in records), encoding="utf-8")
    for split in ("train", "val"):
        (freeze_dir / f"manifest.{split}.jsonl").write_text("", encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text(json.dumps({"non_human": ["dragon"]}), encoding="utf-8")

    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        (freeze_dir / "manifest.test.jsonl").read_bytes()
    ).hexdigest()

    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)

    preds_dir = tmp_path / "predictions"
    preds_dir.mkdir()

    # Write prediction files for all baselines
    for judge_name in ("seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine"):
        # Give prompted_gemma lower F1 so candidate beats incumbent
        p_val = False if judge_name == "prompted_gemma" and r1.pair_id == "p1" else True
        p_list = [
            ev.PredictionRecord(
                pair_id=r.pair_id,
                char_id=r.char_id,
                split="test",
                judge_id=judge_name,
                prediction=p_val if r.pair_id == "p1" else False,
                confidence=0.85,
                score=0.4 if r.pair_id == "p1" else 0.9,
                latency_ms=15,
                parse_status="parsed",
                model_id="m",
                prompt_version="1",
            )
            for r in records
        ]
        ev.write_predictions(preds_dir / f"{judge_name}.jsonl", p_list)


    out_file = tmp_path / "objective4_results.json"
    report = ev.build_report(freeze_dir, lock_path, preds_dir, out_file)

    assert report["schema_version"] == 1
    assert "seeds_f1_summary" in report
    assert report["seeds_f1_summary"]["mean"] == pytest.approx(1.0)
    assert "baselines" in report
    assert "slices" in report
    assert "non_human" in report["slices"]
    assert "deployment_decision" in report
    assert report["deployment_decision"]["status"] == "pass"
    assert out_file.exists()




