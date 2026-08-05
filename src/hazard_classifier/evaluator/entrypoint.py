"""The in-process Python entry point
(`docs/planning/PR7_EXECUTION_PLAN.md` §7).

**Built first, and `cli/run.py` is a thin wrapper over it.** The exit
criterion is that the CLI and the in-process interface "produce identical
records for identical input" -- cheap to guarantee only because the CLI
calls `run` below directly, rather than two independently written pipelines
that happen to agree today and could silently drift apart tomorrow.

This module does not import `evaluator.components` -- `provider`/`pooling`
are accepted untyped (matching `record.py`'s own loose-typing convention for
exactly this reason, `ARCHITECTURE.md` §3.2) and passed straight through to
`profile.resolve`, which resolves them against `profile.build_registry`, the
one place those imports belong (§5).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from . import input_schema
from . import profile as profile_module
from . import runner
from .record import EvaluationRecord


def run(
    run_profile: profile_module.RunProfile,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    provider=None,
    pooling=None,
    allow_download: bool = False,
) -> tuple[EvaluationRecord, ...]:
    """Score every row of `input_path` under `run_profile` and write
    `results.jsonl`/`predictions.csv`/`failures.csv` to `output_dir`.

    Returns the records, in input order, so a caller can inspect them
    directly rather than only through the files just written. Raises
    `profile.ProfileError` or `input_schema.InputSchemaError` for a
    malformed profile or input file, and `run.RunRejectedError` for a
    run-level rejection -- in which case, per `runner.run_batch`, nothing is
    written.

    Composes three already-built, already-tested pieces in the one order
    that matters: resolve the profile into a `RunContext` and `Registry`
    (`profile.resolve`), load and structurally validate the input
    (`input_schema.load_csv`), then run the two-pass batch runner
    (`runner.run_batch`/`write_outputs`). Nothing here is itself new
    behavior.
    """
    resolved = profile_module.resolve(
        run_profile, provider=provider, pooling=pooling, allow_download=allow_download
    )
    rows = input_schema.load_csv(input_path)
    records = runner.run_batch(rows, resolved.run_context, resolved.registry)
    runner.write_outputs(records, output_dir)
    return records


@dataclasses.dataclass(frozen=True)
class CheckReport:
    """What `check_input` found. `problems` is empty exactly when `run` on
    the same profile and input would not raise `RunRejectedError`.
    """

    rows: int
    hazard_scope: tuple[str, ...]
    problems: tuple[runner.SuppliedHazardProblem, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


def check_input(
    run_profile: profile_module.RunProfile,
    input_path: str | Path,
    *,
    provider=None,
    pooling=None,
    allow_download: bool = False,
) -> CheckReport:
    """Answer "would this run be rejected?" without scoring anything or
    writing anything ([D-75](../../docs/planning/DECISIONS.md#d-75)).

    **This is `run`'s own rejection path and nothing else** -- it performs
    exactly the three checks `ARCHITECTURE.md` §2 defines and stops:

    - conditions (2) and (3), a `hazard_scope` wider than the artifact
      supports and an unregistered implementation, raised out of
      `profile.resolve` -> `open_run` just as they are for a real run;
    - the input's structural contract, raised as `InputSchemaError` out of
      `input_schema.load_csv` -- a missing column, a blank identity, a
      duplicate `response_id`;
    - condition (1) for **every** row, returned in the report rather than
      raised, because listing all of them at once is the entire point.

    So a clean report is a genuine prediction, not an approximation: the
    only thing left between it and a scored batch is the pipeline itself,
    whose failures are per-row and never reject a run.

    **It deliberately does not score, so it cannot be a substitute for the
    run's own pass 1**, which still runs (`runner.run_batch`). This is a
    convenience over the same rule, not a gate the run trusts -- an input
    file can change between the two calls, and a check the run relied on
    would be a way for the two to disagree.

    Cheap by construction: the artifact is loaded and the ten components are
    constructed, but the encoder's weights load lazily on first use and
    nothing here embeds anything.
    """
    resolved = profile_module.resolve(
        run_profile, provider=provider, pooling=pooling, allow_download=allow_download
    )
    rows = input_schema.load_csv(input_path)
    problems = runner.find_supplied_hazard_problems(rows, resolved.run_context)
    return CheckReport(
        rows=len(rows),
        hazard_scope=tuple(sorted(resolved.run_context.hazard_scope)),
        problems=problems,
    )
