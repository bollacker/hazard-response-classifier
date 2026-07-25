"""Tests for `hazard_classifier.heads` (`VERIFICATION.md` IS-3).

Forcing functions for `DECISIONS.md` D-7: `mean`/`scale` are identical across
hazards within a component (independent of `sample_weight`) and computed over
whatever row set the caller passes in -- this module has no hazard identity
of its own, so the Legitimization enablement-only-hazard exclusion (D-7/D-18)
must be, and is, entirely the caller's job.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from hazard_classifier.heads import (
    BinaryHead,
    centered_probability,
    fit_binary_head,
    logit,
    sigmoid,
)

# Two well-separated clusters so LogisticRegression converges to a real,
# non-degenerate fit regardless of which rows are up-weighted.
_X = np.array(
    [
        [0.0, 0.0],
        [0.2, 0.1],
        [0.1, -0.1],
        [-0.1, 0.2],
        [5.0, 5.0],
        [5.2, 4.9],
        [4.8, 5.1],
        [5.1, 5.0],
    ]
)
_Y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
_WEIGHT_TARGET_LOW = np.array([1.0, 1.0, 1.0, 1.0, 0.25, 0.25, 0.25, 0.25])
_WEIGHT_TARGET_HIGH = np.array([0.25, 0.25, 0.25, 0.25, 1.0, 1.0, 1.0, 1.0])

# Three overlapping "hazard" groups whose labels don't align with hazard
# identity (realistic hazard-weighting shape, D-7/§3 step 4 hazard weighting
# -- unlike the perfectly-separable, class-aligned _X/_Y above, where a
# uniform per-class reweighting happens to select the same max-margin
# separator regardless of which class is up-weighted).
_rng = np.random.default_rng(20260725)
_GROUP_X = np.vstack(
    [
        _rng.normal(loc=center, scale=1.2, size=(6, 2))
        for center in [(0.0, 0.0), (1.5, 1.0), (-1.0, 1.5)]
    ]
)
_GROUP_Y = (_GROUP_X[:, 0] + _GROUP_X[:, 1] * 0.5 + _rng.normal(0, 0.8, size=18) > 0.5).astype(int)
_GROUP_HAZARD = np.array(["A"] * 6 + ["B"] * 6 + ["C"] * 6)


def _weight_for_target_hazard(target: str) -> np.ndarray:
    return np.where(_GROUP_HAZARD == target, 1.0, 0.25)


def test_logit_sigmoid_centering_math_matches_hand_computed_values() -> None:
    assert logit(0.5) == pytest.approx(0.0)
    assert sigmoid(0.0) == pytest.approx(0.5)
    assert centered_probability(0.5, 0.5) == pytest.approx(0.5)
    assert centered_probability(0.9, 0.5) > 0.5
    # 0/1 probabilities must not blow up to +/-inf (toy's 1e-6 clip).
    assert np.isfinite(logit(0.0))
    assert np.isfinite(logit(1.0))


def test_mean_scale_identical_across_hazard_weightings_coef_and_center_differ() -> None:
    """D-7: standardization stats don't depend on hazard weighting; the
    logistic fit and its centering do. Uses the overlapping three-group
    fixture, not the cleanly-separable `_X`/`_Y` pair -- a uniform per-class
    reweighting of perfectly-separable data can select the identical
    max-margin separator regardless of which class is up-weighted, which
    would make this assertion vacuously true rather than a real check.
    """
    head_a = fit_binary_head(_GROUP_X, _GROUP_Y, _weight_for_target_hazard("A"))
    head_b = fit_binary_head(_GROUP_X, _GROUP_Y, _weight_for_target_hazard("B"))

    assert np.array_equal(head_a.mean, head_b.mean)
    assert np.array_equal(head_a.scale, head_b.scale)

    assert not np.array_equal(head_a.coef, head_b.coef)
    assert head_a.center_mean != head_b.center_mean


def test_binary_head_fit_has_no_hazard_parameter() -> None:
    """Structural forcing function: this module cannot itself apply or skip
    a hazard-family exclusion (D-7/D-18) because it never receives a hazard
    identity at all -- the caller must pre-filter rows.
    """
    params = set(inspect.signature(fit_binary_head).parameters)
    assert params == {"x", "y", "sample_weight", "seed"}


def test_row_set_passed_in_determines_mean_scale_not_hazard_awareness() -> None:
    """Simulates the Legitimization enablement-only-hazard exclusion
    (D-7/D-18) at the caller level: fitting on the full row set vs. a subset
    with certain rows removed must change `mean`/`scale`, proving the
    exclusion has to happen before calling `fit_binary_head` -- there is no
    way to ask this function to ignore rows by label after the fact.
    """
    full_head = fit_binary_head(_X, _Y, np.ones(8))

    # Simulate excluding the last two "enablement-only-hazard" rows.
    x_excluded = _X[:6]
    y_excluded = _Y[:6]
    w_excluded = np.ones(6)
    excluded_head = fit_binary_head(x_excluded, y_excluded, w_excluded)

    assert not np.array_equal(full_head.mean, excluded_head.mean)
    assert not np.array_equal(full_head.scale, excluded_head.scale)


def test_degenerate_single_class_labels_produce_skipped_constant_head() -> None:
    """D-5: a single-class label vector is never fit with logistic
    regression -- it is a weighted-mean constant substitution, `status`
    'skipped'. `predict_proba` returns that constant for any input, and
    `predict_proba_centered` collapses to exactly 0.5 everywhere because the
    center mean *is* the constant (logit(p) - logit(p) == 0).
    """
    y_all_ones = np.ones(8, dtype=int)
    head = fit_binary_head(_X, y_all_ones, np.ones(8))

    assert head.status == "skipped"
    assert head.coef is None
    assert head.intercept is None
    assert head.constant_probability == pytest.approx(1.0)

    probe = np.array([[1.0, 2.0], [-3.0, 9.0]])
    assert np.array_equal(head.predict_proba(probe), np.array([1.0, 1.0]))
    assert np.allclose(head.predict_proba_centered(probe), [0.5, 0.5])


def test_save_load_round_trip_gives_bit_identical_predictions(tmp_path) -> None:
    head = fit_binary_head(_X, _Y, _WEIGHT_TARGET_LOW)
    probe = np.array([[0.05, 0.05], [4.9, 5.05], [2.5, 2.5]])
    before = head.predict_proba_centered(probe)

    archive_path = tmp_path / "head.npz"
    np.savez(archive_path, **head.to_arrays())
    loaded_arrays = dict(np.load(archive_path))
    reloaded = BinaryHead.from_arrays(loaded_arrays)

    after = reloaded.predict_proba_centered(probe)
    assert np.array_equal(before, after)
    assert reloaded.status == head.status
    assert reloaded.center_mean == head.center_mean


def test_save_load_round_trip_for_skipped_head(tmp_path) -> None:
    head = fit_binary_head(_X, np.zeros(8, dtype=int), np.ones(8))
    assert head.status == "skipped"

    archive_path = tmp_path / "skipped_head.npz"
    np.savez(archive_path, **head.to_arrays())
    reloaded = BinaryHead.from_arrays(dict(np.load(archive_path)))

    assert reloaded.status == "skipped"
    assert reloaded.coef is None
    assert reloaded.intercept is None
    assert reloaded.constant_probability == pytest.approx(0.0)
    probe = np.array([[1.0, 1.0]])
    assert np.array_equal(reloaded.predict_proba(probe), head.predict_proba(probe))
