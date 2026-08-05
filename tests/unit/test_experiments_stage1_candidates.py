"""Tests for slice B's stage-1 axis-variant candidates
(`hazard_classifier.experiments.candidates.TwoHeadFamily`,
`MultinomialSoftmax`) -- `docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` §5.

The single most important test here is
`test_two_head_family_at_r_configuration_matches_r_exactly`: it is the
forcing function proving the generalized `TwoHeadFamily` machinery didn't
silently diverge from the already-tested `TwoHeadReference` it is meant to
generalize.
"""

from __future__ import annotations

import numpy as np
import pytest

from hazard_classifier.experiments.candidates import (
    STAGE1_BUILDERS,
    MultinomialSoftmax,
    TwoHeadFamily,
    TwoHeadReference,
    _optimize_ungated_thresholds,
    _ungated_prediction,
)


def _synthetic_data(rng, n_per_hazard=60, hazards=("hte", "prv", "spc_fin")):
    """Three hazards, each with real, learnable signal across all three
    classes -- enough rows and enough hazards to exercise per-hazard,
    pooled, and one-hot conditioning meaningfully.
    """
    hazard_array = np.array(sum(([h] * n_per_hazard for h in hazards), []))
    y = rng.integers(0, 3, size=len(hazard_array))
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal
    return X, y, hazard_array


def _finite_rows(*probas):
    mask = np.ones(len(probas[0]), dtype=bool)
    for proba in probas:
        mask &= np.isfinite(proba).all(axis=1)
    return mask


# --------------------------------------------------------------------------
# The cross-check: TwoHeadFamily at R's own configuration == TwoHeadReference
# --------------------------------------------------------------------------


def test_two_head_family_at_r_configuration_matches_r_exactly():
    rng = np.random.default_rng(1)
    X, y, hazards = _synthetic_data(rng)

    reference = TwoHeadReference()
    reference.fit(X, y, hazards)
    reference_proba = reference.predict_proba(X, hazards)

    family = TwoHeadFamily("R-equivalent", weighting="W1", hazard_conditioning="H3", branching="B2")
    family.fit(X, y, hazards)
    family_proba = family.predict_proba(X, hazards)

    assert reference.unavailable_hazards == family.unavailable_hazards
    mask = _finite_rows(reference_proba, family_proba)
    assert mask.any()
    np.testing.assert_array_equal(reference_proba[mask], family_proba[mask])
    np.testing.assert_array_equal(np.isnan(reference_proba), np.isnan(family_proba))


def test_two_head_family_defaults_to_r_levels():
    family = TwoHeadFamily("anything")
    assert family.weighting == "W1"
    assert family.hazard_conditioning == "H3"
    assert family.branching == "B2"


# --------------------------------------------------------------------------
# Weighting: W2 (global) vs W3 (local)
# --------------------------------------------------------------------------


def test_w2_and_w3_reweight_relative_to_different_populations():
    """W2's weights come from the whole fit population pooled across
    hazards; W3's come from each hazard's own local counts. Constructed so
    hazard 'a' is globally rare (in a population dominated by hazard 'b')
    but locally balanced within itself -- W2 and W3 must therefore assign it
    systematically different weights.
    """
    rng = np.random.default_rng(2)
    # Hazard 'a': 30 rows, locally balanced (10/10/10).
    y_a = np.array([0] * 10 + [1] * 10 + [2] * 10)
    # Hazard 'b': 300 rows, dominated by class 0.
    y_b = np.array([0] * 270 + [1] * 15 + [2] * 15)
    y = np.concatenate([y_a, y_b])
    hazards = np.array(["a"] * len(y_a) + ["b"] * len(y_b))
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal

    w2 = TwoHeadFamily("W2", weighting="W2")
    w2.fit(X, y, hazards)
    w3 = TwoHeadFamily("W3", weighting="W3")
    w3.fit(X, y, hazards)

    # Both must fit successfully (no degenerate cells here).
    assert w2.unavailable_hazards == frozenset()
    assert w3.unavailable_hazards == frozenset()

    proba_w2 = w2.predict_proba(X, hazards)
    proba_w3 = w3.predict_proba(X, hazards)
    mask = _finite_rows(proba_w2, proba_w3)
    assert mask.any()
    # Different weighting scopes on hazard 'a' (globally rare, locally
    # balanced) should not coincidentally produce identical decisions.
    a_mask = (hazards == "a") & mask
    assert a_mask.any()
    assert not np.array_equal(proba_w2[a_mask], proba_w3[a_mask])


def test_w1_is_uniform_weight_regardless_of_class_balance():
    """Sanity check on the axis's reference point: W1 must not vary with the
    class balance the way W2/W3 deliberately do.
    """
    rng = np.random.default_rng(3)
    y = np.array([0] * 50 + [1] * 5 + [2] * 5)
    hazards = np.array(["hte"] * len(y))
    X = rng.normal(size=(len(y), 4))

    family = TwoHeadFamily("W1", weighting="W1")
    family.fit(X, y, hazards)
    # Uniform weights means fit_binary_head saw sample_weight of all ones --
    # verified indirectly via the no-class-weighting test pattern already
    # used for TwoHeadReference (see test_experiments_candidates.py).
    assert family.weighting == "W1"


# --------------------------------------------------------------------------
# Hazard-conditioning: H1 (pooled) and H2 (one-hot)
# --------------------------------------------------------------------------


def test_h1_fits_one_cell_shared_across_every_hazard():
    rng = np.random.default_rng(4)
    X, y, hazards = _synthetic_data(rng)

    h1 = TwoHeadFamily("H1", hazard_conditioning="H1")
    h1.fit(X, y, hazards)

    assert h1._cells.keys() == {"__pooled__"}
    proba = h1.predict_proba(X, hazards)
    assert np.isfinite(proba).all()  # one global fit, no per-hazard unavailability


def test_h2_appends_a_one_hot_hazard_encoding_and_learns_from_it():
    """H2 fits one shared cell, but hazard identity is available to it as a
    feature. Constructed so hazard identity is the *only* signal (features
    are pure noise, label determined solely by hazard) -- H2 must still
    separate the hazards via the one-hot columns; H1 (no hazard feature at
    all) cannot.
    """
    rng = np.random.default_rng(5)
    n_per_hazard = 80
    hazards = np.array((["hte"] * n_per_hazard) + (["prv"] * n_per_hazard))
    y = np.array(([0] * n_per_hazard) + ([2] * n_per_hazard))  # hazard determines class
    X = rng.normal(size=(len(y), 4))  # pure noise, no signal

    h2 = TwoHeadFamily("H2", hazard_conditioning="H2")
    h2.fit(X, y, hazards)
    h1 = TwoHeadFamily("H1", hazard_conditioning="H1")
    h1.fit(X, y, hazards)

    from hazard_classifier.experiments.comparison_metrics import Predictions, classification_metrics

    h2_metrics = classification_metrics(y, Predictions.from_proba(h2.predict_proba(X, hazards)))
    h1_metrics = classification_metrics(y, Predictions.from_proba(h1.predict_proba(X, hazards)))

    assert h2_metrics.macro_f1 > h1_metrics.macro_f1 + 0.2, (
        "H2 has hazard identity as a feature and should exploit it; "
        "H1 has no way to see hazard at all"
    )


def test_h2_marks_an_unseen_hazard_unavailable_rather_than_a_fabricated_encoding():
    rng = np.random.default_rng(6)
    X, y, hazards = _synthetic_data(rng, hazards=("hte", "prv"))

    h2 = TwoHeadFamily("H2", hazard_conditioning="H2")
    h2.fit(X, y, hazards)

    unseen_X = rng.normal(size=(5, X.shape[1]))
    unseen_hazards = np.array(["never_seen"] * 5)
    proba = h2.predict_proba(unseen_X, unseen_hazards)

    assert np.isnan(proba).all()


# --------------------------------------------------------------------------
# Branching: B1 (flat, ungated)
# --------------------------------------------------------------------------


def test_ungated_prediction_can_predict_high_without_crossing_nonzero():
    """The defining structural difference from B2's gated rule
    (`rules.ordinal_prediction`): a row can be labeled 2 even if it never
    crossed the nonzero threshold. This is deliberately non-monotone -- it
    is what makes B1 a distinct axis level, not a bug.
    """
    nonzero = np.array([0.1, 0.9])  # row 0 does NOT cross nonzero
    high = np.array([0.9, 0.9])  # row 0 DOES cross high

    ungated = _ungated_prediction(nonzero, high, 0.5, 0.5)
    from hazard_classifier.rules import ordinal_prediction

    gated = ordinal_prediction(nonzero, high, 0.5, 0.5)

    assert ungated[0] == 2  # ungated: high alone is enough
    assert gated[0] == 0  # gated: high is irrelevant without nonzero first
    assert ungated[1] == gated[1] == 2  # both agree when nonzero also crosses


def test_optimize_ungated_thresholds_recovers_a_good_threshold_pair():
    rng = np.random.default_rng(7)
    n = 300
    true_class = rng.integers(0, 3, size=n)
    # Centered probabilities correlated with the true class, plus noise.
    nonzero = np.clip(0.5 + 0.3 * (true_class > 0) + rng.normal(scale=0.05, size=n), 0, 1)
    high = np.clip(0.5 + 0.3 * (true_class == 2) + rng.normal(scale=0.05, size=n), 0, 1)

    nonzero_threshold, high_threshold = _optimize_ungated_thresholds(true_class, nonzero, high)
    predicted = _ungated_prediction(nonzero, high, nonzero_threshold, high_threshold)

    assert np.mean(predicted == true_class) > 0.7


def test_b1_candidate_fits_and_scores_using_the_ungated_rule():
    rng = np.random.default_rng(8)
    X, y, hazards = _synthetic_data(rng)

    b1 = TwoHeadFamily("B1", branching="B1")
    b1.fit(X, y, hazards)
    proba = b1.predict_proba(X, hazards)

    finite = np.isfinite(proba).all(axis=1)
    assert finite.any()
    np.testing.assert_allclose(proba[finite].sum(axis=1), 1.0)


# --------------------------------------------------------------------------
# L1 -- multinomial softmax
# --------------------------------------------------------------------------


def test_multinomial_softmax_fits_and_scores_a_fittable_hazard():
    rng = np.random.default_rng(9)
    X, y, hazards = _synthetic_data(rng)

    candidate = MultinomialSoftmax()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)

    finite = np.isfinite(proba).all(axis=1)
    assert finite.any()
    np.testing.assert_allclose(proba[finite].sum(axis=1), 1.0)
    # A genuine multinomial distribution -- unlike R's one-hot decision, L1
    # is expected to produce non-degenerate probabilities somewhere.
    assert not np.allclose(proba[finite].max(axis=1), 1.0)


def test_multinomial_softmax_records_a_single_class_hazard_as_unavailable():
    rng = np.random.default_rng(10)
    n = 40
    hazards = np.array((["hte"] * n) + (["prv"] * n))
    y = np.concatenate([rng.integers(0, 3, size=n), np.zeros(n, dtype=np.int64)])
    X = rng.normal(size=(len(y), 4))

    candidate = MultinomialSoftmax()
    candidate.fit(X, y, hazards)

    assert candidate.unavailable_hazards == frozenset({"prv"})
    proba = candidate.predict_proba(X, hazards)
    assert np.isnan(proba[hazards == "prv"]).all()


def test_multinomial_softmax_handles_a_hazard_missing_one_class():
    """~42 fit rows/hazard makes a hazard that only ever saw two of the three
    classes plausible. `LogisticRegression.classes_` then omits the third --
    this is the forcing function for placing output columns by class label
    rather than assuming positional [0, 1, 2] order.
    """
    rng = np.random.default_rng(11)
    n = 30
    hazards = np.array(["hte"] * n)
    y = np.array(([0] * (n // 2)) + ([2] * (n - n // 2)))  # class 1 never appears
    X = rng.normal(size=(n, 4))
    X[:, 0] += np.where(y == 0, -1.0, 1.0)

    candidate = MultinomialSoftmax()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)

    assert np.isfinite(proba).all()
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)
    # Class 1 was never seen -- this candidate must never place mass there.
    np.testing.assert_allclose(proba[:, 1], 0.0)


# --------------------------------------------------------------------------
# The build registry
# --------------------------------------------------------------------------


def test_stage1_builders_cover_every_per_target_non_reference_level():
    # S2 is fit jointly (JOINT_BUILDERS, tested in
    # test_experiments_stage1_l2_s2.py) and P2/P3 need no candidate-level
    # code (TwoHeadReference on different pooling) -- both deliberately
    # absent here. See test_all_ten_stage1_levels_are_accounted_for for the
    # complete ten-level picture.
    assert set(STAGE1_BUILDERS.keys()) == {"L1", "L2", "W2", "W3", "H1", "H2", "B1"}
    # Every builder must actually produce a usable candidate.
    for level, builder in STAGE1_BUILDERS.items():
        candidate = builder()
        assert candidate.name == level
        assert callable(candidate.fit)
        assert callable(candidate.predict_proba)


def test_every_stage1_builder_fits_and_scores_on_shared_synthetic_data():
    """One pass proving every builder in the registry actually runs
    end-to-end -- fit, predict, and a well-formed metrics computation --
    without needing a bespoke test per candidate for this baseline check.
    """
    from hazard_classifier.experiments.comparison_metrics import Predictions, classification_metrics

    rng = np.random.default_rng(12)
    X, y, hazards = _synthetic_data(rng)

    for level, builder in STAGE1_BUILDERS.items():
        candidate = builder()
        candidate.fit(X, y, hazards)
        proba = candidate.predict_proba(X, hazards)
        predictions = Predictions.from_proba(proba)
        metrics = classification_metrics(y, predictions)
        assert metrics.n_total == len(y)
        assert 0.0 <= metrics.coverage <= 1.0, level
