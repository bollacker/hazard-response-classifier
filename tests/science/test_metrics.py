"""Science-level tests for Deliverable 2's metric computation (`PLAN.md`
§5): D-13 holdout partitioning, D-15 legitimization's enablement-only-hazard
exclusion, D-16 high-head-only AUC, and D-17's positive-class convention /
confusion shape / false-safe-false-unsafe rate definition.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support, roc_auc_score

from hazard_classifier.metrics import (
    component_metrics,
    final_label_metrics,
    legitimization_eligible_mask,
    partition_by_holdout,
)

# Frozen enablement-only and specialized-advice sets for these tests --
# deliberately local fixtures, not imported from hazard_classifier.config, so
# these tests don't implicitly assume production reads config either
# (DECISIONS.md D-23: the frozen sets must come from the artifact, never
# installed config).
_ENABLEMENT_ONLY = frozenset({"prv", "sxc_prn"})
_SPECIALIZED_ADVICE = frozenset({"spc_ele", "spc_fin", "spc_hlt", "spc_lgl"})


def test_partition_by_holdout_splits_by_seed_membership():
    seed_prompt_ids = ["s1", "s2", "s3", "s4"]
    held_out_mask, in_sample_mask = partition_by_holdout(seed_prompt_ids, {"s2", "s4"})
    assert held_out_mask.tolist() == [False, True, False, True]
    assert in_sample_mask.tolist() == [True, False, True, False]
    assert np.all(held_out_mask != in_sample_mask)


def test_partition_by_holdout_empty_holdout_puts_everything_in_sample():
    held_out_mask, in_sample_mask = partition_by_holdout(["s1", "s2"], set())
    assert not held_out_mask.any()
    assert in_sample_mask.all()


def test_legitimization_eligible_mask_excludes_enablement_only_hazards():
    hazard = ["hte", "prv", "sxc_prn", "spc_lgl"]
    mask = legitimization_eligible_mask(hazard, _ENABLEMENT_ONLY)
    assert mask.tolist() == [True, False, False, True]


def test_legitimization_eligible_mask_uses_the_passed_set_not_installed_config():
    # DECISIONS.md D-23: every required-components lookup must read the
    # artifact's frozen set, never installed hazard_classifier.config. Prove
    # it by passing a frozen set that disagrees with installed config's
    # ENABLEMENT_ONLY_HAZARDS in both directions and confirming the passed
    # set's answer wins, not config's.
    from hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS

    frozen = frozenset({"hte"})  # this artifact trained "hte" as enablement-only
    assert "hte" not in ENABLEMENT_ONLY_HAZARDS  # sanity: config disagrees
    assert "prv" in ENABLEMENT_ONLY_HAZARDS  # sanity: config still has prv

    mask = legitimization_eligible_mask(["hte", "prv"], frozen)
    assert mask.tolist() == [False, True]


def test_component_metrics_perfect_prediction():
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_pred = y_true.copy()
    high_prob = np.array([0.1, 0.2, 0.9, 0.1, 0.2, 0.9])

    result = component_metrics(y_true, y_pred, high_prob)

    assert result["exact_accuracy"] == 1.0
    assert result["within_one_accuracy"] == 1.0
    assert result["binary_present_accuracy"] == 1.0
    assert result["mae"] == 0.0
    assert result["qwk"] == pytest.approx(1.0)
    assert result["auc"] == pytest.approx(1.0)
    assert result["confusion_counts"]["actual_2"]["predicted_2"] == 2
    assert result["confusion_counts"]["actual_0"]["predicted_1"] == 0


def test_component_metrics_auc_uses_high_head_not_nonzero_head():
    y_true = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
    y_pred = y_true.copy()
    # A nonzero-head-shaped score: separates y=0 from y>0 cleanly, but is
    # tied between y=1 and y=2 -- a poor discriminator for the "y==2" label
    # component_metrics's AUC is actually supposed to measure.
    nonzero_like_score = np.array([0.1, 0.1, 0.1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
    # The high-head score: cleanly separates y==2 from everything else.
    high_prob = np.array([0.1, 0.1, 0.1, 0.2, 0.2, 0.2, 0.9, 0.9, 0.9])

    result = component_metrics(y_true, y_pred, high_prob)
    wrong_auc = roc_auc_score((y_true == 2).astype(int), nonzero_like_score)

    assert result["auc"] == pytest.approx(1.0)
    assert result["auc"] != pytest.approx(wrong_auc)
    assert wrong_auc == pytest.approx(0.75)


def test_component_metrics_auc_is_none_for_single_class():
    y_true = np.zeros(5, dtype=np.int8)
    y_pred = np.zeros(5, dtype=np.int8)
    high_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

    result = component_metrics(y_true, y_pred, high_prob)
    assert result["auc"] is None


def test_component_metrics_qwk_is_none_for_single_class():
    """DECISIONS.md D-33: the same single-class fixture that makes `auc`
    undefined also makes `cohen_kappa_score` return `NaN` (confirmed
    directly, not assumed) -- `qwk` must report `None`, not a bare `NaN`
    that `json.dump` would emit as an invalid-strict-JSON token.
    """
    y_true = np.zeros(5, dtype=np.int8)
    y_pred = np.zeros(5, dtype=np.int8)
    high_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

    result = component_metrics(y_true, y_pred, high_prob)
    assert result["qwk"] is None


def test_component_metrics_qwk_matches_sklearn():
    y_true = np.array([0, 1, 2, 1, 0, 2, 1, 0])
    y_pred = np.array([0, 1, 1, 1, 0, 2, 0, 1])
    high_prob = np.linspace(0.1, 0.9, len(y_true))

    result = component_metrics(y_true, y_pred, high_prob)
    expected_qwk = cohen_kappa_score(y_true, y_pred, weights="quadratic")
    assert result["qwk"] == pytest.approx(expected_qwk)


def test_final_label_metrics_excludes_specialized_advice_from_headline():
    hazard = ["hte", "hte", "spc_fin", "spc_fin", "prv", "prv"]
    is_safe_true = np.array([True, False, True, False, True, False])
    predicted_safe = np.array([True, True, False, False, True, False])

    result = final_label_metrics(is_safe_true, predicted_safe, hazard, _SPECIALIZED_ADVICE)

    # Only the 4 non-specialized-advice rows (hte x2, prv x2) count.
    assert result["n"] == 4
    counts = result["confusion_counts"]
    assert counts["predicted_safe_actual_safe"] == 2
    assert counts["predicted_safe_actual_unsafe"] == 1
    assert counts["predicted_unsafe_actual_safe"] == 0
    assert counts["predicted_unsafe_actual_unsafe"] == 1
    assert result["false_safe_rate"] == pytest.approx(1 / 4)
    assert result["false_unsafe_rate"] == pytest.approx(0 / 4)


def test_final_label_metrics_matches_sklearn_precision_recall_f1():
    hazard = ["hte", "hte", "spc_fin", "spc_fin", "prv", "prv"]
    is_safe_true = np.array([True, False, True, False, True, False])
    predicted_safe = np.array([True, True, False, False, True, False])
    headline = [h != "spc_fin" for h in hazard]

    result = final_label_metrics(is_safe_true, predicted_safe, hazard, _SPECIALIZED_ADVICE)
    expected_precision, expected_recall, expected_f1, _ = precision_recall_fscore_support(
        is_safe_true[headline].astype(np.int8),
        predicted_safe[headline].astype(np.int8),
        labels=[1],
        average=None,
        zero_division=0,
    )

    assert result["precision"] == pytest.approx(float(expected_precision[0]))
    assert result["recall"] == pytest.approx(float(expected_recall[0]))
    assert result["f1"] == pytest.approx(float(expected_f1[0]))


def test_final_label_metrics_empty_headline_population_returns_none_not_crash():
    hazard = ["spc_fin", "spc_lgl", "spc_hlt"]
    is_safe_true = np.array([True, False, True])
    predicted_safe = np.array([True, True, False])

    result = final_label_metrics(is_safe_true, predicted_safe, hazard, _SPECIALIZED_ADVICE)

    assert result["n"] == 0
    assert result["precision"] is None
    assert result["false_safe_rate"] is None


def test_final_label_metrics_uses_the_passed_set_not_installed_config():
    # DECISIONS.md D-23: every rule-family lookup must read the artifact's
    # frozen set, never installed hazard_classifier.config. Prove it by
    # passing a frozen specialized-advice set that disagrees with installed
    # config in both directions and confirming the passed set's answer wins.
    from hazard_classifier.config import SPECIALIZED_ADVICE_HAZARDS

    frozen = frozenset({"hte"})  # this artifact trained "hte" as specialized-advice
    assert "hte" not in SPECIALIZED_ADVICE_HAZARDS  # sanity: config disagrees
    assert "spc_fin" in SPECIALIZED_ADVICE_HAZARDS  # sanity: config still has spc_fin

    hazard = ["hte", "spc_fin"]
    is_safe_true = np.array([True, True])
    predicted_safe = np.array([True, True])

    result = final_label_metrics(is_safe_true, predicted_safe, hazard, frozen)

    # "hte" is excluded (frozen says specialized-advice), "spc_fin" is kept
    # (frozen doesn't say specialized-advice) -- the opposite of what config
    # alone would produce.
    assert result["n"] == 1


def test_component_metrics_n_reflects_the_passed_row_count():
    # DECISIONS.md D-17's DI-Q4 amendment: components.enablement.n equals the
    # population's full n_rows (Enablement is required for every hazard, D-18
    # -- nothing is excluded from it), while components.legitimization.n is
    # n_rows minus the enablement-only-hazard row count, since those rows are
    # never passed to component_metrics for Legitimization in the first place
    # (legitimization_eligible_mask filters them out upstream, D-15/D-18).
    # component_metrics itself carries no hazard-family knowledge -- it just
    # reports how many rows it was actually given, so this behavior falls out
    # of the caller's existing pre-filtering rather than new logic here.
    hazard = ["hte", "prv", "sxc_prn", "spc_lgl", "hte"]
    y_true = np.array([1, 0, 0, 2, 1])
    y_pred = np.array([1, 0, 0, 2, 1])
    high_prob = np.array([0.1, 0.9, 0.9, 0.9, 0.1])
    n_rows = len(hazard)

    enablement_result = component_metrics(y_true, y_pred, high_prob)

    mask = legitimization_eligible_mask(hazard, _ENABLEMENT_ONLY)
    enablement_only_count = int(np.sum(~mask))
    legit_result = component_metrics(y_true[mask], y_pred[mask], high_prob[mask])

    assert enablement_result["n"] == n_rows
    assert enablement_only_count == 2  # prv, sxc_prn
    assert legit_result["n"] == n_rows - enablement_only_count
    assert legit_result["n"] < enablement_result["n"]


def test_d15_enablement_only_hazards_excluded_from_legitimization_but_not_final_label():
    hazard = ["hte", "prv", "sxc_prn", "spc_lgl"]
    y_true = np.array([1, 0, 0, 2])
    y_pred = np.array([1, 0, 0, 2])
    high_prob = np.array([0.1, 0.9, 0.9, 0.9])
    is_safe_true = np.array([True, True, False, False])
    predicted_safe = np.array([True, True, False, True])

    # D-15: legitimization's component metrics must not see the prv/sxc_prn
    # rows at all -- only "hte" and "spc_lgl" (indices 0 and 3) remain.
    mask = legitimization_eligible_mask(hazard, _ENABLEMENT_ONLY)
    legit_result = component_metrics(y_true[mask], y_pred[mask], high_prob[mask])
    assert sum(legit_result["confusion_counts"][f"actual_{a}"][f"predicted_{p}"]
               for a in range(3) for p in range(3)) == 2

    # The final-label headline is unaffected by D-15: it excludes only
    # specialized-advice hazards (spc_lgl here), so prv/sxc_prn stay in.
    label_result = final_label_metrics(is_safe_true, predicted_safe, hazard, _SPECIALIZED_ADVICE)
    assert label_result["n"] == 3
