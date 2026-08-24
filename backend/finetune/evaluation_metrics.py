"""Pure standard-library evaluation metrics for Objective-4 consistency judge."""
import math
import random
import statistics
from collections import defaultdict
from typing import Sequence


def prf1(labels: Sequence[bool], preds: Sequence[bool]) -> tuple[float, float, float]:
    """Precision, recall, F1 on the positive (`different_character` / label=True) class."""
    tp = sum(1 for y, p in zip(labels, preds) if y and p)
    fp = sum(1 for y, p in zip(labels, preds) if not y and p)
    fn = sum(1 for y, p in zip(labels, preds) if y and not p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def clustered_f1_ci(
    labels: Sequence[bool],
    preds: Sequence[bool],
    char_ids: Sequence[str],
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Character-clustered bootstrap confidence interval for positive-class F1."""
    if not labels or not char_ids:
        return 0.0, 0.0
    clusters: dict[str, list[int]] = defaultdict(list)
    for i, char_id in enumerate(char_ids):
        clusters[char_id].append(i)
    keys = sorted(clusters.keys())

    rng = random.Random(seed)
    scores = []
    for _ in range(resamples):
        drawn = [i for key in rng.choices(keys, k=len(keys)) for i in clusters[key]]
        scores.append(prf1([labels[i] for i in drawn], [preds[i] for i in drawn])[2])
    scores.sort()
    lo = scores[int(alpha / 2 * len(scores))]
    hi = scores[min(len(scores) - 1, int((1 - alpha / 2) * len(scores)))]
    return lo, hi


def clustered_delta_f1_ci(
    labels: Sequence[bool],
    tuned_preds: Sequence[bool],
    base_preds: Sequence[bool],
    char_ids: Sequence[str],
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Character-clustered paired bootstrap confidence interval for delta-F1 (tuned - base)."""
    if not labels or not char_ids:
        return 0.0, 0.0
    clusters: dict[str, list[int]] = defaultdict(list)
    for i, char_id in enumerate(char_ids):
        clusters[char_id].append(i)
    keys = sorted(clusters.keys())

    rng = random.Random(seed)
    deltas = []
    for _ in range(resamples):
        drawn = [i for key in rng.choices(keys, k=len(keys)) for i in clusters[key]]
        sub_labels = [labels[i] for i in drawn]
        tuned_f1 = prf1(sub_labels, [tuned_preds[i] for i in drawn])[2]
        base_f1 = prf1(sub_labels, [base_preds[i] for i in drawn])[2]
        deltas.append(tuned_f1 - base_f1)
    deltas.sort()
    lo = deltas[int(alpha / 2 * len(deltas))]
    hi = deltas[min(len(deltas) - 1, int((1 - alpha / 2) * len(deltas)))]
    return lo, hi


def mcnemar_exact(
    labels: Sequence[bool], left: Sequence[bool], right: Sequence[bool]
) -> float:
    """Exact two-tailed McNemar test for discordant predictions against ground truth."""
    left_only = sum(a == y and b != y for y, a, b in zip(labels, left, right))
    right_only = sum(a != y and b == y for y, a, b in zip(labels, left, right))
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, k)
        for k in range(min(left_only, right_only) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def auroc(
    labels: Sequence[bool], scores: Sequence[float | None]
) -> dict[str, float | str | None]:
    """Tied-rank Mann-Whitney AUROC for positive-oriented scores."""
    if len(labels) == 0:
        return {"value": None, "reason": "empty slice"}
    if any(s is None for s in scores):
        return {"value": None, "reason": "scores contain None"}
    pos_count = sum(1 for y in labels if y)
    neg_count = len(labels) - pos_count
    if pos_count == 0 or neg_count == 0:
        return {"value": None, "reason": "AUROC requires both classes"}

    indexed = sorted(enumerate(scores), key=lambda x: x[1])  # type: ignore[arg-type]
    n = len(indexed)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j

    pos_rank_sum = sum(ranks[idx] for idx, y in enumerate(labels) if y)
    u_pos = pos_rank_sum - (pos_count * (pos_count + 1)) / 2.0
    auc = u_pos / (pos_count * neg_count)
    return {"value": auc, "reason": None}


def cohen_kappa(
    labels: Sequence[bool], preds: Sequence[bool]
) -> dict[str, float | str | None]:
    """Cohen's kappa against ground truth or inter-rater agreement."""
    n = len(labels)
    if n == 0:
        return {"value": None, "reason": "empty slice"}
    p_o = sum(1 for y, p in zip(labels, preds) if y == p) / n
    p_pos1 = sum(1 for y in labels if y) / n
    p_neg1 = 1.0 - p_pos1
    p_pos2 = sum(1 for p in preds if p) / n
    p_neg2 = 1.0 - p_pos2
    p_e = (p_pos1 * p_pos2) + (p_neg1 * p_neg2)

    if math.isclose(p_e, 1.0):
        return {"value": None, "reason": "kappa expected agreement is one"}
    kappa = (p_o - p_e) / (1.0 - p_e)
    return {"value": kappa, "reason": None}


def calibration(
    labels: Sequence[bool],
    confidences: Sequence[float | None],
    predictions: Sequence[bool] | None = None,
) -> dict:
    """Exploratory ten-bin reliability table and Brier score."""
    if len(labels) == 0:
        return {"status": "unavailable", "reason": "empty slice", "brier_score": None, "bins": []}
    if any(c is None for c in confidences):
        return {
            "status": "unavailable",
            "reason": "confidences missing or None",
            "brier_score": None,
            "bins": [],
        }

    probs = []
    for idx, conf in enumerate(confidences):
        c = float(conf)  # type: ignore[arg-type]
        if predictions is not None:
            p = c if predictions[idx] else (1.0 - c)
        else:
            p = c
        probs.append(p)

    n = len(labels)
    brier = sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(probs, labels)) / n

    bins = []
    for b in range(10):
        lo = b / 10.0
        hi = (b + 1) / 10.0
        if b == 9:
            indices = [i for i, p in enumerate(probs) if lo <= p <= hi]
        else:
            indices = [i for i, p in enumerate(probs) if lo <= p < hi]

        count = len(indices)
        mean_p = statistics.mean([probs[i] for i in indices]) if count else None
        pos_rate = statistics.mean([1.0 if labels[i] else 0.0 for i in indices]) if count else None
        bins.append({
            "bin": b,
            "range": [lo, hi],
            "count": count,
            "mean_probability": mean_p,
            "positive_rate": pos_rate,
        })

    return {
        "status": "available",
        "reason": None,
        "brier_score": brier,
        "bins": bins,
    }


def mean_sample_std(values: Sequence[float]) -> dict[str, float | None]:
    """Mean and sample standard deviation for multiple training seeds."""
    if not values:
        return {"mean": None, "sample_std": None}
    if len(values) == 1:
        return {"mean": values[0], "sample_std": 0.0}
    return {
        "mean": statistics.mean(values),
        "sample_std": statistics.stdev(values),
    }
