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
            split=r.split,
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
                "model_id": "seed0_checkpoint50",
                "checkpoint_id": "checkpoint-050",
                "step": 50,
                "path": "runs/seed-0/output/checkpoint-050",
                "sha256": "a" * 64,
                "val_f1": 0.85,
            },
            "seed_1": {
                "model_id": "seed1_checkpoint100",
                "checkpoint_id": "checkpoint-100",
                "step": 100,
                "path": "runs/seed-1/output/checkpoint-100",
                "sha256": "b" * 64,
                "val_f1": 0.82,
            },
            "seed_2": {
                "model_id": "seed2_checkpoint50",
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
                parse_status="parsed",
                model_id="m",
                prompt_version="1",
            )
            for r in records
        ]
        ev.write_predictions(preds_dir / f"{judge_name}.jsonl", p_list)


    out_file = tmp_path / "objective4_results.json"
    report = ev.build_report(freeze_dir, lock_path, preds_dir, out_file, test_records=records)

    assert report["schema_version"] == 1
    assert "seeds_f1_summary" in report
    assert report["seeds_f1_summary"]["mean"] == pytest.approx(1.0)
    assert "baselines" in report
    assert "slices" in report
    assert "non_human" in report["slices"]
    assert report["slices"]["non_human"]["seed_0"]["f1"] == pytest.approx(1.0)
    assert "human_inter_rater_agreement" in report
    assert report["human_inter_rater_agreement"]["percent_agreement"] == pytest.approx(1.0)
    assert "deployment_decision" in report
    assert report["deployment_decision"]["status"] == "fail"
    assert report["deployment_decision"]["rung"] == "D"
    assert out_file.exists()


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
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    for judge in ("seed_0", "seed_1", "seed_2", "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine"):
        ev.write_predictions(predictions_dir / f"{judge}.jsonl", predictions(records, [False, False]))

    report = ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)
    assert report["human_inter_rater_agreement"]["n"] == 2
    assert report["human_inter_rater_agreement"]["percent_agreement"] == 0.5


def test_deployment_never_passes_when_base_ci_includes_zero_or_recall_regresses(
    tmp_path, valid_lock, monkeypatch
):
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    records = [manifest_record(f"p{i}", split="test", char_id=f"c{i}") for i in range(4)]
    records[0] = records[0].model_copy(update={"label": True, "same_character": False})
    records[1] = records[1].model_copy(update={"label": True, "same_character": False})
    test_path = freeze_dir / "manifest.test.jsonl"
    test_path.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")
    (freeze_dir / "character_slices.json").write_text("{}", encoding="utf-8")
    valid_lock["manifest_hashes"]["manifest.test.jsonl"] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    lock_path = tmp_path / "lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    candidate = [True, False, False, False]
    base = [False, False, False, False]
    incumbent = [True, True, False, False]
    for judge in ("seed_0", "seed_1", "seed_2"):
        ev.write_predictions(predictions_dir / f"{judge}.jsonl", predictions(records, candidate))
    ev.write_predictions(predictions_dir / "zero_shot_base.jsonl", predictions(records, base))
    ev.write_predictions(predictions_dir / "prompted_gemma.jsonl", predictions(records, incumbent))
    for judge in ("clip_cosine", "dinov2_cosine"):
        ev.write_predictions(predictions_dir / f"{judge}.jsonl", predictions(records, base))
    monkeypatch.setattr(ev, "clustered_delta_f1_ci", lambda *args, **kwargs: (-0.1, 0.4))

    report = ev.build_report(freeze_dir, lock_path, predictions_dir, test_records=records)
    assert report["deployment_decision"]["rung"] == "D"
    assert report["deployment_decision"]["status"] == "fail"


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
