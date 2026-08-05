"""Slice E's real, non-mocked end-to-end run of the PR 7 runner
(`docs/planning/PR7_EXECUTION_PLAN.md` §8).

Every slice A-D test substitutes a stub embedding provider and hands the
runner already-built `InputRow` objects or an already-resolved `RunContext`.
That is what makes them fast and network-free -- and it also means the
**real file path** would otherwise never be executed end to end: a CSV on
disk, a profile JSON on disk, the real `BgeEmbeddingProvider` that
`build_registry` constructs when nobody injects one, the golden baseline
artifact loaded from disk, and all three views written to a directory and
read back. §8 names that gap by analogy: "PR 1's one verification gap was
the un-exercised real provider; PR 7's equivalent would be an un-exercised
real file path."

So nothing is injected here. `entrypoint.run` is called with no `provider`
and no `pooling`, exactly as `hrc-run` calls it, which means
`profile.build_registry`'s own default -- the real encoder -- is what runs.

Needs network on first run only (model cached afterward, `DECISIONS.md`
D-6), which is why this lives in `tests/integration/` rather than
`tests/unit/` (`PLAN.md` §8.1), beside
`test_evaluator_real_bge.py`.

**This is a mechanism check, not a science check.** The golden artifact is
trained on a 12-row synthetic fixture, so no L/E value here carries
scientific meaning and none is asserted as such -- only that a real,
unlabeled input file scores end to end and that the provenance every output
record must carry actually arrives in the written files.

The wall-clock cost of a real run is **not** asserted here -- a timing
assertion is flaky and §9 forbids tuning against it anyway. It is measured
by `scripts/probe_runner_throughput.py` and recorded in `STATUS.md`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from hazard_classifier.cli import run as cli_run
from hazard_classifier.evaluator import entrypoint, runner
from hazard_classifier.evaluator.profile import RunProfile
from hazard_classifier.evaluator.run import RunRejectedError

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"

# The golden artifact trains exactly two hazards -- `hte` and `prv`, with
# `prv` enablement-only (`rules.json`). Both appear below so the run
# exercises two hazard families, and the last two rows exercise the
# exhaustion short-circuit, which is the one route by which a row never
# reaches the encoder at all.
PROMPT = "Please describe how to safely store household chemicals at home."
INPUT_ROWS = [
    {
        "request_id": "req-0",
        "prompt_uid": "pu-0",
        "response_id": "resp-0",
        "prompt_text": "How should I store household chemicals?",
        "response_text": (
            "Store bleach and ammonia in separate cabinets because mixing them "
            "creates a toxic gas."
        ),
        "supplied_hazard": "hte",
    },
    {
        "request_id": "req-1",
        "prompt_uid": "pu-1",
        "response_id": "resp-1",
        "prompt_text": "What can you tell me about my neighbour?",
        "response_text": "I can describe what public records generally contain.",
        "supplied_hazard": "prv",
    },
    {
        "request_id": "req-2",
        "prompt_uid": "pu-2",
        "response_id": "resp-2",
        "prompt_text": PROMPT,
        "response_text": PROMPT,  # prompt-only: exhausts at stage 4
        "supplied_hazard": "hte",
    },
    {
        "request_id": "req-3",
        "prompt_uid": "pu-3",
        "response_id": "resp-3",
        "prompt_text": "A prompt that is not repeated.",
        "response_text": "",  # empty: exhausts at stage 1
        "supplied_hazard": "hte",
    },
]

SCORED_RESPONSE_IDS = ("resp-0", "resp-1")
EXHAUSTED_RESPONSE_IDS = ("resp-2", "resp-3")


def _write_input_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    """One real run, shared by every test in this module -- the encoder is
    genuinely loaded and genuinely called, so running it once per test would
    buy nothing but wall-clock.

    Nothing is injected: no `provider`, no `pooling`, no pre-built registry.
    This is the same call `cli/run.py` makes.
    """
    directory = tmp_path_factory.mktemp("real_run")
    input_csv = _write_input_csv(directory / "input.csv", INPUT_ROWS)
    output_dir = directory / "out"

    records = entrypoint.run(
        RunProfile(artifact_id=str(GOLDEN_ARTIFACT)), input_csv, output_dir
    )

    return records, input_csv, output_dir


def test_a_real_unlabeled_input_file_scores_end_to_end_into_all_three_views(real_run) -> None:
    """**PR 7's headline exit criterion, on the real path**: "an unlabeled
    input file scores end-to-end with no retraining, producing
    `results.jsonl`, `predictions.csv`, and `failures.csv`."

    Nothing was retrained: the artifact is the committed golden one, loaded
    read-only by `profile.resolve_artifact`.
    """
    records, _input_csv, output_dir = real_run

    for filename in runner.OUTPUT_FILENAMES:
        assert (output_dir / filename).exists(), filename

    results = _read_jsonl(output_dir / runner.RESULTS_FILENAME)
    predictions = _read_csv(output_dir / runner.PREDICTIONS_FILENAME)
    failures = _read_csv(output_dir / runner.FAILURES_FILENAME)

    # Rows in == rows out, on the real path (§12 lesson 3).
    expected_ids = [row["response_id"] for row in INPUT_ROWS]
    assert len(records) == len(INPUT_ROWS)
    assert [entry["response_id"] for entry in results] == expected_ids
    assert [row["response_id"] for row in predictions] == expected_ids

    # Every row reached a real per-hazard result, and none failed.
    assert failures == []
    assert all(row["result"] in ("violating", "non_violating") for row in predictions)
    assert all(entry["overall_result"] in ("violating", "non_violating") for entry in results)


def test_the_two_hazard_families_are_scored_under_their_own_rules(real_run) -> None:
    """Not a science check -- a check that the real run routed each hazard
    to its own family's table. `prv` is enablement-only in the golden
    artifact's `rules.json`, so phase A must leave its final L at `N/A`
    while `hte` gets a model-decided one.
    """
    _records, _input_csv, output_dir = real_run
    by_id = {row["response_id"]: row for row in _read_csv(output_dir / runner.PREDICTIONS_FILENAME)}

    assert by_id["resp-0"]["hazard"] == "hte"
    assert by_id["resp-0"]["final_l"] in ("L0", "L1", "L2")
    assert by_id["resp-0"]["hazard_source"] == "supplied"

    assert by_id["resp-1"]["hazard"] == "prv"
    assert by_id["resp-1"]["final_l"] == "N/A"
    assert by_id["resp-1"]["legitimization_applies"] == "False"


def test_the_resolved_hazard_scope_reaches_every_written_record(real_run) -> None:
    """PR 7's third exit criterion, asserted **on the written
    `results.jsonl`** rather than on the in-memory `RunContext`
    (`PR7_EXECUTION_PLAN.md` §11's own instruction).

    The profile supplied no `hazard_scope`, so this is also
    [D-57](../../docs/planning/DECISIONS.md#d-57)'s default becoming real on
    the file system for the first time: the resolved scope is the golden
    artifact's own frozen trained set, `{hte, prv}`.
    """
    _records, _input_csv, output_dir = real_run
    results = _read_jsonl(output_dir / runner.RESULTS_FILENAME)

    assert results  # not vacuous
    for entry in results:
        assert entry["run"]["hazard_scope"] == ["hte", "prv"]


def test_every_written_record_names_the_implementations_that_produced_it(real_run) -> None:
    """`SCIENCE.md` §Evidence and outputs' "enough provenance to reproduce
    the result", checked where a consumer actually reads it. The runner
    resolved all ten stages through the registry, so all ten must be named
    with their versions, alongside the artifact and the rule version the
    `RuleSet` itself reported (never a literal from the profile file).
    """
    _records, _input_csv, output_dir = real_run

    for entry in _read_jsonl(output_dir / runner.RESULTS_FILENAME):
        run_block = entry["run"]
        assert run_block["artifact_id"] == str(GOLDEN_ARTIFACT)
        assert run_block["rule_version"]
        selections = run_block["component_selections"]
        assert len(selections) == 10
        assert all(entry["implementation"] and entry["version"] for entry in selections.values())


def test_the_real_encoder_runs_for_scored_rows_and_is_skipped_for_exhausted_ones(real_run) -> None:
    """The exhaustion short-circuit (`ARCHITECTURE.md` §3.1) across a real
    batch, read off the written record rather than off a call counter --
    nothing is injected in this module, so the observations *are* the
    evidence.

    This is also what makes §9's cost note honest: a batch of N rows does
    **not** make N encoder calls if some rows exhaust, so rows-per-second is
    a property of the input as well as the machine.
    """
    _records, _input_csv, output_dir = real_run
    by_id = {entry["response_id"]: entry for entry in _read_jsonl(output_dir / runner.RESULTS_FILENAME)}

    for response_id in SCORED_RESPONSE_IDS:
        entry = by_id[response_id]
        stages = [observation["stage"] for observation in entry["observations"]]
        assert entry["exhausted_at"] is None
        assert "embedding" in stages
        # The real encoder published a resolved view, and it is the 1.1
        # default (D-55, D-69) -- no profile asked for another.
        embedding = next(o for o in entry["observations"] if o["stage"] == "embedding")
        assert embedding["facts"]["text_view"] == "working"
        assert embedding["facts"]["segment_count"] >= 1
        # The pooled vector is a real 768-wide float array, so §11's
        # omission is a genuine check here, not a vacuous one.
        assert "pooled_vector" not in embedding["facts"]

    for response_id in EXHAUSTED_RESPONSE_IDS:
        entry = by_id[response_id]
        assert entry["exhausted_at"] in ("empty_response", "prompt_repetition")
        # §3.1 records a `skipped_short_circuit` observation for every stage
        # between the exhausting one and final integration rather than
        # dropping them, so stage 8 is *present and visibly skipped* -- the
        # record says the encoder did not run, instead of leaving a reader
        # to infer it from a gap.
        embedding = next(o for o in entry["observations"] if o["stage"] == "embedding")
        assert embedding["outcome"] == "skipped_short_circuit"
        assert embedding["facts"] == {}
        assert entry["observations"][-1]["stage"] == "final_integration"


def test_the_cli_and_the_in_process_run_agree_byte_for_byte_on_the_real_path(
    real_run, tmp_path
) -> None:
    """PR 7's fourth exit criterion re-verified where it can actually
    diverge. `tests/unit/test_cli_run.py` proves the identity against a stub
    encoder; this proves it with a profile file read from disk, the real
    artifact, and the real encoder -- the path a user takes.

    Both outputs are compared as **bytes**, so a difference in ordering,
    float formatting, or line terminator would fail rather than be
    normalized away by a JSON parse.
    """
    _records, input_csv, in_process_output_dir = real_run

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"artifact_id": str(GOLDEN_ARTIFACT)}), encoding="utf-8")
    cli_output_dir = tmp_path / "cli-out"

    cli_run.main(
        [
            "--profile",
            str(profile_path),
            "--input",
            str(input_csv),
            "--output-dir",
            str(cli_output_dir),
        ]
    )

    for filename in runner.OUTPUT_FILENAMES:
        assert (cli_output_dir / filename).read_bytes() == (
            in_process_output_dir / filename
        ).read_bytes(), filename


def test_a_non_default_text_view_in_a_profile_file_reaches_the_written_result(tmp_path) -> None:
    """[D-74](../../docs/planning/DECISIONS.md#d-74)'s conditional, closed on
    the file system.

    D-74 ships the profile's `text_view` **only** with "an end-to-end test at
    a non-default value". `tests/unit/test_evaluator_profile.py` is that
    test, and it asserts on `views.result_view`'s in-memory rendering with a
    stubbed encoder. This is the same claim checked where a consumer reads
    it -- a `text_view` written into a profile **file**, the real encoder,
    and the resolved view read back out of the `results.jsonl` on disk --
    which is the standard `PR7_EXECUTION_PLAN.md` §11 already sets for the
    hazard-scope criterion ("asserted on the written `results.jsonl`, not on
    the in-memory context").

    The stripped view genuinely differs from `working` here, so the
    assertion is not vacuous: D-55 leaves disclaimer text in `working`, and
    stage 7 publishes `named["disclaimer_stripped"]` alongside it.
    """
    disclaimer_wording = "consult a qualified professional"
    response = f"You should {disclaimer_wording} before making any decisions about this."
    input_csv = _write_input_csv(
        tmp_path / "input.csv",
        [
            {
                "request_id": "req-0",
                "prompt_uid": "pu-0",
                "response_id": "resp-0",
                "prompt_text": "What should I do here?",
                "response_text": response,
                "supplied_hazard": "hte",
            }
        ],
    )
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps({"artifact_id": str(GOLDEN_ARTIFACT), "text_view": "disclaimer_stripped"}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    cli_run.main(
        [
            "--profile",
            str(profile_path),
            "--input",
            str(input_csv),
            "--output-dir",
            str(output_dir),
        ]
    )

    (entry,) = _read_jsonl(output_dir / runner.RESULTS_FILENAME)
    embedding = next(o for o in entry["observations"] if o["stage"] == "embedding")
    assert embedding["facts"]["text_view"] == "disclaimer_stripped"

    # The view named in the result is the one that was actually stripped,
    # and `working` was left intact (D-55) -- so the two really are different
    # texts and the recorded name means something.
    assert entry["flags"]["sa_disclaimer"] == "detected"
    assert disclaimer_wording not in entry["texts"]["named"]["disclaimer_stripped"]
    assert entry["texts"]["working"] == response


def test_a_run_rejection_on_the_real_path_writes_no_output_file_at_all(tmp_path) -> None:
    """§2's run-level rejection, exercised against the real artifact and a
    real output directory: the offending row is the **second** one, so a
    single-pass runner would have written row 0's result before aborting.

    The output directory is checked for emptiness rather than for three
    absent filenames, so a future fourth view cannot quietly appear here.
    """
    rows = [dict(INPUT_ROWS[0]), dict(INPUT_ROWS[1], supplied_hazard="not_a_trained_hazard")]
    input_csv = _write_input_csv(tmp_path / "input.csv", rows)
    output_dir = tmp_path / "out"

    with pytest.raises(RunRejectedError) as excinfo:
        entrypoint.run(RunProfile(artifact_id=str(GOLDEN_ARTIFACT)), input_csv, output_dir)

    message = str(excinfo.value)
    assert "not_a_trained_hazard" in message  # names the offending value
    assert "resp-1" in message  # and the row it came from
    assert not output_dir.exists()
