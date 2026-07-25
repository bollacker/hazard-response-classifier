"""Tests for `hazard_classifier.model.evaluate_rows` (`VERIFICATION.md` IS-8).

Builds on the same synthetic-fixture pattern as the other `model.py` test
files -- no BGE/embed.py dependency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.model import (
    BlankGroundTruthError,
    evaluate_rows,
    fit,
)

_ENABLEMENT_ONLY = frozenset({"prv"})
_N_TRAIN = 20


def _fit_classifier(holdout_seed_fraction: float = 0.0):
    rng = np.random.default_rng(11)
    hazards = np.array(["hte"] * 10 + ["prv"] * 10)
    df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i}" for i in range(_N_TRAIN)],
            "hazard": hazards,
            "enablement_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] * 2,
            "legitimization_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] + [""] * 10,
        }
    )
    enablement_features = rng.normal(size=(_N_TRAIN, 3))
    enablement_features[:, 0] += df["enablement_value"].astype(int).to_numpy() * 2.0
    legitimization_features = rng.normal(size=(_N_TRAIN, 3))
    legit_labels = np.where(df["hazard"] == "prv", 0, df["legitimization_value"].replace("", "0").astype(int))
    legitimization_features[:, 0] += legit_labels * 2.0
    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": np.ones(_N_TRAIN, dtype=bool), "legitimization": np.ones(_N_TRAIN, dtype=bool)}
    return fit(
        df, features, effective, _ENABLEMENT_ONLY, holdout_seed_fraction=holdout_seed_fraction, seed=11
    )


def _eval_frame(rows: list[dict]) -> tuple[pd.DataFrame, dict, dict, np.ndarray]:
    df = pd.DataFrame(rows)
    n = len(df)
    rng = np.random.default_rng(22)
    enablement_features = rng.normal(size=(n, 3))
    legitimization_features = rng.normal(size=(n, 3))
    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": np.ones(n, dtype=bool), "legitimization": np.ones(n, dtype=bool)}
    disclaimer_sentence_count = np.zeros(n, dtype=int)
    return df, features, effective, disclaimer_sentence_count


def _valid_rows(n: int, hazard: str = "hte") -> list[dict]:
    return [
        {
            "seed_prompt_id": f"esp{i}",
            "hazard": hazard,
            "enablement_value": str(i % 3),
            "legitimization_value": "" if hazard == "prv" else str(i % 3),
            "is_safe_ground_truth": "safe" if i % 2 == 0 else "unsafe",
        }
        for i in range(n)
    ]


def test_excluded_row_never_enters_either_population() -> None:
    classifier = _fit_classifier()
    rows = _valid_rows(4) + [
        {
            "seed_prompt_id": "esp_unseen",
            "hazard": "totally_unseen",
            "enablement_value": "1",
            "legitimization_value": "1",
            "is_safe_ground_truth": "safe",
        }
    ]
    df, features, effective, disclaimer = _eval_frame(rows)

    report = evaluate_rows(df, features, effective, disclaimer, classifier)

    assert report["excluded_unseen_hazard_count"] == 1
    assert report["excluded_skipped_cell_count"] == 0
    assert report["excluded_row_count"] == 1
    # No holdout recorded (default fraction 0) -> everything survives into
    # in_sample_unrecorded except the excluded row.
    assert report["in_sample_unrecorded"]["n_rows"] == 4
    assert "held_out" not in report


def test_empty_holdout_warns_and_puts_everything_in_sample_unrecorded() -> None:
    classifier = _fit_classifier(holdout_seed_fraction=0.0)
    assert classifier.holdout_seed_prompt_ids == []
    rows = _valid_rows(5)
    df, features, effective, disclaimer = _eval_frame(rows)

    with pytest.warns(UserWarning, match="no recorded held-out split"):
        report = evaluate_rows(df, features, effective, disclaimer, classifier)

    assert report["holdout_recorded"] is False
    assert "held_out" not in report
    assert report["in_sample_unrecorded"]["n_rows"] == 5


def test_blank_label_on_unseen_hazard_is_excluded_not_abort() -> None:
    """Finding A (D-26's 2026-07-25 amendment): a blank label never reaches
    validation for a row D-14 already excluded -- this must not raise
    `BlankGroundTruthError`.
    """
    classifier = _fit_classifier()
    rows = _valid_rows(3) + [
        {
            "seed_prompt_id": "esp_unseen_blank",
            "hazard": "totally_unseen",
            "enablement_value": "",
            "legitimization_value": "",
            "is_safe_ground_truth": "",
        }
    ]
    df, features, effective, disclaimer = _eval_frame(rows)

    report = evaluate_rows(df, features, effective, disclaimer, classifier)

    assert report["excluded_unseen_hazard_count"] == 1
    assert report["in_sample_unrecorded"]["n_rows"] == 3


def test_blank_label_on_known_non_enablement_only_hazard_aborts() -> None:
    classifier = _fit_classifier()
    rows = _valid_rows(2) + [
        {
            "seed_prompt_id": "esp_blank_legit",
            "hazard": "hte",  # known, non-enablement-only -> legit required
            "enablement_value": "1",
            "legitimization_value": "",  # blank -- a data defect here
            "is_safe_ground_truth": "safe",
        }
    ]
    df, features, effective, disclaimer = _eval_frame(rows)

    with pytest.raises(BlankGroundTruthError):
        evaluate_rows(df, features, effective, disclaimer, classifier)


def test_blank_legitimization_tolerated_for_enablement_only_hazard() -> None:
    classifier = _fit_classifier()
    rows = _valid_rows(2, hazard="prv")  # blank legitimization_value, D-15/D-18
    df, features, effective, disclaimer = _eval_frame(rows)

    report = evaluate_rows(df, features, effective, disclaimer, classifier)

    assert report["excluded_row_count"] == 0
    assert report["in_sample_unrecorded"]["n_rows"] == 2
    # No legitimization-eligible rows in this population at all.
    assert report["in_sample_unrecorded"]["components"]["legitimization"]["n"] == 0


def test_metrics_json_shape() -> None:
    classifier = _fit_classifier()
    rows = _valid_rows(6)
    df, features, effective, disclaimer = _eval_frame(rows)

    report = evaluate_rows(df, features, effective, disclaimer, classifier)

    assert set(report.keys()) >= {
        "holdout_recorded",
        "excluded_row_count",
        "excluded_unseen_hazard_count",
        "excluded_skipped_cell_count",
        "in_sample_unrecorded",
    }
    population = report["in_sample_unrecorded"]
    assert set(population.keys()) == {"n_rows", "components", "final_label"}
    for component_name in ("enablement", "legitimization"):
        component = population["components"][component_name]
        assert set(component.keys()) == {
            "n",
            "exact_accuracy",
            "within_one_accuracy",
            "binary_present_accuracy",
            "auc",
            "qwk",
            "mae",
            "confusion_counts",
        }
    final_label = population["final_label"]
    assert set(final_label.keys()) == {
        "n",
        "precision",
        "recall",
        "f1",
        "false_safe_rate",
        "false_unsafe_rate",
        "confusion_counts",
    }
