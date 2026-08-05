"""Tests for `hazard_classifier.experiments.comparison_metrics`
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` slice A §4.3).

The two load-bearing ones are `test_a_candidate_compared_against_itself_has_a_zero_width_interval`
(catches an unpaired bootstrap) and
`test_group_resampling_gives_a_wider_interval_than_row_resampling` (catches a
row-level bootstrap). Both are the traps §4.3 names explicitly, and both
inflate confidence silently if they are wrong.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import f1_score

from hazard_classifier.experiments.comparison_metrics import (
    N_CLASSES,
    Predictions,
    UnpairableComparisonError,
    classification_metrics,
    cluster_bootstrap_interval,
    cluster_resample_indices,
    confusion_matrix,
    group_row_indices,
    macro_f1_score,
    paired_cluster_bootstrap,
    per_class_f1,
    worst_class_f1_score,
)


def _scored(labels) -> Predictions:
    labels = np.asarray(labels, dtype=np.int64)
    return Predictions(labels=labels, scored=np.ones(len(labels), dtype=bool))


# --------------------------------------------------------------------------
# Metrics -- hand-computable cases (§4.4 bullet 1)
# --------------------------------------------------------------------------


def test_per_class_f1_on_a_hand_computed_confusion():
    # class 0: P=1/1, R=1/2  -> F1 = 2/3
    # class 1: P=1/2, R=1/1  -> F1 = 2/3
    # class 2: P=1/1, R=1/1  -> F1 = 1
    y_true = [0, 0, 1, 2]
    y_pred = [0, 1, 1, 2]

    f1 = per_class_f1(y_true, y_pred)

    np.testing.assert_allclose(f1, [2 / 3, 2 / 3, 1.0])
    assert macro_f1_score(y_true, y_pred) == pytest.approx(7 / 9)
    assert worst_class_f1_score(y_true, y_pred) == pytest.approx(2 / 3)


def test_perfect_prediction_scores_one_everywhere():
    y_true = [0, 0, 1, 1, 2, 2]
    assert macro_f1_score(y_true, y_true) == pytest.approx(1.0)
    assert worst_class_f1_score(y_true, y_true) == pytest.approx(1.0)


def test_a_degenerate_single_class_candidate_has_worst_class_f1_of_zero():
    """The §3 floor exists to reject a candidate that solves some classes by
    abandoning another. An abandoned class must score 0, not 'undefined'.
    """
    y_true = [0, 0, 0, 1, 1, 2]
    y_pred = [0, 0, 0, 0, 0, 0]

    f1 = per_class_f1(y_true, y_pred)

    np.testing.assert_allclose(f1, [2 / 3, 0.0, 0.0])
    assert worst_class_f1_score(y_true, y_pred) == 0.0
    assert macro_f1_score(y_true, y_pred) == pytest.approx(2 / 9)


def test_per_class_f1_matches_sklearn_on_random_data():
    """`confusion_matrix`/`per_class_f1` are hand-rolled via `bincount` to
    keep the bootstrap cheap. This pins that shortcut to sklearn's answer
    rather than assuming they agree.
    """
    rng = np.random.default_rng(20260804)
    for _ in range(25):
        n = int(rng.integers(5, 200))
        y_true = rng.integers(0, N_CLASSES, size=n)
        y_pred = rng.integers(0, N_CLASSES, size=n)

        expected = f1_score(
            y_true, y_pred, labels=[0, 1, 2], average=None, zero_division=0
        )
        np.testing.assert_allclose(per_class_f1(y_true, y_pred), expected)


def test_confusion_matrix_counts():
    counts = confusion_matrix([0, 0, 1, 2], [0, 1, 1, 2])
    assert counts.shape == (3, 3)
    assert counts[0, 0] == 1 and counts[0, 1] == 1
    assert counts[1, 1] == 1
    assert counts[2, 2] == 1
    assert counts.sum() == 4


def test_ground_truth_out_of_range_or_nan_raises():
    with pytest.raises(ValueError):
        per_class_f1([0, 1, 5], [0, 1, 2])
    with pytest.raises(ValueError):
        per_class_f1([0.0, 1.0, np.nan], [0, 1, 2])


# --------------------------------------------------------------------------
# Coverage / D-45 unavailability
# --------------------------------------------------------------------------


def test_predictions_from_proba_treats_an_all_nan_row_as_unscored():
    proba = np.array([[0.7, 0.2, 0.1], [np.nan, np.nan, np.nan], [0.0, 0.0, 1.0]])
    predictions = Predictions.from_proba(proba)

    np.testing.assert_array_equal(predictions.scored, [True, False, True])
    assert predictions.labels[0] == 0
    assert predictions.labels[2] == 2


def test_predictions_from_proba_rejects_a_partially_nan_row():
    proba = np.array([[0.5, np.nan, 0.5]])
    with pytest.raises(ValueError, match="partially NaN"):
        Predictions.from_proba(proba)


def test_predictions_from_proba_rejects_unnormalized_rows():
    with pytest.raises(ValueError, match="sum to 1"):
        Predictions.from_proba(np.array([[0.5, 0.2, 0.1]]))


def test_unscored_rows_are_excluded_not_counted_as_errors():
    """D-45: an unavailable cell is not a wrong answer. The metric is
    computed over scored rows, and coverage says so out loud.
    """
    y_true = [0, 1, 2, 0]
    predictions = Predictions(
        labels=np.array([0, 1, 2, 2], dtype=np.int64),
        scored=np.array([True, True, True, False]),
    )

    metrics = classification_metrics(y_true, predictions)

    assert metrics.n_scored == 3
    assert metrics.n_total == 4
    assert metrics.coverage == pytest.approx(0.75)
    # The three scored rows are perfect; the unscored one does not drag it down.
    assert metrics.macro_f1 == pytest.approx(1.0)


def test_a_candidate_that_scored_nothing_reports_zero_coverage():
    predictions = Predictions(
        labels=np.zeros(3, dtype=np.int64), scored=np.zeros(3, dtype=bool)
    )
    metrics = classification_metrics([0, 1, 2], predictions)
    assert metrics.n_scored == 0
    assert metrics.coverage == 0.0


# --------------------------------------------------------------------------
# Cluster resampling (§4.3's first trap)
# --------------------------------------------------------------------------


def test_group_row_indices_is_deterministic_and_covers_every_row():
    groups = np.array(["g2", "g1", "g2", "g3", "g1"])
    unique, rows = group_row_indices(groups)

    np.testing.assert_array_equal(unique, ["g1", "g2", "g3"])
    assert sorted(np.concatenate(rows).tolist()) == [0, 1, 2, 3, 4]


def test_cluster_resample_draws_whole_groups_never_individual_rows():
    """Structural proof of the cluster bootstrap: within one resample, every
    row of a given group appears the same number of times.
    """
    groups = np.array(["a", "a", "a", "b", "b", "c"])
    rng = np.random.default_rng(0)

    for _ in range(50):
        index = cluster_resample_indices(groups, rng)
        for group in ("a", "b", "c"):
            rows = np.flatnonzero(groups == group)
            counts = [int(np.sum(index == row)) for row in rows]
            assert len(set(counts)) == 1, f"group {group} was split across the resample: {counts}"


def test_group_resampling_gives_a_wider_interval_than_row_resampling():
    """Rows sharing a prompt group are correlated, so a row-level bootstrap
    understates the interval. Constructed so the correlation is total --
    every row within a group is identical -- which makes the contrast
    unambiguous rather than a matter of degree.
    """
    rng = np.random.default_rng(7)
    n_groups, rows_per_group = 24, 10
    groups, y_true, y_pred = [], [], []
    for g in range(n_groups):
        truth = g % N_CLASSES
        # Half the groups are predicted correctly, half are not.
        predicted = truth if g % 2 == 0 else (truth + 1) % N_CLASSES
        groups += [f"g{g}"] * rows_per_group
        y_true += [truth] * rows_per_group
        y_pred += [predicted] * rows_per_group

    groups = np.array(groups)
    y_true = np.array(y_true)
    predictions = _scored(y_pred)

    grouped = cluster_bootstrap_interval(
        y_true, predictions, groups, n_resamples=400, seed=1
    )
    group_width = grouped.ci_high - grouped.ci_low

    # A naive row-level bootstrap, implemented here in the test only -- it is
    # the mistake this module must not make, so it does not exist in the module.
    row_rng = np.random.default_rng(1)
    row_values = np.array(
        [
            macro_f1_score(y_true[idx], predictions.labels[idx])
            for idx in (
                row_rng.integers(0, len(y_true), size=len(y_true)) for _ in range(400)
            )
        ]
    )
    row_low, row_high = np.percentile(row_values, [2.5, 97.5])
    row_width = float(row_high - row_low)

    assert group_width > 1.5 * row_width, (
        f"group bootstrap width {group_width:.4f} should be materially wider than "
        f"the row bootstrap's {row_width:.4f}; a row-level resample understates it"
    )


# --------------------------------------------------------------------------
# Paired bootstrap (§4.3's second trap) -- §4.4 bullet 2
# --------------------------------------------------------------------------


def _ladder_fixture(seed=3, n_groups=30, rows_per_group=4):
    rng = np.random.default_rng(seed)
    groups, y_true = [], []
    for g in range(n_groups):
        groups += [f"g{g}"] * rows_per_group
        y_true += rng.integers(0, N_CLASSES, size=rows_per_group).tolist()
    return np.array(groups), np.array(y_true), rng


def test_a_candidate_compared_against_itself_has_a_zero_width_interval():
    """The single most valuable test here (§4.4). A correctly *paired*
    bootstrap differences a candidate against itself on the same resampled
    rows, so every resample's difference is exactly zero. An unpaired
    implementation -- drawing independent resamples for each side -- produces
    a non-degenerate interval here and is caught immediately.
    """
    groups, y_true, rng = _ladder_fixture()
    predictions = _scored(rng.integers(0, N_CLASSES, size=len(y_true)))

    difference = paired_cluster_bootstrap(
        y_true, predictions, predictions, groups, n_resamples=250
    )

    assert difference.point_estimate == 0.0
    assert difference.ci_low == 0.0
    assert difference.ci_high == 0.0
    assert difference.excludes_zero is False


def test_two_genuinely_different_candidates_get_a_non_degenerate_interval():
    """Companion to the self-comparison test above: without this, a bootstrap
    that always returned a zero-width interval would pass that test too.
    """
    groups, y_true, rng = _ladder_fixture()
    strong = _scored(y_true.copy())  # perfect
    weak = _scored(rng.integers(0, N_CLASSES, size=len(y_true)))  # noise

    difference = paired_cluster_bootstrap(y_true, strong, weak, groups, n_resamples=400)

    assert difference.ci_high > difference.ci_low
    assert difference.point_estimate > 0
    assert difference.excludes_zero is True


def test_paired_bootstrap_is_deterministic_under_a_fixed_seed():
    groups, y_true, rng = _ladder_fixture()
    a = _scored(rng.integers(0, N_CLASSES, size=len(y_true)))
    b = _scored(rng.integers(0, N_CLASSES, size=len(y_true)))

    first = paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=200, seed=42)
    second = paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=200, seed=42)
    other = paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=200, seed=43)

    assert first == second
    assert (other.ci_low, other.ci_high) != (first.ci_low, first.ci_high)


def test_paired_bootstrap_restricts_both_candidates_to_the_rows_they_share():
    groups, y_true, rng = _ladder_fixture()
    n = len(y_true)

    a_scored = np.ones(n, dtype=bool)
    b_scored = np.ones(n, dtype=bool)
    b_scored[: n // 3] = False  # b could not score the first third (D-45)

    a = Predictions(labels=y_true.copy(), scored=a_scored)
    b = Predictions(labels=y_true.copy(), scored=b_scored)

    difference = paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=100)

    assert difference.n_paired_rows == int(b_scored.sum())
    assert difference.n_paired_rows < n


def test_paired_bootstrap_raises_when_no_row_is_scored_by_both():
    groups, y_true, _ = _ladder_fixture()
    n = len(y_true)
    a = Predictions(labels=y_true.copy(), scored=np.array([True] * (n // 2) + [False] * (n - n // 2)))
    b = Predictions(labels=y_true.copy(), scored=~a.scored)

    with pytest.raises(UnpairableComparisonError):
        paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=10)


def test_paired_bootstrap_accepts_an_alternative_metric():
    groups, y_true, rng = _ladder_fixture()
    strong = _scored(y_true.copy())
    weak = _scored(np.zeros(len(y_true), dtype=np.int64))

    difference = paired_cluster_bootstrap(
        y_true, strong, weak, groups, metric=worst_class_f1_score, n_resamples=200
    )

    # Perfect candidate's worst class is 1.0; the all-zero candidate's is 0.0.
    assert difference.point_estimate == pytest.approx(1.0)
    assert difference.excludes_zero is True


def test_mismatched_lengths_raise():
    groups, y_true, _ = _ladder_fixture()
    short = _scored(y_true[:-1])
    with pytest.raises(ValueError):
        paired_cluster_bootstrap(y_true, short, short, groups, n_resamples=10)


def test_interval_dataclasses_are_json_ready():
    groups, y_true, rng = _ladder_fixture()
    a = _scored(y_true.copy())
    b = _scored(rng.integers(0, N_CLASSES, size=len(y_true)))

    paired = paired_cluster_bootstrap(y_true, a, b, groups, n_resamples=50).as_dict()
    marginal = cluster_bootstrap_interval(y_true, a, groups, n_resamples=50).as_dict()
    metrics = classification_metrics(y_true, a).as_dict()

    for payload in (paired, marginal, metrics):
        assert all(isinstance(v, (int, float, bool, list)) for v in payload.values())
