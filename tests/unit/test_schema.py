"""Engineering-level tests for input schema validation (`PLAN.md` §8.1):
column presence, hazard normalization, label ranges, and the mode-scoped
(train/evaluate/predict) ground-truth rules from DECISIONS.md D-24/D-26/D-27.
"""

from __future__ import annotations

import csv

import pytest

from hazard_classifier.schema import SchemaError, load_csv, normalize_hazard

FULL_HEADER = [
    "seed_prompt_id",
    "prompt_uid",
    "prompt_text",
    "response_text",
    "hazard",
    "enablement_value",
    "legitimization_value",
    "is_safe_ground_truth",
]
CORE_HEADER = FULL_HEADER[:5]


def _write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_normalize_hazard_strips_and_hyphen_to_underscore():
    assert normalize_hazard("spc-fin ") == "spc_fin"
    assert normalize_hazard(" spc-fin") == "spc_fin"


def test_normalize_hazard_does_not_lowercase():
    # DECISIONS.md D-27: "be like the toy" -- strip + hyphen->underscore only,
    # never lowercase, so a case variant stays a genuinely distinct code.
    assert normalize_hazard("SPC_FIN") == "SPC_FIN"
    assert normalize_hazard("SPC_FIN") != "spc_fin"


def test_load_csv_train_normalizes_hazard_column(tmp_path):
    path = tmp_path / "train.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "spc-fin ", "1", "1", "unsafe"]],
    )
    df = load_csv(path, mode="train")
    assert df["hazard"].tolist() == ["spc_fin"]


def test_load_csv_train_rejects_unknown_hazard_when_known_hazards_given(tmp_path):
    # The case variant "SPC_FIN" is a genuinely different code from "spc_fin"
    # (no lowercasing), so it stays unseen against a lowercase known set.
    path = tmp_path / "train.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "SPC_FIN", "1", "1", "unsafe"]],
    )
    with pytest.raises(SchemaError, match="unrecognized hazard"):
        load_csv(path, mode="train", known_hazards={"spc_fin"})


def test_load_csv_train_known_hazard_passes(tmp_path):
    path = tmp_path / "train.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "spc-fin", "1", "1", "unsafe"]],
    )
    df = load_csv(path, mode="train", known_hazards={"spc_fin"})
    assert df["hazard"].tolist() == ["spc_fin"]


def test_load_csv_train_missing_required_column_raises(tmp_path):
    path = tmp_path / "train.csv"
    header = [c for c in FULL_HEADER if c != "is_safe_ground_truth"]
    _write_csv(path, header, [["s1", "p1", "prompt", "response", "hte", "1", "1"]])
    with pytest.raises(SchemaError, match="is_safe_ground_truth"):
        load_csv(path, mode="train")


def test_load_csv_train_out_of_range_label_raises(tmp_path):
    path = tmp_path / "train.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "hte", "3", "1", "unsafe"]],
    )
    with pytest.raises(SchemaError, match="enablement_value"):
        load_csv(path, mode="train")


def test_load_csv_evaluate_out_of_range_label_raises(tmp_path):
    path = tmp_path / "evaluate.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "hte", "1", "5", "unsafe"]],
    )
    with pytest.raises(SchemaError, match="legitimization_value"):
        load_csv(path, mode="evaluate")


def test_load_csv_blank_ordinal_label_does_not_raise(tmp_path):
    # A blank legitimization_value is expected for enablement-only hazards
    # (D-15/D-18) -- schema.py cannot tell which hazards those are (no
    # artifact), so it must never reject a blank at this layer at all.
    path = tmp_path / "train.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "prv", "1", "", "unsafe"]],
    )
    df = load_csv(path, mode="train")
    assert df["legitimization_value"].tolist() == [""]


def test_load_csv_predict_requires_only_core_columns(tmp_path):
    path = tmp_path / "predict.csv"
    _write_csv(path, CORE_HEADER, [["s1", "p1", "prompt", "response", "hte"]])
    df = load_csv(path, mode="predict")
    assert df["hazard"].tolist() == ["hte"]


def test_load_csv_predict_ignores_ground_truth_columns_entirely(tmp_path):
    # DECISIONS.md D-24: ground-truth columns are optional and ignored on the
    # predict path -- not even range-checked, so a caller can reuse a labeled
    # CSV unchanged, garbage values and all.
    path = tmp_path / "predict.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "hte", "7", "9", "garbage"]],
    )
    df = load_csv(path, mode="predict")
    assert df["enablement_value"].tolist() == ["7"]


def test_load_csv_evaluate_requires_ground_truth_columns_present(tmp_path):
    path = tmp_path / "evaluate.csv"
    _write_csv(path, CORE_HEADER, [["s1", "p1", "prompt", "response", "hte"]])
    with pytest.raises(SchemaError, match="enablement_value"):
        load_csv(path, mode="evaluate")


def test_load_csv_evaluate_blank_ground_truth_and_unknown_hazard_does_not_raise(tmp_path):
    # DECISIONS.md D-26's 2026-07-25 Finding-A amendment, at the layer
    # schema.py actually controls: schema.py must never promote a blank
    # ground-truth value to a run-abort, even when it cannot confirm the
    # hazard is known at all -- whether this row is tolerated (an
    # enablement-only hazard) or a hard-fail (D-14, excluded-and-counted, not
    # a run-abort) is a per-row judgment against the loaded artifact that
    # only hrc-evaluate can make (IS-8), never schema.py.
    path = tmp_path / "evaluate.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "totally_unknown_hazard", "", "", ""]],
    )
    df = load_csv(path, mode="evaluate")
    assert df["hazard"].tolist() == ["totally_unknown_hazard"]


def test_known_hazards_rejected_outside_train_mode(tmp_path):
    # D-27: predict/evaluate must never reject on hazard membership at this
    # layer (that would abort the run against D-22/D-14) -- a caller passing
    # known_hazards for the wrong mode is a usage error, not something to
    # silently ignore.
    path = tmp_path / "evaluate.csv"
    _write_csv(
        path,
        FULL_HEADER,
        [["s1", "p1", "prompt", "response", "hte", "1", "1", "unsafe"]],
    )
    with pytest.raises(ValueError, match="mode='train'"):
        load_csv(path, mode="evaluate", known_hazards={"hte"})
