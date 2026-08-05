"""Tests for slice C's stage-2 composites
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` §6): `MultinomialSoftmax`'s
new `weighting` knob, which is what lets it serve as the `Loss=L1,
Weighting=W3` composite stage 1's `best_level_per_axis` names for E.

The L composite needs no new code -- it *is* `S2`, already fitted and
recorded in stage 1 (only Sharing differs from `R` there) -- so there is
nothing new to test for it beyond what `test_experiments_stage1_l2_s2.py`
already covers.
"""

from __future__ import annotations

import numpy as np

from hazard_classifier.experiments.candidates import MultinomialSoftmax, _inverse_frequency_weights


def _synthetic_data(rng, n_per_hazard=60, hazards=("hte", "spc_fin", "cse")):
    hazard_array = np.array(sum(([h] * n_per_hazard for h in hazards), []))
    y = rng.integers(0, 3, size=len(hazard_array))
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal
    return X, y, hazard_array


def test_multinomial_softmax_default_is_unchanged_from_stage1s_l1():
    """Backward-compatibility forcing function: the composite feature must
    not perturb L1's own stage-1 result. Bit-identical to a plain
    `MultinomialSoftmax()` call at the default weighting.
    """
    rng = np.random.default_rng(40)
    X, y, hazards = _synthetic_data(rng)

    default = MultinomialSoftmax()
    default.fit(X, y, hazards)
    explicit_w1 = MultinomialSoftmax(name="L1", weighting="W1")
    explicit_w1.fit(X, y, hazards)

    np.testing.assert_array_equal(
        default.predict_proba(X, hazards), explicit_w1.predict_proba(X, hazards)
    )
    assert default.name == "L1"


def test_w3_weighting_changes_the_fit_relative_to_w1():
    """The composite's whole point: W3 must actually reweight the fit, not
    silently behave like W1. Constructed so a locally rare class exists
    within one hazard's own cell (matching W3's local-per-cell semantics,
    same as `TwoHeadFamily`'s own W3).
    """
    rng = np.random.default_rng(41)
    n = 60
    hazards = np.array(["hte"] * n)
    y = np.array([0] * 45 + [1] * 10 + [2] * 5)  # locally imbalanced
    X = rng.normal(size=(n, 4))
    X[:, 0] += np.where(y == 0, -1.0, np.where(y == 1, 0.0, 1.0))

    w1 = MultinomialSoftmax(name="L1", weighting="W1")
    w1.fit(X, y, hazards)
    w3 = MultinomialSoftmax(name="L1+W3", weighting="W3")
    w3.fit(X, y, hazards)

    proba_w1 = w1.predict_proba(X, hazards)
    proba_w3 = w3.predict_proba(X, hazards)
    assert not np.allclose(proba_w1, proba_w3)


def test_w3_weighting_matches_the_shared_inverse_frequency_helper():
    """Pins that the composite reuses `TwoHeadFamily`'s own W3 definition
    (local, per-cell inverse frequency) rather than an independent one --
    verified by capturing the actual sample_weight LogisticRegression saw.
    """
    import hazard_classifier.experiments.candidates as candidates_module

    rng = np.random.default_rng(42)
    n = 50
    hazards = np.array(["hte"] * n)
    y = np.array([0] * 30 + [1] * 15 + [2] * 5)
    X = rng.normal(size=(n, 4))

    captured: dict[str, np.ndarray] = {}
    real_fit = candidates_module.LogisticRegression.fit

    def spy_fit(self, z, y_h, sample_weight=None, **kwargs):
        captured["weight"] = np.asarray(sample_weight)
        return real_fit(self, z, y_h, sample_weight=sample_weight, **kwargs)

    original = candidates_module.LogisticRegression.fit
    candidates_module.LogisticRegression.fit = spy_fit
    try:
        candidate = MultinomialSoftmax(name="L1+W3", weighting="W3")
        candidate.fit(X, y, hazards)
    finally:
        candidates_module.LogisticRegression.fit = original

    expected = _inverse_frequency_weights(y)
    np.testing.assert_array_equal(captured["weight"], expected)


def test_multinomial_softmax_composite_name_is_settable():
    candidate = MultinomialSoftmax(name="L1+W3", weighting="W3")
    assert candidate.name == "L1+W3"
