"""Science-level tests for the D-9/D-10 monotonicity gate (`PLAN.md` §8.2:
"Threshold optimizer" -- monotonicity asserted via adversarial synthetic
cases where the high head fires without the nonzero head firing).
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import cohen_kappa_score

from hazard_classifier.rules import optimize_ordinal_thresholds, ordinal_prediction


def test_ordinal_prediction_gates_high_on_nonzero():
    # The exact case the toy's ungated rule (`out[high >= high_threshold] =
    # 2`, unconditional) got wrong: rows 0 and 3 have the high head crossing
    # its threshold while the nonzero head does not. The toy would predict 2
    # for both; the gated rule must not.
    nonzero = np.array([0.10, 0.90, 0.90, 0.10])
    high = np.array([0.90, 0.10, 0.90, 0.90])
    out = ordinal_prediction(nonzero, high, nonzero_threshold=0.5, high_threshold=0.5)
    assert out.tolist() == [0, 1, 2, 0]


def test_ordinal_prediction_is_monotone_under_random_inputs():
    rng = np.random.default_rng(0)
    nonzero = rng.uniform(0, 1, size=2000)
    high = rng.uniform(0, 1, size=2000)
    out = ordinal_prediction(nonzero, high, nonzero_threshold=0.5, high_threshold=0.5)
    predicted_high = out == 2
    predicted_at_least_one = out >= 1
    assert np.all(predicted_at_least_one[predicted_high])


def _synthetic_ordinal_dataset(rng, n_per_class=120):
    """Three well-separated clusters in (nonzero, high) probability space, so
    thresholds are recoverable, plus an adversarial slice within class 0
    where the high head fires without the nonzero head firing -- exactly the
    pattern the toy's ungated combination rule mis-scored as 2.
    """
    y0 = np.zeros(n_per_class, dtype=np.int8)
    nz0 = rng.uniform(0.05, 0.30, n_per_class)
    hi0 = rng.uniform(0.05, 0.30, n_per_class)

    n_adversarial = n_per_class // 4
    y_adv = np.zeros(n_adversarial, dtype=np.int8)
    nz_adv = rng.uniform(0.05, 0.30, n_adversarial)
    hi_adv = rng.uniform(0.75, 0.95, n_adversarial)  # high fires, nonzero doesn't

    y1 = np.ones(n_per_class, dtype=np.int8)
    nz1 = rng.uniform(0.70, 0.95, n_per_class)
    hi1 = rng.uniform(0.05, 0.30, n_per_class)

    y2 = np.full(n_per_class, 2, dtype=np.int8)
    nz2 = rng.uniform(0.70, 0.95, n_per_class)
    hi2 = rng.uniform(0.70, 0.95, n_per_class)

    y = np.concatenate([y0, y_adv, y1, y2])
    nonzero = np.concatenate([nz0, nz_adv, nz1, nz2])
    high = np.concatenate([hi0, hi_adv, hi1, hi2])
    return y, nonzero, high


def test_optimize_ordinal_thresholds_never_predicts_2_without_nonzero_crossed():
    rng = np.random.default_rng(1)
    y, nonzero, high = _synthetic_ordinal_dataset(rng)

    nonzero_threshold, high_threshold, _metrics = optimize_ordinal_thresholds(y, nonzero, high)

    pred = ordinal_prediction(nonzero, high, nonzero_threshold, high_threshold)
    predicted_high = pred == 2
    predicted_at_least_one = pred >= 1
    assert np.all(predicted_at_least_one[predicted_high]), (
        "a row was predicted 2 without the nonzero threshold being crossed"
    )

    # The adversarial rows (high fires, nonzero doesn't) must never be
    # scored 2 -- the concrete case D-10 exists to fix.
    adversarial_high_only = (high > 0.7) & (nonzero < 0.4) & (y == 0)
    assert adversarial_high_only.any()
    assert np.all(pred[adversarial_high_only] != 2)


def test_optimize_ordinal_thresholds_recovers_thresholds_that_separate_classes():
    rng = np.random.default_rng(2)
    y, nonzero, high = _synthetic_ordinal_dataset(rng)

    nonzero_threshold, high_threshold, metrics = optimize_ordinal_thresholds(y, nonzero, high)
    pred = ordinal_prediction(nonzero, high, nonzero_threshold, high_threshold)

    exact_accuracy = float(np.mean(pred == y))
    assert exact_accuracy > 0.85
    assert metrics["threshold_train_exact_accuracy"] == pytest.approx(exact_accuracy)
    assert metrics["threshold_train_qwk"] > 0.85


def test_grid_search_qwk_matches_sklearn_quadratic_kappa():
    # Cross-checks the ported vectorized QWK formula (from the toy's
    # `optimize_ordinal_thresholds`) against sklearn's reference
    # implementation, at the winning threshold pair the grid search selects.
    rng = np.random.default_rng(3)
    y, nonzero, high = _synthetic_ordinal_dataset(rng)

    nonzero_threshold, high_threshold, metrics = optimize_ordinal_thresholds(y, nonzero, high)
    pred = ordinal_prediction(nonzero, high, nonzero_threshold, high_threshold)

    sklearn_qwk = cohen_kappa_score(y, pred, weights="quadratic")
    assert metrics["threshold_train_qwk"] == pytest.approx(sklearn_qwk, abs=1e-9)
