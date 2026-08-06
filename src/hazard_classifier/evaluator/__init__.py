"""The Release 1.1 evaluator (`docs/ARCHITECTURE.md` §§1-13).

A new package alongside the pre-staging baseline in `hazard_classifier`'s
top-level modules, not a rewrite of it (`ARCHITECTURE.md` §3.2). Built
incrementally across `docs/planning/RELEASE_1_1_QUEUE_PROPOSAL.md`'s PRs;
PRs 1 through 4 are landed (`STATUS.md`).

- `record.py`, `contract.py`, `registry.py`, `run.py` -- the carried record,
  the component protocol, the registry, and run entry (§2, §4, §6).
- `pipeline.py` -- stage order and the exhaustion short-circuit (§3, §3.1).
- `components/` -- the ten stages (§7): working, partial, and placeholder
  implementations, per `ARCHITECTURE.md` §7's maturity table.
- `views.py` -- derived outputs (§11); `results.jsonl`, `predictions.csv`,
  and `failures.csv` are built, `metrics.json` is not (it needs both PR 5's
  real model and the Standards team's approved criteria; the first cleared
  with PR 5 slice C, the second has not).
- `input_schema.py` -- the 1.1 input CSV schema and record construction
  (PR 7 slice A, `docs/planning/PR7_EXECUTION_PLAN.md` §4).
- `training/`, `artifact.py`, `no_fixed_rules.py` -- fitting the 1.1 L/E
  models and writing/reading the artifact that carries them (§10, PR 5
  slices A and B, `docs/planning/PR5_EXECUTION_PLAN.md`). Fitting is offline
  and separate from scoring, per `SCIENCE.md`'s "trained and versioned
  separately from scoring".
- `profile.py` -- the run profile and artifact resolution: `RunProfile`,
  `resolve_artifact` (both formats, dispatching on the 1.1 manifest's
  `format` field), `build_registry` (the one file that imports
  `components/*`, and where stage 9's implementation follows the artifact),
  and `resolve` (profile -> `RunContext`) (PR 7 slice B,
  `PR7_EXECUTION_PLAN.md` §5; PR 5 slice C added the 1.1 branch).
- `runner.py` -- the two-pass batch runner and the three output files
  (PR 7 slice C, `PR7_EXECUTION_PLAN.md` §6).
- `entrypoint.py` -- the in-process Python entry point (`run`, plus
  `check_input` for the pre-flight path, `DECISIONS.md` D-75); `hrc-run`
  (`hazard_classifier.cli.run`) is a thin CLI wrapper over both, so the two
  are guaranteed to produce identical records for identical input (PR 7
  slice D, `PR7_EXECUTION_PLAN.md` §7).

**As of PR 7 the evaluator is runnable end to end** — an unlabeled CSV, a
run profile, and an artifact produce `results.jsonl`, `predictions.csv`, and
`failures.csv`, from the CLI or in process — and **as of PR 5 slice C it
scores with the real three-class model** rather than PR 1's wrapped baseline.
What it is *not* is finished: Release 1.1 is a pre-staging prototype
(`DECISIONS.md` D-58) whose hazard, narrative, and refusal stages are visible
placeholders, and **whose L and E models are reported *not evaluated*** —
approved per-outcome criteria do not exist, and the structure was selected on
a null result (D-68). `README.md` §Release 1.1 evaluator status is the
disclosure that governs anything this package produces;
`docs/howto/hrc-run.md` is how to drive it.
"""
