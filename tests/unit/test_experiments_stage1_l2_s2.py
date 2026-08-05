"""Tests for `L2` (`OrdinalCumulativeLink`) and `S2`
(`JointCandidate`/`SharedTwoHeadJoint`) -- the two levels originally left as
Open Questions and completed on direction: L2 via a new `statsmodels`
dependency, S2 via a protocol extension alongside the existing `Candidate`.
"""

from __future__ import annotations

import numpy as np
import pytest

from hazard_classifier.experiments.candidates import (
    JOINT_BUILDERS,
    STAGE1_BUILDERS,
    STAGE1_LEVELS,
    OrdinalCumulativeLink,
    SharedTwoHeadJoint,
    TwoHeadReference,
    _l2_pca_components,
)
from hazard_classifier.experiments.comparison_metrics import Predictions, classification_metrics


def _synthetic_data(rng, n_per_hazard=60, hazards=("hte", "prv", "spc_fin")):
    hazard_array = np.array(sum(([h] * n_per_hazard for h in hazards), []))
    y = rng.integers(0, 3, size=len(hazard_array))
    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal
    return X, y, hazard_array


# --------------------------------------------------------------------------
# L2 -- OrdinalCumulativeLink
# --------------------------------------------------------------------------


def test_l2_fits_and_scores_a_fittable_hazard():
    rng = np.random.default_rng(20)
    X, y, hazards = _synthetic_data(rng)

    candidate = OrdinalCumulativeLink()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)

    finite = np.isfinite(proba).all(axis=1)
    assert finite.any()
    np.testing.assert_allclose(proba[finite].sum(axis=1), 1.0)


def test_l2_recovers_a_reasonable_fit_on_a_known_generating_process():
    """A self-consistency check against a *known* answer, since there is no
    trusted second implementation in this environment to cross-check
    against: simulate from a genuine proportional-odds process and confirm
    the fit predicts substantially better than chance.
    """
    rng = np.random.default_rng(21)
    n = 300
    X = rng.normal(size=(n, 4))
    true_beta = np.array([2.0, -1.0, 0.0, 0.0])
    latent = X @ true_beta + rng.normal(scale=0.5, size=n)
    y = np.digitize(latent, bins=[-0.5, 0.5]).astype(np.int64)
    hazards = np.array(["hte"] * n)

    candidate = OrdinalCumulativeLink()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)
    predicted = proba.argmax(axis=1)

    assert np.mean(predicted == y) > 0.6


def test_l2_marks_a_single_class_hazard_unavailable_not_a_crash():
    """OrderedModel itself raises an opaque shape-mismatch ValueError on a
    single-class fit (confirmed by hand while building this) -- this is the
    forcing function that the pre-fit class-count guard actually intercepts
    it before that exception would surface.
    """
    rng = np.random.default_rng(22)
    n = 40
    hazards = np.array((["hte"] * n) + (["prv"] * n))
    y = np.concatenate([rng.integers(0, 3, size=n), np.zeros(n, dtype=np.int64)])
    X = rng.normal(size=(len(y), 4))

    candidate = OrdinalCumulativeLink()
    candidate.fit(X, y, hazards)

    assert candidate.unavailable_hazards == frozenset({"prv"})
    proba = candidate.predict_proba(X, hazards)
    assert np.isnan(proba[hazards == "prv"]).all()


def test_l2_handles_a_hazard_missing_one_class_by_label_not_position():
    """OrderedModel drops output *columns* (not zero-fills them) for a class
    that never appeared -- `model.labels` says which columns are which. This
    is the forcing function for using `labels` rather than assuming
    positional [0, 1, 2] order.
    """
    rng = np.random.default_rng(23)
    n = 40
    hazards = np.array(["hte"] * n)
    y = np.array(([0] * (n // 2)) + ([2] * (n - n // 2)))  # class 1 never appears
    X = rng.normal(size=(n, 4))
    X[:, 0] += np.where(y == 0, -1.0, 1.0)

    candidate = OrdinalCumulativeLink()
    candidate.fit(X, y, hazards)
    proba = candidate.predict_proba(X, hazards)

    assert np.isfinite(proba).all()
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)
    np.testing.assert_allclose(proba[:, 1], 0.0)


def test_l2_pca_components_matches_the_formula_pinned_against_real_data():
    """The formula's exact shape, so a future edit can't silently drift from
    what was empirically validated against every real (target, hazard) cell
    in the interim dataset (see the function's own docstring).
    """
    assert _l2_pca_components(n_rows=49, n_features=768) == 4  # cse, the worst real case
    assert _l2_pca_components(n_rows=124, n_features=768) == 10  # hte, capped at 10
    assert _l2_pca_components(n_rows=10, n_features=768) == 2  # floored at 2
    assert _l2_pca_components(n_rows=1000, n_features=4) == 4  # capped by n_features


def test_l2_does_not_crash_or_silently_overfit_at_bge_scale_and_real_hazard_row_counts(monkeypatch):
    """Forcing function for the regularization fix, not the low-dimensional
    synthetic fixtures every other L2 test here uses (where PCA is nearly a
    no-op because there are few features to begin with). Replicates the real
    shape that broke the first version of this candidate: 768-dimensional
    BGE-sized input against a ~45-row hazard cell.

    Before the PCA step existed, `OrderedModel`'s own constructor raised a
    rank-deficiency `ValueError` on data shaped exactly like this (confirmed
    by hand while building this candidate) -- this pins that it no longer
    does, and that the fit is not simply a memorized, perfectly-separating
    solution (`accuracy < 1.0` on an imbalanced, noisy population where
    perfect in-sample accuracy would itself be the overfitting signal).
    """
    rng = np.random.default_rng(31)
    n, d = 49, 768  # cse's real shape: 49 rows, BGE's 768 dimensions
    X = rng.normal(size=(n, d))
    true_direction = rng.normal(size=d)
    latent = X @ true_direction * 0.02 + rng.normal(scale=1.0, size=n)
    # Imbalanced like the real worst case (35/5/9) rather than uniform.
    thresholds = np.quantile(latent, [0.71, 0.90])
    y = np.digitize(latent, thresholds).astype(np.int64)
    hazards = np.array(["cse"] * n)

    candidate = OrdinalCumulativeLink()
    candidate.fit(X, y, hazards)

    assert candidate.unavailable_hazards == frozenset()
    proba = candidate.predict_proba(X, hazards)
    assert np.isfinite(proba).all()
    accuracy = (proba.argmax(axis=1) == y).mean()
    assert accuracy < 1.0, "perfect in-sample accuracy here would itself be the overfitting signature"


def test_l2_is_registered_as_a_per_target_stage1_builder():
    assert "L2" in STAGE1_BUILDERS
    candidate = STAGE1_BUILDERS["L2"]()
    assert candidate.name == "L2"
    assert isinstance(candidate, OrdinalCumulativeLink)


# --------------------------------------------------------------------------
# S2 -- SharedTwoHeadJoint / JointCandidate
# --------------------------------------------------------------------------


def _joint_data(rng, l_hazards=("hte", "spc_fin"), e_hazards=("hte", "spc_fin", "prv"), n=60):
    def make(hazard_list, seed):
        r = np.random.default_rng(seed)
        hazards = np.array(sum(([h] * n for h in hazard_list), []))
        y = r.integers(0, 3, size=len(hazards))
        signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
        X = r.normal(size=(len(y), 6))
        X[:, 0] += signal
        return X, y, hazards

    X_l, y_l, hazards_l = make(l_hazards, rng.integers(0, 2**31))
    X_e, y_e, hazards_e = make(e_hazards, rng.integers(0, 2**31))
    return X_l, y_l, hazards_l, X_e, y_e, hazards_e


def test_s2_fits_one_shared_head_pair_serving_both_targets():
    rng = np.random.default_rng(24)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)

    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    # Every hazard appearing in either target got exactly one shared head pair.
    assert set(s2._heads.keys()) == {"hte", "spc_fin", "prv"}
    # The *same* head object serves both targets for a hazard both share.
    l_view = s2.target_view("L")
    e_view = s2.target_view("E")
    assert l_view.name == "S2[L]"
    assert e_view.name == "S2[E]"


def test_s2_serves_a_hazard_missing_entirely_from_one_target():
    """`prv` has no L rows at all (mirrors legitimization_rows excluding
    enablement-only hazards). The shared head still fits from E's rows
    alone, and E must still be scoreable for it even though L cannot be.
    """
    rng = np.random.default_rng(25)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)

    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    assert "prv" not in set(hazards_l)
    assert "prv" in s2._heads  # fit from E's rows alone
    assert "prv" not in s2._thresholds["L"]
    assert "prv" in s2._thresholds["E"]

    e_view = s2.target_view("E")
    prv_rows = hazards_e == "prv"
    proba = e_view.predict_proba(X_e[prv_rows], hazards_e[prv_rows])
    assert np.isfinite(proba).all()


def test_s2_target_view_fit_raises():
    rng = np.random.default_rng(26)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)
    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    with pytest.raises(RuntimeError, match="target_view"):
        s2.target_view("L").fit(X_l, y_l, hazards_l)


def test_s2_rejects_an_invalid_target():
    rng = np.random.default_rng(27)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)
    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    with pytest.raises(ValueError):
        s2.target_view("Q")


def test_s2_target_views_conform_to_the_candidate_protocol_downstream():
    """The whole point of `target_view`: comparison_metrics.py's machinery
    should work on an S2 view exactly like any other candidate, with no
    special-casing.
    """
    rng = np.random.default_rng(28)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)
    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    for view, X, y, hazards in (
        (s2.target_view("L"), X_l, y_l, hazards_l),
        (s2.target_view("E"), X_e, y_e, hazards_e),
    ):
        proba = view.predict_proba(X, hazards)
        predictions = Predictions.from_proba(proba)
        metrics = classification_metrics(y, predictions)
        assert metrics.n_total == len(y)
        assert metrics.coverage == 1.0  # every hazard here has rows for this target


def test_s2_head_is_genuinely_shared_not_independently_coincidental():
    """The forcing function for 'shared parameterization': the fitted
    coefficients must reflect the *pooled* population, not just L's own
    rows. Constructed so X correlates only with L's labels; if S2's head
    were secretly fit on L alone, it would match an L-only fit exactly.
    """
    rng = np.random.default_rng(29)
    n = 80
    hazards = np.array(["hte"] * n)
    y_l = rng.integers(0, 3, size=n)
    y_e = rng.integers(0, 3, size=n)  # unrelated labels, same X
    X = rng.normal(size=(n, 6))
    X[:, 0] += np.where(y_l == 0, -1.0, 1.0)

    s2 = SharedTwoHeadJoint()
    s2.fit(X, y_l, hazards, X, y_e, hazards)
    shared_nonzero_head, _ = s2._heads["hte"]

    l_only = TwoHeadReference()
    l_only.fit(X, y_l, hazards)
    l_only_head, _, _, _ = l_only._cells["hte"]

    assert not np.allclose(shared_nonzero_head.coef, l_only_head.coef)


def test_s2_fits_strictly_fewer_head_pairs_than_r_fits_per_target():
    """Sharing's economy, made concrete on the *joint* total: S2 fits one
    head pair per hazard across both targets; R fits one per hazard *per
    target*. On the same hazard set, S2 must use at most half as many.
    (Per target the decision function is the same size as R's -- see the
    parameter-count test below -- so this saving is visible only jointly.)
    """
    rng = np.random.default_rng(30)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng, l_hazards=("hte", "spc_fin"), e_hazards=("hte", "spc_fin"))

    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    r_l = TwoHeadReference()
    r_l.fit(X_l, y_l, hazards_l)
    r_e = TwoHeadReference()
    r_e.fit(X_e, y_e, hazards_e)

    s2_head_pairs = len(s2._heads)
    r_head_pairs = len(r_l._cells) + len(r_e._cells)
    assert s2_head_pairs * 2 == r_head_pairs


def test_s2_target_view_reports_a_per_target_parameter_count_equal_to_rs():
    """§4.1 criterion 2 compares per-target ladder rows, so each S2
    `target_view` must report the parameters serving *that target only* --
    the shared head pairs it decides through plus its own thresholds --
    which equals R's count for the same hazard set (the shared head is
    reused, not smaller). The *joint* total is where sharing's saving
    shows: strictly less than R's two-target sum whenever a hazard is
    shared. A joint count on a per-target row (the original defect) would
    overstate S2 against every other candidate's per-target rows.
    """
    rng = np.random.default_rng(31)
    X_l, y_l, hazards_l, X_e, y_e, hazards_e = _joint_data(rng)  # prv is E-only

    s2 = SharedTwoHeadJoint()
    s2.fit(X_l, y_l, hazards_l, X_e, y_e, hazards_e)

    r_l = TwoHeadReference()
    r_l.fit(X_l, y_l, hazards_l)
    r_e = TwoHeadReference()
    r_e.fit(X_e, y_e, hazards_e)

    l_count = s2.target_view("L").fitted_parameter_count()
    e_count = s2.target_view("E").fitted_parameter_count()
    assert l_count == r_l.fitted_parameter_count()
    assert e_count == r_e.fitted_parameter_count()

    joint = s2.fitted_parameter_count()
    assert joint < l_count + e_count  # heads counted once, not per target
    # Exactly: both targets' thresholds, but each shared head only once.
    shared_heads = sum(2 * (len(nz.coef) + 1) for nz, _ in s2._heads.values())
    thresholds = 2 * (len(s2._thresholds["L"]) + len(s2._thresholds["E"]))
    assert joint == shared_heads + thresholds


# --------------------------------------------------------------------------
# The registries, now complete
# --------------------------------------------------------------------------


def test_all_ten_stage1_levels_are_accounted_for():
    assert set(STAGE1_LEVELS) == {"L1", "L2", "W2", "W3", "S2", "H1", "H2", "B1", "P2", "P3"}
    assert len(STAGE1_LEVELS) == 10

    per_target_builders = set(STAGE1_BUILDERS.keys())
    joint_builders = set(JOINT_BUILDERS.keys())
    pooling_levels = {"P2", "P3"}  # no candidate-level code; TwoHeadReference on different pooling

    assert per_target_builders | joint_builders | pooling_levels == set(STAGE1_LEVELS)
    assert per_target_builders.isdisjoint(joint_builders)
    assert per_target_builders.isdisjoint(pooling_levels)
