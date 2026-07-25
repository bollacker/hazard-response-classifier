"""Tests for `hazard_classifier.model.predict_rows` (`VERIFICATION.md` IS-10).

Reuses the same synthetic-fixture pattern as `test_model_evaluate.py` -- no
BGE/embed.py dependency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.model import (
    FAILURES_COLUMNS,
    PREDICTIONS_COLUMNS,
    fit,
    predict_rows,
    to_failures_frame,
    to_predictions_frame,
)

_ENABLEMENT_ONLY = frozenset({"prv"})
_N_TRAIN = 20


def _fit_classifier():
    rng = np.random.default_rng(33)
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
    return fit(df, features, effective, _ENABLEMENT_ONLY, seed=33)


def _predict_frame(rows: list[dict]):
    df = pd.DataFrame(rows)
    n = len(df)
    rng = np.random.default_rng(44)
    features = {
        "enablement": rng.normal(size=(n, 3)),
        "legitimization": rng.normal(size=(n, 3)),
    }
    effective = {"enablement": np.ones(n, dtype=bool), "legitimization": np.ones(n, dtype=bool)}
    disclaimer_sentence_count = np.zeros(n, dtype=int)
    return df, features, effective, disclaimer_sentence_count


def test_unseen_hazard_routes_to_failures_with_correct_reason() -> None:
    classifier = _fit_classifier()
    rows = [{"prompt_uid": "p0", "hazard": "totally_unseen"}]
    df, features, effective, disclaimer = _predict_frame(rows)

    predictions, failures = predict_rows(df, features, effective, disclaimer, classifier)

    assert predictions == []
    assert len(failures) == 1
    assert failures[0]["prompt_uid"] == "p0"
    assert failures[0]["failure_reason"] == "unseen_hazard"


def test_skipped_cell_routes_to_failures_with_correct_reason() -> None:
    rng = np.random.default_rng(55)
    hazards = np.array(["hte"] * 10 + ["prv"] * 10)
    train_df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i}" for i in range(_N_TRAIN)],
            "hazard": hazards,
            "enablement_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] * 2,
            "legitimization_value": [str(v) for v in ["1"] * 10] + [""] * 10,  # single-class -> skipped
        }
    )
    enablement_features = rng.normal(size=(_N_TRAIN, 3))
    enablement_features[:, 0] += train_df["enablement_value"].astype(int).to_numpy() * 2.0
    legitimization_features = rng.normal(size=(_N_TRAIN, 3))
    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": np.ones(_N_TRAIN, dtype=bool), "legitimization": np.ones(_N_TRAIN, dtype=bool)}

    with pytest.warns(UserWarning, match="Legitimization"):
        classifier = fit(train_df, features, effective, _ENABLEMENT_ONLY, seed=55)
    assert classifier.cells[("legitimization", "hte")].status == "skipped"

    rows = [{"prompt_uid": "p1", "hazard": "hte"}]
    df, pred_features, pred_effective, disclaimer = _predict_frame(rows)
    predictions, failures = predict_rows(df, pred_features, pred_effective, disclaimer, classifier)

    assert predictions == []
    assert len(failures) == 1
    assert failures[0]["failure_reason"] == "skipped_or_absent_cell"


def test_scoreable_row_routes_to_predictions_with_expected_fields() -> None:
    classifier = _fit_classifier()
    rows = [{"prompt_uid": "p2", "hazard": "hte"}]
    df, features, effective, disclaimer = _predict_frame(rows)

    predictions, failures = predict_rows(df, features, effective, disclaimer, classifier)

    assert failures == []
    assert len(predictions) == 1
    row = predictions[0]
    assert row["prompt_uid"] == "p2"
    assert row["hazard"] == "hte"
    assert row["enablement_predicted"] in (0, 1, 2)
    assert row["legitimization_predicted"] in (0, 1, 2)
    assert isinstance(row["v14_overall_unsafe_score"], float)
    assert row["predicted_label"] in ("safe", "unsafe")
    assert isinstance(row["rule_reasons"], str)


def test_every_row_lands_in_exactly_one_output() -> None:
    classifier = _fit_classifier()
    rows = [
        {"prompt_uid": "p3", "hazard": "hte"},
        {"prompt_uid": "p4", "hazard": "prv"},
        {"prompt_uid": "p5", "hazard": "nope"},
        {"prompt_uid": "p6", "hazard": "hte"},
    ]
    df, features, effective, disclaimer = _predict_frame(rows)

    predictions, failures = predict_rows(df, features, effective, disclaimer, classifier)

    assert len(predictions) + len(failures) == len(rows)
    output_uids = {row["prompt_uid"] for row in predictions} | {row["prompt_uid"] for row in failures}
    assert output_uids == {"p3", "p4", "p5", "p6"}


def test_columns_are_exact_and_never_echo_seed_prompt_id() -> None:
    assert PREDICTIONS_COLUMNS == (
        "prompt_uid",
        "hazard",
        "enablement_predicted",
        "legitimization_predicted",
        "v14_overall_unsafe_score",
        "predicted_label",
        "rule_reasons",
    )
    assert FAILURES_COLUMNS == ("prompt_uid", "hazard", "failure_reason")
    assert "seed_prompt_id" not in PREDICTIONS_COLUMNS
    assert "seed_prompt_id" not in FAILURES_COLUMNS


def test_empty_batch_still_writes_a_header(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.csv"
    failures_path = tmp_path / "failures.csv"

    to_predictions_frame([]).to_csv(predictions_path, index=False)
    to_failures_frame([]).to_csv(failures_path, index=False)

    reloaded_predictions = pd.read_csv(predictions_path)
    reloaded_failures = pd.read_csv(failures_path)

    assert list(reloaded_predictions.columns) == list(PREDICTIONS_COLUMNS)
    assert list(reloaded_failures.columns) == list(FAILURES_COLUMNS)
    assert len(reloaded_predictions) == 0
    assert len(reloaded_failures) == 0
