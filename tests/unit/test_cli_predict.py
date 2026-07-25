"""CLI smoke test for `hrc-predict` (`PLAN.md` §8.1: train -> predict
against `examples/sample_input.csv`, BGE mocked so no network/model
download is needed).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hazard_classifier import embed
from hazard_classifier.cli.predict import main as predict_main
from hazard_classifier.cli.train import main as train_main

_SAMPLE_INPUT = Path(__file__).resolve().parents[2] / "examples" / "sample_input.csv"


def _fake_embed_sentences(sentences, **kwargs):
    rng = np.random.default_rng(0)
    return rng.normal(size=(len(sentences), embed.EMBEDDING_DIM)).astype(np.float32)


def _train(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    model_dir = tmp_path / "model"
    train_main(["--input", str(_SAMPLE_INPUT), "--output-dir", str(model_dir)])
    return model_dir


def test_hrc_predict_scores_every_row_with_no_failures(tmp_path, monkeypatch) -> None:
    """Ground-truth columns are present in `sample_input.csv` but must be
    ignored on this path (D-24) -- every one of its 12 rows is a hazard the
    artifact just trained on, so none should hard-fail.
    """
    model_dir = _train(tmp_path, monkeypatch)
    output_dir = tmp_path / "predictions"

    predict_main(["--model-dir", str(model_dir), "--input", str(_SAMPLE_INPUT), "--output-dir", str(output_dir)])

    assert (output_dir / "predictions.csv").exists()
    assert (output_dir / "failures.csv").exists()

    predictions = pd.read_csv(output_dir / "predictions.csv")
    failures = pd.read_csv(output_dir / "failures.csv")

    assert list(predictions.columns) == [
        "prompt_uid",
        "hazard",
        "enablement_predicted",
        "legitimization_predicted",
        "v14_overall_unsafe_score",
        "predicted_label",
        "rule_reasons",
    ]
    assert list(failures.columns) == ["prompt_uid", "hazard", "failure_reason"]
    assert len(predictions) == 12
    assert len(failures) == 0
    # D-18: prv is enablement-only, so legitimization_predicted must be blank/NaN for those rows.
    assert predictions.loc[predictions["hazard"] == "prv", "legitimization_predicted"].isna().all()
    assert predictions["predicted_label"].isin(["safe", "unsafe"]).all()
    # seed_prompt_id must never be echoed into either output (D-25's 2026-07-25 amendment).
    assert "seed_prompt_id" not in predictions.columns
    assert "seed_prompt_id" not in failures.columns


def test_hrc_predict_routes_unseen_hazard_to_failures(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    output_dir = tmp_path / "predictions"

    df = pd.read_csv(_SAMPLE_INPUT, dtype=str, keep_default_na=False)
    unseen_row = df.iloc[[0]].copy()
    unseen_row["hazard"] = "totally_unseen_hazard"
    unseen_row["prompt_uid"] = "pu_unseen"
    mixed_input = tmp_path / "mixed.csv"
    pd.concat([df, unseen_row], ignore_index=True).to_csv(mixed_input, index=False)

    predict_main(["--model-dir", str(model_dir), "--input", str(mixed_input), "--output-dir", str(output_dir)])

    predictions = pd.read_csv(output_dir / "predictions.csv")
    failures = pd.read_csv(output_dir / "failures.csv")

    assert len(predictions) + len(failures) == 13
    assert len(failures) == 1
    assert failures.iloc[0]["prompt_uid"] == "pu_unseen"
    assert failures.iloc[0]["failure_reason"] == "unseen_hazard"
    assert "pu_unseen" not in set(predictions["prompt_uid"])


def test_hrc_predict_fatal_on_schema_error(tmp_path, monkeypatch, capsys) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    bad_input = tmp_path / "missing_hazard_column.csv"
    bad_input.write_text("seed_prompt_id,prompt_uid,prompt_text,response_text\nsp0,pu0,prompt,response\n")

    with pytest.raises(SystemExit) as exc_info:
        predict_main(
            ["--model-dir", str(model_dir), "--input", str(bad_input), "--output-dir", str(tmp_path / "out")]
        )

    assert exc_info.value.code == 1
    assert "hrc-predict" in capsys.readouterr().err


def test_hrc_predict_fatal_on_missing_model_dir(tmp_path, capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        predict_main(
            [
                "--model-dir",
                str(tmp_path / "does_not_exist"),
                "--input",
                str(_SAMPLE_INPUT),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )

    assert exc_info.value.code == 1
    assert "hrc-predict" in capsys.readouterr().err
