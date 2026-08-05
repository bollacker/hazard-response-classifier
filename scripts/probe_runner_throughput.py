#!/usr/bin/env python3
"""Measure what a real Release 1.1 batch run actually costs.

**Why this exists.** `PR7_EXECUTION_PLAN.md` §8 asks slice E to "report the
wall-clock cost of a real run and note rows-per-second in `STATUS.md`...
Not a performance-tuning exercise -- a recorded number, so the first person
to run a large batch is not surprised." §9 is explicit that the shape being
measured is *not* to be redesigned: `ARCHITECTURE.md` §8 fixes **one embed
call per record**, so an N-row batch makes up to N encoder calls rather than
one batched call, and restructuring that would move a component's work into
the runner. Measure it, record it, and if it is genuinely too slow for a
real benchmark run that is a finding for `STATUS.md` and a decision for
Kurt.

A number in a document rots; a script that reproduces it does not. This is
the quotable source for the figure `STATUS.md` carries, in the same role as
`scripts/probe_disclaimer_scope.py` and `scripts/probe_working_text_delta.py`.

**What it runs.** The same composition `evaluator/entrypoint.py` performs --
`profile.resolve` -> `input_schema.load_csv` -> `runner.run_batch` ->
`runner.write_outputs` -- decomposed only so each phase can be timed
separately. Nothing is stubbed: the real `BgeEmbeddingProvider`, the real
golden baseline artifact, real response texts from `data/`, real files
written to a temporary directory.

**What the rows are.** `data/`'s 859 Jailbreak v1.0 rows, filtered to the
hazards the golden artifact was actually trained on (`hte`, `prv`) so the
run is not a `hazard_scope` rejection. Their `response_text` values are real
and are what makes the timing meaningful -- a synthetic one-sentence fixture
would understate the cost by an order of magnitude. The identity columns the
1.1 schema requires but this dataset does not carry (`request_id`,
`response_id`) are synthesized **here, for the probe only**; nothing in the
evaluator ever synthesizes an identity (`input_schema.py` rejects a blank
one outright).

**What the numbers mean.** `startup` includes loading the artifact and
constructing the ten components, but the encoder's weights load lazily
inside the first `embed()` call, so the first scored row carries that cost
and is reported separately. `steady_state_rows_per_second` excludes it and
is the figure to quote for a large batch. Rows that **exhaust** (empty or
prompt-only responses) never reach the encoder at all
(`ARCHITECTURE.md` §3.1), so throughput is a property of the input as much
as of the machine -- the exhausted count is reported for that reason.

Run:  python scripts/probe_runner_throughput.py
      python scripts/probe_runner_throughput.py --rows 40
      python scripts/probe_runner_throughput.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from hazard_classifier.evaluator import input_schema, profile, runner  # noqa: E402

DATA_CSV = REPO_ROOT / "data" / "jb_1.0_1003_ground_truth_items_for_riki_eval__with_seed_prompt_id.csv"
GOLDEN_ARTIFACT = REPO_ROOT / "tests" / "golden" / "baseline" / "artifact"

INPUT_COLUMNS = list(input_schema.REQUIRED_COLUMNS)


def build_input_csv(path: Path, limit: int | None) -> tuple[int, int]:
    """Write a 1.1 input CSV from `data/`'s real rows, keeping only hazards
    the golden artifact supports. Returns (row count, total response chars).
    """
    import pandas as pd

    frame = pd.read_csv(DATA_CSV, dtype=str, keep_default_na=False)
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    supported = {h.strip().lower().replace("-", "_") for h in classifier.trained_hazards}

    rows: list[dict[str, str]] = []
    for index, record in enumerate(frame.to_dict(orient="records")):
        hazard = str(record["hazard"]).strip().lower().replace("-", "_")
        if hazard not in supported:
            continue
        rows.append(
            {
                "request_id": f"probe-req-{index}",
                "prompt_uid": str(record["prompt_uid"]),
                "response_id": f"probe-resp-{index}",
                "prompt_text": str(record["prompt_text"]),
                "response_text": str(record["response_text"]),
                "supplied_hazard": hazard,
            }
        )
        if limit is not None and len(rows) >= limit:
            break

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows), sum(len(row["response_text"]) for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Cap the number of input rows (default: every supported row in data/).",
    )
    parser.add_argument("--json", action="store_true", help="Emit the measurements as JSON only.")
    args = parser.parse_args(argv)

    if not DATA_CSV.exists():
        print(f"missing {DATA_CSV}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as workspace:
        directory = Path(workspace)
        input_csv = directory / "input.csv"
        row_count, response_chars = build_input_csv(input_csv, args.rows)
        if row_count == 0:
            print("no rows in data/ carry a hazard the golden artifact supports", file=sys.stderr)
            return 1

        started = time.perf_counter()
        resolved = profile.resolve(profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT)))
        startup_seconds = time.perf_counter() - started

        rows = input_schema.load_csv(input_csv)
        load_seconds = time.perf_counter() - started - startup_seconds

        # `runner.run_batch` scores the whole batch in one call, so per-row
        # timing is taken by calling it once per row. That repeats its
        # rejection pass N times instead of once -- N frozenset lookups per
        # call, microseconds against a ~130 ms row -- which is the price of
        # getting a per-row distribution rather than one aggregate. The
        # scoring work itself is identical: `run_batch` is a plain loop over
        # `_score_row` with no batching of its own (`ARCHITECTURE.md` §8
        # fixes one embed call per record, §9 forbids changing that here).
        scoring_started = time.perf_counter()
        per_row_seconds: list[float] = []
        records = []
        for row in rows:
            row_started = time.perf_counter()
            (record,) = runner.run_batch([row], resolved.run_context, resolved.registry)
            per_row_seconds.append(time.perf_counter() - row_started)
            records.append(record)
        scoring_seconds = time.perf_counter() - scoring_started

        write_started = time.perf_counter()
        runner.write_outputs(records, directory / "out")
        write_seconds = time.perf_counter() - write_started

    exhausted = sum(1 for record in records if record.exhausted_at is not None)
    scored = row_count - exhausted
    steady = per_row_seconds[1:] or per_row_seconds

    measurements = {
        "rows": row_count,
        "scored_rows": scored,
        "exhausted_rows": exhausted,
        "mean_response_chars": round(response_chars / row_count, 1),
        "startup_seconds": round(startup_seconds, 3),
        "input_load_seconds": round(load_seconds, 3),
        "scoring_seconds": round(scoring_seconds, 3),
        "write_seconds": round(write_seconds, 3),
        "total_seconds": round(startup_seconds + load_seconds + scoring_seconds + write_seconds, 3),
        "first_row_seconds": round(per_row_seconds[0], 3),
        "median_row_seconds": round(statistics.median(steady), 3),
        "max_row_seconds": round(max(steady), 3),
        "steady_state_rows_per_second": round(len(steady) / sum(steady), 2),
        "end_to_end_rows_per_second": round(
            row_count / (startup_seconds + load_seconds + scoring_seconds + write_seconds), 2
        ),
    }

    if args.json:
        print(json.dumps(measurements, indent=2))
        return 0

    print(f"Artifact: {GOLDEN_ARTIFACT}")
    print(f"Input:    {measurements['rows']} real rows from data/ "
          f"({measurements['scored_rows']} scored, {measurements['exhausted_rows']} exhausted), "
          f"mean response {measurements['mean_response_chars']} chars")
    print()
    print(f"  startup (artifact + components)   {measurements['startup_seconds']:>8.3f} s")
    print(f"  input load + validate             {measurements['input_load_seconds']:>8.3f} s")
    print(f"  scoring loop                      {measurements['scoring_seconds']:>8.3f} s")
    print(f"  write three views                 {measurements['write_seconds']:>8.3f} s")
    print(f"  total                             {measurements['total_seconds']:>8.3f} s")
    print()
    print(f"  first row (loads encoder weights) {measurements['first_row_seconds']:>8.3f} s")
    print(f"  median row thereafter             {measurements['median_row_seconds']:>8.3f} s")
    print(f"  slowest row thereafter            {measurements['max_row_seconds']:>8.3f} s")
    print()
    print(f"  steady-state throughput           {measurements['steady_state_rows_per_second']:>8.2f} rows/s")
    print(f"  end-to-end throughput             {measurements['end_to_end_rows_per_second']:>8.2f} rows/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
