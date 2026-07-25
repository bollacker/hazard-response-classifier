"""CLI smoke test for `hrc-evaluate` (`PLAN.md` §8.1: train -> evaluate
against `examples/sample_input.csv`, BGE mocked so no network/model
download is needed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from hazard_classifier import embed
from hazard_classifier.cli.evaluate import main as evaluate_main
from hazard_classifier.cli.train import main as train_main

_SAMPLE_INPUT = Path(__file__).resolve().parents[2] / "examples" / "sample_input.csv"


def _fake_embed_sentences(sentences, **kwargs):
    import numpy as np

    rng = np.random.default_rng(0)
    return rng.normal(size=(len(sentences), embed.EMBEDDING_DIM)).astype(np.float32)


def _train(tmp_path, monkeypatch, extra_args: list[str] | None = None) -> Path:
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    model_dir = tmp_path / "model"
    train_main(["--input", str(_SAMPLE_INPUT), "--output-dir", str(model_dir), *(extra_args or [])])
    return model_dir


def test_hrc_evaluate_writes_all_three_outputs(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    output_dir = tmp_path / "eval_results"

    evaluate_main(["--model-dir", str(model_dir), "--input", str(_SAMPLE_INPUT), "--output-dir", str(output_dir)])

    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.txt").exists()

    report = json.loads((output_dir / "metrics.json").read_text())
    # No --holdout-seed-fraction at train time -> everything is in-sample/unrecorded (D-13).
    assert report["holdout_recorded"] is False
    assert "held_out" not in report
    assert report["excluded_row_count"] == 0
    in_sample = report["in_sample_unrecorded"]
    assert in_sample["n_rows"] == 12
    assert in_sample["components"]["enablement"]["n"] == 12
    # prv is enablement-only (D-15/D-18) -- 6 of the 12 rows are excluded from Legitimization.
    assert in_sample["components"]["legitimization"]["n"] == 6
    assert in_sample["final_label"]["n"] == 12

    metrics_csv = pd.read_csv(output_dir / "metrics.csv")
    assert list(metrics_csv.columns) == ["population", "section", "metric", "value"]
    assert set(metrics_csv["population"]) == {"overall", "in_sample_unrecorded"}
    assert (metrics_csv["metric"] == "n_rows").any()

    summary = (output_dir / "summary.txt").read_text()
    assert "holdout_recorded: False" in summary
    assert "no recorded held-out split" in summary
    assert "in_sample_unrecorded" in summary


def test_hrc_evaluate_reports_both_populations_when_holdout_reserved(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch, extra_args=["--holdout-seed-fraction", "0.5"])
    output_dir = tmp_path / "eval_results"

    evaluate_main(["--model-dir", str(model_dir), "--input", str(_SAMPLE_INPUT), "--output-dir", str(output_dir)])

    report = json.loads((output_dir / "metrics.json").read_text())
    assert report["holdout_recorded"] is True
    assert "held_out" in report
    assert "in_sample_unrecorded" in report
    assert report["held_out"]["n_rows"] + report["in_sample_unrecorded"]["n_rows"] == 12

    summary = (output_dir / "summary.txt").read_text()
    assert "no recorded held-out split" not in summary
    assert "=== held_out" in summary
    assert "=== in_sample_unrecorded" in summary


def test_hrc_evaluate_fatal_on_blank_ground_truth(tmp_path, monkeypatch, capsys) -> None:
    """A blank `enablement_value` on a known, non-enablement-only hazard row
    is a data defect (`DECISIONS.md` D-26) -- `evaluate_rows` raises
    `BlankGroundTruthError`, which must exit cleanly via `fatal`, not a raw
    traceback.
    """
    model_dir = _train(tmp_path, monkeypatch)

    bad_input = tmp_path / "blank_label.csv"
    df = pd.read_csv(_SAMPLE_INPUT, dtype=str, keep_default_na=False)
    df.loc[df["prompt_uid"] == "pu0", "enablement_value"] = ""
    df.to_csv(bad_input, index=False)

    with pytest.raises(SystemExit) as exc_info:
        evaluate_main(
            ["--model-dir", str(model_dir), "--input", str(bad_input), "--output-dir", str(tmp_path / "eval_out")]
        )

    assert exc_info.value.code == 1
    assert "hrc-evaluate" in capsys.readouterr().err
