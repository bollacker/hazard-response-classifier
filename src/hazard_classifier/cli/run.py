"""`hrc-run` (`docs/planning/PR7_EXECUTION_PLAN.md` §7): score an unlabeled
1.1 input CSV end to end, with no retraining -- the fourth CLI, not a
modification of the three baseline ones (`DECISIONS.md` D-48). `hrc-evaluate`
is already taken by the baseline and means something else: it scores
*labelled* rows against ground truth, not unlabeled ones.

Thin wrapper around `evaluator.entrypoint.run` -- calls it directly, so this
CLI and the in-process interface are guaranteed to produce identical records
for identical input by construction, not merely by both having been written
carefully (`tests/unit/test_cli_run.py`'s identity test proves this by
running both and comparing the parsed `results.jsonl`, not by asserting they
share a function).

`--check-input` is the same wrapper over `entrypoint.check_input`: it reports
every row that would reject the run and exits without scoring anything
(`DECISIONS.md` D-75). Both modes read the same rule -- `runner`'s pass 1 --
so the check cannot disagree with the run it predicts.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from hazard_classifier.evaluator import entrypoint
from hazard_classifier.evaluator.input_schema import InputSchemaError
from hazard_classifier.evaluator.profile import ProfileError, load_profile
from hazard_classifier.evaluator.run import RunRejectedError

from ._common import add_allow_download_flag, fatal


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrc-run",
        description=(
            "Score an unlabeled Release 1.1 input CSV end to end, no retraining "
            "(docs/planning/PR7_EXECUTION_PLAN.md)."
        ),
    )
    parser.add_argument(
        "--profile",
        required=True,
        type=Path,
        help="Run profile JSON (evaluator.profile.RunProfile's fields).",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help=(
            "Artifact directory to score against; overrides the profile's own "
            "artifact_id when given, so one profile file can be reused across "
            "machines without a hard-coded path."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="1.1 input CSV (evaluator.input_schema.REQUIRED_COLUMNS).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write results.jsonl/predictions.csv/failures.csv to. "
            "Required unless --check-input is given, which writes nothing."
        ),
    )
    parser.add_argument(
        "--check-input",
        action="store_true",
        default=False,
        help=(
            "Pre-flight only: report every input row that would reject the run, "
            "then exit without scoring anything. Exits 1 if any would."
        ),
    )
    add_allow_download_flag(parser)
    return parser


def _check_input(run_profile, args) -> None:
    """`--check-input`: print what would reject this run, and exit.

    Every offending row is listed, not the first ten the run's own error
    message spells out -- a caller asking this question wants the whole list
    so cleaning the file is one pass (D-75).
    """
    report = entrypoint.check_input(
        run_profile, args.input, allow_download=args.allow_download
    )

    if report.ok:
        print(
            f"hrc-run: {report.rows} row(s) OK against hazard_scope="
            f"{list(report.hazard_scope)!r} -- this input would not be rejected."
        )
        return

    print(
        f"hrc-run: {len(report.problems)} of {report.rows} row(s) would reject the run "
        f"(hazard_scope={list(report.hazard_scope)!r}):",
        file=sys.stderr,
    )
    for problem in report.problems:
        print(
            f"  row {problem.index} (response_id={problem.response_id!r}): "
            f"{problem.reason}",
            file=sys.stderr,
        )
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    # Checked here rather than by argparse: --output-dir is required for a
    # real run and meaningless for a check, which writes nothing.
    if not args.check_input and args.output_dir is None:
        fatal("hrc-run: --output-dir is required (omit it only with --check-input)")

    try:
        run_profile = load_profile(args.profile)
    except ProfileError as exc:
        fatal(f"hrc-run: {exc}")

    if args.model_dir is not None:
        run_profile = dataclasses.replace(run_profile, artifact_id=str(args.model_dir))

    try:
        if args.check_input:
            _check_input(run_profile, args)
            return

        records = entrypoint.run(
            run_profile,
            args.input,
            args.output_dir,
            allow_download=args.allow_download,
        )
    except InputSchemaError as exc:
        fatal(f"hrc-run: {exc}")
    except RunRejectedError as exc:
        fatal(f"hrc-run: {exc}")
    except FileNotFoundError as exc:
        fatal(f"hrc-run: could not load artifact from {run_profile.artifact_id}: {exc}")

    failed = sum(1 for record in records if record.overall_result == "failure")
    print(f"Scored {len(records)} row(s), {failed} failed -- wrote results.jsonl/predictions.csv/failures.csv to {args.output_dir}")


if __name__ == "__main__":
    main()
