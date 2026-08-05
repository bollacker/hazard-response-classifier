"""The batch runner and its output files
(`docs/planning/PR7_EXECUTION_PLAN.md` §6; `docs/ARCHITECTURE.md` §2, §11).

**The two-pass loop is this module's whole point, and getting it wrong is
the single easiest mistake in PR 7.** `ARCHITECTURE.md` §2 classifies a bad
supplied hazard as a **run-level rejection** -- condition (1) is about "the
supplied hazard of *any input row*" -- so it must abort **before any row is
scored**. A runner that validated each row as it reached it would abort
*mid-batch*, having already written results for earlier rows, which is
precisely what §2 says a rejection is not. So `run_batch` validates every
row's supplied hazard first, and only then scores anything.

Four steps, of which this module owns the last two:

1. load and structurally validate every row (`input_schema.load_csv`);
2. `open_run` once (`profile.resolve`);
3. **`validate_supplied_hazard` over every row, before scoring any**;
4. only then loop, scoring row by row.

Step 3 is exposed as a query as well as a gate --
`find_supplied_hazard_problems` -- so `hrc-run --check-input` can report what
*would* reject a run without running it, off the same rule rather than a
second copy of it (`entrypoint.check_input`,
[D-75](../../docs/planning/DECISIONS.md#d-75)).

**Rejections and failures are different things, and keeping them apart is
most of this module's subtlety.** A **rejection** is about the run's
configuration and input contract: it raises `RunRejectedError` out of
`run_batch`, nothing is scored, and no output file is written. A **failure**
is about one row's content: it becomes a `failures.csv` row (and a record in
`results.jsonl`) and the loop continues to the next row. Nothing here ever
converts one into the other -- in particular `_score_row`'s exception
handler deliberately does **not** catch `RunRejectedError`.

**This module never imports a concrete component** (`ARCHITECTURE.md` §6,
and PR 7's exit criterion). It composes `validate_supplied_hazard`,
`run_pipeline`, and the views, and resolves every implementation through the
`Registry` it is handed -- `profile.build_registry` is the one place that
imports `components/*`. `tests/unit/test_evaluator_profile.py` asserts this
by parsing this module's own source, not by trusting this paragraph.
"""

from __future__ import annotations

import csv
import dataclasses
import json
from pathlib import Path
from typing import Iterable, Sequence

from . import views
from .input_schema import InputRow, build_record
from .pipeline import run_pipeline
from .record import ComponentError, ComponentObservation, EvaluationRecord
from .registry import Registry
from .run import RunContext, RunRejectedError, validate_supplied_hazard

__all__ = [
    "RESULTS_FILENAME",
    "PREDICTIONS_FILENAME",
    "FAILURES_FILENAME",
    "OUTPUT_FILENAMES",
    "SuppliedHazardProblem",
    "find_supplied_hazard_problems",
    "describe_supplied_hazard_problems",
    "run_batch",
    "write_outputs",
]

RESULTS_FILENAME = "results.jsonl"
PREDICTIONS_FILENAME = "predictions.csv"
FAILURES_FILENAME = "failures.csv"
OUTPUT_FILENAMES = (RESULTS_FILENAME, PREDICTIONS_FILENAME, FAILURES_FILENAME)

# Every CSV is written with an explicit "\n" terminator rather than the
# csv module's platform default ("\r\n"), so "same input, same profile, same
# artifact -> byte-identical outputs" (§6) holds across platforms and not
# merely across runs on one machine.
_LINE_TERMINATOR = "\n"


@dataclasses.dataclass(frozen=True)
class SuppliedHazardProblem:
    """One input row whose supplied hazard is a §2 condition-(1) rejection:
    missing, unrecognized, or outside the run's resolved `hazard_scope`.

    Carries the row's position **and** its `response_id` because either
    alone is insufficient in practice -- the position is what a spreadsheet
    shows, the id is what the caller's own data is keyed on -- and no text,
    matching the sensitive-data bound the tabular views hold to (§11).
    """

    index: int
    response_id: str
    supplied_hazard: str
    reason: str


# `validate_supplied_hazard` raises a message phrased as a whole-run verdict
# ("run rejected: ..."), which is right for one row checked on its own and
# wrong once many are listed together -- each line would claim to be its own
# rejected run. Stripped for the per-row rendering only; `removeprefix` is a
# no-op if that wording ever changes, so this degrades to the old text rather
# than breaking.
_ROW_REASON_PREFIX = "run rejected: "


def find_supplied_hazard_problems(
    rows: Sequence[InputRow], run_context: RunContext
) -> tuple[SuppliedHazardProblem, ...]:
    """Pass 1, as a **query**: every row whose supplied hazard would reject
    the run, in input order, raising nothing.

    **This is the single implementation of §2's condition (1) over a batch,
    and it has two callers on purpose.** `run_batch` below turns a non-empty
    result into the `RunRejectedError` that aborts the run, and
    `entrypoint.check_input` reports it without running anything. A
    pre-flight check that re-implemented the rule could drift out of
    agreement with the run it is supposed to predict, which would be worse
    than having no check at all -- so there is one rule and two renderings
    of it, and `test_evaluator_runner.py` pins the agreement rather than
    assuming it.

    Scanning to the end rather than stopping at the first offender is what
    makes cleaning a dirty input one round instead of N. The scan is pure
    set membership over already-parsed rows, so its cost is not a
    consideration: nothing here touches the encoder, the artifact, or disk.
    """
    problems: list[SuppliedHazardProblem] = []
    for index, row in enumerate(rows):
        try:
            validate_supplied_hazard(row.supplied_hazard, run_context)
        except RunRejectedError as exc:
            problems.append(
                SuppliedHazardProblem(
                    index=index,
                    response_id=row.response_id,
                    supplied_hazard=row.supplied_hazard,
                    reason=str(exc).removeprefix(_ROW_REASON_PREFIX),
                )
            )
    return tuple(problems)


# How many offending rows a rejection message spells out before summarizing
# the rest. A message is read in a terminal; the full list is available
# structurally from `find_supplied_hazard_problems` and is what
# `hrc-run --check-input` prints.
_MAX_LISTED_PROBLEMS = 10


def describe_supplied_hazard_problems(
    problems: Sequence[SuppliedHazardProblem],
    run_context: RunContext,
    total_rows: int,
) -> str:
    """The human-readable rejection message `ARCHITECTURE.md` §2 requires:
    it names the offending values, the reason, and -- since a batch has many
    rows -- which rows they came from, plus the resolved scope they were
    checked against, because "not in scope" is unactionable without knowing
    the scope.
    """
    listed = problems[:_MAX_LISTED_PROBLEMS]
    lines = [
        f"run rejected: {len(problems)} of {total_rows} input row(s) carry a supplied "
        "hazard that is missing, unrecognized, or outside the run's hazard scope; "
        "no row was scored and no output was written",
        f"  resolved hazard_scope: {sorted(run_context.hazard_scope)!r}",
    ]
    lines.extend(
        f"  row {problem.index} (response_id={problem.response_id!r}): {problem.reason}"
        for problem in listed
    )
    if len(problems) > len(listed):
        lines.append(f"  ... and {len(problems) - len(listed)} more")
    lines.append(
        "  run with --check-input to list every offending row without scoring anything"
    )
    return "\n".join(lines)


def _validate_every_supplied_hazard(rows: Sequence[InputRow], run_context: RunContext) -> None:
    """Pass 1. Raises `RunRejectedError` naming **every** offending row if
    any row's supplied hazard is a §2 condition-(1) rejection.

    Runs to a rejection over the **whole** input before `_score_row` is
    called even once. That is the property `test_evaluator_runner.py` pins
    with a two-row input whose *second* row is the bad one.
    """
    problems = find_supplied_hazard_problems(rows, run_context)
    if problems:
        raise RunRejectedError(
            describe_supplied_hazard_problems(problems, run_context, len(rows))
        )


def _failed_record(record: EvaluationRecord, exc: BaseException) -> EvaluationRecord:
    """Turn a record whose pipeline raised into an honest failure record.

    **A backstop, not an expected path.** `ARCHITECTURE.md` §5 states that
    `ComponentError` is a record field rather than an exception and that no
    1.1 component raises at run time, so reaching here means a genuine bug
    in a component -- which must still not take the rest of the batch down
    (§6: "a per-row failure never aborts the batch").

    The record stays canonical: it keeps every field the pre-pipeline record
    had, gains an observation recording the error, and reports
    `overall_result="failure"` with the exception as its reason. Nothing is
    invented -- no per-hazard judgment is synthesized, because none was
    made, and `views.failure_rows` renders such a record through its
    record-level branch rather than pretending phase D decided something.

    The stage is not recoverable: the partial record is lost when the
    exception unwinds `run_pipeline`, so the observation names this module
    rather than guessing at a component.
    """
    error = ComponentError(
        stage="runner",
        message=f"{type(exc).__name__}: {exc}",
        hazard=None,
    )
    observation = ComponentObservation(
        stage="runner",
        implementation="batch_runner",
        version="1",
        maturity="working",
        outcome="error",
        facts={},
        text_out=None,
        error=error,
    )
    return dataclasses.replace(
        record,
        observations=record.observations + (observation,),
        overall_result="failure",
        overall_failure_reason=error.message,
    )


def _score_row(row: InputRow, run_context: RunContext, registry: Registry) -> EvaluationRecord:
    """Pass 2, one row. Never raises for anything about the row's *content*
    -- a `ComponentError`, a phase D per-hazard failure, and an unexpected
    exception from a component all produce a record the caller keeps.

    `RunRejectedError` is deliberately **not** caught: it is a rejection,
    not a failure, and swallowing one into a `failures.csv` row would
    collapse the distinction §2 draws. Pass 1 has already made it
    unreachable from here; letting it propagate keeps that true rather than
    merely assumed.
    """
    record = build_record(row, run_context)
    try:
        return run_pipeline(record, run_context, registry)
    except RunRejectedError:
        raise
    except Exception as exc:  # noqa: BLE001 -- see the docstring above
        return _failed_record(record, exc)


def run_batch(
    rows: Sequence[InputRow],
    run_context: RunContext,
    registry: Registry,
) -> tuple[EvaluationRecord, ...]:
    """Score `rows` and return one record per row, in input order.

    Raises `RunRejectedError` -- having scored nothing -- if any row's
    supplied hazard is missing or outside `run_context.hazard_scope`.

    **Exactly one record comes back per input row.** A runner that scored
    999 of 1000 rows and quietly dropped one is the precise shape of the
    "component that runs and looks healthy" failure this project has now met
    three times (`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 5), so the
    count is asserted here rather than left to a caller to notice.
    """
    rows = tuple(rows)
    _validate_every_supplied_hazard(rows, run_context)

    records = tuple(_score_row(row, run_context, registry) for row in rows)

    assert len(records) == len(rows), (
        f"batch runner produced {len(records)} records for {len(rows)} input rows; "
        "every input row must produce exactly one record"
    )
    return records


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[dict]) -> None:
    """Write `rows` under `columns`, always emitting the header -- even for
    an empty batch, so a downstream pipeline can rely on the file's
    existence and shape (the convention the baseline's own `failures.csv`
    already sets, `DECISIONS.md` D-25).
    """
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator=_LINE_TERMINATOR)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_outputs(records: Sequence[EvaluationRecord], output_dir: str | Path) -> dict[str, Path]:
    """Write all three views to `output_dir` and return their paths by
    filename.

    **All three files are always written**, including `failures.csv` on a
    clean batch -- absence would be ambiguous between "no failures" and "the
    run did not get that far", and the run-rejection case is already
    distinguished by *no* files existing at all (§6's exit criterion).

    **Determinism** (§6): records are written in input order, each record's
    rows in `evaluated_hazards` order, and nothing is ordered by dict
    iteration -- so the same input, profile, and artifact produce
    byte-identical files.
    """
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    results_path = directory / RESULTS_FILENAME
    with open(results_path, "w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(views.result_view(record)))
            handle.write("\n")

    predictions_path = directory / PREDICTIONS_FILENAME
    _write_csv(
        predictions_path,
        views.PREDICTION_COLUMNS,
        (row for record in records for row in views.prediction_rows(record)),
    )

    failures_path = directory / FAILURES_FILENAME
    _write_csv(
        failures_path,
        views.FAILURE_COLUMNS,
        (row for record in records for row in views.failure_rows(record)),
    )

    return {
        RESULTS_FILENAME: results_path,
        PREDICTIONS_FILENAME: predictions_path,
        FAILURES_FILENAME: failures_path,
    }
