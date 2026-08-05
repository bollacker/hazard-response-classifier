"""Tests for `hazard_classifier.experiments.candidates`
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` slice A §4.2).
"""

from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pytest

from hazard_classifier.experiments import candidates
from hazard_classifier.experiments.candidates import TwoHeadReference


def _synthetic_data(rng, n_per_hazard=60):
    """Two hazards: `hte` has real, learnable signal across all three
    classes; `prv` is single-class (all 0), the forcing case for D-45's
    unfittable-cell handling.
    """
    hazards = np.array((["hte"] * n_per_hazard) + (["prv"] * n_per_hazard))
    y_hte = rng.integers(0, 3, size=n_per_hazard)
    y_prv = np.zeros(n_per_hazard, dtype=np.int64)
    y = np.concatenate([y_hte, y_prv])

    # A feature correlated with the label so the fit is not degenerate noise.
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal

    return X, y, hazards


def test_candidate_protocol_shape():
    candidate = TwoHeadReference()
    assert candidate.name == "R"
    assert callable(candidate.fit)
    assert callable(candidate.predict_proba)


def test_r_fits_and_scores_a_fittable_hazard():
    rng = np.random.default_rng(20260804)
    X, y, hazards = _synthetic_data(rng)

    candidate = TwoHeadReference()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)

    assert proba.shape == (len(y), 3)
    hte_mask = hazards == "hte"
    assert np.isfinite(proba[hte_mask]).all()
    np.testing.assert_allclose(proba[hte_mask].sum(axis=1), 1.0)
    # One-hot on the decided label (§4.2: R decides by threshold, not a
    # calibrated distribution) -- exactly one 1.0 per row, never a blend.
    assert set(proba[hte_mask].max(axis=1).tolist()) == {1.0}


def test_r_records_an_unfittable_hazard_as_unavailable_not_substituted():
    rng = np.random.default_rng(20260804)
    X, y, hazards = _synthetic_data(rng)

    candidate = TwoHeadReference()
    candidate.fit(X, y, hazards)

    assert candidate.unavailable_hazards == frozenset({"prv"})

    proba = candidate.predict_proba(X, hazards)
    prv_mask = hazards == "prv"
    assert np.isnan(proba[prv_mask]).all(), "D-45: unfittable is unavailable, never a substitute value"


def test_r_predict_proba_on_a_hazard_never_seen_at_fit_time_is_nan_not_a_crash():
    rng = np.random.default_rng(20260804)
    X, y, hazards = _synthetic_data(rng)

    candidate = TwoHeadReference()
    candidate.fit(X, y, hazards)

    unseen_X = rng.normal(size=(4, 6))
    unseen_hazards = np.array(["never_seen"] * 4)
    proba = candidate.predict_proba(unseen_X, unseen_hazards)

    assert proba.shape == (4, 3)
    assert np.isnan(proba).all()


def test_r_no_class_weighting_means_uniform_sample_weight(monkeypatch):
    """R's `fit` must pass uniform sample_weight to `fit_binary_head` -- the
    axis's `W1` level. Captured via the real `fit_binary_head`, not
    reimplemented, so this is a genuine forcing function against a
    regression that starts passing a non-uniform weight silently.
    """
    seen_weights: list[np.ndarray] = []
    real_fit_binary_head = candidates.fit_binary_head

    def spy(x, y, sample_weight, **kwargs):
        seen_weights.append(np.asarray(sample_weight))
        return real_fit_binary_head(x, y, sample_weight, **kwargs)

    monkeypatch.setattr(candidates, "fit_binary_head", spy)

    rng = np.random.default_rng(1)
    X, y, hazards = _synthetic_data(rng)
    TwoHeadReference().fit(X, y, hazards)

    assert seen_weights, "fit_binary_head was never called"
    for weights in seen_weights:
        np.testing.assert_array_equal(weights, np.ones_like(weights))


def test_assert_no_fixed_rule_import_raises_on_a_forbidden_import(tmp_path):
    bad_module_path = tmp_path / "bad_candidate_module.py"
    bad_module_path.write_text("from hazard_classifier.evaluator.components import integration\n")

    spec = importlib.util.spec_from_file_location("bad_candidate_module", bad_module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # a real import: integration.py itself is fine to load

    with pytest.raises(AssertionError, match="fixed rules"):
        candidates._assert_no_fixed_rule_import(module)


def test_assert_no_fixed_rule_import_passes_the_candidates_module_itself():
    # candidates.py runs this same check on itself at import time (bottom of
    # the module) -- it would have failed to import at all otherwise. Calling
    # it again here confirms it is a clean no-op, not just untriggered.
    candidates._assert_no_fixed_rule_import(sys.modules[candidates.__name__])
