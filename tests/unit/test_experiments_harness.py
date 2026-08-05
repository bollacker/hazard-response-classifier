"""Slice A §4.4 -- the harness anchored against known answers
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md`).

§4.4's first two bullets (hand-computable metrics; the self-comparison
bootstrap) are covered in `test_experiments_comparison_metrics.py`, alongside
the code they pin. What is here is the other two: the majority-class anchor
against the **real** interim data, and end-to-end determinism.

The anchor is the important one. It is the only test in the harness whose
expected values were fixed by an external document
(`PREREGISTRATION_LE_STRUCTURE.md` §3) before the harness existed, so it is
the one test that can catch the harness being confidently wrong in a way its
own internally-consistent unit tests cannot.

No BGE dependency: the majority-class candidate ignores features entirely,
so this reads the real labels without embedding anything (`PLAN.md` §8.1).
"""

from __future__ import annotations

import numpy as np
import pytest

from hazard_classifier.experiments.candidates import MajorityClassBaseline, TwoHeadReference
from hazard_classifier.experiments.comparison_metrics import (
    WORST_CLASS_F1_FLOOR,
    Predictions,
    classification_metrics,
    paired_cluster_bootstrap,
)
from hazard_classifier.interim_data import legitimization_rows, load_interim

# PREREGISTRATION_LE_STRUCTURE.md §3's own table. Verified against the source
# data when this test was written -- an earlier draft of that document carried
# wrong L counts (455/195/113), so these are re-derived here rather than
# trusted, and the test asserts the counts as well as the accuracy.
PREREGISTERED = {
    "L": {"rows": 763, "counts": (434, 187, 142), "majority_accuracy": 0.569},
    "E": {"rows": 859, "counts": (546, 170, 143), "majority_accuracy": 0.636},
}


def _target_frame(target: str):
    frame = load_interim()
    if target == "L":
        return legitimization_rows(frame), "legitimization_value"
    return frame, "enablement_value"


@pytest.mark.parametrize("target", ["L", "E"])
def test_class_balance_matches_the_preregistration_table(target):
    """Lesson 2 of the execution plan: verify every number before relying on
    it. The §3 table is quoted downstream, so this pins it to the data.
    """
    frame, column = _target_frame(target)
    expected = PREREGISTERED[target]

    assert len(frame) == expected["rows"]
    counts = frame[column].value_counts().sort_index()
    assert tuple(int(counts[k]) for k in (0, 1, 2)) == expected["counts"]


@pytest.mark.parametrize("target", ["L", "E"])
def test_majority_class_candidate_reproduces_the_preregistered_figures(target):
    """§4.4's anchor: a candidate that always predicts one class must score
    exactly the majority-class figures the pre-registration states, with a
    worst-class F1 of 0. A harness that cannot reproduce a number computable
    by hand from the class balance is not measuring what it claims to.
    """
    frame, column = _target_frame(target)
    expected = PREREGISTERED[target]

    y = frame[column].to_numpy(dtype=np.int64)
    hazards = frame["hazard"].to_numpy()
    X = np.zeros((len(y), 1), dtype=np.float64)  # ignored by this candidate

    candidate = MajorityClassBaseline()
    candidate.fit(X, y, hazards)
    predictions = Predictions.from_proba(candidate.predict_proba(X, hazards))
    metrics = classification_metrics(y, predictions)

    assert candidate.majority_class == 0
    assert metrics.accuracy == pytest.approx(expected["majority_accuracy"], abs=5e-4)
    assert metrics.worst_class_f1 == 0.0
    assert metrics.coverage == 1.0
    # Only the majority class gets any credit at all.
    assert metrics.per_class_f1[1] == 0.0
    assert metrics.per_class_f1[2] == 0.0


@pytest.mark.parametrize("target", ["L", "E"])
def test_the_majority_class_candidate_is_rejected_by_the_worst_class_floor(target):
    """Connects the anchor to the rule that uses it: §3's floor exists to
    reject exactly this candidate -- respectable accuracy, useless on the two
    classes that matter.
    """
    frame, column = _target_frame(target)
    y = frame[column].to_numpy(dtype=np.int64)
    hazards = frame["hazard"].to_numpy()
    X = np.zeros((len(y), 1), dtype=np.float64)

    candidate = MajorityClassBaseline()
    candidate.fit(X, y, hazards)
    metrics = classification_metrics(
        y, Predictions.from_proba(candidate.predict_proba(X, hazards))
    )

    assert metrics.worst_class_f1 < WORST_CLASS_F1_FLOOR
    assert metrics.accuracy > 0.5, "the point of the floor is that accuracy alone looks fine here"


def _synthetic_fit_data(seed=11, n_per_hazard=50):
    rng = np.random.default_rng(seed)
    hazards = np.array((["hte"] * n_per_hazard) + (["spc_fin"] * n_per_hazard))
    y = rng.integers(0, 3, size=len(hazards))
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal
    groups = np.array([f"g{i // 4}" for i in range(len(y))])
    return X, y, hazards, groups


def test_fitting_the_reference_twice_produces_identical_predictions():
    """§4.4 determinism, at the candidate level. `fit_binary_head` seeds its
    `LogisticRegression`, so a refit on identical inputs must be
    bit-identical -- not merely close.
    """
    X, y, hazards, _ = _synthetic_fit_data()

    first, second = TwoHeadReference(), TwoHeadReference()
    first.fit(X, y, hazards)
    second.fit(X, y, hazards)

    np.testing.assert_array_equal(
        first.predict_proba(X, hazards), second.predict_proba(X, hazards)
    )
    assert first.unavailable_hazards == second.unavailable_hazards


def test_the_whole_measurement_path_is_reproducible_end_to_end():
    """§4.4 determinism, at the harness level: fit -> predict -> metrics ->
    paired bootstrap, run twice, must agree exactly. This is the property
    that makes a recorded stage-1 result re-derivable rather than a one-off
    observation.
    """
    X, y, hazards, groups = _synthetic_fit_data()

    def run_once():
        reference = TwoHeadReference()
        reference.fit(X, y, hazards)
        majority = MajorityClassBaseline()
        majority.fit(X, y, hazards)

        pred_r = Predictions.from_proba(reference.predict_proba(X, hazards))
        pred_m = Predictions.from_proba(majority.predict_proba(X, hazards))
        metrics = classification_metrics(y, pred_r)
        difference = paired_cluster_bootstrap(
            y, pred_r, pred_m, groups, n_resamples=200, seed=99
        )
        return metrics, difference

    first_metrics, first_difference = run_once()
    second_metrics, second_difference = run_once()

    assert first_metrics == second_metrics
    assert first_difference == second_difference


def test_a_perfect_candidate_beats_the_majority_baseline_with_separation():
    """A known-answer sanity check on the selection rule's separation test:
    a perfect candidate must beat the degenerate one with an interval that
    excludes zero. If this cannot separate, nothing will.
    """
    X, y, hazards, groups = _synthetic_fit_data()

    perfect = Predictions(labels=y.copy(), scored=np.ones(len(y), dtype=bool))
    majority = MajorityClassBaseline()
    majority.fit(X, y, hazards)
    degenerate = Predictions.from_proba(majority.predict_proba(X, hazards))

    difference = paired_cluster_bootstrap(y, perfect, degenerate, groups, n_resamples=400)

    assert difference.point_estimate > 0
    assert difference.excludes_zero is True
    assert difference.ci_low > 0
