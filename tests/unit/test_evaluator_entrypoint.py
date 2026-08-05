"""Tests for `hazard_classifier/evaluator/entrypoint.py`: the in-process
Python entry point (slice D, `docs/planning/PR7_EXECUTION_PLAN.md` §7).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.embed import EMBEDDING_DIM
from hazard_classifier.evaluator import entrypoint, profile
from hazard_classifier.evaluator.input_schema import InputSchemaError
from hazard_classifier.evaluator.run import RunRejectedError

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"


class _StubProvider:
    name: ClassVar[str] = "stub"
    version: ClassVar[str] = "1"

    def embed(self, texts) -> np.ndarray:
        return np.zeros((len(list(texts)), EMBEDDING_DIM), dtype=np.float32)


class _StubPooling:
    name: ClassVar[str] = "stub"

    def pool(self, vectors: np.ndarray) -> np.ndarray:
        return (
            np.zeros(EMBEDDING_DIM, dtype=np.float32)
            if vectors.shape[0] == 0
            else vectors.mean(axis=0)
        )


def _write_input_csv(path: Path, rows: list[dict]) -> None:
    import csv

    columns = ["request_id", "prompt_uid", "response_id", "prompt_text", "response_text", "supplied_hazard"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(index: int, hazard: str = "hte") -> dict:
    return {
        "request_id": f"req-{index}",
        "prompt_uid": f"pu-{index}",
        "response_id": f"resp-{index}",
        "prompt_text": "How should I store household chemicals?",
        "response_text": "Store bleach and ammonia in separate cabinets.",
        "supplied_hazard": hazard,
    }


def test_run_writes_all_three_outputs_and_returns_the_records(tmp_path) -> None:
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0), _row(1)])
    output_dir = tmp_path / "out"
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    records = entrypoint.run(
        run_profile, input_csv, output_dir, provider=_StubProvider(), pooling=_StubPooling()
    )

    assert len(records) == 2
    assert [record.response_id for record in records] == ["resp-0", "resp-1"]
    for filename in ("results.jsonl", "predictions.csv", "failures.csv"):
        assert (output_dir / filename).exists()


def test_run_propagates_a_run_rejection_without_writing_anything(tmp_path) -> None:
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0, hazard="hte"), _row(1, hazard="not_in_scope")])
    output_dir = tmp_path / "out"
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    with pytest.raises(RunRejectedError):
        entrypoint.run(run_profile, input_csv, output_dir, provider=_StubProvider(), pooling=_StubPooling())

    assert not output_dir.exists()


def test_run_propagates_a_malformed_input_error(tmp_path) -> None:
    input_csv = tmp_path / "input.csv"
    input_csv.write_text("request_id,prompt_uid\nreq-0,pu-0\n")
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    with pytest.raises(InputSchemaError):
        entrypoint.run(
            run_profile, input_csv, tmp_path / "out", provider=_StubProvider(), pooling=_StubPooling()
        )


def test_run_is_deterministic_across_two_identical_calls(tmp_path) -> None:
    """Not the CLI/in-process identity test (that needs both entry points,
    `tests/unit/test_cli_run.py`) -- this is the narrower property the
    identity test depends on: calling `run` twice on the same input produces
    byte-identical files.
    """
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0), _row(1), _row(2)])
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    entrypoint.run(run_profile, input_csv, first_dir, provider=_StubProvider(), pooling=_StubPooling())
    entrypoint.run(run_profile, input_csv, second_dir, provider=_StubProvider(), pooling=_StubPooling())

    for filename in ("results.jsonl", "predictions.csv", "failures.csv"):
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()


def test_run_records_the_resolved_hazard_scope_in_every_output_record(tmp_path) -> None:
    """PR 7 exit criterion: "the resolved hazard scope is recorded in the
    run context and in every output record" -- checked on the written
    `results.jsonl`, not on the in-memory context, per the plan's own
    verification note (§11's table).
    """
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0)])
    output_dir = tmp_path / "out"
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    entrypoint.run(run_profile, input_csv, output_dir, provider=_StubProvider(), pooling=_StubPooling())

    with open(output_dir / "results.jsonl", encoding="utf-8") as handle:
        entry = json.loads(handle.readline())

    assert entry["run"]["hazard_scope"] == sorted(classifier.trained_hazards)


# --- check_input: the pre-flight path (D-75) -------------------------------


def test_check_input_reports_clean_for_an_input_that_would_run(tmp_path) -> None:
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0), _row(1, hazard="prv")])
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    report = entrypoint.check_input(
        run_profile, input_csv, provider=_StubProvider(), pooling=_StubPooling()
    )

    assert report.ok
    assert report.problems == ()
    assert report.rows == 2
    # The resolved scope is reported, because "not in scope" is unactionable
    # without it -- and it is D-57's default, since the profile named none.
    assert report.hazard_scope == ("hte", "prv")


def test_check_input_reports_every_offending_row(tmp_path) -> None:
    input_csv = tmp_path / "input.csv"
    _write_input_csv(
        input_csv,
        [_row(0), _row(1, hazard="not_in_scope"), _row(2), _row(3, hazard="also_bad")],
    )
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    report = entrypoint.check_input(
        run_profile, input_csv, provider=_StubProvider(), pooling=_StubPooling()
    )

    assert not report.ok
    assert [problem.index for problem in report.problems] == [1, 3]
    assert [problem.response_id for problem in report.problems] == ["resp-1", "resp-3"]
    assert [problem.supplied_hazard for problem in report.problems] == [
        "not_in_scope",
        "also_bad",
    ]
    assert report.rows == 4


def test_check_input_writes_nothing_and_scores_nothing(tmp_path) -> None:
    """It is a *pre-flight* check: no output directory is even an argument,
    and the encoder is never asked to do anything.
    """

    class _ExplodingProvider(_StubProvider):
        def embed(self, texts):  # pragma: no cover -- must never be called
            raise AssertionError("check_input must not score anything")

    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0), _row(1)])
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    report = entrypoint.check_input(
        run_profile, input_csv, provider=_ExplodingProvider(), pooling=_StubPooling()
    )

    assert report.ok
    assert list(tmp_path.iterdir()) == [input_csv]


def test_check_input_agrees_with_run_on_the_same_input(tmp_path) -> None:
    """The property the check exists for: `report.ok` is exactly "`run`
    would not raise `RunRejectedError`" (D-75). Checked through both entry
    points on the same files, not by inspecting the shared function.
    """
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    for name, rows in (
        ("clean", [_row(0), _row(1)]),
        ("second-row-bad", [_row(0), _row(1, hazard="not_in_scope")]),
        ("all-bad", [_row(0, hazard="nope")]),
    ):
        case_dir = tmp_path / name
        case_dir.mkdir()
        input_csv = case_dir / "input.csv"
        _write_input_csv(input_csv, rows)

        report = entrypoint.check_input(
            run_profile, input_csv, provider=_StubProvider(), pooling=_StubPooling()
        )
        try:
            entrypoint.run(
                run_profile,
                input_csv,
                case_dir / "out",
                provider=_StubProvider(),
                pooling=_StubPooling(),
            )
        except RunRejectedError:
            rejected = True
        else:
            rejected = False

        assert report.ok is not rejected, name


def test_check_input_raises_the_same_structural_errors_a_run_would(tmp_path) -> None:
    """A pre-flight check that passed a file `run` would reject on its
    *schema* would be a false all-clear, so `check_input` performs the same
    `load_csv` and lets the same error out.
    """
    input_csv = tmp_path / "input.csv"
    input_csv.write_text("request_id,prompt_uid\nreq-0,pu-0\n")
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    with pytest.raises(InputSchemaError):
        entrypoint.check_input(
            run_profile, input_csv, provider=_StubProvider(), pooling=_StubPooling()
        )


def test_check_input_raises_a_rejection_for_a_scope_wider_than_the_artifact(tmp_path) -> None:
    """§2 conditions (2) and (3) are run-level, not per-row, so they still
    *raise* out of the check rather than appearing in `problems` -- the
    check reports what is per-row and propagates what is not.
    """
    input_csv = tmp_path / "input.csv"
    _write_input_csv(input_csv, [_row(0)])
    run_profile = profile.RunProfile(
        artifact_id=str(GOLDEN_ARTIFACT), hazard_scope={"hte", "prv", "cse"}
    )

    with pytest.raises(RunRejectedError):
        entrypoint.check_input(
            run_profile, input_csv, provider=_StubProvider(), pooling=_StubPooling()
        )
