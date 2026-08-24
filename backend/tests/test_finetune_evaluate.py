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
