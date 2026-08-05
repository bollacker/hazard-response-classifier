"""CLI tests for `hrc-run` (slice D, `docs/planning/PR7_EXECUTION_PLAN.md`
§7). BGE is mocked so no network/model download is needed, matching
`test_cli_predict.py`'s established pattern.

`test_cli_and_in_process_produce_identical_records_for_identical_input` is
this slice's own exit criterion, verified the way the plan requires: "run
both, compare the parsed `results.jsonl`" -- not an assertion that the CLI
calls `entrypoint.run`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hazard_classifier import embed
from hazard_classifier.cli.run import main as run_main
from hazard_classifier.cli.train import main as train_main
from hazard_classifier.evaluator import entrypoint, profile

_SAMPLE_INPUT = Path(__file__).resolve().parents[2] / "examples" / "sample_input.csv"

_INPUT_COLUMNS = ["request_id", "prompt_uid", "response_id", "prompt_text", "response_text", "supplied_hazard"]


def _fake_embed_sentences(sentences, **kwargs):
    rng = np.random.default_rng(0)
    return rng.normal(size=(len(sentences), embed.EMBEDDING_DIM)).astype(np.float32)


def _train(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    model_dir = tmp_path / "model"
    train_main(["--input", str(_SAMPLE_INPUT), "--output-dir", str(model_dir)])
    return model_dir


def _write_input_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_INPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(index: int, hazard: str = "hte") -> dict:
    return {
        "request_id": f"req-{index}",
        "prompt_uid": f"pu-{index}",
        "response_id": f"resp-{index}",
        "prompt_text": "How should I store household chemicals?",
        "response_text": "Store bleach and ammonia in separate cabinets because mixing them creates a toxic gas.",
        "supplied_hazard": hazard,
    }


def _write_profile(path: Path, artifact_id: str) -> None:
    path.write_text(json.dumps({"artifact_id": artifact_id}))


def test_hrc_run_help_works() -> None:
    """PR 7's exit criterion, literally: "`hrc-run --help` works"."""
    with pytest.raises(SystemExit) as exc_info:
        run_main(["--help"])
    assert exc_info.value.code == 0


def test_hrc_run_scores_every_row_with_no_failures(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, "hte"), _row(1, "prv")])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))
    output_dir = tmp_path / "out"

    run_main(
        [
            "--profile",
            str(profile_path),
            "--input",
            str(input_csv),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert (output_dir / "results.jsonl").exists()
    predictions = pd.read_csv(output_dir / "predictions.csv")
    failures = pd.read_csv(output_dir / "failures.csv")
    assert len(predictions) == 2
    assert len(failures) == 0


def test_hrc_run_model_dir_flag_overrides_the_profiles_artifact_id(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0)])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, "this/path/does/not/exist")
    output_dir = tmp_path / "out"

    run_main(
        [
            "--profile",
            str(profile_path),
            "--model-dir",
            str(model_dir),
            "--input",
            str(input_csv),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert (output_dir / "results.jsonl").exists()


def test_hrc_run_fatal_on_a_run_rejection(tmp_path, monkeypatch, capsys) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, hazard="totally_unsupported_hazard")])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))
    output_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc_info:
        run_main(
            [
                "--profile",
                str(profile_path),
                "--input",
                str(input_csv),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert exc_info.value.code == 1
    assert "hrc-run" in capsys.readouterr().err
    assert not output_dir.exists()


def test_hrc_run_fatal_on_a_malformed_input_csv(tmp_path, monkeypatch, capsys) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    bad_input = tmp_path / "bad.csv"
    bad_input.write_text("request_id,prompt_uid\nreq-0,pu-0\n")
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    with pytest.raises(SystemExit) as exc_info:
        run_main(
            [
                "--profile",
                str(profile_path),
                "--input",
                str(bad_input),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )

    assert exc_info.value.code == 1
    assert "hrc-run" in capsys.readouterr().err


def test_hrc_run_fatal_on_a_missing_profile_field(tmp_path, capsys) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"text_view": "working"}))

    with pytest.raises(SystemExit) as exc_info:
        run_main(
            [
                "--profile",
                str(profile_path),
                "--input",
                str(_SAMPLE_INPUT),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )

    assert exc_info.value.code == 1
    assert "hrc-run" in capsys.readouterr().err


def test_cli_and_in_process_produce_identical_records_for_identical_input(tmp_path, monkeypatch) -> None:
    """The slice's own exit criterion. Both paths score the same input under
    the same profile; the parsed `results.jsonl` files must match exactly,
    not merely "look similar" -- including the pooled embedding's effect on
    the score, which is why both runs need the same monkeypatched encoder
    rather than two different stubs.
    """
    model_dir = _train(tmp_path, monkeypatch)
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, "hte"), _row(1, "prv"), _row(2, "hte")])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    cli_output_dir = tmp_path / "cli_out"
    run_main(
        [
            "--profile",
            str(profile_path),
            "--input",
            str(input_csv),
            "--output-dir",
            str(cli_output_dir),
        ]
    )

    in_process_output_dir = tmp_path / "in_process_out"
    run_profile = profile.load_profile(profile_path)
    entrypoint.run(run_profile, input_csv, in_process_output_dir)

    def _read_results(directory: Path) -> list[dict]:
        with open(directory / "results.jsonl", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    cli_results = _read_results(cli_output_dir)
    in_process_results = _read_results(in_process_output_dir)

    assert cli_results == in_process_results
    assert len(cli_results) == 3

    # And the byte-for-byte form too, not only the parsed structure.
    assert (
        (cli_output_dir / "results.jsonl").read_bytes()
        == (in_process_output_dir / "results.jsonl").read_bytes()
    )
    assert (
        (cli_output_dir / "predictions.csv").read_bytes()
        == (in_process_output_dir / "predictions.csv").read_bytes()
    )
    assert (
        (cli_output_dir / "failures.csv").read_bytes()
        == (in_process_output_dir / "failures.csv").read_bytes()
    )


# --- --check-input: the pre-flight mode (D-75) -----------------------------


def test_check_input_reports_clean_and_exits_zero(tmp_path, monkeypatch, capsys) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, "hte"), _row(1, "prv")])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    # No --output-dir, and no SystemExit: a clean check is a success.
    run_main(["--profile", str(profile_path), "--input", str(input_csv), "--check-input"])

    out = capsys.readouterr().out
    assert "2 row(s) OK" in out
    assert "would not be rejected" in out


def test_check_input_lists_every_offending_row_and_exits_one(tmp_path, monkeypatch, capsys) -> None:
    """The whole point of the mode: a caller fixing a dirty file gets the
    complete list in one round, and gets it before committing to a run.
    """
    model_dir = _train(tmp_path, monkeypatch)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(
        input_csv,
        [_row(0, "hte"), _row(1, "not_in_scope"), _row(2, "prv"), _row(3, "also_bad")],
    )
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    with pytest.raises(SystemExit) as exc_info:
        run_main(["--profile", str(profile_path), "--input", str(input_csv), "--check-input"])

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "2 of 4 row(s) would reject the run" in err
    for token in ("resp-1", "not_in_scope", "resp-3", "also_bad"):
        assert token in err
    assert "resp-0" not in err  # clean rows are not listed


def test_check_input_writes_no_output_files(tmp_path, monkeypatch) -> None:
    model_dir = _train(tmp_path, monkeypatch)
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, "hte")])
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    run_main(["--profile", str(profile_path), "--input", str(input_csv), "--check-input"])

    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob("**/results.jsonl"))


def test_check_input_predicts_the_real_run_through_the_cli(tmp_path, monkeypatch) -> None:
    """Agreement, asserted end to end through the CLI rather than through
    the shared function: a clean check must be followed by a run that
    completes, and a dirty one by a run that exits 1.
    """
    model_dir = _train(tmp_path, monkeypatch)
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, str(model_dir))

    for name, rows, expect_clean in (
        ("clean", [_row(0, "hte"), _row(1, "prv")], True),
        ("dirty", [_row(0, "hte"), _row(1, "not_in_scope")], False),
    ):
        case_dir = tmp_path / name
        case_dir.mkdir()
        input_csv = case_dir / "input.csv"
        _write_input_csv(input_csv, rows)
        check_argv = ["--profile", str(profile_path), "--input", str(input_csv), "--check-input"]
        run_argv = [
            "--profile", str(profile_path),
            "--input", str(input_csv),
            "--output-dir", str(case_dir / "out"),
        ]

        if expect_clean:
            run_main(check_argv)
            run_main(run_argv)
            assert (case_dir / "out" / "results.jsonl").exists()
        else:
            with pytest.raises(SystemExit) as check_exit:
                run_main(check_argv)
            with pytest.raises(SystemExit) as run_exit:
                run_main(run_argv)
            assert check_exit.value.code == run_exit.value.code == 1
            assert not (case_dir / "out").exists()


def test_output_dir_is_required_without_check_input(tmp_path, capsys) -> None:
    """`--output-dir` stopped being an argparse-required flag so `--check-input`
    could omit it; the requirement itself must not have been lost with it.
    """
    profile_path = tmp_path / "profile.json"
    _write_profile(profile_path, "unused")
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, "hte")])

    with pytest.raises(SystemExit) as exc_info:
        run_main(["--profile", str(profile_path), "--input", str(input_csv)])

    assert exc_info.value.code == 1
    assert "--output-dir is required" in capsys.readouterr().err
