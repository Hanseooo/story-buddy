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
    assert rows[0].latency_phase == "cold"
    assert rows[1].prediction is False
    assert rows[1].confidence is None
    assert rows[1].latency_ms is None
    assert rows[1].latency_phase == "warm"
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
            latency_phase="warm",
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
            latency_phase="warm",
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


def predictions(records, preds, judge_id="candidate"):
    return [
        ev.PredictionRecord(
            pair_id=r.pair_id,
            char_id=r.char_id,
            split=r.split,
            judge_id=judge_id,
            prediction=p,
            confidence=0.9,
            score=0.9 if p else 0.1,
            latency_ms=10,
            latency_phase="cold" if index == 0 else "warm",
            parse_status="parsed",
            model_id="m",
            prompt_version="1",
        )
        for index, (r, p) in enumerate(zip(records, preds))
    ]


def write_report_evidence_hashes(freeze_dir, lock=None):
    import hashlib
    import json

    names = ("character_slices.json", "annotation_agreement.jsonl")
    hashes = {
        name: hashlib.sha256((freeze_dir / name).read_bytes()).hexdigest()
        for name in names
    }
    (freeze_dir / "freeze_report.json").write_text(
        json.dumps({"artifact_sha256": hashes}), encoding="utf-8"
    )
    if lock is not None:
        lock["report_artifact_hashes"] = hashes


def write_report_evidence(freeze_dir, records, lock):
    import json

    (freeze_dir / "character_slices.json").write_text(
        json.dumps({record.char_id: "human" for record in records}), encoding="utf-8"
    )
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        "".join(
            json.dumps({"pair_id": record.pair_id, "labels": [True, True]}) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    write_report_evidence_hashes(freeze_dir, lock)


@pytest.fixture
def val_records():
    r1 = manifest_record("p1", split="val")
    r1 = r1.model_copy(update={"label": True, "same_character": False})
    r2 = manifest_record("p2", split="val")
    r2 = r2.model_copy(update={"label": False, "same_character": True})
    return [r1, r2]


@pytest.fixture
def valid_lock(tmp_path):
    checkpoints = {}
    for seed, step in ((0, 50), (1, 100), (2, 50)):
        checkpoint = tmp_path / "runs" / f"seed-{seed}" / "output" / f"checkpoint-{step}"
        checkpoint.mkdir(parents=True)
        (checkpoint / "adapter_model.safetensors").write_bytes(f"seed-{seed}".encode())
        checkpoints[seed] = checkpoint
    return {
        "schema_version": ev.PREDICTION_SCHEMA_VERSION,
        "bootstrap_seed": 0,
        "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "base_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "llamafactory_version": "v0.9.5",
        "llamafactory_commit": "7af909522a951e3ad9f022ea6f88b6755257eaa5",
        "deployment_seed": 0,
        "seeds": [0, 1, 2],
        "selected_checkpoints": {
            "seed_0": {
                "model_id": "seed0_checkpoint50",
                "checkpoint_id": "checkpoint-50",
                "step": 50,
                "path": str(checkpoints[0]),
                "sha256": ev._hash_directory(checkpoints[0]),
                "val_f1": 0.85,
            },
            "seed_1": {
                "model_id": "seed1_checkpoint100",
                "checkpoint_id": "checkpoint-100",
                "step": 100,
                "path": str(checkpoints[1]),
                "sha256": ev._hash_directory(checkpoints[1]),
                "val_f1": 0.82,
            },
            "seed_2": {
                "model_id": "seed2_checkpoint50",
                "checkpoint_id": "checkpoint-50",
                "step": 50,
                "path": str(checkpoints[2]),
                "sha256": ev._hash_directory(checkpoints[2]),
                "val_f1": 0.80,
            },
        },
        "controls": {
            "clip_cosine": {"threshold": 0.75, "val_f1": 0.65, "selected_on": "manifest.val.jsonl"},
            "dinov2_cosine": {"threshold": 0.80, "val_f1": 0.70, "selected_on": "manifest.val.jsonl"},
        },
        "manifest_hashes": {
            "manifest.train.jsonl": "1" * 64,
            "manifest.val.jsonl": "2" * 64,
            "manifest.test.jsonl": "3" * 64,
        },
        "report_artifact_hashes": {
            "annotation_agreement.jsonl": "4" * 64,
            "character_slices.json": "5" * 64,
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
    # Scores are positive-oriented negative cosine: p1=-0.4 is more different than p2=-0.9.
    selected = ev.select_threshold([-0.4, -0.9], val_records)
    assert selected["threshold"] in {-0.9, -0.4}
    assert selected["val_f1"] == pytest.approx(1.0)
    assert selected["selected_on"] == "manifest.val.jsonl"


def test_embedding_observation_applies_locked_positive_oriented_threshold():
    assert ev._embedding_observation(similarity=0.4, threshold=-0.6, latency_ms=9) == ev.JudgeObservation(
        prediction=True, confidence=None, score=-0.4, latency_ms=9
    )
    assert ev._embedding_observation(similarity=0.9, threshold=-0.6, latency_ms=9).prediction is False


def test_evaluation_lock_is_immutable_and_contains_all_required_pins(tmp_path, valid_lock):
    path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(path, valid_lock)
    ev.write_evaluation_lock(path, valid_lock)
    with pytest.raises(ManifestError, match="evaluation lock differs"):
        ev.write_evaluation_lock(path, {**valid_lock, "prompt_version": "5"})


def test_concurrent_identical_lock_creation_returns_unambiguous_success(tmp_path, valid_lock):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "evaluation_lock.json"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ev.write_evaluation_lock(path, valid_lock), range(2)))
    assert results == [valid_lock, valid_lock]


@pytest.mark.parametrize("field,value", [
    ("schema_version", 1),
    ("schema_version", "1"),
    ("prompt_version", "   "),
    ("vlm_judge_model", ""),
])
def test_evaluation_lock_rejects_invalid_registered_fields(tmp_path, valid_lock, field, value):
    with pytest.raises(ManifestError):
        ev.write_evaluation_lock(tmp_path / "lock.json", {**valid_lock, field: value})


def test_evaluation_lock_rejects_malformed_digest(tmp_path, valid_lock):
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = "A" * 64
    with pytest.raises(ManifestError, match="SHA-256"):
        ev.write_evaluation_lock(tmp_path / "lock.json", valid_lock)


def test_evaluation_lock_rejects_checkpoint_identity_drift(tmp_path, valid_lock):
    valid_lock["selected_checkpoints"]["seed_0"]["sha256"] = "a" * 64
    with pytest.raises(ManifestError, match="checkpoint.*digest"):
        ev.write_evaluation_lock(tmp_path / "lock.json", valid_lock)



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
    import hashlib
    import json
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    val_mf = freeze_dir / "manifest.val.jsonl"
    val_mf.write_text("".join(json.dumps(r.model_dump(mode="json")) + "\n" for r in val_records), encoding="utf-8")
    for split in ("train", "test"):
        (freeze_dir / f"manifest.{split}.jsonl").write_text("", encoding="utf-8")
    (freeze_dir / "freeze_report.json").write_text(json.dumps({"artifact_sha256": {
        f"manifest.{split}.jsonl": hashlib.sha256((freeze_dir / f"manifest.{split}.jsonl").read_bytes()).hexdigest()
        for split in ("train", "val", "test")
    } | {
        "annotation_agreement.jsonl": "4" * 64,
        "character_slices.json": "5" * 64,
    }}), encoding="utf-8")

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
    for control in ("clip_cosine", "dinov2_cosine"):
        ev.write_predictions(preds_dir / f"{control}.jsonl", predictions(val_records, [True, False]))

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
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)

    # First reservation succeeds
    entry1 = ev.reserve_test_read(
        ledger_path, lock_path, signoff, run_id="run-1", test_manifest_sha256="3" * 64,
    )
    assert entry1["status"] == "reserved"
    assert entry1["run_id"] == "run-1"

    # Second reservation for different run_id fails closed
    with pytest.raises(ManifestError, match="reserved by"):
        ev.reserve_test_read(
            ledger_path, lock_path, signoff, run_id="run-2", test_manifest_sha256="3" * 64,
        )


def test_record_test_result_updates_status(tmp_path, valid_lock):
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    (freeze_dir / "manifest.test.jsonl").write_text("test_data", encoding="utf-8")
    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)

    ev.reserve_test_read(
        ledger_path, lock_path, signoff, run_id="run-1", test_manifest_sha256="3" * 64,
    )
    res = ev.record_test_result(
        ledger_path, run_id="run-1", status="completed", report_sha256="a" * 64, rung="B"
    )
    assert res["status"] == "completed"
    assert res["rung"] == "B"


def test_run_heldout_evaluates_only_test_manifest_and_records_ledger(tmp_path, valid_lock):
    import json
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    test_rec = manifest_record("p_test", split="test")
    (freeze_dir / "manifest.test.jsonl").write_text(json.dumps(test_rec.model_dump(mode="json")) + "\n", encoding="utf-8")
    write_report_evidence(freeze_dir, [test_rec], valid_lock)
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
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)

    def mock_predict(judge_name, record):
        return ev.JudgeObservation(prediction=True, confidence=0.85, score=0.85, latency_ms=20)

    res = ev.run_heldout(
        freeze_dir=freeze_dir,
        lock_path=lock_path,
        signoff_path=signoff,
        ledger_path=ledger_path,
        run_id="run-1",
        predictions_dir=preds_dir,
        report_path=tmp_path / "report.json",
        predict_fn=mock_predict,
    )
    assert "predictions" in res
    assert (preds_dir / "seed_0.jsonl").exists()

    # Repeat run fails closed
    with pytest.raises(ManifestError, match="deviation"):
        ev.run_heldout(
            freeze_dir=freeze_dir,
            lock_path=lock_path,
            signoff_path=signoff,
            ledger_path=ledger_path,
            run_id="run-2",
            predictions_dir=preds_dir,
            report_path=tmp_path / "report-2.json",
            predict_fn=mock_predict,
        )


def test_heldout_reserves_before_manifest_parse(tmp_path, valid_lock, monkeypatch):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    test_path = freeze_dir / "manifest.test.jsonl"
    record = manifest_record("p_test", split="test")
    test_path.write_text(record.model_dump_json() + "\n", encoding="utf-8")
    write_report_evidence(freeze_dir, [record], valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)
    ledger = tmp_path / "ledger.jsonl"
    real_read_manifest = ev.read_manifest

    def guarded_read(path):
        assert ev._read_ledger(ledger)[0].status == "reserved"
        return real_read_manifest(path)

    monkeypatch.setattr(ev, "read_manifest", guarded_read)
    ev.run_heldout(
        freeze_dir, lock_path, signoff, ledger, run_id="run-1",
        predictions_dir=tmp_path / "predictions", report_path=tmp_path / "report.json",
        predict_fn=lambda judge, row: ev.JudgeObservation(prediction=False, latency_ms=1),
    )


def test_heldout_resume_reuses_hash_verified_predictions(tmp_path, valid_lock, monkeypatch):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    record = manifest_record("p_test", split="test")
    test_path = freeze_dir / "manifest.test.jsonl"
    test_path.write_text(record.model_dump_json() + "\n", encoding="utf-8")
    write_report_evidence(freeze_dir, [record], valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)
    ledger = tmp_path / "ledger.jsonl"
    predictions_dir = tmp_path / "predictions"
    calls = []

    original_write = ev.write_predictions
    writes = 0

    def interrupt_after_first(path, rows):
        nonlocal writes
        original_write(path, rows)
        writes += 1
        if writes == 1:
            raise RuntimeError("interrupted")

    monkeypatch.setattr(ev, "write_predictions", interrupt_after_first)
    with pytest.raises(RuntimeError, match="interrupted"):
        ev.run_heldout(
            freeze_dir, lock_path, signoff, ledger, run_id="run-1",
            predictions_dir=predictions_dir, report_path=tmp_path / "report.json",
            predict_fn=lambda judge, row: calls.append(judge) or ev.JudgeObservation(
                prediction=False, latency_ms=1
            ),
        )

    monkeypatch.setattr(ev, "write_predictions", original_write)
    first_prediction = predictions_dir / "seed_0.jsonl"
    original_bytes = first_prediction.read_bytes()
    first_prediction.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="prediction.*SHA-256"):
        ev.run_heldout(
            freeze_dir, lock_path, signoff, ledger, run_id="run-1",
            predictions_dir=predictions_dir, report_path=tmp_path / "report.json",
            predict_fn=lambda judge, row: pytest.fail("tampered evidence must fail before prediction"),
        )
    first_prediction.write_bytes(original_bytes)
    calls.clear()
    ev.run_heldout(
        freeze_dir, lock_path, signoff, ledger, run_id="run-1",
        predictions_dir=predictions_dir, report_path=tmp_path / "report.json",
        predict_fn=lambda judge, row: calls.append(judge) or ev.JudgeObservation(
            prediction=False, latency_ms=1
        ),
    )
    assert "seed_0" not in calls
    assert [event.status for event in ev._read_ledger(ledger)] == [
        "reserved", "failed", "resumed", "failed", "resumed", "completed"
    ]


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
    (freeze_dir / "character_slices.json").write_text(json.dumps({"dragon": "non_human", "human": "human"}), encoding="utf-8")
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        json.dumps({"pair_id": "p1", "labels": [False, False]}) + "\n"
        + json.dumps({"pair_id": "p2", "labels": [True, True]}) + "\n",
        encoding="utf-8",
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)

    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        (freeze_dir / "manifest.test.jsonl").read_bytes()
    ).hexdigest()

    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)

    preds_dir = tmp_path / "predictions"
    preds_dir.mkdir()

    # Write prediction files for all baselines
    for judge_name in ("seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine"):
        # Give prompted_gemma and zero_shot_base lower F1 so candidate beats them
        p_val = False if judge_name in ("prompted_gemma", "zero_shot_base") and r1.pair_id == "p1" else True
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
                latency_phase="cold" if index == 0 else "warm",
                parse_status="parsed",
                model_id="m",
                prompt_version="1",
            )
            for index, r in enumerate(records)
        ]
        ev.write_predictions(preds_dir / f"{judge_name}.jsonl", p_list)


    out_file = tmp_path / "objective4_results.json"
    report = ev.build_report(freeze_dir, lock_path, preds_dir, out_file, test_records=records)

    assert ev.Objective4Report.model_validate(report).schema_version == 1
    assert "seeds_f1_summary" in report
    assert report["seeds_f1_summary"]["mean"] == pytest.approx(1.0)
    assert set(report["judges"]) == set(ev.REPORT_JUDGES)
    assert "slices" in report
    assert set(report["slices"]) == {"human", "non_human"}
    assert report["slices"]["non_human"]["seed_0"]["f1"] == pytest.approx(1.0)
    assert report["slices"]["human"]["seed_0"]["n"] == 1
    assert report["slices"]["human"]["seed_0"]["auroc"] == {
        "value": None, "reason": "AUROC requires both classes"
    }
    assert "intra_rater_agreement" in report
    assert report["intra_rater_agreement"]["percent_agreement"] == pytest.approx(1.0)
    assert report["intra_rater_agreement"]["slices"]["human"]["n"] == 1
    assert report["intra_rater_agreement"]["slices"]["non_human"]["n"] == 1
    assert "deployment_decision" in report
    assert report["objective4"]["requirement_met"] is False
    assert report["deployment_decision"]["ship_candidate"] is False
    assert report["deployment_decision"]["rung"] == "D"
    seed = report["judges"]["seed_0"]
    assert seed["latency_ms"] == {"n": 1, "mean": 15, "sample_std": 0.0}
    assert seed["cold_start_latency_ms"] == {"value": 15, "reason": None}
    assert seed["parse_failures"] == {"count": 0, "rate": 0.0}
    assert seed["label_prevalence"] == 0.5
    assert seed["prediction_rate"] == 0.5
    assert out_file.exists()

    second_file = tmp_path / "objective4_results_copy.json"
    ev.build_report(freeze_dir, lock_path, preds_dir, second_file, test_records=records)
    assert second_file.read_bytes() == out_file.read_bytes()


@pytest.mark.parametrize(
    ("beats_base", "delta", "candidate_recall", "incumbent_recall", "rung", "met", "ships"),
    [
        (True, 0.01, 0.1, 0.9, "A", True, True),
        (True, -0.03, 0.8, 0.8, "B", True, True),
        (True, -0.03, 0.79, 0.8, "C", True, False),
        (True, -0.031, 0.9, 0.8, "C", True, False),
        (False, 0.2, 1.0, 0.0, "D", False, False),
    ],
)
def test_claim_ladder_matches_frozen_preregistration(
    beats_base, delta, candidate_recall, incumbent_recall, rung, met, ships
):
    decision = ev.classify_claim_rung(
        beats_base=beats_base,
        delta_f1_vs_incumbent=delta,
        candidate_recall=candidate_recall,
        incumbent_recall=incumbent_recall,
    )
    assert decision == {
        "rung": rung,
        "objective4_requirement_met": met,
        "ship_candidate": ships,
    }


def test_report_counts_parse_failures_and_aggregates_only_immutable_prediction_rows(
    tmp_path, valid_lock
):
    import hashlib
    import json

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [
        manifest_record("p1", split="test", char_id="human"),
        manifest_record("p2", split="test", char_id="creature").model_copy(
            update={"label": True, "same_character": False}
        ),
    ]
    manifest = freeze_dir / "manifest.test.jsonl"
    manifest.write_text(
        "".join(json.dumps(row.model_dump(mode="json")) + "\n" for row in records),
        encoding="utf-8",
    )
    (freeze_dir / "character_slices.json").write_text(
        '{"human":"human","creature":"non_human"}', encoding="utf-8"
    )
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        '{"pair_id":"p1","labels":[true,false]}\n'
        '{"pair_id":"p2","labels":[false,false]}\n', encoding="utf-8"
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for judge in ev.REPORT_JUDGES:
        rows = predictions(records, [False, False])
        rows = [
            row.model_copy(update={
                "judge_id": judge,
                "latency_ms": latency,
                "parse_status": status,
                "latency_phase": phase,
                "confidence": None if status == "malformed" else row.confidence,
                "score": None if status == "malformed" else row.score,
            })
            for row, latency, status, phase in zip(
                rows, (10, 30), ("parsed", "malformed"), ("cold", "warm")
            )
        ]
        ev.write_predictions(predictions_dir / f"{judge}.jsonl", rows)

    report = ev.build_report(
        freeze_dir, lock_path, predictions_dir, test_records=records
    )

    metric = report["judges"]["seed_0"]
    assert metric["parse_failures"] == {"count": 1, "rate": 0.5}
    assert metric["latency_ms"] == {"n": 1, "mean": 30, "sample_std": 0.0}
    assert metric["cold_start_latency_ms"] == {"value": 10, "reason": None}
    assert metric["calibration"]["status"] == "unavailable"
    assert report["prediction_rate_drift"]["seed_0_vs_zero_shot_base"] == 0.0
    assert report["intra_rater_agreement"]["n"] == 2
    assert report["intra_rater_agreement"]["slices"]["non_human"]["n"] == 1
    assert "pair_id" not in json.dumps(report)

    invalid = dict(report)
    invalid["judges"] = {"seed_0": {"n": 2}}
    with pytest.raises(Exception):
        ev.Objective4Report.model_validate(invalid)
    invalid = dict(report)
    invalid["registered_endpoints"] = {"cost_per_call": report["registered_endpoints"]["cost_per_call"]}
    with pytest.raises(Exception):
        ev.Objective4Report.model_validate(invalid)


def test_report_fails_closed_on_unfrozen_or_incomplete_slice_evidence(tmp_path, valid_lock):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [manifest_record("p1", split="test", char_id="c1")]
    manifest = freeze_dir / "manifest.test.jsonl"
    manifest.write_text(records[0].model_dump_json() + "\n", encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text("{}", encoding="utf-8")
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        '{"pair_id":"p1","labels":[true,true]}\n', encoding="utf-8"
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for judge in ev.REPORT_JUDGES:
        ev.write_predictions(
            predictions_dir / f"{judge}.jsonl", predictions(records, [False], judge)
        )

    with pytest.raises(ManifestError, match="character slice evidence"):
        ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)

    (freeze_dir / "character_slices.json").write_text('{"c1":"human"}', encoding="utf-8")
    with pytest.raises(ManifestError, match="SHA-256"):
        ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)


def test_report_publication_is_exclusive(tmp_path, valid_lock):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [manifest_record("p1", split="test", char_id="c1")]
    manifest = freeze_dir / "manifest.test.jsonl"
    manifest.write_text(records[0].model_dump_json() + "\n", encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text('{"c1":"human"}', encoding="utf-8")
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        '{"pair_id":"p1","labels":[true,true]}\n', encoding="utf-8"
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for judge in ev.REPORT_JUDGES:
        ev.write_predictions(
            predictions_dir / f"{judge}.jsonl", predictions(records, [False], judge)
        )
    report_path = tmp_path / "report.json"
    report_path.write_text("different", encoding="utf-8")

    with pytest.raises(ManifestError, match="report differs"):
        ev.build_report(freeze_dir, lock_path, predictions_dir, report_path, test_records=records)


@pytest.mark.parametrize(
    "pair_ids",
    [("p2", "p1"), ("p1", "p1")],
)
def test_agreement_evidence_requires_exact_ordered_pair_ids(pair_ids):
    rows = [{"pair_id": pair_id, "labels": [True, True]} for pair_id in pair_ids]
    with pytest.raises(ManifestError, match="agreement evidence alignment"):
        ev.validate_agreement_alignment(["p1", "p2"], rows)


@pytest.mark.parametrize("change", ["judge", "phase"])
def test_report_prediction_evidence_requires_judge_identity_and_cold_then_warm(change):
    records = [manifest_record("p1", split="test"), manifest_record("p2", split="test")]
    rows = predictions(records, [False, False])
    if change == "judge":
        rows[1] = rows[1].model_copy(update={"judge_id": "other"})
    else:
        rows[0] = rows[0].model_copy(update={"latency_phase": "warm"})
    with pytest.raises(ManifestError, match="prediction evidence"):
        ev.validate_report_prediction_evidence(records, rows, "candidate")


def test_validate_never_reads_test_and_requires_both_control_predictions(
    tmp_path, val_records, monkeypatch
):
    import hashlib
    import json

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    val_bytes = "".join(json.dumps(r.model_dump(mode="json")) + "\n" for r in val_records).encode()
    (freeze_dir / "manifest.val.jsonl").write_bytes(val_bytes)
    (freeze_dir / "freeze_report.json").write_text(
        json.dumps({
            "artifact_sha256": {
                "manifest.train.jsonl": "1" * 64,
                "manifest.val.jsonl": hashlib.sha256(val_bytes).hexdigest(),
                "manifest.test.jsonl": "3" * 64,
                "annotation_agreement.jsonl": "4" * 64,
                "character_slices.json": "5" * 64,
            }
        }),
        encoding="utf-8",
    )

    runs = tmp_path / "runs"
    for seed in (0, 1, 2):
        checkpoint = runs / f"seed-{seed}" / "output" / "checkpoint-50"
        checkpoint.mkdir(parents=True)
        (checkpoint / "adapter_model.safetensors").write_bytes(b"weights")
    candidates = tmp_path / "candidates.json"
    ev.inventory_checkpoints(runs, candidates)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for seed in (0, 1, 2):
        ev.write_predictions(predictions_dir / f"seed{seed}_checkpoint50.jsonl", predictions(val_records, [True, False]))

    original_read_bytes = ev.Path.read_bytes

    def guarded_read_bytes(path):
        if path.name == "manifest.test.jsonl":
            raise AssertionError("validation opened held-out data")
        return original_read_bytes(path)

    monkeypatch.setattr(ev.Path, "read_bytes", guarded_read_bytes)
    with pytest.raises(ManifestError, match="clip_cosine"):
        ev.validate_offline(freeze_dir, candidates, predictions_dir, tmp_path / "lock.json")


def test_report_reads_frozen_ordered_agreement_labels(tmp_path, valid_lock):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [
        manifest_record("p1", split="test", char_id="c1"),
        manifest_record("p2", split="test", char_id="c2"),
    ]
    test_path = freeze_dir / "manifest.test.jsonl"
    test_path.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text('{"c1":"human","c2":"human"}', encoding="utf-8")
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        '{"pair_id":"p1","labels":[true,false]}\n{"pair_id":"p2","labels":[false,false]}\n',
        encoding="utf-8",
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for judge in ("seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine"):
        ev.write_predictions(
            predictions_dir / f"{judge}.jsonl", predictions(records, [False, False], judge)
        )

    report = ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)
    assert report["intra_rater_agreement"]["n"] == 2
    assert report["intra_rater_agreement"]["percent_agreement"] == 0.5


def test_deployment_never_passes_when_base_ci_includes_zero_or_recall_regresses(
    tmp_path, valid_lock, monkeypatch
):
    import hashlib
    import json

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [manifest_record(f"p{i}", split="test", char_id=f"c{i}") for i in range(4)]
    records[0] = records[0].model_copy(update={"label": True, "same_character": False})
    records[1] = records[1].model_copy(update={"label": True, "same_character": False})
    test_path = freeze_dir / "manifest.test.jsonl"
    test_path.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text(
        json.dumps({f"c{i}": "human" for i in range(4)}), encoding="utf-8"
    )
    (freeze_dir / "annotation_agreement.jsonl").write_text(
        "".join(
            json.dumps({"pair_id": f"p{i}", "labels": [True, True]}) + "\n"
            for i in range(4)
        ),
        encoding="utf-8",
    )
    write_report_evidence_hashes(freeze_dir, valid_lock)
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    candidate = [True, False, False, False]
    base = [False, False, False, False]
    incumbent = [True, True, False, False]
    for judge in ("seed_0", "seed_1", "seed_2"):
        ev.write_predictions(
            predictions_dir / f"{judge}.jsonl", predictions(records, candidate, judge)
        )
    ev.write_predictions(
        predictions_dir / "zero_shot_base.jsonl", predictions(records, base, "zero_shot_base")
    )
    ev.write_predictions(
        predictions_dir / "prompted_gemma.jsonl",
        predictions(records, incumbent, "prompted_gemma"),
    )
    for judge in ("clip_cosine", "dinov2_cosine"):
        ev.write_predictions(
            predictions_dir / f"{judge}.jsonl", predictions(records, base, judge)
        )
    monkeypatch.setattr(ev, "clustered_delta_f1_ci", lambda *args, **kwargs: (-0.1, 0.4))

    report = ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)
    assert report["deployment_decision"]["rung"] == "D"
    assert report["objective4"]["requirement_met"] is False
    assert report["deployment_decision"]["ship_candidate"] is False


def test_vlm_observation_uses_metadata_and_shipped_prompt_for_gemma(monkeypatch):
    from types import SimpleNamespace
    from contracts.story_memory import VlmVerdict
    from pipeline.consistency_check import JUDGE_PROMPT, SceneVerdict

    calls = []

    def fake_judge(prompt, urls, schema, model=None, route="judge"):
        calls.append((prompt, urls, schema, model, route))
        verdict = schema(differences_observed="none", same_character=False)
        return SimpleNamespace(verdict=verdict, confidence=0.8, latency_ms=17)

    monkeypatch.setattr("providers.judge_with_metadata", fake_judge)
    record = manifest_record("p1")
    base = ev._vlm_observer("base", lambda path: f"uri:{path}", prompt=ev.QUESTION, schema=VlmVerdict)
    gemma = ev._vlm_observer(
        "gemma", lambda path: f"uri:{path}",
        prompt=JUDGE_PROMPT.format(name="the character"), schema=SceneVerdict, route="openrouter",
    )

    observation = base(record)
    gemma(record)
    assert observation == ev.JudgeObservation(prediction=True, confidence=0.8, score=0.8, latency_ms=17)
    assert calls[0][0] == ev.QUESTION
    assert calls[0][4] == "judge"
    assert calls[1][0] == JUDGE_PROMPT.format(name="the character")
    assert calls[1][4] == "openrouter"


def test_selected_checkpoint_keeps_unique_vllm_model_id(tmp_path, val_records):
    import hashlib
    import json

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    val_path = freeze_dir / "manifest.val.jsonl"
    val_path.write_text("".join(r.model_dump_json() + "\n" for r in val_records), encoding="utf-8")
    hashes = {
        "manifest.train.jsonl": "1" * 64,
        "manifest.val.jsonl": hashlib.sha256(val_path.read_bytes()).hexdigest(),
        "manifest.test.jsonl": "3" * 64,
        "annotation_agreement.jsonl": "4" * 64,
        "character_slices.json": "5" * 64,
    }
    (freeze_dir / "freeze_report.json").write_text(json.dumps({"artifact_sha256": hashes}), encoding="utf-8")
    runs = tmp_path / "runs"
    for seed in (0, 1, 2):
        checkpoint = runs / f"seed-{seed}" / "output" / "checkpoint-50"
        checkpoint.mkdir(parents=True)
        (checkpoint / "adapter_model.safetensors").write_bytes(str(seed).encode())
    candidates = tmp_path / "candidates.json"
    ev.inventory_checkpoints(runs, candidates)
    pred_dir = tmp_path / "predictions"
    pred_dir.mkdir()
    for name in ("seed0_checkpoint50", "seed1_checkpoint50", "seed2_checkpoint50", "clip_cosine", "dinov2_cosine"):
        ev.write_predictions(pred_dir / f"{name}.jsonl", predictions(val_records, [True, False]))

    lock = ev.validate_offline(freeze_dir, candidates, pred_dir, tmp_path / "lock.json")
    assert [lock["selected_checkpoints"][f"seed_{seed}"]["model_id"] for seed in (0, 1, 2)] == [
        "seed0_checkpoint50", "seed1_checkpoint50", "seed2_checkpoint50"
    ]


def write_signoff(path, lock_path):
    import hashlib
    import json

    path.write_text(json.dumps({
        "evaluation_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "approved_by": "owner",
        "approved_at": "2026-08-25T12:00:00+08:00",
    }), encoding="utf-8")


def test_heldout_requires_matching_external_signoff_before_reservation(tmp_path, valid_lock):
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    (freeze_dir / "manifest.test.jsonl").write_text("secret", encoding="utf-8")

    with pytest.raises(ManifestError, match="sign-off"):
        ev.reserve_test_read(
            tmp_path / "ledger.jsonl", lock_path, tmp_path / "missing-signoff.json",
            run_id="run-1", test_manifest_sha256="3" * 64,
        )
    assert not (tmp_path / "ledger.jsonl").exists()


def test_ledger_requires_hash_stable_resume_and_rung_d_deviation_for_second_read(
    tmp_path, valid_lock
):
    import hashlib
    import json

    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    signoff = tmp_path / "signoff.json"
    write_signoff(signoff, lock_path)
    ledger = tmp_path / "ledger.jsonl"
    test_sha = "3" * 64
    ev.reserve_test_read(ledger, lock_path, signoff, run_id="run-1", test_manifest_sha256=test_sha)
    with pytest.raises(ManifestError, match="identical hashes"):
        ev.reserve_test_read(ledger, lock_path, signoff, run_id="run-1", test_manifest_sha256="4" * 64)

    report = tmp_path / "report.json"
    report.write_text('{"deployment_decision":{"rung":"D"}}', encoding="utf-8")
    ev.record_test_result(
        ledger, run_id="run-1", status="completed",
        report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(), rung="D",
    )
    with pytest.raises(ManifestError, match="deviation"):
        ev.reserve_test_read(ledger, lock_path, signoff, run_id="run-2", test_manifest_sha256=test_sha)

    deviation = tmp_path / "deviation.json"
    deviation.write_text(json.dumps({
        "first_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "defect": "confirmed evaluation-code defect",
        "fix_commit": "a" * 40,
        "debug_evidence_sha256": ["b" * 64],
        "debug_splits": ["train", "val"],
        "approved_at": "2026-08-25T13:00:00+08:00",
    }), encoding="utf-8")
    second = ev.reserve_test_read(
        ledger, lock_path, signoff, run_id="run-2", test_manifest_sha256=test_sha,
        deviation_path=deviation,
    )
    assert second["ordinal"] == 2
    ev.record_test_result(ledger, run_id="run-2", status="completed", report_sha256="c" * 64, rung="B")
    with pytest.raises(ManifestError, match="third"):
        ev.reserve_test_read(ledger, lock_path, signoff, run_id="run-3", test_manifest_sha256=test_sha)


def test_capture_validation_writes_every_candidate_and_control(
    tmp_path, val_records, monkeypatch
):
    import json

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    (freeze_dir / "manifest.val.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in val_records), encoding="utf-8"
    )
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps({"candidates": [
        {"model_id": "seed0_checkpoint50"},
        {"model_id": "seed1_checkpoint50"},
    ]}), encoding="utf-8")

    def observer(record):
        return ev.JudgeObservation(prediction=record.label, confidence=0.8, score=0.8, latency_ms=1)

    monkeypatch.setattr(ev, "finetuned_judge", lambda loader, model: observer)
    monkeypatch.setattr(ev, "embedding_control", lambda name, threshold, loader: observer)
    out = tmp_path / "predictions"
    written = ev.capture_validation(freeze_dir, candidates, out)
    assert written == [
        "seed0_checkpoint50.jsonl", "seed1_checkpoint50.jsonl",
        "clip_cosine.jsonl", "dinov2_cosine.jsonl",
    ]
