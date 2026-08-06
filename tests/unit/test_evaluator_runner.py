"""Tests for `hazard_classifier/evaluator/runner.py` and the `failures.csv`
view (slice C, `docs/planning/PR7_EXECUTION_PLAN.md` §6).

The load-bearing test here is
`test_a_bad_hazard_on_the_second_row_scores_nothing_and_writes_nothing`:
`ARCHITECTURE.md` §2 makes a bad supplied hazard a **run-level rejection**,
so it must abort before *any* row is scored. A runner that folded validation
into the scoring loop would pass every other test in this file and fail that
one.
"""

from __future__ import annotations

import ast
import csv
import dataclasses
import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.embed import EMBEDDING_DIM
from hazard_classifier.evaluator import profile, runner, views
from hazard_classifier.evaluator.input_schema import InputRow
from hazard_classifier.evaluator.record import (
    ComponentObservation,
    EvaluationRecord,
    HazardJudgment,
    Judgment,
)
from hazard_classifier.evaluator.run import RunConfig, RunRejectedError, open_run

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"


class _StubProvider:
    """Counts `embed` calls, so "no row was scored" can be asserted against
    what the encoder was actually asked to do rather than inferred from an
    absent output file.
    """

    name: ClassVar[str] = "stub"
    version: ClassVar[str] = "1"

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts) -> np.ndarray:
        self.calls += 1
        return np.zeros((len(list(texts)), EMBEDDING_DIM), dtype=np.float32)


class _StubPooling:
    name: ClassVar[str] = "stub"

    def pool(self, vectors: np.ndarray) -> np.ndarray:
        return (
            np.zeros(EMBEDDING_DIM, dtype=np.float32)
            if vectors.shape[0] == 0
            else vectors.mean(axis=0)
        )


class _MissingEnablementScorer:
    """A stage-9 stub that judges Legitimization but not Enablement.

    `SCIENCE.md` phase D: "E is never fixed by rule here, so a missing E
    judgment is always a failure." This is therefore the smallest honest way
    to produce a per-hazard failure -- no artificial `RunContext`, no hazard
    the artifact was never trained on.
    """

    stage: ClassVar[str] = "scoring"
    implementation: ClassVar[str] = "stub_missing_enablement"
    version: ClassVar[str] = "1"
    maturity: ClassVar[str] = "partial"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        per_hazard = dict(record.per_hazard)
        for hazard in record.evaluated_hazards:
            per_hazard[hazard] = HazardJudgment(
                hazard=hazard,
                source="supplied" if hazard == record.supplied_hazard else "detected",
                legitimization_applies=True,
                provisional_l=Judgment(label="L1", distribution=None, model_version="stub:1"),
                provisional_e=None,
            )
        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={},
            text_out=None,
            errors=(),
        )
        return dataclasses.replace(
            record, per_hazard=per_hazard, observations=record.observations + (observation,)
        )


class _RaisingScorer:
    """A stage-9 stub that raises. `ARCHITECTURE.md` §5 says no 1.1
    component raises at run time, so this exercises the runner's backstop
    against a genuine component bug -- which must still not take the batch
    down.
    """

    stage: ClassVar[str] = "scoring"
    implementation: ClassVar[str] = "stub_raising"
    version: ClassVar[str] = "1"
    maturity: ClassVar[str] = "partial"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        raise RuntimeError("deliberate component bug")


def _resolved(*, scoring_override=None, hazard_scope=None):
    """Build a real registry from the golden artifact (stubbing only the
    encoder, for speed and to keep the test network-free), optionally
    swapping stage 9 for a stub through the registry -- the replaceability
    §6 exists to provide, exercised rather than asserted.
    """
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    provider = _StubProvider()
    built = profile.build_registry(classifier, provider=provider, pooling=_StubPooling())

    selection = dict(built.component_selection)
    if scoring_override is not None:
        built.registry.register(scoring_override)
        selection["scoring"] = scoring_override.implementation

    config = RunConfig(
        hazard_scope=hazard_scope if hazard_scope is not None else frozenset(classifier.trained_hazards),
        component_selection=selection,
        artifact_id=str(GOLDEN_ARTIFACT),
        rule_version=built.rule_version,
    )
    run_context = open_run(config, built.registry, classifier.trained_hazards)
    return run_context, built.registry, provider


def _row(index: int, *, hazard: str = "hte", response: str | None = None) -> InputRow:
    return InputRow(
        request_id=f"req-{index}",
        prompt_uid=f"pu-{index}",
        response_id=f"resp-{index}",
        prompt_text="How should I store household chemicals?",
        response_text=response
        if response is not None
        else "Store bleach and ammonia in separate cabinets.",
        supplied_hazard=hazard,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# --- Pass 1: run rejections abort before anything is scored ----------------


def test_a_bad_hazard_on_the_second_row_scores_nothing_and_writes_nothing(tmp_path) -> None:
    """**The crux of PR 7** (`PR7_EXECUTION_PLAN.md` §6). A runner that
    validated each row as it reached it would score row 0, then abort --
    leaving one row of results behind, which is exactly what
    `ARCHITECTURE.md` §2 says a rejection is *not*. Proven three ways: the
    error is raised, the encoder was never called at all, and no output file
    exists.
    """
    run_context, registry, provider = _resolved()
    rows = [_row(0, hazard="hte"), _row(1, hazard="not_in_scope")]

    with pytest.raises(RunRejectedError) as excinfo:
        runner.run_batch(rows, run_context, registry)

    # Asserted first, because this is the load-bearing property: a
    # single-pass runner raises the same error, with a plausible message,
    # having already scored row 0. Confirmed as a real forcing function by
    # sabotage -- folding validation into the scoring loop makes this line
    # fail with provider.calls == 1.
    assert provider.calls == 0

    # And nothing was written -- write_outputs is never called.
    for filename in runner.OUTPUT_FILENAMES:
        assert not (tmp_path / filename).exists()

    message = str(excinfo.value)
    assert "not_in_scope" in message
    assert "resp-1" in message  # names the offending row, not just the value


def test_a_blank_supplied_hazard_is_a_rejection_not_a_failure() -> None:
    run_context, registry, provider = _resolved()

    with pytest.raises(RunRejectedError):
        runner.run_batch([_row(0, hazard="   ")], run_context, registry)

    assert provider.calls == 0


def test_the_rejection_names_every_offending_row_not_just_the_first() -> None:
    """D-75. Pass 1 scans to the end, so cleaning a dirty input is one round
    rather than N: a caller who fixes the row the message names must not
    discover the next one only on the next run.
    """
    run_context, registry, provider = _resolved()
    rows = [
        _row(0, hazard="hte"),
        _row(1, hazard="not_in_scope"),
        _row(2, hazard="prv"),
        _row(3, hazard="also_bad"),
        _row(4, hazard="   "),
    ]

    with pytest.raises(RunRejectedError) as excinfo:
        runner.run_batch(rows, run_context, registry)

    message = str(excinfo.value)
    assert provider.calls == 0
    assert "3 of 5 input row(s)" in message
    for response_id, hazard in (("resp-1", "not_in_scope"), ("resp-3", "also_bad")):
        assert response_id in message
        assert hazard in message
    assert "resp-4" in message  # the blank one is named too
    # "not in scope" is unactionable without knowing the scope.
    assert "'hte', 'prv'" in message
    # The verdict is stated once, for the run -- not once per row, which
    # would read as though each line were its own rejected run.
    assert message.count("run rejected") == 1
    # The clean rows are not named -- the message is the problem list, not
    # a dump of the input.
    assert "resp-0" not in message
    assert "resp-2" not in message


def test_a_long_problem_list_is_summarized_in_the_message_but_not_in_the_query() -> None:
    """The message is read in a terminal, so it lists ten and counts the
    rest; `find_supplied_hazard_problems` -- what `--check-input` prints --
    keeps every one.
    """
    run_context, registry, _provider = _resolved()
    rows = [_row(index, hazard="not_in_scope") for index in range(25)]

    problems = runner.find_supplied_hazard_problems(rows, run_context)
    assert len(problems) == 25
    assert [problem.index for problem in problems] == list(range(25))

    message = runner.describe_supplied_hazard_problems(problems, run_context, len(rows))
    assert "25 of 25 input row(s)" in message
    assert "... and 15 more" in message
    assert "resp-9" in message
    assert "resp-10" not in message


def test_the_problem_query_and_the_run_always_agree() -> None:
    """**The property that makes a pre-flight check worth having** (D-75).
    A check that says "clean" and is then rejected -- or the reverse -- is
    worse than no check, so the two read one rule rather than two copies of
    it, and that is asserted rather than assumed.
    """
    run_context, registry, _provider = _resolved()

    for rows in (
        [_row(0), _row(1)],
        [_row(0), _row(1, hazard="not_in_scope")],
        [_row(0, hazard="   ")],
        [],
    ):
        problems = runner.find_supplied_hazard_problems(rows, run_context)
        try:
            runner.run_batch(rows, run_context, registry)
        except RunRejectedError:
            rejected = True
        else:
            rejected = False

        assert rejected == bool(problems), rows


def test_the_problem_query_carries_no_text() -> None:
    """The sensitive-data bound the tabular views hold to (§11), applied to
    the one other place a row's contents could leak.
    """
    run_context, _registry, _provider = _resolved()
    secret = "an unusual sentence that should never reach a rejection message"
    rows = [_row(0, hazard="not_in_scope", response=secret)]

    (problem,) = runner.find_supplied_hazard_problems(rows, run_context)

    assert secret not in json.dumps(dataclasses.asdict(problem))
    assert secret not in runner.describe_supplied_hazard_problems(
        (problem,), run_context, len(rows)
    )


# --- Pass 2: per-row failures never abort the batch ------------------------


def test_a_failing_row_does_not_abort_the_batch_and_lands_in_failures(tmp_path) -> None:
    """A phase D per-hazard failure: the batch completes, every row gets a
    record, and the failed row is named in `failures.csv`.
    """
    run_context, registry, _provider = _resolved(scoring_override=_MissingEnablementScorer())
    rows = [_row(0), _row(1), _row(2)]

    records = runner.run_batch(rows, run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    assert len(records) == 3  # the batch completed
    failures = _read_csv(paths[runner.FAILURES_FILENAME])
    assert [row["response_id"] for row in failures] == ["resp-0", "resp-1", "resp-2"]
    assert all(row["hazard"] == "hte" for row in failures)
    assert all("enablement" in row["failure_reason"] for row in failures)
    # Phase D decided, with no upstream component having reported a problem.
    assert all(row["stage"] == "final_integration" for row in failures)


def test_a_failed_row_still_appears_in_results_jsonl(tmp_path) -> None:
    """`PR7_EXECUTION_PLAN.md` §6: "A row whose every hazard failed still
    appears in `results.jsonl`... Do not make them exclusive."
    """
    run_context, registry, _provider = _resolved(scoring_override=_MissingEnablementScorer())

    records = runner.run_batch([_row(0)], run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    results = _read_jsonl(paths[runner.RESULTS_FILENAME])
    assert [entry["response_id"] for entry in results] == ["resp-0"]
    assert results[0]["overall_result"] == "failure"
    assert len(_read_csv(paths[runner.FAILURES_FILENAME])) == 1


def test_a_mixed_batch_scores_the_good_rows_and_fails_only_the_bad_one(tmp_path) -> None:
    """The distinction that matters most in practice: one row's content
    failing must not touch its neighbours' results.
    """

    class _SelectiveScorer(_MissingEnablementScorer):
        """Drops Enablement for `resp-1` only; every other row is scored by
        the real baseline scorer's logic being bypassed with a complete
        judgment pair.
        """

        implementation: ClassVar[str] = "stub_selective"

        def run(self, record: EvaluationRecord) -> EvaluationRecord:
            per_hazard = dict(record.per_hazard)
            drop_e = record.response_id == "resp-1"
            for hazard in record.evaluated_hazards:
                per_hazard[hazard] = HazardJudgment(
                    hazard=hazard,
                    source="supplied",
                    legitimization_applies=True,
                    provisional_l=Judgment(label="L1", distribution=None, model_version="stub:1"),
                    provisional_e=(
                        None
                        if drop_e
                        else Judgment(label="E0", distribution=None, model_version="stub:1")
                    ),
                )
            observation = ComponentObservation(
                stage=self.stage,
                implementation=self.implementation,
                version=self.version,
                maturity=self.maturity,
                outcome="ran",
                facts={},
                text_out=None,
                errors=(),
            )
            return dataclasses.replace(
                record, per_hazard=per_hazard, observations=record.observations + (observation,)
            )

    run_context, registry, _provider = _resolved(scoring_override=_SelectiveScorer())

    records = runner.run_batch([_row(0), _row(1), _row(2)], run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    assert [record.overall_result for record in records] == [
        "non_violating",
        "failure",
        "non_violating",
    ]
    failures = _read_csv(paths[runner.FAILURES_FILENAME])
    assert [row["response_id"] for row in failures] == ["resp-1"]

    # The two good rows are fully present in predictions.csv, unaffected.
    predictions = _read_csv(paths[runner.PREDICTIONS_FILENAME])
    assert [row["response_id"] for row in predictions] == ["resp-0", "resp-1", "resp-2"]
    assert [row["result"] for row in predictions] == ["non_violating", "failure", "non_violating"]


def test_a_component_that_raises_fails_only_its_own_row(tmp_path) -> None:
    """The backstop path: `ARCHITECTURE.md` §5 says no 1.1 component raises
    at run time, so a raise is a bug -- and a bug in one row must still not
    abort the batch (§6).
    """
    run_context, registry, _provider = _resolved(scoring_override=_RaisingScorer())

    records = runner.run_batch([_row(0), _row(1)], run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    assert len(records) == 2
    assert all(record.overall_result == "failure" for record in records)
    assert all("deliberate component bug" in record.overall_failure_reason for record in records)

    failures = _read_csv(paths[runner.FAILURES_FILENAME])
    assert [row["response_id"] for row in failures] == ["resp-0", "resp-1"]
    assert all("RuntimeError" in row["failure_reason"] for row in failures)
    # The stage is genuinely unknown -- the partial record is lost when the
    # exception unwinds run_pipeline -- and is recorded as absent, not guessed.
    assert all(row["stage"] == "" for row in failures)

    # The record stays canonical and lossless even so.
    results = _read_jsonl(paths[runner.RESULTS_FILENAME])
    assert [entry["response_id"] for entry in results] == ["resp-0", "resp-1"]


def test_a_run_rejection_is_never_swallowed_into_a_failures_row() -> None:
    """`_score_row` catches broad exceptions on purpose, so this pins that
    it does not catch the one exception that means something else entirely.
    Collapsing a rejection into a failure would erase §2's distinction.
    """

    class _RejectingScorer(_RaisingScorer):
        implementation: ClassVar[str] = "stub_rejecting"

        def run(self, record: EvaluationRecord) -> EvaluationRecord:
            raise RunRejectedError("a rejection raised from inside the pipeline")

    run_context, registry, _provider = _resolved(scoring_override=_RejectingScorer())

    with pytest.raises(RunRejectedError):
        runner.run_batch([_row(0)], run_context, registry)


# --- Rows in == rows out ---------------------------------------------------


def test_every_input_row_produces_exactly_one_record() -> None:
    """`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 5, carried into
    `PR7_EXECUTION_PLAN.md` §12: "a runner that scores 999 of 1000 rows and
    quietly drops one is the exact shape of this failure. Count rows in and
    rows out, and assert the total."
    """
    run_context, registry, _provider = _resolved()
    rows = [_row(index) for index in range(7)]

    records = runner.run_batch(rows, run_context, registry)

    assert len(records) == len(rows)
    assert [record.response_id for record in records] == [row.response_id for row in rows]


# --- Outputs ---------------------------------------------------------------


def test_a_clean_batch_writes_all_three_files_including_an_empty_failures_csv(tmp_path) -> None:
    """PR 7's headline exit criterion, at the unit level: an unlabeled input
    scores end to end and produces all three views. `failures.csv` is
    written even with nothing in it -- absence would be ambiguous between
    "no failures" and "the run did not get that far".
    """
    run_context, registry, _provider = _resolved()

    records = runner.run_batch([_row(0), _row(1)], run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    assert set(paths) == set(runner.OUTPUT_FILENAMES)
    for filename in runner.OUTPUT_FILENAMES:
        assert (tmp_path / filename).exists()

    assert len(_read_jsonl(paths[runner.RESULTS_FILENAME])) == 2
    assert len(_read_csv(paths[runner.PREDICTIONS_FILENAME])) == 2

    failures_path = paths[runner.FAILURES_FILENAME]
    assert _read_csv(failures_path) == []
    # ...but the header is there, so a consumer can read it unconditionally.
    assert failures_path.read_text(encoding="utf-8") == ",".join(views.FAILURE_COLUMNS) + "\n"


def test_outputs_are_written_in_input_order(tmp_path) -> None:
    run_context, registry, _provider = _resolved()
    rows = [_row(index) for index in (2, 0, 1)]

    records = runner.run_batch(rows, run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    expected = ["resp-2", "resp-0", "resp-1"]
    assert [entry["response_id"] for entry in _read_jsonl(paths[runner.RESULTS_FILENAME])] == expected
    assert [row["response_id"] for row in _read_csv(paths[runner.PREDICTIONS_FILENAME])] == expected


def test_the_same_input_produces_byte_identical_outputs(tmp_path) -> None:
    """§6's determinism requirement, asserted on bytes rather than on parsed
    content -- "sort nothing by dict iteration order".
    """
    rows = [_row(0), _row(1)]

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    for directory in (first_dir, second_dir):
        run_context, registry, _provider = _resolved()
        records = runner.run_batch(rows, run_context, registry)
        runner.write_outputs(records, directory)

    for filename in runner.OUTPUT_FILENAMES:
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes(), filename


def test_write_outputs_creates_a_missing_output_directory(tmp_path) -> None:
    run_context, registry, _provider = _resolved()
    records = runner.run_batch([_row(0)], run_context, registry)

    target = tmp_path / "nested" / "output"
    runner.write_outputs(records, target)

    assert (target / runner.RESULTS_FILENAME).exists()


# --- views.failure_rows, directly ------------------------------------------


def test_failure_rows_is_empty_for_a_clean_record() -> None:
    run_context, registry, _provider = _resolved()
    (record,) = runner.run_batch([_row(0)], run_context, registry)

    assert record.overall_result != "failure"
    assert views.failure_rows(record) == []


def test_failure_rows_carries_no_text() -> None:
    """The sensitive-data bound `prediction_rows` already holds to (§11)."""
    run_context, registry, _provider = _resolved(scoring_override=_MissingEnablementScorer())
    secret = "an unusual sentence that should never reach the failures view"
    (record,) = runner.run_batch([_row(0, response=secret)], run_context, registry)

    rendered = json.dumps(views.failure_rows(record))

    assert secret not in rendered
    assert record.texts.original not in rendered
    assert set(views.FAILURE_COLUMNS) == set(views.failure_rows(record)[0])


def test_failure_rows_names_the_component_stage_when_one_reported_an_error() -> None:
    """A `ComponentError` scoped to a hazard is what `stage` reports, rather
    than the integrator that merely acted on it.
    """
    run_context, registry, _provider = _resolved(scoring_override=_MissingEnablementScorer())
    (record,) = runner.run_batch([_row(0)], run_context, registry)

    from hazard_classifier.evaluator.record import ComponentError

    with_error = dataclasses.replace(
        record,
        observations=record.observations
        + (
            ComponentObservation(
                stage="scoring",
                implementation="x",
                version="1",
                maturity="partial",
                outcome="error",
                facts={},
                text_out=None,
                errors=(ComponentError(stage="scoring", message="unavailable", hazard="hte"),),
            ),
        ),
    )

    assert views.failure_rows(with_error)[0]["stage"] == "scoring"


def test_failure_rows_has_its_own_version_distinct_from_the_other_views() -> None:
    """§11: "every view is versioned separately"."""
    assert views.FAILURES_VERSION == "1"
    assert hasattr(views, "RESULT_VIEW_VERSION")
    assert hasattr(views, "PREDICTION_ROWS_VERSION")


# --- The single-threaded contract (D-61) -----------------------------------


def test_the_evaluator_builds_no_parallelism_anywhere() -> None:
    """`SCIENCE.md` §Evidence and outputs requires **concurrency**
    verification, scoped by [D-61](../../docs/planning/DECISIONS.md#d-61) to
    the contract 1.1 actually claims: single-threaded per process, no
    thread-safety claimed, parallelism (if any) at the process level and
    **1.1 builds none** (`ARCHITECTURE.md` §6).

    Determinism -- the "correct and reproducible" half -- is covered by
    `test_the_same_input_produces_byte_identical_outputs` and
    `test_run_is_deterministic_across_two_identical_calls`. What nothing
    pinned was the **contract itself**: D-61 said parallelism is not built,
    and only D-61's existence said so. A future session adding a thread pool
    to `run_batch` would break the claim in `ARCHITECTURE.md` §6, every
    determinism test would keep passing, and no test would notice.

    Checked statically, the way D-37's no-pickle rule is
    (`test_no_evaluator_module_imports_pickle_or_joblib`) -- a property of
    the code rather than of one run. This test failing is not automatically
    a defect: it means the contract changed, and `ARCHITECTURE.md` §6, D-61
    and `SCIENCE.md`'s concurrency item all have to move with it.
    """
    banned = {
        "threading",
        "multiprocessing",
        "concurrent",
        "asyncio",
        "subprocess",
        "joblib",
    }
    package_dir = Path(runner.__file__).resolve().parent
    paths = sorted(package_dir.rglob("*.py"))
    assert paths  # the glob itself must not silently match nothing

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".")[0]}
            else:
                continue
            offending = names & banned
            assert not offending, (
                f"{path.name} imports {sorted(offending)}; Release 1.1's contract is "
                "single-threaded per process with no parallelism built (D-61, "
                "ARCHITECTURE.md §6)"
            )


def test_run_batch_scores_rows_sequentially_in_input_order(tmp_path) -> None:
    """The observable half of the same contract: `run_batch` is a sequential
    loop, so the encoder is called exactly once per row and the records come
    back in input order.

    A parallel implementation would be free to interleave or batch these, so
    this pins the ordering guarantee a single-threaded runner actually gives
    -- which is what makes `results.jsonl` reproducible row for row, not
    merely deterministic in aggregate.
    """
    run_context, registry, provider = _resolved()
    rows = [_row(0), _row(1), _row(2)]

    records = runner.run_batch(rows, run_context, registry)
    paths = runner.write_outputs(records, tmp_path)

    assert [record.request_id for record in records] == [row.request_id for row in rows]
    # One `embed` call per row -- never batched across rows.
    assert provider.calls == len(rows)

    written = _read_jsonl(paths[runner.RESULTS_FILENAME])
    assert [record["request_id"] for record in written] == [row.request_id for row in rows]
