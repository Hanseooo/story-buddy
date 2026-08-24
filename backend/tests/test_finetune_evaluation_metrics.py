"""Tests for pure standard-library evaluation metrics."""
import pytest

from finetune import evaluation_metrics as metrics


def test_exact_metrics_match_small_hand_checked_examples():
    assert metrics.prf1([True, True, False, False], [True, False, True, False]) == pytest.approx(
        (0.5, 0.5, 0.5)
    )
    assert metrics.mcnemar_exact(
        [True, True, False, False], [True, False, True, False], [False, False, True, False]
    ) == pytest.approx(1.0)
    assert metrics.auroc([True, False, True, False], [0.9, 0.8, 0.8, 0.1]) == {
        "value": pytest.approx(0.875),
        "reason": None,
    }
    assert metrics.cohen_kappa([True, True, False, False], [True, False, True, False]) == {
        "value": pytest.approx(0.0),
        "reason": None,
    }


def test_degenerate_metrics_report_unavailable_reasons():
    assert metrics.auroc([], [])["reason"] == "empty slice"
    assert metrics.auroc([True, True], [0.8, 0.9])["reason"] == "AUROC requires both classes"
    assert metrics.cohen_kappa([True, True], [True, True])["reason"] == "kappa expected agreement is one"


def test_cluster_bootstrap_is_character_grouped_and_seeded():
    labels = [True, False, True, False]
    tuned = [True, False, True, False]
    base = [False, False, False, False]
    chars = ["a", "a", "b", "b"]
    first = metrics.clustered_delta_f1_ci(labels, tuned, base, chars, resamples=100, seed=0)
    second = metrics.clustered_delta_f1_ci(labels, tuned, base, chars, resamples=100, seed=0)
    assert first == second
    assert first[0] == pytest.approx(1.0)


def test_calibration_and_brier_score():
    cal = metrics.calibration([True, False], [0.5, 0.0])
    assert cal["status"] == "available"
    assert cal["brier_score"] == pytest.approx(0.125)
    assert len(cal["bins"]) == 10
    missing = metrics.calibration([True, False], [0.5, None])
    assert missing["status"] == "unavailable"
    assert missing["reason"] is not None


def test_mean_sample_std():
    summary = metrics.mean_sample_std([0.8, 0.82, 0.84])
    assert summary["mean"] == pytest.approx(0.82)
    assert summary["sample_std"] == pytest.approx(0.02)


def test_prf1_scores_the_different_character_class():
    labels = [True, True, True, False, False]
    preds = [True, True, False, True, False]
    p, r, f1 = metrics.prf1(labels, preds)
    assert p == pytest.approx(2 / 3)
    assert r == pytest.approx(2 / 3)
    assert f1 == pytest.approx(2 / 3)


def test_prf1_is_zero_rather_than_undefined_when_nothing_is_predicted_positive():
    assert metrics.prf1([True, False], [False, False]) == (0.0, 0.0, 0.0)


def test_bootstrap_resamples_by_char_id_not_by_pair():
    labels = [True] * 4 + [False] * 4
    preds = [True] * 4 + [False] * 4
    char_ids = ["a", "a", "a", "a", "b", "b", "b", "b"]
    lo, hi = metrics.clustered_f1_ci(labels, preds, char_ids, resamples=50, seed=0)
    assert 0.0 <= lo <= hi <= 1.0

